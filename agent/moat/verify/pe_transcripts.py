"""Peers item 4: confirm each peer transcript's quarter label against the call date and the quarter named inside it.

Calendar-year companies: a call in Apr-May reports Q1, Jul-Aug Q2, Oct-Nov Q3, Jan-Mar the prior year's Q4.
Takeda (fiscal year ends Mar 31): the call in late Jul reports FY Q1 (Apr-Jun), Oct-Nov Q2, Jan-Feb Q3,
May the full fiscal year (Q4). Its labels must be FY-based: FY2024 Q1 = Apr-Jun 2024.
"""
import io
import re
from datetime import date
from pathlib import Path

import pandas as pd

from agent.moat.common import write
from agent.moat.verify.pe_lib import ROOT

PEERS = ["NVS", "GSK", "SNY", "TAK", "REGN", "ALNY", "BBIO", "ROCHE"]
MONTHS = {m: i for i, m in enumerate(["january", "february", "march", "april", "may", "june", "july", "august",
                                       "september", "october", "november", "december"], 1)}
DATE_RE = re.compile(r"\b(January|February|March|April|May|June|July|August|September|October|November|December)"
                     r"\s+(\d{1,2}),?\s+(20\d\d)\b")
ISO_RE = re.compile(r"(20\d\d)[-/](\d{1,2})[-/](\d{1,2})")
QREF = re.compile(r"\b(?:Q([1-4])\s*(?:FY\s?)?(20\d\d)|(first|second|third|fourth)[- ]quarter(?: of)?\s*(?:fiscal\s*)?(?:year\s*)?(20\d\d)|"
                  r"(20\d\d)\s*Q([1-4])|FY\s?(20\d\d)\s*Q([1-4]))", re.I)
ORD = {"first": 1, "second": 2, "third": 3, "fourth": 4}


def expected(ticker, d):
    m = d.month
    if ticker == "TAK":
        if m in (7, 8):
            return f"{d.year}Q1"
        if m in (10, 11, 12):
            return f"{d.year}Q2"
        if m in (1, 2, 3):
            return f"{d.year - 1}Q3"
        return f"{d.year - 1}Q4"  # Apr-Jun: full-year results for FY(year-1)
    if m in (4, 5, 6):
        return f"{d.year}Q1"
    if m in (7, 8, 9):
        return f"{d.year}Q2"
    if m in (10, 11, 12):
        return f"{d.year}Q3"
    return f"{d.year - 1}Q4"


def call_date(head, body):
    m = ISO_RE.search(head.split("retrieved")[0])
    if m:
        try:
            return date(int(m.group(1)), int(m.group(2)), int(m.group(3))), "url"
        except ValueError:
            pass
    cands = []
    for m in DATE_RE.finditer(body[:60000]):
        try:
            cands.append(date(int(m.group(3)), MONTHS[m.group(1).lower()], int(m.group(2))))
        except ValueError:
            pass
    if cands:
        from collections import Counter
        return Counter(cands).most_common(1)[0][0], "text_most_common_date"
    return None, "none"


def quarter_named(body):
    from collections import Counter
    c = Counter()
    for m in QREF.finditer(body[:80000]):
        g = m.groups()
        if g[0]:
            c[f"{g[1]}Q{g[0]}"] += 1
        elif g[2]:
            c[f"{g[3]}Q{ORD[g[2].lower()]}"] += 1
        elif g[4]:
            c[f"{g[4]}Q{g[5]}"] += 1
        elif g[6]:
            c[f"{g[6]}Q{g[7]}"] += 1
    return c.most_common(3)


def main():
    rows = []
    for t in PEERS:
        dd = ROOT / "data/moat/companies" / t / "transcripts"
        for f in sorted(dd.glob("*.md")) if dd.exists() else []:
            txt = f.read_text(errors="replace")
            head = txt[:600]
            src = re.search(r"source: (\S+)", head)
            label = f.name.split("_")[0]
            d, how = call_date(head, txt)
            exp = expected(t, d) if d else None
            qn = quarter_named(txt)
            rows.append(dict(ticker=t, file=str(f.relative_to(ROOT)), label=label, call_date=d, date_from=how,
                             expected_label=exp, label_ok=(exp == label), quarters_named_in_text="; ".join(f"{k}x{v}" for k, v in qn),
                             top_named=qn[0][0] if qn else None, source_url=src.group(1) if src else None,
                             convention="fiscal (FY ends Mar 31)" if t == "TAK" else "calendar"))
    v = pd.DataFrame(rows)
    print(v[["ticker", "label", "call_date", "date_from", "expected_label", "label_ok", "quarters_named_in_text"]].to_string())
    v.to_pickle("/tmp/pe_transcripts.pkl")
    buf = io.StringIO()
    v.to_csv(buf, index=False)
    write("verify_peers", "verified/peers/transcript_labels.csv", buf.getvalue(), group="tables", doc_type="table",
          quality="verified", source_url="data/moat/companies/<T>/transcripts")


if __name__ == "__main__":
    main()
