"""Build the verified deals outputs: verified/deals/{deal_comps,deal_benchmarks,duplicates,pr_checks}.csv + NOTES.md,
append errors to verify/ai_wrong.jsonl, dedupe gaps/deals.jsonl.
Run: PYTHONPATH=. python -m agent.moat.verify.dv_build"""
import csv
import io
import json
import re
import statistics
from datetime import date

import pandas as pd

from agent.moat.common import write, OUT
from agent.moat.verify.dv_judg import J
from agent.moat.verify.dv_lib import WORK, load, norm, source_text, amt_set, has_amt, isnum

STREAM = "verify_deals"
d = load()
orig = d.copy()
for c in ("verify_status", "role_unverified", "verify_note", "quote_on_page", "numbers_on_page"):
    d[c] = ""
d["verify_status"] = "unchecked"
d["role_unverified"] = 0
d["equity_usd_m"] = d["equity_usd_m"].astype("object")
NUM = ["upfront_usd_m", "equity_usd_m", "milestones_usd_m", "total_potential_usd_m"]
for c in d.columns:
    d[c] = d[c].astype("object")
idx = {r: i for i, r in enumerate(d.deal_id)}

# ------------------------------------------------------------------ 1. mechanical quote/number check on every row
print("mechanical check of all rows ...", flush=True)
mech = {}
for i, r in d.iterrows():
    try:
        page, doc, loc = source_text(r)
    except Exception as e:  # noqa
        page, doc = "", ""
    q = norm(r["quote"])
    qok = bool(q) and q in norm(page)
    pv, dv = amt_set(page), amt_set(doc)
    miss = []
    for f in ("upfront_usd_m", "milestones_usd_m", "total_potential_usd_m"):
        v = r[f]
        if isnum(v) and not has_amt(dv, float(v)):
            if f == "total_potential_usd_m" and isnum(r["upfront_usd_m"]) and isnum(r["milestones_usd_m"]) and \
                    abs(float(v) - float(r["upfront_usd_m"]) - float(r["milestones_usd_m"])) < 0.6:
                continue
            miss.append(f.replace("_usd_m", ""))
    mech[r["deal_id"]] = (qok, miss, page)
    d.at[i, "quote_on_page"] = int(qok)
    d.at[i, "numbers_on_page"] = "ok" if not miss else "missing:" + "/".join(miss)

# ------------------------------------------------------------------ 2. apply hand judgments
errors = []  # rows for ai_wrong
SEV_HIGH = {"not_a_deal", "termination_fee", "financing", "threshold_as_price", "threshold_as_milestone", "market_size_as_value",
            "thousands_as_millions", "aud_as_usd", "debt_payoff_as_price", "financing_as_price", "wrong_numbers", "total_as_upfront",
            "milestones_as_upfront", "equity_read_as_total", "supply_agreement", "manufacturing_agreement", "settlement",
            "aggregate_not_deal", "not_biopharma", "merger_as_license", "per_program_as_total", "component_double_count",
            "royalty_financing_as_license", "wrong_parties", "warrant_as_total", "cost_as_milestone", "milestone_event_as_deal"}
