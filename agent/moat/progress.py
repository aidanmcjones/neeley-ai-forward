"""Coverage matrix for the data tracker: companies x buckets, with what each bucket needs and what exists.

Reads data/corpus/manifest.csv, data/moat/manifests/*.jsonl, data/moat/verified/**, and the moat tables that are
keyed by ticker. Prints JSON (also written to data/moat/progress.json) that the tracker artifact's db is seeded from.
Run:  python -m agent.moat.progress
"""

import glob
import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from agent.drug_pack import DRUGS

ROOT = Path(__file__).resolve().parent.parent.parent
COMPANIES = ["MRK", "BMY", "PFE", "LLY", "NVO", "ABBV", "JNJ", "AZN", "AMGN", "GILD"]
QUARTERS = [f"{y}Q{q}" for y in (2024, 2025, 2026) for q in (1, 2, 3, 4)][:10]  # 2024Q1..2026Q2


def corpus():
    return pd.read_csv(ROOT / "data/corpus/manifest.csv")


def moat():
    rows = []
    for f in glob.glob(str(ROOT / "data/moat/manifests/*.jsonl")):
        for line in open(f):
            if line.strip():
                rows.append(json.loads(line))
    return pd.DataFrame(rows)


def table(name):
    p = ROOT / "data/moat/tables" / name
    return pd.read_csv(p, low_memory=False) if p.exists() else pd.DataFrame()


def verified_exists(stream):
    return (ROOT / "data/moat/verified" / stream).exists()


