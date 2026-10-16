"use client";

import { useEffect, useState } from "react";

import { functionsBase } from "@/lib/functions";

export function ConfirmPanel() {
  const [message, setMessage] = useState("Checking the confirmation link…");
  const [ok, setOk] = useState(false);

  useEffect(() => {
    const token = new URLSearchParams(window.location.search).get("token") || "";
    const base = functionsBase();
    if (!token) {
      setMessage("This page needs the token from the confirmation email.");
      return;
    }
    if (!base) {
      setMessage("This build has no functions URL, so the confirmation cannot be recorded.");
      return;
    }
    let cancelled = false;
    fetch(`${base}/confirm?token=${encodeURIComponent(token)}`, {
      method: "POST",
      headers: { accept: "application/json", "content-type": "application/json" },
      body: JSON.stringify({ token }),
    })
      .then(async (response) => {
        const payload = (await response.json()) as { message?: string };
        if (cancelled) return;
        setOk(response.ok);
        setMessage(payload.message || "The confirmation link could not be checked.");
      })
      .catch(() => {
        if (!cancelled) setMessage("The confirmation service did not respond.");
      });
    return () => {
      cancelled = true;
    };
  }, []);

  return <p className={`text-sm leading-relaxed ${ok ? "" : "text-muted-foreground"}`}>{message}</p>;
}
