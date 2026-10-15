"use client";

import { useId } from "react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { subscribeConfig } from "@/lib/newsletter-config";

export function SubscribeForm({ id }: { id?: string }) {
  const config = subscribeConfig();
  const generated = useId();
  const formId = id ?? generated;
  const emailId = `${formId}-email`;
  const consentId = `${formId}-consent`;

  return (
    <form
      id={formId}
      action={config.configured ? config.action : undefined}
      method="post"
      className="space-y-3"
      aria-describedby={`${formId}-note`}
    >
      {config.provider === "buttondown" && config.configured ? <input type="hidden" name="embed" value="1" /> : null}
      <div className="space-y-1.5">
        <label htmlFor={emailId} className="text-sm font-medium">
          Email
        </label>
        <Input
          id={emailId}
          name="email"
          type="email"
          required
          autoComplete="email"
          placeholder="you@example.com"
          disabled={!config.configured}
        />
      </div>
      <label htmlFor={consentId} className="flex items-start gap-2 text-sm leading-snug text-muted-foreground">
        <input
          id={consentId}
          name="consent"
          type="checkbox"
          value="yes"
          required
          disabled={!config.configured}
          className="mt-0.5 size-4 shrink-0 accent-primary"
        />
        <span>{config.consent}</span>
      </label>
      <Button type={config.configured ? "submit" : "button"} size="lg" disabled={!config.configured}>
        Subscribe
      </Button>
      <p id={`${formId}-note`} className="text-xs leading-relaxed text-muted-foreground">
        {config.note}
      </p>
    </form>
  );
}
