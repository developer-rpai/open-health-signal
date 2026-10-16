"""HTTP behavior for subscribe, confirm, unsubscribe, contact, and the Resend webhook.

The Supabase edge functions and ``python -m inflammon.local_functions`` both
follow this contract. The in-memory store is what the tests and the local
dry-run server use. Production rows live in Postgres.
"""

from __future__ import annotations

import json
import time
from copy import deepcopy
from typing import Any
from urllib.parse import parse_qs

from inflammon.mailing import (
    INTEREST_TYPES,
    confirm_token_matches,
    deliver_issue,
    hash_confirm_token,
    new_confirm_token,
    normalize_email,
    one_click_body,
    sign_unsubscribe_token,
    suppression_from_resend_event,
    valid_email,
    verify_svix,
    verify_unsubscribe_token,
)

CONTACT_LIMIT = 5
CONTACT_WINDOW_SECONDS = 3600


class ListStore:
    """Small subscriber book. ``reload_subscriber`` re-reads so sends see the latest status."""

    def __init__(self, seed: dict[str, Any] | None = None) -> None:
        self.data: dict[str, Any] = seed or {
            "subscribers": [],
            "sends": [],
            "contact_requests": [],
            "issues": [],
            "allowlist": ["owner@example.com"],
            "rate": {},
        }

    def reload_subscriber(self, subscriber_id: str) -> dict[str, Any] | None:
        for row in self.data["subscribers"]:
            if row["id"] == subscriber_id:
                return deepcopy(row)
        return None

    def by_email(self, email: str) -> dict[str, Any] | None:
        normalized = normalize_email(email)
        for row in self.data["subscribers"]:
            if row["email"] == normalized:
                return row
        return None

    def by_confirm_hash(self, token_hash: str) -> dict[str, Any] | None:
        for row in self.data["subscribers"]:
            if row.get("confirm_token_hash") == token_hash:
                return row
        return None

    def logged_keys(self) -> set[str]:
        return {row["idempotency_key"] for row in self.data["sends"] if row.get("status") in {"sent", "dry_run"}}


def handle_request(
    method: str,
    path: str,
    *,
    query: dict[str, str] | None = None,
    headers: dict[str, str] | None = None,
    body: bytes = b"",
    store: ListStore,
    secret: str,
    functions_base: str,
    site_url: str,
    from_address: str = "",
    api_key: str = "",
    webhook_secret: str = "",
    turnstile_secret: str = "",
    owner_email: str = "owner@example.com",
    dry_run: bool = True,
    expose_preview: bool = False,
    now: float | None = None,
    client_ip: str = "127.0.0.1",
    post=None,
    verify_turnstile=None,
) -> tuple[int, str, str]:
    """Return status, content type, and body."""
    query = query or {}
    headers = {key.lower(): value for key, value in (headers or {}).items()}
    method = method.upper()
    path = path.rstrip("/") or "/"
    if method == "OPTIONS":
        return 204, "text/plain", ""

    if path == "/subscribe" and method == "POST":
        return _subscribe(
            _fields(body, headers),
            store=store,
            secret=secret,
            site_url=site_url,
            from_address=from_address,
            api_key=api_key,
            dry_run=dry_run,
            expose_preview=expose_preview,
            client_ip=client_ip,
            post=post,
            now=now,
        )
    if path == "/confirm" and method in {"GET", "POST"}:
        token = query.get("token") or _fields(body, headers).get("token") or ""
        wants_json = "application/json" in headers.get("accept", "")
        return _confirm(
            token,
            store=store,
            secret=secret,
            expose_preview=expose_preview,
            wants_json=wants_json,
            now=now,
        )
    if path == "/unsubscribe" and method == "GET":
        return _unsubscribe_get(query.get("token") or "", secret=secret, store=store)
    if path == "/unsubscribe" and method == "POST":
        return _unsubscribe_post(
            query.get("token") or "",
            body=body,
            secret=secret,
            store=store,
            now=now,
        )
    if path == "/resend-webhook" and method == "POST":
        return _webhook(body, headers=headers, store=store, webhook_secret=webhook_secret, now=now)
    if path == "/contact" and method == "POST":
        return _contact(
            _fields(body, headers),
            store=store,
            client_ip=client_ip,
            turnstile_secret=turnstile_secret,
            owner_email=owner_email,
            from_address=from_address,
            api_key=api_key,
            dry_run=dry_run,
            now=now,
            post=post,
            verify_turnstile=verify_turnstile,
        )
    if path == "/auth/magic-link" and method == "POST":
        return _magic_link(_fields(body, headers), store=store, dry_run=dry_run)
    if path == "/issues" and method == "GET":
        return _json(200, {"issues": store.data["issues"]})
    if path.startswith("/issues/") and path.endswith("/approve") and method == "POST":
        slug = path[len("/issues/") : -len("/approve")].strip("/")
        return _approve(
            slug,
            store=store,
            secret=secret,
            functions_base=functions_base,
            site_url=site_url,
            from_address=from_address,
            api_key=api_key,
            dry_run=dry_run,
            post=post,
            now=now,
        )
    return _json(404, {"ok": False, "error": "not_found"})


