"""openFDA drug/enforcement recalls for the monitored products.

Recalls are searched on ``product_description``. Many inflammatory-disease
drugs have no enforcement reports; an empty search is a real result, not
a failed request.
"""

from __future__ import annotations

import logging
from typing import Any

import httpx

from inflammon.http_client import HttpCache, openfda_total, shared_limiter
from inflammon.taxonomy import DRUGS, CLASS_BY_KEY

log = logging.getLogger(__name__)

ENFORCEMENT_URL = "https://api.fda.gov/drug/enforcement.json"


def _search_terms() -> list[tuple[str, str]]:
    terms: list[tuple[str, str]] = []
    seen: set[str] = set()
    for drug in DRUGS:
        candidates = [drug.key.replace("_", " "), *drug.brands]
        if " " in drug.generic_name:
            candidates.append(drug.generic_name.lower())
        for term in candidates:
            cleaned = term.strip().lower()
            if len(cleaned) < 4 or cleaned in seen:
                continue
            seen.add(cleaned)
            terms.append((cleaned, drug.drug_class))
    return terms


async def fetch_recalls(cache: HttpCache) -> dict[str, Any]:
    limiter = shared_limiter("openfda", 0.28)
    found: dict[str, dict[str, Any]] = {}
    errors: list[str] = []
    terms = _search_terms()
    async with httpx.AsyncClient(timeout=60) as client:
        for term, drug_class in terms:
            status, body = await cache.get_json(
                client,
                ENFORCEMENT_URL,
                {"search": f"product_description:{term}", "limit": 20},
                limiter=limiter,
            )
            total = openfda_total(status, body)
            if total is None:
                errors.append(term)
                continue
            if total == 0 or not isinstance(body, dict):
                continue
            for item in body.get("results") or []:
                number = str(item.get("recall_number") or item.get("event_id") or "")
                if not number or number in found:
                    continue
                description = str(item.get("product_description") or "")
                found[number] = {
                    "recall_number": number,
                    "product_description": description[:500],
                    "reason": str(item.get("reason_for_recall") or "")[:500],
                    "status": str(item.get("status") or ""),
                    "classification": str(item.get("classification") or ""),
                    "recalling_firm": str(item.get("recalling_firm") or ""),
                    "report_date": str(item.get("report_date") or ""),
                    "matched_term": term,
                    "drug_class": drug_class,
                }
    rows = sorted(found.values(), key=lambda row: row["report_date"], reverse=True)
    detail = f"{len(rows)} recalls across {len(terms)} product searches"
    if errors:
        detail += f"; {len(errors)} searches failed"
        log.warning("enforcement gaps: %s", ", ".join(errors[:8]))
    status_name = "ok" if not errors or rows or len(errors) < len(terms) else "error"
    if errors and not rows and len(errors) == len(terms):
        status_name = "error"
    return {"status": status_name, "detail": detail, "rows": rows, "class_labels": {k: v.label for k, v in CLASS_BY_KEY.items()}}
