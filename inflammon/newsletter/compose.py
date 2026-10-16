"""Diff a snapshot against the previous fingerprint and compose one issue."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from html import unescape
from pathlib import Path

from inflammon.compliance import (
    FDA_ATTRIBUTION,
    FDA_CAVEAT,
    FDA_INDEPENDENCE,
    NCBI_DISCLAIMER_URL,
    RESEARCH_LINE,
    postal_address,
)
from inflammon.newsletter.cadence import newsletter_cadence
from inflammon.taxonomy import CONDITIONS, DISCLAIMER, DRUG_CLASSES, DRUG_TOPICS

CLASS_SHORT = {item.key: item.short_label for item in DRUG_CLASSES}
TOPIC_LABELS = {item.key: item.label for item in (*CONDITIONS, *DRUG_TOPICS)}

ALERT_CAP = 5
RECALL_CAP = 4
SIGNAL_CAP = 6
TRIAL_CAP = 4
PAPER_CAP = 4
STRENGTHEN_RATIO = 1.25

COMPARATOR_PHRASE = {
    "all_faers": "the rest of FAERS",
}
COMPARATOR_SENTENCE = {
    "all_faers": "all other FAERS reports",
}


def load_snapshot(directory: str | Path) -> dict:
    root = Path(directory)

    def load(name: str) -> dict:
        path = root / name
        if not path.is_file():
            raise FileNotFoundError(f"Missing {path}. Run `make refresh` before building a newsletter issue.")
        return json.loads(path.read_text(encoding="utf8"))

    recent = load("recent.json")
    return {
        "manifest": load("manifest.json"),
        "alerts": load("alerts.json").get("items") or [],
        "recalls": load("recalls.json").get("items") or [],
        "signals": load("signals.json").get("rows") or [],
        "validation": load("validation.json"),
        "publications": recent.get("publications") or [],
        "trials": recent.get("trials") or [],
    }


def signal_identity(row: dict) -> str:
    scope = row.get("scope") or "class"
    who = row.get("drug") if scope == "drug" else (row.get("drug_class") or row.get("key"))
    return "|".join(
        [
            str(row.get("analysis") or ""),
            str(scope),
            str(who or ""),
            str(row.get("reaction") or ""),
            str(row.get("comparator") or ""),
        ]
    )


def is_high(row: dict) -> bool:
    if row.get("admin_term") or row.get("indication_term"):
        return False
    if row.get("preset") is False:
        return False
    return bool(row.get("evans_signal") or row.get("ror_signal"))


def fingerprint(snapshot: dict) -> dict:
    high: dict[str, float | None] = {}
    for row in snapshot["signals"]:
        if is_high(row):
            high[signal_identity(row)] = row.get("prr")
    return {
        "snapshot_generated_at": snapshot["manifest"].get("generated_at"),
        "alert_keys": sorted({alert_key(item) for item in snapshot["alerts"]}),
        "recall_keys": sorted({recall_key(item) for item in snapshot["recalls"]}),
        "high_signals": {key: high[key] for key in sorted(high)},
        "trial_keys": sorted(item.get("nct_id") for item in snapshot["trials"] if item.get("nct_id")),
        "paper_keys": sorted(item.get("pmid") for item in snapshot["publications"] if item.get("pmid")),
    }


def compose_issue(
    snapshot: dict,
    previous: dict | None,
    *,
    site_url: str,
    cadence: str | None = None,
) -> dict:
    manifest = snapshot["manifest"]
    generated_at = manifest.get("generated_at") or datetime.now(timezone.utc).isoformat()
    slug = _slug(generated_at)
    site = site_url.rstrip("/") or "http://127.0.0.1:43123"
    resolved = newsletter_cadence(cadence)
    daily = resolved == "daily"
    inaugural = previous is None
    if daily:
        kind = "daily"
        empty = "None in this daily edition."
    elif inaugural:
        kind = "inaugural"
        empty = "None in this snapshot."
    else:
        kind = "weekly"
        empty = "None this week."

    alerts = _alerts(snapshot["alerts"], previous, inaugural)
    recalls = _recalls(snapshot["recalls"], previous, inaugural)
    ranked_signals = _ranked_signal_changes(snapshot, previous, inaugural)
    signals = [_signal_item(row, change, previous_prr) for row, change, previous_prr in ranked_signals]
    trials = _trials(snapshot["trials"], previous, inaugural)
    papers = _papers(snapshot["publications"], previous, inaugural)

    headline = _headline(ranked_signals, generated_at, inaugural, daily)
    intro = _intro(snapshot, previous, inaugural, generated_at, daily)
    long_date = _long_date(generated_at)
    if daily:
        kicker = f"Daily test edition · {long_date}"
    elif inaugural:
        kicker = f"Inaugural briefing · {long_date}"
    else:
        kicker = f"Week of {long_date}"
    subject = headline
    if daily and not headline.lower().startswith("daily test edition"):
        subject = f"Daily test edition: {headline}"
    return {
        "product": "Inflammation Signal Monitor",
        "slug": slug,
        "cadence": resolved,
        "kind": kind,
        "subject": subject,
        "headline": headline,
        "kicker": kicker,
        "intro": intro,
        "preheader": intro.split(". ")[0].rstrip(".") + ".",
        "snapshot_generated_at": generated_at,
        "openfda_last_updated": manifest.get("openfda_last_updated"),
        "site_url": site,
        "dashboard_url": f"{site}/",
        "archive_path": f"/newsletter/{slug}",
        "disclaimer": manifest.get("disclaimer") or DISCLAIMER,
        "fda_caveat": FDA_CAVEAT,
        "research_line": RESEARCH_LINE,
        "fda_attribution": FDA_ATTRIBUTION,
        "fda_independence": FDA_INDEPENDENCE,
        "ncbi_disclaimer_url": NCBI_DISCLAIMER_URL,
        "postal_address": postal_address(),
        "unsubscribe_page": f"{site}/unsubscribe",
        "sections": [
            {
                "id": "alerts",
                "heading": "Latest FDA safety notices" if inaugural else "New FDA safety alerts",
                "empty": empty,
                "items": alerts[:ALERT_CAP],
            },
            {
                "id": "recalls",
                "heading": "Recalls in the extract" if inaugural else "New recalls",
                "empty": empty,
                "items": recalls[:RECALL_CAP],
            },
            {
                "id": "signals",
                "heading": "Strongest prespecified safety signals" if inaugural else "New or strengthened drug-safety signals",
                "empty": empty,
                "items": signals[:SIGNAL_CAP],
            },
            {
                "id": "trials",
                "heading": "Recent trials" if inaugural else "Notable new trials",
                "empty": empty,
                "items": trials[:TRIAL_CAP],
            },
            {
                "id": "papers",
                "heading": "Recent PubMed papers" if inaugural else "Top new PubMed papers",
                "empty": empty,
                "note": f"Titles and links only. Abstracts are not shown. NCBI disclaimer: {NCBI_DISCLAIMER_URL}",
                "items": papers[:PAPER_CAP],
            },
        ],
    }


def alert_key(item: dict) -> str:
    return str(item.get("link") or item.get("title") or "")


def recall_key(item: dict) -> str:
    return str(item.get("recall_number") or item.get("product_description") or "")


def _alerts(items: list[dict], previous: dict | None, inaugural: bool) -> list[dict]:
    chosen = items if inaugural else [item for item in items if alert_key(item) not in set(previous.get("alert_keys") or [])]
    tagged = [item for item in chosen if item.get("tags")]
    ordered = tagged or chosen
    rows = []
    for item in ordered:
        title = _clean(item.get("title"))
        if not title:
            continue
        meta_bits = [bit for bit in (_clean(item.get("source")), _clean(item.get("published"))) if bit]
        summary = _clean(item.get("summary"))
        rows.append(
            {
                "title": title,
                "meta": " · ".join(meta_bits),
                "body": summary,
                "href": _http_url(item.get("link")),
                "badge": "",
            }
        )
    return rows


def _recalls(items: list[dict], previous: dict | None, inaugural: bool) -> list[dict]:
    chosen = items if inaugural else [item for item in items if recall_key(item) not in set(previous.get("recall_keys") or [])]
    ordered = sorted(
        chosen,
        key=lambda item: (_class_rank(item.get("classification")), _date_desc(item.get("report_date"))),
    )
    rows = []
    for item in ordered:
        description = _clean(item.get("product_description"))
        if not description:
            continue
        reason = _clean(item.get("reason"))
        firm = _clean(item.get("recalling_firm"))
        classification = _clean(item.get("classification")) or "Unclassified"
        number = _clean(item.get("recall_number"))
        reported = _clean(item.get("report_date"))
        meta = " · ".join(bit for bit in (number, classification, firm) if bit)
        if reported:
            meta = f"{meta} · reported {reported}" if meta else f"reported {reported}"
        rows.append(
            {
                "title": _truncate(description, 280),
                "meta": meta,
                "body": reason,
                "href": "",
                "badge": classification,
            }
        )
    return rows


def _ranked_signal_changes(snapshot: dict, previous: dict | None, inaugural: bool) -> list[tuple]:
    if inaugural:
        checks = [
            _validation_as_signal(check)
            for check in snapshot["validation"].get("checks") or []
            if check.get("evans_signal")
        ]
        checks.sort(key=lambda row: float(row.get("prr") or 0), reverse=True)
        return [(row, "", None) for row in checks]

    previous_high = (previous or {}).get("high_signals") or {}
    changes = []
    for row in snapshot["signals"]:
        if not is_high(row):
            continue
        key = signal_identity(row)
        if key not in previous_high:
            changes.append((row, "new", None))
            continue
        previous_prr = previous_high.get(key)
        current = row.get("prr")
        if (
            previous_prr not in (None, 0)
            and current is not None
            and float(current) >= STRENGTHEN_RATIO * float(previous_prr)
        ):
            changes.append((row, "strengthened", float(previous_prr)))
    changes.sort(key=lambda item: (not item[0].get("evans_signal"), -(float(item[0].get("prr") or 0))))
    return changes


def _signal_item(row: dict, change: str, previous_prr: float | None) -> dict:
    name = _display_name(row)
    reaction = _title_case(row.get("reaction") or "")
    badge = "Evans" if row.get("evans_signal") else "ROR only"
    if change == "new":
        badge = f"New · {badge}"
    elif change == "strengthened":
        badge = f"Strengthened · {badge}"
    prr = row.get("prr")
    ror = row.get("ror")
    meta = f"PRR {_fmt(prr)} (95% CI {_fmt(row.get('prr_ci_low'))}–{_fmt(row.get('prr_ci_high'))})"
    if ror is not None:
        meta += f" · ROR {_fmt(ror)} (95% CI {_fmt(row.get('ror_ci_low'))}–{_fmt(row.get('ror_ci_high'))})"
    return {
        "title": f"{name} · {reaction}",
        "meta": meta,
        "body": _plain_english(row, change, previous_prr),
        "href": "",
        "badge": badge,
    }


def _trials(items: list[dict], previous: dict | None, inaugural: bool) -> list[dict]:
    known = set() if inaugural else set((previous or {}).get("trial_keys") or [])
    chosen = [item for item in items if item.get("nct_id") and (inaugural or item.get("nct_id") not in known)]
    chosen = _unique(chosen, lambda item: item.get("nct_id"))
    chosen.sort(key=lambda item: (_recruiting_rank(item), _date_desc(item.get("start_date"))))
    picked = _diversify(chosen, lambda item: item.get("topic") or "", TRIAL_CAP * 3)
    rows = []
    for item in picked:
        title = _clean(item.get("title"))
        if not title:
            continue
        topic = TOPIC_LABELS.get(item.get("topic") or "", "")
        meta = " · ".join(
            bit
            for bit in (
                _clean(item.get("nct_id")),
                _clean(item.get("phase")),
                _clean(item.get("status")).replace("_", " ").title(),
                topic,
                f"start {_clean(item.get('start_date'))}" if item.get("start_date") else "",
            )
            if bit
        )
        rows.append(
            {
                "title": title,
                "meta": meta,
                "body": _clean(item.get("conditions")),
                "href": _http_url(item.get("link")),
                "badge": "",
            }
        )
    return rows


def _papers(items: list[dict], previous: dict | None, inaugural: bool) -> list[dict]:
    known = set() if inaugural else set((previous or {}).get("paper_keys") or [])
    chosen = _unique(
        [item for item in items if item.get("pmid") and (inaugural or item.get("pmid") not in known)],
        lambda item: item.get("pmid"),
    )
    picked = _diversify(chosen, lambda item: item.get("topic") or "", PAPER_CAP * 3)
    rows = []
    for item in picked:
        title = _clean(item.get("title"))
        if not title:
            continue
        rows.append(
            {
                "title": title,
                "meta": "",
                "body": "",
                "href": _http_url(item.get("link")),
                "badge": "",
            }
        )
    return rows


def _headline(ranked: list[tuple], generated_at: str, inaugural: bool, daily: bool) -> str:
    source = None
    for row, _change, _previous in ranked:
        if row.get("evans_signal") and row.get("prr") is not None:
            source = row
            break
    if source is None and ranked and ranked[0][0].get("prr") is not None:
        source = ranked[0][0]
    if source is not None:
        return _reporting_headline(source)
    long_date = _long_date(generated_at)
    if daily:
        return f"Daily test edition, {long_date}: no new or strengthened high signals"
    if inaugural:
        return f"Inflammation Signal Monitor briefing, {long_date}"
    return f"Week of {long_date}: no new or strengthened high signals"


def _reporting_headline(row: dict) -> str:
    name = _display_name(row)
    reaction = _title_case(row.get("reaction") or "").lower()
    times = f"{float(row['prr']):.1f}"
    return f"{name}: {reaction} reported more often than expected (PRR {times})"


def _intro(snapshot: dict, previous: dict | None, inaugural: bool, generated_at: str, daily: bool) -> str:
    manifest = snapshot["manifest"]
    long_date = _long_date(generated_at)
    extract = manifest.get("openfda_last_updated") or "an undated extract"
    if daily and inaugural:
        lead = (
            f"This daily test edition is the first briefing, from the snapshot of {long_date}. "
            "There is no earlier snapshot to compare, so the lists below are the latest notices "
            "and the strongest prespecified signals in the current extract, not day-over-day changes. "
            "The edition is still produced when little is new."
        )
    elif daily:
        earlier = _long_date(str((previous or {}).get("snapshot_generated_at") or ""))
        lead = (
            f"This daily test edition compares the {long_date} snapshot with the one from {earlier}. "
            "It is produced even when little is new. "
            "It includes FDA notices, recalls, trials, and papers that were not in that extract, "
            "and drug-safety signals that are newly high or whose PRR is at least 25% higher."
        )
    elif inaugural:
        lead = (
            f"This is the first briefing, from the snapshot of {long_date}. "
            "There is no earlier snapshot to compare, so the lists below are the latest notices "
            "and the strongest prespecified signals in the current extract, not week-over-week changes."
        )
    else:
        earlier = _long_date(str((previous or {}).get("snapshot_generated_at") or ""))
        lead = (
            f"This briefing compares the {long_date} snapshot with the one from {earlier}. "
            "It includes FDA notices, recalls, trials, and papers that were not in that extract, "
            "and drug-safety signals that are newly high or whose PRR is at least 25% higher."
        )
    ror_only = [
        _title_case(check.get("reaction") or "")
        for check in snapshot["validation"].get("checks") or []
        if check.get("recovered") and not check.get("evans_signal")
    ]
    caveat = ""
    if ror_only:
        caveat = (
            f" {_join_names(ror_only)} cleared a reporting-odds bound only. "
            "The PRR is below 2, so those comparisons are not Evans signals and they are not the headline."
        )
    return (
        f"{lead} openFDA extract dated {extract}.{caveat} "
        "PRR and ROR describe reporting. A higher ratio is a disproportionality signal. It is not an incidence rate."
    )


def _plain_english(row: dict, change: str, previous_prr: float | None) -> str:
    name = _display_name(row)
    reaction = _title_case(row.get("reaction") or "").lower()
    prr = row.get("prr")
    ror = row.get("ror")
    sentences: list[str] = []
    if change == "new":
        sentences.append("This pair was not a high signal in the previous snapshot.")
    elif change == "strengthened" and previous_prr is not None and prr is not None:
        sentences.append(
            f"The PRR rose from {_fmt(previous_prr)} to {_fmt(prr)}, at least 25% higher than the previous snapshot."
        )
    if prr is not None:
        sentences.append(
            f"{reaction[:1].upper() + reaction[1:]} was reported more often than expected with {name} than with "
            f"{_compare_sentence(row)} (PRR {_fmt(prr)}, 95% CI {_fmt(row.get('prr_ci_low'))}–{_fmt(row.get('prr_ci_high'))}). "
            "This is a disproportionality signal."
        )
    if ror is not None:
        sentences.append(
            f"The reporting odds ratio is {_fmt(ror)} (95% CI {_fmt(row.get('ror_ci_low'))}–{_fmt(row.get('ror_ci_high'))})."
        )
    if row.get("evans_signal"):
        sentences.append("This meets the Evans screen: at least 3 reports, a PRR of at least 2, and a chi-square of at least 4.")
    elif row.get("ror_signal"):
        sentences.append(
            "The reporting odds ratio has a 95% lower bound above 1, with at least 3 reports. "
            "The PRR is below 2, so this is not an Evans signal."
        )
    sentences.append("The ratio is not an incidence rate.")
    return " ".join(sentences)


def _validation_as_signal(check: dict) -> dict:
    key = check.get("key")
    return {
        "scope": "class",
        "drug": None,
        "drug_label": None,
        "drug_class": key,
        "drug_class_label": CLASS_SHORT.get(key, key),
        "reaction": check.get("reaction"),
        "analysis": check.get("analysis"),
        "comparator": check.get("comparator"),
        "comparator_label": COMPARATOR_SENTENCE.get(check.get("comparator") or "", CLASS_SHORT.get(check.get("comparator") or "", check.get("comparator"))),
        "prr": check.get("prr"),
        "prr_ci_low": check.get("prr_ci_low"),
        "prr_ci_high": check.get("prr_ci_high"),
        "ror": check.get("ror"),
        "ror_ci_low": check.get("ror_ci_low"),
        "ror_ci_high": check.get("ror_ci_high"),
        "chi2": check.get("chi2"),
        "a": check.get("a"),
        "evans_signal": check.get("evans_signal"),
        "ror_signal": check.get("ror_signal"),
        "preset": True,
        "admin_term": False,
        "indication_term": False,
    }


def _display_name(row: dict) -> str:
    if row.get("scope") == "drug" and row.get("drug_label"):
        return str(row["drug_label"])
    key = row.get("drug_class") or row.get("key")
    if key in CLASS_SHORT:
        return CLASS_SHORT[key]
    return str(row.get("drug_class_label") or row.get("drug_label") or "This product")


def _compare_phrase(row: dict) -> str:
    comparator = row.get("comparator") or ""
    if comparator in COMPARATOR_PHRASE:
        return COMPARATOR_PHRASE[comparator]
    if comparator in CLASS_SHORT:
        return CLASS_SHORT[comparator]
    return str(row.get("comparator_label") or "the comparator")


def _compare_sentence(row: dict) -> str:
    comparator = row.get("comparator") or ""
    if comparator in COMPARATOR_SENTENCE:
        return COMPARATOR_SENTENCE[comparator]
    if comparator in CLASS_SHORT:
        return CLASS_SHORT[comparator]
    return str(row.get("comparator_label") or "the comparator")


def _unique(items: list[dict], key_of) -> list[dict]:
    seen: set[str] = set()
    unique: list[dict] = []
    for item in items:
        key = str(key_of(item) or "")
        if not key or key in seen:
            continue
        seen.add(key)
        unique.append(item)
    return unique


def _diversify(items: list[dict], topic_of, limit: int) -> list[dict]:
    picked: list[dict] = []
    seen: set[str] = set()
    rest: list[dict] = []
    for item in items:
        topic = str(topic_of(item) or "")
        if topic not in seen:
            seen.add(topic)
            picked.append(item)
        else:
            rest.append(item)
        if len(picked) >= limit:
            return picked[:limit]
    for item in rest:
        picked.append(item)
        if len(picked) >= limit:
            break
    return picked


def _class_rank(value: str | None) -> int:
    text = " ".join((value or "").lower().split())
    if text in {"class i", "i"}:
        return 0
    if text in {"class ii", "ii"}:
        return 1
    if text in {"class iii", "iii"}:
        return 2
    return 3


def _date_desc(value: str | None) -> str:
    digits = "".join(ch for ch in str(value or "") if ch.isdigit())
    # Invert lexicographic order so newer YYYYMMDD sorts first when the tuple is ascending.
    return "".join(str(9 - int(ch)) for ch in digits) if digits else "9" * 8


def _recruiting_rank(item: dict) -> int:
    status = str(item.get("status") or "")
    if status == "RECRUITING":
        return 0
    if "RECRUITING" in status:
        return 1
    return 2


def _slug(iso: str) -> str:
    try:
        return _parse(iso).strftime("%Y-%m-%d")
    except ValueError:
        return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def _long_date(iso: str) -> str:
    try:
        stamp = _parse(iso)
    except ValueError:
        return iso or "an undated snapshot"
    return f"{stamp.day} {stamp.strftime('%B %Y')}"


def _parse(iso: str) -> datetime:
    return datetime.fromisoformat(iso.replace("Z", "+00:00"))


def _fmt(value) -> str:
    if value is None:
        return "—"
    return f"{float(value):.2f}"


def _title_case(value: str) -> str:
    return " ".join(part[:1].upper() + part[1:].lower() if part else "" for part in str(value).split(" "))


def _clean(value) -> str:
    if value is None:
        return ""
    return " ".join(unescape(str(value)).split())


def _truncate(value: str, limit: int) -> str:
    if len(value) <= limit:
        return value
    return value[: limit - 1].rstrip() + "…"


def _http_url(value) -> str:
    text = _clean(value)
    if text.startswith("https://") or text.startswith("http://"):
        return text
    return ""


def _join_names(names: list[str]) -> str:
    unique = list(dict.fromkeys(name for name in names if name))
    if not unique:
        return ""
    if len(unique) == 1:
        return unique[0]
    return ", ".join(unique[:-1]) + f" and {unique[-1]}"
