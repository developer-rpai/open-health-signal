// Transactional copy for subscribe, confirm, and contact.
// Plain strings. No Deno APIs, so tests/mailing.test.mjs can import this file.

export const CONTACT_EMAIL = "contact@openhealthsignals.org";
export const DEFAULT_OWNER_NOTIFY_EMAIL = "rakeshpai@openhealthsignals.org";

export const INTEREST_LABELS = {
  research_collaboration: "Research collaboration",
  data_expansion: "Data expansion",
  code_contribution: "Code contribution",
  custom_analysis: "Custom analysis",
  media: "Media",
  sponsorship: "Sponsorship",
};

const CONFIRM_INTRO = "Confirm this address to get the Inflammation Signal Monitor briefing.";
const CONFIRM_NOTE = "You're added only after you open that link. If you didn't ask for this, ignore this message.";
const WELCOME_BODY =
  "About once a week you'll get the Inflammation Signal Monitor digest. It covers public signals on inflammatory conditions and drugs: FDA adverse-event reports and FAERS trends, research, and access news.";
const WELCOME_ADVICE = "This is informational, not medical advice.";
const WELCOME_UNSUB = "The link is signed for this address and takes effect immediately.";
const ACK = "Thanks, we got your message and will reply within a few days.";

export function interestLabel(value) {
  return INTEREST_LABELS[value] || String(value || "").trim() || "Message";
}

export function excerpt(message, limit = 280) {
  const lines = String(message || "")
    .split(/\r?\n/)
    .map((line) => line.trim())
    .filter(Boolean);
  const text = lines.slice(0, 3).join("\n");
  if (text.length <= limit) return text;
  return `${text.slice(0, limit - 3).trimEnd()}...`;
}

function oneLine(value) {
  return String(value || "")
    .replace(/\s+/g, " ")
    .trim();
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}

function domainOf(from) {
  const raw = String(from || "").trim();
  const angled = raw.match(/<([^>]+)>/);
  const address = (angled ? angled[1] : raw).trim();
  const at = address.lastIndexOf("@");
  if (at < 0) return "";
  return address.slice(at + 1).toLowerCase();
}

export function maskRecipient(email) {
  const raw = String(email || "").trim();
  const at = raw.lastIndexOf("@");
  if (at <= 0 || at === raw.length - 1) return "***";
  return `${raw.slice(0, 1)}***@${raw.slice(at + 1)}`;
}

export function listFrom(newsletterFrom) {
  const raw = String(newsletterFrom || "").trim();
  return raw || `Open Health Signals <${CONTACT_EMAIL}>`;
}

export function contactFrom(newsletterFrom) {
  const domain = domainOf(newsletterFrom);
  if (!domain || domain === "openhealthsignals.org") {
    return `Open Health Signals <${CONTACT_EMAIL}>`;
  }
  return String(newsletterFrom || "").trim();
}

export function listUnsubscribeHeaders(url) {
  return {
    "List-Unsubscribe": `<${url}>`,
    "List-Unsubscribe-Post": "List-Unsubscribe=One-Click",
  };
}

function layout({ preheader, blocks, quote, actionHref, actionLabel, postal }) {
  const parts = blocks.map(
    (block) =>
      `<p style="margin:0 0 16px 0;font-family:Georgia,Palatino,serif;font-size:16px;line-height:1.5;color:#1c1917;">${escapeHtml(block)}</p>`,
  );
  if (quote) {
    parts.push(
      `<p style="margin:0 0 16px 0;font-family:Georgia,Palatino,serif;font-size:16px;line-height:1.5;color:#1c1917;white-space:pre-wrap;">${escapeHtml(quote)}</p>`,
    );
  }
  if (actionHref) {
    parts.push(
      `<p style="margin:0 0 16px 0;"><a href="${escapeHtml(actionHref)}" style="color:#0f5c5c;">${escapeHtml(actionLabel)}</a></p>`,
    );
  }
  const postalLine = String(postal || "").trim();
  if (postalLine) {
    parts.push(
      `<p style="margin:16px 0 0 0;font-family:Helvetica,Arial,sans-serif;font-size:12px;line-height:1.5;color:#5c564c;">${escapeHtml(postalLine)}</p>`,
    );
  }
  const pre = escapeHtml(preheader);
  return `<!DOCTYPE html>
<html lang="en">
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>${pre}</title></head>
<body style="margin:0;padding:0;background:#f4f1ea;color:#1c1917;">
<div style="display:none;max-height:0;overflow:hidden;">${pre}</div>
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="background:#f4f1ea;">
<tr><td align="center" style="padding:24px 12px;">
<table role="presentation" width="560" cellpadding="0" cellspacing="0" border="0" style="width:560px;max-width:560px;background:#fffdf8;border:1px solid #e4ddd0;">
<tr><td style="padding:18px 28px;background:#0f5c5c;font-family:Georgia,Palatino,serif;font-size:14px;color:#f6f3ec;">Open Health Signals</td></tr>
<tr><td style="padding:28px 28px 12px 28px;">${parts.join("")}</td></tr>
</table>
</td></tr>
</table>
</body>
</html>
`;
}

