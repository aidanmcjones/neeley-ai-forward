"""Coverage matrix for the data tracker: companies x buckets, with what each bucket needs and what exists.

Reads data/corpus/manifest.csv, data/moat/manifests/*.jsonl, data/moat/verified/**, and the moat tables that are
keyed by ticker. Prints JSON (also written to data/moat/progress.json) that the tracker artifact's db is seeded from.
Run:  python -m agent.moat.progress
"""

import glob
import json
import re
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


VERIFIED_NAME = {"exec_comp_metrics.csv": "incentive_metrics.csv"}


def table(name):
    """A moat table: the Opus-verified copy under data/moat/verified/<stream>/ when one exists, else the raw
    collector table. The verified copies are complete where the raw ones were partial (analyst_topics has 10
    quarters per company, incentive_metrics has all 8 US filers)."""
    vname = VERIFIED_NAME.get(name, name)
    hits = sorted((ROOT / "data/moat/verified").glob(f"*/{vname}"))
    if hits:
        return pd.read_csv(hits[0], low_memory=False)
    p = ROOT / "data/moat/tables" / name
    return pd.read_csv(p, low_memory=False) if p.exists() else pd.DataFrame()


def verified_exists(stream):
    return (ROOT / "data/moat/verified" / stream).exists()


def onboarded_tickers():
    """Tickers with a data/moat/manifests/onboard_<TICKER>.jsonl (agent.moat.onboard_company)."""
    return sorted(p.stem[len("onboard_"):] for p in (ROOT / "data/moat/manifests").glob("onboard_*.jsonl")
                  if not p.stem.startswith("onboard_drug_"))


def onboarded_drugs():
    return sorted(p.stem[len("onboard_drug_"):] for p in (ROOT / "data/moat/manifests").glob("onboard_drug_*.jsonl"))


def _onboard_table(key, name):
    p = ROOT / "data/moat/onboard" / key / f"{name}.csv"
    return pd.read_csv(p, low_memory=False, dtype=str) if p.exists() else pd.DataFrame()


def onboard_buckets(t):
    """The same ten buckets as main(), computed for an onboarded ticker from its onboard manifest, its
    data/moat/onboard/<T>/ tables and any corpus rows for that ticker (data/corpus peers)."""
    from agent.moat.index import corpus_rows
    rows = []
    p = ROOT / "data/moat/manifests" / f"onboard_{t}.jsonl"
    if p.exists():
        rows = [json.loads(l) for l in p.read_text().splitlines() if l.strip()]
    # everything else already collected for this ticker: data/corpus (peers) and other moat streams (e.g. peers)
    from agent.moat.index import moat_rows
    corp = [r for r in corpus_rows().values() if str(r.get("ticker") or "").upper() == t]
    corp += [r for r in moat_rows().values() if str(r.get("ticker") or "").upper() == t
             and not str(r.get("stream", "")).startswith("onboard_")]
    prof = {}
    pp = ROOT / "data/moat/onboard" / t / "profile.json"
    if pp.exists():
        prof = json.loads(pp.read_text())
    foreign = bool(prof.get("foreign_private_issuer"))
    docs = {r["path"]: r for r in rows if r.get("doc_type") not in ("table", "profile")}
    b = {}
    fy = {Path(r["path"]).stem.split("_")[1][:6] for r in docs.values() if r.get("doc_type") == "annual_report"}
    fy |= {Path(str(r.get("path"))).stem.split("_")[1][:6] for r in corp if r.get("doc_type") == "annual_report"
           and "_FY" in str(r.get("path"))}
    b["annual"] = dict(have=min(len(fy), 5), need=5)
    if foreign:
        q = sum(1 for r in docs.values() if r.get("doc_type") == "foreign_current_report" and "/6k/" in r["path"])
        q += sum(1 for r in corp if r.get("doc_type") in ("foreign_current_report", "interim_report"))
        b["quarterly"] = dict(have=min(q, 14), need=14)
    else:
        q = {Path(r["path"]).stem for r in docs.values() if r.get("doc_type") == "quarterly_report"}
        q |= {Path(str(r.get("path"))).stem for r in corp if r.get("doc_type") == "quarterly_report"}
        b["quarterly"] = dict(have=min(len(q), 11), need=11)
    tq = set()
    for base in ("data/corpus/companies", "data/corpus/peers", "data/moat/companies"):
        for f in glob.glob(str(ROOT / base / t / "transcripts" / "*_transcript.md")):
            tq.add(Path(f).name[:6])
    b["calls"] = dict(have=len(tq & set(QUARTERS)), need=10)
    prod = _onboard_table(t, "product_revenue_quarterly")
    if foreign:
        b["product_revenue"] = dict(have=prod.accession.nunique() if len(prod) else 0, need=0,
                                    note="annual only (20-F)")
    else:
        b["product_revenue"] = dict(have=min(prod.accession.nunique(), 12) if len(prod) else 0, need=12)
    forces = set(_onboard_table(t, "policy_mentions").get("force", pd.Series(dtype=str)).dropna())
    if len(_onboard_table(t, "ira_selected")):
        forces.add("IRA")
    if len(_onboard_table(t, "manufacturing_sites")):
        forces.add("manufacturing")
    if len(prod) and "geography" in prod.columns and prod.geography.fillna("").str.len().gt(0).any():
        forces.add("exposure_base")
    b["policy"] = dict(have=len(forces & {"IRA", "MFN", "tariff", "manufacturing", "exposure_base"}), need=5)
    prods = _onboard_table(t, "products")
    top = []
    if len(prods):
        prods["sp"] = pd.to_numeric(prods.partd_spend_2024, errors="coerce").fillna(0) + \
            pd.to_numeric(prods.partb_spend_2024, errors="coerce").fillna(0)
        fam = set()
        for x in prods[prods.sp > 0].sort_values("sp", ascending=False).brand:
            if str(x).split()[0] not in fam and len(top) < 6:  # same brand families as onboard_company.products
                fam.add(str(x).split()[0])
                top.append(x)
    priced = set()
    for name in ("partd_spending", "partb_spending", "nadac_history"):
        d = _onboard_table(t, name)
        if len(d) and "drug" in d.columns:
            priced |= set(d.drug.astype(str))
    have_p = sum(1 for x in top if re.sub(r"[^a-z0-9]+", "-", str(x).lower()).strip("-") in priced)
    b["pricing"] = dict(have=have_p, need=len(top), note=f"{have_p} of {len(top)} top products")
    ib = list((ROOT / "data/moat/onboard" / t).glob("ibes_*.csv"))
    b["consensus"] = dict(have=int(bool(ib)), need=1, note="" if ib else "needs --ibes (WRDS Duo)")
    top_q = _onboard_table(t, "analyst_topics")
    b["attention"] = dict(have=min(top_q.quarter.nunique(), 10) if len(top_q) else 0, need=10)
    fp = int(len(_onboard_table(t, "sec_comment_letters")) > 0)
    fp += min(sum(1 for r in docs.values() if r.get("doc_type") == "proxy_statement")
              + sum(1 for r in corp if r.get("doc_type") == "proxy_statement"), 3)
    fp += int(len(_onboard_table(t, "insider_trades")) > 0) if not foreign else 1
    fp += int(len(_onboard_table(t, "exec_comp_metrics")) > 0) if not foreign else 1
    b["fine_print"] = dict(have=fp, need=6)
    lab = 0
    for x in top:
        s = re.sub(r"[^a-z0-9]+", "-", str(x).lower()).strip("-")
        if any((ROOT / base / s / "label_sections.md").exists() for base in ("data/moat/drugs", "data/corpus/drugs")):
            lab += 1
    b["product_evidence"] = dict(have=lab, need=len(top), note=f"{lab} of {len(top)} top products have a label pack")
    b["_onboarded"] = dict(have=len(docs), need=0, note=f"{len(docs)} onboard docs, {len(corp)} corpus docs")
    return b


