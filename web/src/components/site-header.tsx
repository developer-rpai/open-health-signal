"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

import { SubscribeForm } from "@/components/subscribe-form";

const LINKS = [
  { href: "/", label: "Overview" },
  { href: "/signals", label: "Drug signals" },
  { href: "/trends", label: "Disease trends" },
  { href: "/newsletter", label: "Newsletter" },
  { href: "/methods", label: "Methods" },
  { href: "/about", label: "About" },
];

export function SiteHeader() {
  const pathname = usePathname();
  return (
    <header className="border-b border-border bg-background/95">
      <div className="mx-auto flex max-w-6xl flex-col gap-4 px-4 py-4 sm:px-6 md:flex-row md:items-end md:justify-between">
        <Link href="/" className="group block">
          <p className="font-mono text-[11px] tracking-[0.18em] text-primary uppercase">
            Public pharmacovigilance
          </p>
          <p className="font-heading text-2xl leading-none text-foreground">
            Inflammation Signal Monitor
          </p>
        </Link>
        <nav aria-label="Primary" className="flex flex-wrap gap-1">
          {LINKS.map((link) => {
            const active = link.href === "/" ? pathname === "/" : pathname === link.href || pathname.startsWith(`${link.href}/`);
            return (
              <Link
                key={link.href}
                href={link.href}
                aria-current={active ? "page" : undefined}
                className={`rounded-md px-2.5 py-1.5 text-sm ${
                  active
                    ? "bg-primary text-primary-foreground"
                    : "text-foreground/80 hover:bg-muted hover:text-foreground"
                }`}
              >
                {link.label}
              </Link>
            );
          })}
        </nav>
      </div>
    </header>
  );
}

export function SiteFooter({ generated, version }: { generated: string; version: string }) {
  return (
    <footer className="mt-16 border-t border-border">
      <div className="mx-auto grid max-w-6xl gap-8 px-4 py-8 sm:px-6 lg:grid-cols-[1.1fr_0.9fr]">
        <div>
          <h2 className="text-xl">Weekly briefing</h2>
          <p className="mt-2 max-w-md text-sm leading-relaxed text-muted-foreground">
            FDA notices, safety signals, trials, and papers after each Monday refresh.{" "}
            <Link href="/subscribe" className="underline decoration-border underline-offset-2 hover:text-foreground">
              Subscribe page
            </Link>
            .
          </p>
          <div className="mt-4 max-w-md">
            <SubscribeForm id="footer-subscribe" />
          </div>
        </div>
        <div className="flex flex-col gap-2 text-sm text-muted-foreground lg:pt-1">
        <p>
          Snapshot {generated}. Version {version}. Refreshed weekly from public sources.
          Not medical advice.
        </p>
        <p>
          Report adverse events to{" "}
          <a className="underline decoration-border underline-offset-2 hover:text-foreground" href="https://www.fda.gov/safety/medwatch-fda-safety-information-and-adverse-event-reporting-program">
            FDA MedWatch
          </a>
          . Methods, licenses, and the Evans criteria are on the{" "}
          <Link className="underline decoration-border underline-offset-2 hover:text-foreground" href="/methods">
            methods page
          </Link>
          .
        </p>
        </div>
      </div>
    </footer>
  );
}

export function Disclaimer({ text }: { text: string }) {
  return (
    <p className="border-y border-amber-800/20 bg-amber-100/70 px-4 py-3 text-sm leading-relaxed text-amber-950">
      <span className="font-medium">Not medical advice. </span>
      {text}
    </p>
  );
}
