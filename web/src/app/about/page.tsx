import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "About",
  description: "Why Inflammation Signal Monitor exists, and how to cite it.",
};

export default function AboutPage() {
  return (
    <article className="max-w-3xl space-y-8 text-[15px] leading-relaxed">
      <header>
        <h1 className="text-4xl">About</h1>
        <p className="mt-3 text-lg text-muted-foreground">
          A free, open record of public safety information for immune-mediated inflammatory disease.
        </p>
      </header>

      <section>
        <h2 className="text-2xl">Why this exists</h2>
        <p className="mt-2">
          Rheumatoid arthritis, inflammatory bowel disease, psoriasis, and lupus are treated with drugs that carry
          serious, labeled risks: gastrointestinal bleeding with NSAIDs, infection with TNF and interleukin
          inhibitors, and cardiovascular events and thrombosis with JAK inhibitors. The reports, recalls, safety
          communications, trials, and papers that describe those risks are public, but they sit on different sites
          and update on different calendars.
        </p>
        <p className="mt-3">
          Inflammation Signal Monitor pulls those public sources on a weekly schedule, scores FAERS
          disproportionality with published formulas, and publishes a static dashboard anyone can read without an
          account. The code, the tests for the formulas, and the data snapshot are in this repository.
        </p>
      </section>

      <section>
        <h2 className="text-2xl">Who it is for</h2>
        <p className="mt-2">
          Clinicians, pharmacovigilance staff, journalists, patient organizations, and researchers who want a
          starting point and a citation, not a clinical decision. Nothing here replaces a label, a regulator’s
          assessment, or a conversation with a clinician.
        </p>
      </section>

      <section>
        <h2 className="text-2xl">Maintainer</h2>
        <p className="mt-2">
          Rakesh Pai, a healthcare data engineer. The project is maintained as public-health infrastructure,
          independent of any employer, using only public data. Contributions are welcome; see CONTRIBUTING.md.
        </p>
      </section>

      <section>
        <h2 className="text-2xl">How to cite</h2>
        <p className="mt-2">The repository includes a CITATION.cff file. A plain citation:</p>
        <blockquote className="mt-3 border-l-2 border-primary pl-4 text-sm">
          Pai R. Inflammation Signal Monitor (version 0.1.0). Open-source pharmacovigilance dashboard for
          inflammatory disease and anti-inflammatory drug safety. 2026.
        </blockquote>
      </section>

      <section>
        <h2 className="text-2xl">License</h2>
        <p className="mt-2">
          The code is MIT licensed. Source data keep the licenses named on the methods page. PubMed abstracts are
          not redistributed.
        </p>
      </section>
    </article>
  );
}
