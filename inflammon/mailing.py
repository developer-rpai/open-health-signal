"""Subscriber tokens, send-time suppression, and Resend webhook checks.

Supabase is the source of truth in production. This module is the behavior
the Monday job and the local function server both use. Edge functions in
``supabase/functions`` follow the same token and Svix steps.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import secrets
import time
from collections.abc import Callable
from typing import Any

STATUSES = ("pending", "active", "unsubscribed", "bounced", "complained")
SUPPRESSED_STATUSES = frozenset({"pending", "unsubscribed", "bounced", "complained"})
INTEREST_TYPES = (
    "research_collaboration",
    "data_expansion",
    "code_contribution",
    "custom_analysis",
    "media",
    "sponsorship",
)
UNSUBSCRIBE_PLACEHOLDER = "__UNSUBSCRIBE_URL__"
SVIX_TOLERANCE_SECONDS = 300


def normalize_email(email: str) -> str:
    return (email or "").strip().lower()


def valid_email(email: str) -> bool:
    normalized = normalize_email(email)
    if " " in normalized or normalized.count("@") != 1:
        return False
    local, domain = normalized.split("@")
    return bool(local) and "." in domain and not domain.startswith(".") and not domain.endswith(".")


def new_confirm_token() -> str:
    return secrets.token_urlsafe(32)


def hash_confirm_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def confirm_token_matches(token: str, token_hash: str) -> bool:
    if not token or not token_hash:
        return False
    return hmac.compare_digest(hash_confirm_token(token), token_hash)


def sign_unsubscribe_token(subscriber_id: str, email: str, secret: str) -> str:
    if not secret:
        raise ValueError("unsubscribe signing secret is empty")
    payload = json.dumps(
        {"email": normalize_email(email), "sid": str(subscriber_id)},
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    body = _b64encode(payload)
    signature = hmac.new(secret.encode("utf-8"), body.encode("ascii"), hashlib.sha256).digest()
    return f"{body}.{_b64encode(signature)}"


def verify_unsubscribe_token(token: str, secret: str) -> dict[str, str] | None:
    if not token or not secret or "." not in token:
        return None
    body, signature = token.split(".", 1)
    expected = hmac.new(secret.encode("utf-8"), body.encode("ascii"), hashlib.sha256).digest()
    try:
        presented = _b64decode(signature)
    except (ValueError, TypeError):
        return None
    if not hmac.compare_digest(expected, presented):
        return None
    try:
        payload = json.loads(_b64decode(body))
    except (ValueError, TypeError, json.JSONDecodeError):
        return None
    sid = str(payload.get("sid") or "")
    email = normalize_email(str(payload.get("email") or ""))
    if not sid or not email:
        return None
    return {"sid": sid, "email": email}


def decision_at_send_time(status: str | None) -> str:
    """Return ``send`` only for a row that is active at the moment of sending."""
    if status == "active":
        return "send"
    return "suppress"


def idempotency_key(issue_slug: str, subscriber_id: str) -> str:
    return f"{issue_slug}:{subscriber_id}"


def unsubscribe_url(functions_base: str, token: str) -> str:
    return f"{functions_base.rstrip('/')}/unsubscribe?token={token}"


def list_unsubscribe_headers(url: str) -> dict[str, str]:
    return {
        "List-Unsubscribe": f"<{url}>",
        "List-Unsubscribe-Post": "List-Unsubscribe=One-Click",
    }


def plan_recipient(
    *,
    issue_slug: str,
    subscriber: dict[str, Any],
    secret: str,
    functions_base: str,
    already_logged: set[str],
    site_url: str = "",
) -> dict[str, Any]:
    """Decide one recipient from the row read at send time.

    The visible link opens the site page. ``List-Unsubscribe`` points at the
    function, which accepts the RFC 8058 POST without JavaScript.
    """
    subscriber_id = str(subscriber["id"])
    key = idempotency_key(issue_slug, subscriber_id)
    status = subscriber.get("status")
    if decision_at_send_time(status if isinstance(status, str) else None) != "send":
        return {"idempotency_key": key, "action": "suppress", "subscriber_status": status}
    if key in already_logged:
        return {"idempotency_key": key, "action": "skip_duplicate", "subscriber_status": status}
    token = sign_unsubscribe_token(subscriber_id, str(subscriber.get("email") or ""), secret)
    header_url = unsubscribe_url(functions_base, token)
    page_base = (site_url or functions_base).rstrip("/")
    page_url = f"{page_base}/unsubscribe?token={token}"
    return {
        "idempotency_key": key,
        "action": "send",
        "subscriber_status": status,
        "email": normalize_email(str(subscriber.get("email") or "")),
        "unsubscribe_url": page_url,
        "list_unsubscribe_url": header_url,
        "headers": {**list_unsubscribe_headers(header_url), "Idempotency-Key": key},
    }


def resend_email_payload(
    *,
    from_address: str,
    to_email: str,
    subject: str,
    html_body: str,
    text_body: str,
    unsubscribe: str,
    list_unsubscribe: str,
) -> dict[str, Any]:
    return {
        "from": from_address,
        "to": [to_email],
        "subject": subject,
        "html": html_body.replace(UNSUBSCRIBE_PLACEHOLDER, unsubscribe),
        "text": text_body.replace(UNSUBSCRIBE_PLACEHOLDER, unsubscribe),
        "headers": list_unsubscribe_headers(list_unsubscribe),
    }


Reload = Callable[[str], dict[str, Any] | None]


def deliver_issue(
    *,
    issue_slug: str,
    subject: str,
    html_body: str,
    text_body: str,
    subscriber_ids: list[str],
    reload: Reload,
    secret: str,
    functions_base: str,
    from_address: str,
    already_logged: set[str],
    dry_run: bool,
    site_url: str = "",
    post: Callable[..., dict] | None = None,
    api_key: str = "",
) -> list[dict[str, Any]]:
    """Send, or record a dry run, after re-reading each subscriber.

    ``reload`` is called inside the loop so a bounce that lands between
    selection and delivery is suppressed.
    """
    results: list[dict[str, Any]] = []
    for subscriber_id in subscriber_ids:
        current = reload(subscriber_id)
        if current is None:
            results.append(
                {
                    "idempotency_key": idempotency_key(issue_slug, subscriber_id),
                    "action": "suppress",
                    "subscriber_status": None,
                }
            )
            continue
        plan = plan_recipient(
            issue_slug=issue_slug,
            subscriber=current,
            secret=secret,
            functions_base=functions_base,
            already_logged=already_logged,
            site_url=site_url,
        )
        if plan["action"] != "send":
            results.append(plan)
            continue
        record = {
            "idempotency_key": plan["idempotency_key"],
            "action": "dry_run" if dry_run else "sent",
            "subscriber_status": "active",
            "email": plan["email"],
            "unsubscribe_url": plan["unsubscribe_url"],
            "headers": plan["headers"],
        }
        if dry_run:
            already_logged.add(plan["idempotency_key"])
            results.append(record)
            continue
        if post is None or not api_key or not from_address:
            raise RuntimeError("Resend is not configured. Nothing was sent.")
        payload = resend_email_payload(
            from_address=from_address,
            to_email=plan["email"],
            subject=subject,
            html_body=html_body,
            text_body=text_body,
            unsubscribe=plan["unsubscribe_url"],
            list_unsubscribe=plan["list_unsubscribe_url"],
        )
        response = post(
            "https://api.resend.com/emails",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                "Idempotency-Key": plan["idempotency_key"],
            },
            json=payload,
        )
        record["provider_id"] = response.get("id")
        already_logged.add(plan["idempotency_key"])
        results.append(record)
    return results


def svix_secret_bytes(secret: str) -> bytes:
    part = secret[6:] if secret.startswith("whsec_") else secret
    padding = "=" * (-len(part) % 4)
    return base64.b64decode(part + padding)


def sign_svix(*, secret: str, svix_id: str, timestamp: str, body: bytes) -> str:
    signed = f"{svix_id}.{timestamp}.".encode("ascii") + body
    digest = hmac.new(svix_secret_bytes(secret), signed, hashlib.sha256).digest()
    return "v1," + base64.b64encode(digest).decode("ascii")


def verify_svix(
    *,
    secret: str,
    body: bytes,
    svix_id: str,
    svix_timestamp: str,
    svix_signature: str,
    now: float | None = None,
    tolerance: int = SVIX_TOLERANCE_SECONDS,
) -> bool:
    if not secret or not svix_id or not svix_timestamp or not svix_signature:
        return False
    try:
        stamp = int(svix_timestamp)
    except ValueError:
        return False
    current = time.time() if now is None else now
    if abs(current - stamp) > tolerance:
        return False
    expected = sign_svix(secret=secret, svix_id=svix_id, timestamp=svix_timestamp, body=body)
    for presented in svix_signature.split():
        if hmac.compare_digest(expected, presented):
            return True
    return False


def suppression_from_resend_event(event: dict[str, Any]) -> dict[str, str] | None:
    status = {"email.bounced": "bounced", "email.complained": "complained"}.get(str(event.get("type") or ""))
    if not status:
        return None
    data = event.get("data") or {}
    recipients = data.get("to") or []
    if isinstance(recipients, str):
        recipients = [recipients]
    if not recipients:
        return None
    email = normalize_email(str(recipients[0]))
    if not email:
        return None
    return {"email": email, "status": status}


def one_click_body(raw: str) -> bool:
    return "List-Unsubscribe=One-Click" in (raw or "")


def _b64encode(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def _b64decode(value: str) -> bytes:
    padding = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode(value + padding)
