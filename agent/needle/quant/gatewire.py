"""Derived and assumption maps for the numeric gate (docs/gate_wiring.md, agent.needle.cite.gate).

Every number FIND prints in a finding's sentence or impact formula must be verified by a passing citation, re-computed
from cited operands (a `derived` entry), or carry an assumption label. This module builds those maps:

  company_maps(co, derived, assumptions)      Rev_TTM, t, D (the EPS translation constants of section 4.2)
  const(assumptions, name, values, desc)      model constants (pi, H, weights): label "constant: <name> (...)"
  pct_operand(cite, pct)                      a cited percent as an operand ("65%" on the CMS page -> 0.65)
  forensics_maps(sig, derived, assumptions)   XBRL-derived detector statistics (ETR, DSO, DIO, margin, R&D share)
  peer_stats(assumptions, sig)                peer median and z over the shortlist panel: labelled, not page-cited

Census rule (docs/citations.md): a number whose label starts with "constant: " is a model constant (weights.py), not
a fact about the company; the census reports it under "assumed" and counts it separately as "constants".
"""

import re

from agent.needle.cite.gate import derived_entry

from . import data
from . import weights as W

CONSTANT = "constant: "
PEER_LABEL = "shortlist peer panel statistic (median / robust z over the 10 shortlist companies, computed by code " \
             "from XBRL; not page-cited)"


def _vals(values):
    if isinstance(values, (tuple, list)):
        out = []
        for v in values:
            out += _vals(v)
        return out
    return [values]


def const(assumptions, name, values, desc=""):
    """Label each value in `values` (scalar or nested tuple) as the model constant `name`."""
    label = f"{CONSTANT}{name}" + (f" ({desc})" if desc else "")
    for v in _vals(values):
        if v is None:
            continue
        assumptions[f"{name}={v!r}"] = {"value": f"{float(v):.12g}", "label": label}
    return assumptions


def assume(assumptions, key, value, label, unit=""):
    assumptions[key] = {"value": f"{float(value):.12g}", "label": label, "unit": unit}
    return assumptions


def identity(derived, key, value, cite, unit=""):
    """A printed rounding of one cited value ('38,095.0' from the operand citation '38,095')."""
    derived[key] = derived_entry(value, "a", {"a": data.gate_operand(cite, derived, value)}, unit)
    return derived


def company_maps(co, derived, assumptions):
    """Rev_TTM, t and D as derived entries over their XBRL operands; the peer-median ETR fallback is labelled."""
    rv = co.citations.get("Rev_TTM", [])
    if len(rv) == 4:
        derived["Rev_TTM"] = derived_entry(co.rev_ttm, "q1 + q2 + q3 + q4",
                                           {f"q{i}": data.gate_operand(c, derived) for i, c in enumerate(rv, 1)})
    elif len(rv) == 1:
        identity(derived, "Rev_TTM", co.rev_ttm, rv[0])
    tc = co.citations.get("t", [])
    if len(tc) == 8:
        ops = {f"x{i}": data.gate_operand(c, derived) for i, c in enumerate(tc[:4], 1)}
        ops.update({f"p{i}": data.gate_operand(c, derived) for i, c in enumerate(tc[4:], 1)})
        derived["t"] = derived_entry(co.tax, "(x1 + x2 + x3 + x4) / (p1 + p2 + p3 + p4)", ops)
    elif len(tc) == 2:
        derived["t"] = derived_entry(co.tax, "x / p", {"x": data.gate_operand(tc[0], derived),
                                                      "p": data.gate_operand(tc[1], derived)})
    elif "t_raw" in co.citations:
        assume(assumptions, "t", co.tax, "peer median TTM GAAP ETR (fallback rule of section 4.2: the company's own "
                                         "TTM ETR lies outside [0, 0.40]); computed by code over the shortlist panel")
    dc = co.citations.get("D", [])
    if dc:
        identity(derived, "D", co.shares, dc[0])
    return derived, assumptions


def pct_operand(cite, pct):
    """Operand dict for a percent printed on a cited page ('65%'), so 'd 0.65' derives as p / 100."""
    return {"value": pct, "citation": cite, "text": f"{pct:g}%"}


