import { newConfirmToken, normalizeEmail, sha256Hex, validEmail } from "../_shared/mailing.js";
import { clientIp, empty, json, readFields } from "../_shared/http.js";
import { sendResend, serviceClient } from "../_shared/db.js";
import { takeRate } from "../_shared/rate.js";
import { confirmationEmail, listFrom } from "../_shared/transactional.js";

const CONFIRM_EMAIL_LIMIT = 3;
const CONFIRM_WINDOW_MS = 60 * 60 * 1000;
const PENDING_MESSAGE = "Check your inbox. We sent a confirmation link. You're added once you click it.";

Deno.serve(async (req) => {
  if (req.method === "OPTIONS") return empty();
  if (req.method !== "POST") return json(405, { ok: false, error: "method" });
  const { fields } = await readFields(req);
  if (!["yes", "true", "1", "on"].includes(String(fields.consent || "").toLowerCase())) {
    return json(400, { ok: false, error: "consent_required", message: "Check the consent box before subscribing." });
  }
  const email = normalizeEmail(fields.email || "");
  if (!validEmail(email)) return json(400, { ok: false, error: "email_required", message: "Enter an email address." });

  const db = serviceClient();
  const { data: existing, error: readError } = await db.from("subscribers").select("id,status").eq("email", email).maybeSingle();
  if (readError) return json(500, { ok: false, error: "store", message: readError.message });
  if (existing && (existing.status === "bounced" || existing.status === "complained")) {
    return json(409, {
      ok: false,
      error: "suppressed",
      message: "This address is suppressed after a bounce or a complaint. It is not added again from the form.",
    });
  }
  if (existing?.status === "active") {
    return json(200, { ok: true, status: "active", message: "This address is already confirmed." });
  }
  const alreadyPending = existing?.status === "pending";
  if (alreadyPending && !(await takeRate(db, `confirm:${email}`, CONFIRM_EMAIL_LIMIT, CONFIRM_WINDOW_MS))) {
    return json(200, { ok: true, status: "already_pending", message: PENDING_MESSAGE });
  }
  if (!alreadyPending) await takeRate(db, `confirm:${email}`, CONFIRM_EMAIL_LIMIT, CONFIRM_WINDOW_MS);

  const token = newConfirmToken();
  const confirmTokenHash = await sha256Hex(token);
  const now = new Date().toISOString();
  const patch = {
    email,
    status: "pending",
    consent_at: now,
    consent_ip: clientIp(req),
    confirm_token_hash: confirmTokenHash,
    confirm_sent_at: now,
  };
  const write = existing
    ? await db.from("subscribers").update(patch).eq("id", existing.id)
    : await db.from("subscribers").insert(patch);
  if (write.error) return json(500, { ok: false, error: "store", message: write.error.message });

  const site = (Deno.env.get("SITE_URL") || "").replace(/\/$/, "");
  const link = `${site}/confirm?token=${encodeURIComponent(token)}`;
  const mail = confirmationEmail({ confirmUrl: link });
  await sendResend({
    to: email,
    from: listFrom(Deno.env.get("NEWSLETTER_FROM") || ""),
    subject: mail.subject,
    text: mail.text,
    html: mail.html,
    replyTo: mail.replyTo,
  });
  return json(200, {
    ok: true,
    status: alreadyPending ? "already_pending" : "pending",
    message: PENDING_MESSAGE,
  });
});
