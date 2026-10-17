"use client";

import { useEffect, useState } from "react";

import { FormStatus, messageForError, readApi } from "@/components/form-status";
import { Button } from "@/components/ui/button";
import { functionsBase } from "@/lib/functions";

export function UnsubscribePanel() {
  const [token, setToken] = useState("");
  const [ready, setReady] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [pending, setPending] = useState(false);

  useEffect(() => {
    setToken(new URLSearchParams(window.location.search).get("token") || "");
    setReady(true);
  }, []);

  async function unsubscribe() {
    const base = functionsBase();
    setError("");
    if (!token) return;
    if (!base) {
      setError(messageForError("unavailable"));
      return;
    }
    setPending(true);
    try {
      const response = await fetch(`${base}/unsubscribe?token=${encodeURIComponent(token)}`, {
        method: "POST",
        headers: { "content-type": "application/x-www-form-urlencoded", accept: "application/json" },
        body: "List-Unsubscribe=One-Click",
      });
      const payload = await readApi(response);
      if (response.ok && payload.ok) {
        setSuccess("You're unsubscribed.");
        return;
      }
      setError(messageForError(payload.error || "invalid_token"));
    } catch {
      setError(messageForError("network"));
    } finally {
      setPending(false);
    }
  }

  if (!ready) {
    return <p className="text-lg text-muted-foreground">Reading the link…</p>;
  }

  if (!token) {
    return (
      <FormStatus
        tone="error"
        message="Use the unsubscribe link in a briefing. This page does not take a typed email."
      />
    );
  }

  if (success) {
    return <FormStatus tone="success" message={success} />;
  }

  return (
    <div className="space-y-3">
      {error ? <FormStatus tone="error" message={error} /> : null}
      <p className="text-sm leading-relaxed">This link is signed. Unsubscribe takes effect immediately.</p>
      <Button type="button" size="lg" onClick={unsubscribe} disabled={pending}>
        {pending ? "Sending..." : "Unsubscribe"}
      </Button>
    </div>
  );
}
