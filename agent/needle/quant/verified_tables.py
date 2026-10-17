"""The scraper's verified tables as DECIDE and FIND inputs, cited by row through the facts table.

Every value here is read from a facts row of citations.sqlite (the row_json of the table row) and comes with a
Citation from data.fact_row_citation: the value is re-read from the row and its verify_status goes through the
whitelist (agent.needle.cite.facts), and the citation note carries that verify_status. A research-note constant
(moves.REGISTRY) stays as the labelled fallback when a table has no row for the case.

Tables (paths under data/moat/verified/, facts table name = the path):
  deals/deal_benchmarks.csv            stage x metric medians: acquisition deal_value_usd_m (ALL $1,675M n 104,
                                       marketed $1,800M, Ph3 $2,650M), licensing upfront / total_potential, and
                                       royalty_pct_mid used only where n >= 5
  deals/deal_comps.csv                 comps, only rows with verify_status verified or corrected
  costs/cost_ratios.csv                sga, rnd, advertising over revenue by ticker and fiscal year
  costs/trial_cost_benchmarks.csv      ASPE 2014 cost per study by phase and TA; Moore pivotal-trial costs; Sertkaya
                                       2024 per-patient cost and transition success probabilities by TA
  costs/open_payments_by_nature.csv    promotional class only
  costs/launch_and_marketing_benchmarks.csv, costs/pricing_move_benchmarks.csv (verbatim rows, effect_type)
  pipeline/target_profiles.csv         candidate EV with ev_method; a blank debt is the zero-debt caveat
  pipeline/loe_calendar.csv            company_stated_loe (with tenk_page), rule_output_loe, rule_method
  rx/partd_prescribers_by_drug.csv, rx/prescriber_concentration.csv, rx/formulary_history.csv,
  rx/partb_providers_by_drug.csv, rx/open_payments_by_drug.csv   kill-signal baselines (kill.py)
Not used: deals/pr_checks.csv, the timing columns of new_indication_benchmarks.

TableValue(value, citations, derived, label, table, row_key) is what callers consume: `value` in the parameter's
units, `derived` a gate.derived_entry map when the value is computed from the row (percent / 100, a ratio of two
cells, months to a date).
"""

import json
import re
from dataclasses import dataclass, field
from datetime import date
from functools import lru_cache

from agent.needle.cite.gate import derived_entry

from . import data as DATA


@dataclass
class TableValue:
    value: float
    citations: list
    label: str
    table: str
    row_key: str = ""
    derived: dict = field(default_factory=dict)
    note: str = ""


@lru_cache(maxsize=64)
def _rows(table):
    """[(row_key, verify_status, row dict)] for one facts table, one entry per table row."""
    try:
        cur = DATA.db().execute('SELECT row_key, verify_status, row_json FROM facts WHERE "table" = ?', (table,))
    except Exception:
        return ()
    seen, out = set(), []
    for rk, vs, rj in cur.fetchall():
        if rk in seen:
            continue
        seen.add(rk)
        try:
            out.append((rk, vs, json.loads(rj or "{}")))
        except ValueError:
            continue
    return tuple(out)


def _match(row, where):
    for k, v in where.items():
        x = str(row.get(k, "")).strip().lower()
        if isinstance(v, (tuple, list, set)):
            if x not in {str(y).strip().lower() for y in v}:
                return False
        elif x != str(v).strip().lower():
            return False
    return True


def _num(x):
    try:
        v = float(str(x).replace(",", "").replace("$", ""))
        return None if v != v else v
    except (TypeError, ValueError):
        return None


def find_rows(table, where, statuses=None):
    return [(rk, vs, r) for rk, vs, r in _rows(table) if _match(r, where)
            and (statuses is None or str(vs).lower() in statuses)]


def cell(table, where, fld, statuses=None):
    """(value, Citation, row_key, row) for the first matching row whose fact citation passes, else None."""
    for rk, vs, r in find_rows(table, where, statuses):
        v = r.get(fld)
        if v in (None, ""):
            continue
        c = DATA.fact_row_citation(table, fld, v, row_key=rk)
        if c.verification.ok:
            return v, c, rk, r
    return None


def _label(table, rk, extra=""):
    return f"verified table {table} row {rk}" + (f" ({extra})" if extra else "")