def main():
    c, m = corpus(), moat()
    out = {"as_of": datetime.now(timezone.utc).isoformat(), "companies": {}, "buckets": []}

    # per-ticker helpers
    def c_count(t, **f):
        d = c[c.ticker == t]
        for k, v in f.items():
            d = d[d[k].isin(v)] if isinstance(v, (list, set, tuple)) else d[d[k] == v]
        return len(d)

    def m_paths(t, stream, needle):
        d = m[(m.ticker == t) & (m.stream == stream)] if len(m) else m
        return sum(1 for p in d.path if needle in str(p)) if len(d) else 0

    prod = table("product_revenue_quarterly.csv")
    pol = table("policy_exposure.csv")
    asp = table("partb_asp_quarterly.csv")
    sdud = table("medicaid_sdud.csv")
    partd = table("partd_by_year.csv")
    nadac = table("nadac_history.csv")
    ibes = table("ibes_revenue_consensus.csv")
    topics = table("analyst_topics.csv")
    letters = table("sec_comment_letters.csv")
    tidx = table("transcripts_index.csv")
    h2h = table("head_to_head.csv")
    labels = table("label_changes.csv")
    insiders = table("insider_trades.csv")
    comp = table("exec_comp_metrics.csv")

    for t in COMPANIES:
        foreign = t in ("NVO", "AZN")
        b = {}
        # 1 annual reports: need 5 (FY2021-FY2025)
        ann = c_count(t, doc_type="annual_report") + m_paths(t, "filings", "10k_FY") + m_paths(t, "filings", "20f_FY")
        b["annual"] = dict(have=min(ann, 5), need=5)
        # 2 quarterly: need 11 10-Qs 2023Q1-2026Q2 (US) or ~14 results 6-Ks (foreign)
        if foreign:
            q = c_count(t, doc_type=["foreign_current_report", "interim_report"]) + m_paths(t, "filings", "/6k/")
            b["quarterly"] = dict(have=min(q, 14), need=14)
        else:
            q = c_count(t, doc_type="quarterly_report") + m_paths(t, "filings", "10q_")
            b["quarterly"] = dict(have=min(q, 11), need=11)
        # 3 calls: need 10 quarters 2024Q1-2026Q2
        tq = set(tidx[tidx.ticker == t].quarter) if len(tidx) else set()
        for base in ("data/corpus/companies", "data/moat/companies"):
            for p in glob.glob(str(ROOT / base / t / "transcripts" / "*_transcript.md")):
                tq.add(Path(p).name[:6])
        b["calls"] = dict(have=len(tq & set(QUARTERS)), need=10)
        # 4 product revenue panel: filings since 2023 parsed; need 11 (US) / n.a. (foreign IFRS 6-K)
        if len(prod) and not foreign:
            b["product_revenue"] = dict(have=min(prod[prod.ticker == t].accession.nunique(), 12), need=12)
        else:
            b["product_revenue"] = dict(have=0, need=0 if foreign else 12, note="annual only (20-F)" if foreign else "")
        # 5 policy / three forces: need rows for IRA, MFN, tariff, manufacturing, exposure_base
        forces = set(pol[pol.ticker == t].force) if len(pol) else set()
        b["policy"] = dict(have=len(forces & {"IRA", "MFN", "tariff", "manufacturing", "exposure_base"}), need=5)
        # 6 pricing: this company's case drugs with at least one price series (Medicaid, Part D, NADAC, Part B ASP)
        my_drugs = {k for k, v in DRUGS.items() if v[3] == t}
        priced = set()
        for df, col in ((sdud, "drug"), (partd, "drug"), (nadac, "drug")):
            if len(df) and col in df.columns:
                priced |= set(df[col].astype(str)) & my_drugs
        if len(asp) and "drugs" in asp.columns:
            priced |= {d for d in my_drugs if asp.drugs.astype(str).str.contains(d).any()}
        b["pricing"] = dict(have=len(priced), need=len(my_drugs), note=f"{len(priced)} of {len(my_drugs)} drugs")
        # 7 consensus: IBES revenue consensus present
        b["consensus"] = dict(have=int(len(ibes) and (ibes.oftic == t).any()), need=1)
        # 8 analyst attention: quarters with topic counts; need 10
        b["attention"] = dict(have=topics[topics.ticker == t].quarter.nunique() if len(topics) else 0, need=10)
        # 9 SEC fine print: comment letters, proxies (3), insider trades, exec comp
        fp = 0
        fp += int(len(letters) and (letters.ticker == t).any())
        fp += min(m_paths(t, "secx", "proxy_"), 3)
        fp += int(len(insiders) and (insiders.ticker == t).any()) if not foreign else 1
        fp += int(len(comp) and (comp.ticker == t).any())
        b["fine_print"] = dict(have=fp, need=6)
        # 10 labels / product evidence: drugs for this company with label history and h2h
        labelled = (set(labels.drug.astype(str)) if len(labels) else set()) & my_drugs
        b["product_evidence"] = dict(have=len(labelled), need=len(my_drugs), note=f"{len(labelled)} of {len(my_drugs)} drugs")
        out["companies"][t] = b

    out["buckets"] = [
        dict(key="annual", label="Annual reports FY2021 to FY2025", part=1, why="5 years of risk-factor and MD&A wording for drift"),
        dict(key="quarterly", label="Quarterly reports since 2023", part=1, why="Inventory and receivables vs revenue, by quarter"),
        dict(key="calls", label="Earnings calls, 10 quarters", part=1, why="Deflected questions, dropped metrics, exact quotes"),
        dict(key="product_revenue", label="Product revenue by quarter", part=1, why="Impact math and restatements"),
        dict(key="policy", label="Three forces exposure", part=1, why="IRA, MFN, tariff, manufacturing, US revenue share"),
        dict(key="pricing", label="Net price series", part=1, why="Gross-to-net: Part B ASP, Medicaid, NADAC, Part D"),
        dict(key="consensus", label="Street consensus (I/B/E/S)", part=1, why="Is the finding priced in"),
        dict(key="attention", label="Analyst and press attention", part=1, why="Least-discussed test for the Sharpest Needle"),
        dict(key="fine_print", label="SEC fine print", part=1, why="Comment letters, proxies, insider trades, agreements"),
        dict(key="product_evidence", label="Label history and head-to-head", part=1, why="Product comparison and promo rules"),
    ]
    (ROOT / "data/moat/progress.json").write_text(json.dumps(out, indent=1))
    print(json.dumps(out)[:4000])


if __name__ == "__main__":
    main()