SEV_LOW = {"ta_wrong", "duplicate"}
for k, jd in J.items():
    if k not in idx:
        continue
    i = idx[k]
    before = {f: orig.at[i, f] for f in jd["fix"]}
    for f, v in jd["fix"].items():
        d.at[i, f] = "" if v is None else v
    d.at[i, "verify_status"] = jd["s"]
    note = jd["note"]
    if jd["dup"]:
        note = f"duplicate of {jd['dup']}; " + note
    d.at[i, "verify_note"] = ("hand-checked: " + note).strip("; ")
    et = jd["et"]
    if et:
        wrote = "; ".join(f"{f}={'' if (isinstance(v, float) and v != v) else v}" for f, v in before.items()) or \
            f"deal_type={orig.at[i, 'deal_type']}; upfront={orig.at[i, 'upfront_usd_m']}; total={orig.at[i, 'total_potential_usd_m']}"
        says = note + (("; corrected " + "; ".join(f"{f}={'' if v is None else v}" for f, v in jd["fix"].items())) if jd["fix"] else "")
        sev = "high" if et in SEV_HIGH else ("low" if et in SEV_LOW else "medium")
        if jd["s"] == "dropped" and et not in SEV_LOW:
            sev = "high"
        errors.append(dict(stream="deals", table="deal_comps.csv", row_key=k, what_the_ai_wrote=wrote, what_the_source_says=says,
                           error_type=et, severity=sev, confidence_tier=orig.at[i, "confidence"], origin=orig.at[i, "origin"],
                           how_caught="Opus read of the cited page", example_source=str(orig.at[i, "source_row"])))
    if jd["role"] in ("swapped",) and et != "role_swapped":
        errors.append(dict(stream="deals", table="deal_comps.csv", row_key=k,
                           what_the_ai_wrote=f"licensee={orig.at[i, 'acquirer_or_licensee']}; licensor={orig.at[i, 'target_or_licensor']}",
                           what_the_source_says="payment direction in the cited sentence shows the roles are reversed", error_type="role_swapped",
                           severity="medium", confidence_tier=orig.at[i, "confidence"], origin=orig.at[i, "origin"],
                           how_caught="Opus read of the cited page", example_source=str(orig.at[i, "source_row"])))

# ------------------------------------------------------------------ 3. role direction rate (low:role and medium:role samples)
role_stats = {}
for tier in ("low:role", "medium:role"):
    ks = [k for k in J if k in idx and orig.at[idx[k], "confidence"] == tier]
    sw = [k for k in ks if J[k]["role"] == "swapped"]
    junk = [k for k in ks if J[k]["role"] == "junk"]
    role_stats[tier] = dict(n=len(ks), swapped=len(sw), junk=len(junk))
lr = role_stats["low:role"]
low_rate = lr["swapped"] / lr["n"] if lr["n"] else 0
low_any = (lr["swapped"] + lr["junk"]) / lr["n"] if lr["n"] else 0
# all tiers
allk = [k for k in J if k in idx]
role_stats["all_checked"] = dict(n=len(allk), swapped=sum(J[k]["role"] == "swapped" for k in allk), junk=sum(J[k]["role"] == "junk" for k in allk))
if low_rate > 0.15 or low_any > 0.15:
    m = (d.confidence.isin(["low:role", "medium:role"])) & (d.verify_status == "unchecked")
    d.loc[m, "role_unverified"] = 1

# ------------------------------------------------------------------ 4. automatic screens on unchecked rows (patterns proven on the sample)
SCREENS = [("termination_fee", r"termination fee"), ("financing", r"\bterm loan|credit agreement|indenture|bridge loan|\bliens?\b|private placement|"
                                                                  r"securities purchase agreement|\bPIPE\b|revolving|notes due"),
           ("market_size_as_value", r"market (?:could|is expected to|will) grow|market for .{0,60}(?:valued|estimated)|billion by 20\d\d"),
           ("settlement", r"settlement agreement|release of (?:all )?claims"),
           ("not_a_deal", r"fairness opinion|implied equity value range|transaction price was determined|recognized .{0,40}revenue .{0,40}upfront|"
                          r"capitali[sz]ed license")]
screen_hits = {}
for i, r in d.iterrows():
    q = str(r["quote"])
    hit = next((name for name, rx in SCREENS if re.search(rx, q, re.I)), None)
    if not hit:
        continue
    screen_hits.setdefault(hit, []).append(r["deal_id"])
    if r["verify_status"] == "unchecked":
        d.at[i, "verify_status"] = "dropped"
        d.at[i, "verify_note"] = f"auto-screen: quote matches '{hit}' pattern (pattern precision checked on the hand sample)"
