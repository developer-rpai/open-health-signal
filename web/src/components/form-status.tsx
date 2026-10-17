"use client";

import { useEffect, useRef } from "react";

export function FormStatus({ tone, message }: { tone: "success" | "error"; message: string }) {
  const ref = useRef<HTMLParagraphElement>(null);

  useEffect(() => {
    const node = ref.current;
    if (!node) return;
    node.scrollIntoView({ behavior: "smooth", block: "center" });
    node.focus({ preventScroll: true });
  }, [message, tone]);

  return (
    <p
      ref={ref}
      tabIndex={-1}
      role={tone === "error" ? "alert" : "status"}
      aria-live={tone === "error" ? "assertive" : "polite"}
      className={`text-lg leading-relaxed outline-none ${tone === "error" ? "text-destructive" : "text-foreground"}`}
    >
      {message}
    </p>
  );
}

export function messageForError(error: string | undefined): string {
  switch (error) {
    case "consent_required":
      return "Check the box to agree before subscribing.";
    case "email_required":
    case "invalid_email":
      return "Enter a valid email address.";
    case "rate_limited":
      return "Too many attempts from this network. Wait a bit and try again.";
    case "turnstile":
      return "The spam check did not pass. Reload the page and try again.";
    case "network":
      return "The request did not go through. Check your connection and try again.";
    case "suppressed":
      return "This address cannot be added again after a bounce or complaint.";
    case "invalid_token":
    case "unknown_subscriber":
      return "This link has expired or does not match. Request a new one.";
    case "one_click_required":
      return "Use the unsubscribe button on this page.";
    case "not_allowlisted":
      return "This email is not on the owner list.";
    case "missing_fields":
      return "Name, email, and a message are required.";
    case "interest_type":
      return "Choose what the message is about.";
    case "link":
      return "The link must start with http:// or https://.";
    case "unavailable":
      return "This form is not available on this copy of the site.";
    default:
      return "Something went wrong. Try again.";
  }
}

export async function readApi(response: Response): Promise<{ ok?: boolean; status?: string; error?: string; message?: string; confirm_url?: string; sent?: boolean }> {
  try {
    return (await response.json()) as { ok?: boolean; status?: string; error?: string; message?: string; confirm_url?: string; sent?: boolean };
  } catch {
    return { ok: false, error: "network" };
  }
}
