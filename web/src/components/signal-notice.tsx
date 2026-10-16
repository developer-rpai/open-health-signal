import { FDA_CAVEAT, RESEARCH_LINE } from "@/lib/compliance";

export function SignalNotice() {
  return (
    <aside className="space-y-2 rounded-xl border border-amber-800/20 bg-amber-100/70 px-4 py-3 text-sm leading-relaxed text-amber-950">
      <p>{FDA_CAVEAT}</p>
      <p>{RESEARCH_LINE}</p>
      <p>
        A highlighted row is a disproportionality signal: the reaction was reported more often than expected (PRR in
        the table).
      </p>
    </aside>
  );
}