def find_pct_cite(cites, pct):
    """The first passing citation whose quote prints pct as a percent ('65%')."""
    pat = re.compile(rf"(?<![\d.]){re.escape(f'{pct:g}')}\s?%")
    for c in cites:
        if c is not None and c.verification.ok and pat.search(c.quote or ""):
            return c
    return None


# ------------------------------------------------------------------ forensics detector statistics
_STOCK = {"inventory", "receivables", "assets"}


def _xcite(ticker, p, col, q, annual):
    """XBRL citation of one panel value (USD millions), or None."""
    from agent.needle import xbrl
    t = xbrl.annual(ticker) if annual else p
    key = q if not annual else q[:4]
    try:
        v = float(t.at[key, col])
    except Exception:
        return None
    if v != v:
        return None
    cur = (p.attrs.get("units", {}).get(col) or ["USD"])[0]
    unit = f"{cur} millions"
    if col in _STOCK:
        frame = f"CY{key}Q4I" if annual else f"CY{key}I"
        return data.xbrl_citation(ticker, data._concept(p, col, key), frame, v / 1e6, unit)
    if annual:
        return data.xbrl_citation(ticker, data._concept(p, col, key), f"CY{key}", v / 1e6, unit)
    return data.flow_citation(ticker, p, col, key, v / 1e6, unit)


FORENSIC_EXPR = {   # metric: (columns, expression for the current value in printed units, unit)
    "etr": (("income_tax", "pretax_income"), "a / b * 100", "%"),
    "gross_margin": (("cogs", "revenue"), "(1 - a / b) * 100", "%"),
    "rnd_pct": (("rnd", "revenue"), "a / b * 100", "%"),
    "dso": (("receivables", "revenue"), "a / (b * m) * 365", ""),
    "dio": (("inventory", "cogs"), "a / (b * m) * 365", ""),
    "impairment_pct": (("impairment", "assets"), "a / b * 100", "%"),
}
KIND_METRIC = {"tax_rate_shift": "etr", "etr_peer_outlier": "etr", "gross_margin_drop": "gross_margin",
               "gross_margin_peer_outlier": "gross_margin", "rnd_shift": "rnd_pct", "rnd_pct_peer_outlier": "rnd_pct",
               "dso_rising": "dso", "dso_peer_outlier": "dso", "dio_rising": "dio", "dio_peer_outlier": "dio",
               "impairment": "impairment_pct"}


def _metric_entry(ticker, p, metric, q, annual, derived, tag):
    """Derived-entry key for one metric value at period q, or None when an operand is missing."""
    cols, expr, unit = FORENSIC_EXPR[metric]
    ca, cb = _xcite(ticker, p, cols[0], q, annual), _xcite(ticker, p, cols[1], q, annual)
    if ca is None or cb is None:
        return None
    from agent.needle import xbrl
    t = xbrl.annual(ticker) if annual else p
    key_q = q[:4] if annual else q
    av, bv = float(t.at[key_q, cols[0]]) / 1e6, float(t.at[key_q, cols[1]]) / 1e6
    m = 1 if annual else 4
    from agent.needle.cite.gate import safe_eval
    val = safe_eval(expr, {"a": av, "b": bv, "m": m})
    ops = {"a": data.gate_operand(ca, derived, av), "b": data.gate_operand(cb, derived, bv)}
    if "m" in expr:
        ops["m"] = {"value": m, "assumption": "constant: quarters per year (annualization of a quarterly flow)"}
    key = f"{tag}_{metric}_{q}"
    derived[key] = derived_entry(val, expr, ops, unit)
    return key


