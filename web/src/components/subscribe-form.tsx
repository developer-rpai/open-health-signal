"use client";

import { useState } from "react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { functionsBase, localPreview } from "@/lib/functions";

const CONSENT =
  "I agree to receive the weekly Inflammation Signal Monitor briefing by email. A confirmation message comes first. I am added only after I open that link, and I can unsubscribe from any issue.";

export function SubscribeForm({ id }: { id?: string }) {
  const base = functionsBase();
  const formId = id ?? "subscribe";
  const [message, setMessage] = useState("");
  const [confirmUrl, setConfirmUrl] = useState("");
  const [pending, setPending] = useState(false);
  const configured = base.startsWith("http://") || base.startsWith("https://");

  async function onSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const data = new FormData(event.currentTarget);
    setPending(true);
    setMessage("");
    setConfirmUrl("");
    try {
      const response = await fetch(`${base}/subscribe`, {
        method: "POST",
        headers: { "content-type": "application/json", accept: "application/json" },
        body: JSON.stringify({ email: String(data.get("email") || ""), consent: data.get("consent") ? "yes" : "no" }),
      });
      const payload = (await response.json()) as { message?: string; confirm_url?: string; ok?: boolean };
      setMessage(payload.message || (response.ok ? "Check your inbox." : "The list did not accept that address."));
      if (payload.confirm_url && localPreview()) setConfirmUrl(payload.confirm_url);
    } catch {
      setMessage("The subscribe service did not respond.");
    } finally {
      setPending(false);
    }
  }

  return (
    <form id={formId} className="space-y-3" onSubmit={onSubmit} aria-describedby={`${formId}-note`}>
      <div className="space-y-1.5">
        <label htmlFor={`${formId}-email`} className="text-sm font-medium">
          Email
        </label>
        <Input
          id={`${formId}-email`}
          name="email"
          type="email"
          required
          autoComplete="email"
          placeholder="you@example.com"
          disabled={!configured || pending}
        />
      </div>
      <label htmlFor={`${formId}-consent`} className="flex items-start gap-2 text-sm leading-snug text-muted-foreground">
        <input
          id={`${formId}-consent`}
          name="consent"
          type="checkbox"
          value="yes"
          required
          disabled={!configured || pending}
          className="mt-0.5 size-4 shrink-0 accent-primary"
        />
        <span>{CONSENT}</span>
      </label>
      <Button type="submit" size="lg" disabled={!configured || pending}>
        {pending ? "Sending confirmation…" : "Subscribe"}
      </Button>
      <p id={`${formId}-note`} className="text-xs leading-relaxed text-muted-foreground">
        {configured
          ? "A confirmation email comes first. The address stays pending until that link is opened."
          : "This build has no functions URL. Set NEXT_PUBLIC_FUNCTIONS_BASE and rebuild. The list stays empty until you confirm."}
      </p>
      {message ? <p className="text-sm leading-relaxed">{message}</p> : null}
      {confirmUrl ? (
        <p className="text-sm leading-relaxed">
          Local preview: no confirmation email was sent.{" "}
          <a className="text-primary underline underline-offset-2" href={confirmUrl}>
            Open the confirmation link
          </a>
          .
        </p>
      ) : null}
    </form>
  );
}