# ------------------------------------------------------------------ trial costs and probabilities
ASPE_TA = {"metabolic": "Endocrine", "endocrine": "Endocrine", "oncology": "Oncology", "cardiovascular": "Cardiovascular",
           "neurology": "Central Nervous System", "psychiatry": "Central Nervous System", "dermatology": "Dermatology",
           "infectious disease": "Anti-Infective", "autoimmune": "Immunomodulation", "immunology": "Immunomodulation",
           "gastroenterology": "Gastrointestinal", "respiratory": "Respiratory System", "ophthalmology": "Ophthalmology",
           "urology": "Genitourinary System", "hematology": "Hematology"}
SERTKAYA_TA = {"metabolic": "Endocrine", "endocrine": "Endocrine", "oncology": "Oncology", "cardiovascular": "Cardiovascular",
               "neurology": "Central nervous system", "psychiatry": "Central nervous system", "dermatology": "Dermatology",
               "infectious disease": "Anti-infective", "autoimmune": "Immuno-modulation", "immunology": "Immuno-modulation",
               "gastroenterology": "Gastrointestinal", "respiratory": "Respira-tory system", "hematology": "Hematology",
               "ophthalmology": "Ophthal-mology", "urology": "Genito-urinary system"}
TC = "costs/trial_cost_benchmarks.csv"
MOORE_ROWS = {"trial_cost_placebo": "moore2018|controlled", "trial_cost_active": "moore2018|controlled",
              "trial_cost_median": "moore2018|median"}


def moore(bench):
    sr = MOORE_ROWS.get(bench)
    hit = cell(TC, {"source_row": sr}, "value") if sr else None
    if not hit:
        return None
    v, c, rk, r = hit
    return TableValue(float(v), [c], _label(TC, rk, r.get("metric", "")), TC, rk)


def aspe_phase_cost(ta, phase="Phase 3"):
    t = ASPE_TA.get(str(ta or "").lower())
    hit = cell(TC, {"source_row": f"aspe2014|T1|{t}|{phase}"}, "value") if t else None
    if not hit:
        return None
    v, c, rk, r = hit
    return TableValue(float(v), [c], _label(TC, rk, f"ASPE 2014 {t} {phase} total cost per single study"), TC, rk)


def sertkaya_pos(ta, transition):
    """Transition success probability (fraction) for a TA ('Phase 3 to FDA review', 'FDA review to approval');
    TA 'All' when the TA has no row."""
    for t in (SERTKAYA_TA.get(str(ta or "").lower()), "All"):
        if not t:
            continue
        hit = cell(TC, {"metric": "transition success probability", "phase": transition, "therapeutic_area": t}, "value")
        if hit:
            v, c, rk, r = hit
            p = float(v)
            return TableValue(p / 100, [c], _label(TC, rk, f"Sertkaya 2024 {t} {transition} {p:g}%"), TC, rk,
                              derived={f"pos_{transition}": derived_entry(p / 100, "p / 100", {"p": (p, c)})})
    return None


# ------------------------------------------------------------------ deals
DB_ = "deals/deal_benchmarks.csv"
STAGE = {"ph3": "Ph3", "phase 3": "Ph3", "ph2": "Ph2", "ph1": "Ph1", "preclinical": "preclinical", "nda": "filed",
         "filed": "filed", "approved": "marketed", "marketed": "marketed", "all": "ALL"}


def deal_median(segment, stage, metric, min_n=1):
    st = STAGE.get(str(stage or "all").lower(), "ALL")
    for s in (st, "ALL"):
        hit = cell(DB_, {"segment": segment, "stage_at_deal": s, "therapeutic_area": "ALL", "metric": metric}, "median")
        if hit and (_num(hit[3].get("n")) or 0) >= min_n:
            v, c, rk, r = hit
            return TableValue(float(v), [c], _label(DB_, rk, f"{segment} {s} {metric} median, n {r.get('n')}"), DB_, rk)
    return None


def acquisition_value(stage):
    return deal_median("acquisition", stage, "deal_value_usd_m")


def licensing_total(stage):
    return deal_median("licensing/option/co-dev", stage, "total_potential_usd_m")


def licensing_upfront_share(stage):
    up, tot = deal_median("licensing/option/co-dev", stage, "upfront_usd_m"), licensing_total(stage)
    if not up or not tot:
        return None
    v = up.value / tot.value
    return TableValue(v, up.citations + tot.citations, f"{up.label} / {tot.label}", DB_, f"{up.row_key}/{tot.row_key}",
                      derived={"upfront_share": derived_entry(v, "u / t", {"u": (up.value, up.citations[0]),
                                                                           "t": (tot.value, tot.citations[0])})})