def _subscribe(fields, **kwargs) -> tuple[int, str, str]:
    store: ListStore = kwargs["store"]
    if str(fields.get("consent") or "").strip().lower() not in {"on", "yes", "true", "1"}:
        return _json(400, {"ok": False, "error": "consent_required", "message": "Check the consent box before subscribing."})
    email = normalize_email(str(fields.get("email") or ""))
    if not valid_email(email):
        return _json(400, {"ok": False, "error": "email_required", "message": "Enter an email address."})
    existing = store.by_email(email)
    if existing and existing["status"] in {"bounced", "complained"}:
        return _json(
            409,
            {
                "ok": False,
                "error": "suppressed",
                "message": "This address is suppressed after a bounce or a complaint. It is not added again from the form.",
            },
        )
    if existing and existing["status"] == "active":
        return _json(200, {"ok": True, "status": "active", "message": "This address is already confirmed."})
    token = new_confirm_token()
    now_iso = _iso(kwargs["now"])
    if existing:
        existing["status"] = "pending"
        existing["confirm_token_hash"] = hash_confirm_token(token)
        existing["consent_at"] = now_iso
        existing["consent_ip"] = kwargs["client_ip"]
        existing["confirm_sent_at"] = now_iso
    else:
        store.data["subscribers"].append(
            {
                "id": f"sub_{len(store.data['subscribers']) + 1}",
                "email": email,
                "status": "pending",
                "consent_at": now_iso,
                "consent_ip": kwargs["client_ip"],
                "confirm_token_hash": hash_confirm_token(token),
                "confirm_sent_at": now_iso,
                "confirmed_at": None,
                "unsubscribed_at": None,
            }
        )
    confirm_link = f"{kwargs['site_url'].rstrip('/')}/confirm?token={token}"
    _maybe_send_confirm(
        email=email,
        link=confirm_link,
        from_address=kwargs["from_address"],
        api_key=kwargs["api_key"],
        dry_run=kwargs["dry_run"],
        post=kwargs["post"],
    )
    payload: dict[str, Any] = {
        "ok": True,
        "status": "pending",
        "message": "Check your inbox. The briefing starts after you open the confirmation link.",
    }
    if kwargs["expose_preview"]:
        payload["confirm_url"] = confirm_link
    return _json(200, payload)


