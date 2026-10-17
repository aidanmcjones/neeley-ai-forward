"""Rival product statements: every sentence a maker's latest annual report and latest two calls say about a rival product.
Output: data/moat/tables/rival_product_statements.csv (written via common.write, stream peers)."""
import csv, io, re
from pathlib import Path
from agent.moat.common import write, ROOT

C = ROOT / "data" / "corpus"
M = ROOT / "data" / "moat"

# maker label -> (annual docs, call docs)
MAKERS = {
    "NVS": ([C / "peers/NVS/20f_FY2025.md"], [C / "peers/NVS/transcripts/2026Q2_transcript.md"]),
    "ROCHE": ([C / "peers/ROCHE/reports/annual_report_2025.md", C / "peers/ROCHE/reports/finance_report_2025.md"],
              [C / "peers/ROCHE/transcripts/2026H1_transcript.md"]),
    "AZN": ([C / "companies/AZN/20f_FY2025.md"], [C / "companies/AZN/transcripts/2026Q1_transcript.md", C / "companies/AZN/transcripts/2026Q2_transcript.md"]),
    "AMGN": ([C / "companies/AMGN/10k_FY2025.md"], [C / "companies/AMGN/transcripts/2026Q1_transcript.md", C / "companies/AMGN/transcripts/2026Q2_transcript.md"]),
    "MRK": ([C / "companies/MRK/10k_FY2025.md"], [C / "companies/MRK/transcripts/2026Q1_transcript.md", C / "companies/MRK/transcripts/2026Q2_transcript.md"]),
    "LLY": ([C / "companies/LLY/10k_FY2025.md"], [C / "companies/LLY/transcripts/2026Q1_transcript.md", C / "companies/LLY/transcripts/2026Q2_transcript.md"]),
    "GSK": ([C / "peers/GSK/20f_FY2025.md"], [C / "peers/GSK/transcripts/2026Q1_transcript.md", C / "peers/GSK/transcripts/2025Q3_transcript.md"]),
    "SNY": ([C / "peers/SNY/20f_FY2025.md"], [C / "peers/SNY/transcripts/2026Q1_transcript.md", C / "peers/SNY/transcripts/2026Q2_transcript.md"]),
    "TAK": ([C / "peers/TAK/20f_FY2026.md"], [C / "peers/TAK/transcripts/2026Q1_transcript.md", C / "peers/TAK/transcripts/2025Q4_transcript.md"]),
    "REGN": ([C / "peers/REGN/10k_FY2025.md"], [C / "peers/REGN/transcripts/2026Q1_transcript.md", C / "peers/REGN/transcripts/2026Q2_transcript.md"]),
    "ALNY": ([C / "peers/ALNY/10k_FY2025.md"], [C / "peers/ALNY/transcripts/2026Q1_transcript.md", C / "peers/ALNY/transcripts/2026Q2_transcript.md"]),
    "BBIO": ([C / "peers/BBIO/10k_FY2025.md"], [C / "peers/BBIO/transcripts/2026Q1_transcript.md", C / "peers/BBIO/transcripts/2026Q2_transcript.md"]),
}
# product -> (aliases, makers)
PRODUCTS = {
    "Tecentriq": (["Tecentriq", "atezolizumab"], ["ROCHE"]),
    "Imfinzi": (["Imfinzi", "durvalumab"], ["AZN"]),
    "Jardiance": (["Jardiance", "empagliflozin"], ["LLY"]),  # BI is not in corpus; Lilly co-commercializes
    "Kisqali": (["Kisqali", "ribociclib"], ["NVS"]),
    "Attruby": (["Attruby", "acoramidis"], ["BBIO"]),
    "Amvuttra": (["Amvuttra", "vutrisiran"], ["ALNY"]),
    "Cosentyx": (["Cosentyx", "secukinumab"], ["NVS"]),
    "Entyvio": (["Entyvio", "vedolizumab"], ["TAK"]),
    "Sarclisa": (["Sarclisa", "isatuximab"], ["SNY"]),
    "Praluent": (["Praluent", "alirocumab"], ["REGN", "SNY"]),
    "Leqvio": (["Leqvio", "inclisiran"], ["NVS"]),
    "Dovato": (["Dovato"], ["GSK"]),
    "Cabenuva": (["Cabenuva"], ["GSK"]),
    "Apretude": (["Apretude"], ["GSK"]),
    "Wezlana": (["Wezlana"], ["AMGN"]),
    "Amjevita": (["Amjevita"], ["AMGN"]),
    "Lipfendra": (["Lipfendra", "enlicitide"], ["MRK"]),
}
TOPICS = [("exclusivity", r"patent|exclusiv|loss of|generic|biosimilar|LOE|expir|market protection"),
          ("pricing", r"pric|rebate|IRA|negotiat|MFN|reimburs|gross-to-net|net price|Medicare|Medicaid|access"),
          ("competition", r"compet|versus|vs\.|rival|share|switch|market leader|head-to-head|Keytruda|Opdivo"),
          ("growth", r"grew|growth|increase|decrease|decline|%|up |down |launch|uptake|guidance|expect"),
          ("revenue", r"revenue|sales|million|billion|net product|USD|EUR|CHF|JPY|\$")]
