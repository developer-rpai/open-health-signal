"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

import {
  CONTACT_EMAIL,
  COPYRIGHT_LINE,
  FDA_ATTRIBUTION,
  FDA_INDEPENDENCE,
  MEDWATCH_URL,
  OPERATOR_NAME,
  publicPostalAddress,
} from "@/lib/compliance";

const LINKS = [
  { href: "/", label: "Home" },
  { href: "/signals", label: "Drug signals" },
  { href: "/trends", label: "Disease trends" },
  { href: "/newsletter", label: "Newsletter" },
  { href: "/methods", label: "Methods" },
  { href: "/about", label: "About" },
  { href: "/contact", label: "Contact" },
];

export function SiteHeader() {
  const pathname = usePathname();
  return (
    <header className="border-b border-border bg-background">
      <div className="mx-auto flex max-w-6xl flex-col gap-3 px-4 py-4 sm:px-6 md:flex-row md:items-end md:justify-between">
        <Link href="/" className="block rounded-sm">
          <p className="font-heading text-2xl leading-none text-foreground">Open Health Signals</p>
          <p className="mt-1 text-sm text-muted-foreground">Inflammation Signal Monitor</p>
        </Link>
        <nav aria-label="Primary" className="flex flex-wrap items-center gap-1">
          {LINKS.map((link) => {
            const active = link.href === "/" ? pathname === "/" : pathname === link.href || pathname.startsWith(`${link.href}/`);
            return (
              <Link
                key={link.href}
                href={link.href}
                aria-current={active ? "page" : undefined}
                className={`rounded-md px-2.5 py-1.5 text-sm ${
                  active ? "bg-primary text-primary-foreground" : "text-foreground/80 hover:bg-muted hover:text-foreground"
                }`}
              >
                {link.label}
              </Link>
            );
          })}
          <Link
            href="/subscribe"
            className={`rounded-md px-2.5 py-1.5 text-sm ${
              pathname === "/subscribe" ? "bg-primary text-primary-foreground" : "text-primary hover:bg-muted"
            }`}
          >
            Subscribe
          </Link>
        </nav>
      </div>
    </header>
  );
}

export function SiteFooter({ generated }: { generated: string }) {
  const postal = publicPostalAddress();
  return (
    <footer id="site-footer" className="mt-16 border-t border-border">
      <div className="mx-auto flex max-w-6xl flex-col gap-4 px-4 py-8 text-sm leading-relaxed text-muted-foreground sm:px-6">
        <p>
          Open Health Signals is an independent project operated by {OPERATOR_NAME}.{" "}
          <a className="underline underline-offset-2 hover:text-foreground" href={`mailto:${CONTACT_EMAIL}`}>
            {CONTACT_EMAIL}
          </a>
        </p>
        {postal ? <p>{postal}</p> : null}
        <p>
          {FDA_ATTRIBUTION}. {FDA_INDEPENDENCE}
        </p>
        <p>
          Snapshot {generated}. Report a side effect to{" "}
          <a className="underline underline-offset-2 hover:text-foreground" href={MEDWATCH_URL}>
            FDA MedWatch
          </a>
          .
        </p>
        <p className="flex flex-wrap gap-x-4 gap-y-1">
          <Link className="underline underline-offset-2 hover:text-foreground" href="/privacy">
            Privacy
          </Link>
          <Link className="underline underline-offset-2 hover:text-foreground" href="/terms">
            Terms
          </Link>
          <Link className="underline underline-offset-2 hover:text-foreground" href="/unsubscribe">
            Unsubscribe
          </Link>
          <Link className="underline underline-offset-2 hover:text-foreground" href="/methods">
            Methods
          </Link>
        </p>
        <p>{COPYRIGHT_LINE}</p>
      </div>
    </footer>
  );
}

export function Disclaimer({ text }: { text: string }) {
  return (
    <p className="border-b border-border bg-secondary px-4 py-2.5 text-sm leading-relaxed text-foreground">{text}</p>
  );
}
