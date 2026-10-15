"""Vercel Python entry point for the confirmation link."""

from __future__ import annotations

import os
import sys
from http.server import BaseHTTPRequestHandler
from pathlib import Path
from urllib.parse import parse_qs, urlparse

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from handler import handle_confirm  # noqa: E402


class handler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        query = parse_qs(urlparse(self.path).query)
        email = (query.get("email") or [""])[-1]
        token = (query.get("token") or [""])[-1]
        result = handle_confirm(
            email,
            token,
            secret=os.environ.get("NEWSLETTER_CONFIRM_SECRET", ""),
            audience_id=os.environ.get("RESEND_AUDIENCE_ID", ""),
            api_key=os.environ.get("RESEND_API_KEY", ""),
            post=_post,
        )
        body = result["html"].encode("utf-8")
        self.send_response(result["status"])
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def _post(url: str, *, headers: dict, json: dict) -> dict:
    import httpx

    response = httpx.post(url, headers=headers, json=json, timeout=30.0)
    response.raise_for_status()
    if not response.content:
        return {}
    return response.json()
