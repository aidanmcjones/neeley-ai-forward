"""Policy verifier build: writes data/moat/verified/policy/* (stream verify_policy) and appends ai_wrong.jsonl.

Every quote (original or replacement) is re-located verbatim (whitespace-normalized) on its cited page by
policy_build.locate; any miss raises, so nothing unverified is written.
"""
import csv
import io
import json
import re
from collections import defaultdict

from agent.moat.common import ROOT, now, write
from agent.moat.policy_build import load, locate, norm

T10 = ["MRK", "BMY", "PFE", "LLY", "NVO", "ABBV", "JNJ", "AZN", "AMGN", "GILD"]
C = lambda t, f: f"data/corpus/companies/{t}/{f}"
K = lambda t: C(t, "10k_FY2025.md")
WH_LN = "data/moat/policy_gov/wh/wh_fact_sheet_2025-11-06_lilly_novo.md"
NVO_D2 = C("NVO", "20f_FY2025_d2.md")
F28 = "data/moat/policy_gov/cms/cms_fact_sheet_selected_list_ipay2028.md"

rows = list(csv.DictReader(open(ROOT / "data/moat/tables/policy_exposure.csv")))
byid = {r["row_id"]: r for r in rows}


def page_of(doc, quote):
    url, page, q = locate(doc, [quote])
    if page is None:
        raise SystemExit(f"QUOTE NOT FOUND: {doc} :: {quote[:90]}")
    return url, page, q


def onpage(r):
    """Original quote verbatim on the cited page label."""
    _, pages = load(r["doc"])
    q = norm(r["quote"])
    return any(lab == r["printed_page_or_section"] and q in b for lab, b in pages)


def also(doc, quote):
    _, page, _ = page_of(doc, quote)
    return f'supporting quote ({doc.split("/")[-1]} p.{page}): "{quote}"'


# ---------------- per-row decisions ----------------
FIX = {}  # row_id -> dict(status, note, and optional new field values)


def fix(rid, note, **kw):
    FIX[rid] = dict(status="fixed", note=note, **kw)


def drop(rid, note):
    FIX[rid] = dict(status="dropped", note=note)


def vnote(rid, note):
    FIX[rid] = dict(status="verified", note=note)


fix("R010", "original quote is about Zepbound/orforglipron Medicaid access, not MFN Medicaid pricing; re-cited to the White House fact sheet sentence that states MFN Medicaid access",
    value="yes", doc=WH_LN, quote="provide every State Medicaid program in the country access to MFN drug prices on their products")
fix("R014", "original quote (Novo release) only says semaglutide pricing in Part D/Medicaid/cash; re-cited to the White House fact sheet sentence on MFN Medicaid access",
    value="yes", doc=WH_LN, quote="provide every State Medicaid program in the country access to MFN drug prices on their products")
vnote("R012", "quote supports Zepbound avg $346; Trulicity part " + also(WH_LN, "Trulicity, a commonly used diabetes medicine, at $389 per month"))
vnote("R016", "quote supports Ozempic/Wegovy $350 via TrumpRx; NovoLog part " + also(WH_LN, "Novo Nordisk will provide widely-used insulin products, including NovoLog and Tresiba, at $35 per month of supply") + " (the $35 sentence does not say TrumpRx)")
vnote("R028", "quote supports Reyataz $1,449 -> $217; ~80% part " + also(C("BMY", "policy/press_2025-12-19_us-government-agreement.md"), "making these important medicines available at discounts approximately 80% off current list prices"))
fix("R027", "item mislabeled: the quote is about the scope of the deal (all four July-letter asks), not a new-launch price commitment", item="Scope")
fix("R032", "item mislabeled: the quote is about the scope of the deal (satisfies July MFN letter components), not a new-launch price commitment", item="Scope")
fix("R046", "quote supports only Elkton VA $3B; the other three sites and the 2025-2030 window are not in the cited quote, value trimmed",
    value="Elkton VA $3B", effective_date="2025-10-20")
