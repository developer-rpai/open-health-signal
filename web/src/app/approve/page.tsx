import type { Metadata } from "next";

import { ApprovePanel } from "@/components/approve-panel";

export const metadata: Metadata = {
  title: "Approve issue",
  description: "Owner preview of the Monday draft. A magic link and an allowlisted email are required.",
};

export default function ApprovePage() {
  return (
    <article className="space-y-6">
      <header className="max-w-3xl">
        <p className="font-mono text-[11px] tracking-[0.18em] text-primary uppercase">Owner</p>
        <h1 className="mt-2 text-4xl">Preview and approve</h1>
        <p className="mt-3 text-lg leading-relaxed text-muted-foreground">
          Monday’s job stores the issue as a draft. Sign in with the magic link. Only an allowlisted email can open
          the draft. Approving it is what starts the send. There is no other admin panel.
        </p>
      </header>
      <ApprovePanel />
    </article>
  );
}
