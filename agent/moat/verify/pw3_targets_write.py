"""Wave 3: write verified/pipeline/target_profiles.csv from the Sonnet fill plus Opus checks."""
import json, shutil, numpy as np, pandas as pd
from agent.moat.common import write, OUT

V = OUT / "verified/pipeline"
if not (V / "target_profiles_wave2.csv").exists():
    shutil.copy(V / "target_profiles.csv", V / "target_profiles_wave2.csv")
w2 = pd.read_csv(V / "target_profiles_wave2.csv")
d = pd.read_csv(OUT / "tables/target_profiles_filled.csv")
assert (d.ticker == w2.ticker).all()
spot = {x["ticker"]: x for x in json.load(open(OUT / "verify/pw3_spot.json"))}
E = "https://www.sec.gov/Archives/edgar/data/"
# debt corrections read from the 10-Q balance sheet at 2026-06-30 ($)
DEBT = {
    "KPTI": (249_941_000, "convertible senior notes due 2029 98,650 + due 2028 25,937 + senior secured term loan current 40,307 + "
             "non-current 85,047 ($ thousands); the term loan is interest-bearing senior secured borrowing, a claim ahead of "
             "equity, so it is debt for EV; " + E + "1503802/000119312526347906/kpti-20260630.htm"),
    "GALT": (137_702_000, "related-party convertible notes payable 33,043 + borrowing under related-party convertible line of credit "
             "104,659 ($ thousands, incl. accrued interest, both current); " + E + "1133416/000114036126032945/ef20075252_10q.htm"),
    "PDSB": (4_322_500, "current portion of debt 4,322,500 (non-current nil); " + E + "1472091/000114036126032824/ef20075210_10q.htm"),
    "VSTM": (73_988_000, "long-term debt 73,774 + note payable 214 ($ thousands); vendor financing 7,728 not included; "
             + E + "1526119/000110465926092007/vstm-20260630x10q.htm"),
    "IMCR": (394_206_000, "interest-bearing loans and borrowings 394,206 ($ thousands, convertible notes); "
             + E + "1671927/000167192726000022/imcr-20260630.htm"),
    "CHRS": (37_247_000, "term loan, non-current 37,247 ($ thousands); " + E + "1512762/000110465926091262/chrs-20260630x10q.htm"),
}
CONFIRM = {
    "IBRX": "Opus confirmed: related-party convertible note payable at fair value 774,350 ($ thousands) on the 2026-06-30 balance sheet",
    "TIL": "Opus confirmed: loan payable 85,192 ($ thousands) on the 2026-06-30 balance sheet",
    "SKYE": "Opus confirmed: insurance premium loan payable 143,050 on the 2026-06-30 balance sheet (D&O premium financing, matures 2026-10-13)",
    "ORMP": "Opus: no borrowing on the 2026-06-30 balance sheet. The 'convertible note' 4,636 at 2025-12-31 is a current ASSET "
            "(Lifeward note receivable), not debt; the worker's 'repaid' reading was wrong but debt = 0 is right; "
            + E + "1176309/000121390026087361/ea0300383-10q_oramed.htm",
    "LPCN": "Opus read 10-Q 2026-06-30 balance sheet: total liabilities 2,067,957 are payables, accruals, deferred revenue; no borrowing; "
            + E + "1535955/000149315226035909/form10-q.htm",
    "LTRN": "Opus read 10-Q 2026-06-30 balance sheet: payables, leases and warrant liability 7,497,089 (not debt); no borrowing; "
            + E + "1763950/000149315226037971/form10-q.htm",
    "MAIA": "Opus read 10-Q 2026-06-30 balance sheet: payables, accruals, warrant liability 1,307,269 (not debt); no borrowing; "
            + E + "1878313/000149315226036764/form10-q.htm",
}
ROYALTY = {"IBRX": 415_086_000, "KPTI": 72_338_000, "ENTA": 125_073_000, "ANAB": 256_493_000, "STRO": 239_064_000, "NKTR": 57_378_000}
# foreign filers: cash and debt not in us-gaap companyfacts; EV left blank rather than shown as market cap
FOREIGN = {
    "LKFT": "20-F FY2025 (Galapagos NV, CIK 1421876), IFRS EUR; 65,897,071 ordinary shares at 2026-03-11; cash and debt not taken",
    "IPHA": "20-F FY2025 and H1 2026 6-K, IFRS EUR; ADS = 1 ordinary share (20-F Item 12D); cash and debt not taken",
    "ASND": "20-F FY2025, IFRS EUR; 61,977,408 ordinary shares at 2025-12-31; has convertible notes per 20-F risk factors; cash and debt not taken",
    "ABVX": "6-K H1 2026 IFRS EUR: cash EUR 387,992K, other current financial assets EUR 22,692K, borrowings EUR 1,212K "
            "(1,075 current + 137 non-current) at 2026-06-30; not FX-converted; " + E + "1956827/000195682726000027/abvx-20260630.htm",
    "EVAX": "20-F FY2025: 417,010,756 ordinary shares = 8,340,215 ADSs if fully converted (1 ADS = 50 shares); IFRS USD; cash and debt not taken",
    "CANF": "20-F FY2025: 2,618,425 ordinary shares; 1 ADS = 2 ordinary shares since 2026-01-05; cash from XBRL; debt not taken",
    "GRFS": "20-F FY2025 Grifols SA (subsidiary match); IFRS EUR; not priced into EV",
    "ANL": "20-F FY2025: 142,241,572 Class A + 16,990,000 Class B ordinary shares; ADS ratio not found in the 20-F text read; no EV",
}

