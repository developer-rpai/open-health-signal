import type { Metadata } from "next";
import Link from "next/link";

import { TrendCharts } from "@/components/trend-charts";
import { Badge } from "@/components/ui/badge";
import { NCBI_DISCLAIMER_URL } from "@/lib/compliance";
import { getCdc, getManifest, getRecent, getTrends } from "@/lib/snapshot";

export const metadata: Metadata = {
  title: "Disease trends",
  description: "Trial starts and publications for rheumatoid arthritis, IBD, psoriasis, and lupus.",
};

export default function TrendsPage() {
  const trends = getTrends();
  const recent = getRecent();
  const cdc = getCdc();
  const manifest = getManifest();
  const publications = trends.publications.filter((row) => !row.topic_type || row.topic_type === "condition");

  return (
    <div className="space-y-10">
      <header className="max-w-3xl">
        <h1 className="text-4xl">Disease trends</h1>
        <p className="mt-3 text-muted-foreground">
          Trial starts and publications for rheumatoid arthritis, Crohn’s disease, ulcerative colitis,
          psoriasis, and systemic lupus erythematosus. Arthritis prevalence comes from CDC Chronic Disease
          Indicators. IBD does not have a matching CDC dataset, so the literature and the trial registry are the trend.
        </p>
        <p className="mt-2 text-sm text-muted-foreground">
          FAERS data as of {manifest.openfda_last_updated ?? "an undated extract"}.{" "}
          <Link href="/methods" className="text-primary underline underline-offset-2">
            How these numbers are made
          </Link>
        </p>
      </header>

      <TrendCharts
        publications={publications}
        trials={trends.trials}
        spikes={trends.spikes}
        cdc={cdc.rows}
      />

      <p className="text-sm leading-relaxed text-muted-foreground">{cdc.ibd_note}</p>
      {cdc.catalog_note ? <p className="text-sm text-muted-foreground">{cdc.catalog_note}</p> : null}

      <section className="grid gap-8 lg:grid-cols-2">
        <div>
          <h2 className="mb-3 text-2xl">Recent publications</h2>
          {recent.publications.length === 0 ? (
            <p className="text-sm text-muted-foreground">No recent PubMed records in this snapshot.</p>
          ) : (
            <ul className="space-y-3">
              {recent.publications.slice(0, 8).map((item) => (
                <li key={item.pmid} className="text-sm">
                  <a href={item.link} className="font-medium hover:underline">
                    {item.title}
                  </a>
                </li>
              ))}
            </ul>
          )}
          <p className="mt-3 text-xs text-muted-foreground">
            Titles and links only. Abstracts are not shown.{" "}
            <a className="underline underline-offset-2 hover:text-foreground" href={NCBI_DISCLAIMER_URL}>
              NCBI disclaimer
            </a>
            .
          </p>
        </div>
        <div>
          <h2 className="mb-3 text-2xl">Recently updated trials</h2>
          {recent.trials.length === 0 ? (
            <p className="text-sm text-muted-foreground">No recent trials in this snapshot.</p>
          ) : (
            <ul className="space-y-3">
              {recent.trials.slice(0, 8).map((item) => (
                <li key={item.nct_id} className="text-sm">
                  <a href={item.link} className="font-medium hover:underline">
                    {item.title}
                  </a>
                  <p className="mt-1 flex flex-wrap items-center gap-2 text-muted-foreground">
                    <span className="font-mono text-xs">{item.nct_id}</span>
                    {item.status ? <Badge variant="outline">{item.status}</Badge> : null}
                    {item.phase ? <span>{item.phase.replaceAll("_", " ")}</span> : null}
                  </p>
                </li>
              ))}
            </ul>
          )}
        </div>
      </section>
    </div>
  );
}