def forensics_maps(sig, derived, assumptions):
    """Derived entries for a forensics row's current and prior-year metric, their change, and the peer statistics."""
    metric = KIND_METRIC.get(sig.kind)
    if sig.detector != "forensics" or metric is None:
        return derived, assumptions
    from agent.needle import xbrl
    from agent.needle.detect.forensics import ANNUAL_ONLY
    per = str(sig.period or "")
    annual = sig.ticker in ANNUAL_ONLY or bool(re.fullmatch(r"\d{4}", per))
    try:
        p = xbrl.panel(sig.ticker)
    except Exception:
        return derived, assumptions
    prev = f"{int(per[:4]) - 1}{per[4:]}"
    k_now = _metric_entry(sig.ticker, p, metric, per, annual, derived, "now")
    k_prev = _metric_entry(sig.ticker, p, metric, prev, annual, derived, "prev") if metric != "impairment_pct" else None
    if k_now and k_prev:
        unit = FORENSIC_EXPR[metric][2]
        a, b = derived[k_now]["value"], derived[k_prev]["value"]
        if unit == "%":
            derived[f"chg_{metric}"] = derived_entry(a - b, "a - b", {"a": {"derived": k_now}, "b": {"derived": k_prev}},
                                                     "pts")
        else:
            derived[f"chg_{metric}"] = derived_entry((a / b - 1) * 100, "(a / b - 1) * 100",
                                                     {"a": {"derived": k_now}, "b": {"derived": k_prev}}, "%")
    peer_stats(assumptions, sig)
    return derived, assumptions


def peer_stats(assumptions, sig):
    """Peer median and z: computed by code over the shortlist peer panel; labelled, never page-cited."""
    metric = KIND_METRIC.get(sig.kind) or ""
    if sig.peer_median is not None:
        med = sig.peer_median
        if metric in ("dso", "dio"):
            assume(assumptions, "peer_median", med, PEER_LABEL)
        elif sig.kind in ("rec_gap_peer_outlier", "inv_gap_peer_outlier", "receivables_outpace_revenue",
                          "inventory_outpaces_revenue"):
            assume(assumptions, "peer_median", med * 100, PEER_LABEL, "pts")
        else:
            assume(assumptions, "peer_median", med * 100, PEER_LABEL, "%")
    if sig.peer_z is not None:
        assume(assumptions, "peer_z", sig.peer_z, PEER_LABEL)
    return assumptions


def channel_constants(imp, assumptions):
    """Model constants (weights.py) an impact formula prints."""
    ch = imp.channel
    if ch == "anchor":
        const(assumptions, "ANCHOR", W.ANCHOR, "generic anchor placeholder: 3% margin event, backtest margin_drop")
    if ch == "ira":
        const(assumptions, "K_NET", W.K_NET, "KQ2 cross-check: net hit 0.3-0.5 x list discount, rebated classes")
        const(assumptions, "M_MDP_AVOIDED", W.M_MDP_AVOIDED, "Part D discount-program liability avoided, CMS MDP "
                                                             "guidance")
        if "low-rebate" in (imp.formula or "") or "low rebate" in (imp.formula or ""):
            const(assumptions, "K_LOW_REBATE", 1.0, "class rule: a low-rebate class passes the full list discount, k = 1")
        if "g_pre" in (imp.formula or ""):
            const(assumptions, "G_PRE_GLP1", W.G_PRE_GLP1, "GLP-1 pre-MFP concession, Drug Channels; inference")
            const(assumptions, "G_PRE_IMMUNOLOGY", W.G_PRE_IMMUNOLOGY, "immunology pre-MFP concession; inference")
            const(assumptions, "M_MDP_CATASTROPHIC", W.M_MDP_CATASTROPHIC, "MDP rate, catastrophic phase")
    if ch == "mfn":
        const(assumptions, "S_MFN", W.S_MFN, "Medicaid MFN share of US revenue: Pfizer base rate range")
    if ch == "loe":
        const(assumptions, "R_BIOLOGIC", W.R_BIOLOGIC, "LOE retention years 1/2/3, KQ4")
        const(assumptions, "R_SMALL_MOLECULE", W.R_SMALL_MOLECULE, "LOE retention years 1/2/3, KQ4")
    return assumptions


# ------------------------------------------------------------------ IRA list discounts
IRA_CUT = "policy/ira_cut_check.csv"


def ira_cut_cite(pct):
    """facts row of policy/ira_cut_check.csv (CMS negotiated-price fact sheets, re-computed and matched) whose
    cms_pct_cut is pct, as a verified fact citation, or None."""
    if float(pct) != int(pct):
        return None
    c = data.fact_row_citation(IRA_CUT, "cms_pct_cut", int(pct), where={"cms_pct_cut": str(int(pct))})
    return c if c.verification.ok else None


