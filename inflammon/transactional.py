"""Transactional mail for subscribe, confirm, and contact.

The wording matches ``supabase/functions/_shared/transactional.js``.
A live Resend call happens only when ``NEWSLETTER_DRY_RUN`` is exactly ``0``.
Anything else logs the message and does not call Resend. A send error is
recorded and does not raise.
"""

from __future__ import annotations

import logging
import os
import re
from typing import Any

CONTACT_EMAIL = "contact@openhealthsignals.org"
DEFAULT_OWNER_NOTIFY_EMAIL = "rakeshpai@openhealthsignals.org"

INTEREST_LABELS = {
    "research_collaboration": "Research collaboration",
    "data_expansion": "Data expansion",
    "code_contribution": "Code contribution",
    "custom_analysis": "Custom analysis",
    "media": "Media",
    "sponsorship": "Sponsorship",
}

CONFIRM_INTRO = "Confirm this address for Open Health Signals."
CONFIRM_NOTE = (
    "About once a week you'll get the Inflammation Signal Monitor, our digest of public signals on inflammatory conditions and drugs. "
    "You're added only after you open the link. If you didn't ask for this, ignore this message."
)
WELCOME_OPEN = "Welcome to Open Health Signals."
WELCOME_BODY = (
    "About once a week you'll get the Inflammation Signal Monitor, our digest of public signals on inflammatory conditions and drugs: "
    "FDA adverse-event reports and FAERS trends, research, and access news."
)
WELCOME_ADVICE = "This is informational, not medical advice."
WELCOME_UNSUB = "The link is signed for this address and takes effect immediately."
ACK = "Thank you for contacting us. We got your message and will get back to you as soon as we can."
ACK_SIGN = "Open Health Signals"
SITE_URL = "https://openhealthsignals.org"

logger = logging.getLogger("inflammon.transactional")


def interest_label(value: str) -> str:
    return INTEREST_LABELS.get(value) or str(value or "").strip() or "Message"


def excerpt(message: str, limit: int = 280) -> str:
    lines = [line.strip() for line in re.split(r"\r?\n", str(message or "")) if line.strip()]
    text = "\n".join(lines[:3])
    if len(text) <= limit:
        return text
    return text[: limit - 3].rstrip() + "..."


def _one_line(value: str) -> str:
    return " ".join(str(value or "").split())


def _esc(value: str) -> str:
    return str(value).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


def _domain_of(sender: str) -> str:
    raw = str(sender or "").strip()
    match = re.search(r"<([^>]+)>", raw)
    address = (match.group(1) if match else raw).strip()
    if "@" not in address:
        return ""
    return address.rsplit("@", 1)[1].lower()


def env_is_dry_run() -> bool:
    """True unless NEWSLETTER_DRY_RUN is exactly the string 0."""
    return os.environ.get("NEWSLETTER_DRY_RUN", "") != "0"


def mask_recipient(email: str) -> str:
    raw = str(email or "").strip()
    at = raw.rfind("@")
    if at <= 0 or at == len(raw) - 1:
        return "***"
    return f"{raw[0]}***@{raw[at + 1 :]}"


def list_from(newsletter_from: str) -> str:
    raw = str(newsletter_from or "").strip()
    return raw or f"Open Health Signals <{CONTACT_EMAIL}>"


def contact_from(newsletter_from: str) -> str:
    domain = _domain_of(newsletter_from)
    if not domain or domain == "openhealthsignals.org":
        return f"Open Health Signals <{CONTACT_EMAIL}>"
    return str(newsletter_from or "").strip()


def list_unsubscribe_headers(url: str) -> dict[str, str]:
    return {
        "List-Unsubscribe": f"<{url}>",
        "List-Unsubscribe-Post": "List-Unsubscribe=One-Click",
    }


def _layout(
    *,
    preheader: str,
    blocks: list[str],
    quote: str = "",
    action_href: str = "",
    action_label: str = "",
    postal: str = "",
) -> str:
    parts = [
        (
            '<p style="margin:0 0 16px 0;font-family:Georgia,Palatino,serif;font-size:16px;'
            f'line-height:1.5;color:#1c1917;">{_esc(block)}</p>'
        )
        for block in blocks
    ]
    if quote:
        parts.append(
            '<p style="margin:0 0 16px 0;font-family:Georgia,Palatino,serif;font-size:16px;'
            f'line-height:1.5;color:#1c1917;white-space:pre-wrap;">{_esc(quote)}</p>'
        )
    if action_href:
        parts.append(
            f'<p style="margin:0 0 16px 0;"><a href="{_esc(action_href)}" style="color:#0f5c5c;">{_esc(action_label)}</a></p>'
        )
    postal_line = str(postal or "").strip()
    if postal_line:
        parts.append(
            '<p style="margin:16px 0 0 0;font-family:Helvetica,Arial,sans-serif;font-size:12px;'
            f'line-height:1.5;color:#5c564c;">{_esc(postal_line)}</p>'
        )
    pre = _esc(preheader)
    inner = "".join(parts)
    return f"""<!DOCTYPE html>
<html lang="en">
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>{pre}</title></head>
<body style="margin:0;padding:0;background:#f4f1ea;color:#1c1917;">
<div style="display:none;max-height:0;overflow:hidden;">{pre}</div>
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="background:#f4f1ea;">
<tr><td align="center" style="padding:24px 12px;">
<table role="presentation" width="560" cellpadding="0" cellspacing="0" border="0" style="width:560px;max-width:560px;background:#fffdf8;border:1px solid #e4ddd0;">
<tr><td style="padding:18px 28px;background:#0f5c5c;font-family:Georgia,Palatino,serif;font-size:14px;color:#f6f3ec;">Open Health Signals</td></tr>
<tr><td style="padding:28px 28px 12px 28px;">{inner}</td></tr>
</table>
</td></tr>
</table>
</body>
</html>
"""