def onboard_drug_buckets(slug):
    """Have/need per drug-pack item for a drug onboarded with agent.moat.onboard_drug."""
    key = f"drug_{slug}"
    b = {}
    b["label"] = dict(have=int((ROOT / "data/moat/drugs" / slug / "label_sections.md").exists()), need=1)
    for name, label in [("label_versions", "label_history"), ("orange_book_products", "orange_book"),
                        ("purple_book", "purple_book"), ("paragraph_iv", "paragraph_iv"), ("ira_negotiation", "ira"),
                        ("partd_spending", "partd"), ("partb_spending", "partb"), ("nadac_history", "nadac"),
                        ("medicaid_sdud", "sdud"), ("head_to_head", "head_to_head"), ("open_payments", "open_payments")]:
        b[label] = dict(have=int(len(_onboard_table(key, name)) > 0), need=1)
    return b


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
    # foreign filers' pay metrics come from the remuneration report (NVO 6-K, AZN 20-F exhibit 15.1), not a proxy
    comp_f = table("incentive_metrics_foreign.csv")
    if len(comp_f):
        comp = pd.concat([comp, comp_f], ignore_index=True) if len(comp) else comp_f

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
        missing_p = sorted(my_drugs - priced)
        b["pricing"] = dict(have=len(priced), need=len(my_drugs),
                            note=f"{len(priced)} of {len(my_drugs)} drugs" + (f"; no public price series yet for {', '.join(missing_p)} (2026 launch)" if missing_p else ""))
        # 7 consensus: IBES revenue consensus present
        b["consensus"] = dict(have=int(len(ibes) and (ibes.oftic == t).any()), need=1)
        # 8 analyst attention: quarters with topic counts; need 10
        b["attention"] = dict(have=topics[topics.ticker == t].quarter.nunique() if len(topics) else 0, need=10)
        # 9 SEC fine print: comment letters, proxies (3), insider trades, exec comp
        fp = 0
        fp += int(len(letters) and (letters.ticker == t).any())
        # US filers: 3 DEF 14A proxies. Foreign filers have no proxy; the remuneration report is Item 6B of the
        # 20-F, which is indexed, so the three 20-Fs stand in for the three proxies.
        fp += min(m_paths(t, "secx", "proxy_"), 3) if not foreign else min(ann, 3)
        fp += int(len(insiders) and (insiders.ticker == t).any()) if not foreign else 1  # no Form 4 for foreign
        has_comp = bool(len(comp) and (comp.ticker == t).any())
        fp += int(has_comp)
        note = "" if fp == 6 else ("pay metrics not extracted from the remuneration report" if foreign and not has_comp else "")
        b["fine_print"] = dict(have=fp, need=6, note=note)
        # 10 labels / product evidence: drugs for this company with label history and h2h
        labelled = (set(labels.drug.astype(str)) if len(labels) else set()) & my_drugs
        missing_l = sorted(my_drugs - labelled)
        b["product_evidence"] = dict(have=len(labelled), need=len(my_drugs),
                                     note=f"{len(labelled)} of {len(my_drugs)} drugs" + (f"; no label pack yet for {', '.join(missing_l)} (2026 launch)" if missing_l else ""))
        out["companies"][t] = b

    # tickers and drugs onboarded with agent.moat.onboard_company / onboard_drug (found by scanning manifests)
    for t in onboarded_tickers():
        if t not in out["companies"]:
            out["companies"][t] = onboard_buckets(t)
    out["onboarded"] = onboarded_tickers()
    out["onboarded_drugs"] = {d: onboard_drug_buckets(d) for d in onboarded_drugs()}

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