# precision of each screen on hand-judged rows
screen_prec = {}
for name, ids in screen_hits.items():
    j_ = [k for k in ids if k in J]
    screen_prec[name] = dict(hits=len(ids), judged=len(j_), judged_dropped=sum(J[k]["s"] == "dropped" for k in j_))

# ------------------------------------------------------------------ 5. units
UNIT = []
for i, r in d.iterrows():
    q = str(r["quote"])
    flags = []
    m = re.search(r"\b(AU|A|C|CA|HK|NT|S|NZ)\$\s?(\d[\d,\.]*)\s?(million|billion)?", q)
    if m:
        flags.append(f"non-USD dollars {m.group(0)}")
    if re.search(r"€|\bEUR\b|¥|\bJPY\b|\byen\b|\bCHF\b|\bRMB\b|£|\bGBP\b|\bDKK\b|\bSEK\b|\bKRW\b|\bwon\b", q):
        conv = bool(re.search(r"\(\s*(?:approximately |approx\. |~)?(?:US)?\$\s?\d", q)) or bool(re.search(r"\$\s?\d[^)]{0,20}\(\s*(?:€|£|¥|EUR|CHF|RMB)", q))
        flags.append("non-USD amount in quote; " + ("USD conversion present" if conv else "no USD conversion in quote"))
    for mm in re.finditer(r"\$\s?(\d+(?:\.\d+)?) (?:per share|per CVR|/share)", q):
        ps = float(mm.group(1))
        for f in ("upfront_usd_m", "total_potential_usd_m"):
            if isnum(r[f]) and abs(float(r[f]) - ps) < 1e-6:
                flags.append(f"{f} equals a per-share price ${ps}")
    if r["deal_type"] not in ("acquisition",) and isnum(r["upfront_usd_m"]) and float(r["upfront_usd_m"]) >= 3000:
        flags.append("license upfront >= $3bn: check billions/aggregate")
    if isnum(r["total_potential_usd_m"]) and isnum(r["upfront_usd_m"]) and float(r["total_potential_usd_m"]) + 0.01 < float(r["upfront_usd_m"]):
        flags.append("total < upfront")
    if isnum(r["total_potential_usd_m"]) and isnum(r["milestones_usd_m"]) and float(r["total_potential_usd_m"]) + 0.01 < float(r["milestones_usd_m"]):
        flags.append("total < milestones")
    if flags:
        UNIT.append(dict(deal_id=r["deal_id"], status=r["verify_status"], flags=" | ".join(flags), quote=q[:200]))
        if r["verify_status"] == "unchecked":
            d.at[i, "verify_note"] = (d.at[i, "verify_note"] + "; units: " + " | ".join(flags)).strip("; ")
            if any(x.startswith(("total < upfront", "total < milestones")) for x in flags):
                d.at[i, "total_potential_usd_m"] = ""
                d.at[i, "verify_note"] += " (total blanked)"
            if any("non-USD dollars" in x for x in flags) or any("per-share" in x for x in flags):
                d.at[i, "verify_status"] = "dropped"
                d.at[i, "verify_note"] += " (dropped: unit error)"

# ------------------------------------------------------------------ 6. duplicates across the whole table
SUF = r"\b(inc|incorporated|ltd|limited|corp|corporation|plc|co|company|sa|ag|nv|n\.v|se|llc|gmbh|a/s|ab|kgaa|holdings?|group|the|" \
      r"therapeutics|pharmaceuticals?|pharma|biosciences|bioscience|biopharma|biopharmaceuticals?|biotherapeutics|biotech|biologics|" \
      r"medicines|sciences|oncology|international|global|us|usa)\b"
BIG = {"pfizer", "merck", "gilead", "amgen", "abbvie", "lilly", "eli", "novartis", "roche", "genentech", "sanofi", "gsk", "astrazeneca", "takeda",
       "bristol", "myers", "squibb", "bms", "johnson", "janssen", "novo", "nordisk", "bayer", "biogen", "vertex", "regeneron", "otsuka", "astellas",
       "boehringer", "ingelheim", "daiichi", "sankyo", "jazz", "ono", "kyowa", "kirin"}


