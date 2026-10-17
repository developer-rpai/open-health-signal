"""Write an issue archive and, when asked, send it through the configured provider."""

from __future__ import annotations

import json
import os
from pathlib import Path

from inflammon.compliance import postal_address
from inflammon.mailing import UNSUBSCRIBE_PLACEHOLDER, deliver_issue
from inflammon.newsletter.compose import compose_issue, fingerprint, load_snapshot
from inflammon.newsletter.render import render_html, render_text


class NewsletterSendError(RuntimeError):
    """The issue is already on disk. Sending did not happen."""


def build_and_save(
    *,
    snapshot_dir: str | Path = "data/snapshot",
    out_dir: str | Path = "data/newsletter",
    web_data_dir: str | Path = "web/data/newsletter",
    web_email_dir: str | Path = "web/public/newsletter/email",
    site_url: str | None = None,
    send: bool = False,
) -> dict:
    snapshot = load_snapshot(snapshot_dir)
    out = Path(out_dir)
    state_dir = out / "state"
    previous = _read_json(state_dir / "previous.json")
    prior = _read_json(state_dir / "prior.json")
    generated_at = snapshot["manifest"].get("generated_at")
    if previous and previous.get("snapshot_generated_at") == generated_at:
        baseline = prior
    else:
        baseline = previous

    site = (site_url or os.environ.get("SITE_URL") or os.environ.get("NEXT_PUBLIC_SITE_URL") or "http://127.0.0.1:43123").rstrip("/")
    issue = compose_issue(snapshot, baseline, site_url=site)
    archive_unsubscribe = issue.get("unsubscribe_page") or f"{site}/unsubscribe"
    html_template = render_html(issue, unsubscribe_href=UNSUBSCRIBE_PLACEHOLDER)
    text_template = render_text(issue, unsubscribe_href=UNSUBSCRIBE_PLACEHOLDER)
    html_body = html_template.replace(UNSUBSCRIBE_PLACEHOLDER, archive_unsubscribe)
    text_body = text_template.replace(UNSUBSCRIBE_PLACEHOLDER, archive_unsubscribe)
    issue["delivery"] = {"mode": "dry-run", "sent": False, "provider": "resend"}

    slug = issue["slug"]
    issue_dir = out / "issues" / slug
    issue_dir.mkdir(parents=True, exist_ok=True)
    _write_issue_files(issue_dir, issue, html_body, text_body)
    index = _write_index(out / "index.json", issue)
    _sync_web(Path(web_data_dir), Path(web_email_dir), index, issue, html_body)
    _update_fingerprints(state_dir, previous, snapshot, generated_at)
    _upsert_draft(issue, html_body, text_body)

    if send and not _dry_run_forced():
        try:
            delivery = send_resend(issue, html_template, text_template)
        except NewsletterSendError:
            issue["delivery"] = {"mode": "send", "sent": False, "provider": "resend", "error": "send_failed"}
            _write_issue_files(issue_dir, issue, html_body, text_body)
            _sync_web(Path(web_data_dir), Path(web_email_dir), index, issue, html_body)
            raise
        issue["delivery"] = delivery
        if delivery.get("sent"):
            _mark_issue(issue["slug"], "sent")
        _write_issue_files(issue_dir, issue, html_body, text_body)
        index = _write_index(out / "index.json", issue)
        _sync_web(Path(web_data_dir), Path(web_email_dir), index, issue, html_body)

    return {
        "slug": slug,
        "kind": issue["kind"],
        "headline": issue["headline"],
        "provider": "resend",
        "delivery": issue["delivery"],
        "html": str(issue_dir / "issue.html"),
        "text": str(issue_dir / "issue.txt"),
        "archive": issue["archive_path"],
    }