def _confirm(token: str, **kwargs) -> tuple[int, str, str]:
    store: ListStore = kwargs["store"]
    row = store.by_confirm_hash(hash_confirm_token(token)) if token else None
    if row is None or not confirm_token_matches(token, row.get("confirm_token_hash") or ""):
        message = "This confirmation link does not match. Subscribe again from the dashboard."
        if kwargs["wants_json"]:
            return _json(400, {"ok": False, "error": "invalid_token", "message": message})
        return _page(400, "Link not valid", message)
    if row["status"] in {"bounced", "complained"}:
        message = "This address was suppressed after a bounce or a complaint."
        if kwargs["wants_json"]:
            return _json(409, {"ok": False, "error": "suppressed", "message": message})
        return _page(409, "Address suppressed", message)
    message = "You are confirmed. The next briefing goes out after the Monday draft is approved."
    if row["status"] != "active":
        row["status"] = "active"
        row["confirmed_at"] = _iso(kwargs["now"])
    # The hash stays until unsubscribe so a duplicate confirm (strict-mode double fetch) still matches.
    if kwargs["wants_json"]:
        payload: dict[str, Any] = {"ok": True, "status": "active", "message": message}
        if kwargs["expose_preview"]:
            payload["unsubscribe_token"] = sign_unsubscribe_token(row["id"], row["email"], kwargs["secret"])
        return _json(200, payload)
    return _page(200, "You are confirmed", message)


def _unsubscribe_get(token: str, *, secret: str, store: ListStore) -> tuple[int, str, str]:
    claims = verify_unsubscribe_token(token, secret)
    if claims is None:
        return _page(400, "Link not valid", "This unsubscribe link is not signed for this list.")
    row = store.reload_subscriber(claims["sid"])
    if row is None or row["email"] != claims["email"]:
        return _page(400, "Link not valid", "This unsubscribe link does not match a subscriber.")
    # GET must not change status. RFC 8058 one-click is the POST.
    return _page(
        200,
        "Confirm unsubscribe",
        f"{row['email']} is still {row['status']}. Submit the form on this page to unsubscribe. It takes effect immediately.",
    )


def _unsubscribe_post(token: str, *, body: bytes, secret: str, store: ListStore, now: float | None) -> tuple[int, str, str]:
    claims = verify_unsubscribe_token(token, secret)
    if claims is None:
        return _json(400, {"ok": False, "error": "invalid_token", "message": "This unsubscribe link is not signed for this list."})
    raw = body.decode("utf-8", errors="replace")
    if not one_click_body(raw):
        return _json(400, {"ok": False, "error": "one_click_required", "message": "POST List-Unsubscribe=One-Click to unsubscribe."})
    row = None
    for item in store.data["subscribers"]:
        if item["id"] == claims["sid"] and item["email"] == claims["email"]:
            row = item
            break
    if row is None:
        return _json(400, {"ok": False, "error": "unknown_subscriber"})
    row["status"] = "unsubscribed"
    row["unsubscribed_at"] = _iso(now)
    row["confirm_token_hash"] = None
    return _json(
        200,
        {
            "ok": True,
            "status": "unsubscribed",
            "message": f"{row['email']} is unsubscribed. This took effect immediately.",
        },
    )


def _webhook(body: bytes, *, headers: dict[str, str], store: ListStore, webhook_secret: str, now: float | None) -> tuple[int, str, str]:
    ok = verify_svix(
        secret=webhook_secret,
        body=body,
        svix_id=headers.get("svix-id", ""),
        svix_timestamp=headers.get("svix-timestamp", ""),
        svix_signature=headers.get("svix-signature", ""),
        now=now,
    )
    if not ok:
        return _json(401, {"ok": False, "error": "invalid_signature"})
    try:
        event = json.loads(body.decode("utf-8") or "{}")
    except json.JSONDecodeError:
        return _json(400, {"ok": False, "error": "invalid_json"})
    change = suppression_from_resend_event(event)
    if change is None:
        return _json(200, {"ok": True, "suppressed": False})
    row = store.by_email(change["email"])
    if row is None:
        return _json(200, {"ok": True, "suppressed": False, "reason": "unknown_subscriber"})
    row["status"] = change["status"]
    return _json(200, {"ok": True, "suppressed": True, "status": change["status"], "email": change["email"]})


