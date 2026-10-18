import "server-only";

import fs from "fs";
import path from "path";

export type NewsletterItem = {
  title: string;
  meta: string;
  body: string;
  href: string;
  badge: string;
};

export type NewsletterSection = {
  id: string;
  heading: string;
  empty: string;
  note?: string;
  items: NewsletterItem[];
};

export type NewsletterHighlight = {
  sentence: string;
  href: string;
};

export type NewsletterIssue = {
  slug: string;
  kind: string;
  subject: string;
  headline: string;
  kicker: string;
  intro: string;
  highlights?: NewsletterHighlight[];
  preheader?: string;
  snapshot_generated_at: string;
  disclaimer: string;
  fda_caveat?: string;
  research_line?: string;
  fda_attribution?: string;
  fda_independence?: string;
  ncbi_disclaimer_url?: string;
  postal_address?: string;
  unsubscribe_page?: string;
  signal_caveat?: string;
  openfda_last_updated?: string;
  sections: NewsletterSection[];
  delivery?: {
    mode: string;
    sent: boolean;
    provider: string;
  };
};

export type NewsletterIndexItem = {
  slug: string;
  headline: string;
  kind: string;
  kicker: string;
  subject: string;
  snapshot_generated_at: string;
};

function newsletterRoot(): string {
  return path.join(process.cwd(), "data", "newsletter");
}

export function getNewsletterIndex(): NewsletterIndexItem[] {
  const file = path.join(newsletterRoot(), "index.json");
  if (!fs.existsSync(file)) return [];
  const payload = JSON.parse(fs.readFileSync(file, "utf8")) as { issues?: NewsletterIndexItem[] };
  return payload.issues ?? [];
}

export function getNewsletterIssue(slug: string): NewsletterIssue | null {
  if (!/^[0-9]{4}-[0-9]{2}-[0-9]{2}$/.test(slug)) return null;
  const file = path.join(newsletterRoot(), "issues", `${slug}.json`);
  if (!fs.existsSync(file)) return null;
  return JSON.parse(fs.readFileSync(file, "utf8")) as NewsletterIssue;
}
