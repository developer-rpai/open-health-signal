import { createClient } from "https://esm.sh/@supabase/supabase-js@2.49.1";
import { maskRecipient } from "./transactional.js";

export function serviceClient() {
  const url = Deno.env.get("SUPABASE_URL") || "";
  const key = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY") || "";
  if (!url || !key) throw new Error("Supabase service role is not configured");
  return createClient(url, key, { auth: { persistSession: false } });
}

export function dryRun() {
  return (Deno.env.get("NEWSLETTER_DRY_RUN") || "") !== "0";
}

export async function sendResend({ to, subject, text, html, replyTo, headers, from }) {
  const apiKey = Deno.env.get("RESEND_API_KEY") || "";
  const sender = (from || Deno.env.get("NEWSLETTER_FROM") || "").trim();
  const logged = {
    to: maskRecipient(to),
    subject,
    from: sender,
    reply_to: replyTo ? maskRecipient(replyTo) : null,
  };
  try {
    if (dryRun()) {
      console.log(JSON.stringify({ transactional: "dry_run", ...logged }));
      return { id: null, dry_run: true };
    }
    if (!apiKey || !sender) {
      console.error(JSON.stringify({ transactional: "skipped", reason: "not_configured", ...logged }));
      return { id: null, error: "not_configured" };
    }
    const body = { from: sender, to: [to], subject, text, html };
    if (replyTo) body.reply_to = replyTo;
    if (headers && Object.keys(headers).length) body.headers = headers;
    const response = await fetch("https://api.resend.com/emails", {
      method: "POST",
      headers: { authorization: `Bearer ${apiKey}`, "content-type": "application/json" },
      body: JSON.stringify(body),
    });
    if (!response.ok) {
      console.error(JSON.stringify({ transactional: "failed", status: response.status, ...logged }));
      return { id: null, error: "send_failed" };
    }
    return await response.json();
  } catch (error) {
    console.error(JSON.stringify({ transactional: "failed", error: String(error), ...logged }));
    return { id: null, error: "send_failed" };
  }
}
