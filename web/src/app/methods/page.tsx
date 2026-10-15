import type { Metadata } from "next";

import { getValidation } from "@/lib/snapshot";

export const metadata: Metadata = {
  title: "Methods and data sources",
  description: "PRR, ROR, weekly spike detection, sources, licenses, and limitations.",
};

const SOURCES = [
  {
    name: "openFDA drug/event",
    url: "https://open.fda.gov/apis/drug/event/",
    use: "FAERS adverse-event counts",
    license: "CC0 / US government public domain",
  },
  {
    name: "openFDA drug/enforcement",
    url: "https://open.fda.gov/apis/drug/enforcement/",
    use: "Drug recalls",
    license: "CC0 / US government public domain",
  },
  {
    name: "FDA MedWatch RSS",
    url: "https://www.fda.gov/about-fda/contact-fda/stay-informed/rss-feeds/medwatch/rss.xml",
    use: "Safety notices",
    license: "US government public domain",
  },
  {
    name: "FDA Drug Safety Communications",
    url: "https://www.fda.gov/drugs/drug-safety-and-availability/drug-safety-communications",
    use: "HTML index. No public RSS was available.",
    license: "US government public domain",
  },
  {
    name: "ClinicalTrials.gov API v2",
    url: "https://clinicaltrials.gov/data-api/api",
    use: "Trial starts and recent updates",
    license: "NLM public-domain terms",
  },
  {
    name: "PubMed E-utilities",
    url: "https://www.ncbi.nlm.nih.gov/books/NBK25501/",
    use: "Publication counts and citation metadata",
    license: "NLM terms. Abstracts are not stored.",
  },
  {
    name: "CDC Chronic Disease Indicators",
    url: "https://data.cdc.gov/resource/hksd-2xuw.json",
    use: "US arthritis prevalence (topic=Arthritis)",
    license: "US government public domain",
  },
];