STOP = set("""exchange commission december january february march april may june july august september october november section drug
administration under terms agreement agreements company license licensee licensor collaboration upfront payment payments million billion
milestone milestones royalty royalties the and with for from our we us this that inc ltd corp corporation plc pharmaceuticals therapeutics
biosciences pharma biopharma holdings group global international item note part form current report press release financial results
announces announced today exhibit about forward looking statements statement sales product products united states america europe china
japan greater phase clinical development regulatory commercial net purchase asset assets acquisition merger offer transaction closing
pursuant upon also eligible receive received paid pay will would which their such certain other additional total aggregate potential
food administration fda nasdaq nyse new york boston cambridge san diego francisco south city calif mass research option options rights
worldwide exclusive program programs common stock shares share equity investment business update extended cash runway subsidiary
accounting standards codification directors officers chief executive officer president limited llc gmbh trust fund partners acquire
acquired development-stage healthcare health medical medicine medicines biotech bio sciences oncology science nan none bank citibank""".split())


def toks(s, caps=True):
    s = str(s or "").replace("’", "'")
    words = re.findall(r"[A-Za-z][A-Za-z0-9\-]{3,}", s)
    out = set()
    for w in words:
        if caps and not w[0].isupper():
            continue
        lw = w.lower()
        if lw in STOP or lw in BIG:
            continue
        out.add(lw)
    return out


def toks_all(s):
    s = str(s or "").replace("\u2019", "'")
    return {w.lower() for w in re.findall(r"[A-Z][A-Za-z0-9\-]{2,}", s) if w.lower() not in STOP}


def d2(s):
    y, m, dd = map(int, str(s)[:10].split("-"))
    return date(y, m, dd)


live = d[d.verify_status != "dropped"].copy()
rows = []
for _, r in live.iterrows():
    pt = toks(r["acquirer_or_licensee"]) | toks(r["target_or_licensor"])
    qt = toks(r["quote"])
    rows.append(dict(id=r["deal_id"], date=d2(r["date"]), up=float(r["upfront_usd_m"]) if isnum(r["upfront_usd_m"]) else None,
                     tot=float(r["total_potential_usd_m"]) if isnum(r["total_potential_usd_m"]) else None,
                     ms=float(r["milestones_usd_m"]) if isnum(r["milestones_usd_m"]) else None, pt=pt, qt=qt,
                     origin=str(r["origin"]), judged=r["deal_id"] in J, typ=r["deal_type"],
                     allt=toks_all(r["acquirer_or_licensee"]) | toks_all(r["target_or_licensor"]) | toks_all(r["quote"])))


def close(a, b, tol=0.01):
    return a is not None and b is not None and abs(a - b) <= max(0.05, tol * max(a, b))


pairs = []
for x in range(len(rows)):
    a = rows[x]
    for y in range(x + 1, len(rows)):
        b = rows[y]
        days = abs((a["date"] - b["date"]).days)
        if days > 1500:
            continue
        ov = (a["pt"] & (b["pt"] | b["qt"])) | (b["pt"] & (a["pt"] | a["qt"]))
        ov_small = ov or ((a["qt"] & b["qt"]) if (close(a["tot"], b["tot"], 0.02) and close(a["up"], b["up"])) else set())
        reason = None
        if days <= 30 and (a["pt"] & b["pt"]) and (close(a["up"], b["up"], 0.05) or close(a["tot"], b["tot"], 0.05)):
            reason = "same counterparty within 30 days"
        elif a["up"] is not None and a["up"] >= 1 and close(a["up"], b["up"]) and days <= 400 and ov_small and \
                (a["tot"] is None or b["tot"] is None or close(a["tot"], b["tot"], 0.05) or "10k_note" in (a["origin"] + b["origin"])):
            reason = "same upfront within 400 days, overlapping parties"
        elif a["up"] is not None and a["up"] >= 5 and close(a["up"], b["up"]) and ov_small and \
                ("10k_note" == a["origin"] or "10k_note" == b["origin"]):
            reason = "10-K restatement: same upfront and party within 1500 days"
        elif days == 0 and close(a["up"], b["up"]) and close(a["tot"], b["tot"]) and (a["up"] or a["tot"]):
            reason = "exact duplicate same day"
        if reason and reason != "exact duplicate same day":
            shared = a["allt"] & b["allt"]
            oa, ob = a["allt"] - shared, b["allt"] - shared
            # veto: each side names a different big-pharma counterparty
            if (oa & BIG) and (ob & BIG) and not (a["allt"] & b["allt"] & BIG):
                reason = None
        if reason:
            pairs.append((a["id"], b["id"], reason, days, " ".join(sorted(ov))[:60]))
