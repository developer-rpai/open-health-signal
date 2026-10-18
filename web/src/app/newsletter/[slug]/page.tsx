import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";

import { Badge } from "@/components/ui/badge";
import { NCBI_DISCLAIMER_URL } from "@/lib/compliance";
import { getNewsletterIndex, getNewsletterIssue } from "@/lib/newsletter";

export function generateStaticParams() {
  return getNewsletterIndex().map((issue) => ({ slug: issue.slug }));
}

export const dynamicParams = false;

export async function generateMetadata({ params }: { params: Promise<{ slug: string }> }): Promise<Metadata> {
  const { slug } = await params;
  const issue = getNewsletterIssue(slug);
  if (!issue) return { title: "Newsletter" };
  return { title: issue.headline, description: issue.preheader || issue.headline };
}

export default async function NewsletterIssuePage({ params }: { params: Promise<{ slug: string }> }) {
  const { slug } = await params;
  const issue = getNewsletterIssue(slug);
  if (!issue) notFound();
  return (
    <article className="mx-auto max-w-3xl">
      <p className="text-sm text-muted-foreground">{issue.kicker}</p>
      <h1 className="mt-3 text-4xl leading-tight sm:text-5xl">{issue.headline}</h1>
      {issue.highlights && issue.highlights.length > 0 ? (
        <div className="mt-6">
          <h2 className="text-xs font-medium tracking-widest text-primary uppercase">This week</h2>
          <ul className="mt-3 list-disc space-y-2 pl-5 text-base leading-relaxed">
            {issue.highlights.map((item) => (
              <li key={item.href + item.sentence}>
                {item.href ? (
                  <a href={item.href} className="underline decoration-foreground/30 underline-offset-2 hover:decoration-foreground">
                    {item.sentence}
                  </a>
                ) : (
                  item.sentence
                )}
              </li>
            ))}
          </ul>
        </div>
      ) : null}
      {issue.openfda_last_updated ? (
        <p className="mt-4 text-xs text-muted-foreground">FAERS data as of {issue.openfda_last_updated}.</p>
      ) : null}
      <p className="mt-4 flex flex-wrap gap-x-4 gap-y-2 text-sm">
        <Link href="/methods" className="text-primary underline underline-offset-2">
          How these numbers are made
        </Link>
        <a href={`/newsletter/email/${issue.slug}.html`} className="text-primary underline underline-offset-2">
          Email version
        </a>
      </p>

      <div className="mt-10 space-y-10">
        {issue.sections.map((section) => (
          <section key={section.id}>
            <h2 className="text-2xl text-primary">{section.heading}</h2>
            {section.note ? <p className="mt-2 text-xs text-muted-foreground">{section.note}</p> : null}
            {section.id === "papers" ? (
              <p className="mt-1 text-xs">
                <a className="text-primary underline-offset-2 hover:underline" href={issue.ncbi_disclaimer_url || NCBI_DISCLAIMER_URL}>
                  NCBI disclaimer
                </a>
              </p>
            ) : null}
            {section.items.length === 0 ? (
              <p className="mt-3 text-sm text-muted-foreground">{section.empty}</p>
            ) : (
              <ul className="mt-3 space-y-3">
                {section.items.map((item, index) => (
                  <li key={`${section.id}-${index}`} className="rounded-xl bg-card p-4 ring-1 ring-foreground/10">
                    {item.badge ? <Badge variant="outline">{item.badge}</Badge> : null}
                    {item.href ? (
                      <a href={item.href} className="mt-2 block font-medium hover:underline">
                        {item.title}
                      </a>
                    ) : (
                      <p className="mt-2 font-medium">{item.title}</p>
                    )}
                    {item.meta ? <p className="mt-1 text-xs text-muted-foreground">{item.meta}</p> : null}
                    {item.body ? <p className="mt-2 text-sm leading-relaxed text-muted-foreground">{item.body}</p> : null}
                  </li>
                ))}
              </ul>
            )}
          </section>
        ))}
      </div>

      <p className="mt-10 text-sm leading-relaxed text-muted-foreground">
        Informational only, not medical advice. FAERS reports don&apos;t prove a drug caused an event.
      </p>
      <p className="mt-2 text-sm leading-relaxed text-muted-foreground">
        Data: U.S. FDA (open.fda.gov). Not affiliated with or endorsed by FDA.
      </p>
      <p className="mt-2 text-sm text-muted-foreground">
        You&apos;re getting this because you subscribed.{" "}
        <Link href="/unsubscribe" className="text-primary underline-offset-2 hover:underline">
          Unsubscribe
        </Link>
      </p>
      {issue.postal_address ? <p className="mt-2 text-sm text-muted-foreground">{issue.postal_address}</p> : null}
    </article>
  );
}
