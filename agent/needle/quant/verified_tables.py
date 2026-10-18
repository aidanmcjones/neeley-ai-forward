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
  rx/partb_providers_by_drug.csv, rx/open_payments_by_drug.csv,
  rx/open_payments_physicians.csv   kill-signal baselines (kill.py)
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


# ------------------------------------------------------------------ new-indication timing (M3)
TIMING = "costs/new_indication_timing_summary.csv"
TIMING_TA = {"metabolic": "cardiometabolic", "cardiovascular": "cardiometabolic", "endocrine": "cardiometabolic",
             "cardiometabolic": "cardiometabolic", "oncology": "oncology", "immunology": "immunology",
             "autoimmune": "immunology", "dermatology": "immunology", "rare disease": "rare_disease"}


def _timing_cell(group, metric):
    hit = cell(TIMING, {"group": group, "metric": metric}, "median")
    if hit and _num(hit[0]) is not None and int(_num(hit[3].get("n")) or 0) >= 5:
        return float(hit[0]), hit[1], hit[2], hit[3]
    return None


def indication_timing(ta, name):
    """M3 timing from the verified new-indication timing summary (pivotal_confirmed rows only, built by the scraper
    from new_indication_benchmarks.csv): trial_months / readout_month = median months from pivotal start to primary
    completion; approval_month = that plus the median months from completion to approval. The therapeutic-area row
    is used when it has n >= 5, else the overall row. Values are rounded to whole months (derived entries)."""
    grp = TIMING_TA.get(str(ta or "").lower())
    groups = ([f"ta:{grp}"] if grp else []) + ["overall"]
    for g in groups:
        s2c = _timing_cell(g, "months_start_to_completion")
        c2a = _timing_cell(g, "months_completion_to_approval")
        if not s2c or not c2a:
            continue
        if name in ("trial_months", "readout_month"):
            v = round(s2c[0])
            d = {name: derived_entry(v, "round(a)", {"a": (s2c[0], s2c[1])}, "months")}
            return TableValue(v, [s2c[1]], _label(TIMING, s2c[2], f"{g} median start to primary completion "
                                                                     f"{s2c[0]:g} months, n {s2c[3].get('n')}"),
                              TIMING, s2c[2], d)
        if name == "approval_month":
            v = round(s2c[0] + c2a[0])
            d = {name: derived_entry(v, "round(a + b)", {"a": (s2c[0], s2c[1]), "b": (c2a[0], c2a[1])}, "months")}
            return TableValue(v, [s2c[1], c2a[1]], _label(TIMING, f"{s2c[2]} + {c2a[2]}",
                                                          f"{g} median start to completion {s2c[0]:g} + completion to "
                                                          f"approval {c2a[0]:g} months"), TIMING, s2c[2], d)
    return None


# ------------------------------------------------------------------ LOE
LOE = "pipeline/loe_calendar.csv"


_MONTHS = {m: i for i, m in enumerate(("jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov",
                                        "dec"), 1)}


def _parse_loe(v):
    """A loe_calendar date: '2028', '2028-11-22', '11/22/2028', 'May 2026' (month kept), else None."""
    s = str(v or "")
    m = re.search(r"\b([A-Za-z]{3})[a-z]*\.?\s+(\d{1,2}),\s*(\d{4})", s)
    if m and m.group(1).lower() in _MONTHS:
        return date(int(m.group(3)), _MONTHS[m.group(1).lower()], int(m.group(2)))
    m = re.search(r"(\d{4})-(\d{2})-(\d{2})", s)
    if m:
        return date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
    m = re.search(r"(\d{1,2})/(\d{1,2})/(\d{4})", s)
    if m:
        return date(int(m.group(3)), int(m.group(1)), int(m.group(2)))
    m = re.search(r"\b([A-Za-z]{3})[a-z]*\.?\s+(\d{4})", s)
    if m and m.group(1).lower() in _MONTHS:
        return date(int(m.group(2)), _MONTHS[m.group(1).lower()], 1)
    m = re.search(r"(\d{4})", s)
    return date(int(m.group(1)), 1, 1) if m else None


_DATE_RX = r"(?:January|February|March|April|May|June|July|August|September|October|November|December) \d{1,2}, 20\d\d"