# greedy pairwise merge (no transitive chains): strongest evidence first
RANK = {"exact duplicate same day": 0, "same counterparty within 30 days": 1, "same upfront within 400 days, overlapping parties": 2,
        "10-K restatement: same upfront and party within 1500 days": 3}
rinfo = {r["id"]: r for r in rows}
pri = {"edgar_8k": 0, "edgar_8k+own_8k": 0, "edgar_8k+10k_note": 0, "own_8k": 1, "10k_note": 2}
dead = set()
dup_rows = []
for a, b, why, days, ov in sorted(pairs, key=lambda p: (RANK[p[2]], p[3])):
    if a in dead or b in dead:
        continue
    keep, k = sorted([a, b], key=lambda x: (not rinfo[x]["judged"], pri.get(rinfo[x]["origin"], 3), rinfo[x]["date"], x))
    dead.add(k)
    i = idx[k]
    both_judged = rinfo[k]["judged"] and rinfo[keep]["judged"]
    d.at[i, "verify_status"] = "dropped"
    d.at[i, "verify_note"] = (f"duplicate of {keep} ({why}; shared: {ov})" + ("; was hand-checked" if rinfo[k]["judged"] else "")).strip()
    dup_rows.append(dict(kept=keep, dropped=k, reason=why, shared_tokens=ov, days_apart=days, kept_date=str(rinfo[keep]["date"]),
                         dropped_date=str(rinfo[k]["date"]), kept_origin=rinfo[keep]["origin"], dropped_origin=rinfo[k]["origin"],
                         upfront_kept=rinfo[keep]["up"], upfront_dropped=rinfo[k]["up"], total_kept=rinfo[keep]["tot"],
                         total_dropped=rinfo[k]["tot"], both_hand_checked=int(both_judged), source="auto pass"))
# hand-identified duplicates
for k, jd in J.items():
    if jd["dup"] and k in idx:
        dup_rows.append(dict(kept=jd["dup"], dropped=k, reason="hand-checked: " + jd["note"], kept_date=str(orig.at[idx[jd["dup"]], "date"]) if jd["dup"] in idx else "",
                             dropped_date=str(orig.at[idx[k], "date"]), kept_origin=orig.at[idx[jd["dup"]], "origin"] if jd["dup"] in idx else "",
                             dropped_origin=orig.at[idx[k], "origin"], upfront_kept="", upfront_dropped=orig.at[idx[k], "upfront_usd_m"],
                             total_kept="", total_dropped=orig.at[idx[k], "total_potential_usd_m"], both_hand_checked=1, source="hand"))

