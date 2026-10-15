export type SourceStatus = {
  id: string;
  label: string;
  status: "ok" | "partial" | "error" | string;
  detail: string;
  rows: number;
};

export type Manifest = {
  product: string;
  version: string;
  generated_at: string;
  refresh_cadence: string;
  spike_grain: string;
  disclaimer: string;
  openfda_last_updated: string | null;
  faers_report_total: number | null;
  signal_rows: number;
  high_signal_rows: number;
  new_high_signals: number;
  high_signal_baseline_run: boolean;
  validation_recovered: number;
  validation_tested: number;
  sources: SourceStatus[];
};

export type SignalRow = {
  scope: "drug" | "class";
  drug: string | null;
  drug_label: string | null;
  drug_class: string;
  drug_class_label: string;
  reaction: string;
  analysis: "database" | "active_comparator";
  comparator: string;
  comparator_label: string;
  exposure_n: number;
  preset: boolean;
  admin_term: boolean;
  indication_term: boolean;
  a: number;
  b: number;
  c: number;
  d: number;
  prr: number | null;
  prr_ci_low: number | null;
  prr_ci_high: number | null;
  ror: number | null;
  ror_ci_low: number | null;
  ror_ci_high: number | null;
  chi2: number | null;
  correction: string;
  evans_signal: boolean;
  ror_signal: boolean;
};

export type QuarterlyRow = {
  drug_class: string;
  drug_class_label: string;
  year: number;
  quarter: number;
  period: string;
  report_count: number;
  partial: boolean;
};

export type ValidationCheck = {
  id: string;
  group: string;
  title: string;
  key: string;
  reaction: string;
  analysis: string;
  comparator: string;
  recovered: boolean;
  reason: string;
  prr: number | null;
  prr_ci_low: number | null;
  prr_ci_high: number | null;
  ror: number | null;
  ror_ci_low: number | null;
  ror_ci_high: number | null;
  chi2: number | null;
  a: number | null;
  evans_signal: boolean;
  ror_signal: boolean;
  exposure_n?: number;
  database_prr?: number | null;
  database_ror_ci_low?: number | null;
  database_ror_signal?: boolean;
  database_evans_signal?: boolean;
};

export type AlertItem = {
  source: string;
  title: string;
  link: string;
  published: string;
  summary: string;
  tags: string[];
};

export type RecallItem = {
  recall_number: string;
  product_description: string;
  reason: string;
  status: string;
  classification: string;
  recalling_firm: string;
  report_date: string;
  matched_term: string;
  drug_class: string;
  drug_class_label: string;
};

export type CountRow = {
  topic: string;
  label: string;
  topic_type?: string;
  grain: "year" | "week";
  period: string;
  period_start: string;
  count: number;
  partial: boolean;
};

export type SpikeRow = {
  series: string;
  topic: string;
  label: string;
  period: string;
  period_start: string;
  count: number;
  baseline_mean: number | null;
  baseline_sd: number | null;
  z: number | null;
  ratio: number | null;
  is_spike: boolean;
  latest?: boolean;
  reason?: string;
};

export type Publication = {
  pmid: string;
  title: string;
  journal: string;
  published: string;
  topic: string;
  link: string;
};

export type Trial = {
  nct_id: string;
  title: string;
  status: string;
  phase: string;
  conditions: string;
  start_date: string;
  last_update: string;
  topic: string;
  link: string;
};

export type CdcRow = {
  year: string;
  question: string;
  data_value: number;
  unit: string;
  stratification: string;
  low_ci: number | null;
  high_ci: number | null;
};
