import re, html
from agent.moat.secx_lib import *


def main():
    rows = []
    for t, cik in ciks().items():
        if t in ("AZN", "NVO"):
            note_gap("secx", t, "exhibit 21", "20-F filer; subsidiaries listed in 20-F notes, not collected here")
            continue
        _, fs = filings(cik, "2025-01-01")
        ann = [f for f in fs if f["form"] == "10-K"]
        if not ann:
            note_gap("secx", t, "exhibit 21", "no 10-K found")
            continue
        f = ann[-1]
        docs = folder_docs(cik, f["accession"])
        ex = [(n, u) for n, u in docs if re.search(r"ex(?:h|hibit)?-?21(?!\d\d)", n, re.I) and n.lower().endswith((".htm", ".html", ".txt"))]
        if not ex:
            note_gap("secx", t, "exhibit 21", f"no ex21 file in {f['accession']}")
            continue
        name, url = ex[0]
        raw = sec_get(url)
        n0 = len(rows)
        for tr in re.split(r"(?i)<tr\b", raw)[1:]:
            cells = [" ".join(html.unescape(re.sub(r"<[^>]+>", " ", c)).split()) for c in re.split(r"(?i)</td>", tr.split("</tr>")[0])]
            cells = [c for c in cells if c and c not in ("$", ")")]
            if len(cells) >= 2 and not re.search(r"(?i)^(name|subsidiar|entity|jurisdiction|legal)", cells[0]):
                rows.append({"ticker": t, "entity": cells[0], "country": cells[1], "filed": f["filed"], "url": url})
            elif len(cells) == 1 and len(cells[0]) > 3:
                rows.append({"ticker": t, "entity": cells[0], "country": "", "filed": f["filed"], "url": url})
        if len(rows) == n0:  # non-table layout: one entity per line
            text = tenk.html_to_text(raw)
            for ln in text.splitlines():
                ln = ln.strip()
                if len(ln) > 3 and not re.match(r"(?i)(exhibit|subsidiaries|name of)", ln):
                    parts = re.split(r"\s{2,}|\t|\s[-–—]\s|,\s(?=[A-Z][a-z]+$)", ln)
                    rows.append({"ticker": t, "entity": parts[0], "country": parts[1] if len(parts) > 1 else "",
                                 "filed": f["filed"], "url": url})
        print(t, f["filed"], name, len(rows) - n0, flush=True)
    rows = [dict(r, entity=r["entity"].lstrip("> ").strip()) for r in rows]
    rows = [r for r in rows if not re.match(r"(?i)^(name|subsidiar|exhibit|list of|legal entity|entity)", r["entity"])
            and not re.match(r"(?i)^(jurisdiction|country|state)", r["country"] or "zz")]
    write_csv("tables/subsidiaries.csv", ["ticker", "entity", "country", "filed", "url"], rows)


main()