# ------------------------------------------------------------------ 7. price to revenue (24 rows)
PR = {  # deal_id: (keep, revenue_usd_m, note)
    "D0380": (0, None, "revenue sentence is the acquirer's (Pacira EXPAREL) quarterly sales; deal value $500m is a CVR threshold"),
    "D0381": (0, None, "GOCOVRI $150m is a CVR sales threshold, not trailing revenue"),
    "D0405": (0, None, "$17.5m is a milestone; target is pre-revenue"),
    "D0528": (0, None, "$275m is SpinCo capitalization; deal value was Biohaven debt payoff"),
    "D0554": (0, None, "TYMLOS $300m is a CVR threshold"),
    "D0588": (0, None, "termination fee row; $5.4m is one quarter of TAVNEOS sales"),
    "D0635": (0, None, "$3.7bn is a CVR threshold; Abiomed is a device company"),
    "D0700": (0, None, "$21.6m is a CVR revenue threshold for TYRVAYA"),
    "D0706": (1, 24.0, "Albireo guided FY2022 Bylvay revenue $24m, the year ending at signing (Jan 2023); closest available trailing figure"),
    "D0749": (0, None, "$2.2bn is Seagen's 2023 forecast (forward); row is the termination fee"),
    "D0795": (0, None, "three-year forward revenue in a fairness opinion"),
    "D0838": (0, None, "$15m is a CVR clinical milestone"),
    "D1044": (0, None, "$45m is a royalty cap; row is a bridge loan"),
    "D1085": (0, None, "$3m is an upfront license payment"),
    "D1355": (1, 479.0, "Ayvakit net revenues $479m in 2024 (last fiscal year before the June 2025 deal)"),
    "D1361": (0, None, "ZURZUVAE $250m is a CVR threshold"),
    "D1440": (0, None, "$8.0m is a milestone"),
    "D1535": (0, None, "no target revenue sentence; matched number is not revenue"),
    "D1547": (0, None, "SYFOVRE $1.5bn is a CVR threshold"),
    "D1548": (1, 190.0, "VYKAT XR $190m 2025 revenue (trailing fiscal year before the April 2026 deal)"),
    "D1570": (0, None, "royalty purchase proceeds, not revenue"),
    "D1585": (0, None, "$950m is a CVR threshold"),
    "D1587": (0, None, "CVR threshold table"),
    "D1608": (1, 746.0, "Pacira LTM total revenue $746m (twelve months ended June 30, 2026)"),
}
old_b = pd.read_csv(OUT / "tables" / "deal_benchmarks.csv")
pr_ids = old_b[old_b.metric == "price_to_trailing_revenue_x"].row_ids.iloc[0].split()
pr_rows = []
for k in pr_ids:
    keep, rev, note = PR[k]
    i = idx[k]
    val = d.at[i, "total_potential_usd_m"]
    val = float(val) if isnum(val) and val != "" else None
    pr_rows.append(dict(deal_id=k, date=orig.at[i, "date"], deal_value_usd_m=val, collector_multiple=None, trailing_revenue_usd_m=rev,
                        multiple_x=round(val / rev, 2) if keep and val and rev else "", keep=keep, note=note,
                        row_status=d.at[i, "verify_status"], source_row=orig.at[i, "source_row"]))
# collector multiples for before/after
for pr in pr_rows:
    pass

# ------------------------------------------------------------------ 8. benchmarks rebuild
def royalty_pct(t):
    if not isinstance(t, str) or not t:
        return None
    ns = [float(a or b) for a, b in re.findall(r"(\d+(?:\.\d+)?)\s?%|(\d+(?:\.\d+)?) percent", t)]
    ns = [x for x in ns if 0 < x <= 50]
    if ns:
        return (min(ns) + max(ns)) / 2
    tl = t.lower()
    for k, v in (("low double-digit", 12), ("mid double-digit", 15), ("high double-digit", 20), ("double-digit", 15), ("low single-digit", 3),
                 ("mid single-digit", 5), ("high single-digit", 8), ("single-digit", 5), ("teens", 15)):
        if k in tl:
            return v
    return None


def quart(v):
    v = sorted(v)
    if len(v) < 2:
        return v[0], v[0], v[0]
    q = statistics.quantiles(v, n=4, method="inclusive")
    return q[0], statistics.median(v), q[2]


