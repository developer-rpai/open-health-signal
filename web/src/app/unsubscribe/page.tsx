import type { Metadata } from "next";
import Link from "next/link";

import { UnsubscribePanel } from "@/components/unsubscribe-panel";

export const metadata: Metadata = {
  title: "Unsubscribe",
  description: "Signed unsubscribe link for the weekly briefing. One click takes effect immediately.",
};

export default function UnsubscribePage() {
  return (
    <article className="mx-auto max-w-xl space-y-6">
      <header>
        <h1 className="text-4xl">Unsubscribe</h1>
        <p className="mt-3 text-lg leading-relaxed text-muted-foreground">
          Each issue carries a signed link for that address. Opening it shows this page. Submitting, or the mail
          client’s one-click POST, removes the address immediately. New subscriptions still require the confirmation
          email. That double opt-in step stays in place.
        </p>
      </header>
      <div className="rounded-2xl bg-card p-6 ring-1 ring-foreground/10">
        <UnsubscribePanel />
      </div>
      <p className="text-sm text-muted-foreground">
        How the address is stored is on the{" "}
        <Link href="/privacy" className="text-primary underline-offset-2 hover:underline">
          privacy page
        </Link>
        . Requests for access or erasure, other than this link, are honored within ten business days.
      </p>
    </article>
  );
}
