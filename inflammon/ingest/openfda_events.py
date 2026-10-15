"""openFDA drug/event counts for the inflammation drug list.

Queries use ``generic_name.exact``. openFDA cannot restrict
``drugcharacterization`` to the same drug element as the ingredient, so
these are ingredient-mention counts, not primary-suspect counts. That
choice is conservative for disproportionality: concomitant mentions dilute
a signal toward the null. The limitation is stated on the methods page.

Class totals are a single OR query, so a report that lists two drugs in
the class is counted once.
"""

from __future__ import annotations

import logging
from datetime import date
from typing import Any

import httpx

from inflammon.http_client import HttpCache, RateLimiter, openfda_last_updated, openfda_total, shared_limiter
from inflammon.taxonomy import (
    DRUG_CLASSES,
    SAFETY_REACTIONS,
    Drug,
    class_search_clause,
    drugs_in_class,
    is_admin_term,
    is_indication_term,
    reaction_clause,
    spotlight_drugs,
)

log = logging.getLogger(__name__)

EVENT_URL = "https://api.fda.gov/drug/event.json"
TOP_REACTION_LIMIT = 20
QUARTER_START = (2024, 1)
MAX_EXTRA_REACTIONS = 30
# OpenFDA's public extract is refreshed on its own cadence. The pipeline
# marks a quarter partial when the extract's last_updated falls inside it.


def _quarters(last_updated: str | None) -> list[dict[str, Any]]:
    end_year = 2026
    end_quarter = 3
    if last_updated and len(last_updated) >= 7:
        end_year = int(last_updated[0:4])
        month = int(last_updated[5:7])
        end_quarter = (month - 1) // 3 + 1
    year, quarter = QUARTER_START
    rows = []
    while (year, quarter) <= (end_year, end_quarter):
        start_month = (quarter - 1) * 3 + 1
        end_month = start_month + 2
        end_day = 30 if end_month in {4, 6, 9, 11} else 31
        if end_month == 2:
            end_day = 29 if year % 4 == 0 else 28
        start = date(year, start_month, 1)
        end = date(year, end_month, end_day)
        partial = False
        if last_updated:
            updated = date.fromisoformat(last_updated[:10])
            partial = updated < end
        rows.append(
            {
                "year": year,
                "quarter": quarter,
                "start": start.strftime("%Y%m%d"),
                "end": end.strftime("%Y%m%d"),
                "partial": partial and (year, quarter) == (end_year, end_quarter),
            }
        )
        quarter += 1
        if quarter == 5:
            quarter = 1
            year += 1
    return rows


async def _total(cache: HttpCache, client: httpx.AsyncClient, limiter: RateLimiter, search: str | None) -> int | None:
    params: dict[str, Any] = {"limit": 1}
    if search:
        params["search"] = search
    status, body = await cache.get_json(client, EVENT_URL, params, limiter=limiter)
    if search is None:
        updated = openfda_last_updated(body)
        if updated:
            _total.last_updated = updated  # type: ignore[attr-defined]
    return openfda_total(status, body)


_total.last_updated = None  # type: ignore[attr-defined]


async def _top_reactions(
    cache: HttpCache,
    client: httpx.AsyncClient,
    limiter: RateLimiter,
    search: str,
) -> list[tuple[str, int]]:
    status, body = await cache.get_json(
        client,
        EVENT_URL,
        {"search": search, "count": "patient.reaction.reactionmeddrapt.exact", "limit": TOP_REACTION_LIMIT},
        limiter=limiter,
    )
    if status == 404 or not isinstance(body, dict):
        return []
    results = body.get("results") or []
    rows = []
    for item in results:
        term = item.get("term")
        count = item.get("count")
        if isinstance(term, str) and isinstance(count, int):
            rows.append((term, count))
    return rows


