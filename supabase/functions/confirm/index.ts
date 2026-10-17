import { sha256Hex, signUnsubscribeToken } from "../_shared/mailing.js";
import { empty, html, json, readFields } from "../_shared/http.js";
import { sendResend, serviceClient } from "../_shared/db.js";
import { listFrom, welcomeEmail } from "../_shared/transactional.js";

Deno.serve(async (req) => {
  if (req.method === "OPTIONS") return empty();
  if (req.method !== "GET" && req.method !== "POST") return json(405, { ok: false, error: "method" });
  const url = new URL(req.url);
  const wantsJson = (req.headers.get("accept") || "").includes("application/json");
  let token = url.searchParams.get("token") || "";
  if (!token && req.method === "POST") {
    const { fields } = await readFields(req);
    token = fields.token || "";
  }
  const fail = (status: number, error: string, message: string) =>
    wantsJson ? json(status, { ok: false, error, message }) : html(status, "Link not valid", message);

  if (!token) return fail(400, "invalid_token", "This confirmation link does not match. Subscribe again from the dashboard.");
  const db = serviceClient();
  const hash = await sha256Hex(token);
  const { data, error } = await db.from("subscribers").select("id,email,status").eq("confirm_token_hash", hash).maybeSingle();
  if (error) return json(500, { ok: false, error: "store", message: error.message });
  if (!data) return fail(400, "invalid_token", "This confirmation link does not match. Subscribe again from the dashboard.");
  if (data.status === "bounced" || data.status === "complained") {
    const message = "This address was suppressed after a bounce or a complaint.";
    return wantsJson ? json(409, { ok: false, error: "suppressed", message }) : html(409, "Address suppressed", message);
  }
  const becameActive = data.status !== "active";
  if (becameActive) {
    const { error: updateError } = await db
      .from("subscribers")
      .update({ status: "active", confirmed_at: new Date().toISOString() })
      .eq("id", data.id);
    if (updateError) return json(500, { ok: false, error: "store", message: updateError.message });
    await sendWelcome(data);
  }
  const message = "You're subscribed. The next issue arrives in your inbox within the week.";
  return wantsJson ? json(200, { ok: true, status: "active", message }) : html(200, "You're subscribed", message);
});

async function sendWelcome(row: { id: string; email: string }) {
  if (!row.email) return;
  const site = (Deno.env.get("SITE_URL") || "").replace(/\/$/, "");
  const functionsBase = (Deno.env.get("FUNCTIONS_BASE") || site).replace(/\/$/, "");
  const pageBase = site || functionsBase;
  const token = await signUnsubscribeToken(row.id, row.email, Deno.env.get("UNSUBSCRIBE_HMAC_SECRET") || "");
  const pageUrl = `${pageBase}/unsubscribe?token=${encodeURIComponent(token)}`;
  const headerUrl = `${functionsBase || pageBase}/unsubscribe?token=${encodeURIComponent(token)}`;
  const mail = welcomeEmail({
    unsubscribeUrl: pageUrl,
    listUnsubscribeUrl: headerUrl,
    postalAddress: Deno.env.get("NEWSLETTER_POSTAL_ADDRESS") || "",
  });
  await sendResend({
    to: row.email,
    from: listFrom(Deno.env.get("NEWSLETTER_FROM") || ""),
    subject: mail.subject,
    text: mail.text,
    html: mail.html,
    replyTo: mail.replyTo,
    headers: mail.headers,
  });
}
