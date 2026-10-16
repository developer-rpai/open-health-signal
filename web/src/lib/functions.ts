export function functionsBase(): string {
  return (process.env.NEXT_PUBLIC_FUNCTIONS_BASE || "").replace(/\/$/, "");
}

export function localPreview(): boolean {
  return process.env.NEXT_PUBLIC_LOCAL_PREVIEW === "1";
}

export function turnstileSiteKey(): string {
  return (process.env.NEXT_PUBLIC_TURNSTILE_SITE_KEY || "").trim();
}

export function supabasePublic(): { url: string; anonKey: string } {
  return {
    url: (process.env.NEXT_PUBLIC_SUPABASE_URL || "").replace(/\/$/, ""),
    anonKey: (process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY || "").trim(),
  };
}

export function siteUrl(): string {
  return (process.env.NEXT_PUBLIC_SITE_URL || "").replace(/\/$/, "");
}
