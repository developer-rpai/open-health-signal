import "server-only";

import fs from "fs";
import path from "path";

import type {
  AlertItem,
  CdcRow,
  CountRow,
  Manifest,
  Publication,
  QuarterlyRow,
  RecallItem,
  SignalRow,
  SpikeRow,
  Trial,
  ValidationCheck,
} from "./types";

function readJson<T>(name: string): T {
  const file = path.join(process.cwd(), "data", name);
  if (!fs.existsSync(file)) {
    throw new Error(
      `Missing ${file}. Run \`make refresh\` from the repository root before building the dashboard.`,
    );
  }
  return JSON.parse(fs.readFileSync(file, "utf8")) as T;
}

export function getManifest(): Manifest {
  return readJson<Manifest>("manifest.json");
}

export function getSignals(): SignalRow[] {
  return readJson<{ rows: SignalRow[] }>("signals.json").rows;
}

export function getQuarterly(): QuarterlyRow[] {
  return readJson<{ rows: QuarterlyRow[] }>("quarterly.json").rows;
}

export function getValidation(): { rule: string; recovered: number; tested: number; checks: ValidationCheck[] } {
  return readJson("validation.json");
}

export function getAlerts(): AlertItem[] {
  return readJson<{ items: AlertItem[] }>("alerts.json").items;
}

export function getRecalls(): RecallItem[] {
  return readJson<{ items: RecallItem[] }>("recalls.json").items;
}

export function getTrends(): {
  publications: CountRow[];
  trials: CountRow[];
  alerts_weekly: CountRow[];
  spikes: SpikeRow[];
} {
  return readJson("trends.json");
}

export function getRecent(): { publications: Publication[]; trials: Trial[] } {
  return readJson("recent.json");
}

export function getCdc(): { rows: CdcRow[]; ibd_note: string; catalog_note: string } {
  return readJson("cdc_arthritis.json");
}
