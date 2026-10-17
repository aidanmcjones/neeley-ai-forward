# Product fine print: what the pitch writer needs

Module `agent/needle/quant/product.py`, CLI `python -m agent.needle.quant.product_cli --ticker LLY --product zepbound`. Output: `out/<T>/product_<product>.json` and `.md`. No API is called; every number is computed from files and every quote is checked against the shared citation index.

## What the table shows

Five rows, exactly the case's: approved uses; boxed warnings and safety fine print; dosing and convenience; patent and exclusivity timeline; pricing and gross-to-net exposure. Columns are the product and each rival the case appendix lists for it (the appendix is encoded as `APPENDIX` in `product.py`, all ten companies, Lilly's set includes the Wegovy pill). A rival with no label in the drug packs (generic sitagliptin, generic dapagliflozin) is an empty column with a stated reason. Empty cells are never filled with a guess.

## How a cell is cited

- Label rows (uses, safety, dosing): a verbatim label quote located on its label section page in the index (`fda_label`, page = section), verified by `verify()`. The deep link is the DailyMed setid page. An absent boxed warning is cited to the Warnings and Precautions section, because absence has no quote; the cell says so.
- Timeline: the company-stated US LOE from the 10-K (Lilly's IP table row, Merck's patent table, AstraZeneca's "Patent Expiries of Key Marketed Products" row) is a cited page; Orange Book and Purple Book dates are table refs (file and key) with no page. The cell prints the discrepancy when the regulatory end is later than the company date, and says why (the 10-K gives the compound patent, Orange Book lists the latest patent of any kind).
- Pricing: IRA MFP, list and cut rows, and TrumpRx/MFN cash prices cite the CMS or White House page; Part D per claim, Part B ASP, NADAC and the list-vs-net trend are table refs. The cell reports "no free net series" where that is true. True net price is not public.

Cells that hold values but no page citation are listed in the markdown under "Cells with values but no verified page citation".

## How the tie to the numbers works

`tie_to_financials` builds every channel whose inputs exist, ranks the data-driven ones first and the assumption-driven ones after, and returns each as a finding in the FIND row shape (`signal_family = "product"`, sentence, citations, impact with formula and bull/base/bear, peer, confidence, `obscurity_note`). Each passes `gate()`.

| Channel | Equation | Inputs |
|---|---|---|
| ira_mfp | dRev = -claims x max(0, list30 x (1 - GTN) - MFP30); GTN 50/60/70 percent | Part D claims, CMS list and MFP per 30 days |
| ira_expected | dRev = -Medicare gross spend x cut; cut = quartiles of the CMS cuts already set | company says selection is expected (Keytruda: 2027 selection, MFP 2029) |
| loe_erosion | dRev = -annual US revenue x (1 - pct_of_peak at t=1); US curves by modality | company-stated LOE year, `loe_curves.csv` |
| label_breadth_medicare | dRev = -(rival claims - own claims) x capture x own gross per claim x (1 - GTN); capture 50/35/20 percent (assumed) | rival with more uses and shared uses has Part D claims where the product has none |
| mfn_cash_price | dRev = -revenue x share moved x (1 - cash / list); share 40/25/10 percent (assumed scenario) | White House cash price and list price quote |
| boxed_warning_share | dRev = -revenue x 10 to 25 percent, only if no rival carries a boxed warning | applied as a ceiling to a static difference |

dEPS is left to the FIND scorer: dEPS = dRev x CM x (1 - t) / D. The finding carries dRev, CM and dOI.

## Obscurity note for the FIND owner

Label facts are years old, so an O term computed on the label date is about zero and a product finding can never reach the five (reviewer finding B6). Compute O on the financial consequence: age = date the effect first becomes visible (MFP effective date, LOE year, first period the coverage gap could show), attention = the scorecard share for the consequence's topic (`topic=` flag on the finding), not the label's. The `obscurity_note` field says this on every record.

## Growth limiter and the priced-in call

`growth_limiter` picks the highest-ranked finding (data-driven before assumed, then by base |dRev|) and writes one sentence: what limits growth, its base-case dollars a year, and the call. Priced in is true when analysts asked about the consequence's topic in at least half of covered quarters AND the case starter thread already names it, or when the share is at least 0.8. Evidence returned: the scorecard share and turns, the starter-thread match, and a line saying consensus is not tested at product level (I/B/E/S revenue consensus is company-level only). If no channel has its inputs the sentence says the data do not support a call, and priced-in is false.

## Run results (2026-10-17)

- LLY Zepbound: limiter is the cash price ($346 a month against $1,086 list) at about $3.1B a year on an assumed 25 percent shift of volume; priced in (gross-to-net asked in 80 percent of quarters). The label tie: Wegovy (3 uses incl. cardiovascular and MASH) had 211,575 Medicare Part D claims in 2024 against 353 for Zepbound; about $32M base a year. Zepbound's own LOE is 2036 (10-K) against 2039 in Orange Book.
- MRK Keytruda: LOE 2028 (about $5.3B first full year) and expected IRA selection (MFP 2029, about $3.9B).
- AZN Tagrisso: LOE 2032 per the 20-F table against 2042 in Orange Book, about $2.7B on US revenue of $3.06B; beyond 24 months. Farxiga: generic entry 2026, about $1.5B on US revenue.

## Honest limits

- True net price is unavailable. The pricing row shows list-like and net-like proxies (Part D gross, Part B ASP, NADAC); the Lilly and Novo GTN anchors in the research notes (about 60 and 69 percent) are not cited to a filing and are used only as the GTN band.
- Capture, cash-share and boxed-warning elasticities are assumptions or inferences (no published share elasticity for these); findings built on them are capped at low confidence and flagged `assumed_parameters=True`.
- Label dates: the label shows what is approved now. Part D data stop at 2024, so label changes after that (Zepbound's 2025 indication changes) are not in the claims.
- Company-stated LOE text search (Ozempic, Wegovy) takes a year from a sentence; the cell says so. AstraZeneca's table quote verifies as `number_match` (the PDF conversion leaves zero-width spaces), not `exact`.
- Ex-US is out: revenue channels use US revenue where the filing splits it.
- Rival makers' own statements (`rival_product_statements.csv`) are not yet in the table.