def _contact(fields, **kwargs) -> tuple[int, str, str]:
    store: ListStore = kwargs["store"]
    name = str(fields.get("name") or "").strip()
    email = normalize_email(str(fields.get("email") or ""))
    organization = str(fields.get("organization") or "").strip()
    role = str(fields.get("role") or "").strip()
    interest = str(fields.get("interest_type") or "").strip()
    message = str(fields.get("message") or "").strip()
    link = str(fields.get("link") or "").strip()
    token = str(fields.get("turnstile_token") or "").strip()
    if not name or not valid_email(email) or not organization or not role or not message:
        return _json(400, {"ok": False, "error": "missing_fields", "message": "Name, email, organization, role, and a message are required."})
    if interest not in INTEREST_TYPES:
        return _json(400, {"ok": False, "error": "interest_type", "message": "Choose an interest type."})
    if link and not (link.startswith("https://") or link.startswith("http://")):
        return _json(400, {"ok": False, "error": "link", "message": "The link must start with http:// or https://."})
    checker = kwargs["verify_turnstile"] or _default_turnstile
    if not checker(token, kwargs["turnstile_secret"], kwargs["post"]):
        return _json(400, {"ok": False, "error": "turnstile", "message": "The Turnstile check did not pass."})
    if not _rate_allow(store, kwargs["client_ip"], kwargs["now"]):
        return _json(429, {"ok": False, "error": "rate_limited", "message": "Too many messages from this network. Try again later."})
    request_id = f"req_{len(store.data['contact_requests']) + 1}"
    store.data["contact_requests"].append(
        {
            "id": request_id,
            "name": name,
            "email": email,
            "organization": organization,
            "role": role,
            "interest_type": interest,
            "message": message,
            "link": link or None,
            "status": "new",
            "notes": None,
            "created_at": _iso(kwargs["now"]),
        }
    )
    _notify_owner(
        owner_email=kwargs["owner_email"],
        from_address=kwargs["from_address"],
        api_key=kwargs["api_key"],
        dry_run=kwargs["dry_run"],
        post=kwargs["post"],
        summary=f"{name} ({email}) · {interest}",
    )
    message = (
        "Message received. This dry run did not email the owner."
        if kwargs["dry_run"]
        else "Message received. The owner is notified by email."
    )
    return _json(200, {"ok": True, "id": request_id, "message": message})


def _magic_link(fields, *, store: ListStore, dry_run: bool) -> tuple[int, str, str]:
    email = normalize_email(str(fields.get("email") or ""))
    if not valid_email(email):
        return _json(400, {"ok": False, "error": "email_required"})
    allowlist = {normalize_email(item) for item in store.data.get("allowlist") or []}
    if email not in allowlist:
        return _json(403, {"ok": False, "error": "not_allowlisted", "message": "This email is not on the owner allowlist."})
    return _json(
        200,
        {
            "ok": True,
            "allowlisted": True,
            "dry_run": dry_run,
            "message": "Local preview: no magic-link email was sent. Continue as this owner.",
        },
    )


def _approve(slug: str, **kwargs) -> tuple[int, str, str]:
    store: ListStore = kwargs["store"]
    issue = next((item for item in store.data["issues"] if item.get("slug") == slug), None)
    if issue is None:
        return _json(404, {"ok": False, "error": "not_found"})
    issue["status"] = "approved"
    issue["approved_at"] = _iso(kwargs["now"])
    ids = [row["id"] for row in store.data["subscribers"]]
    try:
        results = deliver_issue(
            issue_slug=slug,
            subject=issue.get("subject") or slug,
            html_body=issue.get("html") or "",
            text_body=issue.get("text_body") or "",
            subscriber_ids=ids,
            reload=store.reload_subscriber,
            secret=kwargs["secret"],
            functions_base=kwargs["functions_base"],
            from_address=kwargs["from_address"],
            already_logged=store.logged_keys(),
            dry_run=kwargs["dry_run"] or not kwargs["api_key"],
            site_url=kwargs.get("site_url") or "",
            post=kwargs["post"],
            api_key=kwargs["api_key"],
        )
    except RuntimeError as exc:
        return _json(500, {"ok": False, "error": "send_failed", "message": str(exc)})
    for result in results:
        if result["action"] in {"dry_run", "sent", "suppress"}:
            store.data["sends"].append(
                {
                    "issue_slug": slug,
                    "subscriber_id": result["idempotency_key"].split(":", 1)[-1],
                    "idempotency_key": result["idempotency_key"],
                    "status": "suppressed" if result["action"] == "suppress" else result["action"],
                    "provider_id": result.get("provider_id"),
                }
            )
    if any(item["action"] == "sent" for item in results):
        issue["status"] = "sent"
    return _json(200, {"ok": True, "status": issue["status"], "delivery": results, "sent": any(item["action"] == "sent" for item in results)})


