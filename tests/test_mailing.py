"""Token signing, send-time suppression, and Resend webhook verification."""

from __future__ import annotations

import json
from pathlib import Path

from inflammon.list_api import ListStore, handle_request
from inflammon.mailing import (
    confirm_token_matches,
    deliver_issue,
    hash_confirm_token,
    new_confirm_token,
    plan_recipient,
    sign_unsubscribe_token,
    verify_svix,
    verify_unsubscribe_token,
)

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tests" / "fixtures" / "resend_bounce.json"
SECRET = "test-unsubscribe-secret"
BASE = "http://127.0.0.1:43124"
NOW = 1_710_000_000.0


def _call(store: ListStore, method: str, path: str, *, query=None, body=None, headers=None, webhook_secret=""):
    raw = b""
    hdrs = dict(headers or {})
    if isinstance(body, dict):
        raw = json.dumps(body).encode()
        hdrs.setdefault("content-type", "application/json")
    elif isinstance(body, str):
        raw = body.encode()
    return handle_request(
        method,
        path,
        query=query,
        headers=hdrs,
        body=raw,
        store=store,
        secret=SECRET,
        functions_base=BASE,
        site_url="http://127.0.0.1:43123",
        webhook_secret=webhook_secret,
        turnstile_secret="1x0000000000000000000000000000000AA",
        dry_run=True,
        expose_preview=True,
        now=NOW,
        client_ip="203.0.113.8",
    )


def test_unsubscribe_token_roundtrip_and_tamper():
    token = sign_unsubscribe_token("sub_1", "Reader@Example.com", SECRET)
    assert token == "eyJlbWFpbCI6InJlYWRlckBleGFtcGxlLmNvbSIsInNpZCI6InN1Yl8xIn0.hrcb_1Yw__ILl9FHRZ4uXh6YCLAz8IL5TEWyKlMXSmk"
    assert verify_unsubscribe_token(token, SECRET) == {"sid": "sub_1", "email": "reader@example.com"}
    assert verify_unsubscribe_token(token, "other-secret") is None
    flipped = ("A" if token[-1] != "A" else "B")
    assert verify_unsubscribe_token(token[:-1] + flipped, SECRET) is None


def test_confirm_token_is_stored_as_a_hash():
    token = new_confirm_token()
    hashed = hash_confirm_token(token)
    assert hashed != token
    assert confirm_token_matches(token, hashed)
    assert not confirm_token_matches(token + "x", hashed)


def test_suppression_is_checked_on_the_row_read_at_send_time():
    rows = {
        "sub_1": {"id": "sub_1", "email": "active@example.com", "status": "active"},
        "sub_2": {"id": "sub_2", "email": "pending@example.com", "status": "pending"},
    }

    def reload(subscriber_id: str):
        row = rows.get(subscriber_id)
        return dict(row) if row else None

    rows["sub_1"]["status"] = "bounced"
    results = deliver_issue(
        issue_slug="2026-10-15",
        subject="Briefing",
        html_body="<p>__UNSUBSCRIBE_URL__</p>",
        text_body="__UNSUBSCRIBE_URL__",
        subscriber_ids=["sub_1", "sub_2", "missing"],
        reload=reload,
        secret=SECRET,
        functions_base=BASE,
        from_address="briefing@example.com",
        already_logged=set(),
        dry_run=True,
    )
    assert [item["action"] for item in results] == ["suppress", "suppress", "suppress"]
    assert results[0]["subscriber_status"] == "bounced"
    assert results[1]["subscriber_status"] == "pending"

    rows["sub_1"]["status"] = "active"
    poster = _capture_post({"id": "em_1"})
    sent = deliver_issue(
        issue_slug="2026-10-15",
        subject="Briefing",
        html_body="<p>__UNSUBSCRIBE_URL__</p>",
        text_body="__UNSUBSCRIBE_URL__",
        subscriber_ids=["sub_1"],
        reload=reload,
        secret=SECRET,
        functions_base=BASE,
        from_address="briefing@example.com",
        already_logged=set(),
        dry_run=False,
        site_url="http://127.0.0.1:43123",
        api_key="re_test",
        post=poster,
    )
    assert sent[0]["action"] == "sent"
    assert sent[0]["headers"]["List-Unsubscribe-Post"] == "List-Unsubscribe=One-Click"
    assert sent[0]["headers"]["Idempotency-Key"] == "2026-10-15:sub_1"
    assert sent[0]["headers"]["List-Unsubscribe"].startswith("<http://127.0.0.1:43124/unsubscribe?token=")
    assert "/unsubscribe?token=" in sent[0]["unsubscribe_url"]
    assert poster.captured["headers"]["Idempotency-Key"] == "2026-10-15:sub_1"
    assert poster.captured["json"]["headers"]["List-Unsubscribe-Post"] == "List-Unsubscribe=One-Click"
    assert "__UNSUBSCRIBE_URL__" not in poster.captured["json"]["html"]
    assert poster.captured["json"]["html"].count("http://127.0.0.1:43123/unsubscribe?token=") == 1
    assert poster.captured["json"]["headers"]["List-Unsubscribe"].startswith("<http://127.0.0.1:43124/unsubscribe?token=")


