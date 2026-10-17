import type { Metadata } from "next";

import { SignalNotice } from "@/components/signal-notice";
import { SignalsExplorer } from "@/components/signals-explorer";
import { getManifest, getQuarterly, getSignals } from "@/lib/snapshot";

export const metadata: Metadata = {
  title: "Drug signals",
  description: "PRR and ROR for anti-inflammatory drugs in the openFDA FAERS extract.",
};

export default function SignalsPage() {
  const rows = getSignals();
  const quarterly = getQuarterly();
  const manifest = getManifest();
  return (
    <div className="space-y-6">
      <header className="max-w-3xl">
        <h1 className="text-4xl">Drug safety signals</h1>
        <p className="mt-3 text-muted-foreground">
          Proportional reporting ratios and reporting odds ratios for prespecified MedDRA reactions, plus the leading
          reactions returned by openFDA. Filter by class or by drug. The JAK versus TNF view compares thrombosis and
          major cardiovascular events with an active comparator.
        </p>
        <p className="mt-2 text-sm text-muted-foreground">
          FAERS data as of {manifest.openfda_last_updated ?? "an undated extract"}.
        </p>
      </header>
      <SignalNotice />
      {rows.length === 0 ? (
        <p className="rounded-xl border border-dashed px-4 py-10 text-sm text-muted-foreground">
          The signal table is empty. openFDA drug/event did not return counts for this snapshot.
        </p>
      ) : (
        <SignalsExplorer rows={rows} quarterly={quarterly} />
      )}
    </div>
  );
}
