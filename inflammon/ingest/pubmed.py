"""PubMed E-utilities counts and recent citation metadata.

Only identifiers, titles, journals, and dates are stored. Abstracts stay
with the publisher. Counts use the history-free esearch endpoint. NCBI
asks unauthenticated clients to stay at or below three requests a second;
this module waits a third of a second between calls.
"""

from __future__ import annotations

import logging
from datetime import date
from typing import Any

import httpx

from inflammon.http_client import HttpCache, RateLimiter
from inflammon.signals.trends import complete_iso_weeks, iso_week_label
from inflammon.taxonomy import CONDITIONS, PUBLICATION_TOPICS

log = logging.getLogger(__name__)

ESEARCH = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
ESUMMARY = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi"
YEAR_START = 2016
WEEKLY_WINDOW = 16


def _base_params() -> dict[str, str]:
    return {"tool": "inflammon", "db": "pubmed", "retmode": "json"}


async def _count(
    cache: HttpCache,
    client: httpx.AsyncClient,
    limiter: RateLimiter,
    term: str,
) -> int | None:
    params = _base_params()
    params.update({"term": term, "rettype": "count"})
    status, body = await cache.get_json(client, ESEARCH, params, limiter=limiter)
    if status != 200 or not isinstance(body, dict):
        return None
    result = body.get("esearchresult") or {}
    if "count" not in result or result.get("ERROR"):
        return None
    return int(result["count"])


async def _recent(
    cache: HttpCache,
    client: httpx.AsyncClient,
    limiter: RateLimiter,
    topic_key: str,
    term: str,
) -> list[dict[str, Any]]:
    params = _base_params()
    params.update({"term": term, "retmax": "6", "sort": "pub_date"})
    status, body = await cache.get_json(client, ESEARCH, params, limiter=limiter)
    if status != 200 or not isinstance(body, dict):
        return []
    ids = (body.get("esearchresult") or {}).get("idlist") or []
    if not ids:
        return []
    summary_params = _base_params()
    summary_params["id"] = ",".join(ids)
    status, summary = await cache.get_json(client, ESUMMARY, summary_params, limiter=limiter)
    if status != 200 or not isinstance(summary, dict):
        return []
    result = summary.get("result") or {}
    rows = []
    for pmid in ids:
        item = result.get(pmid) or {}
        title = item.get("title") or ""
        if not title:
            continue
        rows.append(
            {
                "pmid": pmid,
                "title": title.rstrip("."),
                "journal": item.get("source") or "",
                "published": item.get("pubdate") or "",
                "topic": topic_key,
                "link": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
            }
        )
    return rows


async def fetch_publications(cache: HttpCache, today: date | None = None) -> dict[str, Any]:
    today = today or date.today()
    limiter = RateLimiter(0.34)
    counts: list[dict[str, Any]] = []
    recent: list[dict[str, Any]] = []
    errors = 0
    weeks = complete_iso_weeks(today, WEEKLY_WINDOW)
    async with httpx.AsyncClient(timeout=60) as client:
        for topic in PUBLICATION_TOPICS:
            for year in range(YEAR_START, today.year + 1):
                total = await _count(cache, client, limiter, f"({topic.pubmed_term}) AND {year}[pdat]")
                if total is None:
                    errors += 1
                    continue
                counts.append(
                    {
                        "topic": topic.key,
                        "label": topic.label,
                        "topic_type": topic.topic_type,
                        "grain": "year",
                        "period": str(year),
                        "period_start": f"{year}-01-01",
                        "count": total,
                        "partial": year == today.year,
                    }
                )
            if topic.topic_type == "condition":
                for start, end in weeks:
                    date_range = f"{start.strftime('%Y/%m/%d')}:{end.strftime('%Y/%m/%d')}[pdat]"
                    total = await _count(cache, client, limiter, f"({topic.pubmed_term}) AND {date_range}")
                    if total is None:
                        errors += 1
                        continue
                    counts.append(
                        {
                            "topic": topic.key,
                            "label": topic.label,
                            "topic_type": topic.topic_type,
                            "grain": "week",
                            "period": iso_week_label(start),
                            "period_start": start.isoformat(),
                            "count": total,
                            "partial": False,
                        }
                    )
                recent.extend(await _recent(cache, client, limiter, topic.key, topic.pubmed_term))
    status = "ok" if counts else "error"
    if errors and counts:
        status = "partial"
    return {
        "status": status,
        "detail": f"{len(counts)} publication counts, {len(recent)} recent citations, {errors} failed queries",
        "counts": counts,
        "recent": recent,
    }
