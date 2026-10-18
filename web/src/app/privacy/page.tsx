import type { Metadata } from "next";
import Link from "next/link";

import { CONTACT_EMAIL, FDA_ATTRIBUTION, FDA_INDEPENDENCE, OPERATOR_NAME, RESEARCH_LINE } from "@/lib/compliance";

export const metadata: Metadata = {
  title: "Privacy",
  description: "What Open Health Signals stores, who processes it, how long it is kept, and how to opt out.",
};

export default function PrivacyPage() {
  return (
    <article className="max-w-3xl space-y-8 text-[15px] leading-relaxed">
      <header>
        <h1 className="text-4xl">Privacy</h1>
        <p className="mt-3 text-lg text-muted-foreground">
          The dashboard can be read without an account. An email address is collected only if you subscribe, or if you
          send a message.
        </p>
      </header>

      <section>
        <h2 className="text-2xl">Who operates this site</h2>
        <p className="mt-2">
          {OPERATOR_NAME} operates Open Health Signals, an independent project. The controller for the mailing list and
          the contact form is {OPERATOR_NAME}. Rights requests go to{" "}
          <a className="text-primary underline underline-offset-2" href={`mailto:${CONTACT_EMAIL}`}>
            {CONTACT_EMAIL}
          </a>
          .
        </p>
      </section>

      <section>
        <h2 className="text-2xl">What is collected</h2>
        <p className="mt-2">
          The subscribe form asks for an email address and a consent checkbox. The list stores that address, the time
          you consented, and the IP address of the request. The contact form stores the name, email, message, interest
          type, and any organization, role, or link you choose to add.
        </p>
        <p className="mt-2">
          The lawful basis is consent. A confirmation email is sent first, and the address is added only after that
          link is opened. Each sent issue includes a signed unsubscribe link, and it takes effect immediately.
        </p>
      </section>

      <section>
        <h2 className="text-2xl">Who processes it</h2>
        <ul className="mt-2 list-disc space-y-2 pl-5">
          <li>Cloudflare hosts the site on Cloudflare Pages, serves it through its CDN, and uses Turnstile as the anti-spam check on the contact form.</li>
          <li>Supabase stores the mailing list, contact messages, and the owner sign-in.</li>
          <li>Resend sends the confirmation email and, after you confirm, the briefing. Resend is not the list.</li>
        </ul>
        <p className="mt-2">
          The list is not sold. It is not shared with advertisers or data brokers. A bounce or a complaint from Resend
          marks the address so it is not mailed again.
        </p>
      </section>

      <section>
        <h2 className="text-2xl">Cookies</h2>
        <p className="mt-2">
          Cloudflare may set strictly necessary security cookies, such as __cf_bm, to protect the site and to run
          Turnstile. The site does not use analytics cookies or advertising cookies. No cookie banner is shown, because
          these cookies are strictly necessary.
        </p>
      </section>

      <section>
        <h2 className="text-2xl">How long it is kept</h2>
        <ul className="mt-2 list-disc space-y-2 pl-5">
          <li>A subscription that is never confirmed is deleted after 30 days.</li>
          <li>After you unsubscribe, only a suppression record is kept: the address, the unsubscribed status, and the time. The request IP and the confirmation token are removed.</li>
          <li>Contact messages are kept for up to 12 months, then deleted.</li>
        </ul>
        <p className="mt-2">
          Deletion runs on a database schedule (<code>purge_personal_data</code>). Access and erasure requests that do not
          use the signed unsubscribe link are honored within ten business days.
        </p>
      </section>

      <section>
        <h2 className="text-2xl">Your rights</h2>
        <p className="mt-2">
          You can ask for access, correction, erasure, restriction, objection, or a portable copy of the address we
          hold. Email {CONTACT_EMAIL}. The signed link in each issue, and the one-click POST a mail client sends to
          that link, unsubscribe the address immediately. The public snapshot and the newsletter archive do not contain
          subscriber addresses.
        </p>
      </section>

      <section>
        <h2 className="text-2xl">Consumer health data</h2>
        <p className="mt-2">
          Washington’s My Health My Data Act, and similar laws in other states, treat some inferences about health
          interests as consumer health data. Subscribing to a briefing about inflammatory-disease drug safety can
          indicate an interest in that topic. This section is the consumer health data privacy policy for that
          information.
        </p>
        <ul className="mt-2 list-disc space-y-2 pl-5">
          <li>Categories: email address, consent time, and the IP address of the subscribe or unsubscribe request. We do not ask for a diagnosis, the medicines you take, or any other health detail.</li>
          <li>Purpose: to send the briefing you asked for, and to keep you off the list if you unsubscribe, bounce, or complain.</li>
          <li>Sources: you, when you submit the form or open a link.</li>
          <li>Sharing: Cloudflare, Supabase, and Resend, only to host the site, store the list, and send the email. No sale. No sharing for advertising.</li>
          <li>Rights: you may confirm whether we hold this data, access it, withdraw consent, and ask for deletion. Email {CONTACT_EMAIL}, or use the unsubscribe link to withdraw consent immediately.</li>
        </ul>
        <p className="mt-2">
          Do not put personal health information in the{" "}
          <Link href="/contact" className="text-primary underline underline-offset-2">
            contact form
          </Link>
          . To report a side effect to the FDA, use MedWatch.
        </p>
      </section>

      <section>
        <h2 className="text-2xl">Public data on the dashboard</h2>
        <p className="mt-2">
          {FDA_ATTRIBUTION}. {FDA_INDEPENDENCE} Publication lists show titles and links only. {RESEARCH_LINE}
        </p>
      </section>
    </article>
  );
}
