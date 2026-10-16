import { suppressionFromResendEvent, verifySvix } from "../_shared/mailing.js";
import { empty, json } from "../_shared/http.js";
import { serviceClient } from "../_shared/db.js";

Deno.serve(async (req) => {
  if (req.method === "OPTIONS") return empty();
  if (req.method !== "POST") return json(405, { ok: false, error: "method" });
  const raw = await req.text();
  const body = new TextEncoder().encode(raw);
  const ok = await verifySvix({
    secret: Deno.env.get("RESEND_WEBHOOK_SECRET") || "",
    body,
    svixId: req.headers.get("svix-id") || "",
    svixTimestamp: req.headers.get("svix-timestamp") || "",
    svixSignature: req.headers.get("svix-signature") || "",
  });
  if (!ok) return json(401, { ok: false, error: "invalid_signature" });
  let event: { type?: string; data?: { to?: string[] | string } };
  try {
    event = JSON.parse(raw || "{}");
  } catch {
    return json(400, { ok: false, error: "invalid_json" });
  }
  const change = suppressionFromResendEvent(event);
  if (!change) return json(200, { ok: true, suppressed: false });
  const db = serviceClient();
  const { data, error } = await db.from("subscribers").select("id").eq("email", change.email).maybeSingle();
  if (error) return json(500, { ok: false, error: "store", message: error.message });
  if (!data) return json(200, { ok: true, suppressed: false, reason: "unknown_subscriber" });
  const { error: updateError } = await db.from("subscribers").update({ status: change.status }).eq("id", data.id);
  if (updateError) return json(500, { ok: false, error: "store", message: updateError.message });
  return json(200, { ok: true, suppressed: true, status: change.status, email: change.email });
});
