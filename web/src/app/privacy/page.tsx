import type { Metadata } from "next";
import Link from "next/link";

import { FDA_ATTRIBUTION, FDA_INDEPENDENCE, RESEARCH_LINE } from "@/lib/compliance";

export const metadata: Metadata = {
  title: "Privacy",
  description: "What the weekly briefing stores, who processes the email address, and how to opt out.",
};

export default function PrivacyPage() {
  return (
    <article className="max-w-3xl space-y-8 text-[15px] leading-relaxed">
      <header>
        <h1 className="text-4xl">Privacy</h1>
        <p className="mt-3 text-lg text-muted-foreground">
          The dashboard can be read without an account. An email address is collected only if you subscribe to the
          weekly briefing.
        </p>
      </header>

      <section>
        <h2 className="text-2xl">Email only</h2>
        <p className="mt-2">
          The subscribe form asks for an email address and a consent checkbox. The list stores that address, the time
          you consented, and the IP address of the request. No health information and no payment details are requested.
          The static dashboard does not keep its own copy of the list.
        </p>
      </section>

      <section>
        <h2 className="text-2xl">Who stores the address</h2>
        <p className="mt-2">
          Supabase Postgres is the source of truth. A row is created as pending, with a hashed confirmation token.
          Resend sends the confirmation email and, after you confirm, the weekly issue. Resend is not the list. A
          bounce or a complaint webhook from Resend marks the address suppressed. API keys stay off the public site.
          Double opt-in stays in place: the address is not active until the confirmation link is opened.
        </p>
      </section>

      <section>
        <h2 className="text-2xl">Opt-out, deletion, and GDPR rights</h2>
        <p className="mt-2">
          The signed link in each issue, and the one-click POST a mail client sends to that link, unsubscribe the
          address immediately. You may also request access, correction, erasure, restriction of processing, objection,
          or a portable copy of the address we hold. Those requests, when they do not arrive through the signed link,
          are honored within ten business days. Erasure removes the address from the list. The public snapshot and the
          newsletter archive do not contain subscriber addresses. The{" "}
          <Link href="/contact" className="text-primary underline-offset-2 hover:underline">
            contact form
          </Link>{" "}
          stores the name, email, organization, role, interest, message, and optional link you submit, with a status
          and notes for the owner.
        </p>
      </section>

      <section>
        <h2 className="text-2xl">Surveillance data</h2>
        <p className="mt-2">
          {FDA_ATTRIBUTION}. {FDA_INDEPENDENCE} Publication lists show titles and links only. {RESEARCH_LINE}
        </p>
      </section>
    </article>
  );
}
