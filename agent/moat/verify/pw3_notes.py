"""Wave 3: append AI errors and the NOTES.md wave 3 section."""
import json
import pandas as pd
from agent.moat.common import write, OUT

E = "https://www.sec.gov/Archives/edgar/data/"
AIW = [
    ("target_profiles_filled.csv (Sonnet debt check)", "CHRS, GALT, VSTM, IMCR, PDSB: no convertible/notes/loan line on the latest 10-Q balance sheet; debt = 0",
     "Balance sheets at 2026-06-30 show CHRS term loan non-current $37.2M; GALT related-party convertible notes $33.0M + convertible line of credit $104.7M; VSTM long-term debt $73.8M + note $0.2M; IMCR interest-bearing loans and borrowings $394.2M; PDSB current portion of debt $4.3M",
     "re-scanned all 67 no_debt_line balance sheets across current and non-current liabilities", 5, E + "1512762/000110465926091262/chrs-20260630x10q.htm"),
    ("target_profiles_filled.csv (Sonnet debt check)", "KPTI debt $124.6M: convertible senior notes only, senior secured term loan not included",
     "Term loan is $40.3M current + $85.0M non-current; interest-bearing senior secured borrowing is debt for EV, so debt = $249.9M",
     "read the 10-Q balance sheet", 1, E + "1503802/000119312526347906/kpti-20260630.htm"),
    ("target_profiles_filled.csv (Sonnet debt check)", "ORMP convertible note $4.6M at 2025-12-31 was repaid (debt)",
     "The convertible note is a current ASSET (Lifeward senior secured convertible note receivable); ORMP has no borrowings. Debt = 0 stands",
     "read the 10-Q balance sheet", 1, E + "1176309/000121390026087361/ea0300383-10q_oramed.htm"),
    ("verified/pipeline/target_profiles.csv (wave 2)", "MAIA cash $0 at 2026-06-30",
     "10-Q balance sheet: Cash $27,595,831 at 2026-06-30", "read the 10-Q balance sheet while checking debt", 1, E + "1878313/000149315226036764/form10-q.htm"),
    ("target_profiles_filled.csv", "EVAX market cap $1.18B (417,010,756 shares x ADS price); CANF 2,618,425 shares x ADS price",
     "EVAX 20-F: 417,010,756 ordinary shares = 8,340,215 ADSs (1:50), market cap $23.6M; CANF 1 ADS = 2 ordinary shares since 2026-01-05, market cap $2.3M",
     "read the 20-F share and ADS ratio text", 2, E + "1828253/000117184326001346/evax20251231_20f.htm"),
    ("verified/pipeline/target_profiles.csv (wave 2)", "KNSA cash and short-term investments at 2026-03-31",
     "10-Q for 2026-06-30 (filed 2026-07-28) shows cash $175.7M and short-term investments $350.3M", "read the 10-Q balance sheet", 1,
     E + "1730430/000110465926087545/knsa-20260630x10q.htm"),
    ("fda_calendar.csv (collector)", "11 denosumab biosimilars are biosimilars of XGEVA; Retacrit (7 rows) is a biosimilar of ARANESP",
     "Purple Book Sept 2026: those denosumab names reference Prolia; Retacrit references Procrit/Epogen (epoetin alfa), Aranesp is darbepoetin",
     "Purple Book 351(k) reference-product match (Sonnet recheck, Opus applied)", 18,
     "https://www.accessdata.fda.gov/drugsatfda_docs/PurpleBook/2026/purplebook-search-September-data-download.csv"),
    ("pipeline_assets.csv (collector)", "comparator and backbone drugs listed as sponsor pipeline assets (e.g. Janssen Tocilizumab, Regeneron Apixiban, Immatics Dacarbazine)",
     "Orange Book / Purple Book holders are other companies or multi-source generics; 32 more rows dropped, 117 flagged marketed_comparator",
     "asset name vs Orange Book products and Purple Book holder, sponsor family match", 32, "data/moat/verify/pp_cache/orange_book.zip"),
]
with (OUT / "verify/ai_wrong.jsonl").open("a") as f:
    for t, said, src, how, n, ex in AIW:
        f.write(json.dumps({"stream": "pipeline", "table": t, "what_the_ai_said": said, "what_the_source_says": src,
                            "how_caught": how, "count": n, "example_source": ex}) + "\n")