def send_resend(
    issue: dict,
    html_body: str,
    text_body: str,
    *,
    api_key: str | None = None,
    post=None,
    subscribers: list[dict] | None = None,
    reload=None,
    secret: str | None = None,
    functions_base: str | None = None,
    from_address: str | None = None,
) -> dict:
    """Send one Resend email per active subscriber. The archive files are already written."""
    key = api_key if api_key is not None else os.environ.get("RESEND_API_KEY", "").strip()
    sender = from_address if from_address is not None else os.environ.get("NEWSLETTER_FROM", "").strip()
    signing = secret if secret is not None else os.environ.get("UNSUBSCRIBE_HMAC_SECRET", "").strip()
    base = (functions_base if functions_base is not None else os.environ.get("FUNCTIONS_BASE", "")).strip()
    if not key:
        raise NewsletterSendError("RESEND_API_KEY is not set. The issue was written; nothing was sent.")
    if not sender:
        raise NewsletterSendError("NEWSLETTER_FROM is not set. The issue was written; nothing was sent.")
    if not signing:
        raise NewsletterSendError("UNSUBSCRIBE_HMAC_SECRET is not set. The issue was written; nothing was sent.")
    if not base:
        raise NewsletterSendError("FUNCTIONS_BASE is not set. The issue was written; nothing was sent.")
    if not postal_address():
        raise NewsletterSendError(
            "NEWSLETTER_POSTAL_ADDRESS is not set. Live send refused. The issue was written; nothing was sent."
        )
    if subscribers is None:
        rows = _load_subscribers()
        if reload is None:
            reload = _reload_subscriber
    else:
        rows = subscribers
        if reload is None:
            by_id = {str(row["id"]): row for row in rows}

            def reload(subscriber_id: str, _by_id=by_id):
                current = _by_id.get(str(subscriber_id))
                return dict(current) if current else None

    results = deliver_issue(
        issue_slug=issue["slug"],
        subject=issue["subject"],
        html_body=html_body,
        text_body=text_body,
        subscriber_ids=[str(row["id"]) for row in rows],
        reload=reload,
        secret=signing,
        functions_base=base,
        from_address=sender,
        already_logged=set(),
        dry_run=False,
        site_url=issue.get("site_url") or os.environ.get("SITE_URL", ""),
        post=post or _post,
        api_key=key,
    )
    sent = [item for item in results if item["action"] == "sent"]
    return {
        "mode": "send",
        "sent": True,
        "provider": "resend",
        "recipient_count": len(sent),
        "suppressed": sum(1 for item in results if item["action"] == "suppress"),
        "ids": [item.get("provider_id") for item in sent],
    }


def _supabase() -> tuple[str, str]:
    url = os.environ.get("SUPABASE_URL", "").strip().rstrip("/")
    service = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "").strip()
    if not url or not service:
        raise NewsletterSendError(
            "SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY are not set. The issue was written; nothing was sent."
        )
    return url, service


def _load_subscribers() -> list[dict]:
    url, service = _supabase()
    payload = _supabase_get(url, service, {"select": "id,email,status"})
    if not isinstance(payload, list):
        raise NewsletterSendError("Supabase did not return a subscriber list. The issue was written; nothing was sent.")
    return payload


def _reload_subscriber(subscriber_id: str) -> dict | None:
    """Read one row at send time so a bounce that arrived after the list was built is honored."""
    url, service = _supabase()
    payload = _supabase_get(url, service, {"select": "id,email,status", "id": f"eq.{subscriber_id}"})
    if isinstance(payload, list) and payload:
        return payload[0]
    return None


def _supabase_get(url: str, service: str, params: dict) -> object:
    import httpx

    response = httpx.get(
        f"{url}/rest/v1/subscribers",
        params=params,
        headers={"apikey": service, "Authorization": f"Bearer {service}"},
        timeout=45.0,
    )
    response.raise_for_status()
    return response.json()