def royalty(stage):
    """Royalty midpoint (fraction) where the cell has n >= 5; None otherwise (research-note fallback)."""
    t = deal_median("licensing/option/co-dev", stage, "royalty_pct_mid", min_n=5)
    if not t:
        return None
    return TableValue(t.value / 100, t.citations, t.label, DB_, t.row_key,
                      derived={"royalty": derived_entry(t.value / 100, "p / 100", {"p": (t.value, t.citations[0])})})


def deal_comps(filter_=None):
    """Verified or corrected deal comps (dict rows)."""
    return [r for _, vs, r in _rows("deals/deal_comps.csv") if str(vs).lower() in ("verified", "corrected")
            and (filter_ is None or filter_(r))]


def target_ev(ticker):
    """Candidate EV from pipeline/target_profiles.csv (ev_method), with the zero-debt caveat when debt is blank."""
    hit = cell("pipeline/target_profiles.csv", {"ticker": ticker}, "enterprise_value")
    if not hit:
        return None
    v, c, rk, r = hit
    note = f"ev_method: {r.get('ev_method')}"
    if r.get("debt") in (None, ""):
        note += "; zero-debt caveat: debt not reported, EV assumes no debt"
    return TableValue(float(v) / 1e6, [c], _label("pipeline/target_profiles.csv", rk, note), "pipeline/target_profiles.csv",
                      rk, derived={"target_ev": derived_entry(float(v) / 1e6, "e / 1000000", {"e": (float(v), c)})},
                      note=note)


# ------------------------------------------------------------------ costs and pricing
def cost_ratio(ticker, ratio, fy=None):
    rows = find_rows("costs/cost_ratios.csv", {"ticker": ticker, "ratio": ratio})
    rows = sorted(rows, key=lambda x: str(x[2].get("fy")), reverse=True)
    for rk, vs, r in rows:
        if fy and str(r.get("fy")) != str(fy):
            continue
        c = DATA.fact_row_citation("costs/cost_ratios.csv", "value_pct", r.get("value_pct"), row_key=rk)
        if c.verification.ok:
            return TableValue(float(r["value_pct"]) / 100, [c], _label("costs/cost_ratios.csv", rk, f"{ratio} FY{r['fy']}"),
                              "costs/cost_ratios.csv", rk)
    return None


def promotional_spend(drug, year=None):
    """USD of promotional-class Open Payments for a drug: costs/open_payments_by_nature.csv promotional rows."""
    rows = [x for x in find_rows("costs/open_payments_by_nature.csv", {"drug": drug})
            if str(x[2].get("class", "")).startswith("promotional") and (year is None or str(x[2].get("program_year")) == str(year))]
    cites, tot = [], 0.0
    for rk, vs, r in rows:
        c = DATA.fact_row_citation("costs/open_payments_by_nature.csv", "usd", r.get("usd"), row_key=rk)
        if c.verification.ok:
            cites.append(c)
            tot += float(r["usd"])
    return TableValue(tot, cites, f"verified table costs/open_payments_by_nature.csv, {len(cites)} promotional rows",
                      "costs/open_payments_by_nature.csv") if cites else None


def pricing_moves(company):
    out = []
    for rk, vs, r in find_rows("costs/pricing_move_benchmarks.csv", {"company": company}):
        c = DATA.fact_row_citation("costs/pricing_move_benchmarks.csv", "magnitude", r.get("magnitude"), row_key=rk)
        if c.verification.ok:
            out.append((r, c))
    return out


# ------------------------------------------------------------------ LOE
LOE = "pipeline/loe_calendar.csv"


def loe(ticker, brand, territory="US"):
    """(date, TableValue for the year, row) from pipeline/loe_calendar.csv: company_stated_loe first (10-K page in
    tenk_page), else rule_output_loe. None when no passing row."""
    for fld in ("company_stated_loe", "rule_output_loe"):
        hit = cell(LOE, {"ticker": ticker, "brand": str(brand).upper(), "territory": territory}, fld)
        if not hit:
            continue
        v, c, rk, r = hit
        m = re.search(r"(\d{4})(?:-(\d{2})-(\d{2}))?", str(v))
        if not m:
            continue
        d = date(int(m.group(1)), int(m.group(2) or 1), int(m.group(3) or 1))
        page = r.get("tenk_page")
        extra = (f"{fld} {v}" + (f", 10-K page {int(float(page))}" if _num(page) else "")
                 + (f"; rule {r.get('rule_output_loe')} ({r.get('rule_method')})" if r.get("rule_output_loe") else ""))
        return d, TableValue(float(m.group(1)), [c], _label(LOE, rk, extra), LOE, rk), r
    return None