o = d.copy()
o["debt_like_royalty_not_in_ev"] = o.ticker.map(ROYALTY)
o["prior_debt"] = o.debt
o["opus_note"] = ""
for tk, (v, src) in DEBT.items():
    m = o.ticker == tk
    o.loc[m, "debt"] = float(v); o.loc[m, "debt_source"] = "Opus read 10-Q 2026-06-30 balance sheet: " + src
    o.loc[m, "debt_check"] = "opus_corrected"
for tk, s in CONFIRM.items():
    m = o.ticker == tk
    o.loc[m, "debt_source"] = s if tk in ("ORMP", "LPCN", "LTRN", "MAIA") else s + "; " + o.loc[m, "debt_source"].astype(str)
    if tk in ("LPCN", "LTRN", "MAIA"):
        o.loc[m, "debt"] = 0.0
    o.loc[m, "debt_check"] = "opus_confirmed"
m = o.ticker == "MAIA"
o.loc[m, "cash"] = 27_595_831.0; o.loc[m, "cash_concept"] = "10-Q balance sheet text: Cash"
o.loc[m, "opus_note"] = "cash was 0 in wave 2 (wrong concept); 10-Q 2026-06-30 balance sheet shows Cash $27,595,831"
m = o.ticker == "KNSA"
o.loc[m, ["cash", "securities", "cash_date"]] = [175_677_000.0, 350_251_000.0, "2026-06-30"]
o.loc[m, "opus_note"] = "cash and short-term investments moved from 2026-03-31 to the 2026-06-30 10-Q balance sheet (175,677 and 350,251 $ thousands)"
m = o.ticker == "EVAX"
o.loc[m, "shares_outstanding"] = 8_340_215.0; o.loc[m, "shares_date"] = "2025-12-31"
o.loc[m, "opus_note"] = "price is per ADS; shares changed from 417,010,756 ordinary to 8,340,215 ADS equivalents (1 ADS = 50 shares)"
m = o.ticker == "CANF"
o.loc[m, "shares_outstanding"] = 1_309_212.5
o.loc[m, "opus_note"] = "price is per ADS; shares changed from 2,618,425 ordinary to 1,309,212.5 ADS equivalents (1 ADS = 2 shares)"
for tk, s in FOREIGN.items():
    m = o.ticker == tk
    o.loc[m, "debt_source"] = "foreign filer, debt not taken: " + s
    o.loc[m, "debt_check"] = "unchecked_foreign"
