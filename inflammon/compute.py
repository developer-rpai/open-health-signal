"""Turn stored FAERS counts into PRR/ROR rows and weekly spike flags."""

from __future__ import annotations

from typing import Any

from inflammon.signals.disproportionality import (
    active_comparator_table,
    database_table,
    disproportionality,
)
from inflammon.signals.trends import detect_latest_spike, trailing_spikes
from inflammon.taxonomy import (
    CLASS_BY_KEY,
    DRUG_BY_KEY,
    VALIDATION_CHECKS,
    is_admin_term,
    is_indication_term,
)


def exposure_index(exposures: list[dict[str, Any]]) -> dict[tuple[str, str], dict[str, Any]]:
    return {(row["scope"], row["key"]): row for row in exposures}


def pair_index(pairs: list[dict[str, Any]]) -> dict[tuple[str, str, str], dict[str, Any]]:
    return {(row["scope"], row["key"], row["reaction"]): row for row in pairs}


def build_signal_rows(
    *,
    database_n: int,
    exposures: list[dict[str, Any]],
    pairs: list[dict[str, Any]],
    reaction_totals: dict[str, int],
) -> list[dict[str, Any]]:
    exposures_by_key = exposure_index(exposures)
    rows: list[dict[str, Any]] = []
    for pair in pairs:
        exposure = exposures_by_key.get((pair["scope"], pair["key"]))
        reaction_n = reaction_totals.get(pair["reaction"])
        if exposure is None or reaction_n is None:
            continue
        table = database_table(exposure["report_count"], pair["pair_count"], reaction_n, database_n)
        if min(table) < 0:
            continue
        stats = disproportionality(*table)
        rows.append(
            _row(
                pair=pair,
                exposure=exposure,
                stats=stats.as_dict(),
                analysis="database",
                comparator="all_faers",
                comparator_label="All other FAERS reports",
            )
        )
    rows.extend(_active_comparator_rows(exposures_by_key, pair_index(pairs)))
    rows.sort(
        key=lambda row: (
            -(row["prr"] or 0),
            row["reaction"],
            row["scope"],
            row["drug"] or row["drug_class"],
        )
    )
    return rows


def _active_comparator_rows(
    exposures_by_key: dict[tuple[str, str], dict[str, Any]],
    pairs_by_key: dict[tuple[str, str, str], dict[str, Any]],
) -> list[dict[str, Any]]:
    """JAK inhibitor class versus TNF inhibitor class, for every shared reaction."""
    jak = exposures_by_key.get(("class", "jak_inhibitor"))
    tnf = exposures_by_key.get(("class", "tnf_inhibitor"))
    if jak is None or tnf is None:
        return []
    reactions = {
        key[2]
        for key in pairs_by_key
        if key[0] == "class" and key[1] in {"jak_inhibitor", "tnf_inhibitor"}
    }
    rows = []
    for reaction in sorted(reactions):
        jak_pair = pairs_by_key.get(("class", "jak_inhibitor", reaction))
        tnf_pair = pairs_by_key.get(("class", "tnf_inhibitor", reaction))
        if jak_pair is None or tnf_pair is None:
            continue
        table = active_comparator_table(
            jak["report_count"],
            jak_pair["pair_count"],
            tnf["report_count"],
            tnf_pair["pair_count"],
        )
        if min(table) < 0:
            continue
        stats = disproportionality(*table)
        preset = bool(jak_pair["preset"] or tnf_pair["preset"])
        rows.append(
            _row(
                pair={**jak_pair, "preset": preset},
                exposure=jak,
                stats=stats.as_dict(),
                analysis="active_comparator",
                comparator="tnf_inhibitor",
                comparator_label="TNF inhibitors",
            )
        )
    return rows


def _row(
    *,
    pair: dict[str, Any],
    exposure: dict[str, Any],
    stats: dict[str, Any],
    analysis: str,
    comparator: str,
    comparator_label: str,
) -> dict[str, Any]:
    drug = DRUG_BY_KEY.get(pair["key"]) if pair["scope"] == "drug" else None
    drug_class = CLASS_BY_KEY[pair["drug_class"]]
    reaction = pair["reaction"]
    return {
        "scope": pair["scope"],
        "drug": drug.key if drug else None,
        "drug_label": drug.label if drug else None,
        "drug_class": drug_class.key,
        "drug_class_label": drug_class.label,
        "reaction": reaction,
        "analysis": analysis,
        "comparator": comparator,
        "comparator_label": comparator_label,
        "exposure_n": exposure["report_count"],
        "preset": bool(pair["preset"]),
        "admin_term": is_admin_term(reaction),
        "indication_term": is_indication_term(reaction),
        **stats,
    }


