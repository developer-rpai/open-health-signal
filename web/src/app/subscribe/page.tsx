import type { Metadata } from "next";
import Link from "next/link";

import { SubscribeForm } from "@/components/subscribe-form";

export const metadata: Metadata = {
  title: "Subscribe",
  description: "Email briefing from Open Health Signals after each refresh of Inflammation Signal Monitor.",
};

export default function SubscribePage() {
  return (
    <article className="grid gap-10 lg:grid-cols-[1.1fr_0.9fr] lg:items-start">
      <div className="max-w-xl">
        <h1 className="text-4xl leading-tight">Subscribe</h1>
        <p className="mt-4 text-lg leading-relaxed text-muted-foreground">
          The briefing lists what changed since the previous snapshot: FDA notices and recalls, drug-safety signals that
          are new or stronger, trials, and PubMed titles.
        </p>
        <ul className="mt-6 space-y-3 text-sm leading-relaxed">
          <li>A confirmation email comes first. The address is added only after that link is opened.</li>
          <li>Each sent issue has a signed unsubscribe link. It takes effect immediately.</li>
          <li>
            Past issues stay on the site.{" "}
            <Link href="/newsletter" className="text-primary underline underline-offset-2">
              Read the archive
            </Link>
            .
          </li>
        </ul>
      </div>
      <div className="rounded-xl bg-card p-6 ring-1 ring-foreground/10">
        <h2 className="text-2xl">Email address</h2>
        <div className="mt-4">
          <SubscribeForm id="subscribe" />
        </div>
      </div>
    </article>
  );
}
