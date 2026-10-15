import type { Metadata } from "next";
import Link from "next/link";

import { SubscribeForm } from "@/components/subscribe-form";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { formatGenerated, formatNumber, formatRatio, titleCaseReaction } from "@/lib/format";
import { getAlerts, getManifest, getRecalls, getValidation } from "@/lib/snapshot";

export const metadata: Metadata = { title: "Overview" };

export default function OverviewPage() {
  const manifest = getManifest();
  const validation = getValidation();
  const alerts = getAlerts();
  const recalls = getRecalls();
  const tagged = alerts.filter((item) => item.tags.length > 0);
  const shownAlerts = (tagged.length > 0 ? tagged : alerts).slice(0, 8);
  const groups = [...new Set(validation.checks.map((check) => check.group))];
  const failedSources = manifest.sources.filter((source) => source.status !== "ok");

  return (
    <div className="space-y-10">
      <section className="max-w-3xl">
        <h1 className="text-4xl leading-tight sm:text-5xl">
          Safety signals for inflammatory disease, kept in one public record.
        </h1>
        <p className="mt-4 text-lg leading-relaxed text-muted-foreground">
          FAERS disproportionality for NSAIDs, corticosteroids, TNF and interleukin inhibitors, and JAK inhibitors,
          next to FDA notices, recalls, trial starts, and new publications. The snapshot is rebuilt weekly.
        </p>
        <p className="mt-3 text-sm text-muted-foreground">
          openFDA extract dated {manifest.openfda_last_updated ?? "unknown"}. Snapshot generated{" "}
          {formatGenerated(manifest.generated_at)}.
        </p>
      </section>

      <section className="grid gap-6 rounded-2xl bg-card p-6 ring-1 ring-foreground/10 lg:grid-cols-[1.15fr_0.85fr] lg:items-center sm:p-8">
        <div>
          <p className="font-mono text-[11px] tracking-[0.18em] text-primary uppercase">Weekly briefing</p>
          <h2 className="mt-2 text-3xl">One email after the Monday refresh.</h2>
          <p className="mt-3 leading-relaxed text-muted-foreground">
            New FDA safety alerts and recalls, drug-safety signals that are new or stronger, notable trials, and the
            top new PubMed papers. Past issues stay in the{" "}
            <Link href="/newsletter" className="text-primary underline-offset-2 hover:underline">
              archive
            </Link>
            .
          </p>
        </div>
        <SubscribeForm id="home-subscribe" />
      </section>

      {failedSources.length > 0 ? (
        <div className="rounded-xl border border-destructive/30 bg-destructive/5 px-4 py-3 text-sm" role="status">
          <p className="font-medium">A source did not fully load.</p>
          <ul className="mt-2 space-y-1">
            {failedSources.map((source) => (
              <li key={source.id}>
                <span className="font-medium">{source.label}</span> — {source.status}. {source.detail}
              </li>
            ))}
          </ul>
        </div>
      ) : null}

      <section className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <Stat label="FAERS reports in the extract" value={formatNumber(manifest.faers_report_total)} />
        <Stat label="Rows in the signal table" value={formatNumber(manifest.signal_rows)} />
        <Stat
          label="Known signals recovered"
          value={`${validation.recovered} of ${validation.tested}`}
        />
        <Stat label="Recalls matched" value={formatNumber(recalls.length)} />
      </section>

      <section>
        <div className="mb-3 flex items-end justify-between gap-4">
          <h2 className="text-2xl">Known-signal sanity check</h2>
          <Link href="/methods" className="text-sm text-primary underline-offset-2 hover:underline">
            How recovery is defined
          </Link>
        </div>
        <div className="grid gap-3 lg:grid-cols-3">
          {groups.map((group) => {
            const checks = validation.checks.filter((check) => check.group === group);
            const recovered = checks.filter((check) => check.recovered).length;
            const evans = checks.filter((check) => check.evans_signal).length;
            return (
              <Card key={group}>
                <CardHeader>
                  <CardTitle>{group}</CardTitle>
                  <CardDescription>
                    {evans} meet the Evans screen. {recovered} of {checks.length} clear Evans or a ROR bound above 1.
                  </CardDescription>
                </CardHeader>
                <CardContent className="space-y-2">
                  {checks.map((check) => (
                    <div key={check.id} className="flex items-start justify-between gap-3 text-sm">
                      <span>{titleCaseReaction(check.reaction)}</span>
                      <Badge variant={check.evans_signal ? "default" : "outline"}>
                        {!check.recovered
                          ? "Not recovered"
                          : check.evans_signal
                            ? `Evans · PRR ${formatRatio(check.prr)}`
                            : `ROR only · PRR ${formatRatio(check.prr)}`}
                      </Badge>
                    </div>
                  ))}
                </CardContent>
              </Card>
            );
          })}
        </div>
        <p className="mt-3 max-w-3xl text-sm leading-relaxed text-muted-foreground">
          Evans screen on this snapshot:{" "}
          {validation.checks
            .filter((check) => check.evans_signal)
            .map((check) => titleCaseReaction(check.reaction))
            .join(", ") || "none"}
          .
          {validation.checks.some((check) => check.recovered && !check.evans_signal)
            ? ` ROR only, with PRR below 2: ${validation.checks
                .filter((check) => check.recovered && !check.evans_signal)
                .map((check) => `${titleCaseReaction(check.reaction)} (PRR ${formatRatio(check.prr)})`)
                .join("; ")}. A ROR signal here is not the same as an Evans signal.`
            : ""}
        </p>
      </section>

      <section className="grid gap-8 lg:grid-cols-2">
        <div>
          <h2 className="mb-3 text-2xl">Latest FDA notices</h2>
          {shownAlerts.length === 0 ? (
            <p className="rounded-xl border border-dashed px-4 py-8 text-sm text-muted-foreground">
              No notices in this snapshot. The MedWatch feed or the Drug Safety Communications page did not return items.
            </p>
          ) : (
            <ul className="space-y-3">
              {shownAlerts.map((item) => (
                <li key={item.link || item.title} className="rounded-xl bg-card p-4 ring-1 ring-foreground/10">
                  <p className="text-xs tracking-wide text-muted-foreground uppercase">{item.source}</p>
                  <a href={item.link} className="mt-1 block font-medium hover:underline">
                    {item.title}
                  </a>
                  {item.published ? <p className="mt-1 text-xs text-muted-foreground">{item.published}</p> : null}
                  {item.summary ? <p className="mt-2 line-clamp-3 text-sm text-muted-foreground">{item.summary}</p> : null}
                  {item.tags.length > 0 ? (
                    <p className="mt-2 text-xs text-primary">{item.tags.join(" · ")}</p>
                  ) : null}
                </li>
              ))}
            </ul>
          )}
          {tagged.length === 0 && alerts.length > 0 ? (
            <p className="mt-3 text-sm text-muted-foreground">
              None of the current feed items name a monitored drug or condition. The list above is the unfiltered feed.
            </p>
          ) : null}
        </div>
        <div>
          <h2 className="mb-3 text-2xl">Recent recalls</h2>
          {recalls.length === 0 ? (
            <p className="rounded-xl border border-dashed px-4 py-8 text-sm text-muted-foreground">
              No openFDA enforcement reports matched the monitored product names.
            </p>
          ) : (
            <ul className="space-y-3">
              {recalls.slice(0, 6).map((item) => (
                <li key={item.recall_number} className="rounded-xl bg-card p-4 ring-1 ring-foreground/10">
                  <div className="flex items-center justify-between gap-2">
                    <p className="font-mono text-xs text-muted-foreground">{item.recall_number}</p>
                    <Badge variant="outline">{item.classification || "Unclassified"}</Badge>
                  </div>
                  <p className="mt-2 text-sm font-medium">{item.product_description}</p>
                  <p className="mt-1 text-sm text-muted-foreground">{item.reason}</p>
                  <p className="mt-2 text-xs text-muted-foreground">
                    {item.recalling_firm}
                    {item.report_date ? ` · reported ${item.report_date}` : ""} · matched “{item.matched_term}”
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

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <Card size="sm">
      <CardHeader>
        <CardDescription>{label}</CardDescription>
        <CardTitle className="font-mono text-2xl tracking-tight">{value}</CardTitle>
      </CardHeader>
    </Card>
  );
}