tp = pd.read_csv(OUT / "verified/pipeline/target_profiles.csv")
fc = pd.read_csv(OUT / "verified/pipeline/fda_calendar.csv")
pa = pd.read_csv(OUT / "verified/pipeline/pipeline_assets.csv")
pdp = pd.read_csv(OUT / "verified/pipeline/pipeline_assets_dropped.csv")
neg = sorted(tp[tp.negative_ev == 1].ticker.unique())
W3 = f"""

## Wave 3 (2026-10-17): fills promoted, Opus checks

Scripts: `agent/moat/verify/pw3_*.py` (spot, docs, docs_batch, unchecked, bs, debtscan, targets_write, fda_write,
assets_write, notes). Prior verified files kept as `*_wave2.csv`. Filing text cached in `data/moat/verify/pp_cache/w3/`.

### target_profiles.csv ({len(tp)} rows)

verify_status: {tp.verify_status.value_counts().to_dict()}. EV present on {int(tp.enterprise_value.notna().sum())} rows;
`negative_ev`=1 on {int(tp.negative_ev.sum())} rows ({len(neg)} tickers: {', '.join(neg)}).

Price fills (all dated 2026-10-16 close): 79 rows Tiingo, 41 rows (24 tickers) Yahoo chart API (Stooq served an anti-bot page).
Yahoo spot check: Tiingo was still 429, so all 24 Yahoo tickers were checked against the Nasdaq historical API close
for 2026-10-16: 24 of 24 within 3% (largest gap 0.03%, TPST). Detail in `data/moat/verify/pw3_spot.json` and the
`price_check` column. KPTI $0.3901 also confirmed on Nasdaq.

Arithmetic: market cap = price x shares and EV = market cap + debt - cash - securities recomputed for all 199 from the
row's own fields; the Sonnet file matched on 197 of 197 (2 had no shares). Runway recomputed after the fixes below.

Cover-page shares (4 multi-class): TEM 180,434,756 (175,390,967 A + 5,043,789 B), KNSA 78,024,013 (A 48,289,273 +
B 895,158 + A1 12,781,964 + B1 16,057,618), ALMS 129,435,239 (non-voting 0), PROK 302,322,655 (208,926,941 A +
93,395,714 B): all 4 match the 10-Q XBRL cover (R1.htm).

Debt (balance sheet at 2026-06-30, column `debt_check`):
- The 5 Sonnet finds: IBRX $774.35M related-party convertible note (fair value) confirmed; TIL $85.19M loan payable
  confirmed; SKYE $0.14M D&O premium loan confirmed; KPTI corrected from $124.6M to $249.9M: the senior secured term
  loan ($40.3M current + $85.0M non-current) is interest-bearing borrowing senior to equity, so it is debt for EV;
  ORMP debt 0 confirmed, but the "convertible note" was an asset (Lifeward note receivable), not repaid debt.
- Re-scan of the 67 "no_debt_line" calls across current AND non-current liabilities found 5 misses, now corrected:
  CHRS $37.25M term loan, GALT $137.70M related-party converts and convertible credit line, VSTM $73.99M, IMCR $394.21M
  convertible notes, PDSB $4.32M. 62 zero-debt calls stand.
- Royalty-sale liabilities are not counted as debt; they are in `debt_like_royalty_not_in_ev`: IBRX $415.1M revenue
  interest liability, ANAB $256.5M, STRO $239.1M, ENTA $125.1M, KPTI $72.3M, NKTR $57.4M. Add them for a stricter EV.
- 37 rows keep the wave 2 XBRL debt fact at the balance-sheet date (`xbrl_at_bs_date`).
- The 11 unchecked: LPCN, LTRN, MAIA read (no borrowings; warrant liabilities are not debt). MAIA cash was 0 in wave 2:
  corrected to $27.6M from the balance sheet. 8 foreign filers (LKFT = Galapagos NV, GRFS, CANF, IPHA, ASND, EVAX, ANL,
  ABVX) report IFRS in EUR or USD with no us-gaap cash facts: EV is now BLANK for them instead of equal to market cap
  (ABVX H1 2026 cash EUR 388.0M and borrowings EUR 1.2M are in `debt_source`, not FX-converted).
- Share basis: EVAX shares changed to 8,340,215 ADS equivalents (1 ADS = 50 shares; market cap $1.18B -> $23.6M);
  CANF to 1,309,212.5 ADS equivalents (1 ADS = 2 shares). KNSA cash and investments moved to the 2026-06-30 10-Q.
- Caveats: LIANY shares are dated 2023-11-09; 8 foreign rows remain `filled_unchecked`.

### fda_calendar.csv ({len(fc)} rows)

verify_status: {fc.verify_status.value_counts().to_dict()}.
- openFDA: 60 of 60 Drugs@FDA actions match (application, date, action type); result in `openfda_check`.
- Purple Book Sept 2026: 135 of 153 biosimilar rows pass; 18 corrected (`verify_status=corrected`): 11 denosumab
  biosimilars now reference PROLIA (were XGEVA), 7 Retacrit rows reference PROCRIT (were ARANESP; Aranesp is
  darbepoetin). New columns `licensure_date` (Purple Book approval date, {int(fc.licensure_date.notna().sum())} rows) and
  `reference_product_purple_book`.
- PDUFA: the 23 "not found" quotes are now `verbatim_fragments` with the verbatim runs (at least 6 words) listed in
  `quote_fragments` and coverage in `verify_note`. 19 are stitched on the cited page (often across a page marker); 4 were
  re-pointed after confirming the fragments: PFE 10-K p8 -> data/corpus/companies/PFE/10q_2026Q2.md p49, and 3 SNY rows
  -> data/moat/companies/SNY/6k/2025-10-24_0001121404-25-000026.md p5, p5, p7. Quote fragments, not the stitched quote,
  are what to cite.

### pipeline_assets.csv ({len(pa)} rows; {len(pdp)} in pipeline_assets_dropped.csv)

- 80 sampled assets: owner, phase, CT.gov phase and lead sponsor 80 of 80 pass (verify_status=pass on the matching rows).
- Merges (2): Merck "MMC" into "Mitomycin C (MMC)" (RxNav: both mitomycin); Novartis "KJX839" into "ALN-PCSSC; KJX839".
  The merged Merck mitomycin row was then dropped as a comparator.
- Comparators: asset names checked against Orange Book products (ingredient, trade name, applicant) and Purple Book
  (proper and proprietary name, applicant), with a sponsor-family match (Roche = Genentech, Janssen = J&J, and so on).
  32 obvious ones dropped (named in the recheck, or a multi-source generic with 3+ holders matched on the asset name,
  e.g. dacarbazine, temozolomide, gefitinib, epirubicin, prednisone, tocilizumab at Janssen, apixaban at Regeneron).
  {int((pa.marketed_comparator == 1).sum())} kept rows carry `marketed_comparator=1` (marketed by another holder: comparator, backbone or licensed asset; check
  before use; family matching misses some acquisitions, e.g. Pfizer encorafenib via Array). 152 rows are the sponsor's own
  marketed drug (noted in asset_flag). Alias-only matches never drop (they catch co-administered drugs).

AI errors added to `data/moat/verify/ai_wrong.jsonl`: {len(AIW)} entries.
"""
notes = (OUT / "verified/pipeline/NOTES.md").read_text()
if "## Wave 3" not in notes:
    notes += W3
write("verify_pipeline", "verified/pipeline/NOTES.md", notes, group="pipeline", doc_type="notes")
print("ok", len(W3))
