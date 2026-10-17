// Stance badge (Defend / Attack / Reprice / Partner, or any engine stance). Model output, so teal.
export function StanceBadge({ stance, className = "" }: { stance?: string | null; className?: string }) {
  if (!stance) return null;
  return (
    <span className={`inline-flex items-center gap-1 rounded border border-teal bg-teal-soft px-2 py-0.5 text-[11px] font-bold uppercase tracking-wider text-teal ${className}`}>
      <span className="sr-only">Stance: </span>{stance}
    </span>
  );
}
