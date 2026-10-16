import type { Metadata } from "next";
import { IBM_Plex_Mono, IBM_Plex_Sans, Newsreader } from "next/font/google";

import { Disclaimer, SiteFooter, SiteHeader } from "@/components/site-header";
import { getManifest } from "@/lib/snapshot";
import { formatGenerated } from "@/lib/format";
import { RESEARCH_LINE } from "@/lib/compliance";

import "./globals.css";

const plex = IBM_Plex_Sans({
  subsets: ["latin"],
  weight: ["400", "500", "600"],
  variable: "--font-plex",
});

const plexMono = IBM_Plex_Mono({
  subsets: ["latin"],
  weight: ["400", "500"],
  variable: "--font-plex-mono",
});

const newsreader = Newsreader({
  subsets: ["latin"],
  variable: "--font-newsreader",
});

export const metadata: Metadata = {
  title: {
    default: "Inflammation Signal Monitor",
    template: "%s · Inflammation Signal Monitor",
  },
  description:
    "A free public dashboard of FAERS safety signals, FDA notices, recalls, trials, and publications for inflammatory disease and anti-inflammatory drugs.",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  const manifest = getManifest();
  return (
    <html lang="en" className={`${plex.variable} ${plexMono.variable} ${newsreader.variable}`}>
      <body className="antialiased">
        <SiteHeader />
        <Disclaimer text={RESEARCH_LINE} />
        <main className="mx-auto max-w-6xl px-4 py-8 sm:px-6">{children}</main>
        <SiteFooter generated={formatGenerated(manifest.generated_at)} version={manifest.version} />
      </body>
    </html>
  );
}