export function confirmationEmail({ confirmUrl }) {
  return {
    kind: "confirm",
    subject: "Confirm your Open Health Signals briefing",
    text: `${CONFIRM_INTRO}\n\n${confirmUrl}\n\n${CONFIRM_NOTE}\n`,
    html: layout({
      preheader: "Confirm this address to get the briefing.",
      blocks: [CONFIRM_INTRO, CONFIRM_NOTE],
      actionHref: confirmUrl,
      actionLabel: "Confirm this address",
    }),
    replyTo: CONTACT_EMAIL,
    headers: {},
  };
}

export function welcomeEmail({ unsubscribeUrl, listUnsubscribeUrl, postalAddress }) {
  const postal = String(postalAddress || "").trim();
  const lines = [
    "You're confirmed.",
    "",
    WELCOME_BODY,
    "",
    WELCOME_ADVICE,
    "",
    `Unsubscribe: ${unsubscribeUrl}`,
    WELCOME_UNSUB,
    "",
    `Questions: ${CONTACT_EMAIL}`,
  ];
  if (postal) lines.push("", postal);
  lines.push("");
  return {
    kind: "welcome",
    subject: "You're on the Inflammation Signal Monitor list",
    text: lines.join("\n"),
    html: layout({
      preheader: "You're confirmed. The digest is about once a week.",
      blocks: ["You're confirmed.", WELCOME_BODY, WELCOME_ADVICE, WELCOME_UNSUB, `Questions: ${CONTACT_EMAIL}`],
      actionHref: unsubscribeUrl,
      actionLabel: "Unsubscribe",
      postal,
    }),
    replyTo: CONTACT_EMAIL,
    headers: listUnsubscribeHeaders(listUnsubscribeUrl),
  };
}

export function contactAckEmail({ interestLabel, excerpt: quote }) {
  const label = interestLabel || "your note";
  return {
    kind: "contact_ack",
    subject: "We got your message",
    text: `${ACK}\n\nYou wrote (${label}):\n${quote}\n`,
    html: layout({
      preheader: ACK,
      blocks: [ACK, `You wrote (${label}):`],
      quote,
    }),
    replyTo: CONTACT_EMAIL,
    headers: {},
  };
}

export function ownerNotifyEmail({ name, email, organization, role, interestLabel, message, link }) {
  const who = `${oneLine(name)} <${oneLine(email)}>`;
  const org = [oneLine(organization), oneLine(role)].filter(Boolean).join(" · ");
  const about = `About: ${interestLabel || "Message"}`;
  const lines = [who];
  if (org) lines.push(org);
  lines.push(about, "", message || "");
  if (link) lines.push("", link);
  lines.push("");
  const subjectName = oneLine(name) || "the contact form";
  return {
    kind: "owner_notify",
    subject: `Message from ${subjectName}`,
    text: lines.join("\n"),
    html: layout({
      preheader: `Message from ${subjectName}`,
      blocks: org ? [who, org, about] : [who, about],
      quote: message || "",
      actionHref: link || "",
      actionLabel: link ? "Open the link they sent" : "",
    }),
    replyTo: oneLine(email),
    headers: {},
  };
}