def loe_any(brand, territory="US"):
    """loe() for a brand of any company (a rival's own loe_calendar row), or None."""
    for fld in ("company_stated_loe", "rule_output_loe"):
        hit = cell(LOE, {"brand": str(brand).upper(), "territory": territory}, fld)
        if hit:
            return loe(hit[3].get("ticker"), brand, territory)
    return None


def months_to(d, as_of=None):
    a = as_of or DATA.AS_OF
    return (d.year - a.year) * 12 + (d.month - a.month)


def loe_month(ticker, brand):
    got = loe(ticker, brand)
    if not got:
        return None
    d, tv, r = got
    m = months_to(d)
    a = DATA.AS_OF
    tv.derived = {"loe_month": derived_entry(m, f"(y - {a.year}) * 12 + ({d.month} - {a.month})",
                                             {"y": (d.year, tv.citations[0])})}
    tv.value = m
    return tv


# ------------------------------------------------------------------ prescriber baselines (kill.py)
def _latest(table, where, fld, key="year"):
    rows = [x for x in find_rows(table, where) if _num(x[2].get(fld)) is not None]
    rows.sort(key=lambda x: str(x[2].get(key)), reverse=True)
    for rk, vs, r in rows:
        c = DATA.fact_row_citation(table, fld, r[fld], row_key=rk)
        if c.verification.ok:
            return float(r[fld]), c, r
    return None


CONTRACT_YEAR = {"2023Q4": "CY2024", "2025Q4": "CY2026", "2026Q3": "CY2026"}


def rx_baselines(drug):
    """{signal id: (value, Citation, text)} from the chosen product's latest year in the rx tables. Part D PUF data lag
    about 18 months, so these are baselines, not month-6 observations."""
    d = str(drug or "").lower()
    out = {}
    hit = _latest("rx/partd_prescribers_by_drug.csv", {"drug": d}, "prescribers_all_cms")
    if hit:
        v, c, r = hit
        out["zs_breadth"] = (v, c, f"Part D prescribers {v:,.0f} ({r['year']}, all CMS)")
    else:
        hit = _latest("rx/partb_providers_by_drug.csv", {"drug": d, "level": "total"}, "providers")
        if hit:
            v, c, r = hit
            out["zs_breadth"] = (v, c, f"Part B providers {v:,.0f} ({r['year']})")
    hit = _latest("rx/prescriber_concentration.csv", {"drug": d}, "prescriber_growth_yoy_all_cms")
    if hit:
        v, c, r = hit
        out["zs_return_writing"] = (v, c, f"prescriber growth YoY {v:+.1%} ({r['year']}, all CMS)")
    hit = _latest("rx/prescriber_concentration.csv", {"drug": d}, "top20pct_share_all_prescribers")
    if hit:
        v, c, r = hit
        out["zs_depth"] = (v, c, f"top 20% of prescribers write {v:.1%} of claims in {r['year']}")
    rows = [x for x in find_rows("rx/formulary_history.csv", {"drug": d, "rxcui_link": "brand"})
            if _num(x[2].get("coverage_share")) is not None]
    rows.sort(key=lambda x: str(x[2].get("quarter")), reverse=True)
    for rk, vs, r in rows:
        c = DATA.fact_row_citation("rx/formulary_history.csv", "coverage_share", r["coverage_share"], row_key=rk)
        if c.verification.ok:
            cy = r.get("contract_year") or CONTRACT_YEAR.get(str(r.get("quarter")), "")
            out["coverage"] = (float(r["coverage_share"]), c, f"Part D formulary coverage {float(r['coverage_share']):.1%} "
                                                              f"({r['quarter']} release, {cy})")
            break
    else:
        pb = [x for x in find_rows("rx/formulary_history.csv", {"drug": d}) if str(x[2].get("part_b_drug")).lower() == "true"]
        if pb:
            out["coverage_note"] = (None, None, "Part B drug: blank Part D coverage is not 'uncovered'")
    hit = _latest("rx/open_payments_by_drug.csv", {"drug": d}, "usd_promotional", key="program_year")
    if hit:
        v, c, r = hit
        out["promotional"] = (v, c, f"Open Payments promotional ${v:,.0f} (PY{r['program_year']})")
    return out
