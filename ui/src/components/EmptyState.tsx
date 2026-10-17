import type { ReactNode } from "react";

// Honest empty state: always names the missing file.
export function EmptyState({ file, message, children }: { file?: string; message?: string; children?: ReactNode }) {
  return (
    <div role="status" className="rounded-lg border border-dashed border-line bg-surface-2 px-5 py-6 text-sm">
      <div className="font-semibold">{message ?? (file ? `Could not load ${file}` : "Nothing to show")}</div>
      {file && (
        <div className="mt-1 text-muted">
          Missing or unreadable: <code className="font-mono text-xs">{file}</code>. Regenerate with{" "}
          <code className="font-mono text-xs">python -m agent.ui_export</code>.
        </div>
      )}
      {children && <div className="mt-2 text-muted">{children}</div>}
    </div>
  );
}