export default function MethodsPage() {
  const validation = getValidation();
  return (
    <article className="max-w-3xl space-y-8 text-[15px] leading-relaxed">
      <header>
        <h1 className="text-4xl">Methods and data sources</h1>
        <p className="mt-3 text-muted-foreground">
          The monitor is a weekly screen of public surveillance data. It is not a risk estimate and it is not medical advice.
        </p>
      </header>

      <section className="rounded-xl border border-amber-800/20 bg-amber-100/70 px-4 py-4 text-amber-950">
        <h2 className="text-xl">Not medical advice</h2>
        <p className="mt-2">
          Do not start, stop, or change a medicine because of a number on this site. Disproportionality does not
          show how often a reaction happens in people taking a drug, and it does not prove the drug caused the
          reaction. Decisions about treatment belong with a clinician. Adverse events can be reported to FDA MedWatch.
        </p>
      </section>

      <section>
        <h2 className="text-2xl">2×2 table</h2>
        <p className="mt-2">
          For an exposure (a drug or a class) and a MedDRA preferred term, reports in the openFDA FAERS extract form:
        </p>
        <div className="my-4 overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b text-left">
                <th className="py-2 pr-4" />
                <th className="py-2 pr-4">Reaction</th>
                <th className="py-2">No reaction</th>
              </tr>
            </thead>
            <tbody>
              <tr className="border-b">
                <th className="py-2 pr-4 text-left font-medium">Exposed</th>
                <td className="py-2 pr-4 font-mono">a</td>
                <td className="py-2 font-mono">b</td>
              </tr>
              <tr>
                <th className="py-2 pr-4 text-left font-medium">Comparator</th>
                <td className="py-2 pr-4 font-mono">c</td>
                <td className="py-2 font-mono">d</td>
              </tr>
            </tbody>
          </table>
        </div>
        <p>
          The proportional reporting ratio is (a / (a+b)) / (c / (c+d)). The reporting odds ratio is (a/b) / (c/d).
          95% intervals use the normal approximation on the log scale with 1.96 as the quantile. If any cell is zero,
          every cell is increased by 0.5 before the ratios and chi-square are calculated (Haldane–Anscombe). The
          displayed report count stays the observed count.
        </p>
        <p className="mt-3">
          An Evans signal requires at least 3 reports in cell a, a PRR of at least 2, and a chi-square of at least 4
          (Evans, Waller, and Davis, Pharmacoepidemiology and Drug Safety, 2001). A ROR signal requires at least 3
          reports in cell a and a lower 95% bound above 1.
        </p>
      </section>

      <section>
        <h2 className="text-2xl">What “exposed” means here</h2>
        <p className="mt-2">
          openFDA cannot require the ingredient and <span className="font-mono text-xs">drugcharacterization = 1</span> to
          sit on the same drug element. Counts are therefore ingredient mentions: the report lists the generic name
          and lists the reaction. Concomitant mentions dilute signals toward the null, so a signal that still appears
          has survived a conservative case definition. Class totals use one OR query, so a report naming two drugs in
          the class is counted once.
        </p>
        <p className="mt-3">
          The database-wide comparator is the rest of the openFDA extract (about the public FAERS file, not a
          treatment registry). There is no exposure denominator, so these ratios are not incidences.
        </p>
      </section>

      <section>
        <h2 className="text-2xl">Why JAK events are compared with TNF inhibitors</h2>
        <p className="mt-2">
          The 2021 FDA boxed warning for tofacitinib, upadacitinib, and baricitinib describes major adverse
          cardiovascular events, thrombosis, malignancy, and death. ORAL Surveillance compared tofacitinib with TNF
          inhibitors in rheumatoid arthritis. A FAERS-wide background is full of venous thrombosis from hospitalized
          patients, which can hide that contrast. The prespecified JAK checks therefore use TNF inhibitors as the
          active comparator. The same reactions are also scored against the whole extract and shown as a sensitivity
          result in the validation file; that sensitivity result is not the pass/fail rule.
        </p>
        <p className="mt-3">
          Tuberculosis with TNF inhibitors, and gastrointestinal bleeding or ulcer with NSAIDs, are large enough
          historically to test against the rest of FAERS.
        </p>
        <p className="mt-3 text-sm text-muted-foreground">{validation.rule}</p>
      </section>

      <section>
        <h2 className="text-2xl">Weekly spikes</h2>
        <p className="mt-2">
          Publication counts, trial starts, and dated FDA notices are bucketed by complete Monday–Sunday weeks.
          The week that contains the refresh day is left out, because it is still open. A point is a spike when the
          trailing baseline has at least four earlier weeks, the z-score is at least 2 (sample standard deviation),
          and the count is at least 1.5 times the baseline mean. A flat baseline has no z-score; a count at least 1.5
          times that flat mean is still flagged. This is a screen for the weekly job, not a seasonal model.
        </p>
      </section>

      <section>
        <h2 className="text-2xl">Sources and licenses</h2>
        <div className="mt-3 overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b text-left">
                <th className="py-2 pr-3 font-medium">Source</th>
                <th className="py-2 pr-3 font-medium">Use</th>
                <th className="py-2 font-medium">License</th>
              </tr>
            </thead>
            <tbody>
              {SOURCES.map((source) => (
                <tr key={source.name} className="border-b border-border/80 align-top">
                  <td className="py-2 pr-3">
                    <a href={source.url} className="underline decoration-border underline-offset-2 hover:text-primary">
                      {source.name}
                    </a>
                  </td>
                  <td className="py-2 pr-3">{source.use}</td>
                  <td className="py-2">{source.license}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <p className="mt-3">
          data.cdc.gov does not publish an IBD dataset comparable to Chronic Disease Indicators. Arthritis is taken
          from hksd-2xuw. Crohn’s disease and ulcerative colitis are followed with PubMed and ClinicalTrials.gov.
          openFDA’s own terms say not to rely on it for medical care; the extract can lag and counts are unvalidated.
        </p>
      </section>

      <section>
        <h2 className="text-2xl">Limitations</h2>
        <ul className="mt-2 list-disc space-y-2 pl-5">
          <li>Spontaneous reports under-count events, and publicity or litigation can suddenly increase them.</li>
          <li>Duplicate reports are not removed beyond whatever openFDA has already done.</li>
          <li>Indication confounding remains. People on these drugs are not the general population.</li>
          <li>Reports that mention both a JAK inhibitor and a TNF inhibitor stay in both sides of the active comparison.</li>
          <li>Product-use terms such as “drug ineffective” are computed when openFDA returns them and hidden in the default table.</li>
          <li>PubMed stores citation metadata only. Abstracts remain with the publisher.</li>
        </ul>
      </section>
    </article>
  );
}
