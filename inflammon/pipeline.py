"""Weekly refresh: pull public sources, score signals, write the snapshot.

The job is safe to re-run. HTTP responses are cached unless ``force`` is set.
The first successful run establishes a high-signal baseline and does not mark
every current signal as new. Later weekly runs report keys that were absent
from that baseline.
"""

from __future__ import annotations

import asyncio
import json
import logging
from pathlib import Path
from typing import Any

from inflammon.compute import build_signal_rows, build_validation, spike_series
from inflammon.db import connect, insert_rows, reset
from inflammon.export import manifest, now_iso, write_snapshot
from inflammon.http_client import HttpCache
from inflammon.ingest.cdc_cdi import fetch_cdc
from inflammon.ingest.clinicaltrials import fetch_trials
from inflammon.ingest.fda_rss import fetch_alerts
from inflammon.ingest.openfda_enforcement import fetch_recalls
from inflammon.ingest.openfda_events import fetch_faers
from inflammon.ingest.pubmed import fetch_publications
from inflammon.taxonomy import CLASS_BY_KEY

log = logging.getLogger(__name__)

STATE_PATH = Path("data/state/seen_signal_keys.json")
HIGH_SIGNAL_RULE = "evans_signal or ror_signal, preset reaction, not an admin or indication term"


async def _pull(cache: HttpCache) -> dict[str, Any]:
    faers, recalls, alerts, trials, publications, cdc = await asyncio.gather(
        fetch_faers(cache),
        fetch_recalls(cache),
        fetch_alerts(cache),
        fetch_trials(cache),
        fetch_publications(cache),
        fetch_cdc(cache),
    )
    return {
        "faers": faers,
        "recalls": recalls,
        "alerts": alerts,
        "trials": trials,
        "publications": publications,
        "cdc": cdc,
    }


def _store(pulled: dict[str, Any]) -> None:
    connection = connect()
    reset(connection)
    faers = pulled["faers"]
    if faers.get("database_n") is not None:
        insert_rows(
            connection,
            "faers_context",
            ("database_n", "last_updated"),
            [(faers["database_n"], faers.get("last_updated"))],
        )
    insert_rows(
        connection,
        "faers_exposure",
        ("scope", "key", "label", "drug_class", "report_count"),
        [
            (row["scope"], row["key"], row["label"], row["drug_class"], row["report_count"])
            for row in faers.get("exposures") or []
        ],
    )
    insert_rows(
        connection,
        "faers_pairs",
        ("scope", "key", "drug_class", "reaction", "pair_count", "preset"),
        [
            (row["scope"], row["key"], row["drug_class"], row["reaction"], row["pair_count"], row["preset"])
            for row in faers.get("pairs") or []
        ],
    )
    insert_rows(
        connection,
        "faers_reaction_totals",
        ("reaction", "report_count"),
        list((faers.get("reaction_totals") or {}).items()),
    )
    insert_rows(
        connection,
        "faers_quarterly",
        ("drug_class", "year", "quarter", "report_count"),
        [
            (row["drug_class"], row["year"], row["quarter"], row["report_count"])
            for row in faers.get("quarterly") or []
        ],
    )
    insert_rows(
        connection,
        "recalls",
        (
            "recall_number",
            "product_description",
            "reason",
            "status",
            "classification",
            "recalling_firm",
            "report_date",
            "matched_term",
            "drug_class",
        ),
        [
            (
                row["recall_number"],
                row["product_description"],
                row["reason"],
                row["status"],
                row["classification"],
                row["recalling_firm"],
                row["report_date"],
                row["matched_term"],
                row["drug_class"],
            )
            for row in pulled["recalls"].get("rows") or []
        ],
    )
    insert_rows(
        connection,
        "alerts",
        ("source", "title", "link", "published", "summary", "tags"),
        [
            (row["source"], row["title"], row["link"], row["published"], row["summary"], ",".join(row["tags"]))
            for row in pulled["alerts"].get("rows") or []
        ],
    )
    insert_rows(
        connection,
        "publication_counts",
        ("topic", "label", "topic_type", "grain", "period", "period_start", "count", "partial"),
        [
            (
                row["topic"],
                row["label"],
                row["topic_type"],
                row["grain"],
                row["period"],
                row["period_start"],
                row["count"],
                row["partial"],
            )
            for row in pulled["publications"].get("counts") or []
        ],
    )
    insert_rows(
        connection,
        "publication_recent",
        ("pmid", "title", "journal", "published", "topic", "link"),
        [
            (row["pmid"], row["title"], row["journal"], row["published"], row["topic"], row["link"])
            for row in pulled["publications"].get("recent") or []
        ],
    )
    insert_rows(
        connection,
        "trial_counts",
        ("topic", "label", "grain", "period", "period_start", "count", "partial"),
        [
            (row["topic"], row["label"], row["grain"], row["period"], row["period_start"], row["count"], row["partial"])
            for row in pulled["trials"].get("counts") or []
        ],
    )
    insert_rows(
        connection,
        "trial_recent",
        ("nct_id", "title", "status", "phase", "conditions", "start_date", "last_update", "topic"),
        [
            (
                row["nct_id"],
                row["title"],
                row["status"],
                row["phase"],
                row["conditions"],
                row["start_date"],
                row["last_update"],
                row["topic"],
            )
            for row in pulled["trials"].get("recent") or []
        ],
    )
    insert_rows(
        connection,
        "cdc_arthritis",
        ("year", "question", "data_value", "unit", "stratification", "low_ci", "high_ci"),
        [
            (
                row["year"],
                row["question"],
                row["data_value"],
                row["unit"],
                row["stratification"],
                row["low_ci"],
                row["high_ci"],
            )
            for row in pulled["cdc"].get("rows") or []
        ],
    )
    connection.close()


