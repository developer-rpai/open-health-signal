"""FDA MedWatch and drug-safety feeds.

MedWatch has a public RSS feed. The Drug Safety Communications index does
not: the historical RSS path returns 404, so this module fetches the public
HTML index and keeps the links it can parse. The Apify actor in ``apify/``
is the scraper meant to survive markup changes on that page and on state
health-department pages.
"""

from __future__ import annotations

import logging
import re
from html.parser import HTMLParser
from typing import Any
from xml.etree import ElementTree

import httpx

from inflammon.http_client import USER_AGENT, HttpCache, RateLimiter
from inflammon.taxonomy import CONDITIONS, DRUGS

log = logging.getLogger(__name__)

MEDWATCH_RSS = "https://www.fda.gov/about-fda/contact-fda/stay-informed/rss-feeds/medwatch/rss.xml"
DRUGS_RSS = "https://www.fda.gov/about-fda/contact-fda/stay-informed/rss-feeds/drugs/rss.xml"
DSC_RSS_CANDIDATES = (
    "https://www.fda.gov/about-fda/contact-fda/stay-informed/rss-feeds/drug-safety-communications/rss.xml",
)
DSC_PAGE = "https://www.fda.gov/drugs/drug-safety-and-availability/drug-safety-communications"

TAG_PATTERN = re.compile(r"<[^>]+>")


def tag_text(text: str) -> list[str]:
    """Return drug-class and condition keys mentioned in a notice."""
    haystack = text.lower()
    tags: list[str] = []
    for drug in DRUGS:
        names = [drug.label.lower(), drug.key.replace("_", " "), *drug.brands]
        if any(name and name in haystack for name in names):
            if drug.drug_class not in tags:
                tags.append(drug.drug_class)
    for condition in CONDITIONS:
        if condition.label.lower() in haystack or condition.key.replace("_", " ") in haystack:
            tags.append(condition.key)
    if "jak inhibitor" in haystack or "janus kinase" in haystack:
        if "jak_inhibitor" not in tags:
            tags.append("jak_inhibitor")
    if "nsaid" in haystack or "nonsteroidal" in haystack:
        if "nsaid" not in tags:
            tags.append("nsaid")
    if "ulcerative colitis" in haystack or "crohn" in haystack or "inflammatory bowel" in haystack:
        if "crohns_disease" not in tags and "crohn" in haystack:
            tags.append("crohns_disease")
        if "ulcerative_colitis" not in tags and "ulcerative colitis" in haystack:
            tags.append("ulcerative_colitis")
    return tags


def parse_rss(xml_text: str, source: str) -> list[dict[str, Any]]:
    try:
        root = ElementTree.fromstring(xml_text)
    except ElementTree.ParseError:
        return []
    items = []
    for item in root.findall(".//item"):
        title = (item.findtext("title") or "").strip()
        link = (item.findtext("link") or "").strip()
        published = (item.findtext("pubDate") or "").strip()
        summary = TAG_PATTERN.sub(" ", item.findtext("description") or "")
        summary = re.sub(r"\s+", " ", summary).strip()[:600]
        if not title:
            continue
        items.append(
            {
                "source": source,
                "title": title,
                "link": link,
                "published": published,
                "summary": summary,
                "tags": tag_text(f"{title} {summary}"),
            }
        )
    return items


class _AnchorParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.links: list[tuple[str, str]] = []
        self._href: str | None = None
        self._chunks: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() != "a":
            return
        href = dict(attrs).get("href")
        if href:
            self._href = href
            self._chunks = []

    def handle_data(self, data: str) -> None:
        if self._href is not None:
            self._chunks.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() == "a" and self._href is not None:
            text = re.sub(r"\s+", " ", "".join(self._chunks)).strip()
            self.links.append((self._href, text))
            self._href = None
            self._chunks = []


def parse_dsc_html(html: str) -> list[dict[str, Any]]:
    parser = _AnchorParser()
    parser.feed(html)
    rows = []
    seen: set[str] = set()
    for href, text in parser.links:
        if "safety-communication" not in href and "/drugs/drug-safety-and-availability/" not in href:
            continue
        if href.rstrip("/").endswith("drug-safety-communications"):
            continue
        if not text or len(text) < 20:
            continue
        if href.startswith("/"):
            href = "https://www.fda.gov" + href
        if href in seen:
            continue
        seen.add(href)
        rows.append(
            {
                "source": "FDA Drug Safety Communications",
                "title": text,
                "link": href,
                "published": "",
                "summary": "",
                "tags": tag_text(text),
            }
        )
    return rows


async def _fetch_text(cache: HttpCache, client: httpx.AsyncClient, limiter: RateLimiter, url: str) -> tuple[int, str]:
    if limiter:
        await limiter.wait()
    cache.requests += 1
    try:
        response = await client.get(url, headers={"User-Agent": USER_AGENT})
    except httpx.HTTPError as exc:
        cache.errors.append(str(exc))
        return 0, ""
    return response.status_code, response.text


async def fetch_alerts(cache: HttpCache) -> dict[str, Any]:
    limiter = RateLimiter(0.3)
    items: list[dict[str, Any]] = []
    notes: list[str] = []
    failed = False
    async with httpx.AsyncClient(timeout=60, follow_redirects=True) as client:
        for url, source in (
            (MEDWATCH_RSS, "FDA MedWatch"),
            (DRUGS_RSS, "FDA Drugs"),
        ):
            status, text = await _fetch_text(cache, client, limiter, url)
            parsed = parse_rss(text, source) if status == 200 else []
            if status != 200 or not parsed:
                failed = True
                notes.append(f"{source} RSS HTTP {status}, {len(parsed)} items")
            else:
                notes.append(f"{source} RSS {len(parsed)} items")
            items.extend(parsed)
        dsc_rss_ok = False
        for url in DSC_RSS_CANDIDATES:
            status, text = await _fetch_text(cache, client, limiter, url)
            if status == 200 and "<item" in text.lower():
                parsed = parse_rss(text, "FDA Drug Safety Communications")
                items.extend(parsed)
                notes.append(f"DSC RSS {len(parsed)} items")
                dsc_rss_ok = True
            else:
                notes.append(f"DSC RSS unavailable (HTTP {status})")
        if not dsc_rss_ok:
            status, html = await _fetch_text(cache, client, limiter, DSC_PAGE)
            if status == 200:
                parsed = parse_dsc_html(html)
                items.extend(parsed)
                notes.append(f"DSC HTML index {len(parsed)} links")
                if not parsed:
                    notes.append("DSC HTML returned no safety-communication links; the Apify actor is the fallback scraper")
            else:
                failed = True
                notes.append(f"DSC HTML HTTP {status}")
    # Stable order: tagged inflammation items first, then the feed order.
    items.sort(key=lambda row: (0 if row["tags"] else 1, row["source"]))
    status_name = "ok" if items else "error"
    if failed and items:
        status_name = "partial"
    return {"status": status_name, "detail": "; ".join(notes), "rows": items}
