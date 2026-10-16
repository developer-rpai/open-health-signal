"use client";

import { useState } from "react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { subscribeConfig } from "@/lib/newsletter-config";

export function UnsubscribeForm() {
  const config = subscribeConfig();
  const [address, setAddress] = useState("");
  const username = process.env.NEXT_PUBLIC_BUTTONDOWN_USERNAME?.trim() || "";
  const usernameOk = /^[A-Za-z0-9_-]+$/.test(username);

  if (address) {
    return (
      <p className="text-sm leading-relaxed">
        Request received for {address}. Opt-outs are honored within ten business days. The one-click link in each
        sent briefing is created for that address by the email processor. New subscriptions still require the
        confirmation email.
      </p>
    );
  }

  return (
    <form
      className="space-y-3"
      onSubmit={(event) => {
        event.preventDefault();
        const data = new FormData(event.currentTarget);
        const email = String(data.get("email") || "").trim();
        if (email) setAddress(email);
      }}
    >
      <label htmlFor="unsubscribe-email" className="text-sm font-medium">
        Email
      </label>
      <Input id="unsubscribe-email" name="email" type="email" required autoComplete="email" placeholder="you@example.com" />
      <Button type="submit" size="lg">
        Unsubscribe
      </Button>
      <p className="text-sm leading-relaxed text-muted-foreground">
        {config.provider === "buttondown" && usernameOk ? (
          <a className="text-primary underline-offset-2 hover:underline" href={`https://buttondown.com/${username}`}>
            Open the Buttondown page for this list.
          </a>
        ) : (
          "The one-click link in each sent issue is filled in by Buttondown for that recipient."
        )}
      </p>
    </form>
  );
}
