"""Top-product rows from 20-F product tables (page-marked text) -> tables/peer_product_revenue.csv (stream peers).
Heuristic: on flattened tables, a row = a short name line followed by numeric-only lines until the next name line."""
import csv, io, re, sys
from pathlib import Path
from agent.moat.common import write, ROOT

ANCHOR = {"NVS": "Entresto"}  # GSK, SNY, TAK flattened tables did not parse to product level; see gaps
PAGE = re.compile(r"^\[\[page (\d+) \| printed ([^\]]+)\]\]")
NUM = re.compile(r"^\(?[-–]?\d[\d  ,.]*\)?%?$|^[-–]$|^n/?m$|^\d+\s*$", re.I)
NAME = re.compile(r"^[A-Z][A-Za-z0-9®™()'’/+\- .&,]{2,45}$")


def pages(path):
    cur, buf, out = None, [], []
    for ln in path.read_text(errors="ignore").split("\n"):
        m = PAGE.match(ln)
        if m:
            if cur:
                out.append((cur, buf))
            cur, buf = (m.group(1), m.group(2).strip()), []
        else:
            buf.append(ln.strip())
    if cur:
        out.append((cur, buf))
    return out


def rows_of(lines):
    rows, name, nums = [], None, []
    for ln in lines:
        if not ln:
            continue
        if NUM.match(ln.replace(" ", " ")):
            nums.append(ln)
        elif NAME.match(ln) and len(ln.split()) <= 6 and not ln.endswith("."):
            if name and len(nums) >= 3:
                rows.append((name, nums))
            name, nums = ln, []
        else:
            # description / indication text lines inside a row: ignore, keep row open
            if len(ln) > 45 and name:
                continue
    if name and len(nums) >= 3:
        rows.append((name, nums))
    return rows


def best(path, anchor):
    cands = []
    for (pg, pr), lines in pages(path):
        chunks = [(pg, pr, lines, 0)]
        if len(lines) > 400:
            chunks = [(pg, pr, lines[i:i + 300], i) for i in range(0, len(lines), 150)]
        for pg2, pr2, ls, off in chunks:
            if anchor not in " ".join(ls):
                continue
            rows = [r for r in rows_of(ls) if not r[0].lower().startswith("total")]
            where = pg2 if off == 0 else f"{pg2} (no page breaks in source; line offset {off})"
            cands.append((len(rows), where, pr2, rows))
    cands.sort(key=lambda x: -x[0])
    return cands[:1]


def main():
    out = [["ticker", "fiscal_year", "doc", "rank_in_table", "product", "values_raw", "first_value", "page", "printed_page",
            "source_path", "parse_note"]]
    for t, anchor in ANCHOR.items():
        for p in sorted((ROOT / "data").glob(f"*/companies/{t}/20f_FY*.md")) + sorted(
                (ROOT / "data/corpus/peers" / t).glob("20f_FY*.md")):
            fy = re.search(r"FY(\d{4})", p.name).group(1)
            for n, pg, pr, rows in best(p, anchor):
                if n < 8:
                    continue
                for i, (name, nums) in enumerate(rows[:20], 1):
                    out.append([t, fy, p.stem, i, name, " ; ".join(nums[:12]), nums[0].strip(), pg, pr,
                                str(p.relative_to(ROOT)), f"table page rows={n}; values in column order of the filing"])
                print(t, fy, "page", pg, "printed", pr, "rows", n)
    buf = io.StringIO()
    csv.writer(buf).writerows(out)
    write("peers", "tables/peer_product_revenue.csv", buf.getvalue(), group="tables", doc_type="table",
          source_url="20-F product tables in data/moat and data/corpus")
    print(len(out) - 1, "rows")


main()
