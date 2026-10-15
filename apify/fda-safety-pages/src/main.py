"""Stub actor for public safety pages that have no API.

One HTTP GET per start URL. Links are taken from anchor tags with the
standard-library HTML parser. Pages are not executed as code. This is the
scraper to point at the FDA Drug Safety Communications index and, later,
state health-department advisories (California CDPH, New York State DOH)
that the weekly Python package does not pretend to have a stable API for.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from html.parser import HTMLParser
from urllib.parse import urljoin

import httpx
from apify import Actor


class _Links(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.found: list[tuple[str, str]] = []
        self._href: str | None = None
        self._chunks: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() != "a":
            return
        href = dict(attrs).get("href")
        if href and not href.startswith(("#", "javascript:", "mailto:")):
            self._href = href
            self._chunks = []

    def handle_data(self, data: str) -> None:
        if self._href is not None:
            self._chunks.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() == "a" and self._href is not None:
            title = " ".join("".join(self._chunks).split())
            if len(title) >= 20:
                self.found.append((self._href, title))
            self._href = None
            self._chunks = []


async def main() -> None:
    async with Actor:
        actor_input = await Actor.get_input() or {}
        start_urls = actor_input.get("startUrls") or [
            {"url": "https://www.fda.gov/drugs/drug-safety-and-availability/drug-safety-communications"}
        ]
        max_items = int(actor_input.get("maxItems") or 40)
        stored = 0
        async with httpx.AsyncClient(
            timeout=45,
            follow_redirects=True,
            headers={"User-Agent": "inflammon-fda-safety-pages/0.1 (public safety page stub)"},
        ) as client:
            for entry in start_urls:
                if stored >= max_items:
                    break
                url = entry.get("url") if isinstance(entry, dict) else str(entry)
                if not url or not url.startswith("https://"):
                    Actor.log.warning("Skipping non-HTTPS URL")
                    continue
                try:
                    response = await client.get(url)
                    response.raise_for_status()
                except httpx.HTTPError as exc:
                    Actor.log.warning("Fetch failed for %s: %s", url, exc)
                    continue
                parser = _Links()
                parser.feed(response.text)
                seen: set[str] = set()
                for href, title in parser.found:
                    if stored >= max_items:
                        break
                    absolute = urljoin(url, href)
                    if not absolute.startswith("https://") or absolute in seen:
                        continue
                    seen.add(absolute)
                    await Actor.push_data(
                        {
                            "title": title[:300],
                            "url": absolute,
                            "sourcePage": url,
                            "extractedAt": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
                        }
                    )
                    stored += 1
        Actor.log.info("Stored %s links", stored)


if __name__ == "__main__":
    asyncio.run(main())
