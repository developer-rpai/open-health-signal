"use client";

import { useEffect, useState } from "react";

import { FormStatus, messageForError, readApi } from "@/components/form-status";
import { functionsBase } from "@/lib/functions";

export function ConfirmPanel() {
  const [phase, setPhase] = useState<"loading" | "success" | "error">("loading");
  const [message, setMessage] = useState("Checking the confirmation link…");

  useEffect(() => {
    const token = new URLSearchParams(window.location.search).get("token") || "";
    const base = functionsBase();
    if (!token) {
      setPhase("error");
      setMessage("This confirmation link has expired or does not match. Subscribe again to get a new one.");
      return;
    }
    if (!base) {
      setPhase("error");
      setMessage(messageForError("unavailable"));
      return;
    }
    let cancelled = false;
    fetch(`${base}/confirm?token=${encodeURIComponent(token)}`, {
      method: "POST",
      headers: { accept: "application/json", "content-type": "application/json" },
      body: JSON.stringify({ token }),
    })
      .then(async (response) => {
        const payload = await readApi(response);
        if (cancelled) return;
        if (response.ok && payload.ok && payload.status === "active") {
          setPhase("success");
          setMessage("You're confirmed. The next briefing will include this address.");
          return;
        }
        setPhase("error");
        setMessage(
          payload.error === "invalid_token" || !payload.error
            ? "This confirmation link has expired or does not match. Subscribe again to get a new one."
            : messageForError(payload.error),
        );
      })
      .catch(() => {
        if (!cancelled) {
          setPhase("error");
          setMessage(messageForError("network"));
        }
      });
    return () => {
      cancelled = true;
    };
  }, []);

  if (phase === "loading") {
    return (
      <p className="text-lg leading-relaxed text-muted-foreground" role="status" aria-live="polite">
        {message}
      </p>
    );
  }

  return <FormStatus tone={phase === "success" ? "success" : "error"} message={message} />;
}