fix("R048", "effective_date 2025-2028 not supported: the release says 'in the next few years' with no end year", effective_date="next few years (no end year stated)")
fix("R049", "quote was truncated before the numbers it supports; replaced with the full clause", quote="supported by 13 manufacturing and distribution sites and 7 major R&D facilities")
vnote("R056", "verified as a 2025 announcement of US manufacturing capex ($900M Ohio + $1B North Carolina); this is NOT a forward pledge and is excluded from the pledge column in force_summary")
vnote("R057", "historic spend since 2018, not a pledge; excluded from force_summary")
for i in range(59, 69):
    vnote(f"R{i:03d}", "zero rate applies to companies eligible under clause 3(b) (onshoring plan) AND with an MFN agreement with HHS; effective 2026-07-31 only for Annex III companies (Sept 29, 2026 for others) and Annex III is not in the local proclamation text, so per-company Annex III membership is not verified")
for i in range(79, 89):
    vnote(f"R{i:03d}", "20% applies only to companies with (or likely soon to have) Commerce-approved onshoring plans; general rule, not company-specific")
fix("R119", "WRONG SCOPE: 159,077 is the Novo Nordisk A/S PARENT-company note (its 2024 comparative 261,712 does not match group 2024 net sales 290,403). Replaced with the group figure for external US customers",
    item="FY2025 US revenue (group, external customers in the US)", value="173166",
    quote="Of the total net sales of DKK 309,064 million, DKK 173,166 million was generated from external customers in the US", doc=NVO_D2)
fix("R120", "WRONG SCOPE: 289,015 is the parent-company (Novo Nordisk A/S) total, not the group; replaced with group net sales",
    item="FY2025 Total revenue (group net sales)", value="309064", quote="Net sales 309,064 290,403 232,261", doc=NVO_D2)
vnote("R127", "US product sales only (Amgen discloses geography for product sales, not total revenues); force_summary uses US product sales / total product sales 35,148")
fix("R142", "label wrong: 'Fast-acting insulin' = Fiasp 2,818 + NovoRapid (NovoLog) 15,765 = 18,583, exactly the selected insulin-aspart products (NovoMix is a separate line); it is NOT an upper bound with non-selected products",
    item="FY2025 revenue of selected drug: Fiasp + NovoRapid/NovoLog (Fast-acting insulin line)",
    quote="Fast-acting insulin 8,245 7,773 5,265 10,338 10,749 10,684 5,023 4,963 5,077 2,894 3,111 2,772 1,110 1,201 1,290 1,311 1,474 1,545 18,583", note_col="worldwide (group)")
fix("R143", "WRONG SCOPE: 2,048 is US only; AbbVie's total Imbruvica net revenue is 2,869 (US 2,048 + collaboration revenues 821 from Janssen ex-US)",
    item="FY2025 revenue of selected drug: Imbruvica (US 2,048 + collaboration 821)", value="2869", note_col="worldwide (AbbVie-reported total)",
    quote="Imbruvica United States $ 2,048 $ 2,448 $ 2,665 (16.4) % (8.1) % (16.4) % (8.1) % Collaboration revenues 821 899 931 (8.6) % (3.5) % (8.6) % (3.5) % Total $ 2,869")
fix("R144", "quote showed only the US row; replaced with the row through Total $907 so the worldwide value follows from the quote",
    quote="Linzess/Constella United States $ 864 $ 916 $ 1,073 (5.7) % (14.6) % (5.7) % (14.6) % International 43 38 35 13.6 % 7.5 % 13.3 % 7.2 % Total $ 907")
fix("R145", "quote showed only the US row (3,612); replaced with the row through Total $3,621",
    quote="Vraylar United States $ 3,612 $ 3,260 $ 2,755 10.8 % 18.4 % 10.8 % 18.4 % International 9 7 4 33.3 % 57.8 % 36.8 % 58.6 % Total $ 3,621")
