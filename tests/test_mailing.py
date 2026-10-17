"""Token signing, send-time suppression, and Resend webhook verification."""

from __future__ import annotations

import json
import logging
import subprocess
from pathlib import Path

from inflammon.list_api import CONFIRM_EMAIL_LIMIT, ListStore, handle_request
from inflammon.transactional import (
    confirmation_email,
    contact_ack_email,
    contact_from,
    env_is_dry_run,
    excerpt as py_excerpt,
    list_from,
    mask_recipient,
    owner_notify_email,
    welcome_email,
)
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
    confirms = [item for item in store.data["mail"] if item["kind"] == "confirm"]
    welcomes = [item for item in store.data["mail"] if item["kind"] == "welcome"]
    assert len(confirms) == 2
    assert token in confirms[1]["text"]
    assert len(welcomes) == 1
    assert welcomes[0]["text"].lower().count("not medical advice") == 1
    assert welcomes[0]["reply_to"] == "contact@openhealthsignals.org"


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


def test_pending_confirmation_resends_until_the_hourly_cap():
    store = ListStore()
    sent: list[dict] = []

    def post(url, *, headers, json):
        sent.append(json)
        return {"id": "email_1"}

    hashes = []
    for _ in range(CONFIRM_EMAIL_LIMIT):
        status, _, body = _live(store, "POST", "/subscribe", body={"email": "again@example.com", "consent": "yes"}, post=post)
        assert status == 200
        hashes.append(store.by_email("again@example.com")["confirm_token_hash"])
    assert len(sent) == CONFIRM_EMAIL_LIMIT
    assert len(set(hashes)) == CONFIRM_EMAIL_LIMIT
    assert sent[0]["subject"] == "Confirm your Open Health Signals briefing"
    assert sent[0]["reply_to"] == "contact@openhealthsignals.org"
    assert "<html" in sent[0]["html"].lower() or "<!DOCTYPE html>" in sent[0]["html"]
    capped, _, capped_body = _live(
        store, "POST", "/subscribe", body={"email": "again@example.com", "consent": "yes"}, post=post
    )
    assert capped == 200
    assert json.loads(capped_body)["status"] == "already_pending"
    assert "Check your inbox" in capped_body
    assert len(sent) == CONFIRM_EMAIL_LIMIT
    assert store.by_email("again@example.com")["confirm_token_hash"] == hashes[-1]


def test_confirm_sends_one_welcome_with_unsubscribe_and_optional_postal():
    store = ListStore()
    sent: list[dict] = []

    def post(url, *, headers, json):
        sent.append(json)
        return {"id": "email_1"}

    created, _, created_body = _live(
        store,
        "POST",
        "/subscribe",
        body={"email": "reader@example.com", "consent": "yes"},
        post=post,
        postal="PO Box 1, San Jose, CA 95113",
    )
    assert created == 200
    token = json.loads(created_body)["confirm_url"].split("token=", 1)[1]
    confirmed, _, _ = _live(
        store,
        "POST",
        "/confirm",
        query={"token": token},
        headers={"accept": "application/json"},
        post=post,
        postal="PO Box 1, San Jose, CA 95113",
    )
    assert confirmed == 200
    again, _, _ = _live(
        store,
        "POST",
        "/confirm",
        query={"token": token},
        headers={"accept": "application/json"},
        post=post,
        postal="PO Box 1, San Jose, CA 95113",
    )
    assert again == 200
    welcomes = [item for item in sent if item["subject"].startswith("You're on the")]
    assert len(welcomes) == 1
    welcome = welcomes[0]
    assert welcome["reply_to"] == "contact@openhealthsignals.org"
    assert welcome["text"].lower().count("not medical advice") == 1
    assert "about once a week" in welcome["text"].lower()
    assert "FAERS" in welcome["text"]
    assert "PO Box 1, San Jose, CA 95113" in welcome["text"]
    assert "PO Box 1, San Jose, CA 95113" in welcome["html"]
    assert "causes" not in welcome["text"].lower()
    assert welcome["headers"]["List-Unsubscribe-Post"] == "List-Unsubscribe=One-Click"
    assert welcome["headers"]["List-Unsubscribe"].startswith(f"<{BASE}/unsubscribe?token=")
    assert f"{BASE.replace('43124', '43123')}/unsubscribe?token=" in welcome["text"]

    bare = ListStore()
    bare_sent: list[dict] = []

    def bare_post(url, *, headers, json):
        bare_sent.append(json)
        return {"id": "email_2"}

    _, _, bare_body = _live(bare, "POST", "/subscribe", body={"email": "bare@example.com", "consent": "yes"}, post=bare_post, postal="")
    bare_token = json.loads(bare_body)["confirm_url"].split("token=", 1)[1]
    _live(
        bare,
        "POST",
        "/confirm",
        query={"token": bare_token},
        headers={"accept": "application/json"},
        post=bare_post,
        postal="",
    )
    bare_welcome = next(item for item in bare_sent if "not medical advice" in item["text"])
    assert "San Jose" not in bare_welcome["text"]
    assert "#5c564c" not in bare_welcome["html"]


