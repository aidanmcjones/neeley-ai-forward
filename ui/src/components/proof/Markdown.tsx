import type { ReactNode } from "react";

// Tiny markdown renderer for trusted, repo-authored docs (gate2_md): headings, paragraphs,
// bullet lists, pipe tables, horizontal rules, **bold**, `code`. Builds React nodes; never sets HTML.

function inline(text: string, key: string): ReactNode[] {
  const out: ReactNode[] = [];
  const re = /(\*\*[^*]+\*\*|`[^`]+`)/g;
  let last = 0, m: RegExpExecArray | null, i = 0;
  while ((m = re.exec(text))) {
    if (m.index > last) out.push(text.slice(last, m.index));
    const tok = m[0];
    if (tok.startsWith("**")) out.push(<strong key={`${key}-${i++}`}>{tok.slice(2, -2)}</strong>);
    else out.push(<code key={`${key}-${i++}`} className="font-mono text-[12px] bg-surface-2 rounded px-1">{tok.slice(1, -1)}</code>);
    last = m.index + tok.length;
  }
  if (last < text.length) out.push(text.slice(last));
  return out;
}

const cells = (row: string) => row.trim().replace(/^\|/, "").replace(/\|$/, "").split("|").map((c) => c.trim());

export function Markdown({ source }: { source: string }) {
  const lines = source.replace(/\r\n/g, "\n").split("\n");
  const blocks: ReactNode[] = [];
  let i = 0, b = 0;
  while (i < lines.length) {
    const line = lines[i];
    const k = `b${b++}`;
    if (!line.trim()) { i++; continue; }
    const h = line.match(/^(#{1,4})\s+(.*)$/);
    if (h) {
      const lvl = h[1].length;
      const cls = lvl === 1 ? "font-display text-[26px] tracking-wide text-purple-deep dark:text-purple mt-2"
        : lvl === 2 ? "text-[15px] font-bold mt-4" : "text-[13px] font-bold mt-3";
      blocks.push(<div key={k} role="heading" aria-level={lvl + 2} className={cls}>{inline(h[2], k)}</div>);
      i++; continue;
    }
    if (/^---+\s*$/.test(line)) { blocks.push(<hr key={k} className="border-line my-3" />); i++; continue; }
    if (line.trim().startsWith("|")) {
      const rows: string[] = [];
      while (i < lines.length && lines[i].trim().startsWith("|")) rows.push(lines[i++]);
      const head = cells(rows[0]);
      const body = rows.slice(1).filter((r) => !/^\s*\|?\s*:?-{2,}/.test(r)).map(cells);
      blocks.push(
        <div key={k} className="overflow-x-auto my-2 rounded-md border border-line">
          <table className="w-full border-collapse text-[12.5px]">
            <thead className="bg-surface-2"><tr>{head.map((c, j) => (
              <th key={j} scope="col" className="text-left px-2.5 py-1.5 border-b border-line text-[11px] uppercase tracking-wide text-muted font-semibold">{inline(c, `${k}h${j}`)}</th>
            ))}</tr></thead>
            <tbody>{body.map((r, ri) => (
              <tr key={ri} className="border-b border-line last:border-0">{r.map((c, j) => (
                <td key={j} className="px-2.5 py-1.5 align-top">{inline(c, `${k}r${ri}c${j}`)}</td>
              ))}</tr>
            ))}</tbody>
          </table>
        </div>,
      );
      continue;
    }
    if (/^\s*[-*]\s+/.test(line)) {
      const items: string[] = [];
      while (i < lines.length && /^\s*[-*]\s+/.test(lines[i])) items.push(lines[i++].replace(/^\s*[-*]\s+/, ""));
      blocks.push(<ul key={k} className="list-disc pl-5 space-y-1 my-1">{items.map((t, j) => <li key={j}>{inline(t, `${k}l${j}`)}</li>)}</ul>);
      continue;
    }
    const para: string[] = [];
    while (i < lines.length && lines[i].trim() && !/^(#{1,4}\s|\||---|\s*[-*]\s)/.test(lines[i])) para.push(lines[i++]);
    if (!para.length) { para.push(lines[i++]); }
    blocks.push(<p key={k} className="my-1.5 leading-relaxed">{inline(para.join(" "), k)}</p>);
  }
  return <div className="text-[13px] max-w-[95ch]">{blocks}</div>;
}
