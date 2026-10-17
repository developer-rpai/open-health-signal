import type { Metadata } from "next";
import Link from "next/link";

import { getNewsletterIndex } from "@/lib/newsletter";

export const metadata: Metadata = {
  title: "Newsletter",
  description: "Archive of Open Health Signals briefings from Inflammation Signal Monitor.",
};

export default function NewsletterIndexPage() {
  const issues = getNewsletterIndex();
  return (
    <div className="max-w-3xl">
      <h1 className="text-4xl">Newsletter</h1>
      <p className="mt-4 text-lg leading-relaxed text-muted-foreground">
        Each issue is the difference from the previous snapshot. The pages here are the public record.
      </p>
      <p className="mt-3 text-sm">
        <Link href="/subscribe" className="text-primary underline underline-offset-2">
          Subscribe
        </Link>
      </p>
      {issues.length === 0 ? (
        <p className="mt-8 text-sm text-muted-foreground">No issues in this archive yet.</p>
      ) : (
        <ul className="mt-8 space-y-3">
          {issues.map((issue) => (
            <li key={issue.slug} className="rounded-xl bg-card p-5 ring-1 ring-foreground/10">
              <p className="text-sm text-muted-foreground">{issue.kicker}</p>
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