def build_validation(signals: list[dict[str, Any]]) -> dict[str, Any]:
    by_key = {
        (
            row["analysis"],
            row["scope"],
            row["drug"] if row["scope"] == "drug" else row["drug_class"],
            row["reaction"],
            row["comparator"],
        ): row
        for row in signals
    }
    checks = []
    for spec in VALIDATION_CHECKS:
        row = by_key.get((spec["analysis"], "class", spec["key"], spec["reaction"], spec["comparator"]))
        if row is None:
            checks.append(
                {
                    **spec,
                    "recovered": False,
                    "reason": "missing_counts",
                    "prr": None,
                    "prr_ci_low": None,
                    "prr_ci_high": None,
                    "ror": None,
                    "ror_ci_low": None,
                    "ror_ci_high": None,
                    "chi2": None,
                    "a": None,
                    "evans_signal": False,
                    "ror_signal": False,
                }
            )
            continue
        recovered = bool(row["ror_signal"] or row["evans_signal"])
        sensitivity = None
        if spec["analysis"] == "active_comparator":
            sensitivity = by_key.get(("database", "class", spec["key"], spec["reaction"], "all_faers"))
        checks.append(
            {
                **spec,
                "recovered": recovered,
                "reason": "signal_recovered" if recovered else "below_signal_threshold",
                "database_prr": None if sensitivity is None else sensitivity["prr"],
                "database_ror_ci_low": None if sensitivity is None else sensitivity["ror_ci_low"],
                "database_ror_signal": False if sensitivity is None else sensitivity["ror_signal"],
                "database_evans_signal": False if sensitivity is None else sensitivity["evans_signal"],
                "prr": row["prr"],
                "prr_ci_low": row["prr_ci_low"],
                "prr_ci_high": row["prr_ci_high"],
                "ror": row["ror"],
                "ror_ci_low": row["ror_ci_low"],
                "ror_ci_high": row["ror_ci_high"],
                "chi2": row["chi2"],
                "a": row["a"],
                "b": row["b"],
                "c": row["c"],
                "d": row["d"],
                "exposure_n": row["exposure_n"],
                "evans_signal": row["evans_signal"],
                "ror_signal": row["ror_signal"],
                "correction": row["correction"],
            }
        )
    recovered_n = sum(1 for check in checks if check["recovered"])
    return {
        "rule": (
            "A known signal is recovered when the prespecified 2×2 table has "
            "at least 3 reports in cell a and either an Evans signal "
            "(PRR ≥ 2 and χ² ≥ 4) or a ROR whose 95% lower bound is above 1. "
            "JAK thrombosis and MACE are compared with TNF inhibitors. "
            "TNF–tuberculosis and NSAID–gastrointestinal bleeding are compared "
            "with the rest of the openFDA FAERS extract."
        ),
        "recovered": recovered_n,
        "tested": len(checks),
        "checks": checks,
    }


def spike_series(
    counts: list[dict[str, Any]],
    *,
    series: str,
    topic_field: str = "topic",
) -> list[dict[str, Any]]:
    """Run the trailing weekly detector on each topic's week grain."""
    grouped: dict[str, list[dict[str, Any]]] = {}
    for row in counts:
        if row.get("grain") != "week":
            continue
        grouped.setdefault(row[topic_field], []).append(row)
    spikes = []
    for topic, rows in grouped.items():
        rows.sort(key=lambda item: item["period_start"])
        values = [float(item["count"]) for item in rows]
        results = trailing_spikes(values)
        latest = detect_latest_spike(values)
        for item, result in zip(rows, results):
            if not result.is_spike:
                continue
            spikes.append(
                {
                    "series": series,
                    "topic": topic,
                    "label": item.get("label") or topic,
                    "period": item["period"],
                    "period_start": item["period_start"],
                    "count": item["count"],
                    "baseline_mean": result.baseline_mean,
                    "baseline_sd": result.baseline_sd,
                    "z": result.z,
                    "ratio": result.ratio,
                    "is_spike": True,
                }
            )
        if rows:
            last = rows[-1]
            spikes.append(
                {
                    "series": series,
                    "topic": topic,
                    "label": last.get("label") or topic,
                    "period": last["period"],
                    "period_start": last["period_start"],
                    "count": last["count"],
                    "baseline_mean": latest.baseline_mean,
                    "baseline_sd": latest.baseline_sd,
                    "z": latest.z,
                    "ratio": latest.ratio,
                    "is_spike": latest.is_spike,
                    "latest": True,
                    "reason": latest.reason,
                }
            )
    return spikes