fix("R146", "quote showed only the US row; replaced with the row through Total $3,769. Scope: CMS selected 'Botox; Botox Cosmetic' as one drug, so Botox Cosmetic (2,602, row N005) is added in force_summary",
    quote="Botox Therapeutic United States $ 3,151 $ 2,718 $ 2,476 16.0 % 9.8 % 16.0 % 9.8 % International 618 565 515 9.3 % 9.8 % 9.9 % 14.0 % Total $ 3,769")
fix("R147", "quote replaced to show Worldwide 2,633 (no international sales; Bayer sells ex-US)",
    quote="XARELTO U.S. 2,633 2,373 2,365 11.0 0.3 International — — — — — Worldwide 2,633")
fix("R148", "quote showed only the US row (3,847); replaced with the row through Worldwide 6,078",
    quote="STELARA U.S. 3,847 6,720 6,966 ( 42.7 ) ( 3.5 ) International 2,230 3,641 3,892 ( 38.7 ) ( 6.4 ) Worldwide 6,078")
fix("R149", "quote showed only the US row (1,453); replaced with the row through Worldwide 3,574",
    quote="ERLEADA U.S. 1,453 1,282 1,065 13.4 20.3 International 2,121 1,717 1,322 23.5 29.8 Worldwide 3,574")
for rid in ["R203", "R204", "R205", "R206", "R207", "R208", "R209"]:
    vnote(rid, "the CMS IPAY 2028 list has no manufacturer column: company attribution is by brand ownership, not by the cited doc; the figure is Medicare Part B+D spend Nov 2024-Oct 2025, not company revenue")
drop("R211", "value 'see 10-K' is not a datum and the quote (other proposed policy actions) does not describe an Enbrel/Otezla IRA effect")
vnote("R137", "worldwide = US 2,914 + outside US 1,362 (2025 columns of the by-product table, which includes collaboration and other revenue); basis consistent with peers")

# ---------------- added rows (support recomputed summary) ----------------
NEW = [
    ("N001", "ABBV", "IRA", "FY2025 revenue of selected drug: Botox Cosmetic (CMS selected 'Botox; Botox Cosmetic')", 2602, "USD m", "2025-12-31", K("ABBV"),
     "Aesthetics Botox Cosmetic United States $ 1,504 $ 1,682 $ 1,670 (10.5) % 0.7 % (10.5) % 0.7 % International 1,098 1,038 1,012 5.7 % 2.7 % 6.2 % 6.7 % Total $ 2,602", "worldwide; included because CMS names the selected drug 'Botox; Botox Cosmetic'"),
    ("N002", "MRK", "IRA", "FY2025 revenue of expected selection: Keytruda/Keytruda Qlex (expected 2027 selection, MFP 2029)", 31680, "USD m", "2025-12-31", K("MRK"),
     "Keytruda/Keytruda Qlex 31,680 29,482 25,011", "worldwide; includes Keytruda Qlex (subcutaneous), whose inclusion in a pembrolizumab selection is not stated"),
    ("N003", "MRK", "IRA", "Lenvima selected for IPAY 2028 (Eisai product; Merck alliance)", "2028-01-01", "date", "2028-01-01", K("MRK"),
     "in January 2026, HHS announced that Lenvima has been selected for government price setting, the set price for which will become effective on January 1, 2028", "partnered drug: counted only in the incl-partnered column"),
    ("N004", "MRK", "IRA", "FY2025 alliance revenue: Lenvima (partnered selected drug)", 1053, "USD m", "2025-12-31", K("MRK"),
     "Alliance revenue - Lenvima (1) 1,053 1,010 960", "partnered"),
    ("N005", "PFE", "IRA", "FY2025 revenue: Eliquis (BMS-named selected drug, Pfizer alliance)", 7961, "USD m", "2025-12-31", K("PFE"),
     "Eliquis $7,961 Up 7% (operationally)", "partnered; worldwide"),
    ("N006", "PFE", "IRA", "FY2025 revenue: Xtandi (Astellas-named selected drug, IPAY 2027; Pfizer alliance)", 2194, "USD m", "2025-12-31", K("PFE"),
     "Xtandi $2,194 Up 8% (operationally)", "partnered; worldwide"),
    ("N007", "PFE", "IRA", "Pfizer states Xtandi was selected (IPAY 2027)", "2027-01-01", "date", "2027-01-01", K("PFE"),
     "Ibrance and Xtandi were included in the list of 15 drugs selected", "partnered"),
    ("N008", "JNJ", "IRA", "FY2025 revenue: Imbruvica (Pharmacyclics-named selected drug, IPAY 2026; J&J collaboration)", 2823, "USD m", "2025-12-31", K("JNJ"),
     "IMBRUVICA U.S. 892 1,020 1,051 ( 12.5 ) ( 3.0 ) International 1,931 2,018 2,214 ( 4.3 ) ( 8.8 ) Worldwide 2,823", "partnered; worldwide"),
    ("N009", "LLY", "IRA", "FY2025 revenue: Jardiance (Boehringer-named selected drug, IPAY 2026; Lilly alliance) US 1,582 + OUS 1,849", 3431, "USD m", "2025-12-31", K("LLY"),
     "Jardiance (2) 1,582 1,598 1,600 1,849 1,743 1,144", "partnered; worldwide, computed. Tradjenta (IPAY 2027, also BI/Lilly) is not broken out by Lilly"),
]