# recompute
f = lambda s: s.fillna(0)
o["market_cap"] = o.price * o.shares_outstanding
o["enterprise_value"] = o.market_cap + f(o.debt) - f(o.cash) - f(o.securities)
nocash = o.cash.isna()
o.loc[nocash, "enterprise_value"] = np.nan
burn = o.annual_operating_cash_burn
o["runway_years"] = np.where(burn > 0, (f(o.cash) + f(o.securities)) / burn, np.nan)
o.loc[o.cash.isna() & o.securities.isna(), "runway_years"] = np.nan
o["negative_ev"] = (o.enterprise_value < 0).astype(int)
# Yahoo spot check
o["price_check"] = ""
for tk, x in spot.items():
    m = o.ticker == tk
    o.loc[m, "price_check"] = f"Nasdaq historical close {x['second']} on {x['yahoo_date']} ({x['pct']:+.2f}%)"
# status
xb = o.debt_check.isna() & o.debt.notna()
o.loc[xb, "debt_check"] = "xbrl_at_bs_date"
o.loc[xb & o.debt_source.isna(), "debt_source"] = "SEC companyfacts " + o.debt_concept.astype(str) + " (wave 2 method, within 200 days of the balance sheet)"
changed = o.ticker.isin(list(DEBT) + ["MAIA", "KNSA", "EVAX", "CANF"] + list(FOREIGN))
orig = w2.verify_status
filled = w2.price.isna()
debt_ok = o.debt_check.isin(["no_debt_line", "found", "opus_corrected", "opus_confirmed", "xbrl_at_bs_date"])
st = np.where(~filled, np.where(changed, "recomputed", orig),
              np.where(debt_ok & o.enterprise_value.notna(), "filled_verified", "filled_unchecked"))
o["verify_status"] = st
o["ev_method"] = np.where(o.enterprise_value.isna(),
    "no EV: foreign filer (IFRS, cash and debt not taken) or shares missing; market cap only, see debt_source",
    "price x shares + debt - cash - current marketable securities at one balance-sheet date; debt read from the 10-Q "
    "balance sheet (current and non-current borrowings, converts, term loans); royalty-sale liabilities excluded, in "
    "debt_like_royalty_not_in_ev")
o["verify_note"] = (o.verify_note.fillna("").astype(str) + np.where(o.opus_note != "", "; Opus wave 3: " + o.opus_note, "")).str.strip("; ")
cols = [c for c in o.columns if c not in ("prior_debt", "opus_note", "checked_debt_tickers_orig_priced")]
o = o[cols]
write("verify_pipeline", "verified/pipeline/target_profiles.csv", o.to_csv(index=False), group="pipeline",
      doc_type="verified_table", source_url="SEC 10-Q/20-F balance sheets; Tiingo; Yahoo chart cross-checked with Nasdaq")
write("verify_pipeline", "verified/pipeline/target_profiles_wave2.csv", (V / "target_profiles_wave2.csv").read_text(),
      group="pipeline", doc_type="verified_table_prior")
print(o.verify_status.value_counts().to_dict(), "neg_ev", int(o.negative_ev.sum()), "ev", int(o.enterprise_value.notna().sum()))
print(o.drop_duplicates("ticker").debt_check.value_counts(dropna=False).to_dict())
w = o[o.ticker.isin(list(DEBT) + ["MAIA", "KNSA", "EVAX", "CANF"])].drop_duplicates("ticker")
print(w[["ticker", "market_cap", "debt", "cash", "enterprise_value", "verify_status"]].to_string())
print(o[o.negative_ev == 1].ticker.unique().tolist())
