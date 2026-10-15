import type { Metadata } from "next";
import Link from "next/link";

import { getNewsletterIndex } from "@/lib/newsletter";

export const metadata: Metadata = {
  title: "Newsletter",
  description: "Archive of weekly Inflammation Signal Monitor briefings.",
};

export default function NewsletterIndexPage() {
  const issues = getNewsletterIndex();
  return (
    <div className="max-w-3xl">
      <p className="font-mono text-[11px] tracking-[0.18em] text-primary uppercase">Archive</p>
      <h1 className="mt-2 text-4xl">Weekly briefing</h1>
      <p className="mt-4 text-lg leading-relaxed text-muted-foreground">
        Each issue is built from the snapshot diff after the Monday refresh. The pages here are the public record. The
        email is the same briefing, sent only after a subscriber confirms.
      </p>
      <p className="mt-3 text-sm">
        <Link href="/subscribe" className="text-primary underline-offset-2 hover:underline">
          Subscribe
        </Link>
      </p>
      {issues.length === 0 ? (
        <p className="mt-8 rounded-xl border border-dashed px-4 py-8 text-sm text-muted-foreground">
          No issues yet. The first one is written the next time <span className="font-mono">make newsletter</span> runs.
        </p>
      ) : (
        <ul className="mt-8 space-y-3">
          {issues.map((issue) => (
            <li key={issue.slug} className="rounded-xl bg-card p-5 ring-1 ring-foreground/10">
              <p className="text-xs tracking-wide text-muted-foreground uppercase">{issue.kicker}</p>
              <Link href={`/newsletter/${issue.slug}`} className="mt-1 block font-heading text-2xl leading-snug hover:underline">
                {issue.headline}
              </Link>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