def ira_cut_median(derived):
    """Derived entry key for the median of the cycle 1-2 negotiated discounts (percent), from the two middle facts
    rows of policy/ira_cut_check.csv, or None."""
    try:
        rows = data.db().execute('SELECT value FROM facts WHERE "table" = ? AND field = ?', (IRA_CUT, "cms_pct_cut")
                                 ).fetchall()
        vals = sorted(float(r[0]) for r in rows)
    except Exception:
        return None
    n = len(vals)
    if n < 2 or n % 2:
        return None
    a, b = vals[n // 2 - 1], vals[n // 2]
    ca, cb = ira_cut_cite(a), ira_cut_cite(b)
    if ca is None or cb is None:
        return None
    derived["ira_cut_median"] = derived_entry((a + b) / 2, "(a + b) / 2", {"a": (a, ca), "b": (b, cb)}, "%",
                                              label=f"median of the {n} cycle 1-2 negotiated discounts (middle rows "
                                                    f"{a:g}% and {b:g}%)")
    return "ira_cut_median"


def ira_discount_maps(d, analog_cites, derived):
    """Derived entries for each list discount d (decimal) the IRA formula prints: p / 100 over a cited CMS percent
    (the analog quote, else the ira_cut_check facts row), or the median entry. Returns the list of unsupported d."""
    missing = []
    for v in sorted(set(d if isinstance(d, tuple) else (d,))):
        pct = round(v * 100, 1)
        c = find_pct_cite(analog_cites, pct) or ira_cut_cite(pct)
        if c is not None:
            op = pct_operand(c, pct) if c.page is not None else (pct, c)
            derived[f"d_{v:g}"] = derived_entry(v, "p / 100", {"p": op})
            continue
        key = ira_cut_median(derived)
        if key and abs(derived[key]["value"] - pct) < 1e-9:
            derived[f"d_{v:g}"] = derived_entry(v, "m / 100", {"m": {"derived": key}})
            continue
        missing.append(v)
    return missing


_DOSES = re.compile(r"\(([\d.]+)/yr\)")


def dose_counts(sentence, assumptions):
    """Label the '(N/yr)' dose counts of the dosing rows: a unit conversion of the cited label frequency ('once daily'
    = 365, 'every 2 weeks' = 26), computed by code, not a number printed on the label page."""
    for m in _DOSES.finditer(sentence or ""):
        assume(assumptions, f"doses_{m.group(1)}", float(m.group(1)),
               "doses per year implied by the cited label frequency (unit conversion by code: once daily = 365, "
               "weekly = 52, every N weeks = 52 / N)")
    return assumptions


# ------------------------------------------------------------------ label indication counts (count operands)
INDICATION_MAP = "epi/indication_map.csv"


def indication_rows(drug):
    """[(row_key, sub_indication, Citation)] for one drug's epi/indication_map.csv rows, each cited on its DailyMed
    label line (agent.needle.cite.facts.apply_locator: label-section rows resolve to the label page). One entry per
    distinct sub_indication."""
    import json as _json
    try:
        rows = data.db().execute('SELECT row_key, row_json FROM facts WHERE "table" = ? AND lower(drug) = ?',
                                 (INDICATION_MAP, str(drug).lower())).fetchall()
    except Exception:
        return []
    out, seen = [], set()
    for rk, rj in rows:
        if rk in seen:
            continue
        seen.add(rk)
        try:
            sub = _json.loads(rj or "{}").get("sub_indication") or ""
        except ValueError:
            sub = ""
        c = data.fact_row_citation(INDICATION_MAP, "indication", None, row_key=rk)
        out.append((rk, sub, c))
    uniq, keys = [], set()
    for rk, sub, c in out:
        k = re.sub(r"\W+", " ", sub.lower()).strip()
        if k in keys:
            continue
        keys.add(k)
        uniq.append((rk, sub, c))
    return uniq


def indication_count(drug):
    """(n, {operand name: count operand}, [Citation]) for the number of indication rows of a drug, or None when the
    drug has no rows. Every row is an operand (a row whose citation does not pass makes the derivation fail)."""
    rows = indication_rows(drug)
    if not rows:
        return None
    ops = {f"r{i}": {"value": 1, "citation": c, "count": True} for i, (_, _, c) in enumerate(rows)}
    return len(rows), ops, [c for _, _, c in rows if c.verification.ok]
