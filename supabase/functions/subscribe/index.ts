import { newConfirmToken, normalizeEmail, sha256Hex, validEmail } from "../_shared/mailing.js";
import { clientIp, empty, json, readFields } from "../_shared/http.js";
import { dryRun, sendResend, serviceClient } from "../_shared/db.js";

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
  if (!dryRun()) {
    await sendResend({
      to: email,
      subject: "Confirm your Open Health Signals briefing",
      text: `Confirm this address to receive the weekly briefing.\n\n${link}\n\nIf you did not ask for this, ignore the message. You will not be added until you open the link.`,
    });
  }
  return json(200, {
    ok: true,
    status: alreadyPending ? "already_pending" : "pending",
    message: "Check your inbox. We sent a confirmation link. You're added once you click it.",
  });
});