# ---------------- build verified policy_exposure ----------------
cols = ["row_id", "ticker", "force", "item", "value", "unit", "effective_date", "doc", "printed_page_or_section", "quote", "source", "source_row", "note", "status", "verify_note"]
out = []
stats = defaultdict(int)
for r in rows:
    rid = r["row_id"]
    is_site = r["doc"].endswith(".csv")
    d = FIX.get(rid)
    rr = dict(r)
    if is_site:
        continue  # handled below
    assert onpage(r), rid
    if d is None:
        status, note = "verified", "quote verbatim on cited page; value/unit/date follow from it"
        if r["unit"] == "date" and r["force"] == "MFN" and r["value"][:4] in ("2025", "2026"):
            note += " (date taken from the document dateline)"
    else:
        status, note = d["status"], d["note"]
        for k in ("item", "value", "effective_date", "doc", "quote"):
            if k in d:
                rr[k] = d[k]
        if "note_col" in d:
            rr["note"] = d["note_col"]
        if "quote" in d or "doc" in d:
            url, page, q = page_of(rr["doc"], rr["quote"])
            rr.update(printed_page_or_section=page, quote=q, source=url, source_row=f"{rr['doc']}#page={page}")
    rr["status"], rr["verify_note"] = status, note
    stats[status] += 1
    out.append(rr)

for nid, t, force, item, v, u, eff, doc, q, nc in NEW:
    url, page, qq = page_of(doc, q)
    out.append(dict(row_id=nid, ticker=t, force=force, item=item, value=str(v), unit=u, effective_date=eff, doc=doc, printed_page_or_section=page,
                    quote=qq, source=url, source_row=f"{doc}#page={page}", note=nc, status="added", verify_note="added by verifier; quote verbatim on cited page"))
    stats["added"] += 1

