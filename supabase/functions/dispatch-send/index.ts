import { empty, json, readFields } from "../_shared/http.js";
import { serviceClient } from "../_shared/db.js";
import { createClient } from "https://esm.sh/@supabase/supabase-js@2.49.1";

// Owner approval calls this with the magic-link session.
// It asks GitHub Actions to run the send job. The Action stays a dry run
// until NEWSLETTER_DRY_RUN is set to 0 on the repository.

Deno.serve(async (req) => {
  if (req.method === "OPTIONS") return empty();
  if (req.method !== "POST") return json(405, { ok: false, error: "method" });
  const header = req.headers.get("authorization") || "";
  const url = Deno.env.get("SUPABASE_URL") || "";
  const anon = Deno.env.get("SUPABASE_ANON_KEY") || "";
  if (!header.toLowerCase().startsWith("bearer ") || !url || !anon) {
    return json(401, { ok: false, error: "auth", message: "Sign in with the owner magic link first." });
  }
  const userClient = createClient(url, anon, {
    auth: { persistSession: false },
    global: { headers: { Authorization: header } },
  });
  const { data: userData, error: userError } = await userClient.auth.getUser();
  if (userError || !userData.user?.email) {
    return json(401, { ok: false, error: "auth", message: "Sign in with the owner magic link first." });
  }
  const db = serviceClient();
  const { data: allowed } = await db.from("owner_allowlist").select("email").eq("email", userData.user.email.toLowerCase()).maybeSingle();
  if (!allowed) return json(403, { ok: false, error: "not_allowlisted", message: "This email is not on the owner allowlist." });

  const { fields } = await readFields(req);
  const slug = (fields.slug || "").trim();
  const token = Deno.env.get("GITHUB_DISPATCH_TOKEN") || "";
  const repo = Deno.env.get("GITHUB_REPOSITORY") || "";
  if (!token || !repo) {
    return json(200, {
      ok: true,
      dispatched: false,
      dry_run: true,
      message: "Approved. The send workflow is not connected, so nothing was emailed.",
    });
  }
  const response = await fetch(`https://api.github.com/repos/${repo}/dispatches`, {
    method: "POST",
    headers: {
      authorization: `Bearer ${token}`,
      accept: "application/vnd.github+json",
      "content-type": "application/json",
    },
    body: JSON.stringify({ event_type: "issue-approved", client_payload: { slug } }),
  });
  if (!response.ok) return json(502, { ok: false, error: "dispatch", message: "GitHub did not accept the send request." });
  return json(200, { ok: true, dispatched: true, message: "Approved. The send workflow is running." });
});