def settlement(ticker, brand, territory="US"):
    """(date, TableValue, row) for a patent-settlement generic entry date: a loe_calendar settlement row for the brand
    (adult or full dose, not the pediatric strength), else a sentence in the company's latest 10-Q or 10-K that says
    generics may launch the brand on a dated day under a settlement (Vyndamax: June 1, 2031, PFE 10-Q Q2 2026).
    Settlement dates are company-stated contract dates, read before the patent table year. None when not found."""
    b = str(brand or "").lower().split(" ")[0]
    if not b:
        return None
    for rk, vs, r in find_rows(LOE, {"ticker": ticker, "territory": territory}):
        name = str(r.get("brand") or "").lower()
        if not name.startswith(b) or "settlement" not in name or "pediatric" in name:
            continue
        v = r.get("company_stated_loe")
        if not re.search(_DATE_RX, str(v or "")):
            continue
        c = DATA.fact_row_citation(LOE, "company_stated_loe", v, row_key=rk)
        if c.verification.ok:
            d = _parse_loe(v)
            return d, TableValue(float(d.year), [c], _label(LOE, rk, f"settlement entry date {v}"), LOE, rk), r
    from agent.needle.cite.locator import Citation
    from agent.needle.cite.verify import verify as _verify
    idx = DATA.index()
    rows = DATA.db().execute("SELECT doc_id FROM docs WHERE ticker = ? AND doc_type IN ('quarterly_report', "
                             "'annual_report') ORDER BY filed DESC LIMIT 3", (ticker,)).fetchall()
    for (doc_id,) in rows:
        for n, (_, text) in idx.pages(doc_id).items():
            flat = " ".join(text.replace("\u200b", " ").split())
            for sent in re.split(r"(?<=[.;])\s+", flat):
                if not re.search(r"\b" + re.escape(b) + r"\b", sent, re.I) or not re.search(r"generic", sent, re.I):
                    continue
                if not re.search(r"settle|terms of the settlements|under the agreements", sent, re.I):
                    continue
                m = re.search(r"(?:launch|market|entry)[^.]{0,120}?(" + _DATE_RX + ")", sent)
                if not m or len(sent) > 500:
                    continue
                c = _verify(Citation(canonical_id=doc_id, page=n, quote=sent, claim_type="quote"), idx)
                if c.verification.ok:
                    d = _parse_loe(m.group(1))
                    return d, TableValue(float(d.year), [c], f"company filing {doc_id} p. {n}: settlement generic "
                                         f"entry {m.group(1)}", "filing", f"{doc_id}#p{n}"), {"ticker": ticker,
                                         "brand": brand, "company_stated_loe": m.group(1), "tenk_page": n}
    return None


def loe(ticker, brand, territory="US"):
    """(date, TableValue for the year, row): a settlement generic entry date first (settlement()), then
    pipeline/loe_calendar.csv company_stated_loe (10-K page in tenk_page; a bare year takes the Orange/Purple Book
    rule date when that date falls in the same year), else rule_output_loe. Never a labels_table (Orange/Purple
    Book max incl. orphan exclusivity) date. None when no passing row."""
    got = settlement(ticker, brand, territory) if territory == "US" else None
    if got:
        return got
    for fld in ("company_stated_loe", "rule_output_loe"):
        hit = cell(LOE, {"ticker": ticker, "brand": str(brand).upper(), "territory": territory}, fld)
        if not hit:
            continue
        v, c, rk, r = hit
        d = _parse_loe(v)
        if d is None:
            continue
        rule = _parse_loe(r.get("rule_output_loe")) if fld == "company_stated_loe" else None
        extra_c = []
        if rule and re.fullmatch(r"\s*\d{4}\s*", str(v)) and rule.year == d.year:
            rc = DATA.fact_row_citation(LOE, "rule_output_loe", r.get("rule_output_loe"), row_key=rk)
            if rc.verification.ok:   # company year 2027 + Orange Book rule date 2027-09-05: keep the dated day
                d, extra_c = rule, [rc]
        page = r.get("tenk_page")
        extra = (f"{fld} {v}" + (f", 10-K page {int(float(page))}" if _num(page) else "")
                 + (f"; rule {r.get('rule_output_loe')} ({r.get('rule_method')})" if r.get("rule_output_loe") else ""))
        return d, TableValue(float(d.year), [c] + extra_c, _label(LOE, rk, extra), LOE, rk), r
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
                                             {"y": {"value": d.year, "citation": tv.citations[0], "year": True}})}
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
    out.update(physician_breadth(d))
    return out


OP_PHYS = "rx/open_payments_physicians.csv"


def physician_breadth(drug):
    """{"physician_breadth": (value, [Citation, ...], text)} from the latest program year whose three counts all pass.
    The text carries the paid-relationship vs light-touch split and the row's verify_status (also in each citation
    note). No row for the drug: empty, and the kill table shows the labelled research-threshold fallback."""
    flds = ("n_physicians_distinct", "n_physicians_consulting_or_speaking", "n_physicians_no_consulting_or_speaking")
    rows = [x for x in find_rows(OP_PHYS, {"drug": drug}) if all(_num(x[2].get(f)) is not None for f in flds)]
    rows.sort(key=lambda x: str(x[2].get("program_year")), reverse=True)
    for rk, vs, r in rows:
        cs = [DATA.fact_row_citation(OP_PHYS, f, r[f], row_key=rk) for f in flds]
        if all(c.verification.ok for c in cs):
            n, paid, light = (float(r[f]) for f in flds)
            return {"physician_breadth": (n, cs, f"Open Payments {n:,.0f} distinct physicians (PY{r['program_year']}): "
                                                 f"{paid:,.0f} paid relationships (consulting, speaking), {light:,.0f} "
                                                 f"light-touch only; {r.get('verify_status') or vs}")}
    return {}
