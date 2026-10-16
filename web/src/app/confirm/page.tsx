import type { Metadata } from "next";

import { ConfirmPanel } from "@/components/confirm-panel";

export const metadata: Metadata = {
  title: "Confirm subscription",
  description: "Open the link from the confirmation email to join the weekly briefing.",
};

export default function ConfirmPage() {
  return (
    <article className="mx-auto max-w-xl space-y-6">
      <header>
        <h1 className="text-4xl">Confirm your address</h1>
        <p className="mt-3 text-lg leading-relaxed text-muted-foreground">
          The briefing starts only after this confirmation. Until then the address stays pending.
        </p>
      </header>
      <div className="rounded-2xl bg-card p-6 ring-1 ring-foreground/10">
        <ConfirmPanel />
      </div>
    </article>
  );
}
