"""Diff a snapshot against the previous fingerprint and compose one issue."""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from html import unescape
from pathlib import Path

from inflammon.compliance import (
    FDA_ATTRIBUTION,
    FDA_CAVEAT,
    FDA_INDEPENDENCE,
    NCBI_DISCLAIMER_URL,
    RESEARCH_LINE,
    SIGNAL_CAVEAT,
    postal_address,
)
from inflammon.newsletter.cadence import newsletter_cadence
from inflammon.taxonomy import CONDITIONS, DISCLAIMER, DRUG_CLASSES, DRUG_TOPICS, DRUGS

CLASS_SHORT = {item.key: item.short_label for item in DRUG_CLASSES}
TOPIC_LABELS = {item.key: item.label for item in (*CONDITIONS, *DRUG_TOPICS)}

ALERT_CAP = 5
RECALL_CAP = 4
SIGNAL_CAP = 6
TRIAL_CAP = 4
PAPER_CAP = 4
STRENGTHEN_RATIO = 1.25
SUBJECT_LIMIT = 70
HIGHLIGHT_CAP = 5

# Sponsor names are not in the snapshot, so a notable trial is a phase 3 study.
_HIGH_IMPACT_JOURNALS = (
    "annals of the rheumatic diseases",
    "arthritis & rheumatology",
    "arthritis and rheumatology",
    "the lancet",
    "new england journal of medicine",
    "lancet",
    "jama",
    "bmj",
    "nature medicine",
    "gastroenterology",
    "hepatology",
)
_BIOSIMILAR = re.compile(r"-[a-z]{4}\b", re.IGNORECASE)

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

    long_date = _long_date(generated_at)
    if daily:
        kicker = f"Daily test edition · {long_date}"
    elif inaugural:
        kicker = f"Inaugural briefing · {long_date}"
    else:
        kicker = f"Week of {long_date}"
    archive_path = f"/newsletter/{slug}"
    bundles = _news_bundles(
        alerts,
        recalls,
        ranked_signals,
        trials,
        papers,
        site=site,
        archive_path=archive_path,
        inaugural=inaugural,
    )
    fragments = _subject_fragments(bundles)
    if fragments:
        budget = SUBJECT_LIMIT - len("Daily test edition: ") if daily else SUBJECT_LIMIT
        headline = _join_subject(fragments, budget)
    elif daily:
        headline = f"Daily test edition, {long_date}"
    else:
        headline = f"Open Health Signals, {long_date}"
    if daily and fragments:
        subject = f"Daily test edition: {headline}"
    else:
        subject = headline
    highlights = _highlights(bundles)
    sections = [
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
        ]
    sections = [section for section in sections if section["items"]]
    return {
        "product": "Open Health Signals",
        "slug": slug,
        "cadence": resolved,
        "kind": kind,
        "subject": subject,
        "headline": headline,
        "kicker": kicker,
        "intro": "",
        "highlights": highlights,
        "preheader": _preheader(highlights, headline),
        "signal_caveat": SIGNAL_CAVEAT,
        "snapshot_generated_at": generated_at,
        "openfda_last_updated": manifest.get("openfda_last_updated"),
        "site_url": site,
        "dashboard_url": f"{site}/",
        "archive_path": archive_path,
        "disclaimer": manifest.get("disclaimer") or DISCLAIMER,
        "fda_caveat": FDA_CAVEAT,
        "research_line": RESEARCH_LINE,
        "fda_attribution": FDA_ATTRIBUTION,
        "fda_independence": FDA_INDEPENDENCE,
        "ncbi_disclaimer_url": NCBI_DISCLAIMER_URL,
        "postal_address": postal_address(),
        "unsubscribe_page": f"{site}/unsubscribe",
        "sections": sections,
    }


def alert_key(item: dict) -> str:
    return str(item.get("link") or item.get("title") or "")


def recall_key(item: dict) -> str:
    return str(item.get("recall_number") or item.get("product_description") or "")


def _alerts(items: list[dict], previous: dict | None, inaugural: bool) -> list[dict]:
    chosen = items if inaugural else [item for item in items if alert_key(item) not in set(previous.get("alert_keys") or [])]
    chosen = [item for item in chosen if _is_safety_alert(item)]
    ordered = sorted(chosen, key=_notice_sort_key)
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
                "tags": [str(tag) for tag in item.get("tags") or []],
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
                "phase": _clean(item.get("phase")),
                "status": _clean(item.get("status")),
                "topic": _clean(item.get("topic")),
                "conditions": _clean(item.get("conditions")),
                "sponsor": _clean(item.get("sponsor") or item.get("lead_sponsor")),
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
                "meta": _clean(item.get("journal")),
                "body": "",
                "href": _http_url(item.get("link")),
                "badge": "",
            }
        )
    return rows


