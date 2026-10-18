"""Peer comparison for every findings-table row (case: "how the same item looks at another shortlist company or a
rival product's maker"). Each comparison is a gated claim: its numbers are verified by a citation, derived from cited
operands (XBRL companyfacts frames, CMS pages, loe_calendar rows) or labelled. Where no comparable disclosure exists
the row says so and gives the reason.

  forensics metric rows   the same metric (ETR, gross margin, R&D share, DSO, DIO, impairment share) for every
                          shortlist company from XBRL; the median is derived from the cited per-company values and the
                          nearest named peer is printed with its value (receivables and inventory gap rows use DSO and
                          DIO, the level form of the same item)
  IRA rows                another shortlist company's drug selected for the same price-applicability year, its CMS
                          Part B+D spend cited to the CMS page
  MFN rows                another shortlist company's Medicaid MFN agreement, cited to its policy page
  LOE rows                the rival maker's own company-stated LOE (loe_calendar row)
  label rows              the rival product named in the finding (its label is cited in the finding)
  nugget rows             the nugget's own peer note, gated on the nugget's verified quotes
"""

import statistics

from agent.needle.cite.gate import derived_entry, numeric_gate
from agent.needle.cite.locator import Citation
from agent.needle.cite.verify import verify as cite_verify

from . import data
from . import gatewire as GW

NONE = "no comparable disclosure: "
GAP_LEVEL = {"receivables_outpace_revenue": "dso", "rec_gap_peer_outlier": "dso", "receivables_net": "dso",
             "inventory_outpaces_revenue": "dio", "inv_gap_peer_outlier": "dio"}
LABEL = {"etr": ("effective tax rate", "%"), "gross_margin": ("gross margin", "%"), "rnd_pct": ("R&D share of revenue", "%"),
         "dso": ("days sales outstanding", " days"), "dio": ("days inventory", " days"),
         "impairment_pct": ("impairment share of assets", "%")}


def _period(f):
    parts = str(getattr(f, "fact_key", "") or "").split("|")
    if len(parts) == 3 and parts[1]:
        return parts[1]
    return None


def _metric_value(t, metric, per, derived, tag):
    """(key, value, period used) of one company's metric from XBRL with cited operands, or None."""
    from agent.needle import xbrl
    from agent.needle.detect.forensics import ANNUAL_ONLY
    try:
        p = xbrl.panel(t)
    except Exception:
        return None
    annual = t in ANNUAL_ONLY
    if annual:
        try:
            a = xbrl.annual(t)
            cands = [str(y) for y in a.index if str(y)[:4].isdigit()]
        except Exception:
            return None
        want = per[:4] if per else None
        q = want if want in cands else (sorted(cands)[-1] if cands else None)
    else:
        idx = [str(x) for x in p.index]
        q = per if per in idx else None
        if q is None:
            col = GW.FORENSIC_EXPR[metric][0][0]
            try:
                q = str(p[col].dropna().index[-1])
            except Exception:
                return None
    if q is None:
        return None
    try:
        key = GW._metric_entry(t, p, metric, q, annual, derived, f"{tag}_{t}")
    except Exception:
        return None
    if not key:
        return None
    return key, float(derived[key]["value"]), q


def _forensics(f):
    from agent.needle.detect import SHORTLIST
    metric = GW.KIND_METRIC.get(f.kind) or GAP_LEVEL.get(f.kind) or GAP_LEVEL.get(getattr(f.impact, "channel", ""))
    if metric not in GW.FORENSIC_EXPR:
        return None
    per = _period(f)
    derived, vals = {}, {}
    for t in SHORTLIST:
        got = _metric_value(t, metric, per, derived, "peer")
        if got:
            vals[t] = got
    own = vals.pop(f.ticker, None)
    if len(vals) < 3:
        return NONE + f"fewer than three shortlist companies report the XBRL operands for {LABEL[metric][0]}", [], {}, {}
    keys = {f"p{i}": {"derived": k} for i, (t, (k, v, q)) in enumerate(sorted(vals.items()))}
    med = statistics.median(v for k, v, q in vals.values())
    derived["peer_median"] = derived_entry(med, "median(" + ", ".join(keys) + ")", keys,
                                           "%" if LABEL[metric][1] == "%" else "",
                                           label="median of the shortlist peers' cited XBRL values")
    ref = own[1] if own else med
    near_t, (nk, nv, nq) = min(vals.items(), key=lambda kv: abs(kv[1][1] - ref))
    name, unit = LABEL[metric]
    fmt = (lambda x: f"{x:.1f}") if unit == "%" else (lambda x: f"{x:.0f}")
    pl = (lambda q: f"FY{q}" if len(str(q)) == 4 else str(q))
    text = (f"Same item at the other shortlist companies ({name}, XBRL): median {fmt(med)}{unit}; nearest named peer "
            f"{near_t} {fmt(nv)}{unit} ({pl(nq)})")
    if own:
        text += f"; {f.ticker} {fmt(own[1])}{unit} ({pl(own[2])})"
    return text, [], derived, {}


