import { sha256Hex } from "../_shared/mailing.js";
import { empty, html, json, readFields } from "../_shared/http.js";
import { serviceClient } from "../_shared/db.js";

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
  const { data, error } = await db.from("subscribers").select("id,status").eq("confirm_token_hash", hash).maybeSingle();
  if (error) return json(500, { ok: false, error: "store", message: error.message });
  if (!data) return fail(400, "invalid_token", "This confirmation link does not match. Subscribe again from the dashboard.");
  if (data.status === "bounced" || data.status === "complained") {
    const message = "This address was suppressed after a bounce or a complaint.";
    return wantsJson ? json(409, { ok: false, error: "suppressed", message }) : html(409, "Address suppressed", message);
  }
  if (data.status !== "active") {
    const { error: updateError } = await db
      .from("subscribers")
      .update({ status: "active", confirmed_at: new Date().toISOString() })
      .eq("id", data.id);
    if (updateError) return json(500, { ok: false, error: "store", message: updateError.message });
  }
  const message = "You are confirmed. The next briefing goes out after the Monday draft is approved.";
  return wantsJson ? json(200, { ok: true, status: "active", message }) : html(200, "You are confirmed", message);
});