def num(x):
    return float(x) if isnum(x) and x != "" else None


B = d.copy()
B["stage_at_deal"] = B["stage_at_deal"].fillna("").astype(str).replace("nan", "")
B["therapeutic_area"] = B["therapeutic_area"].fillna("").astype(str).replace("nan", "").replace("", "unclassified")
ver = B[B.verify_status.isin(["verified", "corrected"])]
alive = B[B.verify_status != "dropped"]
metrics = {"upfront_usd_m": lambda r: num(r["upfront_usd_m"]), "total_potential_usd_m": lambda r: num(r["total_potential_usd_m"]),
           "royalty_pct_mid": lambda r: royalty_pct(r["royalty_terms"])}
old_cell = {(r.segment, r.stage_at_deal, r.therapeutic_area, r.metric): r for r in old_b.itertuples()}
out = []


def cell(segment, stage, ta, metric, vrows, arows, fn):
    vals = [(fn(r), r["deal_id"]) for _, r in vrows.iterrows() if fn(r) is not None]
    allv = [fn(r) for _, r in arows.iterrows() if fn(r) is not None]
    oc = old_cell.get((segment, stage, ta, metric))
    rec = dict(segment=segment, stage_at_deal=stage, therapeutic_area=ta, metric=metric, n=len(allv), verified_n=len(vals),
               q1="", median="", q3="", thin="", median_incl_unchecked=round(statistics.median(allv), 2) if allv else "",
               collector_n=oc.n if oc is not None else "", collector_median=oc.median if oc is not None else "", row_ids="")
    if len(vals) >= 5:
        q1, med, q3 = quart([v for v, _ in vals])
        rec.update(q1=round(q1, 2), median=round(med, 2), q3=round(q3, 2), thin=int(len(vals) < 10), row_ids=" ".join(i for _, i in vals))
    return rec


lic_v = ver[~ver.deal_type.isin(["acquisition", "royalty monetization"])]
lic_a = alive[~alive.deal_type.isin(["acquisition", "royalty monetization"])]
for stage in ["preclinical", "Ph1", "Ph2", "Ph3", "filed", "marketed", ""]:
    sv = lic_v if stage == "" else lic_v[lic_v.stage_at_deal == stage]
    sa = lic_a if stage == "" else lic_a[lic_a.stage_at_deal == stage]
    tas = sorted(set(sv.therapeutic_area) | set(old_b[(old_b.stage_at_deal == (stage or "ALL")) & (old_b.segment != "acquisition")].therapeutic_area) - {"ALL"}) + ["ALL"]
    for ta in tas:
        gv = sv if ta == "ALL" else sv[sv.therapeutic_area == ta]
        ga = sa if ta == "ALL" else sa[sa.therapeutic_area == ta]
        for m, fn in metrics.items():
            out.append(cell("licensing/option/co-dev", stage or "ALL", ta, m, gv, ga, fn))
acq_v = ver[(ver.deal_type == "acquisition") & ver.total_potential_usd_m.map(lambda x: num(x) is not None)]
acq_a = alive[(alive.deal_type == "acquisition") & alive.total_potential_usd_m.map(lambda x: num(x) is not None)]
prv = [p for p in pr_rows if p["keep"]]
pr_rec = dict(segment="acquisition", stage_at_deal="marketed", therapeutic_area="ALL", metric="price_to_trailing_revenue_x", n=len(prv),
              verified_n=len(prv), q1="", median="", q3="", thin="", median_incl_unchecked="",
              collector_n=24, collector_median=old_cell[("acquisition", "marketed", "ALL", "price_to_trailing_revenue_x")].median,
              row_ids=" ".join(p["deal_id"] for p in prv))
if len(prv) >= 1:
    q1, med, q3 = quart([p["multiple_x"] for p in prv])
    pr_rec.update(q1=round(q1, 2), median=round(med, 2), q3=round(q3, 2), thin=int(len(prv) < 10))
