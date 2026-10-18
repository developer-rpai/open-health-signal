"""ClinicalTrials.gov API v2 counts for inflammatory conditions.

Yearly and weekly series count studies whose start date falls in the
period (``AREA[StartDate]``). Weekly windows are complete ISO weeks from
:func:`inflammon.signals.trends.complete_iso_weeks`. The open week is omitted
so the spike detector is not comparing a partial week with full ones.
"""

from __future__ import annotations

import logging
from datetime import date
from typing import Any

import httpx

from inflammon.http_client import HttpCache, RateLimiter
from inflammon.signals.trends import complete_iso_weeks, iso_week_label
from inflammon.taxonomy import CONDITIONS

log = logging.getLogger(__name__)

STUDIES_URL = "https://clinicaltrials.gov/api/v2/studies"
YEAR_START = 2016
WEEKLY_WINDOW = 16


async def _count(
    cache: HttpCache,
    client: httpx.AsyncClient,
    limiter: RateLimiter,
    condition: str,
    start: str,
    end: str,
) -> int | None:
    status, body = await cache.get_json(
        client,
        STUDIES_URL,
        {
            "query.cond": condition,
            "countTotal": "true",
            "pageSize": 1,
            "filter.advanced": f"AREA[StartDate]RANGE[{start},{end}]",
        },
        limiter=limiter,
    )
    if status != 200 or not isinstance(body, dict) or "totalCount" not in body:
        return None
    return int(body["totalCount"])


async def _recent(
    cache: HttpCache,
    client: httpx.AsyncClient,
    limiter: RateLimiter,
    topic_key: str,
    condition: str,
) -> list[dict[str, Any]]:
    status, body = await cache.get_json(
        client,
        STUDIES_URL,
        {
            "query.cond": condition,
            "pageSize": 8,
            "countTotal": "true",
            "sort": "LastUpdatePostDate:desc",
            "fields": "NCTId,BriefTitle,OverallStatus,StartDate,LastUpdatePostDate,Phase,Condition,InterventionName,InterventionType,LeadSponsorName",
        },
        limiter=limiter,
    )
    if status != 200 or not isinstance(body, dict):
        return []
    rows = []
    for study in body.get("studies") or []:
        protocol = study.get("protocolSection") or {}
        ident = protocol.get("identificationModule") or {}
        status_mod = protocol.get("statusModule") or {}
        design = protocol.get("designModule") or {}
        conditions = (protocol.get("conditionsModule") or {}).get("conditions") or []
        phases = design.get("phases") or []
        interventions = []
        for entry in (protocol.get("armsInterventionsModule") or {}).get("interventions") or []:
            name = (entry.get("name") or "").strip()
            if not name:
                continue
            interventions.append({"type": entry.get("type") or "", "name": name})
        sponsor = ((protocol.get("sponsorCollaboratorsModule") or {}).get("leadSponsor") or {}).get("name") or ""
        nct_id = ident.get("nctId") or ""
        rows.append(
            {
                "nct_id": nct_id,
                "title": ident.get("briefTitle") or "",
                "status": status_mod.get("overallStatus") or "",
                "phase": ", ".join(phases),
                "conditions": "; ".join(conditions[:6]),
                "start_date": (status_mod.get("startDateStruct") or {}).get("date") or "",
                "last_update": (status_mod.get("lastUpdatePostDateStruct") or {}).get("date") or "",
                "topic": topic_key,
                "link": f"https://clinicaltrials.gov/study/{nct_id}" if nct_id else "",
                "interventions": interventions,
                "sponsor": sponsor,
            }
        )
    return rows


async def fetch_trials(cache: HttpCache, today: date | None = None) -> dict[str, Any]:
    today = today or date.today()
    limiter = RateLimiter(0.15)
    counts: list[dict[str, Any]] = []
    recent: list[dict[str, Any]] = []
    errors = 0
    weeks = complete_iso_weeks(today, WEEKLY_WINDOW)
    async with httpx.AsyncClient(timeout=60) as client:
        for topic in CONDITIONS:
            assert topic.trials_query
            for year in range(YEAR_START, today.year + 1):
                total = await _count(
                    cache,
                    client,
                    limiter,
                    topic.trials_query,
                    f"{year}-01-01",
                    f"{year}-12-31",
                )
                if total is None:
                    errors += 1
                    continue
                counts.append(
                    {
                        "topic": topic.key,
                        "label": topic.label,
                        "grain": "year",
                        "period": str(year),
                        "period_start": f"{year}-01-01",
                        "count": total,
                        "partial": year == today.year,
                    }
                )
            for start, end in weeks:
                total = await _count(
                    cache,
                    client,
                    limiter,
                    topic.trials_query,
                    start.isoformat(),
                    end.isoformat(),
                )
                if total is None:
                    errors += 1
                    continue
                counts.append(
                    {
                        "topic": topic.key,
                        "label": topic.label,
                        "grain": "week",
                        "period": iso_week_label(start),
                        "period_start": start.isoformat(),
                        "count": total,
                        "partial": False,
                    }
                )
            recent.extend(await _recent(cache, client, limiter, topic.key, topic.trials_query))
    status = "ok" if counts else "error"
    if errors and counts:
        status = "partial"
    return {
        "status": status,
        "detail": f"{len(counts)} trial counts, {len(recent)} recent studies, {errors} failed queries",
        "counts": counts,
        "recent": recent,
    }