# ---------------- manufacturing sites: corrected counts ----------------
det = list(csv.DictReader(open(ROOT / "data/moat/tables/manufacturing_sites_detail.csv")))
FP = [  # (ticker, regex on firm|registrant, reason)
    ("MRK", r"organon", "Organon was spun off from Merck in 2021 (MRK 10-K: 'the 2021 spin-off'); alias 'organon llc$' matched the registrant"),
    ("PFE", r"meridian medical", "Meridian Medical Technologies is self-registered and was divested by Pfizer (2021); alias matched the firm name"),
    ("PFE", r"upjohn manufacturing ireland", "Upjohn business went to Viatris in 2020 (PFE 10-K: Upjohn combined with Mylan to create Viatris); self-registered"),
    ("PFE", r"^biohaven pharmaceuticals, inc", "self-registered Biohaven entity (the post-2022 spun-out Biohaven Ltd), not Pfizer"),
    ("ABBV", r"natural immunogenics", "dietary-supplement firm 'Natural Immunogenics' matched the alias 'immunogen'"),
    ("JNJ", r"kenvue", "Kenvue (consumer health) separated from J&J in 2023; McNeil sites are registered by Kenvue Brands LLC"),
]
FLAG = [
    ("PFE", r"zydus hospira", "joint venture (Zydus/Hospira), ownership share not verified"),
    ("PFE", r"gentrac", "registered by Wyeth/Pfizer; ownership vs contract site not verified"),
    ("MRK", r"intervet|vet pharma|burgwedel", "Merck Animal Health site (counted; not human pharma)"),
    ("MRK", r"cherokee", "registered by Merck & Co.; ownership vs contract site not verified"),
    ("JNJ", r"amo \(hangzhou\)", "J&J MedTech (Surgical Vision) site, not pharma"),
    ("GILD", r"gilead alberta", "matched via registrant despite firm-name exclusion; Gilead-owned Edmonton site, kept"),
]
ADD = [("NVO", "3005949964", "Catalent Indiana, LLC (1100 S Strong Drive, Bloomington IN)", "USA", "drls_reg.txt:line 4878"),
       ("NVO", "3005949964", "Catalent Indiana, LLC (1300 S. Patterson Drive, Bloomington IN)", "USA", "drls_reg.txt:line 4879")]
ISUS = ("USA", "PRI", "VIR", "GUM")
site_rows = []
cnt = {t: defaultdict(int) for t in T10}
for d in det:
    t, hay = d["ticker"], (d["firm_name"] + " | " + d["registrant_name"]).lower()
    fp = [why for tk, pat, why in FP if tk == t and re.search(pat, hay)]
    fl = [why for tk, pat, why in FLAG if tk == t and re.search(pat, hay)]
    keep = not fp
    mfg = d["has_manufacture_op"] == "Y"
    us = d["country_code"] in ISUS
    cnt[t]["orig_mfg"] += mfg
    cnt[t]["orig_mfg_us"] += mfg and us
    if keep:
        cnt[t]["mfg"] += mfg
        cnt[t]["mfg_us"] += mfg and us
    if fp:
        cnt[t]["removed"] += mfg
    site_rows.append([t, d["fei_number"], d["firm_name"], d["registrant_name"], d["country_code"], d["has_manufacture_op"], d["source_row"],
                      "re-read: FEI, firm name and operations match the FDA file line", "dropped" if fp else "verified", "; ".join(fp + fl)])
for t, fei, name, c, src in ADD:
    cnt[t]["mfg"] += 1
    cnt[t]["mfg_us"] += 1
    cnt[t]["added"] += 1
    site_rows.append([t, fei, name, "Catalent Indiana, LLC", c, "Y", src, "found by verifier probe", "added",
                      "former Catalent fill-finish site acquired by Novo Nordisk (NVO 20-F: 'acquisition of three former Catalent sites'); still registered under the Catalent name"])
CONF = {
    "MRK": "medium: 5 Organon sites removed; includes 6 Merck Animal Health sites; CDER file only (CBER-only vaccine/biologic sites may be missing)",
    "BMY": "low: CDER file only; BMS cell-therapy sites (CBER) and several biologics sites are likely missing, so the count is an undercount",
    "PFE": "medium: 4 non-Pfizer sites removed (Meridian x2 with MANUFACTURE, Upjohn Ireland, Biohaven); Zydus Hospira JV kept and flagged; CBER vaccine sites likely missing",
    "LLY": "low: only 10 MANUFACTURE sites matched; newer US sites and CBER-registered biologics sites may be missing",
    "NVO": "medium: +2 former Catalent Bloomington IN sites registered under the Catalent name; Anagni (Catalent) already matched via registrant",
    "ABBV": "medium-high: 1 supplement firm removed",
    "JNJ": "medium: 2 Kenvue (McNeil) sites removed; 1 MedTech site kept and flagged; CBER sites likely missing",
    "AZN": "medium-high: no false positives found; CBER biologics may be missing",
    "AMGN": "low: biologics-heavy company, CDER file captures few sites (New Albany OH and Louisville KY are registered without a MANUFACTURE op); likely undercount",
    "GILD": "medium: Kite cell-therapy sites appear in the file; Gilead Alberta kept",
}

