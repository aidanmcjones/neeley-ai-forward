// Teal pulsing star marking model- or template-written content. Teal is reserved for AI output.
export function AiMark({ label = "AI", className = "" }: { label?: string; className?: string }) {
  return (
    <span className={`inline-flex items-center gap-1.5 text-teal font-semibold text-xs uppercase tracking-wide ${className}`}>
      <span aria-hidden="true" className="ai-pulse text-sm leading-none">✦</span>
      <span>{label}</span>
    </span>
  );
}
