export function formatNumber(value: number | null | undefined, digits = 0): string {
  if (value == null || Number.isNaN(value)) return "—";
  return value.toLocaleString("en-US", {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  });
}

export function formatRatio(value: number | null | undefined): string {
  if (value == null || Number.isNaN(value)) return "—";
  if (value >= 100) return value.toLocaleString("en-US", { maximumFractionDigits: 1 });
  return value.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

export function formatInterval(low: number | null, high: number | null): string {
  if (low == null || high == null) return "—";
  return `${formatRatio(low)}–${formatRatio(high)}`;
}

export function formatGenerated(iso: string): string {
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return iso;
  const formatted = date.toLocaleString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
    hour: "numeric",
    minute: "2-digit",
    timeZone: "America/Los_Angeles",
  });
  return `${formatted} PT`;
}

export function titleCaseReaction(reaction: string): string {
  return reaction
    .toLowerCase()
    .replace(/\b\w/g, (letter) => letter.toUpperCase());
}

export const CLASS_ORDER = [
  "nsaid",
  "corticosteroid",
  "tnf_inhibitor",
  "il_inhibitor",
  "jak_inhibitor",
  "other_immunomodulator",
] as const;

export const CLASS_COLOR: Record<string, string> = {
  nsaid: "#8a5a12",
  corticosteroid: "#5c4d78",
  tnf_inhibitor: "#0f5c5c",
  il_inhibitor: "#1e4f8a",
  jak_inhibitor: "#8c3030",
  other_immunomodulator: "#5c5848",
  rheumatoid_arthritis: "#8c3030",
  crohns_disease: "#0f5c5c",
  ulcerative_colitis: "#1e4f8a",
  psoriasis: "#8a5a12",
  lupus: "#5c4d78",
};
