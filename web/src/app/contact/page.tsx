import type { Metadata } from "next";

import { ContactForm } from "@/components/contact-form";

export const metadata: Metadata = {
  title: "Contact",
  description: "Research collaboration, data, code, custom analysis, media, or sponsorship.",
};

export default function ContactPage() {
  return (
    <article className="grid gap-10 lg:grid-cols-[1.1fr_0.9fr] lg:items-start">
      <div className="max-w-xl">
        <h1 className="text-4xl leading-tight">Contact</h1>
        <p className="mt-4 text-lg leading-relaxed text-muted-foreground">
          Research collaboration, a public dataset, a code change, a custom analysis, press, or sponsorship. You can
          also write to{" "}
          <a className="text-primary underline underline-offset-2" href="mailto:contact@openhealthsignals.org">
            contact@openhealthsignals.org
          </a>
          .
        </p>
        <ul className="mt-6 space-y-3 text-sm leading-relaxed">
          <li>Research collaboration — methods, replication, or a joint analysis.</li>
          <li>Data expansion — a public source that should be in the weekly pull.</li>
          <li>Code contribution — a patch to the pipeline or the dashboard.</li>
          <li>Custom analysis — a question the published tables do not answer.</li>
          <li>Media and sponsorship — interviews, or support for hosting.</li>
        </ul>
      </div>
      <div className="rounded-2xl bg-card p-6 ring-1 ring-foreground/10">
        <h2 className="text-2xl">Message</h2>
        <div className="mt-4">
          <ContactForm />
        </div>
      </div>
    </article>
  );
}