def _news_bundles(
    alerts: list[dict],
    recalls: list[dict],
    ranked_signals: list[tuple],
    trials: list[dict],
    papers: list[dict],
    *,
    site: str,
    archive_path: str,
    inaugural: bool,
) -> dict[str, list[dict]]:
    signal_rows = []
    for row, change, _previous in ranked_signals:
        if row.get("prr") is None and not row.get("reaction"):
            continue
        signal_rows.append(
            {
                "subject": _signal_fragment(row, change),
                "sentence": _signal_sentence(row, change),
                "href": f"{site}/signals",
            }
        )
    class_i_rows = []
    class_ii_rows = []
    for item in recalls:
        rank = _class_rank(item.get("badge"))
        if rank > 1:
            continue
        name, generic, biosimilar = _recall_names(item.get("title") or "")
        if not name:
            continue
        row = {
            "subject": _recall_fragment(name, biosimilar, "Class II" if rank == 1 else "Class I"),
            "sentence": _recall_sentence(name, generic, biosimilar, item.get("body") or "", "Class II" if rank == 1 else "Class I"),
            "href": f"{site}{archive_path}#recalls",
        }
        if rank == 0:
            class_i_rows.append(row)
        else:
            class_ii_rows.append(row)
    notice_rows = []
    for item in alerts:
        notice_rows.append(
            {
                "subject": _notice_fragment(item, inaugural),
                "sentence": _notice_sentence(item),
                "href": item.get("href") or f"{site}{archive_path}#alerts",
            }
        )
    phase3 = [item for item in trials if _is_phase3(item)]
    trial_rows = []
    for index, item in enumerate(phase3):
        trial_rows.append(
            {
                "subject": _trial_fragment(item),
                "sentence": _trial_sentence(item, index),
                "href": item.get("href") or f"{site}{archive_path}#trials",
                "condition": _condition_abbrev(item),
            }
        )
    paper_rows = []
    for item in papers:
        journal = _journal_of(item)
        if not _is_high_impact(journal):
            continue
        paper_rows.append(
            {
                "subject": _paper_fragment(journal),
                "sentence": _paper_sentence(item, journal),
                "href": item.get("href") or f"{site}{archive_path}#papers",
            }
        )
    return {
        "signals": signal_rows,
        "class_i": class_i_rows,
        "notices": notice_rows,
        "class_ii": class_ii_rows,
        "trials": trial_rows,
        "papers": paper_rows,
    }


def _subject_fragments(bundles: dict) -> list[str]:
    fragments: list[str] = []
    if bundles["signals"]:
        fragments.append(bundles["signals"][0]["subject"])
    if bundles["class_i"]:
        fragments.append(bundles["class_i"][0]["subject"])
    if bundles["notices"]:
        fragments.append(bundles["notices"][0]["subject"])
    if bundles["class_ii"]:
        fragments.append(bundles["class_ii"][0]["subject"])
    if bundles["trials"]:
        fragments.append(_trials_subject(bundles["trials"]))
    if bundles["papers"]:
        fragments.append(bundles["papers"][0]["subject"])
    return fragments


def _highlights(bundles: dict) -> list[dict]:
    picked: list[dict] = []
    for key, cap in (
        ("signals", 1),
        ("class_i", 1),
        ("notices", 2),
        ("class_ii", 1),
        ("trials", 2),
        ("papers", 1),
    ):
        for item in bundles[key][:cap]:
            picked.append(item)
            if len(picked) >= HIGHLIGHT_CAP:
                return [_public_highlight(row) for row in picked]
    return [_public_highlight(row) for row in picked]


def _public_highlight(item: dict) -> dict:
    return {"sentence": item["sentence"], "href": item["href"]}


def _join_subject(fragments: list[str], limit: int) -> str:
    chosen: list[str] = []
    for fragment in fragments:
        piece = " ".join(fragment.split())
        if not piece:
            continue
        candidate = ", ".join([*chosen, piece])
        if len(chosen) < 3 and len(candidate) <= limit:
            chosen.append(piece)
            continue
        if not chosen:
            chosen.append(_fit_fragment(piece, limit))
        break
    return ", ".join(chosen)


def _fit_fragment(text: str, limit: int) -> str:
    if len(text) <= limit:
        return text
    cut = text[:limit].rsplit(" ", 1)[0]
    return cut or text[:limit]