def test_contact_mail_is_best_effort_and_dry_run_only_logs(caplog):
    store = ListStore()
    sent: list[dict] = []

    def post(url, *, headers, json):
        sent.append(json)
        return {"id": "email_1"}

    status, _, body = _live(
        store,
        "POST",
        "/contact",
        body={
            "name": "Ada",
            "email": "ada@example.com",
            "organization": "Clinic",
            "role": "Researcher",
            "interest_type": "media",
            "message": "First line of the note\nSecond line\nThird\nFourth should stay in the owner copy only",
            "link": "https://example.com/paper",
            "turnstile_token": "local-pass",
        },
        post=post,
        from_address="Open Health Signals <briefing@openhealthsignals.org>",
    )
    assert status == 200
    assert "Message received." in body
    assert len(sent) == 2
    ack, owner = sent
    assert ack["to"] == ["ada@example.com"]
    assert ack["from"] == "Open Health Signals <contact@openhealthsignals.org>"
    assert ack["reply_to"] == "contact@openhealthsignals.org"
    assert ack["text"].startswith("Thanks, we got your message and will reply within a few days.")
    assert "First line of the note" in ack["text"]
    assert "Fourth should stay" not in ack["text"]
    assert owner["to"] == ["rakeshpai@openhealthsignals.org"]
    assert owner["reply_to"] == "ada@example.com"
    assert "Fourth should stay in the owner copy only" in owner["text"]
    assert "https://example.com/paper" in owner["text"]
    assert owner["from"] == ack["from"]

    broken = ListStore()

    def explode(url, *, headers, json):
        raise RuntimeError("resend down")

    failed, _, failed_body = _live(
        broken,
        "POST",
        "/contact",
        body={
            "name": "Ada",
            "email": "ada@example.com",
            "interest_type": "media",
            "message": "Still store this.",
            "turnstile_token": "local-pass",
        },
        post=explode,
    )
    assert failed == 200
    assert "Message received." in failed_body
    assert broken.data["contact_requests"][0]["message"] == "Still store this."
    assert all(item.get("error") == "send_failed" for item in broken.data["mail"])

    quiet = ListStore()
    called = []

    def unexpected(url, *, headers, json):
        called.append(url)
        return {}

    with caplog.at_level(logging.INFO, logger="inflammon.transactional"):
        dry, _, _ = _live(
            quiet,
            "POST",
            "/subscribe",
            body={"email": "dry@example.com", "consent": "yes"},
            post=unexpected,
            dry_run=True,
        )
    assert dry == 200
    assert called == []
    assert any(
        "dry_run" in record.message
        and "d***@example.com" in record.message
        and "dry@example.com" not in record.message
        and "Confirm your Open Health Signals briefing" in record.message
        for record in caplog.records
    )


def test_dry_run_is_live_only_for_exact_zero(monkeypatch):
    monkeypatch.setenv("NEWSLETTER_DRY_RUN", "0")
    assert env_is_dry_run() is False
    for value in ("", "1", "false", "no", "0 ", "00", "true"):
        monkeypatch.setenv("NEWSLETTER_DRY_RUN", value)
        assert env_is_dry_run() is True
    monkeypatch.delenv("NEWSLETTER_DRY_RUN", raising=False)
    assert env_is_dry_run() is True
    assert mask_recipient("jane@example.com") == "j***@example.com"
    assert mask_recipient("J@domain.test") == "J***@domain.test"
    assert mask_recipient("not-an-email") == "***"


