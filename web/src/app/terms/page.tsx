import type { Metadata } from "next";
import Link from "next/link";

import { FDA_ATTRIBUTION, FDA_INDEPENDENCE, RESEARCH_LINE } from "@/lib/compliance";

export const metadata: Metadata = {
  title: "Terms",
  description: "No warranty, no medical advice, and no attempts to re-identify people in public surveillance data.",
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
          purpose. Public extracts lag, counts can change, and a source can fail. Use the methods page to see how a
          figure was produced.
        </p>
      </section>

      <section>
        <h2 className="text-2xl">No medical advice</h2>
        <p className="mt-2">
          Nothing here is medical advice, a diagnosis, or a treatment recommendation. A disproportionality signal means
          a reaction was reported more often than expected (PRR on the drug signals page). It is not an instruction to
          start, stop, or change a medicine. Talk with your doctor before any change. Report adverse events to{" "}
          <a
            className="text-primary underline-offset-2 hover:underline"
            href="https://www.fda.gov/safety/medwatch-fda-safety-information-and-adverse-event-reporting-program"
          >
            FDA MedWatch
          </a>
          .
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
        <h2 className="text-2xl">Sources</h2>
        <p className="mt-2">
          {FDA_ATTRIBUTION}. {FDA_INDEPENDENCE} Publication titles link to PubMed. The{" "}
          <Link href="/privacy" className="text-primary underline-offset-2 hover:underline">
            privacy page
          </Link>{" "}
          covers the mailing list.
        </p>
      </section>
    </article>
  );
}
