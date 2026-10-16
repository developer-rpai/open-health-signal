"""Cached, rate-limited HTTP for public APIs.

Responses are stored under ``data/raw/http`` so a weekly refresh can be
re-run without spending the unauthenticated openFDA daily quota again.
Pass ``force=True`` to ignore the cache. HTTP 404 bodies are cached
because openFDA uses 404 for an empty search. Server errors are not cached.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import os
from pathlib import Path
from typing import Any

import httpx

log = logging.getLogger(__name__)

USER_AGENT = "inflammon/0.1.0 (public-health pharmacovigilance research)"
CACHE_DIR = Path("data/raw/http")


_SHARED: dict[str, "RateLimiter"] = {}


def openfda_request_params(url: str, params: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    """Return ``(cache_params, request_params)``.

    ``OPENFDA_API_KEY`` is added only to the outgoing request. It is not part of
    the cache key and it is not written into the cache file.
    """
    cache_params = {key: value for key, value in params.items() if key != "api_key"}
    request_params = dict(cache_params)
    host = url.lower()
    if "api.fda.gov" in host or "open.fda.gov" in host:
        api_key = os.environ.get("OPENFDA_API_KEY", "").strip()
        if api_key:
            request_params["api_key"] = api_key
    return cache_params, request_params


def shared_limiter(name: str, min_interval: float) -> "RateLimiter":
    """One limiter per host, shared by concurrent ingesters."""
    limiter = _SHARED.get(name)
    if limiter is None:
        limiter = RateLimiter(min_interval)
        _SHARED[name] = limiter
    return limiter


class RateLimiter:
    def __init__(self, min_interval: float) -> None:
        self.min_interval = min_interval
        self._lock = asyncio.Lock()
        self._next = 0.0

    async def wait(self) -> None:
        async with self._lock:
            loop = asyncio.get_running_loop()
            now = loop.time()
            if now < self._next:
                await asyncio.sleep(self._next - now)
            self._next = loop.time() + self.min_interval


class HttpCache:
    def __init__(self, root: Path = CACHE_DIR, force: bool = False) -> None:
        self.root = root
        self.force = force
        self.root.mkdir(parents=True, exist_ok=True)
        self.requests = 0
        self.cache_hits = 0
        self.errors: list[str] = []

    def _path(self, url: str, params: dict[str, Any]) -> Path:
        payload = json.dumps({"url": url, "params": params}, sort_keys=True)
        digest = hashlib.sha256(payload.encode()).hexdigest()
        return self.root / f"{digest}.json"

    async def get_json(
        self,
        client: httpx.AsyncClient,
        url: str,
        params: dict[str, Any] | None = None,
        *,
        limiter: RateLimiter | None = None,
        retries: int = 4,
    ) -> tuple[int, Any]:
        params = params or {}
        cache_params, request_params = openfda_request_params(url, params)
        path = self._path(url, cache_params)
        if path.exists() and not self.force:
            self.cache_hits += 1
            cached = json.loads(path.read_text())
            return int(cached["status"]), cached["body"]

        last_error = "request failed"
        for attempt in range(retries + 1):
            if limiter is not None:
                await limiter.wait()
            self.requests += 1
            try:
                response = await client.get(url, params=request_params, headers={"User-Agent": USER_AGENT})
            except httpx.HTTPError as exc:
                last_error = f"{url} {exc}"
                await asyncio.sleep(min(2**attempt, 20))
                continue
            status = response.status_code
            try:
                body: Any = response.json()
            except json.JSONDecodeError:
                body = {"_non_json": response.text[:2000]}
            if status in {429, 500, 502, 503, 504} and attempt < retries:
                delay = min(2**attempt, 20)
                retry_after = response.headers.get("Retry-After")
                if retry_after and retry_after.isdigit():
                    delay = max(delay, int(retry_after))
                last_error = f"{url} HTTP {status}"
                await asyncio.sleep(delay)
                continue
            if status < 400 or status == 404:
                path.write_text(json.dumps({"status": status, "url": url, "params": cache_params, "body": body}))
            if status >= 400 and status != 404:
                self.errors.append(f"HTTP {status} {url}")
                log.warning("HTTP %s for %s", status, url)
            return status, body
        self.errors.append(last_error)
        log.error(last_error)
        return 0, {"error": {"code": "REQUEST_FAILED", "message": last_error}}


def openfda_total(status: int, body: Any) -> int | None:
    """Return a report total, 0 for an empty search, or None on failure."""
    if status == 404:
        return 0
    if not isinstance(body, dict):
        return None
    error = body.get("error")
    if isinstance(error, dict) and error.get("code") == "NOT_FOUND":
        return 0
    meta = body.get("meta")
    if not isinstance(meta, dict):
        return None
    results = meta.get("results") or {}
    total = results.get("total")
    if total is None:
        return None
    return int(total)


def openfda_last_updated(body: Any) -> str | None:
    if isinstance(body, dict):
        meta = body.get("meta") or {}
        value = meta.get("last_updated")
        if isinstance(value, str):
            return value
    return None
