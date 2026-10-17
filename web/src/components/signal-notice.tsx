import Link from "next/link";

import { FDA_CAVEAT } from "@/lib/compliance";

export function SignalNotice() {
  return (
    <aside className="space-y-2 border-l-2 border-primary pl-4 text-sm leading-relaxed">
      <p>{FDA_CAVEAT}</p>
      <p>
        <Link href="/methods" className="text-primary underline underline-offset-2">
          How these numbers are made
        </Link>
      </p>
    </aside>
  );
}