def test_duplicate_idempotency_key_is_not_sent_again():
    subscriber = {"id": "sub_9", "email": "a@example.com", "status": "active"}
    plan = plan_recipient(
        issue_slug="2026-10-15",
        subscriber=subscriber,
        secret=SECRET,
        functions_base=BASE,
        already_logged={"2026-10-15:sub_9"},
    )
    assert plan["action"] == "skip_duplicate"


def test_svix_fixture_accepts_the_real_signature_and_rejects_a_forged_one():
    fixture = json.loads(FIXTURE.read_text(encoding="utf8"))
    body = fixture["body"].encode("utf-8")
    assert verify_svix(
        secret=fixture["secret"],
        body=body,
        svix_id=fixture["svix_id"],
        svix_timestamp=fixture["svix_timestamp"],
        svix_signature=fixture["svix_signature"],
        now=float(fixture["svix_timestamp"]),
    )
    assert not verify_svix(
        secret=fixture["secret"],
        body=body,
        svix_id=fixture["svix_id"],
        svix_timestamp=fixture["svix_timestamp"],
        svix_signature="v1,forged",
        now=float(fixture["svix_timestamp"]),
    )
    assert not verify_svix(
        secret=fixture["secret"],
        body=body,
        svix_id=fixture["svix_id"],
        svix_timestamp=fixture["svix_timestamp"],
        svix_signature=fixture["svix_signature"],
        now=float(fixture["svix_timestamp"]) + 10_000,
    )


def test_webhook_suppresses_a_bounce_and_the_next_send_skips_that_address():
    fixture = json.loads(FIXTURE.read_text(encoding="utf8"))
    store = ListStore(
        {
            "subscribers": [
                {
                    "id": "sub_1",
                    "email": "reader@example.com",
                    "status": "active",
                    "consent_at": "2026-10-01T00:00:00Z",
                    "consent_ip": "203.0.113.8",
                    "confirm_token_hash": None,
                }
            ],
            "sends": [],
            "contact_requests": [],
            "issues": [
                {
                    "slug": "2026-10-15",
                    "subject": "Briefing",
                    "html": "<p>__UNSUBSCRIBE_URL__</p>",
                    "text_body": "__UNSUBSCRIBE_URL__",
                    "status": "draft",
                }
            ],
            "allowlist": ["owner@example.com"],
            "rate": {},
        }
    )
    status, _, raw = _call(
        store,
        "POST",
        "/resend-webhook",
        body=fixture["body"],
        headers={
            "content-type": "application/json",
            "svix-id": fixture["svix_id"],
            "svix-timestamp": fixture["svix_timestamp"],
            "svix-signature": fixture["svix_signature"],
        },
        webhook_secret=fixture["secret"],
    )
    assert status == 200
    assert json.loads(raw)["status"] == "bounced"
    assert store.reload_subscriber("sub_1")["status"] == "bounced"

    forged, _, _ = _call(
        store,
        "POST",
        "/resend-webhook",
        body=fixture["body"],
        headers={
            "svix-id": fixture["svix_id"],
            "svix-timestamp": fixture["svix_timestamp"],
            "svix-signature": "v1,forged",
        },
        webhook_secret=fixture["secret"],
    )
    assert forged == 401

    approved, _, approved_body = _call(store, "POST", "/issues/2026-10-15/approve")
    assert approved == 200
    delivery = json.loads(approved_body)["delivery"]
    assert delivery[0]["action"] == "suppress"
    assert delivery[0]["subscriber_status"] == "bounced"
    assert json.loads(approved_body)["sent"] is False


