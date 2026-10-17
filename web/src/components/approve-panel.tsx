"use client";

import { useEffect, useState } from "react";

import { FormStatus, messageForError, readApi } from "@/components/form-status";
import { Button } from "@/components/ui/button";
import { functionsBase, localPreview, siteUrl, supabasePublic } from "@/lib/functions";

type Issue = {
  slug: string;
  subject: string;
  headline?: string;
  html: string;
  status: string;
};

type Session = { email: string; accessToken?: string };

export function ApprovePanel() {
  const [email, setEmail] = useState("");
  const [session, setSession] = useState<Session | null>(null);
  const [issues, setIssues] = useState<Issue[]>([]);
  const [notice, setNotice] = useState<{ tone: "success" | "error"; message: string } | null>(null);
  const [pending, setPending] = useState(false);
  const supabase = supabasePublic();
  const preview = localPreview() && !supabase.url;

  useEffect(() => {
    if (!supabase.url || !supabase.anonKey) return;
    let cancelled = false;
    import("@supabase/supabase-js").then(async ({ createClient }) => {
      const client = createClient(supabase.url, supabase.anonKey);
      const { data } = await client.auth.getSession();
      const current = data.session;
      if (!current?.user.email || cancelled) return;
      setSession({ email: current.user.email, accessToken: current.access_token });
      const { data: rows, error } = await client
        .from("issues")
        .select("slug,subject,headline,html,status")
        .eq("status", "draft");
      if (cancelled) return;
      if (error) {
        setNotice({ tone: "error", message: messageForError("not_allowlisted") });
        return;
      }
      setIssues((rows || []) as Issue[]);
    });
    return () => {
      cancelled = true;
    };
  }, [supabase.anonKey, supabase.url]);

  async function requestLink(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const address = email.trim();
    setNotice(null);
    setPending(true);
    try {
      if (supabase.url && supabase.anonKey) {
        const { createClient } = await import("@supabase/supabase-js");
        const client = createClient(supabase.url, supabase.anonKey);
        const redirect = `${siteUrl() || window.location.origin}/approve`;
        const { error } = await client.auth.signInWithOtp({ email: address, options: { emailRedirectTo: redirect } });
        if (error) {
          setNotice({ tone: "error", message: messageForError("invalid_email") });
          return;
        }
        setNotice({
          tone: "success",
          message: `Check your inbox. We sent a sign-in link to ${address}.`,
        });
        return;
      }
      if (!preview) {
        setNotice({ tone: "error", message: messageForError("unavailable") });
        return;
      }
      const response = await fetch(`${functionsBase()}/auth/magic-link`, {
        method: "POST",
        headers: { "content-type": "application/json", accept: "application/json" },
        body: JSON.stringify({ email: address }),
      });
      const payload = await readApi(response);
      if (!response.ok || !payload.ok) {
        setNotice({ tone: "error", message: messageForError(payload.error || "not_allowlisted") });
        return;
      }
      setSession({ email: address });
      const issuesResponse = await fetch(`${functionsBase()}/issues`, { headers: { accept: "application/json" } });
      const body = (await issuesResponse.json()) as { issues?: Issue[] };
      setIssues((body.issues || []).filter((issue) => issue.status === "draft"));
      setNotice(null);
    } catch {
      setNotice({ tone: "error", message: messageForError("network") });
    } finally {
      setPending(false);
    }
  }

  async function approve(slug: string) {
    setPending(true);
    setNotice(null);
    try {
      if (supabase.url && session?.accessToken) {
        const { createClient } = await import("@supabase/supabase-js");
        const client = createClient(supabase.url, supabase.anonKey);
        const { error } = await client.from("issues").update({ status: "approved", approved_at: new Date().toISOString() }).eq("slug", slug);
        if (error) {
          setNotice({ tone: "error", message: messageForError("not_allowlisted") });
          return;
        }
        const response = await fetch(`${functionsBase()}/dispatch-send`, {
          method: "POST",
          headers: {
            "content-type": "application/json",
            accept: "application/json",
            authorization: `Bearer ${session.accessToken}`,
          },
          body: JSON.stringify({ slug }),
        });
        const payload = await readApi(response);
        if (!response.ok || payload.ok === false) {
          setNotice({ tone: "error", message: messageForError(payload.error) });
          return;
        }
        setNotice({ tone: "success", message: "Approved. The send has been requested." });
        setIssues((current) => current.filter((issue) => issue.slug !== slug));
        return;
      }
      const response = await fetch(`${functionsBase()}/issues/${slug}/approve`, {
        method: "POST",
        headers: { accept: "application/json" },
      });
      const payload = await readApi(response);
      if (!response.ok || payload.ok === false) {
        setNotice({ tone: "error", message: messageForError(payload.error) });
        return;
      }
      setNotice({
        tone: "success",
        message: payload.sent ? "Approved. The issue was sent." : "Approved. Nothing was emailed.",
      });
      setIssues((current) => current.map((issue) => (issue.slug === slug ? { ...issue, status: payload.status || "approved" } : issue)));
    } catch {
      setNotice({ tone: "error", message: messageForError("network") });
    } finally {
      setPending(false);
    }
  }

  if (!session) {
    if (notice?.tone === "success") {
      return <FormStatus tone="success" message={notice.message} />;
    }
    return (
      <form onSubmit={requestLink} className="max-w-md space-y-3 rounded-2xl bg-card p-6 ring-1 ring-foreground/10">
        {notice ? <FormStatus tone={notice.tone} message={notice.message} /> : null}
        <label htmlFor="owner-email" className="text-sm font-medium">
          Owner email
        </label>
        <input
          id="owner-email"
          type="email"
          required
          value={email}
          onChange={(event) => setEmail(event.target.value)}
          placeholder="owner@example.com"
          autoComplete="email"
          disabled={pending}
          className="h-9 w-full rounded-lg border border-input bg-transparent px-3 text-sm"
        />
        <Button type="submit" size="lg" disabled={pending}>
          {pending ? "Sending..." : "Email me a sign-in link"}
        </Button>
      </form>
    );
  }

  const drafts = issues.filter((issue) => issue.status === "draft");
  return (
    <div className="space-y-6">
      <p className="text-sm text-muted-foreground">Signed in as {session.email}.</p>
      {notice ? <FormStatus tone={notice.tone} message={notice.message} /> : null}
      {drafts.length === 0 ? (
        <p className="rounded-xl border border-dashed px-4 py-10 text-sm text-muted-foreground">No draft is waiting.</p>
      ) : (
        drafts.map((issue) => (
          <section key={issue.slug} className="space-y-4 rounded-2xl bg-card p-4 ring-1 ring-foreground/10 sm:p-6">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div>
                <p className="font-mono text-[11px] tracking-[0.16em] text-primary uppercase">{issue.slug}</p>
                <h2 className="text-2xl">{issue.headline || issue.subject}</h2>
              </div>
              <Button type="button" size="lg" disabled={pending} onClick={() => approve(issue.slug)}>
                {pending ? "Sending..." : "Approve and send"}
              </Button>
            </div>
            <iframe title={`Preview ${issue.slug}`} sandbox="" srcDoc={issue.html} className="h-[32rem] w-full rounded-xl bg-white" />
          </section>
        ))
      )}
    </div>
  );
}
