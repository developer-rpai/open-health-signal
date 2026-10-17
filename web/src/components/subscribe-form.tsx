"use client";

import Link from "next/link";
import { useState } from "react";

import { FormStatus, messageForError, readApi } from "@/components/form-status";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { functionsBase, localPreview } from "@/lib/functions";

export function SubscribeForm({ id }: { id?: string }) {
  const base = functionsBase();
  const formId = id ?? "subscribe";
  const [pending, setPending] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [confirmUrl, setConfirmUrl] = useState("");
  const configured = base.startsWith("http://") || base.startsWith("https://");

  async function onSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const data = new FormData(event.currentTarget);
    const email = String(data.get("email") || "").trim();
    setError("");
    setSuccess("");
    setConfirmUrl("");
    if (!configured) {
      setError(messageForError("unavailable"));
      return;
    }
    setPending(true);
    try {
      const response = await fetch(`${base}/subscribe`, {
        method: "POST",
        headers: { "content-type": "application/json", accept: "application/json" },
        body: JSON.stringify({ email, consent: data.get("consent") ? "yes" : "no" }),
      });
      const payload = await readApi(response);
      if (response.ok && payload.ok && (payload.status === "pending" || payload.status === "already_pending")) {
        setSuccess(`Check your inbox. We sent a confirmation link to ${email}. You're added once you click it.`);
        if (payload.confirm_url && localPreview()) setConfirmUrl(payload.confirm_url);
        return;
      }
      if (response.ok && payload.ok && payload.status === "active") {
        setSuccess(`${email} is already confirmed. No new confirmation was sent.`);
        return;
      }
      setError(messageForError(payload.error));
    } catch {
      setError(messageForError("network"));
    } finally {
      setPending(false);
    }
  }

  if (success) {
    return (
      <div className="space-y-3">
        <FormStatus tone="success" message={success} />
        {confirmUrl ? (
          <p className="text-sm leading-relaxed">
            <a className="text-primary underline underline-offset-2" href={confirmUrl}>
              Open the confirmation link
            </a>
          </p>
        ) : null}
      </div>
    );
  }

  return (
    <form id={formId} className="space-y-3" onSubmit={onSubmit} aria-busy={pending}>
      {error ? <FormStatus tone="error" message={error} /> : null}
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
        <span>
          I agree to receive the Open Health Signals briefing by email. A confirmation message comes first. I am added
          only after I open that link, and I can unsubscribe from any issue.{" "}
          <Link href="/privacy" className="underline underline-offset-2 hover:text-foreground">
            Privacy
          </Link>
          .
        </span>
      </label>
      <Button type="submit" size="lg" disabled={!configured || pending}>
        {pending ? "Sending..." : "Subscribe"}
      </Button>
      {!configured ? <FormStatus tone="error" message={messageForError("unavailable")} /> : null}
    </form>
  );
}