def confirmation_email(*, confirm_url: str) -> dict[str, Any]:
    return {
        "kind": "confirm",
        "subject": "Confirm your Open Health Signals email",
        "text": f"{CONFIRM_INTRO}\n\n{confirm_url}\n\n{CONFIRM_NOTE}\n",
        "html": _layout(
            preheader="Confirm this address for Open Health Signals.",
            blocks=[CONFIRM_INTRO, CONFIRM_NOTE],
            action_href=confirm_url,
            action_label="Confirm this address",
        ),
        "reply_to": CONTACT_EMAIL,
        "headers": {},
    }


def welcome_email(*, unsubscribe_url: str, list_unsubscribe_url: str, postal_address: str) -> dict[str, Any]:
    postal = str(postal_address or "").strip()
    lines = [
        WELCOME_OPEN,
        "",
        WELCOME_BODY,
        "",
        WELCOME_ADVICE,
        "",
        f"Unsubscribe: {unsubscribe_url}",
        WELCOME_UNSUB,
        "",
        f"Questions: {CONTACT_EMAIL}",
    ]
    if postal:
        lines.extend(["", postal])
    lines.append("")
    return {
        "kind": "welcome",
        "subject": "Welcome to Open Health Signals",
        "text": "\n".join(lines),
        "html": _layout(
            preheader="Welcome to Open Health Signals.",
            blocks=[WELCOME_OPEN, WELCOME_BODY, WELCOME_ADVICE, WELCOME_UNSUB, f"Questions: {CONTACT_EMAIL}"],
            action_href=unsubscribe_url,
            action_label="Unsubscribe",
            postal=postal,
        ),
        "reply_to": CONTACT_EMAIL,
        "headers": list_unsubscribe_headers(list_unsubscribe_url),
    }


def contact_ack_email(*, interest_label: str = "", excerpt_text: str = "") -> dict[str, Any]:
    del interest_label, excerpt_text
    return {
        "kind": "contact_ack",
        "subject": "Thanks for contacting Open Health Signals",
        "text": f"{ACK}\n\n{ACK_SIGN}\n{SITE_URL}\n",
        "html": _layout(
            preheader=ACK,
            blocks=[ACK, ACK_SIGN],
            action_href=SITE_URL,
            action_label="openhealthsignals.org",
        ),
        "reply_to": CONTACT_EMAIL,
        "headers": {},
    }


def owner_notify_email(
    *,
    name: str,
    email: str,
    organization: str,
    role: str,
    interest_label: str,
    message: str,
    link: str,
) -> dict[str, Any]:
    who = f"{_one_line(name)} <{_one_line(email)}>"
    org = " · ".join(part for part in (_one_line(organization), _one_line(role)) if part)
    about = f"About: {interest_label or 'Message'}"
    lines = [who]
    if org:
        lines.append(org)
    lines.extend([about, "", message or ""])
    if link:
        lines.extend(["", link])
    lines.append("")
    subject_name = _one_line(name) or "the contact form"
    return {
        "kind": "owner_notify",
        "subject": f"Message from {subject_name}",
        "text": "\n".join(lines),
        "html": _layout(
            preheader=f"Message from {subject_name}",
            blocks=[who, org, about] if org else [who, about],
            quote=message or "",
            action_href=link or "",
            action_label="Open the link they sent" if link else "",
        ),
        "reply_to": _one_line(email),
        "headers": {},
    }


def send_message(
    message: dict[str, Any],
    *,
    dry_run: bool,
    api_key: str,
    sender: str,
    post,
    mail_log: list[dict[str, Any]],
) -> None:
    """Log under dry-run. Otherwise POST to Resend. Never raises."""
    record = {
        "kind": message["kind"],
        "to": message["to"],
        "from": sender,
        "subject": message["subject"],
        "reply_to": message.get("reply_to") or "",
        "text": message["text"],
        "html": message["html"],
        "headers": message.get("headers") or {},
        "dry_run": True,
    }
    mail_log.append(record)
    if dry_run or not api_key or not sender or post is None:
        logger.info(
            "transactional dry_run to=%s subject=%s reply_to=%s",
            mask_recipient(record["to"]),
            record["subject"],
            mask_recipient(record["reply_to"]) if record["reply_to"] else "",
        )
        return
    payload: dict[str, Any] = {
        "from": sender,
        "to": [message["to"]],
        "subject": message["subject"],
        "text": message["text"],
        "html": message["html"],
    }
    if message.get("reply_to"):
        payload["reply_to"] = message["reply_to"]
    if message.get("headers"):
        payload["headers"] = message["headers"]
    try:
        post(
            "https://api.resend.com/emails",
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json=payload,
        )
    except Exception:
        logger.exception(
            "transactional send failed to=%s subject=%s",
            mask_recipient(record["to"]),
            record["subject"],
        )
        record["error"] = "send_failed"
        return
    record["dry_run"] = False