def _ira(f):
    from .find import IRA_DRUGS
    me = [d for d in IRA_DRUGS if d[0] == f.ticker and d[1] == f.product]
    if not me:
        return None
    ipay, G0 = me[0][2], me[0][3]
    others = [d for d in IRA_DRUGS if d[0] != f.ticker and d[2] == ipay]
    if not others:
        return NONE + f"no other shortlist company has a drug selected for {ipay}", [], {}, {}
    t, drug, ip, G, sdoc, spage, squote = min(others, key=lambda d: abs(d[3] - G0))[:7]
    c = cite_verify(Citation(canonical_id=sdoc, page=spage, quote=squote, claim_type="number",
                             value=f"{G * 1e6:,.0f}"), data.index())
    if not c.verification.ok:
        return NONE + f"the CMS spend quote for {t} {drug} did not verify", [], {}, {}
    derived = {"peer_G": derived_entry(G, "g / 1000000", {"g": {"value": G * 1e6, "citation": c}})}
    return (f"Same item at {t}: {drug.split('/')[0]}'s Medicare price is also set from January {ip}; CMS Part B+D spend "
            f"${G:,.1f}M"), [c], derived, {}


def _mfn(f):
    from .find import _policy_cite, _policy_rows
    from agent.needle.detect import SHORTLIST
    idx = data.index()
    for t in SHORTLIST:
        if t == f.ticker:
            continue
        try:
            pe, fs = _policy_rows(t)
        except Exception:
            continue
        med = pe[(pe.force == "MFN") & pe.item.str.contains("Medicaid", na=False)]
        if med.empty or fs.empty:
            continue
        c = _policy_cite(med.iloc[0], idx)
        if c is None:
            continue
        return (f"Same item at {t}: its MFN agreement ({fs.iloc[0].mfn_date}) also extends MFN pricing to Medicaid; "
                "its terms are not public either"), [c], {}, {}
    return NONE + "no other shortlist company's Medicaid MFN term verifies", [], {}, {}


def _loe(f):
    from . import verified_tables as VT
    rival = str((f.peer or {}).get("rival") or "")
    if not rival:
        return None
    got = VT.loe_any(rival.split(" ")[0])
    if not got:
        return NONE + f"the rival {rival} has no company-stated LOE row in loe_calendar", [], {}, {}
    d, tv, row = got
    return (f"Rival maker: {rival} US protection ends {d.year} (company-stated, {row.get('company') or row.get('ticker')} "
            "filing)"), list(tv.citations), {}, {}


def _nugget(f):
    note = str((f.peer or {}).get("note") or "").strip()
    if not note:
        return NONE + "the nugget names no peer", [], {}, {}
    cites = [c for c in f.citations if c.verification.ok]
    extra = GW.page_line_support(note, cites, data.index())
    derived, am = {}, {}
    GW.auto_derive(note, cites + extra, derived, tag="peer")
    return note, extra, derived, am


def peer_comparison(f):
    """(text, extra citations, derived, assumptions) for one Scored row; text starts with NONE when there is none."""
    try:
        if getattr(f, "detector", "") == "nuggets":
            got = _nugget(f)
        elif f.kind == "ira_selected":
            got = _ira(f)
        elif f.kind == "mfn_medicaid":
            got = _mfn(f)
        elif f.kind == "exclusivity_earlier" or getattr(f.impact, "channel", "") == "loe":
            got = _loe(f)
        else:
            got = _forensics(f)
        if got is None and (f.peer or {}).get("rival"):
            got = (f"Rival product named in the finding: {f.peer['rival']} (its label is cited in the finding)",
                   [], {}, {})
        if got is None:
            why = ("a text change is measured against the company's own prior filing; no peer filing states the same "
                   "item" if f.detector in ("drift", "calls") else "the item has no XBRL concept or table row that "
                   "other shortlist companies report")
            got = (NONE + why, [], {}, {})
    except Exception as e:   # fail closed
        got = (NONE + f"peer lookup failed ({type(e).__name__})", [], {}, {})
    return got


def gated(f):
    """(text, citations, derived, assumptions, passed): the comparison and whether its numbers pass the gate; a
    comparison that fails is replaced by a 'no comparable disclosure' line naming the reason."""
    text, extra, derived, am = peer_comparison(f)
    cites = [c for c in list(f.citations) + list(extra) if c.verification.ok]
    if text.startswith(NONE):
        return text, [], {}, {}, True
    res = numeric_gate([("peer", text)], cites, derived, am)
    if res.passed or res.numeric_check["status"] in ("no_numbers", "unchecked"):
        return text, cites, derived, am, True
    n = len(res.numeric_check["unsupported"])
    return (NONE + f"the peer figures found ({n} number(s)) do not pass the citation gate", [], {}, {}, False)
