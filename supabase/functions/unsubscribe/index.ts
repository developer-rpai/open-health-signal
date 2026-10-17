import { oneClickBody, verifyUnsubscribeToken } from "../_shared/mailing.js";
import { empty, html, json, readFields } from "../_shared/http.js";
import { serviceClient } from "../_shared/db.js";

Deno.serve(async (req) => {
  if (req.method === "OPTIONS") return empty();
  const url = new URL(req.url);
  const token = url.searchParams.get("token") || "";
  const secret = Deno.env.get("UNSUBSCRIBE_HMAC_SECRET") || "";
  const claims = await verifyUnsubscribeToken(token, secret);
  if (!claims) {
    const message = "This unsubscribe link is not signed for this list.";
    return req.method === "GET" ? html(400, "Link not valid", message) : json(400, { ok: false, error: "invalid_token", message });
  }
  const db = serviceClient();
  const { data, error } = await db.from("subscribers").select("id,email,status").eq("id", claims.sid).maybeSingle();
  if (error) return json(500, { ok: false, error: "store", message: error.message });
  if (!data || data.email !== claims.email) {
    const message = "This unsubscribe link does not match a subscriber.";
    return req.method === "GET" ? html(400, "Link not valid", message) : json(400, { ok: false, error: "unknown_subscriber", message });
  }

  if (req.method === "GET") {
    // Opening the link does not unsubscribe. RFC 8058 one-click is the POST below.
    const form = `<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>Confirm unsubscribe</title></head>
<body style="margin:0;background:#f4f1ea;color:#1c1917;font-family:Georgia,serif;">
<main style="max-width:32rem;margin:4rem auto;padding:0 1.25rem;">
<p style="font-size:0.95rem;color:#0f5c5c;">Open Health Signals</p>
<h1 style="font-weight:normal;">Confirm unsubscribe</h1>
<p style="line-height:1.5;">${escapeHtml(data.email)} is still ${escapeHtml(data.status)}. Submit to unsubscribe. It takes effect immediately.</p>
<form method="post" action="${escapeHtml(url.pathname + url.search)}">
<button type="submit" name="List-Unsubscribe" value="One-Click">Unsubscribe</button>
</form>
</main></body></html>`;
    return new Response(form, { status: 200, headers: { "content-type": "text/html; charset=utf-8", "access-control-allow-origin": "*" } });
  }

  if (req.method !== "POST") return json(405, { ok: false, error: "method" });
  const { raw } = await readFields(req);
  if (!oneClickBody(raw) && !oneClickBody(url.search)) {
    return json(400, { ok: false, error: "one_click_required", message: "POST List-Unsubscribe=One-Click to unsubscribe." });
  }
  const { error: updateError } = await db
    .from("subscribers")
    .update({ status: "unsubscribed", unsubscribed_at: new Date().toISOString(), confirm_token_hash: null })
    .eq("id", data.id);
  if (updateError) return json(500, { ok: false, error: "store", message: updateError.message });
  return json(200, { ok: true, status: "unsubscribed", message: `${data.email} is unsubscribed. This took effect immediately.` });
});

function escapeHtml(value: string) {
  return value.replaceAll("&", "&amp;").replaceAll("<", "&lt;").replaceAll(">", "&gt;").replaceAll('"', "&quot;");
}
