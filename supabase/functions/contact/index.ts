import { INTEREST_TYPES, normalizeEmail, validEmail } from "../_shared/mailing.js";
import { clientIp, empty, json, readFields } from "../_shared/http.js";
import { sendResend, serviceClient } from "../_shared/db.js";
import { takeRate } from "../_shared/rate.js";
import {
  DEFAULT_OWNER_NOTIFY_EMAIL,
  contactAckEmail,
  contactFrom,
  excerpt,
  interestLabel,
  ownerNotifyEmail,
} from "../_shared/transactional.js";

const LIMIT = 5;
const WINDOW_MS = 60 * 60 * 1000;

Deno.serve(async (req) => {
  if (req.method === "OPTIONS") return empty();
  if (req.method !== "POST") return json(405, { ok: false, error: "method" });
  const { fields } = await readFields(req);
  const name = (fields.name || "").trim();
  const email = normalizeEmail(fields.email || "");
  const organization = (fields.organization || "").trim();
  const role = (fields.role || "").trim();
  const interest = (fields.interest_type || "").trim();
  const message = (fields.message || "").trim();
  const link = (fields.link || "").trim();
  if (!name || !validEmail(email) || !message) {
    return json(400, { ok: false, error: "missing_fields", message: "Name, email, and a message are required." });
  }
  if (!INTEREST_TYPES.includes(interest)) {
    return json(400, { ok: false, error: "interest_type", message: "Choose an interest type." });
  }
  if (link && !link.startsWith("https://") && !link.startsWith("http://")) {
    return json(400, { ok: false, error: "link", message: "The link must start with http:// or https://." });
  }
  const turnstileOk = await verifyTurnstile(fields.turnstile_token || "", clientIp(req));
  if (!turnstileOk) return json(400, { ok: false, error: "turnstile", message: "The Turnstile check did not pass." });

  const db = serviceClient();
  const allowed = await takeRate(db, `contact:${clientIp(req)}`, LIMIT, WINDOW_MS);
  if (!allowed) return json(429, { ok: false, error: "rate_limited", message: "Too many messages from this network. Try again later." });

  const { data, error } = await db
    .from("contact_requests")
    .insert({ name, email, organization, role, interest_type: interest, message, link: link || null, status: "new" })
    .select("id")
    .single();
  if (error) return json(500, { ok: false, error: "store", message: error.message });

  const label = interestLabel(interest);
  const quote = excerpt(message);
  const from = contactFrom(Deno.env.get("NEWSLETTER_FROM") || "");
  const ack = contactAckEmail({ interestLabel: label, excerpt: quote });
  await sendResend({
    to: email,
    from,
    subject: ack.subject,
    text: ack.text,
    html: ack.html,
    replyTo: ack.replyTo,
  });
  const ownerAddress = (Deno.env.get("OWNER_NOTIFY_EMAIL") || DEFAULT_OWNER_NOTIFY_EMAIL).trim();
  const owner = ownerNotifyEmail({
    name,
    email,
    organization,
    role,
    interestLabel: label,
    message,
    link,
  });
  await sendResend({
    to: ownerAddress,
    from,
    subject: owner.subject,
    text: owner.text,
    html: owner.html,
    replyTo: owner.replyTo,
  });
  return json(200, { ok: true, id: data.id, message: "Message received." });
});

async function verifyTurnstile(token: string, ip: string) {
  const secret = Deno.env.get("TURNSTILE_SECRET_KEY") || "";
  if (!token || !secret) return false;
  const response = await fetch("https://challenges.cloudflare.com/turnstile/v0/siteverify", {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ secret, response: token, remoteip: ip }),
  });
  if (!response.ok) return false;
  const payload = await response.json();
  return Boolean(payload.success);
}
