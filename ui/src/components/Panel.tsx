import type { ReactNode } from "react";

// Titled card. `meta` sits right of the title; `ai` gives the teal AI treatment.
export function Panel({ title, meta, children, ai = false, className = "", bodyClassName = "p-4" }: {
  title?: ReactNode; meta?: ReactNode; children?: ReactNode; ai?: boolean; className?: string; bodyClassName?: string;
}) {
  return (
    <section className={`rounded-lg border shadow-card min-w-0 ${ai ? "border-teal/50 bg-teal-soft/40" : "border-line bg-surface"} ${className}`}>
      {(title != null || meta != null) && (
        <header className={`flex items-center justify-between gap-3 border-b px-4 py-2.5 ${ai ? "border-teal/30" : "border-line"}`}>
          <h2 className="text-[13px] font-bold uppercase tracking-wide truncate">{title}</h2>
          {meta != null && <div className="text-xs text-muted shrink-0">{meta}</div>}
        </header>
      )}
      <div className={bodyClassName}>{children}</div>
    </section>
  );
}