def _preheader(highlights: list[dict], headline: str) -> str:
    lead = " ".join(str(headline or "").split()).rstrip(".")
    if not lead and highlights:
        lead = " ".join(str(highlights[0].get("sentence") or "").split()).rstrip(".")
    if not lead:
        return ""
    sentence = f"This week: {lead}."
    if len(sentence) <= 100:
        return sentence
    return _fit_words(sentence[:-1], 96)


def _signal_fragment(row: dict, change: str) -> str:
    name = _display_name(row)
    reaction = _title_case(row.get("reaction") or "").lower()
    qualifier = {"new": "new ", "strengthened": "stronger "}.get(change, "")
    return f"{name}: {qualifier}{reaction} signal"


def _signal_sentence(row: dict, change: str) -> str:
    name = _display_name(row)
    reaction = _title_case(row.get("reaction") or "")
    prr = row.get("prr")
    detail = f" (PRR {_fmt(prr)})" if prr is not None else ""
    if change == "strengthened":
        return f"The {reaction.lower()} signal with {name} is stronger than in the last snapshot{detail}."
    if change == "new":
        return f"{reaction} is a new high signal with {name}{detail}."
    return f"{reaction} was reported more often than expected with {name}{detail}."


def _recall_fragment(name: str, biosimilar: bool, classification: str) -> str:
    if biosimilar and classification == "Class I":
        text = f"{name} biosimilar recall"
        if len(text) <= 32:
            return text
    short = "Class II" if classification == "Class II" else "Class I"
    text = f"{name} {short} recall"
    if len(text) <= 32:
        return text
    return f"{name} recall"


def _recall_sentence(name: str, generic: str, biosimilar: bool, reason: str, classification: str = "Class I") -> str:
    label = "Class II" if classification == "Class II" else "Class I"
    if biosimilar and generic and generic.lower() != name.lower():
        article = "an" if generic[:1].lower() in "aeiou" else "a"
        lead = f"{name}, {article} {generic.lower()} biosimilar, is under a {label} recall"
    elif biosimilar:
        lead = f"{name}, a biosimilar, is under a {label} recall"
    else:
        lead = f"{name} is under a {label} recall"
    short = _short_reason(reason)
    if short:
        return f"{lead} for {short}."
    return f"{lead}."


def _short_reason(reason: str) -> str:
    text = _clean(reason)
    if not text:
        return ""
    head = text.split(":")[0].strip(" .")
    head = head[:1].lower() + head[1:] if head else ""
    if len(head) > 80:
        head = head[:79].rsplit(" ", 1)[0]
    return head


def _recall_names(description: str) -> tuple[str, str, bool]:
    text = _clean(description)
    lowered = text.lower()
    biosimilar = bool(_BIOSIMILAR.search(lowered)) or "biosimilar" in lowered
    generic = ""
    for drug in DRUGS:
        if re.search(rf"\b{re.escape(drug.generic_name.lower())}\b", lowered) or re.search(
            rf"\b{re.escape(drug.label.lower())}\b", lowered
        ):
            generic = drug.label
            break
    head = text.split(",")[0].split("(")[0].strip()
    first = head.split()[0] if head else ""
    if first.isupper() or first.islower():
        pretty = first[:1].upper() + first[1:].lower()
    else:
        pretty = first
    if pretty.lower() in {"the", "a", "an"}:
        pretty = ""
    return pretty or generic, generic, biosimilar


def _name_in_text(text: str) -> str:
    lowered = _clean(text).lower()
    if not lowered:
        return ""
    for drug in DRUGS:
        for token in drug.brands:
            if re.search(rf"\b{re.escape(token)}\b", lowered):
                return token[:1].upper() + token[1:]
    for drug in DRUGS:
        if re.search(rf"\b{re.escape(drug.label.lower())}\b", lowered) or re.search(
            rf"\b{re.escape(drug.generic_name.lower())}\b", lowered
        ):
            return drug.label
    for key, label in CLASS_SHORT.items():
        if key.replace("_", " ") in lowered or label.lower() in lowered:
            return _singular_class(label)
    return ""


def _name_from_tags(tags: list) -> str:
    for tag in tags:
        label = CLASS_SHORT.get(str(tag))
        if label:
            return _singular_class(label)
    return ""


def _singular_class(label: str) -> str:
    if label.endswith("s") and not label.endswith("ss"):
        return label[:-1]
    return label


def _is_phase3(item: dict) -> bool:
    return "PHASE3" in str(item.get("phase") or "").upper()


def _trial_fragment(item: dict) -> str:
    condition = _condition_abbrev(item)
    if condition:
        return f"phase 3 trial in {condition}"
    return "phase 3 trial"


