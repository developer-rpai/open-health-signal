import type { Metadata } from "next";

import { CONTACT_EMAIL, COPYRIGHT_LINE, OPERATOR_NAME, publicPostalAddress } from "@/lib/compliance";

export const metadata: Metadata = {
  title: "About",
  description: "Open Health Signals is an independent health-data project. Inflammation Signal Monitor is the first one.",
};

export default function AboutPage() {
  const postal = publicPostalAddress();
  return (
    <article className="max-w-3xl space-y-8 text-[15px] leading-relaxed">
      <header>
        <h1 className="text-4xl">About</h1>
        <p className="mt-3 text-lg text-muted-foreground">
          Open Health Signals publishes public health data. Inflammation Signal Monitor is the first project.
        </p>
      </header>

      <section>
        <h2 className="text-2xl">This project</h2>
        <p className="mt-2">
          Rheumatoid arthritis, inflammatory bowel disease, psoriasis, and lupus are treated with drugs that carry
          serious labeled risks. The reports, recalls, safety communications, trials, and papers that describe those
          risks are public, and they sit on different sites.
        </p>
        <p className="mt-3">
          Inflammation Signal Monitor pulls those sources, scores FAERS disproportionality with published formulas, and
          publishes a static dashboard. The code and the snapshot are in this repository.
        </p>
      </section>

      <section>
        <h2 className="text-2xl">Who it is for</h2>
        <p className="mt-2">
          Clinicians, pharmacovigilance staff, journalists, patient organizations, and researchers who want a starting
          point and a citation. Nothing here replaces a label, a regulator’s assessment, or a conversation with a
          clinician.
        </p>
      </section>

      <section>
        <h2 className="text-2xl">Operator</h2>
        <p className="mt-2">
          {OPERATOR_NAME} operates Open Health Signals, independent of any employer, using only public data.{" "}
          <a className="text-primary underline underline-offset-2" href={`mailto:${CONTACT_EMAIL}`}>
            {CONTACT_EMAIL}
          </a>
        </p>
        {postal ? <p className="mt-2">{postal}</p> : null}
        <p className="mt-2">{COPYRIGHT_LINE}</p>
      </section>

      <section>
        <h2 className="text-2xl">How to cite</h2>
        <p className="mt-2">The repository includes a CITATION.cff file. A plain citation:</p>
        <blockquote className="mt-3 border-l-2 border-primary pl-4 text-sm">
          Pai R. Open Health Signals: Inflammation Signal Monitor. Public FAERS dashboard for inflammatory disease and
          anti-inflammatory drug safety. 2026. https://openhealthsignals.org
        </blockquote>
      </section>

      <section>
        <h2 className="text-2xl">License</h2>
        <p className="mt-2">
          The code is MIT licensed. Source data keep the licenses named on the methods page. PubMed abstracts are not
          redistributed.
        </p>
      </section>
    </article>
  );
}
