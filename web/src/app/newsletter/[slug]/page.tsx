import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";

import { Badge } from "@/components/ui/badge";
import { getNewsletterIndex, getNewsletterIssue } from "@/lib/newsletter";

export function generateStaticParams() {
  return getNewsletterIndex().map((issue) => ({ slug: issue.slug }));
}

export const dynamicParams = false;

export async function generateMetadata({ params }: { params: Promise<{ slug: string }> }): Promise<Metadata> {
  const { slug } = await params;
  const issue = getNewsletterIssue(slug);
  if (!issue) return { title: "Newsletter" };
  return { title: issue.headline, description: issue.intro };
}

export default async function NewsletterIssuePage({ params }: { params: Promise<{ slug: string }> }) {
  const { slug } = await params;
  const issue = getNewsletterIssue(slug);
  if (!issue) notFound();
  const emailed = issue.delivery?.sent === true;

  return (
    <article className="mx-auto max-w-3xl">
      <p className="font-mono text-[11px] tracking-[0.18em] text-primary uppercase">{issue.kicker}</p>
      <h1 className="mt-3 text-4xl leading-tight sm:text-5xl">{issue.headline}</h1>
      <p className="mt-5 text-lg leading-relaxed">{issue.intro}</p>
      <p className="mt-4 flex flex-wrap gap-x-4 gap-y-2 text-sm">
        <Link href="/" className="text-primary underline-offset-2 hover:underline">
          Open the dashboard
        </Link>
        <a href={`/newsletter/email/${issue.slug}.html`} className="text-primary underline-offset-2 hover:underline">
          Email version
        </a>
        <Link href="/subscribe" className="text-primary underline-offset-2 hover:underline">
          Subscribe
        </Link>
      </p>
      <p className="mt-3 text-sm text-muted-foreground">
        {emailed
          ? `Sent with ${issue.delivery?.provider}.`
          : "Archived from a dry run. This copy was not emailed."}
      </p>

      <div className="mt-10 space-y-10">
        {issue.sections.map((section) => (
          <section key={section.id}>
            <h2 className="text-2xl text-primary">{section.heading}</h2>
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

      <p className="mt-10 text-sm leading-relaxed text-muted-foreground">{issue.disclaimer}</p>
      <p className="mt-3 text-sm text-muted-foreground">
        Unsubscribe from the email you received. The provider replaces that link when an issue is sent.
      </p>
    </article>
  );
}
