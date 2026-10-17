"""tables/target_profiles.csv: SEC-filing targets with market cap under about $20B."""
import gzip
import re
import time

import pandas as pd
import requests

from agent.moat.common import write, note_gap
from agent.tenk import Store, sec_get

TIINGO = open("/Users/aidanjones/.config/catalyst-lab/tiingo").read().strip()
arch = Store()
arch.bucket = "catalyst-lab-archive"
PAGE = 3500  # archive text has no native page marks: pseudo-page = 3,500-character block
a = pd.read_csv("data/moat/tables/pipeline_assets.csv")
t = a[a.flag.str.startswith("potential") & a.is_sponsor_public & a.sponsor_cik.notna()].copy()
t["sponsor_cik"] = t.sponsor_cik.astype(int)
t["rank"] = t.most_advanced_phase.map({"Phase 3": 3, "Phase 2/3": 2.5, "Phase 2": 2})
t = t.sort_values(["sponsor_cik", "rank", "n_trials"], ascending=[True, False, False])
t = t.groupby("sponsor_cik").head(3)
prices = pd.read_csv("data/moat/tables/prices_daily.csv")
cache = {}


def latest(facts, ns, concepts, unit="USD", annual=False):
    best = None
    for c in concepts:
        d = facts.get(ns, {}).get(c, {}).get("units", {}).get(unit, [])
        for x in d:
            if annual and not (x.get("fp") == "FY" and x.get("form", "").startswith(("10-K", "20-F"))):
                continue
            if best is None or (x["end"], x.get("filed", "")) > (best["end"], best.get("filed", "")):
                best = {**x, "concept": c}
        if best:
            return best
    return None


_old = pd.read_csv("data/moat/scratch/pipeline/target_profiles_run1.csv")
_old = _old[_old.price.notna()].drop_duplicates("ticker").set_index("ticker")
_blocked = False


def tiingo(tk):
    global _blocked
    if tk in _old.index:
        return float(_old.loc[tk, "price"]), str(_old.loc[tk, "price_date"])
    if _blocked:
        return None, None
    time.sleep(0.5)
    try:
        r = requests.get(f"https://api.tiingo.com/tiingo/daily/{tk}/prices", headers={
            "Authorization": f"Token {TIINGO}", "Content-Type": "application/json"}, timeout=30)
        if r.status_code == 200 and r.json():
            j = r.json()[-1]
            return j["close"], j["date"][:10]
        if r.status_code == 429:
            _blocked = True
            print("tiingo rate limited at", tk, flush=True)
    except Exception:
        pass
    return None, None


def profile(cik, tk):
    if cik in cache:
        return cache[cik]
    out = {}
    try:
        cf = sec_get(f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik:010d}.json", as_json=True)["facts"]
    except Exception as e:
        cache[cik] = {"err": f"companyfacts: {e}"[:80]}
        return cache[cik]
    cash = latest(cf, "us-gaap", ["CashAndCashEquivalentsAtCarryingValue", "CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalents"])
    sec_ = latest(cf, "us-gaap", ["MarketableSecuritiesCurrent", "AvailableForSaleSecuritiesDebtSecuritiesCurrent", "ShortTermInvestments"])
    debt = latest(cf, "us-gaap", ["LongTermDebt", "LongTermDebtNoncurrent", "DebtInstrumentCarryingAmount", "NotesPayable"])
    ocf = latest(cf, "us-gaap", ["NetCashProvidedByUsedInOperatingActivities"], annual=True)
    sh = latest(cf, "dei", ["EntityCommonStockSharesOutstanding"], unit="shares")
    out.update(cash=cash and cash["val"], cash_date=cash and cash["end"], securities=sec_ and sec_["val"],
               debt=debt and debt["val"], ocf_annual=ocf and ocf["val"], ocf_period_end=ocf and ocf["end"],
               shares_out=sh and sh["val"], shares_date=sh and sh["end"])
    # latest 10-K in the archive
    try:
        sub = sec_get(f"https://data.sec.gov/submissions/CIK{cik:010d}.json", as_json=True)["filings"]["recent"]
        for i, f in enumerate(sub["form"]):
            if f in ("10-K", "10-K/A") and sub["filingDate"][i] >= "2025-01-01":
                acc = sub["accessionNumber"][i]
                out.update(tenk_acc=acc, tenk_filed=sub["filingDate"][i], tenk_period=sub["reportDate"][i],
                           tenk_url=f"https://www.sec.gov/Archives/edgar/data/{cik}/{acc.replace('-', '')}/{sub['primaryDocument'][i]}")
                break
    except Exception as e:
        out["err"] = f"submissions: {e}"[:80]
    if out.get("tenk_acc"):
        key = f"10k/date={out['tenk_filed']}/{out['tenk_acc']}.txt.gz"
        try:
            out["text"] = gzip.decompress(arch.s3.get_object(Bucket=arch.bucket, Key=key)["Body"].read()).decode("utf-8", "ignore")
            out["r2_key"] = "catalyst-lab-archive/" + key
        except Exception as e:
            out["err"] = f"archive miss {key}"
    px, d = tiingo(tk)
    out.update(price=px, price_date=d)
    cache[cik] = out
    return out