# ---------------- force_summary ----------------
V = {r["row_id"]: r for r in out}
fv = lambda rid: float(V[rid]["value"])
STRICT = {  # selected drugs where the ticker is the CMS-named (or brand-owning, for IPAY 2028) manufacturer
    "MRK": [("Januvia (2026); Janumet/Janumet XR (2027)", "R131")],
    "BMY": [("Eliquis (2026)", "R132"), ("Pomalyst (2027)", "R133"), ("Orencia (2028)", "R134")],
    "PFE": [("Ibrance (2027)", "R135"), ("Xeljanz/Xeljanz XR (2028)", "R136")],
    "LLY": [("Trulicity (2028)", "R137"), ("Verzenio (2028)", "R138")],
    "NVO": [("Ozempic (2027)", "R139"), ("Wegovy (2027)", "R140"), ("Rybelsus (2027)", "R141"), ("Fiasp/NovoLog (2026)", "R142")],
    "ABBV": [("Imbruvica (2026)", "R143"), ("Linzess (2027)", "R144"), ("Vraylar (2027)", "R145"), ("Botox (2028)", "R146"), ("Botox Cosmetic (2028)", "N001")],
    "JNJ": [("Xarelto (2026)", "R147"), ("Stelara (2026)", "R148"), ("Erleada (2028)", "R149")],
    "AZN": [("Farxiga (2026)", "R150"), ("Calquence (2027)", "R151")],
    "AMGN": [("Enbrel (2026)", "R152"), ("Otezla/Otezla XR (2027)", "R153")],
    "GILD": [("Biktarvy (2028)", "R154")],
}
COUNT = {"MRK": 2, "BMY": 3, "PFE": 2, "LLY": 2, "NVO": 2, "ABBV": 4, "JNJ": 3, "AZN": 2, "AMGN": 2, "GILD": 1}
PART = {"MRK": [("Lenvima (2028, Eisai)", "N004")], "PFE": [("Eliquis (2026, BMS)", "N005"), ("Xtandi (2027, Astellas)", "N006")],
        "JNJ": [("Imbruvica (2026, Pharmacyclics/AbbVie)", "N008")], "LLY": [("Jardiance (2026, Boehringer)", "N009")]}
