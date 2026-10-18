import { SELECTED_WORK } from "@/lib/selected-work";

export function SelectedWork() {
  if (SELECTED_WORK.length === 0) return null;
  return (
    <section>
      <h2 className="text-2xl">Selected work</h2>
      <ul className="mt-3 space-y-3">
        {SELECTED_WORK.map((item) => (
          <li key={item.url}>
            <a className="text-primary underline underline-offset-2" href={item.url}>
              {item.title}
            </a>
            <span className="text-muted-foreground">
              {" "}
              · {item.venue} · {item.year}
            </span>
          </li>
        ))}
      </ul>
    </section>
  );
}
