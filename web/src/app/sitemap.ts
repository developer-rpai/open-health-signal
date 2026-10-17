import type { MetadataRoute } from "next";

import { getNewsletterIndex } from "@/lib/newsletter";

export const dynamic = "force-static";

const SITE = "https://openhealthsignals.org";

export default function sitemap(): MetadataRoute.Sitemap {
  const paths = [
    "/",
    "/signals",
    "/trends",
    "/newsletter",
    "/subscribe",
    "/contact",
    "/methods",
    "/about",
    "/privacy",
    "/terms",
    "/unsubscribe",
    "/confirm",
  ];
  const issues = getNewsletterIndex().map((issue) => `/newsletter/${issue.slug}`);
  return [...paths, ...issues].map((path) => ({
    url: path === "/" ? `${SITE}/` : `${SITE}${path}`,
    lastModified: new Date("2026-10-17"),
  }));
}