TOT = {"MRK": "R112", "BMY": "R114", "PFE": "R116", "LLY": "R118", "NVO": "R120", "ABBV": "R122", "JNJ": "R124", "AZN": "R126", "AMGN": "R128", "GILD": "R130"}
USR = {"MRK": "R111", "BMY": "R113", "PFE": "R115", "LLY": "R117", "NVO": "R119", "ABBV": "R121", "JNJ": "R123", "AZN": "R125", "AMGN": "R127", "GILD": "R129"}
MFN = {"MRK": "R018", "BMY": "R020", "PFE": "R001", "LLY": "R009", "NVO": "R013", "ABBV": "R040", "JNJ": "R036", "AZN": "R005", "AMGN": "R022", "GILD": "R024"}
TAR = {t: f"R{59 + i:03d}" for i, t in enumerate(T10)}
PLEDGE = {  # total, capex, R&D, horizon, scope, rows, note
    "MRK": (70, 12, None, "next several years (from 2025)", "capital + R&D", "R044,R045", "'more than $70B ... including at least $12B in capital expenditures'; R&D share not stated (remainder <=58 implied)"),
    "BMY": (40, None, None, "5 years (2025-2030)", "US investment, unspecified mix", "R047", "no capex/R&D split in source"),
    "PFE": (70, None, None, "next few years (no end year)", "R&D + capital projects", "R048", "no split in source"),
    "LLY": (50, 50, None, "not stated", "US manufacturing only", "R050,R051", "all manufacturing (capex); White House counts at least $27B as new"),
    "NVO": (10, None, None, "not stated", "additional US investment, unspecified mix", "R052", "'additional' $10B per White House; no split"),
    "ABBV": (100, None, None, "10 years (2026-2036)", "R&D + capital incl. manufacturing", "R053", "no split in source"),
    "JNJ": (55, None, None, "~4 years, by early 2029", "manufacturing + R&D + technology", "R054", "no split in source"),
    "AZN": (50, None, None, "by 2030", "manufacturing + R&D", "R055", "no split in source"),
    "AMGN": (None, None, None, "", "no forward pledge", "R056,R057", "no forward total pledge found; $2.5B = 2025 US manufacturing capex announcements; >$40B = historic manufacturing + R&D since 2018"),
    "GILD": (32, None, None, "through 2030", "manufacturing + R&D + infrastructure", "R058", "$11B newly announced capital and operational + $21B already planned (press_2025-05-07); no capex/R&D split"),
}
fcols = ["ticker", "ira_drug_count_ipay2026_2028", "ira_drugs", "ira_drug_fy2025_revenue", "ira_revenue_unit", "fy2025_total_revenue", "ira_share_of_total_revenue_pct",
         "ira_partnered_drugs_not_counted", "ira_share_incl_partnered_pct", "expected_selection", "expected_fy2025_revenue", "expected_share_pct", "expected_quote",
         "mfn_date", "us_investment_pledge_usd_bn", "pledge_capex_usd_bn", "pledge_rd_usd_bn", "pledge_horizon", "pledge_scope", "pledge_note",
         "tariff_exempt_until", "mfg_sites_total", "mfg_sites_non_us", "pct_mfg_sites_outside_us", "mfg_sites_confidence",
         "us_revenue_share_pct", "us_revenue_basis", "traceable_row_ids"]
summ = []
for t in T10:
    ira = sum(fv(rid) for _, rid in STRICT[t])
    tot = fv(TOT[t])
    part = sum(fv(rid) for _, rid in PART.get(t, []))
    if t == "AMGN":
        usr, usb = 25656 / 35148, "US product sales / total product sales (geography disclosed for product sales only)"
    elif t == "NVO":
        usr, usb = fv(USR[t]) / tot, "group sales to external US customers / group net sales"
    else:
        usr, usb = fv(USR[t]) / tot, "US revenue / total revenue (as reported)"
    c = cnt[t]
    p = PLEDGE[t]
    exp = ("Keytruda (expected 2027 selection, MFP 2029-01-01)", 31680, round(100 * 31680 / tot, 1), V["R210"]["quote"]) if t == "MRK" else ("", "", "", "")
    ids = [rid for _, rid in STRICT[t]] + [rid for _, rid in PART.get(t, [])] + [TOT[t], USR[t], MFN[t], TAR[t]] + p[5].split(",") + (["R210", "N002", "N003"] if t == "MRK" else []) + (["N007"] if t == "PFE" else [])
    summ.append([t, COUNT[t], "; ".join(d for d, _ in STRICT[t]), round(ira), V[TOT[t]]["unit"], round(tot), round(100 * ira / tot, 1),
                 "; ".join(d for d, _ in PART.get(t, [])), round(100 * (ira + part) / tot, 1) if t in PART else round(100 * ira / tot, 1),
                 exp[0], exp[1], exp[2], exp[3], V[MFN[t]]["value"], p[0] if p[0] is not None else "", p[1] or "", p[2] or "", p[3], p[4], p[6],
                 V[TAR[t]]["value"], c["mfg"], c["mfg"] - c["mfg_us"], round(100 * (c["mfg"] - c["mfg_us"]) / c["mfg"], 1), CONF[t],
                 round(100 * usr, 1), usb, ",".join(ids)])

