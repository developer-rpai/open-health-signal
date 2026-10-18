"use client";

import { Menu, X } from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";

import {
  CONTACT_EMAIL,
  COPYRIGHT_LINE,
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

function navActive(pathname: string, href: string) {
  if (href === "/") return pathname === "/";
  return pathname === href || pathname.startsWith(`${href}/`);
}

export function SiteHeader() {
  const pathname = usePathname();
  const [open, setOpen] = useState(false);

  useEffect(() => {
    setOpen(false);
  }, [pathname]);

  return (
    <header className="border-b border-border bg-background">
      <div className="mx-auto flex max-w-6xl flex-col px-4 sm:px-6 lg:flex-row lg:items-end lg:justify-between lg:gap-6 lg:py-4">
        <div className="flex min-w-0 items-center justify-between gap-3 py-3 lg:py-0">
          <Link href="/" className="min-w-0 rounded-sm text-left">
            <p className="font-heading text-2xl leading-tight text-foreground">Open Health Signals</p>
            <p className="mt-1 text-sm text-muted-foreground">Inflammation Signal Monitor</p>
          </Link>
          <button
            type="button"
            className="inline-flex h-11 w-11 shrink-0 items-center justify-center rounded-md border border-border text-foreground hover:bg-muted lg:hidden"
            aria-expanded={open}
            aria-controls="site-nav"
            onClick={() => setOpen((value) => !value)}
          >
            {open ? <X aria-hidden="true" className="size-5" /> : <Menu aria-hidden="true" className="size-5" />}
            <span className="sr-only">{open ? "Close menu" : "Open menu"}</span>
          </button>
        </div>
        <nav id="site-nav" aria-label="Primary" className={`${open ? "block" : "hidden"} pb-3 lg:block lg:pb-0`}>
          <div className="flex flex-col lg:flex-row lg:flex-wrap lg:items-center lg:justify-end">
            {LINKS.map((link) => {
              const active = navActive(pathname, link.href);
              return (
                <Link
                  key={link.href}
                  href={link.href}
                  aria-current={active ? "page" : undefined}
                  className={`flex min-h-11 items-center rounded-md px-3 text-left text-sm lg:px-2.5 ${
                    active ? "bg-primary text-primary-foreground" : "text-foreground/80 hover:bg-muted hover:text-foreground"
                  }`}
                >
                  {link.label}
                </Link>
              );
            })}
            <Link
              href="/subscribe"
              className={`flex min-h-11 items-center rounded-md px-3 text-left text-sm lg:px-2.5 ${
                pathname === "/subscribe" ? "bg-primary text-primary-foreground" : "text-primary hover:bg-muted"
              }`}
            >
              Subscribe
            </Link>
          </div>
        </nav>
      </div>
    </header>
  );
}

export function SiteFooter({ generated }: { generated: string }) {
  const postal = publicPostalAddress();
  return (
    <footer id="site-footer" className="mt-10 border-t border-border">
      <div className="mx-auto flex max-w-6xl flex-col gap-1.5 px-4 py-4 text-[13px] leading-snug text-muted-foreground sm:px-6">
        <p>
          Open Health Signals is an independent project operated by {OPERATOR_NAME}
          {" · "}
          <a className="underline underline-offset-2 hover:text-foreground" href={`mailto:${CONTACT_EMAIL}`}>
            {CONTACT_EMAIL}
          </a>
          {postal ? ` · ${postal}` : null}
        </p>
        <p>
          Data: U.S. FDA (
          <a className="underline underline-offset-2 hover:text-foreground" href="https://open.fda.gov">
            open.fda.gov
          </a>
          ). Not affiliated with or endorsed by FDA. Not medical advice; don&apos;t change any medication without talking
          to your doctor.
        </p>
        <p>
          Snapshot {generated}
          {" · "}
          Report a side effect to{" "}
          <a className="underline underline-offset-2 hover:text-foreground" href={MEDWATCH_URL}>
            FDA MedWatch
          </a>
        </p>
        <p className="flex flex-wrap items-center gap-x-3 gap-y-1">
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
          <span className="max-sm:basis-full sm:before:mr-3 sm:before:content-['·']">{COPYRIGHT_LINE}</span>
        </p>
      </div>
    </footer>
  );
}