rows = []
for r in t.itertuples():
    tk = r.sponsor_ticker
    p = profile(int(r.sponsor_cik), tk)
    mcap = p.get("price") and p.get("shares_out") and p["price"] * p["shares_out"]
    if mcap and mcap > 20e9:
        continue
    liq = (p.get("cash") or 0) + (p.get("securities") or 0)
    ev = mcap + (p.get("debt") or 0) - liq if mcap else None
    burn = -p["ocf_annual"] if p.get("ocf_annual") is not None else None
    cite = excerpt = None
    txt = p.get("text")
    if txt:
        names = [x for x in [r.asset] + str(r.aliases).split("; ") if x and len(x) >= 4 and x.lower() != "nan"]
        pages, spans = [], []
        for nm in names:
            for m in re.finditer(re.escape(nm.split(" ")[0] if len(nm.split()) > 2 else nm), txt, re.I):
                pages.append(m.start() // PAGE + 1)
                spans.append((m.start(), nm))
                if len(spans) >= 3:
                    break
            if spans:
                break
        if spans:
            blocks = sorted(set(pages))[:3]
            md = f"<!-- source: {p['tenk_url']} | archive: {p['r2_key']} | asset: {r.asset} | pseudo-page = {PAGE}-char block -->\n"
            for b in blocks:
                md += f"\n[[page {b}]]\n" + txt[(b - 1) * PAGE:b * PAGE] + "\n"
            slug = re.sub(r"[^A-Za-z0-9]+", "_", r.asset)[:40]
            rel = f"pipeline/{tk}/10k_{slug}.md"
            write("pipeline", rel, md, ticker=tk, doc_type="10-K asset excerpt", form="10-K",
                  period=p.get("tenk_period"), filed=p.get("tenk_filed"), source_url=p["tenk_url"], pages=len(blocks))
            cite = f"{tk} 10-K filed {p['tenk_filed']}, pseudo-pages {','.join(map(str, blocks))} ({p['tenk_url']})"
            excerpt = f"data/moat/{rel}"
    rows.append(dict(
        ticker=tk, sponsor=r.sponsor, sponsor_cik=int(r.sponsor_cik), asset=r.asset, aliases=r.aliases,
        phase=r.most_advanced_phase, indications=r.indications, n_trials=r.n_trials,
        nearest_primary_completion=r.nearest_primary_completion, price=p.get("price"), price_date=p.get("price_date"),
        shares_outstanding=p.get("shares_out"), shares_date=p.get("shares_date"), market_cap=mcap,
        cash=p.get("cash"), securities=p.get("securities"), debt=p.get("debt"), cash_date=p.get("cash_date"),
        annual_operating_cash_burn=burn, burn_period_end=p.get("ocf_period_end"),
        runway_years=(liq / burn if burn and burn > 0 else None), enterprise_value=ev,
        ev_method="price x dei shares outstanding + debt - cash - short-term investments",
        tenk_filed=p.get("tenk_filed"), tenk_asset_citation=cite, tenk_excerpt=excerpt,
        gap=p.get("err"), source="SEC XBRL companyfacts; Tiingo daily; " + str(p.get("tenk_url")),
        source_row=f"{int(r.sponsor_cik)}:{r.asset}"))
df = pd.DataFrame(rows)
write("pipeline", "tables/target_profiles.csv", df.to_csv(index=False), group="pipeline", doc_type="table",
      source_url="SEC companyfacts; Tiingo")
print(len(df), df.market_cap.notna().sum(), df.tenk_asset_citation.notna().sum())
for g in df[df.gap.notna()].gap.value_counts().head(5).items():
    print(g)
note_gap("pipeline", None, "target_profiles.page_citations", "archive 10-K texts carry no page marks; cited by 3,500-char pseudo-page block plus SEC URL")
