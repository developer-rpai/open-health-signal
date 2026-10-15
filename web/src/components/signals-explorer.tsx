"use client";

import { useMemo, useState } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { CLASS_COLOR, CLASS_ORDER, formatInterval, formatNumber, formatRatio, titleCaseReaction } from "@/lib/format";
import type { QuarterlyRow, SignalRow } from "@/lib/types";

type Props = {
  rows: SignalRow[];
  quarterly: QuarterlyRow[];
};

export function SignalsExplorer({ rows, quarterly }: Props) {
  const [drugClass, setDrugClass] = useState("jak_inhibitor");
  const [drug, setDrug] = useState("all");
  const [analysis, setAnalysis] = useState<"database" | "active_comparator">("database");
  const [presetOnly, setPresetOnly] = useState(true);

  const classLabels = useMemo(() => {
    const labels = new Map<string, string>();
    for (const row of rows) labels.set(row.drug_class, row.drug_class_label);
    return labels;
  }, [rows]);

  const drugs = useMemo(() => {
    const list = new Map<string, string>();
    for (const row of rows) {
      if (row.scope === "drug" && row.drug && row.drug_class === drugClass && row.drug_label) {
        list.set(row.drug, row.drug_label);
      }
    }
    return [...list.entries()].sort((a, b) => a[1].localeCompare(b[1]));
  }, [rows, drugClass]);

  const filtered = useMemo(() => {
    return rows
      .filter((row) => row.analysis === analysis)
      .filter((row) => {
        if (analysis === "active_comparator") {
          return row.scope === "class" && row.drug_class === "jak_inhibitor";
        }
        if (drug !== "all") return row.scope === "drug" && row.drug === drug;
        return row.scope === "class" && row.drug_class === drugClass;
      })
      .filter((row) => !row.admin_term && !row.indication_term)
      .filter((row) => !presetOnly || row.preset)
      .sort((a, b) => (b.prr ?? 0) - (a.prr ?? 0));
  }, [rows, analysis, drug, drugClass, presetOnly]);

  const chartRows = filtered.slice(0, 12).map((row) => ({
    name: titleCaseReaction(row.reaction),
    prr: row.prr ?? 0,
    signal: row.evans_signal || row.ror_signal,
  }));

  const quarterRows = quarterly
    .filter((row) => row.drug_class === (analysis === "active_comparator" ? "jak_inhibitor" : drugClass))
    .filter((row) => !(row.partial && row.report_count === 0))
    .sort((a, b) => a.period.localeCompare(b.period));

  const exposure = filtered[0]?.exposure_n;

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-4">
        <div className="flex flex-wrap gap-2" role="group" aria-label="Drug class">
          {CLASS_ORDER.map((key) => (
            <Button
              key={key}
              type="button"
              size="sm"
              variant={drugClass === key && analysis === "database" ? "default" : "outline"}
              onClick={() => {
                setAnalysis("database");
                setDrugClass(key);
                setDrug("all");
              }}
            >
              {classLabels.get(key) ?? key}
            </Button>
          ))}
          <Button
            type="button"
            size="sm"
            variant={analysis === "active_comparator" ? "default" : "outline"}
            onClick={() => {
              setAnalysis("active_comparator");
              setDrug("all");
              setDrugClass("jak_inhibitor");
            }}
          >
            JAK vs TNF
          </Button>
        </div>
        <div className="flex flex-col gap-3 sm:flex-row sm:items-end">
          <label className="flex flex-col gap-1 text-sm">
            <span className="text-muted-foreground">Drug</span>
            <select
              className="h-9 min-w-52 rounded-lg border border-input bg-card px-2.5 text-sm"
              value={analysis === "active_comparator" ? "all" : drug}
              disabled={analysis === "active_comparator"}
              onChange={(event) => setDrug(event.target.value)}
            >
              <option value="all">Whole class</option>
              {drugs.map(([key, label]) => (
                <option key={key} value={key}>
                  {label}
                </option>
              ))}
            </select>
          </label>
          <label className="flex items-center gap-2 pb-2 text-sm">
            <input
              type="checkbox"
              checked={presetOnly}
              onChange={(event) => setPresetOnly(event.target.checked)}
              className="size-4 accent-[var(--primary)]"
            />
            Prespecified reactions only
          </label>
        </div>
      </div>

      <p className="text-sm leading-relaxed text-muted-foreground">
        {analysis === "active_comparator"
          ? "Active comparator: JAK inhibitor reports versus TNF inhibitor reports. This is the comparison used for the thrombosis and MACE sanity check, because a hospital-heavy FAERS background can hide those events."
          : `Database-wide comparison for ${classLabels.get(drugClass) ?? drugClass}${drug !== "all" ? "" : " as a class"}. The comparator is every other report in the openFDA FAERS extract.`}
        {exposure != null ? ` Exposure reports in this row set: ${formatNumber(exposure)}.` : ""}
        {" "}Ingredient mentions, not primary-suspect-only counts. Not incidence.
      </p>

      {filtered.length === 0 ? (
        <div className="rounded-xl border border-dashed border-border bg-card px-4 py-10 text-center text-sm text-muted-foreground">
          No signal rows for this filter. If the FAERS source failed, the gap is listed on the overview.
        </div>
      ) : (
        <>
          <div className="rounded-xl bg-card p-4 ring-1 ring-foreground/10">
            <h2 className="mb-3 text-lg">Proportional reporting ratio</h2>
            <div className="h-72 w-full">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={chartRows} layout="vertical" margin={{ left: 16, right: 16, top: 8, bottom: 8 }}>
                  <CartesianGrid strokeDasharray="3 3" horizontal={false} stroke="rgba(60,40,20,0.12)" />
                  <XAxis type="number" tick={{ fontSize: 12 }} />
                  <YAxis type="category" dataKey="name" width={168} tick={{ fontSize: 11 }} />
                  <Tooltip formatter={(value) => formatRatio(Number(value))} />
                  <Bar dataKey="prr" name="PRR" fill={CLASS_COLOR[drugClass] ?? "#0f5c5c"} radius={3} />
                </BarChart>
              </ResponsiveContainer>
            </div>
            <p className="mt-2 text-xs text-muted-foreground">
              Evans screen: PRR at least 2, chi-square at least 4, and at least 3 reports with the drug and the reaction.
              A ROR signal means the lower 95% bound is above 1.
            </p>
          </div>

          <div className="rounded-xl bg-card ring-1 ring-foreground/10">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Reaction</TableHead>
                  <TableHead className="text-right">Reports</TableHead>
                  <TableHead className="text-right">PRR</TableHead>
                  <TableHead className="text-right">95% CI</TableHead>
                  <TableHead className="text-right">ROR</TableHead>
                  <TableHead className="text-right">95% CI</TableHead>
                  <TableHead>Screen</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {filtered.map((row) => (
                  <TableRow key={`${row.analysis}-${row.reaction}-${row.scope}-${row.drug}`}>
                    <TableCell className="font-medium">{titleCaseReaction(row.reaction)}</TableCell>
                    <TableCell className="text-right font-mono text-xs">{formatNumber(row.a)}</TableCell>
                    <TableCell className="text-right font-mono text-xs">{formatRatio(row.prr)}</TableCell>
                    <TableCell className="text-right font-mono text-xs">{formatInterval(row.prr_ci_low, row.prr_ci_high)}</TableCell>
                    <TableCell className="text-right font-mono text-xs">{formatRatio(row.ror)}</TableCell>
                    <TableCell className="text-right font-mono text-xs">{formatInterval(row.ror_ci_low, row.ror_ci_high)}</TableCell>
                    <TableCell>
                      <div className="flex flex-wrap gap-1">
                        {row.evans_signal ? <Badge>Evans</Badge> : null}
                        {row.ror_signal ? <Badge variant="secondary">ROR</Badge> : null}
                        {!row.evans_signal && !row.ror_signal ? (
                          <span className="text-xs text-muted-foreground">Below threshold</span>
                        ) : null}
                      </div>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        </>
      )}

      <div className="rounded-xl bg-card p-4 ring-1 ring-foreground/10">
        <h2 className="mb-1 text-lg">Quarterly FAERS mentions</h2>
        <p className="mb-3 text-sm text-muted-foreground">
          Class-level report counts by receipt quarter. A partial quarter at the end of the openFDA extract is omitted when it is still zero.
          {drug !== "all" ? " Selecting a single drug does not change this chart; quarters are counted for the class." : ""}
        </p>
        {quarterRows.length === 0 ? (
          <p className="text-sm text-muted-foreground">No quarterly counts for this class.</p>
        ) : (
          <div className="h-64 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={quarterRows} margin={{ left: 0, right: 8, top: 8, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(60,40,20,0.12)" />
                <XAxis dataKey="period" tick={{ fontSize: 11 }} />
                <YAxis tick={{ fontSize: 11 }} width={48} />
                <Tooltip formatter={(value) => formatNumber(Number(value))} />
                <Line
                  type="monotone"
                  dataKey="report_count"
                  name="Reports"
                  stroke={CLASS_COLOR[analysis === "active_comparator" ? "jak_inhibitor" : drugClass]}
                  strokeWidth={2}
                  dot={false}
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
        )}
      </div>
    </div>
  );
}
