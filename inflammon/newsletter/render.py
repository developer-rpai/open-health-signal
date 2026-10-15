"""HTML and plain-text renderings of one newsletter issue."""

from __future__ import annotations

import html

INK = "#1c1917"
TEAL = "#0f5c5c"
PAPER = "#f4f1ea"
CARD = "#f6f3ec"
ALERT = "#8c2f2f"
MUTED = "#5c564c"
RULE = "#e4ddd0"
WHITE = "#fffdf8"


def render_html(issue: dict, *, unsubscribe_href: str) -> str:
    headline = _esc(issue["headline"])
    preheader = _esc(issue.get("preheader") or issue["headline"])
    sections = "\n".join(_section_html(section) for section in issue["sections"])
    dashboard = _esc(issue["dashboard_url"], quote=True)
    archive = _esc(issue["site_url"].rstrip("/") + issue["archive_path"], quote=True)
    unsubscribe = _esc(unsubscribe_href, quote=True)
    disclaimer = _esc(issue["disclaimer"])
    kicker = _esc(issue["kicker"])
    intro = _esc(issue["intro"])
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="x-apple-disable-message-reformatting">
<title>{headline}</title>
<style>
  @media only screen and (max-width: 620px) {{
    .container {{ width: 100% !important; }}
    .px {{ padding-left: 16px !important; padding-right: 16px !important; }}
    .headline {{ font-size: 26px !important; line-height: 1.25 !important; }}
  }}
</style>
</head>
<body style="margin:0;padding:0;background:{PAPER};color:{INK};">
<div style="display:none;max-height:0;overflow:hidden;mso-hide:all;">{preheader}</div>
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" bgcolor="{PAPER}" style="background:{PAPER};margin:0;padding:0;">
  <tr>
    <td align="center" style="padding:24px 12px;">
      <table role="presentation" class="container" width="600" cellpadding="0" cellspacing="0" border="0" style="width:600px;max-width:600px;background:{WHITE};border:1px solid {RULE};">
        <tr>
          <td class="px" style="padding:28px 32px 8px 32px;background:{TEAL};">
            <p style="margin:0;font-family:Georgia,'Iowan Old Style',Palatino,serif;font-size:13px;letter-spacing:0.14em;text-transform:uppercase;color:#d7ebe8;">Inflammation Signal Monitor</p>
            <p style="margin:8px 0 0 0;font-family:Georgia,'Iowan Old Style',Palatino,serif;font-size:16px;color:#f6f3ec;">{kicker}</p>
          </td>
        </tr>
        <tr>
          <td class="px" style="padding:28px 32px 8px 32px;">
            <h1 class="headline" style="margin:0;font-family:Georgia,'Iowan Old Style',Palatino,serif;font-size:32px;line-height:1.2;font-weight:normal;color:{INK};">{headline}</h1>
            <p style="margin:16px 0 0 0;font-family:Georgia,'Iowan Old Style',Palatino,serif;font-size:16px;line-height:1.5;color:{INK};">{intro}</p>
          </td>
        </tr>
        {sections}
        <tr>
          <td class="px" align="left" style="padding:8px 32px 28px 32px;">
            <table role="presentation" cellpadding="0" cellspacing="0" border="0">
              <tr>
                <td bgcolor="{TEAL}" style="background:{TEAL};border-radius:6px;">
                  <a href="{dashboard}" style="display:inline-block;padding:12px 18px;font-family:Helvetica,Arial,sans-serif;font-size:15px;line-height:1;color:#f6f3ec;text-decoration:none;">Open the dashboard</a>
                </td>
              </tr>
            </table>
            <p style="margin:14px 0 0 0;font-family:Helvetica,Arial,sans-serif;font-size:13px;line-height:1.5;color:{MUTED};">
              <a href="{archive}" style="color:{TEAL};">Read this issue on the site</a>
            </p>
          </td>
        </tr>
        <tr>
          <td class="px" style="padding:8px 32px 28px 32px;border-top:1px solid {RULE};">
            <p style="margin:16px 0 0 0;font-family:Helvetica,Arial,sans-serif;font-size:12px;line-height:1.55;color:{MUTED};">{disclaimer}</p>
            <p style="margin:12px 0 0 0;font-family:Helvetica,Arial,sans-serif;font-size:12px;line-height:1.55;color:{MUTED};">
              You received this because you confirmed a subscription to Inflammation Signal Monitor.
              <a href="{unsubscribe}" style="color:{TEAL};">Unsubscribe</a>.
              The email provider fills in that link when the issue is sent.
            </p>
          </td>
        </tr>
      </table>
    </td>
  </tr>
