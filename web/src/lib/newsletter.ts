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
  items: NewsletterItem[];
};

export type NewsletterIssue = {
  slug: string;
  kind: string;
  subject: string;
  headline: string;
  kicker: string;
  intro: string;
  snapshot_generated_at: string;
  disclaimer: string;
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
