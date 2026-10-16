import { createClient } from "https://esm.sh/@supabase/supabase-js@2.49.1";

export function serviceClient() {
  const url = Deno.env.get("SUPABASE_URL") || "";
  const key = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY") || "";
  if (!url || !key) throw new Error("Supabase service role is not configured");
  return createClient(url, key, { auth: { persistSession: false } });
}

export function dryRun() {
  const value = (Deno.env.get("NEWSLETTER_DRY_RUN") || "").trim().toLowerCase();
  return value === "" || value === "1" || value === "true" || value === "yes";
}

export async function sendResend({ to, subject, text, html }) {
  if (dryRun()) return { id: null, dry_run: true };
  const apiKey = Deno.env.get("RESEND_API_KEY") || "";
  const from = Deno.env.get("NEWSLETTER_FROM") || "";
  if (!apiKey || !from) throw new Error("Resend is not configured");
  const response = await fetch("https://api.resend.com/emails", {
    method: "POST",
    headers: { authorization: `Bearer ${apiKey}`, "content-type": "application/json" },
    body: JSON.stringify({ from, to: [to], subject, text, html }),
  });
  if (!response.ok) throw new Error(`Resend returned ${response.status}`);
  return response.json();
}