def _signal_key(row: dict[str, Any]) -> str:
    identity = row["drug"] if row["scope"] == "drug" else row["drug_class"]
    return "|".join([row["analysis"], row["scope"], identity or "", row["reaction"], row["comparator"]])


def _high(row: dict[str, Any]) -> bool:
    if row["admin_term"] or row["indication_term"] or not row["preset"]:
        return False
    return bool(row["evans_signal"] or row["ror_signal"])


def _diff_high_signals(rows: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]], bool]:
    high = [row for row in rows if _high(row)]
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    if not STATE_PATH.exists():
        STATE_PATH.write_text(json.dumps({"keys": sorted({_signal_key(row) for row in high})}, indent=2) + "\n")
        return high, [], True
    previous = set(json.loads(STATE_PATH.read_text()).get("keys") or [])
    fresh = [row for row in high if _signal_key(row) not in previous]
    STATE_PATH.write_text(json.dumps({"keys": sorted(previous | {_signal_key(row) for row in high})}, indent=2) + "\n")
    return high, fresh, False


def _alerts_weekly(alerts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Bucket notices that carry a parseable RFC-822 or ISO date."""
    from datetime import datetime
    from email.utils import parsedate_to_datetime

    counts: dict[str, dict[str, Any]] = {}
    for alert in alerts:
        published = alert.get("published") or ""
        moment = None
        if published:
            try:
                moment = parsedate_to_datetime(published)
            except (TypeError, ValueError, IndexError):
                moment = None
            if moment is None:
                try:
                    moment = datetime.fromisoformat(published.replace("Z", "+00:00"))
                except ValueError:
                    moment = None
        if moment is None:
            continue
        start = moment.date()
        start = start.fromordinal(start.toordinal() - start.weekday())
        key = start.isoformat()
        bucket = counts.setdefault(
            key,
            {"topic": "fda_notices", "label": "FDA notices", "grain": "week", "period_start": key, "count": 0, "partial": False},
        )
        bucket["count"] += 1
    rows = sorted(counts.values(), key=lambda row: row["period_start"])
    for row in rows:
        year, week, _ = __import__("datetime").date.fromisoformat(row["period_start"]).isocalendar()
        row["period"] = f"{year}-W{week:02d}"
    return rows


def build_payloads(pulled: dict[str, Any], generated_at: str | None = None) -> dict[str, Any]:
    generated_at = generated_at or now_iso()
    faers = pulled["faers"]
    signals: list[dict[str, Any]] = []
    validation = {"recovered": 0, "tested": 0, "checks": [], "rule": ""}
    if faers.get("database_n"):
        signals = build_signal_rows(
            database_n=int(faers["database_n"]),
            exposures=faers.get("exposures") or [],
            pairs=faers.get("pairs") or [],
            reaction_totals=faers.get("reaction_totals") or {},
        )
        validation = build_validation(signals)
    high, fresh, baseline = _diff_high_signals(signals) if signals else ([], [], True)

    publication_counts = pulled["publications"].get("counts") or []
    trial_counts = pulled["trials"].get("counts") or []
    alert_weeks = _alerts_weekly(pulled["alerts"].get("rows") or [])
    spikes = []
    spikes.extend(spike_series(publication_counts, series="publications"))
    spikes.extend(spike_series(trial_counts, series="trials"))
    spikes.extend(spike_series(alert_weeks, series="alerts"))

    quarterly = []
    for row in faers.get("quarterly") or []:
        drug_class = CLASS_BY_KEY[row["drug_class"]]
        quarterly.append(
            {
                **row,
                "drug_class_label": drug_class.label,
                "period": f"{row['year']}-Q{row['quarter']}",
            }
        )

    sources = [
        {"id": "openfda_faers", "label": "openFDA drug/event", "status": faers.get("status"), "detail": faers.get("detail"), "rows": len(faers.get("pairs") or [])},
        {"id": "openfda_enforcement", "label": "openFDA drug/enforcement", "status": pulled["recalls"].get("status"), "detail": pulled["recalls"].get("detail"), "rows": len(pulled["recalls"].get("rows") or [])},
        {"id": "fda_rss", "label": "FDA MedWatch, Drugs RSS, and Drug Safety Communications", "status": pulled["alerts"].get("status"), "detail": pulled["alerts"].get("detail"), "rows": len(pulled["alerts"].get("rows") or [])},
        {"id": "clinicaltrials", "label": "ClinicalTrials.gov API v2", "status": pulled["trials"].get("status"), "detail": pulled["trials"].get("detail"), "rows": len(trial_counts)},
        {"id": "pubmed", "label": "PubMed E-utilities", "status": pulled["publications"].get("status"), "detail": pulled["publications"].get("detail"), "rows": len(publication_counts)},
        {"id": "cdc_cdi", "label": "CDC Chronic Disease Indicators hksd-2xuw", "status": pulled["cdc"].get("status"), "detail": pulled["cdc"].get("detail"), "rows": len(pulled["cdc"].get("rows") or [])},
    ]
    for source in sources:
        log.info("%s: %s — %s", source["id"], source["status"], source["detail"])

    alerts_out = []
    for row in pulled["alerts"].get("rows") or []:
        alerts_out.append({**row, "tags": list(row.get("tags") or [])})

    recalls_out = []
    for row in pulled["recalls"].get("rows") or []:
        drug_class = CLASS_BY_KEY.get(row["drug_class"])
        recalls_out.append({**row, "drug_class_label": drug_class.label if drug_class else row["drug_class"]})

    payloads = {
        "manifest.json": manifest(
            generated_at=generated_at,
            sources=sources,
            faers=faers,
            validation=validation,
            signal_rows=len(signals),
            high_signals=len(high),
            new_high_signals=len(fresh),
            baseline_run=baseline,
        ),
        "signals.json": {"rows": signals},
        "quarterly.json": {"rows": quarterly},
        "validation.json": validation,
        "alerts.json": {"items": alerts_out},
        "recalls.json": {"items": recalls_out},
        "trends.json": {
            "publications": [row for row in publication_counts if row["topic_type"] == "condition" or row["grain"] == "year"],
            "publications_all": publication_counts,
            "trials": trial_counts,
            "alerts_weekly": alert_weeks,
            "spikes": spikes,
        },
        "recent.json": {
            "publications": pulled["publications"].get("recent") or [],
            "trials": pulled["trials"].get("recent") or [],
        },
        "cdc_arthritis.json": {
            "rows": pulled["cdc"].get("rows") or [],
            "ibd_note": pulled["cdc"].get("ibd_note"),
            "catalog_note": pulled["cdc"].get("catalog_note"),
        },
        "high_signals.json": {"rule": HIGH_SIGNAL_RULE, "baseline_run": baseline, "items": high},
        "high_signals_new.json": {
            "rule": HIGH_SIGNAL_RULE,
            "baseline_run": baseline,
            "items": [] if baseline else fresh,
            "note": (
                "First successful snapshot. No webhook items, so the weekly job does not alert on the entire history."
                if baseline
                else "Signals that were absent from the previous baseline."
            ),
        },
    }
    payloads["run_report.json"] = {
        "generated_at": generated_at,
        "sources": sources,
        "validation": validation,
        "http": {},
    }
    return payloads


def refresh(force: bool = False) -> dict[str, Any]:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    logging.getLogger("httpx").setLevel(logging.WARNING)
    cache = HttpCache(force=force)
    pulled = asyncio.run(_pull(cache))
    _store(pulled)
    payloads = build_payloads(pulled)
    payloads["run_report.json"]["http"] = {
        "network_requests": cache.requests,
        "cache_hits": cache.cache_hits,
        "errors": cache.errors[:30],
    }
    connection = connect()
    insert_rows(
        connection,
        "source_runs",
        ("source", "status", "detail", "rows", "pulled_at"),
        [
            (source["id"], source["status"], source["detail"], source["rows"], payloads["manifest.json"]["generated_at"])
            for source in payloads["manifest.json"]["sources"]
        ],
    )
    connection.close()
    write_snapshot(payloads)
    _write_run_report(payloads)
    return payloads["manifest.json"]


def _write_run_report(payloads: dict[str, Any]) -> None:
    manifest_payload = payloads["manifest.json"]
    validation = payloads["validation.json"]
    lines = [
        "# Ingestion report",
        "",
        f"Generated {manifest_payload['generated_at']}.",
        f"openFDA extract last updated {manifest_payload.get('openfda_last_updated')}.",
        f"FAERS reports in the extract: {manifest_payload.get('faers_report_total')}.",
        "",
        "## Sources",
        "",
    ]
    for source in manifest_payload["sources"]:
        lines.append(f"- **{source['label']}** — {source['status']}. {source['detail']}")
    lines.extend(["", "## Known-signal sanity check", "", validation.get("rule") or "", ""])
    for check in validation.get("checks") or []:
        flag = "recovered" if check.get("recovered") else "not recovered"
        lines.append(
            f"- {check['title']}: {flag}. "
            f"a={check.get('a')}, PRR={check.get('prr')} "
            f"({check.get('prr_ci_low')}–{check.get('prr_ci_high')}), "
            f"ROR={check.get('ror')} ({check.get('ror_ci_low')}–{check.get('ror_ci_high')})."
        )
    lines.extend(
        [
            "",
            f"Recovered {validation.get('recovered')} of {validation.get('tested')} prespecified checks.",
            "",
            "Counts are ingredient mentions in the openFDA FAERS extract. They are not primary-suspect-only counts and they are not incidence.",
            "",
        ]
    )
    text = "\n".join(lines)
    for directory in (Path("data/snapshot"), Path("web/data")):
        directory.mkdir(parents=True, exist_ok=True)
        (directory / "RUN_REPORT.md").write_text(text)
