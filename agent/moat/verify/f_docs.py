"""Doc sanity checks for the filings stream + fiscal-quarter mapping for JNJ/PFE (file names use calendar labels)."""
import csv, json, re
from pathlib import Path
from agent.moat.verify.f_lib import MAN, pages

SUBS = json.load(open("data/moat/scratch/f_subs.json"))
rows, fq = [], []
seen = set()
for m in MAN:
    p = m["path"]
    if not p.endswith(".md") or p in seen:
        continue
    seen.add(p)
    issues = []
    if not Path(p).exists():
        rows.append({"path": p, "ok": False, "issue": "file missing"}); continue
    pg = pages(p)
    n = len(pg)
    folio = sum(1 for _, pr, _ in pg if pr not in ("?", ""))
    if n == 0:
        issues.append("no page markers")
    elif folio / n < 0.6:
        issues.append(f"only {folio}/{n} pages carry a printed folio")
    if m.get("pages") and m["pages"] != n:
        issues.append(f"manifest pages {m['pages']} != markers {n}")
    run, worst = 0, 0
    for _, _, body in pg:
        run = run + 1 if len(body.strip()) < 40 else 0
        worst = max(worst, run)
    if worst >= 3:
        issues.append(f"run of {worst} empty pages")
    head = open(p).read(600)
    url = re.search(r"source: (\S+)", head).group(1)
    acc_nd = re.search(r"/data/\d+/(\d{18})/", url).group(1)
    acc = f"{acc_nd[:10]}-{acc_nd[10:12]}-{acc_nd[12:]}"
    s = SUBS.get(acc)
    if not s:
        issues.append(f"accession {acc} not in EDGAR submissions")
    else:
        if s["form"] != m["form"]:
            issues.append(f"EDGAR form {s['form']} != manifest {m['form']}")
        if (s.get("period") or None) != (m.get("period") or None):
            issues.append(f"EDGAR period {s.get('period')} != manifest {m.get('period')}")
        if url.split("/")[-1] != s["primary_doc"] and m["form"] in ("10-Q", "10-K", "20-F"):
            issues.append(f"url doc {url.split('/')[-1]} is not the primary doc {s['primary_doc']}")
    if "/AZN/6k/" in p and s:
        if not re.search(r"QUARTER RESULTS|FINAL RESULTS|FULL YEAR|H1|HALF|9M|FY 20|RESULTS 20|FORM 6", s["desc"]) or re.search(r"RESULT OF AGM|SHOWS POSITIVE|OS RESULTS", s["desc"]):
            issues.append(f"not a results announcement (EDGAR description '{s['desc']}'); drop from the results set")
        if n == 1:
            issues.append("single page: source HTML has no page breaks, so printed-page citations are impossible")
    fn = Path(p).name
    mm = re.match(r"10q_(\d{4})Q(\d)\.md", fn)
    if mm and m.get("period"):
        y, q = int(m["period"][:4]), (int(m["period"][5:7]) - 1) // 3 + 1
        mo, dd = int(m["period"][5:7]), int(m["period"][8:10])
        # fiscal quarter: period ends in the first days of a month -> belongs to the previous quarter
        fy_q = q - 1 if (dd <= 7 and mo in (1, 4, 7, 10)) else q
        fy_y = y if fy_q > 0 else y - 1
        fy_q = fy_q or 4
        if (int(mm.group(1)), int(mm.group(2))) != (fy_y, fy_q):
            issues.append(f"file label {mm.group(1)}Q{mm.group(2)} but fiscal quarter is Q{fy_q} FY{fy_y} (period end {m['period']})")
        if m["ticker"] in ("JNJ", "PFE"):
            fq.append({"ticker": m["ticker"], "file": p, "file_label": f"{mm.group(1)}Q{mm.group(2)}",
                       "fiscal_quarter": f"Q{fy_q} FY{fy_y}", "period_end": m["period"], "accession": acc,
                       "label_correct": (int(mm.group(1)), int(mm.group(2))) == (fy_y, fy_q)})
    rows.append({"path": p, "ok": not issues, "issue": "; ".join(issues), "pages": n, "pages_with_folio": folio,
                 "source_url": url, "form": m["form"], "period": m.get("period"), "edgar_desc": (s or {}).get("desc", "")})
with open("data/moat/scratch/doc_checks.csv", "w") as f:
    w = csv.DictWriter(f, ["path", "ok", "issue", "pages", "pages_with_folio", "form", "period", "source_url", "edgar_desc"])
    w.writeheader(); w.writerows(rows)
with open("data/moat/scratch/jnj_fiscal_quarters.csv", "w") as f:
    w = csv.DictWriter(f, list(fq[0].keys()))
    w.writeheader(); w.writerows(sorted(fq, key=lambda r: (r["ticker"], r["period_end"])))
print(len(rows), sum(1 for r in rows if not r["ok"]))
for r in rows:
    if not r["ok"]:
        print(r["path"], "|", r["issue"])