</table>
</body>
</html>
"""


def render_text(issue: dict, *, unsubscribe_href: str) -> str:
    lines = [
        "INFLAMMATION SIGNAL MONITOR",
        issue["kicker"],
        "",
        issue["headline"],
        "",
        issue["intro"],
        "",
    ]
    for section in issue["sections"]:
        lines.append(section["heading"].upper())
        items = section["items"]
        if not items:
            lines.append(section["empty"])
            lines.append("")
            continue
        for item in items:
            lines.append(f"- {item['title']}")
            if item.get("badge"):
                lines.append(f"  {item['badge']}")
            if item.get("meta"):
                lines.append(f"  {item['meta']}")
            if item.get("body"):
                lines.append(f"  {item['body']}")
            if item.get("href"):
                lines.append(f"  {item['href']}")
            lines.append("")
    lines.extend(
        [
            f"Open the dashboard: {issue['dashboard_url']}",
            f"Read this issue on the site: {issue['site_url'].rstrip('/')}{issue['archive_path']}",
            "",
            issue["disclaimer"],
            "",
            f"Unsubscribe: {unsubscribe_href}",
            "",
        ]
    )
    return "\n".join(lines)


def buttondown_payload(issue: dict, html_body: str) -> dict:
    return {
        "subject": issue["subject"],
        "body": "<!-- buttondown-editor-mode: fancy -->\n" + html_body,
        "status": "about_to_send",
    }


def resend_broadcast_payload(issue: dict, html_body: str, text_body: str, *, audience_id: str, from_address: str) -> dict:
    return {
        "audience_id": audience_id,
        "from": from_address,
        "subject": issue["subject"],
        "html": html_body,
        "text": text_body,
    }


def _section_html(section: dict) -> str:
    heading = _esc(section["heading"])
    if not section["items"]:
        body = (
            f'<p style="margin:8px 0 0 0;font-family:Helvetica,Arial,sans-serif;font-size:15px;line-height:1.5;color:{MUTED};">'
            f"{_esc(section['empty'])}</p>"
        )
    else:
        body = "\n".join(_item_html(item) for item in section["items"])
    return f"""<tr>
          <td class="px" style="padding:20px 32px 4px 32px;">
            <h2 style="margin:0;font-family:Georgia,'Iowan Old Style',Palatino,serif;font-size:22px;font-weight:normal;color:{TEAL};">{heading}</h2>
            {body}
          </td>
        </tr>"""


def _item_html(item: dict) -> str:
    title = _esc(item["title"])
    href = item.get("href") or ""
    if href:
        title_html = f'<a href="{_esc(href, quote=True)}" style="color:{INK};text-decoration:underline;">{title}</a>'
    else:
        title_html = title
    badge = ""
    if item.get("badge"):
        color = ALERT if "Class I" == item["badge"] else TEAL
        badge = (
            f'<p style="margin:8px 0 0 0;font-family:Helvetica,Arial,sans-serif;font-size:11px;letter-spacing:0.08em;'
            f'text-transform:uppercase;color:{color};">{_esc(item["badge"])}</p>'
        )
    meta = ""
    if item.get("meta"):
        meta = (
            f'<p style="margin:4px 0 0 0;font-family:Helvetica,Arial,sans-serif;font-size:12px;line-height:1.45;color:{MUTED};">'
            f"{_esc(item['meta'])}</p>"
        )
    body = ""
    if item.get("body"):
        body = (
            f'<p style="margin:8px 0 0 0;font-family:Helvetica,Arial,sans-serif;font-size:14px;line-height:1.5;color:{INK};">'
            f"{_esc(item['body'])}</p>"
        )
    return f"""<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="margin-top:12px;background:{CARD};border:1px solid {RULE};">
              <tr>
                <td style="padding:12px 14px;">
                  {badge}
                  <p style="margin:4px 0 0 0;font-family:Georgia,'Iowan Old Style',Palatino,serif;font-size:16px;line-height:1.35;color:{INK};">{title_html}</p>
                  {meta}
                  {body}
                </td>
              </tr>
            </table>"""


def _esc(value: str, quote: bool = False) -> str:
    return html.escape(str(value), quote=quote)
