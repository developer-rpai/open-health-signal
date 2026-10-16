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
          The subscribe form asks for an email address and a consent checkbox. No name, no health information, and no
          payment details are requested. The static site does not keep a subscriber database of its own.
        </p>
      </section>

      <section>
        <h2 className="text-2xl">Who processes the address</h2>
        <p className="mt-2">
          Buttondown is the processor. The form posts the address to Buttondown, and Buttondown stores it only after
          you open the confirmation message. That confirmation step is double opt-in, and it stays in place. If this
          deployment is switched to the Resend alternative, Resend is the processor and the same confirmation step
          applies. API keys for either processor stay off the public site.
        </p>
      </section>

      <section>
        <h2 className="text-2xl">Opt-out, deletion, and GDPR rights</h2>
        <p className="mt-2">
          You can unsubscribe from any issue or from the{" "}
          <Link href="/unsubscribe" className="text-primary underline-offset-2 hover:underline">
            unsubscribe page
          </Link>
          . Opt-outs are honored within ten business days. You may also request access, correction, erasure,
          restriction of processing, objection, or a portable copy of the email address we hold. Those requests are
          forwarded to the processor. Erasure removes the address from the mailing list. The public snapshot and the
          newsletter archive do not contain subscriber addresses.
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