def _upsert_draft(issue: dict, html_body: str, text_body: str) -> None:
    """Store the Monday issue as a draft when Supabase is configured. Approved issues stay approved."""
    url = os.environ.get("SUPABASE_URL", "").strip().rstrip("/")
    service = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "").strip()
    if not url or not service:
        return
    import httpx

    headers = {"apikey": service, "Authorization": f"Bearer {service}"}
    existing = httpx.get(
        f"{url}/rest/v1/issues",
        params={"select": "status", "slug": f"eq.{issue['slug']}"},
        headers=headers,
        timeout=45.0,
    )
    existing.raise_for_status()
    rows = existing.json()
    if isinstance(rows, list) and rows and rows[0].get("status") in {"approved", "sending", "sent"}:
        return
    saved = httpx.post(
        f"{url}/rest/v1/issues",
        params={"on_conflict": "slug"},
        headers={**headers, "Content-Type": "application/json", "Prefer": "resolution=merge-duplicates"},
        json={
            "slug": issue["slug"],
            "subject": issue["subject"],
            "headline": issue["headline"],
            "html": html_body,
            "text_body": text_body,
            "status": "draft",
        },
        timeout=45.0,
    )
    saved.raise_for_status()


def _mark_issue(slug: str, status: str) -> None:
    url = os.environ.get("SUPABASE_URL", "").strip().rstrip("/")
    service = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "").strip()
    if not url or not service:
        return
    import httpx

    response = httpx.patch(
        f"{url}/rest/v1/issues",
        params={"slug": f"eq.{slug}"},
        headers={
            "apikey": service,
            "Authorization": f"Bearer {service}",
            "Content-Type": "application/json",
        },
        json={"status": status},
        timeout=45.0,
    )
    response.raise_for_status()


def _post(url: str, *, headers: dict, json: dict) -> dict:
    import httpx

    response = httpx.post(url, headers=headers, json=json, timeout=45.0)
    response.raise_for_status()
    if not response.content:
        return {}
    return response.json()


def _dry_run_forced() -> bool:
    from inflammon.transactional import env_is_dry_run

    return env_is_dry_run()


def _update_fingerprints(state_dir: Path, previous: dict | None, snapshot: dict, generated_at: str | None) -> None:
    state_dir.mkdir(parents=True, exist_ok=True)
    if previous and previous.get("snapshot_generated_at") != generated_at:
        _write_json(state_dir / "prior.json", previous)
    _write_json(state_dir / "previous.json", fingerprint(snapshot))


def _write_issue_files(issue_dir: Path, issue: dict, html_body: str, text_body: str) -> None:
    _write_json(issue_dir / "issue.json", issue)
    (issue_dir / "issue.html").write_text(html_body, encoding="utf8")
    (issue_dir / "issue.txt").write_text(text_body, encoding="utf8")


def _write_index(path: Path, issue: dict) -> dict:
    current = _read_json(path) or {"product": "Open Health Signals", "issues": []}
    issues = [item for item in current.get("issues") or [] if item.get("slug") != issue["slug"]]
    issues.append(
        {
            "slug": issue["slug"],
            "headline": issue["headline"],
            "kind": issue["kind"],
            "kicker": issue["kicker"],
            "subject": issue["subject"],
            "snapshot_generated_at": issue["snapshot_generated_at"],
        }
    )
    issues.sort(key=lambda item: item.get("slug") or "", reverse=True)
    current["product"] = "Open Health Signals"
    current["issues"] = issues
    _write_json(path, current)
    return current


def _sync_web(web_data: Path, web_email: Path, index: dict, issue: dict, html_body: str) -> None:
    issues_dir = web_data / "issues"
    issues_dir.mkdir(parents=True, exist_ok=True)
    _write_json(issues_dir / f"{issue['slug']}.json", issue)
    _write_json(web_data / "index.json", index)
    web_email.mkdir(parents=True, exist_ok=True)
    (web_email / f"{issue['slug']}.html").write_text(html_body, encoding="utf8")


def _read_json(path: Path) -> dict | None:
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf8"))


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf8")
