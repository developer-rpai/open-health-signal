export const corsHeaders = {
  "access-control-allow-origin": "*",
  "access-control-allow-headers": "authorization, content-type, accept, apikey, x-client-info",
  "access-control-allow-methods": "GET, POST, OPTIONS",
};

export function json(status, payload) {
  return new Response(JSON.stringify(payload), {
    status,
    headers: { ...corsHeaders, "content-type": "application/json" },
  });
}

export function html(status, title, message) {
  const safeTitle = escapeHtml(title);
  const safeMessage = escapeHtml(message);
  const document = `<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>${safeTitle}</title></head>
<body style="margin:0;background:#f4f1ea;color:#1c1917;font-family:Georgia,serif;">
<main style="max-width:32rem;margin:4rem auto;padding:0 1.25rem;">
<p style="letter-spacing:0.14em;text-transform:uppercase;font-size:0.75rem;color:#0f5c5c;">Inflammation Signal Monitor</p>
<h1 style="font-weight:normal;">${safeTitle}</h1>
<p style="line-height:1.5;">${safeMessage}</p>
</main></body></html>`;
  return new Response(document, {
    status,
    headers: { ...corsHeaders, "content-type": "text/html; charset=utf-8" },
  });
}

export function empty(status = 204) {
  return new Response(null, { status, headers: corsHeaders });
}

export function clientIp(req) {
  const forwarded = req.headers.get("x-forwarded-for") || "";
  const first = forwarded.split(",")[0].trim();
  return first || "0.0.0.0";
}

export async function readFields(req) {
  const contentType = req.headers.get("content-type") || "";
  const raw = await req.text();
  if (contentType.includes("application/json")) {
    try {
      const payload = JSON.parse(raw || "{}");
      return { fields: Object.fromEntries(Object.entries(payload).map(([key, value]) => [key, value == null ? "" : String(value)])), raw };
    } catch {
      return { fields: {}, raw };
    }
  }
  const params = new URLSearchParams(raw);
  const fields = {};
  for (const [key, value] of params.entries()) fields[key] = value;
  return { fields, raw };
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}
