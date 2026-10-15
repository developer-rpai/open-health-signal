"""CDC Chronic Disease Indicators, arthritis rows in dataset hksd-2xuw.

data.cdc.gov does not publish a comparable IBD dataset. Crohn's disease and
ulcerative colitis are followed here with trials and publications only.
The catalog search is stored so that absence is a checked fact, not an
assumption.
"""

from __future__ import annotations

import logging
from typing import Any

import httpx

from inflammon.http_client import HttpCache, RateLimiter

log = logging.getLogger(__name__)

CDI_URL = "https://data.cdc.gov/resource/hksd-2xuw.json"
CATALOG_URL = "https://data.cdc.gov/api/catalog/v1"
QUESTIONS = (
    "Arthritis among adults",
    "Activity limitation due to arthritis among adults with arthritis",
)
IBD_NOTE = (
    "data.cdc.gov has no IBD surveillance dataset comparable to Chronic Disease "
    "Indicators. Dataset hksd-2xuw includes arthritis. Crohn's disease and "
    "ulcerative colitis trends in this monitor are ClinicalTrials.gov start "
    "counts and PubMed publication counts."
)


def _float(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


async def fetch_cdc(cache: HttpCache) -> dict[str, Any]:
    limiter = RateLimiter(0.2)
    rows: list[dict[str, Any]] = []
    catalog_note = ""
    async with httpx.AsyncClient(timeout=60) as client:
        status, body = await cache.get_json(
            client,
            CDI_URL,
            {
                "$where": "locationabbr='US' AND topic='Arthritis' AND stratificationcategory1='Overall'",
                "$limit": 500,
            },
            limiter=limiter,
        )
        if status != 200 or not isinstance(body, list):
            return {
                "status": "error",
                "detail": f"CDC CDI HTTP {status}",
                "rows": [],
                "ibd_note": IBD_NOTE,
                "catalog_note": "",
            }
        for item in body:
            question = item.get("question") or ""
            if question not in QUESTIONS:
                continue
            if item.get("datavaluetype") not in (None, "Crude Prevalence"):
                continue
            value = _float(item.get("datavalue"))
            if value is None:
                continue
            rows.append(
                {
                    "year": str(item.get("yearstart") or ""),
                    "question": question,
                    "data_value": value,
                    "unit": str(item.get("datavalueunit") or "%"),
                    "stratification": str(item.get("stratification1") or "Overall"),
                    "low_ci": _float(item.get("lowconfidencelimit")),
                    "high_ci": _float(item.get("highconfidencelimit")),
                }
            )
        catalog_status, catalog = await cache.get_json(
            client,
            CATALOG_URL,
            {"q": "inflammatory bowel disease", "limit": 5},
            limiter=limiter,
        )
        if catalog_status == 200 and isinstance(catalog, dict):
            results = catalog.get("results") or catalog.get("result") or []
            names = []
            if isinstance(results, list):
                for entry in results[:5]:
                    if isinstance(entry, dict):
                        resource = entry.get("resource") or entry
                        name = resource.get("name") or resource.get("id") or ""
                        if name:
                            names.append(str(name))
            catalog_note = (
                "A data.cdc.gov catalog search for inflammatory bowel disease did not return "
                "a surveillance table comparable to Chronic Disease Indicators. "
                "IBD trends on this dashboard use ClinicalTrials.gov and PubMed."
            )
        else:
            catalog_note = f"CDC catalog search HTTP {catalog_status}"
    rows.sort(key=lambda row: (row["question"], row["year"]))
    status_name = "ok" if rows else "error"
    return {
        "status": status_name,
        "detail": f"{len(rows)} US overall arthritis indicator rows. {catalog_note}",
        "rows": rows,
        "ibd_note": IBD_NOTE,
        "catalog_note": catalog_note,
    }