async def fetch_faers(cache: HttpCache) -> dict[str, Any]:
    limiter = shared_limiter("openfda", 0.28)
    exposures: list[dict[str, Any]] = []
    pairs: list[dict[str, Any]] = []
    quarterly: list[dict[str, Any]] = []
    reaction_totals: dict[str, int] = {}
    errors: list[str] = []

    async with httpx.AsyncClient(timeout=60) as client:
        database_n = await _total(cache, client, limiter, None)
        last_updated = _total.last_updated  # type: ignore[attr-defined]
        if database_n is None:
            return {
                "status": "error",
                "detail": "openFDA drug/event total could not be read",
                "database_n": None,
                "last_updated": None,
                "exposures": [],
                "pairs": [],
                "reaction_totals": {},
                "quarterly": [],
            }

        quarters = _quarters(last_updated)
        spotlight = spotlight_drugs()
        needed_reactions = set(SAFETY_REACTIONS)

        for drug_class in DRUG_CLASSES:
            clause = class_search_clause(drug_class.key)
            total = await _total(cache, client, limiter, clause)
            if total is None:
                errors.append(f"class total failed: {drug_class.key}")
                continue
            exposures.append(
                {
                    "scope": "class",
                    "key": drug_class.key,
                    "label": drug_class.label,
                    "drug_class": drug_class.key,
                    "report_count": total,
                }
            )
            for reaction in SAFETY_REACTIONS:
                pair = await _total(cache, client, limiter, f"{clause} AND {reaction_clause(reaction)}")
                if pair is None:
                    errors.append(f"class pair failed: {drug_class.key} {reaction}")
                    continue
                pairs.append(
                    {
                        "scope": "class",
                        "key": drug_class.key,
                        "drug_class": drug_class.key,
                        "reaction": reaction,
                        "pair_count": pair,
                        "preset": True,
                    }
                )
            top = await _top_reactions(cache, client, limiter, clause)
            for reaction, count in top:
                if reaction not in SAFETY_REACTIONS:
                    pairs.append(
                        {
                            "scope": "class",
                            "key": drug_class.key,
                            "drug_class": drug_class.key,
                            "reaction": reaction,
                            "pair_count": count,
                            "preset": False,
                        }
                    )
                    needed_reactions.add(reaction)
            for quarter in quarters:
                search = f"{clause} AND receivedate:[{quarter['start']} TO {quarter['end']}]"
                count = await _total(cache, client, limiter, search)
                if count is None:
                    errors.append(f"quarter failed: {drug_class.key} {quarter['year']}Q{quarter['quarter']}")
                    continue
                quarterly.append(
                    {
                        "drug_class": drug_class.key,
                        "year": quarter["year"],
                        "quarter": quarter["quarter"],
                        "report_count": count,
                        "partial": quarter["partial"],
                    }
                )

        for drug in spotlight:
            clause = f'patient.drug.openfda.generic_name.exact:"{drug.generic_name}"'
            total = await _total(cache, client, limiter, clause)
            if total is None:
                errors.append(f"drug total failed: {drug.key}")
                continue
            exposures.append(_exposure(drug, total))
            if total == 0:
                continue
            for reaction in SAFETY_REACTIONS:
                pair = await _total(cache, client, limiter, f"{clause} AND {reaction_clause(reaction)}")
                if pair is None:
                    errors.append(f"drug pair failed: {drug.key} {reaction}")
                    continue
                pairs.append(
                    {
                        "scope": "drug",
                        "key": drug.key,
                        "drug_class": drug.drug_class,
                        "reaction": reaction,
                        "pair_count": pair,
                        "preset": True,
                    }
                )
            top = await _top_reactions(cache, client, limiter, clause)
            for reaction, count in top:
                if reaction in SAFETY_REACTIONS:
                    continue
                pairs.append(
                    {
                        "scope": "drug",
                        "key": drug.key,
                        "drug_class": drug.drug_class,
                        "reaction": reaction,
                        "pair_count": count,
                        "preset": False,
                    }
                )
                needed_reactions.add(reaction)

        extras = sorted(
            reaction
            for reaction in needed_reactions
            if reaction not in SAFETY_REACTIONS
            and not is_admin_term(reaction)
            and not is_indication_term(reaction)
        )[:MAX_EXTRA_REACTIONS]
        for reaction in list(SAFETY_REACTIONS) + extras:
            total = await _total(cache, client, limiter, reaction_clause(reaction))
            if total is None:
                errors.append(f"reaction total failed: {reaction}")
                continue
            reaction_totals[reaction] = total

    detail = f"openFDA drug/event last_updated={last_updated}; database_n={database_n}"
    if errors:
        detail += f"; {len(errors)} query gaps"
        log.warning("FAERS gaps: %s", "; ".join(errors[:8]))
    return {
        "status": "ok" if exposures else "error",
        "detail": detail,
        "database_n": database_n,
        "last_updated": last_updated,
        "exposures": exposures,
        "pairs": pairs,
        "reaction_totals": reaction_totals,
        "quarterly": quarterly,
        "errors": errors,
    }


def _exposure(drug: Drug, total: int) -> dict[str, Any]:
    return {
        "scope": "drug",
        "key": drug.key,
        "label": drug.label,
        "drug_class": drug.drug_class,
        "report_count": total,
    }


def non_spotlight_note() -> str:
    """Drugs outside the full reaction panel still have class-level rows."""
    missing = [drug.label for drug in drugs_in_class("other_immunomodulator")]
    return (
        "Full reaction panels are queried for NSAIDs, corticosteroids, TNF inhibitors, "
        "IL inhibitors, and JAK inhibitors. "
        + ", ".join(missing)
        + " are included in the taxonomy and in recall and alert tagging. "
        "Their class is aggregated as other immunomodulators."
    )
