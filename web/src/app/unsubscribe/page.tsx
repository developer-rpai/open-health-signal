import type { Metadata } from "next";
import Link from "next/link";

import { UnsubscribeForm } from "@/components/unsubscribe-form";

export const metadata: Metadata = {
  title: "Unsubscribe",
  description: "Opt out of the weekly Inflammation Signal Monitor briefing.",
};

export default function UnsubscribePage() {
  return (
    <article className="mx-auto max-w-xl space-y-6">
      <header>
        <h1 className="text-4xl">Unsubscribe</h1>
        <p className="mt-3 text-lg leading-relaxed text-muted-foreground">
          Opt-outs are honored within ten business days. Subscribing still requires a confirmation email before an
          address is added. That double opt-in step stays in place.
        </p>
      </header>

      <div className="rounded-2xl bg-card p-6 ring-1 ring-foreground/10">
        <UnsubscribeForm />
      </div>

      <p className="text-sm text-muted-foreground">
        How the address is stored is on the{" "}
        <Link href="/privacy" className="text-primary underline-offset-2 hover:underline">
          privacy page
        </Link>
        .
      </p>
    </article>
  );
}