def _maybe_send_confirm(*, email: str, link: str, from_address: str, api_key: str, dry_run: bool, post) -> None:
    if dry_run or not api_key or not from_address or post is None:
        return
    post(
        "https://api.resend.com/emails",
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        json={
            "from": from_address,
            "to": [email],
            "subject": "Confirm your Inflammation Signal Monitor briefing",
            "text": (
                "Confirm this address to receive the weekly briefing.\n\n"
                f"{link}\n\n"
                "If you did not ask for this, ignore the message. You will not be added until you open the link."
            ),
        },
    )


def _notify_owner(*, owner_email: str, from_address: str, api_key: str, dry_run: bool, post, summary: str) -> None:
    if dry_run or not api_key or not from_address or not owner_email or post is None:
        return
    post(
        "https://api.resend.com/emails",
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        json={
            "from": from_address,
            "to": [owner_email],
            "subject": "New collaboration message",
            "text": summary,
        },
    )


def _default_turnstile(token: str, secret: str, post) -> bool:
    if not token or not secret:
        return False
    # Cloudflare's published test secret passes any non-empty token when the
    # siteverify call is skipped because this process has no network client.
    if secret == "1x0000000000000000000000000000000AA" and post is None:
        return True
    if post is None:
        return False
    result = post(
        "https://challenges.cloudflare.com/turnstile/v0/siteverify",
        headers={"Content-Type": "application/json"},
        json={"secret": secret, "response": token},
    )
    return bool(result.get("success"))


def _rate_allow(store: ListStore, ip: str, now: float | None) -> bool:
    current = time.time() if now is None else now
    bucket = store.data["rate"].get(ip)
    if bucket is None or current - bucket["start"] >= CONTACT_WINDOW_SECONDS:
        store.data["rate"][ip] = {"start": current, "hits": 1}
        return True
    if bucket["hits"] >= CONTACT_LIMIT:
        return False
    bucket["hits"] += 1
    return True


def _fields(body: bytes, headers: dict[str, str]) -> dict[str, str]:
    raw = body.decode("utf-8", errors="replace")
    content_type = headers.get("content-type", "")
    if "application/json" in content_type:
        try:
            payload = json.loads(raw or "{}")
        except json.JSONDecodeError:
            return {}
        return {key: "" if value is None else str(value) for key, value in payload.items()}
    parsed = parse_qs(raw, keep_blank_values=True)
    return {key: values[-1] for key, values in parsed.items()}


def _json(status: int, payload: dict) -> tuple[int, str, str]:
    return status, "application/json", json.dumps(payload)


def _page(status: int, title: str, message: str) -> tuple[int, str, str]:
    import html as html_lib

    safe_title = html_lib.escape(title)
    safe_message = html_lib.escape(message)
    document = f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8"><title>{safe_title}</title></head>
<body><main><h1>{safe_title}</h1><p>{safe_message}</p></main></body></html>"""
    return status, "text/html; charset=utf-8", document


def _iso(now: float | None) -> str:
    stamp = time.time() if now is None else now
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(stamp))