def _trials_subject(trials: list[dict]) -> str:
    conditions: list[str] = []
    for item in trials:
        label = item.get("condition") or _condition_abbrev(item)
        if label and label not in conditions:
            conditions.append(label)
        if len(conditions) == 2:
            break
    noun = "trial" if len(trials) == 1 else "trials"
    if len(conditions) == 1:
        return f"new phase 3 {noun} in {conditions[0]}"
    if len(conditions) >= 2:
        return f"new phase 3 trials in {conditions[0]} and {conditions[1]}"
    return f"new phase 3 {noun}"


def _trial_sentence(item: dict, index: int = 0) -> str:
    drug = _drug_from_trial(item)
    condition = _condition_phrase(item)
    status = _status_phrase(item)
    kind = _study_kind(item.get("title") or "")
    sponsor = _short_sponsor(item.get("sponsor") or "")
    drug_bit = drug if drug else "a study drug"
    where = f" in {condition}" if condition else ""
    status_bit = status or "posted"
    if sponsor:
        status_bit = f"{status_bit}, {sponsor}"
    if index % 2 == 0:
        sentence = f"Phase 3: {drug_bit} {kind}{where} ({status_bit})"
    else:
        sentence = f"Phase 3 {condition or 'study'} study of {drug_bit} ({status_bit})"
    sentence = " ".join(sentence.split())
    if len(sentence) > 140:
        return _fit_words(sentence, 140)
    return sentence


def _journal_of(item: dict) -> str:
    meta = item.get("meta") or ""
    return _clean(meta)


def _is_high_impact(journal: str) -> bool:
    text = " ".join(journal.lower().split())
    if not text:
        return False
    for name in _HIGH_IMPACT_JOURNALS:
        if text == name or text.startswith(name + " "):
            return True
    return False


def _paper_fragment(journal: str) -> str:
    text = f"{journal} paper"
    if len(text) <= 32:
        return text
    return "New research paper"


def _paper_sentence(item: dict, journal: str) -> str:
    title = _as_sentence(item.get("title") or "")
    if journal:
        return f"{journal}: {title}"
    return title


def _as_sentence(text: str) -> str:
    clean = _clean(text)
    if len(clean) > 180:
        return _fit_words(clean, 180)
    if clean and clean[-1] not in ".!?…":
        clean += "."
    return clean


_PROGRAM_PHRASES = (
    "expedited ind",
    "guidance document",
    "recently issued guidance",
    "public meeting",
    "framework initiative",
    "organization chart",
    "prescribe with confidence",
    "data files",
    "paid facilities",
    "what's new",
    "whats new",
    "listening session",
    "drug safety podcasts",
    "approval notifications",
    "registered outsourcing",
)

_SAFETY_WORDS = (
    "warning",
    "recall",
    "counterfeit",
    "contaminat",
    "adverse",
    "safety communication",
    "safety alert",
    "boxed warning",
    "particulate",
    "sterility",
    "endotoxin",
)

_CONDITION_ABBREV = {
    "ulcerative_colitis": "UC",
    "crohns_disease": "Crohn's",
    "rheumatoid_arthritis": "RA",
    "lupus": "lupus",
    "psoriasis": "psoriasis",
    "psoriatic_arthritis": "PsA",
}


def _is_program_announcement(title: str) -> bool:
    text = _clean(title).lower()
    return any(phrase in text for phrase in _PROGRAM_PHRASES)


def _is_safety_alert(item: dict) -> bool:
    title = _clean(item.get("title"))
    if not title or _is_program_announcement(title):
        return False
    source = _clean(item.get("source")).lower()
    blob = f"{title} {_clean(item.get('summary'))}".lower()
    if "drug safety communication" in source:
        if len(title) < 40 and not any(word in blob for word in ("warning", "recall", "safety", "adverse")):
            return False
        return True
    if any(word in blob for word in _SAFETY_WORDS):
        return True
    if item.get("tags"):
        return True
    return False


def _notice_sort_key(item: dict) -> tuple:
    title = _clean(item.get("title")).lower()
    tagged = 0 if item.get("tags") else 1
    urgent = 0 if any(word in title for word in ("counterfeit", "contaminat", "warning", "recall")) else 1
    return (tagged, urgent)


def _notice_fragment(item: dict, inaugural: bool) -> str:
    title = _clean(item.get("title"))
    lowered = title.lower()
    prefix = "" if inaugural else "new "
    if "counterfeit" in lowered:
        return f"Counterfeit {_counterfeit_target(lowered)} alert"
    if "contaminat" in lowered:
        return f"{prefix}contamination alert".strip()
    name = _name_in_text(title) or _name_from_tags(item.get("tags") or [])
    if name:
        kind = "labeling change" if "label" in lowered else "safety notice"
        return f"{prefix}{name} {kind}".strip()
    if "recall" in lowered:
        return f"{prefix}drug recall".strip()
    return f"{prefix}FDA safety alert".strip()