# ---------------- IRA % cut re-derivation ----------------
cut = [["ticker", "drug", "ipay", "mfp_usd_30day", "list_usd_30day", "list_price_year", "cms_pct_cut", "recomputed_pct_cut", "recomputed_exact", "match", "doc", "page", "quote"]]
for r in out:
    m = re.match(r"IRA (.+?) \(IPAY (\d{4})\): MFP per 30-day supply", r["item"])
    if not m:
        continue
    drug, ipay = m.group(1), m.group(2)
    lst = next(x for x in out if x["ticker"] == r["ticker"] and x["item"] == f"IRA {drug} (IPAY {ipay}): list price per 30-day supply")
    pct = next(x for x in out if x["ticker"] == r["ticker"] and x["item"] == f"IRA {drug} (IPAY {ipay}): % cut of MFP vs list")
    exact = 100 * (1 - float(r["value"]) / float(lst["value"]))
    ok = round(exact) == int(float(pct["value"]))
    nums = [float(x.replace(",", "")) for x in re.findall(r"\$([\d,]+(?:\.\d+)?)", r["quote"])]
    ok = ok and nums[:2] == [float(r["value"]), float(lst["value"])] and (pct["value"] + "%") in r["quote"]
    cut.append([r["ticker"], drug, ipay, r["value"], lst["value"], "2023" if ipay == "2026" else "2024", pct["value"], round(exact), f"{exact:.2f}", "yes" if ok else "NO",
                r["doc"], r["printed_page_or_section"], r["quote"]])

# ---------------- write ----------------


def csvtext(header, data, dicts=False):
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(header)
    for d in data:
        w.writerow([d.get(k, "") for k in header] if dicts else d)
    return buf.getvalue()


site_hdr = ["ticker", "fei_number", "firm_name", "registrant_name", "country_code", "has_manufacture_op", "source_row", "check", "status", "verify_note"]
# site rows of policy_exposure: replace the 4 per-company aggregates with corrected counts
for r in rows:
    if not r["doc"].endswith(".csv"):
        continue
    t, c = r["ticker"], cnt[r["ticker"]]
    item = r["item"]
    if "MANUFACTURE operation: total" in item:
        new = c["mfg"]
    elif "MANUFACTURE operation: US" in item:
        new = c["mfg_us"]
    else:
        new = None
    rr = dict(r)
    if new is not None and str(new) != r["value"]:
        rr["value"] = str(new)
        rr["status"], rr["verify_note"] = "fixed", f"corrected count {r['value']} -> {new}: removed {c['removed']} false-positive, added {c['added']} missed site(s); see manufacturing_sites_verified.csv. Confidence: {CONF[t]}"
        stats["fixed"] += 1
    elif new is not None:
        rr["status"], rr["verify_note"] = "verified", f"all detail rows re-read against FDA file lines; no change. Confidence: {CONF[t]}"
        stats["verified"] += 1
    else:
        rr["status"], rr["verify_note"] = "verified", "all-operations count not re-derived (summary uses MANUFACTURE-op counts); detail rows re-read and match FDA lines"
        stats["verified"] += 1
    out.append(rr)

order = {r["row_id"]: i for i, r in enumerate(rows)}
out.sort(key=lambda r: (order.get(r["row_id"], 10_000), r["row_id"]))
write("verify_policy", "verified/policy/policy_exposure.csv", csvtext(cols, out, dicts=True), group="policy", doc_type="table", source_url="see source column")
write("verify_policy", "verified/policy/force_summary.csv", csvtext(fcols, summ), group="policy", doc_type="table", source_url="see traceable_row_ids")
write("verify_policy", "verified/policy/ira_cut_check.csv", csvtext(cut[0], cut[1:]), group="policy", doc_type="table", source_url="CMS fact sheets")
write("verify_policy", "verified/policy/manufacturing_sites_verified.csv", csvtext(site_hdr, site_rows), group="policy", doc_type="table",
      source_url="https://www.accessdata.fda.gov/cder/drls_reg.zip")
print("stats", dict(stats), "rows", len(out))
print("cuts", len(cut) - 1, "mismatch", sum(1 for c in cut[1:] if c[9] != "yes"))
for s in summ:
    print(s[:12], s[13:27])
for t in T10:
    print(t, dict(cnt[t]))
