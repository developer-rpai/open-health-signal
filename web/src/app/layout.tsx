import type { Metadata, Viewport } from "next";
import { IBM_Plex_Mono, IBM_Plex_Sans, Newsreader } from "next/font/google";

import { SiteFooter, SiteHeader } from "@/components/site-header";
import { getManifest } from "@/lib/snapshot";
import { formatGenerated } from "@/lib/format";

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
  metadataBase: new URL("https://openhealthsignals.org"),
  title: {
    default: "Open Health Signals",
    template: "%s · Open Health Signals",
  },
  description:
    "Open Health Signals is an independent health-data project. Inflammation Signal Monitor publishes FAERS safety signals, FDA notices, trials, and papers.",
};

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  const manifest = getManifest();
  return (
    <html lang="en" className={`${plex.variable} ${plexMono.variable} ${newsreader.variable}`}>
      <body className="antialiased">
        <SiteHeader />
        <main className="mx-auto max-w-6xl px-4 py-8 sm:px-6">{children}</main>
        <SiteFooter generated={formatGenerated(manifest.generated_at)} />
      </body>
    </html>
  );
}