def test_double_opt_in_and_one_click_unsubscribe_are_immediate():
    store = ListStore()
    denied, _, _ = _call(store, "POST", "/subscribe", body={"email": "person@example.com", "consent": "no"})
    assert denied == 400
    created, _, created_body = _call(store, "POST", "/subscribe", body={"email": "person@example.com", "consent": "yes"})
    assert created == 200
    assert json.loads(created_body)["status"] == "pending"
    again, _, again_body = _call(store, "POST", "/subscribe", body={"email": "person@example.com", "consent": "yes"})
    assert again == 200
    resent = json.loads(again_body)
    assert resent["status"] == "already_pending"
    pending = store.by_email("person@example.com")
    assert pending["status"] == "pending"
    assert pending["consent_ip"] == "203.0.113.8"
    assert pending["confirm_token_hash"]
    # A second request while still pending rotates the confirm token. Confirm with the latest link.
    first_token = json.loads(created_body)["confirm_url"].split("token=", 1)[1]
    token = resent["confirm_url"].split("token=", 1)[1]
    assert token != first_token

    preview, _, _ = _call(store, "GET", "/unsubscribe", query={"token": "not-a-token"})
    assert preview == 400

    confirmed, _, confirmed_body = _call(
        store,
        "POST",
        "/confirm",
        query={"token": token},
        headers={"accept": "application/json"},
    )
    assert confirmed == 200
    assert store.by_email("person@example.com")["status"] == "active"
    active, _, active_body = _call(store, "POST", "/subscribe", body={"email": "person@example.com", "consent": "yes"})
    assert active == 200
    assert json.loads(active_body)["status"] == "active"
    assert "confirm_url" not in json.loads(active_body)
    unsub_token = json.loads(confirmed_body)["unsubscribe_token"]

    peeked, _, peek_body = _call(store, "GET", "/unsubscribe", query={"token": unsub_token})
    assert peeked == 200
    assert "still active" in peek_body
    assert store.by_email("person@example.com")["status"] == "active"

    done, _, done_body = _call(
        store,
        "POST",
        "/unsubscribe",
        query={"token": unsub_token},
        body="List-Unsubscribe=One-Click",
        headers={"content-type": "application/x-www-form-urlencoded"},
    )
    assert done == 200
    assert json.loads(done_body)["status"] == "unsubscribed"
    assert store.by_email("person@example.com")["status"] == "unsubscribed"
    assert store.by_email("person@example.com")["unsubscribed_at"]


def test_contact_requires_turnstile_and_rate_limits():
    store = ListStore()
    missing, _, _ = _call(
        store,
        "POST",
        "/contact",
        body={
            "name": "Ada",
            "email": "ada@example.com",
            "organization": "Clinic",
            "role": "Researcher",
            "interest_type": "research_collaboration",
            "message": "We want to compare methods.",
            "turnstile_token": "",
        },
    )
    assert missing == 400
    for index in range(5):
        status, _, _ = _call(
            store,
            "POST",
            "/contact",
            body={
                "name": "Ada",
                "email": f"ada{index}@example.com",
                "organization": "Clinic",
                "role": "Researcher",
                "interest_type": "code_contribution",
                "message": "Patch for the quarterly loader.",
                "turnstile_token": "local-pass",
            },
        )
        assert status == 200
    blocked, _, blocked_body = _call(
        store,
        "POST",
        "/contact",
        body={
            "name": "Ada",
            "email": "ada6@example.com",
            "organization": "Clinic",
            "role": "Researcher",
            "interest_type": "media",
            "message": "Interview request.",
            "turnstile_token": "local-pass",
        },
    )
    assert blocked == 429
    assert store.data["contact_requests"][0]["status"] == "new"
    assert store.data["contact_requests"][0]["notes"] is None
    assert "rate_limited" in blocked_body


def test_contact_organization_and_role_are_optional():
    store = ListStore()
    status, _, body = _call(
        store,
        "POST",
        "/contact",
        body={
            "name": "Ada",
            "email": "ada@example.com",
            "interest_type": "media",
            "message": "Question about the extract date.",
            "turnstile_token": "local-pass",
        },
    )
    assert status == 200
    saved = store.data["contact_requests"][-1]
    assert saved["organization"] == ""
    assert saved["role"] == ""
    assert "Message received." in body


def _capture_post(response: dict):
    def post(url, *, headers, json):
        post.captured = {"url": url, "headers": headers, "json": json}
        return response

    post.captured = {}
    return post
