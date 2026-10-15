"""Double opt-in for the Resend alternative.

The static site cannot run this. Deploy ``newsletter/resend`` on its own
(Vercel root directory, or any Python host) and point
``NEXT_PUBLIC_SUBSCRIBE_ENDPOINT`` at ``/subscribe``.
"""

from __future__ import annotations

import hashlib
import hmac
import html
import json
from urllib.parse import parse_qs, quote

RESEND_EMAILS = "https://api.resend.com/emails"
RESEND_AUDIENCES = "https://api.resend.com/audiences"


def confirm_token(email: str, secret: str) -> str:
    normalized = email.strip().lower()
    return hmac.new(secret.encode("utf-8"), normalized.encode("utf-8"), hashlib.sha256).hexdigest()


def handle_subscribe(
    fields: dict,
    *,
    secret: str,
    function_url: str,
    api_key: str,
    from_address: str,
    post,
) -> dict:
    email = str(fields.get("email") or "").strip()
    if str(fields.get("consent") or "").strip().lower() not in {"on", "yes", "true", "1"}:
        return _result(400, "Consent is required", "Check the consent box before subscribing.")
    if not _valid_email(email):
        return _result(400, "Email needed", "Enter an email address.")
    if not secret or not api_key or not from_address or not function_url:
        return _result(500, "List not configured", "The confirmation mailer is missing its API settings.")
    token = confirm_token(email, secret)
    link = f"{function_url.rstrip('/')}/confirm?email={quote(email)}&token={token}"
    post(
        RESEND_EMAILS,
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        json={
            "from": from_address,
            "to": [email],
            "subject": "Confirm your Inflammation Signal Monitor briefing",
            "text": (
                "Confirm this address to receive the weekly Inflammation Signal Monitor briefing.\n\n"
                f"{link}\n\n"
                "If you did not ask for this, ignore the message. You will not be added until you open the link."
            ),
        },
    )
    return _result(
        200,
        "Check your inbox",
        "A confirmation message is on its way. The weekly briefing starts after you open that link.",
    )


def handle_confirm(
    email: str,
    token: str,
    *,
    secret: str,
    audience_id: str,
    api_key: str,
    post,
) -> dict:
    normalized = (email or "").strip()
    if not secret or not audience_id or not api_key:
        return _result(500, "List not configured", "The confirmation mailer is missing its API settings.")
    expected = confirm_token(normalized, secret)
    if not normalized or not token or not hmac.compare_digest(expected, token.strip()):
        return _result(400, "Link not valid", "This confirmation link does not match. Subscribe again from the dashboard.")
    post(
        f"{RESEND_AUDIENCES}/{audience_id}/contacts",
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        json={"email": normalized, "unsubscribed": False},
    )
    return _result(
        200,
        "You are confirmed",
        "The next Inflammation Signal Monitor briefing goes out after the Monday refresh. Unsubscribe from any issue.",
    )


def parse_form(raw: str, content_type: str | None) -> dict:
    if "application/json" in (content_type or ""):
        payload = json.loads(raw or "{}")
        return {key: value for key, value in payload.items()}
    parsed = parse_qs(raw or "", keep_blank_values=True)
    return {key: values[-1] for key, values in parsed.items()}


def _valid_email(email: str) -> bool:
    if " " in email or email.count("@") != 1:
        return False
    local, domain = email.split("@")
    return bool(local) and "." in domain and not domain.startswith(".") and not domain.endswith(".")


def _result(status: int, title: str, message: str) -> dict:
    return {"status": status, "title": title, "message": message, "html": _page(title, message)}


def _page(title: str, message: str) -> str:
    safe_title = html.escape(title)
    safe_message = html.escape(message)
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{safe_title}</title>
</head>
<body style="margin:0;background:#f4f1ea;color:#1c1917;font-family:Georgia,serif;">
  <main style="max-width:32rem;margin:4rem auto;padding:0 1.25rem;">
    <p style="letter-spacing:0.14em;text-transform:uppercase;font-size:0.75rem;color:#0f5c5c;">Inflammation Signal Monitor</p>
    <h1 style="font-weight:normal;font-size:2rem;">{safe_title}</h1>
    <p style="font-size:1.05rem;line-height:1.5;">{safe_message}</p>
  </main>
</body>
</html>
"""
