"""Vercel Python entry point. Set the project root to newsletter/resend."""

from __future__ import annotations

import os
import sys
from http.server import BaseHTTPRequestHandler
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from handler import handle_subscribe, parse_form  # noqa: E402


class handler(BaseHTTPRequestHandler):
    def do_POST(self) -> None:
        length = int(self.headers.get("content-length", "0") or "0")
        raw = self.rfile.read(length).decode("utf-8", errors="replace")
        fields = parse_form(raw, self.headers.get("content-type"))
        result = handle_subscribe(
            fields,
            secret=os.environ.get("NEWSLETTER_CONFIRM_SECRET", ""),
            function_url=os.environ.get("SUBSCRIBE_FUNCTION_URL", ""),
            api_key=os.environ.get("RESEND_API_KEY", ""),
            from_address=os.environ.get("NEWSLETTER_FROM", ""),
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
