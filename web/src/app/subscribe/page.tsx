import type { Metadata } from "next";
import Link from "next/link";

import { SubscribeForm } from "@/components/subscribe-form";

export const metadata: Metadata = {
  title: "Subscribe",
  description: "Weekly email briefing of FDA notices, drug-safety signals, trials, and new papers.",
};

export default function SubscribePage() {
  return (
    <article className="grid gap-10 lg:grid-cols-[1.1fr_0.9fr] lg:items-start">
      <div className="max-w-xl">
        <p className="font-mono text-[11px] tracking-[0.18em] text-primary uppercase">Weekly briefing</p>
        <h1 className="mt-2 text-4xl leading-tight">The Monday email, in one place.</h1>
        <p className="mt-4 text-lg leading-relaxed text-muted-foreground">
          After each weekly refresh the monitor writes a short issue: the week’s headline, new FDA safety alerts and
          recalls, drug-safety signals that are new or stronger, notable trials, and new PubMed papers.
        </p>
        <ul className="mt-6 space-y-3 text-sm leading-relaxed">
          <li>Confirmation comes first. Opening that link is what adds the address.</li>
          <li>Every sent issue has a signed unsubscribe link. It takes effect immediately, and mail clients can use one-click unsubscribe.</li>
          <li>
            Past issues stay on the site, with the numbers and the disclaimer.{" "}
            <Link href="/newsletter" className="text-primary underline-offset-2 hover:underline">
              Read the archive
            </Link>
            .
          </li>
        </ul>
        <p className="mt-6 text-sm leading-relaxed text-muted-foreground">
          The ratios in the email are the same PRR and ROR figures as the dashboard. They describe spontaneous reports.
          They are not medical advice. The{" "}
          <Link href="/methods" className="underline underline-offset-2 hover:text-foreground">
            methods page
          </Link>{" "}
          has the formulas.
        </p>
      </div>
      <div className="rounded-2xl bg-card p-6 ring-1 ring-foreground/10">
        <h2 className="text-2xl">Get the briefing</h2>
        <div className="mt-4">
          <SubscribeForm id="subscribe" />
        </div>
      </div>
    </article>
  );
}
