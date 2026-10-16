"""Local dry-run stand-in for the Supabase edge functions.

    python -m inflammon.local_functions

Nothing is emailed. Confirm links are returned to the browser so the
double opt-in pages can be exercised without Resend or Supabase.
"""

from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from inflammon.list_api import ListStore, handle_request

HOST = "127.0.0.1"
PORT = 43124
SECRET = "local-dev-unsubscribe-secret"
ROOT = Path(__file__).resolve().parents[1]


def seed_store() -> ListStore:
    html_path = ROOT / "web" / "public" / "newsletter" / "email" / "2026-10-15.html"
    text_path = ROOT / "data" / "newsletter" / "issues" / "2026-10-15" / "issue.txt"
    html_body = html_path.read_text(encoding="utf8") if html_path.is_file() else "<p>Draft preview.</p>"
    text_body = text_path.read_text(encoding="utf8") if text_path.is_file() else "Draft preview."
    return ListStore(
        {
            "subscribers": [
                {
                    "id": "sub_pending",
                    "email": "pending@example.com",
                    "status": "pending",
                    "consent_at": "2026-10-01T12:00:00Z",
                    "consent_ip": "203.0.113.10",
                    "confirm_token_hash": None,
                    "confirmed_at": None,
                    "unsubscribed_at": None,
                },
                {
                    "id": "sub_active",
                    "email": "active@example.com",
                    "status": "active",
                    "consent_at": "2026-10-02T12:00:00Z",
                    "consent_ip": "203.0.113.11",
                    "confirm_token_hash": None,
                    "confirmed_at": "2026-10-02T12:05:00Z",
                    "unsubscribed_at": None,
                },
            ],
            "sends": [],
            "contact_requests": [],
            "issues": [
                {
                    "slug": "2026-10-15",
                    "subject": "TNF inhibitors: tuberculosis reported more often than expected (PRR 7.5)",
                    "headline": "TNF inhibitors: tuberculosis reported more often than expected (PRR 7.5)",
                    "html": html_body,
                    "text_body": text_body,
                    "status": "draft",
                }
            ],
            "allowlist": ["owner@example.com"],
            "rate": {},
        }
    )


STORE = seed_store()


class Handler(BaseHTTPRequestHandler):
    def do_OPTIONS(self) -> None:  # noqa: N802
        self._respond(204, "text/plain", "")

    def do_GET(self) -> None:  # noqa: N802
        self._dispatch()

    def do_POST(self) -> None:  # noqa: N802
        self._dispatch()

    def _dispatch(self) -> None:
        parsed = urlparse(self.path)
        query = {key: values[-1] for key, values in parse_qs(parsed.query).items()}
        length = int(self.headers.get("Content-Length") or 0)
        body = self.rfile.read(length) if length else b""
        status, content_type, payload = handle_request(
            self.command,
            parsed.path,
            query=query,
            headers={key: value for key, value in self.headers.items()},
            body=body,
            store=STORE,
            secret=SECRET,
            functions_base=f"http://{HOST}:{PORT}",
            site_url="http://127.0.0.1:43123",
            dry_run=True,
            expose_preview=True,
            turnstile_secret="1x0000000000000000000000000000000AA",
            client_ip=self.client_address[0],
        )
        self._respond(status, content_type, payload)

    def _respond(self, status: int, content_type: str, payload: str) -> None:
        data = payload.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", content_type or "text/plain")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "authorization, content-type, accept")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.end_headers()
        if status != 204:
            self.wfile.write(data)

    def log_message(self, fmt: str, *args) -> None:
        print(f"[list] {self.address_string()} {fmt % args}")


def main() -> None:
    server = ThreadingHTTPServer((HOST, PORT), Handler)
    print(json.dumps({"url": f"http://{HOST}:{PORT}", "dry_run": True}))
    server.serve_forever()


if __name__ == "__main__":
    main()