out.append(pr_rec)
for stage in ["preclinical", "Ph1", "Ph2", "Ph3", "filed", "marketed", ""]:
    gv = acq_v if stage == "" else acq_v[acq_v.stage_at_deal == stage]
    ga = acq_a if stage == "" else acq_a[acq_a.stage_at_deal == stage]
    out.append(cell("acquisition", stage or "ALL", "ALL", "deal_value_usd_m", gv, ga, lambda r: num(r["total_potential_usd_m"])))
bench = pd.DataFrame(out)
bench_keep = bench[(bench.verified_n >= 5) | (bench.metric == "price_to_trailing_revenue_x")].copy()
bench_keep.loc[bench_keep.metric == "price_to_trailing_revenue_x", "thin"] = "below_min_n" if len(prv) < 5 else bench_keep.loc[bench_keep.metric == "price_to_trailing_revenue_x", "thin"]

# ------------------------------------------------------------------ 9. write everything
VC = list(orig.columns) + ["verify_status", "role_unverified", "verify_note", "quote_on_page", "numbers_on_page"]


import os
DRY = os.environ.get("DRY") == "1"


def W(*a, **k):
    if not DRY:
        write(*a, **k)


def to_csv(df, cols=None):
    buf = io.StringIO()
    df.to_csv(buf, index=False, columns=cols)
    return buf.getvalue()


W(STREAM, "verified/deals/deal_comps.csv", to_csv(d, VC), group="deals", doc_type="table", period="2020-2026", quality="verified",
      source_url="data/moat/tables/deal_comps.csv + hand check against data/moat/deals pages")
W(STREAM, "verified/deals/deal_benchmarks.csv", to_csv(bench_keep), group="deals", doc_type="table", period="2020-2026", quality="verified")
W(STREAM, "verified/deals/duplicates.csv", to_csv(pd.DataFrame(dup_rows)), group="deals", doc_type="table", period="2020-2026", quality="verified")
W(STREAM, "verified/deals/pr_checks.csv", to_csv(pd.DataFrame(pr_rows)), group="deals", doc_type="table", period="2020-2026", quality="verified")
pd.DataFrame(UNIT).to_csv(WORK / "unit_flags.csv", index=False)
pd.DataFrame(dup_rows).to_csv(WORK / "dups_preview.csv", index=False)
d.to_csv(WORK / "comps_preview.csv", index=False)
bench.to_csv(WORK / "bench_all_cells.csv", index=False)
json.dump(dict(role_stats=role_stats, low_rate=low_rate, low_any=low_any, screen_prec=screen_prec, n_pairs=len(pairs),
               n_auto_dups=sum(1 for r in dup_rows if r["source"] == "auto pass")), open(WORK / "stats.json", "w"), indent=1, default=str)
with open(WORK / "errors.jsonl", "w") as fh:
    for e in errors:
        fh.write(json.dumps(e, default=str) + "\n")
print(d.verify_status.value_counts().to_dict())
print("role", role_stats, round(low_rate, 3), round(low_any, 3))
print("screens", screen_prec)
print("dups auto", sum(1 for r in dup_rows if r["source"] == "auto pass"), "hand", sum(1 for r in dup_rows if r["source"] == "hand"))
print("bench cells kept", len(bench_keep), "of", len(bench))

if not DRY:
    with open(OUT / "verify" / "ai_wrong.jsonl", "a") as fh:
        for e in errors:
            fh.write(json.dumps(e, default=str) + "\n")
    g = OUT / "gaps" / "deals.jsonl"
    lines = g.read_text().splitlines()
    seen, keep = set(), []
    for ln in lines:
        key = json.dumps({k: v for k, v in json.loads(ln).items() if k != "at"}, sort_keys=True)
        if key not in seen:
            seen.add(key)
            keep.append(ln)
    g.write_text("\n".join(keep) + "\n")
    print("ai_wrong appended", len(errors), "gaps lines", len(lines), "->", len(keep))
