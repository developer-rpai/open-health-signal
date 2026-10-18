"use client";

import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { CLASS_COLOR, formatNumber } from "@/lib/format";
import type { CdcRow, CountRow, SpikeRow } from "@/lib/types";

const CONDITIONS = [
  "rheumatoid_arthritis",
  "crohns_disease",
  "ulcerative_colitis",
  "psoriasis",
  "lupus",
];

function yearlyPivot(rows: CountRow[]) {
  const years = [...new Set(rows.filter((row) => row.grain === "year").map((row) => row.period))].sort();
  return years.map((year) => {
    const point: Record<string, string | number | null> = { year };
    for (const topic of CONDITIONS) {
      const match = rows.find((row) => row.grain === "year" && row.period === year && row.topic === topic);
      point[topic] = match ? match.count : null;
    }
    return point;
  });
}

function labelFor(rows: CountRow[], topic: string) {
  return rows.find((row) => row.topic === topic)?.label ?? topic;
}

export function TrendCharts({
  publications,
  trials,
  spikes,
  cdc,
}: {
  publications: CountRow[];
  trials: CountRow[];
  spikes: SpikeRow[];
  cdc: CdcRow[];
}) {
  const pub = yearlyPivot(publications);
  const trial = yearlyPivot(trials);
  const latestSpikes = spikes.filter((row) => row.latest);
  const historical = spikes.filter((row) => row.is_spike && !row.latest);
  const arthritis = cdc
    .filter((row) => row.question === "Arthritis among adults")
    .sort((a, b) => a.year.localeCompare(b.year));

  return (
    <div className="space-y-8">
      <section className="rounded-xl bg-card p-4 ring-1 ring-foreground/10">
        <h2 className="text-lg">Publications per year</h2>
        <p className="mb-3 text-sm text-muted-foreground">
          PubMed records matching each condition’s MeSH term. The current calendar year is year-to-date.
        </p>
        <div className="h-80 w-full" role="img" aria-label="Line chart of publications per year. The table lists the same counts.">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={pub} margin={{ left: 0, right: 8, top: 8, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(60,40,20,0.12)" />
              <XAxis dataKey="year" tick={{ fontSize: 12 }} />
              <YAxis tick={{ fontSize: 12 }} width={48} />
              <Tooltip formatter={(value) => formatNumber(Number(value))} />
              <Legend />
              {CONDITIONS.map((topic) => (
                <Line
                  key={topic}
                  type="monotone"
                  dataKey={topic}
                  name={labelFor(publications, topic)}
                  stroke={CLASS_COLOR[topic]}
                  strokeWidth={2}
                  dot={false}
                  connectNulls
                />
              ))}
            </LineChart>
          </ResponsiveContainer>
        </div>
        <CountTable caption="Publications per year" rows={pub} series={publications} />
      </section>

      <section className="rounded-xl bg-card p-4 ring-1 ring-foreground/10">
        <h2 className="text-lg">Trials started per year</h2>
        <p className="mb-3 text-sm text-muted-foreground">
          ClinicalTrials.gov studies whose start date falls in the year. This is not a count of status changes.
        </p>
        <div className="h-80 w-full" role="img" aria-label="Line chart of trials started per year. The table lists the same counts.">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={trial} margin={{ left: 0, right: 8, top: 8, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(60,40,20,0.12)" />
              <XAxis dataKey="year" tick={{ fontSize: 12 }} />
              <YAxis tick={{ fontSize: 12 }} width={40} />
              <Tooltip formatter={(value) => formatNumber(Number(value))} />
              <Legend />
              {CONDITIONS.map((topic) => (
                <Line
                  key={topic}
                  type="monotone"
                  dataKey={topic}
                  name={labelFor(trials, topic)}
                  stroke={CLASS_COLOR[topic]}
                  strokeWidth={2}
                  dot={false}
                  connectNulls
                />
              ))}
            </LineChart>
          </ResponsiveContainer>
        </div>
        <CountTable caption="Trials started per year" rows={trial} series={trials} />
      </section>

      <section className="rounded-xl bg-card p-4 ring-1 ring-foreground/10">
        <h2 className="text-lg">Weekly spike screen</h2>
        <p className="mb-3 text-sm text-muted-foreground">
          The latest complete week is compared with the weeks before it. A spike needs a z-score of at least 2 and a count at least 1.5 times the baseline mean, with four or more earlier weeks. FDA notices often lack that much history in a single RSS pull.
        </p>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="text-left text-muted-foreground">
              <tr>
                <th className="py-2 pr-3 font-medium">Series</th>
                <th className="py-2 pr-3 font-medium">Topic</th>
                <th className="py-2 pr-3 font-medium">Week</th>
                <th className="py-2 pr-3 text-right font-medium">Count</th>
                <th className="py-2 pr-3 text-right font-medium">Baseline</th>
                <th className="py-2 font-medium">Latest week</th>
              </tr>
            </thead>
            <tbody>
              {latestSpikes.map((row) => (
                <tr key={`${row.series}-${row.topic}`} className="border-t border-border">
                  <td className="py-2 pr-3 capitalize">{row.series}</td>
                  <td className="py-2 pr-3">{row.label}</td>
                  <td className="py-2 pr-3 font-mono text-xs">{row.period}</td>
                  <td className="py-2 pr-3 text-right font-mono text-xs">{formatNumber(row.count)}</td>
                  <td className="py-2 pr-3 text-right font-mono text-xs">{formatNumber(row.baseline_mean, 1)}</td>
                  <td className="py-2">{row.is_spike ? "Spike" : row.reason === "insufficient_baseline" ? "Not enough weeks" : "Within baseline"}</td>
                </tr>
              ))}
              {latestSpikes.length === 0 ? (
                <tr>
                  <td colSpan={6} className="py-4 text-muted-foreground">
                    No weekly series in this snapshot.
                  </td>
                </tr>
              ) : null}
            </tbody>
          </table>
        </div>
        {historical.length > 0 ? (
          <p className="mt-3 text-sm text-muted-foreground">
            Earlier weeks that cleared the same rule:{" "}
            {historical.map((row) => `${row.label} ${row.period} (${formatNumber(row.count)})`).join("; ")}.
          </p>
        ) : (
          <p className="mt-3 text-sm text-muted-foreground">No earlier week in this window cleared the spike rule.</p>
        )}
      </section>

      <section className="rounded-xl bg-card p-4 ring-1 ring-foreground/10">
        <h2 className="text-lg">Arthritis among US adults</h2>
        <p className="mb-3 text-sm text-muted-foreground">
          CDC Chronic Disease Indicators, dataset hksd-2xuw, crude prevalence among US adults, BRFSS.
        </p>
        {arthritis.length === 0 ? (
          <p className="text-sm text-muted-foreground">The CDC indicator did not load in this snapshot.</p>
        ) : (
          <>
          <div className="h-64 w-full" role="img" aria-label="Line chart of arthritis prevalence. The table lists the same percentages.">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={arthritis} margin={{ left: 0, right: 8, top: 8, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(60,40,20,0.12)" />
                <XAxis dataKey="year" tick={{ fontSize: 12 }} />
                <YAxis tick={{ fontSize: 12 }} width={36} domain={["dataMin - 1", "dataMax + 1"]} />
                <Tooltip formatter={(value) => `${formatNumber(Number(value), 1)}%`} />
                <Line type="monotone" dataKey="data_value" name="Percent" stroke="#0f5c5c" strokeWidth={2} dot />
              </LineChart>
            </ResponsiveContainer>
          </div>
          <div className="mt-4 overflow-x-auto">
            <table className="w-full text-sm">
              <caption className="mb-2 text-left text-sm text-muted-foreground">Arthritis prevalence, percent of US adults</caption>
              <thead className="text-left text-muted-foreground">
                <tr>
                  <th className="py-2 pr-3 font-medium">Year</th>
                  <th className="py-2 text-right font-medium">Percent</th>
                </tr>
              </thead>
              <tbody>
                {[...arthritis].sort((a, b) => b.year.localeCompare(a.year)).map((row) => (
                  <tr key={row.year} className="border-t border-border">
                    <td className="py-1.5 pr-3">{row.year}</td>
                    <td className="py-1.5 text-right font-mono text-xs">{formatNumber(Number(row.data_value), 1)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          </>
        )}
      </section>
    </div>
  );
}

function CountTable({
  caption,
  rows,
  series,
}: {
  caption: string;
  rows: Record<string, string | number | null>[];
  series: CountRow[];
}) {
  if (rows.length === 0) return null;
  return (
    <div className="mt-4 overflow-x-auto">
      <table className="w-full text-sm">
        <caption className="mb-2 text-left text-sm text-muted-foreground">{caption}</caption>
        <thead className="text-left text-muted-foreground">
          <tr>
            <th className="py-2 pr-3 font-medium">Year</th>
            {CONDITIONS.map((topic) => (
              <th key={topic} className="py-2 pr-3 text-right font-medium">
                {labelFor(series, topic)}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {[...rows].sort((a, b) => String(b.year).localeCompare(String(a.year))).map((row) => (
            <tr key={String(row.year)} className="border-t border-border">
              <td className="py-1.5 pr-3">{row.year}</td>
              {CONDITIONS.map((topic) => (
                <td key={topic} className="py-1.5 pr-3 text-right font-mono text-xs">
                  {row[topic] == null ? "n/a" : formatNumber(Number(row[topic]))}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