def test_transactional_copy_matches_the_edge_module():
    script = r"""
import { confirmationEmail, welcomeEmail, contactAckEmail, ownerNotifyEmail, contactFrom, listFrom, excerpt } from "./supabase/functions/_shared/transactional.js";
const pick = (mail) => ({ subject: mail.subject, text: mail.text, html: mail.html, replyTo: mail.replyTo, headers: mail.headers });
const long = "word ".repeat(80);
console.log(JSON.stringify({
  confirm: pick(confirmationEmail({ confirmUrl: "https://openhealthsignals.org/confirm?token=abc" })),
  welcome: pick(welcomeEmail({
    unsubscribeUrl: "https://openhealthsignals.org/unsubscribe?token=abc",
    listUnsubscribeUrl: "https://fn.example/unsubscribe?token=abc",
    postalAddress: "PO Box 1, San Jose, CA",
  })),
  welcomeBare: pick(welcomeEmail({
    unsubscribeUrl: "https://openhealthsignals.org/unsubscribe?token=abc",
    listUnsubscribeUrl: "https://fn.example/unsubscribe?token=abc",
    postalAddress: "  ",
  })),
  ack: pick(contactAckEmail({ interestLabel: "Media", excerpt: "First line\nSecond line" })),
  owner: pick(ownerNotifyEmail({
    name: "Ada Lovelace",
    email: "ada@example.com",
    organization: "Clinic",
    role: "Researcher",
    interestLabel: "Media",
    message: "Full <note>",
    link: "https://example.com/paper",
  })),
  fromSame: contactFrom("Open Health Signals <briefing@openhealthsignals.org>"),
  fromOther: contactFrom("Ops <onboarding@resend.dev>"),
  fromEmpty: listFrom(""),
  excerpt: excerpt(long),
}));
"""
    completed = subprocess.run(
        ["node", "--input-type=module", "-e", script],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    edge = json.loads(completed.stdout)
    pairs = {
        "confirm": confirmation_email(confirm_url="https://openhealthsignals.org/confirm?token=abc"),
        "welcome": welcome_email(
            unsubscribe_url="https://openhealthsignals.org/unsubscribe?token=abc",
            list_unsubscribe_url="https://fn.example/unsubscribe?token=abc",
            postal_address="PO Box 1, San Jose, CA",
        ),
        "welcomeBare": welcome_email(
            unsubscribe_url="https://openhealthsignals.org/unsubscribe?token=abc",
            list_unsubscribe_url="https://fn.example/unsubscribe?token=abc",
            postal_address="  ",
        ),
        "ack": contact_ack_email(interest_label="Media", excerpt_text="First line\nSecond line"),
        "owner": owner_notify_email(
            name="Ada Lovelace",
            email="ada@example.com",
            organization="Clinic",
            role="Researcher",
            interest_label="Media",
            message="Full <note>",
            link="https://example.com/paper",
        ),
    }
    for key, local in pairs.items():
        assert edge[key]["subject"] == local["subject"]
        assert edge[key]["text"] == local["text"]
        assert edge[key]["html"] == local["html"]
        assert edge[key]["replyTo"] == local["reply_to"]
        assert edge[key]["headers"] == local["headers"]
    assert edge["fromSame"] == contact_from("Open Health Signals <briefing@openhealthsignals.org>")
    assert edge["fromOther"] == contact_from("Ops <onboarding@resend.dev>")
    assert edge["fromEmpty"] == list_from("")
    assert edge["excerpt"] == py_excerpt("word " * 80)
    assert "&lt;note&gt;" in pairs["owner"]["html"]
    assert "<note>" not in pairs["owner"]["html"]


def _live(store, method, path, *, post, body=None, query=None, headers=None, postal="", dry_run=False, from_address="Open Health Signals <briefing@openhealthsignals.org>"):
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
        from_address=from_address,
        api_key="re_test",
        turnstile_secret="1x0000000000000000000000000000000AA",
        dry_run=dry_run,
        expose_preview=True,
        now=NOW,
        client_ip="203.0.113.8",
        post=post,
        postal=postal,
        verify_turnstile=lambda token, secret, post: bool(token),
    )


def _capture_post(response: dict):
    def post(url, *, headers, json):
        post.captured = {"url": url, "headers": headers, "json": json}
        return response

    post.captured = {}
    return post
