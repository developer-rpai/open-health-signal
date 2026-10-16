import { INTEREST_TYPES, normalizeEmail, validEmail } from "../_shared/mailing.js";
import { clientIp, empty, json, readFields } from "../_shared/http.js";
import { dryRun, sendResend, serviceClient } from "../_shared/db.js";

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
  if (!name || !validEmail(email) || !organization || !role || !message) {
    return json(400, { ok: false, error: "missing_fields", message: "Name, email, organization, role, and a message are required." });
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
  const allowed = await allowRate(db, `contact:${clientIp(req)}`);
  if (!allowed) return json(429, { ok: false, error: "rate_limited", message: "Too many messages from this network. Try again later." });

  const { data, error } = await db
    .from("contact_requests")
    .insert({ name, email, organization, role, interest_type: interest, message, link: link || null, status: "new" })
    .select("id")
    .single();
  if (error) return json(500, { ok: false, error: "store", message: error.message });

  const owner = Deno.env.get("OWNER_NOTIFY_EMAIL") || "";
  if (owner && !dryRun()) {
    await sendResend({
      to: owner,
      subject: "New collaboration message",
      text: `${name} (${email}) · ${interest}\n${organization} · ${role}\n\n${message}\n${link}`,
    });
  }
  return json(200, { ok: true, id: data.id, message: "Message received. The owner is notified by email." });
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

async function allowRate(db: ReturnType<typeof serviceClient>, bucket: string) {
  const now = Date.now();
  const { data } = await db.from("rate_limits").select("hits,window_start").eq("bucket", bucket).maybeSingle();
  if (!data || now - new Date(data.window_start).getTime() >= WINDOW_MS) {
    await db.from("rate_limits").upsert({ bucket, hits: 1, window_start: new Date(now).toISOString() });
    return true;
  }
  if (data.hits >= LIMIT) return false;
  await db.from("rate_limits").update({ hits: data.hits + 1 }).eq("bucket", bucket);
  return true;
}