def _notice_sentence(item: dict) -> str:
    title = _clean(item.get("title"))
    lowered = title.lower()
    if "counterfeit" in lowered:
        return f"FDA warning about counterfeit {_counterfeit_target(lowered)}."
    if "contaminat" in lowered:
        return "FDA warning about a contaminated drug product."
    name = _name_in_text(title) or _name_from_tags(item.get("tags") or [])
    if name and any(word in lowered for word in ("warning", "safety", "label", "recall", "adverse")):
        return f"FDA safety notice on {name}."
    if len(title) <= 140:
        return _as_sentence(title)
    return _fit_words(title, 140)


def _counterfeit_target(lowered: str) -> str:
    match = re.search(r"counterfeit\s+([a-z0-9][a-z0-9 \-]{0,40})", lowered)
    if not match:
        return "drug"
    kept = []
    for word in match.group(1).split():
        if word in {"sold", "found", "alert", "warning", "online", "products", "product"}:
            break
        kept.append(word)
        if len(kept) == 3:
            break
    return " ".join(kept) or "drug"


def _fit_words(text: str, limit: int) -> str:
    clean = " ".join(text.split()).rstrip(" .")
    if len(clean) <= limit:
        return clean
    room = max(limit - 1, 1)
    cut = clean[:room].rsplit(" ", 1)[0].rstrip(" ,;:")
    if not cut:
        cut = clean[:room].rstrip(" ,;:")
    return f"{cut}…"


def _condition_abbrev(item: dict) -> str:
    topic = str(item.get("topic") or "")
    if topic in _CONDITION_ABBREV:
        return _CONDITION_ABBREV[topic]
    blob = f"{item.get('conditions') or ''} {item.get('title') or ''}".lower()
    if "ulcerative colitis" in blob:
        return "UC"
    if "crohn" in blob:
        return "Crohn's"
    if "psoriatic arthritis" in blob:
        return "PsA"
    if "rheumatoid" in blob:
        return "RA"
    if "lupus" in blob:
        return "lupus"
    if "psoriasis" in blob:
        return "psoriasis"
    return ""


def _condition_phrase(item: dict) -> str:
    topic = str(item.get("topic") or "")
    phrases = {
        "ulcerative_colitis": "ulcerative colitis",
        "crohns_disease": "Crohn's disease",
        "rheumatoid_arthritis": "rheumatoid arthritis",
        "lupus": "lupus",
        "psoriasis": "psoriasis",
        "psoriatic_arthritis": "psoriatic arthritis",
    }
    if topic in phrases:
        return phrases[topic]
    label = _condition_abbrev(item)
    return {
        "UC": "ulcerative colitis",
        "Crohn's": "Crohn's disease",
        "RA": "rheumatoid arthritis",
        "PsA": "psoriatic arthritis",
    }.get(label, label)


def _drug_from_trial(item: dict) -> str:
    title = _clean(item.get("title"))
    named = _name_in_text(title)
    if named and named.lower() not in {label.lower() for label in CLASS_SHORT.values()} and not named.endswith("inhibitor"):
        return _display_drug(named)
    match = re.search(r"\b(?:of|evaluat(?:e|ing))\s+([A-Za-z][A-Za-z0-9-]{2,})", title, re.IGNORECASE)
    if match:
        return _display_drug(match.group(1))
    return ""


def _display_drug(name: str) -> str:
    if name.isalpha() and name[:1].isupper() and name[1:].islower():
        return name.lower()
    if name.isalpha() and name.isupper():
        return name[:1] + name[1:].lower()
    return name


def _study_kind(title: str) -> str:
    lowered = title.lower()
    if "maintenance" in lowered:
        return "maintenance study"
    if "extension" in lowered or "long-term" in lowered or "long term" in lowered:
        return "extension study"
    if "safety" in lowered:
        return "safety study"
    return "study"


def _status_phrase(item: dict) -> str:
    status = str(item.get("status") or "").upper()
    if status == "RECRUITING":
        return "recruiting"
    if status == "NOT_YET_RECRUITING":
        return "not yet recruiting"
    if status == "ACTIVE_NOT_RECRUITING":
        return "active, not recruiting"
    if status == "COMPLETED":
        return "completed"
    return status.replace("_", " ").lower()


def _short_sponsor(sponsor: str) -> str:
    text = _clean(sponsor)
    if not text or len(text) > 18 or "," in text:
        return ""
    return text


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
