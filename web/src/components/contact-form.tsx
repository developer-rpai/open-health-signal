"use client";

import { useEffect, useRef, useState } from "react";

import { FormStatus, messageForError, readApi } from "@/components/form-status";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { MEDWATCH_URL } from "@/lib/compliance";
import { functionsBase, turnstileSiteKey } from "@/lib/functions";

const INTERESTS = [
  ["research_collaboration", "Research collaboration"],
  ["data_expansion", "Data expansion"],
  ["code_contribution", "Code contribution"],
  ["custom_analysis", "Custom analysis"],
  ["media", "Media"],
  ["sponsorship", "Sponsorship"],
] as const;

type TurnstileApi = {
  render: (element: HTMLElement, options: { sitekey: string; callback: (token: string) => void }) => void;
};

export function ContactForm() {
  const base = functionsBase();
  const siteKey = turnstileSiteKey();
  const widget = useRef<HTMLDivElement>(null);
  const [token, setToken] = useState("");
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [pending, setPending] = useState(false);
  const configured = Boolean(base) && Boolean(siteKey);

  useEffect(() => {
    const timer = window.setInterval(() => {
      const input = widget.current?.querySelector<HTMLInputElement>("input[name='cf-turnstile-response']");
      if (input?.value) setToken(input.value);
    }, 300);
    return () => window.clearInterval(timer);
  }, []);

  useEffect(() => {
    if (!siteKey || !widget.current) return;
    let cancelled = false;
    const render = () => {
      const api = (window as Window & { turnstile?: TurnstileApi }).turnstile;
      if (!api || !widget.current || cancelled) return;
      api.render(widget.current, { sitekey: siteKey, callback: (value) => setToken(value) });
    };
    const existing = document.querySelector<HTMLScriptElement>("script[data-turnstile]");
    if (existing) {
      if ((window as Window & { turnstile?: TurnstileApi }).turnstile) render();
      else existing.addEventListener("load", render);
      return () => {
        cancelled = true;
      };
    }
    const script = document.createElement("script");
    script.src = "https://challenges.cloudflare.com/turnstile/v0/api.js?render=explicit";
    script.async = true;
    script.dataset.turnstile = "1";
    script.onload = render;
    document.body.appendChild(script);
    return () => {
      cancelled = true;
    };
  }, [siteKey]);

  async function onSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const data = new FormData(event.currentTarget);
    setError("");
    if (!configured) {
      setError(messageForError("unavailable"));
      return;
    }
    setPending(true);
    try {
      const response = await fetch(`${base}/contact`, {
        method: "POST",
        headers: { "content-type": "application/json", accept: "application/json" },
        body: JSON.stringify({
          name: String(data.get("name") || ""),
          email: String(data.get("email") || ""),
          organization: String(data.get("organization") || ""),
          role: String(data.get("role") || ""),
          interest_type: String(data.get("interest_type") || ""),
          message: String(data.get("message") || ""),
          link: String(data.get("link") || ""),
          turnstile_token: token,
        }),
      });
      const payload = await readApi(response);
      if (response.ok && payload.ok) {
        setSuccess("Thanks, your message was sent. We'll reply by email.");
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
    return <FormStatus tone="success" message={success} />;
  }

  return (
    <form className="space-y-3" onSubmit={onSubmit} aria-busy={pending}>
      {error ? <FormStatus tone="error" message={error} /> : null}
      <Field id="contact-name" name="name" label="Name" required disabled={!configured || pending} />
      <Field id="contact-email" name="email" label="Email" type="email" required disabled={!configured || pending} />
      <Field id="contact-organization" name="organization" label="Organization (optional)" disabled={!configured || pending} />
      <Field id="contact-role" name="role" label="Role (optional)" disabled={!configured || pending} />
      <div className="space-y-1.5">
        <label htmlFor="contact-interest" className="text-sm font-medium">
          Interest
        </label>
        <select
          id="contact-interest"
          name="interest_type"
          required
          disabled={!configured || pending}
          defaultValue=""
          className="h-9 w-full rounded-lg border border-input bg-transparent px-3 text-sm"
        >
          <option value="" disabled>
            Choose one
          </option>
          {INTERESTS.map(([value, label]) => (
            <option key={value} value={value}>
              {label}
            </option>
          ))}
        </select>
      </div>
      <div className="space-y-1.5">
        <label htmlFor="contact-message" className="text-sm font-medium">
          Message
        </label>
        <p className="text-sm leading-relaxed text-muted-foreground">
          Please do not include personal health information. To report a side effect to the FDA, use{" "}
          <a className="underline underline-offset-2 hover:text-foreground" href={MEDWATCH_URL}>
            MedWatch
          </a>
          .
        </p>
        <textarea
          id="contact-message"
          name="message"
          required
          rows={5}
          disabled={!configured || pending}
          className="w-full rounded-lg border border-input bg-transparent px-3 py-2 text-sm"
        />
      </div>
      <Field id="contact-link" name="link" label="Link (optional)" type="url" disabled={!configured || pending} />
      <div ref={widget} className="min-h-16" />
      <Button type="submit" size="lg" disabled={!configured || pending || !token}>
        {pending ? "Sending..." : "Send message"}
      </Button>
      <p className="text-xs leading-relaxed text-muted-foreground">
        {configured
          ? "Cloudflare Turnstile checks this form. Messages are stored for up to 12 months."
          : "The contact form is not available on this copy of the site."}
      </p>
    </form>
  );
}

function Field({
  id,
  name,
  label,
  type = "text",
  required = false,
  disabled = false,
}: {
  id: string;
  name: string;
  label: string;
  type?: string;
  required?: boolean;
  disabled?: boolean;
}) {
  return (
    <div className="space-y-1.5">
      <label htmlFor={id} className="text-sm font-medium">
        {label}
      </label>
      <Input id={id} name={name} type={type} required={required} disabled={disabled} />
    </div>
  );
}
