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


FOOTER_ADVICE = "Informational only, not medical advice. FAERS reports don't prove a drug caused an event."
FOOTER_DATA = "Data: U.S. FDA (open.fda.gov). Not affiliated with or endorsed by FDA."
FOOTER_REASON = "You're getting this because you subscribed."


def render_html(issue: dict, *, unsubscribe_href: str) -> str:
    headline = _esc(issue["headline"])
    preheader = _esc(issue.get("preheader") or issue["headline"])
    sections = "\n".join(_section_html(section) for section in issue["sections"])
    dashboard = _esc(issue["dashboard_url"], quote=True)
    archive = _esc(issue["site_url"].rstrip("/") + issue["archive_path"], quote=True)
    methods = _esc(issue["site_url"].rstrip("/") + "/methods", quote=True)
    provider_unsubscribe = _esc(unsubscribe_href, quote=True)
    postal_raw = str(issue.get("postal_address") or "").strip()
    postal = (
        f'<p class="muted" style="margin:8px 0 0 0;font-family:Helvetica,Arial,sans-serif;font-size:12px;line-height:1.5;color:{MUTED};">{_esc(postal_raw)}</p>'
        if postal_raw
        else ""
    )
    kicker = _esc(issue["kicker"])
    faers_as_of = str(issue.get("openfda_last_updated") or "").strip()
    faers_line = (
        f'<p class="muted" style="margin:14px 0 0 0;font-family:Helvetica,Arial,sans-serif;font-size:12px;line-height:1.45;color:{MUTED};">FAERS data as of {_esc(faers_as_of)}.</p>'
        if faers_as_of
        else ""
    )
    highlights = _highlights_html(issue.get("highlights") or [])
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="color-scheme" content="light dark">
<meta name="supported-color-schemes" content="light dark">
<meta name="x-apple-disable-message-reformatting">
<title>{headline}</title>
<style>
  :root {{ color-scheme: light dark; }}
  @media only screen and (max-width: 620px) {{
    .container {{ width: 100% !important; }}
    .px {{ padding-left: 16px !important; padding-right: 16px !important; }}
    .headline {{ font-size: 26px !important; line-height: 1.25 !important; }}
  }}
  @media (prefers-color-scheme: dark) {{
    .bg {{ background: #1c1917 !important; }}
    .sheet {{ background: #292524 !important; border-color: #44403c !important; }}
    .ink, .headline {{ color: #f4f1ea !important; }}
    .muted {{ color: #d6d3d1 !important; }}
    .card {{ background: #1c1917 !important; border-color: #44403c !important; }}
    .ink a, a.ink {{ color: #f4f1ea !important; }}
    a.teal, .section-title, .kicker {{ color: #9fd4d0 !important; }}
  }}
</style>
</head>
<body class="bg" style="margin:0;padding:0;background:{PAPER};color:{INK};">
<div style="display:none;max-height:0;overflow:hidden;mso-hide:all;">{preheader}</div>
<table role="presentation" class="bg" width="100%" cellpadding="0" cellspacing="0" border="0" bgcolor="{PAPER}" style="background:{PAPER};margin:0;padding:0;">
  <tr>
    <td align="center" style="padding:24px 12px;">
      <table role="presentation" class="container sheet" width="600" cellpadding="0" cellspacing="0" border="0" bgcolor="{WHITE}" style="width:600px;max-width:600px;background:{WHITE};border:1px solid {RULE};">
        <tr>
          <td class="px" style="padding:22px 32px 12px 32px;background:{TEAL};">
            <p style="margin:0;font-family:Georgia,'Iowan Old Style',Palatino,serif;font-size:13px;letter-spacing:0.04em;color:#d7ebe8;">Open Health Signals</p>
            <p style="margin:8px 0 0 0;font-family:Georgia,'Iowan Old Style',Palatino,serif;font-size:16px;color:#f6f3ec;">{kicker}</p>
          </td>
        </tr>
        <tr>
          <td class="px" style="padding:28px 32px 8px 32px;">
            <h1 class="headline ink" style="margin:0;font-family:Georgia,'Iowan Old Style',Palatino,serif;font-size:32px;line-height:1.2;font-weight:normal;color:{INK};">{headline}</h1>
            {highlights}
            {faers_line}
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
            <p class="muted" style="margin:14px 0 0 0;font-family:Helvetica,Arial,sans-serif;font-size:13px;line-height:1.5;color:{MUTED};">
              <a class="teal" href="{archive}" style="color:{TEAL};">Read this issue on the site</a>
              · <a class="teal" href="{methods}" style="color:{TEAL};">How these numbers are made</a>
            </p>
          </td>
        </tr>
        <tr>
          <td class="px" style="padding:8px 32px 28px 32px;border-top:1px solid {RULE};">
            <p class="muted" style="margin:16px 0 0 0;font-family:Helvetica,Arial,sans-serif;font-size:12px;line-height:1.5;color:{MUTED};">{_esc(FOOTER_ADVICE)}</p>
            <p class="muted" style="margin:8px 0 0 0;font-family:Helvetica,Arial,sans-serif;font-size:12px;line-height:1.5;color:{MUTED};">{_esc(FOOTER_DATA)}</p>
            <p class="muted" style="margin:8px 0 0 0;font-family:Helvetica,Arial,sans-serif;font-size:12px;line-height:1.5;color:{MUTED};">{_esc(FOOTER_REASON)} <a class="teal" href="{provider_unsubscribe}" style="color:{TEAL};">Unsubscribe</a></p>
            {postal}
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
        "OPEN HEALTH SIGNALS",
        "Inflammation Signal Monitor",
        issue["kicker"],
        "",
        issue["headline"],
        "",
    ]
    highlights = issue.get("highlights") or []
    if highlights:
        lines.append("This week")
        for item in highlights:
            lines.append(f"- {item.get('sentence') or ''}")
            if item.get("href"):
                lines.append(f"  {item['href']}")
        lines.append("")
    if issue.get("openfda_last_updated"):
        lines.extend([f"FAERS data as of {issue.get('openfda_last_updated')}.", ""])
    for section in issue["sections"]:
        lines.append(section["heading"].upper())
        if section.get("note"):
            lines.append(section["note"])
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
            f"How these numbers are made: {issue['site_url'].rstrip('/')}/methods",
            "",
            FOOTER_ADVICE,
            FOOTER_DATA,
            f"{FOOTER_REASON} Unsubscribe: {unsubscribe_href}",
        ]
    )
    postal = str(issue.get("postal_address") or "").strip()
    if postal:
        lines.extend(["", postal])
    lines.append("")
    return "\n".join(lines)


def _highlights_html(items: list[dict]) -> str:
    if not items:
        return ""
    rows = []
    for item in items:
        sentence = _esc(item.get("sentence") or "")
        href = item.get("href") or ""
        if href:
            inner = f'<a class="ink" href="{_esc(href, quote=True)}" style="color:{INK};text-decoration:underline;">{sentence}</a>'
        else:
            inner = sentence
        rows.append(
            "<li class=\"ink\" style=\"margin:0 0 8px 0;font-family:Georgia,'Iowan Old Style',Palatino,serif;"
            f"font-size:16px;line-height:1.45;color:{INK};\">{inner}</li>"
        )
    joined = "".join(rows)
    return (
        f'<p class="section-title" style="margin:22px 0 8px 0;font-family:Helvetica,Arial,sans-serif;font-size:12px;letter-spacing:0.08em;'
        f'text-transform:uppercase;color:{TEAL};">This week</p>'
        f'<ul style="margin:0;padding:0 0 0 18px;">{joined}</ul>'
    )


def _section_html(section: dict) -> str:
    heading = _esc(section["heading"])
    note = ""
    if section.get("note"):
        note = (
            f'<p class="muted" style="margin:8px 0 0 0;font-family:Helvetica,Arial,sans-serif;font-size:12px;line-height:1.5;color:{MUTED};">'
            f"{_esc(section['note'])}</p>"
        )
    if not section["items"]:
        body = (
            f'<p class="muted" style="margin:8px 0 0 0;font-family:Helvetica,Arial,sans-serif;font-size:15px;line-height:1.5;color:{MUTED};">'
            f"{_esc(section['empty'])}</p>"
        )
    else:
        body = "\n".join(_item_html(item) for item in section["items"])
    return f"""<tr>
          <td id="{_esc(section.get("id") or "", quote=True)}" class="px" style="padding:20px 32px 4px 32px;">
            <h2 class="section-title" style="margin:0;font-family:Georgia,'Iowan Old Style',Palatino,serif;font-size:22px;font-weight:normal;color:{TEAL};">{heading}</h2>
            {note}
            {"" if section.get("id") != "papers" else f'<p style="margin:8px 0 0 0;font-family:Helvetica,Arial,sans-serif;font-size:12px;line-height:1.5;"><a href="https://www.ncbi.nlm.nih.gov/home/about/policies/" style="color:{TEAL};">NCBI disclaimer</a></p>'}
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
            f'<p class="muted" style="margin:4px 0 0 0;font-family:Helvetica,Arial,sans-serif;font-size:12px;line-height:1.45;color:{MUTED};">'
            f"{_esc(item['meta'])}</p>"
        )
    body = ""
    if item.get("body"):
        body = (
            f'<p class="ink" style="margin:8px 0 0 0;font-family:Helvetica,Arial,sans-serif;font-size:14px;line-height:1.5;color:{INK};">'
            f"{_esc(item['body'])}</p>"
        )
    return f"""<table role="presentation" class="card" width="100%" cellpadding="0" cellspacing="0" border="0" bgcolor="{CARD}" style="margin-top:12px;background:{CARD};border:1px solid {RULE};">
              <tr>
                <td style="padding:12px 14px;">
                  {badge}
                  <p class="ink" style="margin:4px 0 0 0;font-family:Georgia,'Iowan Old Style',Palatino,serif;font-size:16px;line-height:1.35;color:{INK};">{title_html}</p>
                  {meta}
                  {body}
                </td>
              </tr>
            </table>"""


def _esc(value: str, quote: bool = False) -> str:
    return html.escape(str(value), quote=quote)
