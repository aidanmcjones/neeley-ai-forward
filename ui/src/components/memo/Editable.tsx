import { createElement, useRef } from "react";

// A memo text block that becomes contentEditable in edit mode. It is uncontrolled while
// editing (React never rewrites it under the caret) and commits its text on blur.
export function Editable({ id, text, editing, onCommit, onDraft, as = "span", className = "" }: {
  id: string; text: string; editing: boolean; onCommit: (id: string, text: string) => void;
  /** Called on every keystroke so a draft survives a reload before blur. */
  onDraft?: (id: string, text: string) => void;
  as?: "span" | "p" | "div" | "h2"; className?: string;
}) {
  const ref = useRef<HTMLElement>(null);
  return createElement(as, {
    ref,
    contentEditable: editing,
    suppressContentEditableWarning: true,
    spellCheck: editing,
    "data-edit-id": id,
    "aria-label": editing ? `Edit ${id}` : undefined,
    role: editing ? "textbox" : undefined,
    onInput: () => onDraft?.(id, ref.current?.innerText ?? ""),
    onBlur: () => {
      const t = ref.current?.innerText ?? "";
      if (t !== text) onCommit(id, t);
    },
    className: `${className} ${editing ? "outline-dashed outline-1 outline-purple/50 rounded-sm bg-chip/40 focus:outline-purple" : ""}`,
  }, text);
}
