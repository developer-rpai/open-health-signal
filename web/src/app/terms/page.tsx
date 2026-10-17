import type { Metadata } from "next";
import Link from "next/link";

import { CONTACT_EMAIL, FDA_ATTRIBUTION, FDA_INDEPENDENCE, MEDWATCH_URL, RESEARCH_LINE } from "@/lib/compliance";

export const metadata: Metadata = {
  title: "Terms",
  description: "No warranty, no medical advice, California law, and no attempts to re-identify people in public data.",
};

export default function TermsPage() {
  return (
    <article className="max-w-3xl space-y-8 text-[15px] leading-relaxed">
      <header>
        <h1 className="text-4xl">Terms</h1>
        <p className="mt-3 text-lg text-muted-foreground">{RESEARCH_LINE}</p>
      </header>

      <section>
        <h2 className="text-2xl">No warranty</h2>
        <p className="mt-2">
          The site, the snapshot, and the newsletter are provided as is, without warranty of any kind, express or
          implied, including warranties of accuracy, completeness, merchantability, or fitness for a particular
          purpose. Use the{" "}
          <Link href="/methods" className="text-primary underline underline-offset-2">
            methods page
          </Link>{" "}
          to see how a figure was produced.
        </p>
      </section>

      <section>
        <h2 className="text-2xl">Upstream data</h2>
        <p className="mt-2">
          FDA, NLM, and CDC extracts can be delayed, incomplete, or corrected after they are published. A weekly
          rebuild does not mean the underlying FAERS extract is from that week. The page states the extract date next
          to the counts.
        </p>
      </section>

      <section>
        <h2 className="text-2xl">No medical advice</h2>
        <p className="mt-2">
          Nothing here is medical advice, a diagnosis, or a treatment recommendation. A disproportionality signal means
          a reaction was reported more often than a comparison group in this extract. It is not an instruction to
          start, stop, or change a medicine. Talk with your doctor before any change. Report a side effect to{" "}
          <a className="text-primary underline underline-offset-2" href={MEDWATCH_URL}>
            FDA MedWatch
          </a>
          .
        </p>
      </section>

      <section>
        <h2 className="text-2xl">Limitation of liability</h2>
        <p className="mt-2">
          To the extent the law allows, Open Health Signals and its operator are not liable for loss or damage from
          using the site, the snapshot, or the newsletter, including decisions made from the figures.
        </p>
      </section>

      <section>
        <h2 className="text-2xl">No re-identification</h2>
        <p className="mt-2">
          Do not attempt to re-identify any person from FAERS, ClinicalTrials.gov, PubMed, CDC, or any other source
          shown here. Do not combine these extracts with other datasets in order to identify a patient, a reporter, or
          a trial participant. The counts are aggregate. They are not a row-level clinical record.
        </p>
      </section>

      <section>
        <h2 className="text-2xl">Copyright</h2>
        <p className="mt-2">
          The code is MIT licensed. Source data keep the licenses named on the methods page. To report a copyright
          concern, email{" "}
          <a className="text-primary underline underline-offset-2" href={`mailto:${CONTACT_EMAIL}`}>
            {CONTACT_EMAIL}
          </a>
          .
        </p>
      </section>

      <section>
        <h2 className="text-2xl">Changes</h2>
        <p className="mt-2">
          These terms can change. The text on this page is the version that applies. Continuing to use the site after
          a change means you accept the updated terms.
        </p>
      </section>

      <section>
        <h2 className="text-2xl">Governing law</h2>
        <p className="mt-2">
          These terms are governed by the laws of the State of California. Venue for disputes is Santa Clara County,
          California.
        </p>
      </section>

      <section>
        <h2 className="text-2xl">Sources</h2>
        <p className="mt-2">
          {FDA_ATTRIBUTION}. {FDA_INDEPENDENCE} The{" "}
          <Link href="/privacy" className="text-primary underline underline-offset-2">
            privacy page
          </Link>{" "}
          covers the mailing list.
        </p>
      </section>
    </article>
  );
}