PAGE = re.compile(r"^\[\[page (\d+) \| printed ([^\]]+)\]\]")
SENT = re.compile(r"(?<=[.!?])\s+(?=[A-Z\"“(])")
SPK = re.compile(r"^[A-Z][A-Za-z.'’\- ]{2,50}( [-–(] ?.{3,90}| \(.{3,60}\)|:)$")
BOILER = re.compile(r"cookie|privacy policy|sign up|log in|webull|marketbeat", re.I)


def topic(s):
    return "|".join(n for n, r in TOPICS if re.search(r, s, re.I)) or "mention"


def scan(path, aliases, is_call):
    rows, seen = [], set()
    if not path.exists():
        return rows
    pat = re.compile(r"\b(" + "|".join(map(re.escape, aliases)) + r")\b", re.I)
    page, printed, speaker = None, None, ""
    lines = path.read_text(errors="ignore").split("\n")
    i = 0
    while i < len(lines):
        ln = lines[i].strip()
        i += 1
        m = PAGE.match(ln)
        if m:
            page, printed = m.group(1), m.group(2).strip()
            continue
        if not ln:
            continue
        if is_call and len(ln) < 130 and not ln.endswith(".") and SPK.match(ln) and not pat.search(ln):
            speaker = re.sub(r"\s*[-–(].*$", "", ln).strip(": ") if ln.count(" ") < 20 else speaker
            continue
        if not pat.search(ln):
            continue
        cands = []
        if len(ln) < 90 and "." not in ln[-3:]:
            # table row: product label plus following short lines
            j, parts = i, [ln]
            while j < len(lines) and len(parts) < 9 and len(lines[j].strip()) < 60 and not PAGE.match(lines[j].strip()):
                if lines[j].strip():
                    parts.append(lines[j].strip())
                j += 1
            if len(parts) > 2 and any(re.search(r"\d", p) for p in parts[1:]):
                cands.append(" | ".join(parts))
        else:
            for s in SENT.split(ln):
                if pat.search(s):
                    cands.append(s.strip())
        for s in cands:
            if len(s) < 25 or BOILER.search(s):
                continue
            s = s[:1000]
            key = re.sub(r"\W+", "", s.lower())[:120]
            if key in seen:
                continue
            seen.add(key)
            rows.append((page, printed, speaker, s))
    return rows


def main():
    out = [["product", "maker", "doc_type", "doc", "period", "page", "printed_page", "speaker", "topic", "quote",
            "source_quality", "path"]]
    cov = {}
    for prod, (aliases, makers) in PRODUCTS.items():
        for mk in makers:
            annual, calls = MAKERS[mk]
            for kind, docs in (("annual_report", annual), ("earnings_call", calls)):
                for p in docs:
                    rows = scan(p, aliases, kind == "earnings_call")
                    q = "unknown"
                    if p.exists():
                        head = p.read_text(errors="ignore")[:600]
                        mq = re.search(r"quality: (\w+)", head)
                        q = {"official": "A", "third_party": "C"}.get(mq.group(1), "A") if mq else "A"
                    per = re.search(r"(FY\d{4}|\d{4}Q\d|\d{4}H\d)", p.name)
                    for page, printed, spk, s in rows:
                        out.append([prod, mk, kind, p.stem, per.group(1) if per else "", page or "", printed or "",
                                    spk if kind == "earnings_call" else "", topic(s), s, q, str(p.relative_to(ROOT))])
                    cov.setdefault(prod, {}).setdefault(f"{mk}:{kind}:{p.stem}", len(rows))
    buf = io.StringIO()
    csv.writer(buf).writerows(out)
    write("peers", "tables/rival_product_statements.csv", buf.getvalue(), group="tables", doc_type="table",
          source_url="data/corpus (local peers and companies docs)")
    print(len(out) - 1, "rows")
    for p, d in cov.items():
        print(p, d)


main()
