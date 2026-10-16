"use client";

import { useEffect, useState } from "react";

import { Button } from "@/components/ui/button";
import { functionsBase } from "@/lib/functions";

export function UnsubscribePanel() {
  const [token, setToken] = useState("");
  const [ready, setReady] = useState(false);
  const [message, setMessage] = useState("");
  const [pending, setPending] = useState(false);
  const [done, setDone] = useState(false);

  useEffect(() => {
    setToken(new URLSearchParams(window.location.search).get("token") || "");
    setReady(true);
  }, []);

  async function unsubscribe() {
    const base = functionsBase();
    if (!token || !base) return;
    setPending(true);
    try {
      const response = await fetch(`${base}/unsubscribe?token=${encodeURIComponent(token)}`, {
        method: "POST",
        headers: { "content-type": "application/x-www-form-urlencoded", accept: "application/json" },
        body: "List-Unsubscribe=One-Click",
      });
      const payload = (await response.json()) as { message?: string };
      setDone(response.ok);
      setMessage(payload.message || "The unsubscribe service did not accept that link.");
    } catch {
      setMessage("The unsubscribe service did not respond.");
    } finally {
      setPending(false);
    }
  }

  if (!ready) {
    return <p className="text-sm text-muted-foreground">Reading the link…</p>;
  }

  if (!token) {
    return (
      <p className="text-sm leading-relaxed text-muted-foreground">
        Use the unsubscribe link in a briefing. It is signed for one address. This page does not take a typed email,
        because an unsigned request cannot change the list.
      </p>
    );
  }

  if (done) {
    return <p className="text-sm leading-relaxed">{message}</p>;
  }

  return (
    <div className="space-y-3">
      <p className="text-sm leading-relaxed">
        This link is signed. Unsubscribe takes effect immediately, including for the one-click header a mail client
        sends.
      </p>
      <Button type="button" size="lg" onClick={unsubscribe} disabled={pending || !functionsBase()}>
        {pending ? "Unsubscribing…" : "Unsubscribe"}
      </Button>
      {!functionsBase() ? (
        <p className="text-xs text-muted-foreground">This build has no functions URL, so the list cannot be changed.</p>
      ) : null}
      {message ? <p className="text-sm leading-relaxed">{message}</p> : null}
    </div>
  );
}
