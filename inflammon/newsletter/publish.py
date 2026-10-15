"""Write an issue archive and, when asked, send it through the configured provider."""

from __future__ import annotations

import json
import os
from pathlib import Path

from inflammon.newsletter.compose import compose_issue, fingerprint, load_snapshot
from inflammon.newsletter.render import buttondown_payload, render_html, render_text, resend_broadcast_payload


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
    provider = _provider()
    issue = compose_issue(snapshot, baseline, site_url=site)
    unsubscribe = _unsubscribe_href(provider)
    html_body = render_html(issue, unsubscribe_href=unsubscribe)
    text_body = render_text(issue, unsubscribe_href=unsubscribe)
    issue["delivery"] = {"mode": "dry-run", "sent": False, "provider": provider}

    slug = issue["slug"]
    issue_dir = out / "issues" / slug
    issue_dir.mkdir(parents=True, exist_ok=True)
    _write_issue_files(issue_dir, issue, html_body, text_body)
    index = _write_index(out / "index.json", issue)
    _sync_web(Path(web_data_dir), Path(web_email_dir), index, issue, html_body)
    _update_fingerprints(state_dir, previous, snapshot, generated_at)

    if send and not _dry_run_forced():
        try:
            delivery = _send(provider, issue, html_body, text_body)
        except NewsletterSendError:
            issue["delivery"] = {"mode": "send", "sent": False, "provider": provider, "error": "send_failed"}
            _write_issue_files(issue_dir, issue, html_body, text_body)
            _sync_web(Path(web_data_dir), Path(web_email_dir), index, issue, html_body)
            raise
        issue["delivery"] = delivery
        _write_issue_files(issue_dir, issue, html_body, text_body)
        index = _write_index(out / "index.json", issue)
        _sync_web(Path(web_data_dir), Path(web_email_dir), index, issue, html_body)

    return {
        "slug": slug,
        "kind": issue["kind"],
        "headline": issue["headline"],
        "provider": provider,
        "delivery": issue["delivery"],
        "html": str(issue_dir / "issue.html"),
        "text": str(issue_dir / "issue.txt"),
        "archive": issue["archive_path"],
    }


def _send(provider: str, issue: dict, html_body: str, text_body: str) -> dict:
    if provider == "resend":
        return send_resend(issue, html_body, text_body)
    if provider == "buttondown":
        return send_buttondown(issue, html_body)
    raise NewsletterSendError(
        f"NEWSLETTER_PROVIDER={provider} is not supported. Use buttondown or resend. The issue was written; nothing was sent."
    )


def send_buttondown(issue: dict, html_body: str, *, api_key: str | None = None, post=None) -> dict:
    key = api_key if api_key is not None else os.environ.get("BUTTONDOWN_API_KEY", "").strip()
    if not key:
        raise NewsletterSendError("BUTTONDOWN_API_KEY is not set. The issue was written; nothing was sent.")
    payload = buttondown_payload(issue, html_body)
    response = (post or _post)(
        "https://api.buttondown.com/v1/emails",
        headers={"Authorization": f"Token {key}", "Content-Type": "application/json"},
        json=payload,
    )
    return {"mode": "send", "sent": True, "provider": "buttondown", "id": response.get("id")}


def send_resend(issue: dict, html_body: str, text_body: str, *, api_key: str | None = None, post=None) -> dict:
    key = api_key if api_key is not None else os.environ.get("RESEND_API_KEY", "").strip()
    audience = os.environ.get("RESEND_AUDIENCE_ID", "").strip()
    sender = os.environ.get("NEWSLETTER_FROM", "").strip()
    if not key:
        raise NewsletterSendError("RESEND_API_KEY is not set. The issue was written; nothing was sent.")
    if not audience:
        raise NewsletterSendError("RESEND_AUDIENCE_ID is not set. The issue was written; nothing was sent.")
    if not sender:
        raise NewsletterSendError("NEWSLETTER_FROM is not set. The issue was written; nothing was sent.")
    caller = post or _post
    payload = resend_broadcast_payload(issue, html_body, text_body, audience_id=audience, from_address=sender)
    created = caller(
        "https://api.resend.com/broadcasts",
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
        json=payload,
    )
    broadcast_id = created.get("id")
    if not broadcast_id:
        raise NewsletterSendError("Resend did not return a broadcast id. The issue was written; sending stopped.")
    caller(
        f"https://api.resend.com/broadcasts/{broadcast_id}/send",
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
        json={},
    )
    return {"mode": "send", "sent": True, "provider": "resend", "id": broadcast_id}


def _post(url: str, *, headers: dict, json: dict) -> dict:
    import httpx

    response = httpx.post(url, headers=headers, json=json, timeout=45.0)
    response.raise_for_status()
    if not response.content:
        return {}
    return response.json()


def _provider() -> str:
    return (os.environ.get("NEWSLETTER_PROVIDER") or "buttondown").strip().lower() or "buttondown"


def _dry_run_forced() -> bool:
    return os.environ.get("NEWSLETTER_DRY_RUN", "").strip().lower() in {"1", "true", "yes"}


def _unsubscribe_href(provider: str) -> str:
    if provider == "resend":
        return "{{{RESEND_UNSUBSCRIBE_URL}}}"
    return "{{ unsubscribe_url }}"


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
    current = _read_json(path) or {"product": "Inflammation Signal Monitor", "issues": []}
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
    current["product"] = "Inflammation Signal Monitor"
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
