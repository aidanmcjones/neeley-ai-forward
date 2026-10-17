"""Data layer for FIND (docs/quant_model.md section 3): moat paths, I/B/E/S noise, company constants, citations
for table rows.

The moat (data/moat) is gitignored and lives in the gap-data worktree. Point at it with env NEEDLE_MOAT (default:
this repo's data/moat if present, else the gap-data worktree copy). Nothing here copies moat data into the repo.

Company constants (section 4.2 EPS translation, section 10.1):
  Rev_TTM  sum of the last 4 quarterly revenues (XBRL); 20-F filers: latest fiscal year
  t        sum income tax / sum pretax income, same quarters (TTM GAAP ETR; fallback rule of section 4.2)
  D        latest quarter's weighted-average diluted shares
  sigma    2 x sd(actual - last pre-announcement I/B/E/S mean), last 8 quarters (join on oftic)
Each constant carries a Citation: XBRL values cite the companyfacts concept and frame; I/B/E/S values cite the
facts row in citations.sqlite (licensed WRDS rows: internal math only, never quoted publicly).
"""

import os
from dataclasses import dataclass, field
from datetime import date
from functools import lru_cache
from pathlib import Path

import pandas as pd

from agent.moat import cite as moat
from agent.needle import xbrl
from agent.needle.cite.locator import Citation, Verification

from . import weights as W

ROOT = Path(__file__).resolve().parents[3]
_GAP = Path("/Users/aidanjones/dev/neeley-ai-forward/.claude/worktrees/gap-data/data/moat")
MOAT = Path(os.environ["NEEDLE_MOAT"]) if os.environ.get("NEEDLE_MOAT") else (
    ROOT / "data" / "moat" if (ROOT / "data" / "moat" / "tables").exists() else _GAP)
AS_OF = date(2026, 10, 17)
REAL_DB = Path(moat.DB)   # resolved at import (env CITATIONS_DB, repo copy, else gap-data); tests may re-point moat.DB


def db():
    """agent.moat.cite.db() on the real citation index, re-pointing the module global if something moved it."""
    if Path(moat.DB) != REAL_DB:
        moat.DB = REAL_DB
        moat.db.cache_clear()
    return moat.db()


def index():
    from agent.needle.cite.index import load_index
    idx = load_index(REAL_DB)
    idx._use()
    return idx

CIK = {"LLY": 59478, "MRK": 310158, "BMY": 14272, "PFE": 78003, "NVO": 353278, "ABBV": 1551152, "JNJ": 200406,
       "AZN": 901832, "AMGN": 318154, "GILD": 882095}


def tables(name):
    return MOAT / "tables" / name


def verified(name):
    return MOAT / "verified" / name


def _now():
    return date.today().isoformat()


def fact_citation(table, source_row, fld, value=None, license=""):
    """Citation for a facts row in citations.sqlite (kind "fact" in the spec): claim_type "number", canonical_id =
    the table, quote = row key + field = value, deep link = fact_link(source) when the source is http."""
    try:
        r = db().execute('SELECT * FROM facts WHERE "table" = ? AND source_row = ? AND field = ? LIMIT 1',
                              (table, source_row, fld)).fetchone()
    except Exception:
        r = None
    if r is None:
        v = Verification("unverified", 0.0, _now(), f"no facts row {table} {source_row} {fld}")
        return Citation(canonical_id=table, quote=f"{source_row} {fld}={value}", claim_type="number",
                        value=None if value is None else str(value), verification=v, confidence_note=v.detail)
    return _fact_row_citation(table, r, source_row, fld, value, license)


def _fact_row_citation(table, r, source_row, fld, value=None, license=""):
    from agent.needle.cite.facts import fact_citation_status, fact_status_grade
    reread = value is not None and _num_eq(r["value"], value)
    status = fact_citation_status(r["verify_status"], reread, table)
    grade, label = fact_status_grade(r["verify_status"], table)
    note = f"facts row {r['row_key']} re-read ({r['verify_status']}: {label})"
    if label == "machine data":
        note += "; machine data (licensed feed, no page copy): the value is re-read from the table row, not a page"
    if value is not None and not reread:
        note += f"; cited value {value} differs from the row value {r['value']}"
    lic = license or ("wrds_licensed" if r["verify_status"] == "no_verified_copy" else "")
    src = r["source"] or ""
    return _located(r, Citation(canonical_id=table, page=None, quote=f"{r['row_key']} [{source_row}] {fld} = {r['value']}",
                    claim_type="number", value=str(r["value"]), unit=r["unit"] or "", doc_title=f"moat table {table}",
                    location=f"row {r['row_key']}", source_url=src if src.startswith("http") else "",
                    deep_link=src if src.startswith("http") else "", license=lic, page_scheme="none",
                    verification=Verification(status, grade if status != "unverified" else 0.0, _now(), note),
                    confidence_note=note), None, value is not None and not reread)


def _located(r, cit, rj=None, mismatch=False):
    """facts.locator applied to a facts-row citation (agent.needle.cite.facts.apply_locator): a doc_id#pN locator
    (or a label-section source_row) gives a verified page citation, url: a machine-data deep link, fact: the row key.
    With no locator column (older sqlite) the citation is unchanged. Fail closed: an error keeps the facts citation."""
    from agent.needle.cite.facts import apply_locator
    import json as _json
    try:
        if rj is None:
            try:
                rj = _json.loads(r["row_json"] or "{}")
            except (ValueError, KeyError, IndexError):
                rj = {}
        return apply_locator(r, cit, rj, index(), value_mismatch=mismatch)
    except Exception:
        return cit


def fact_row_citation(table, fld, value, ticker=None, row_key=None, where=None, license=""):
    """Citation for one field of a facts row's row_json (citations.sqlite facts keeps one indexed field per table
    row; the other columns live in row_json). The row is found by table + ticker (+ row_key, + a dict of row_json
    fields that must match), the field re-read from row_json and compared with `value`; the status follows the
    facts.verify_status whitelist (agent.needle.cite.facts). No row, or a value that differs: unverified."""
    import json as _json
    q, args = 'SELECT * FROM facts WHERE "table" = ?', [table]
    if ticker:
        q += " AND ticker = ?"
        args.append(ticker)
    if row_key:
        q += " AND row_key = ?"
        args.append(row_key)
    try:
        rows = db().execute(q, args).fetchall()
    except Exception:
        rows = []
    for r in rows:
        try:
            rj = _json.loads(r["row_json"] or "{}")
        except ValueError:
            continue
        if where and any(str(rj.get(k, "")).strip().lower() != str(v).strip().lower()
                         and not (_isnum(rj.get(k)) and _isnum(v) and _num_eq(rj.get(k), v)) for k, v in where.items()):
            continue
        if fld not in rj:
            continue
        from agent.needle.cite.facts import fact_citation_status, fact_status_grade
        reread = value is not None and _num_eq(rj[fld], value)
        status = fact_citation_status(r["verify_status"], reread, table)
        grade, label = fact_status_grade(r["verify_status"], table)
        note = f"facts row {r['row_key']} field {fld} re-read from row_json ({r['verify_status']}: {label})"
        if value is not None and not reread:
            note += f"; cited value {value} differs from the row value {rj[fld]}"
        src = r["source"] or ""
        return _located(r, Citation(canonical_id=table, page=None, quote=f"{r['row_key']} {fld} = {rj[fld]}",
                        claim_type="number", value=str(rj[fld]), unit=r["unit"] if r["field"] == fld else ("%" if fld.endswith("_pct") else ""),
                        ticker=ticker or "", doc_title=f"moat table {table}", location=f"row {r['row_key']}",
                        source_url=src if src.startswith("http") else "", deep_link=src if src.startswith("http") else "",
                        license=license or ("wrds_licensed" if r["verify_status"] == "no_verified_copy" else ""),
                        page_scheme="none",
                        verification=Verification(status, grade if status != "unverified" else 0.0, _now(), note),
                        confidence_note=note), rj, value is not None and not reread)
    return table_citation(table, row_key or ticker or "", fld, value)


def _isnum(x):
    try:
        float(x)
        return True
    except (TypeError, ValueError):
        return False


def _num_eq(a, b):
    try:
        return abs(float(a) - float(b)) <= 1e-6 * max(1.0, abs(float(b)))
    except (TypeError, ValueError):
        return str(a) == str(b)


def _xbrl_reread(ticker, concept, frame):
    """[(value, unit)] for concept (one name or 'A/B') at the companyfacts frame, read from the file."""
    try:
        f = xbrl._facts(ticker)
    except Exception:
        return []
    out = []
    for name in str(concept).split("/"):
        name = name.split(":")[-1]
        for ns in ("us-gaap", "ifrs-full", "dei"):
            node = f.get("facts", {}).get(ns, {}).get(name)
            if not node:
                continue
            for unit, vals in node.get("units", {}).items():
                out += [(float(v["val"]), unit) for v in vals if v.get("frame") == frame]
    return out


def xbrl_citation(ticker, concept, frame, value, unit="USD"):
    """Citation for one SEC companyfacts value (concept + frame), re-read from the XBRL file inside this function
    (review C4): status number_match only when the file has that frame and its value equals the cited value (value in
    millions when the unit says millions, else as given); a frame the file does not carry (CY####Q4 for most 10-K
    filers, review D11) or a different value is unverified."""
    cik = CIK.get(ticker.upper())
    url = f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik:010d}.json" if cik else ""
    found = _xbrl_reread(ticker.upper(), concept, frame)
    ok = any(abs(v - value * 1e6) <= 1e-6 * max(1.0, abs(v)) or abs(v - value) <= 1e-6 * max(1.0, abs(v))
             for v, _ in found)
    if ok:
        status, note = "number_match", f"companyfacts {concept} frame {frame} re-read from xbrl_companyfacts.json.gz: equal"
    elif found:
        status, note = "unverified", (f"companyfacts {concept} frame {frame} holds {found[0][0]:,.0f}, not the cited "
                                      f"{value:,.0f}")
    else:
        status, note = "unverified", f"companyfacts has no frame {frame} for {concept} (re-read failed)"
    return Citation(canonical_id=f"xbrl:{ticker.upper()}", page=None, quote=f"{concept} {frame} = {value:,.0f}",
                    claim_type="number", value=f"{value:,.0f}", unit=unit, ticker=ticker.upper(),
                    doc_title=f"{ticker.upper()} SEC XBRL companyfacts", location=f"{concept} {frame}",
                    source_url=url, deep_link=url, page_scheme="none",
                    verification=Verification(status, 0.6 if ok else 0.0, _now(), note), confidence_note=note)


# Derived citations remember their expression and operands by cite_id so the numeric gate can re-compute them
# (gate.derived_entry); data.derived_citation itself stores only a formula string.
DERIVED_OPS = {}
CITES = {}          # cite_id -> Citation for every operand of a derived citation (expand_citations)


def expand_citations(cites):
    """cites plus, recursively, every operand Citation of each derived citation, deduped by cite_id (order kept).
    A record must carry a derived citation's operands inline (the UI and gate_record check it)."""
    out, seen = [], set()

    def add(c):
        if c is None or c.cite_id in seen:
            return
        seen.add(c.cite_id)
        out.append(c)
        for oid in getattr(c, "operands", None) or []:
            add(CITES.get(oid))
    for c in cites:
        add(c)
    return out


def derived_citation(formula, value, operands, unit="", expr=None, names=None):
    """kind "derived": computed by code from cited operands. Status "derived" (never "exact": no document shows the
    number); its score is the weakest operand's grade (spec 4.5 derived_code), which evidence.grade uses."""
    worst = min(operands, key=lambda c: _rank(c.verification.status)) if operands else None
    note = (f"derived by code: {formula}; operands " +
            ", ".join(f"{c.location or c.canonical_id} ({c.cite_id})" for c in operands))
    c = Citation(canonical_id="derived", quote=formula, claim_type="number", value=f"{value:,.4g}", unit=unit,
                    doc_title="derived", doc_type="derived", raw_doc_type="derived", location="computed",
                    page_scheme="none",
                    verification=Verification("derived", worst.verification.score if worst and
                                              worst.verification.ok else 0.0, _now(), note),
                    confidence_note=note)
    c.operands = [o.cite_id for o in operands]
    CITES.update({o.cite_id: o for o in operands})
    if expr:
        DERIVED_OPS[c.cite_id] = (expr, dict(zip(names or [f"o{i}" for i in range(len(operands))], operands)), value)
    return c


def gate_operand(c, dmap, value=None):
    """A gate operand for citation c: a derived citation registers its own derived entry in dmap (recursively) and
    returns {"derived": key}; any other citation returns (value, c) with value defaulting to c.value."""
    from agent.needle.cite.gate import derived_entry
    spec = DERIVED_OPS.get(c.cite_id)
    if spec is None:
        v = value if value is not None else float(str(c.value).replace(",", ""))
        return (v, c)
    expr, ops, val = spec
    key = f"d_{c.cite_id}"
    if key not in dmap:
        dmap[key] = derived_entry(val, expr, {n: gate_operand(o, dmap) for n, o in ops.items()}, c.unit)
    return {"derived": key}


def has_frame(ticker, col, q):
    """Does companyfacts carry the calendar frame CY<q> for this flow metric (Q4 usually does not)?"""
    try:
        s = xbrl._metric_series(xbrl._facts(ticker), "flow", xbrl.METRICS[col][1])
    except Exception:
        return True
    return q in s


def flow_citation(ticker, p, col, q, value, unit):
    """Citation for a quarterly flow value. A Q4 the panel derived as FY - (Q1 + Q2 + Q3) has no CY####Q4 frame in
    companyfacts (review D11), so it is a derived citation over the CY#### frame and the three quarter frames."""
    if not str(q).endswith("Q4") or has_frame(ticker, col, q):
        return xbrl_citation(ticker, _concept(p, col, q), f"CY{q}", value, unit)
    y = str(q)[:4]
    a = xbrl.annual(ticker)
    fy = float(a.at[y, col]) / 1e6 if y in a.index and col in a else None
    ops = ([xbrl_citation(ticker, _concept(p, col, q), f"CY{y}", fy, unit)] if fy is not None else []) + \
          [xbrl_citation(ticker, _concept(p, col, f"{y}Q{n}"), f"CY{y}Q{n}", float(p.at[f"{y}Q{n}", col]) / 1e6, unit)
           for n in (1, 2, 3)]
    if len(ops) == 4:
        return derived_citation(f"{col} CY{y} - (CY{y}Q1 + CY{y}Q2 + CY{y}Q3) = {value:,.0f}", value, ops, unit,
                                expr="fy - q1 - q2 - q3", names=["fy", "q1", "q2", "q3"])
    return derived_citation(f"{col} CY{y} - (CY{y}Q1 + CY{y}Q2 + CY{y}Q3) = {value:,.0f}", value, ops, unit)


def _rank(status):
    return {"exact": 4, "substring": 4, "fuzzy": 3, "number_match": 2}.get(status, 0)


# ------------------------------------------------------------------ I/B/E/S
# I/B/E/S ticker -> multiplier to the per-ordinary-share basis of XBRL D. ZEN is AstraZeneca's per-ADR history
# (1 ADR = 0.5 ordinary share) before I/B/E/S moved AZN to per-share in 2026Q1 (review A2).
PER_SHARE = {"ZEN": 2.0}
@lru_cache(maxsize=1)
def _ibes():
    a = pd.read_csv(tables("ibes_actuals.csv"))
    q = pd.read_csv(tables("ibes_eps_quarterly.csv"))
    c = pd.read_csv(tables("ibes_eps_consensus.csv"))
    return a, q, c


def surprises(ticker, n=W.SIGMA_QUARTERS):
    """Last n quarterly surprises: actual minus the last I/B/E/S mean before the announcement date (join on oftic,
    section 3). Returns a DataFrame (pends, actual, mean, statpers, surprise, act_row, est_row, curr)."""
    a, q, _ = _ibes()
    aq = a[(a.oftic == ticker) & (a.pdicity == "QTR") & (a.measure == "EPS")]
    rows = []
    for _, r in aq.iterrows():
        cand = q[(q.oftic == ticker) & (q.ticker == r.ticker) & (q.fpedats == r.pends) & (q.statpers < r.anndats)]
        if cand.empty:
            cand = q[(q.oftic == ticker) & (q.fpedats == r.pends) & (q.statpers < r.anndats)]
        if cand.empty:
            continue
        last = cand.sort_values("statpers").iloc[-1]
        fa = PER_SHARE.get(r.ticker, 1.0)        # one per-share basis per company (review A2)
        fm = PER_SHARE.get(last.ticker, 1.0)
        rows.append((r.pends, r.value * fa, last.meanest * fm, last.statpers, r.value * fa - last.meanest * fm,
                     r.source_row, last.source_row, r.curr_act, r.anndats))
    d = pd.DataFrame(rows, columns=["pends", "actual", "mean", "statpers", "surprise", "act_row", "est_row", "curr",
                                    "anndats"]).sort_values("pends")
    return d.tail(n)


def sigma_eps(ticker):
    """(sigma_EPS, currency, citations, flags). Section 4.2 with its fallback chain."""
    flags, cites = [], []
    try:
        d = surprises(ticker)
    except FileNotFoundError:
        d = pd.DataFrame()
    if len(d) >= 4:
        for _, r in d.iterrows():
            cites.append(fact_citation("tables/ibes_actuals.csv", r.act_row, "value", r.actual))
            cites.append(fact_citation("tables/ibes_eps_quarterly.csv", r.est_row, "meanest", r["mean"]))
        gaps = pd.to_datetime(d.pends).diff().dt.days.dropna()
        if (gaps > 100).any():
            flags.append("sigma_EPS window skips a quarter (I/B/E/S gap); last 8 available surprises used")
        if len(d) < W.SIGMA_QUARTERS:
            flags.append(f"sigma_EPS from {len(d)} quarters, not {W.SIGMA_QUARTERS}")
        return W.SIGMA_ANNUALIZE * float(d.surprise.std(ddof=1)), str(d.curr.iloc[-1]), cites, flags
    _, _, c = _ibes()
    cf = c[(c.oftic == ticker) & (c.fpi.astype(str) == "1")].sort_values("statpers")
    if len(cf) and pd.notna(cf.iloc[-1].stdev) and cf.iloc[-1].stdev > 0:
        r = cf.iloc[-1]
        flags.append("sigma_EPS fallback 1: FY1 forecast dispersion; not league-comparable (dispersion is 1.2x to "
                     "7.5x smaller than surprise noise, review A3)")
        return float(r.stdev), str(r.curcode), [fact_citation("tables/ibes_eps_consensus.csv", r.source_row, "stdev",
                                                              r.stdev)], flags
    flags.append("sigma_EPS fallback 2: 0.041 x |trailing EPS| (no I/B/E/S)")
    return None, "USD", [], flags


# ------------------------------------------------------------------ company constants
@dataclass
class Company:
    ticker: str
    rev_ttm: float            # USD (or reporting currency) millions
    tax: float
    shares: float             # millions
    sigma: float              # per-share, I/B/E/S currency
    currency: str             # I/B/E/S currency of sigma
    fin_currency: str         # XBRL reporting currency
    annual_only: bool
    last_quarter: str
    citations: dict = field(default_factory=dict)   # name -> list[Citation]
    flags: list = field(default_factory=list)
    comparable: bool = True


def _concept(p, col, q):
    cs = p.attrs.get("concepts", {}).get(col, [])
    return cs[0] if len(cs) == 1 else "/".join(cs[:2]) if cs else col


def annual_only(ticker, p=None):
    """Section 7.3 rule: the filer's latest annual form is 20-F or 40-F (corpus has a 20f_* file), or the panel lacks
    four consecutive recent quarters of revenue."""
    corpus = list((ROOT / "data" / "corpus").glob(f"*/{ticker.upper()}/20f_*.md")) + \
        list((ROOT / "data" / "corpus").glob(f"*/{ticker.upper()}/40f_*.md"))
    return bool(corpus)


@lru_cache(maxsize=64)
def company(ticker):
    """Company constants of section 4.2 / 10.1, each with citations."""
    t = ticker.upper()
    p = xbrl.panel(t)
    flags, cites = [], {}
    fin_cur = (p.attrs.get("units", {}).get("revenue") or ["USD"])[0]
    ao = annual_only(t, p)
    rev = p["revenue"].dropna() if "revenue" in p else pd.Series(dtype=float)
    last4 = list(rev.index[-4:])
    consecutive = len(last4) == 4 and all(_next(last4[i]) == last4[i + 1] for i in range(3))
    if not ao and consecutive:
        rv = [float(p.at[q, "revenue"]) for q in last4]
        tx = [float(p.at[q, "income_tax"]) for q in last4]
        pt = [float(p.at[q, "pretax_income"]) for q in last4]
        rev_ttm, tax = sum(rv) / 1e6, sum(tx) / sum(pt)
        sh = p["shares_diluted"].dropna()
        shares, lq = float(sh.iloc[-1]) / 1e6, last4[-1]
        cites["Rev_TTM"] = [flow_citation(t, p, "revenue", q, v / 1e6, f"{fin_cur} millions")
                            for q, v in zip(last4, rv)]
        cites["t"] = [flow_citation(t, p, "income_tax", q, v / 1e6, f"{fin_cur} millions")
                      for q, v in zip(last4, tx)] + \
                     [flow_citation(t, p, "pretax_income", q, v / 1e6, f"{fin_cur} millions")
                      for q, v in zip(last4, pt)]
        cites["D"] = [xbrl_citation(t, _concept(p, "shares_diluted", sh.index[-1]), f"CY{sh.index[-1]}",
                                    float(sh.iloc[-1]) / 1e6, "shares millions")]
    else:
        a = xbrl.annual(t)
        y = a["revenue"].dropna().index[-1]
        rev_ttm = float(a.at[y, "revenue"]) / 1e6
        tax = float(a.at[y, "income_tax"]) / float(a.at[y, "pretax_income"])
        shs = p["shares_diluted"].dropna() if "shares_diluted" in p else pd.Series(dtype=float)
        if len(shs):
            shares = float(shs.iloc[-1]) / 1e6
            sh_frame = f"CY{shs.index[-1]}"
        else:
            shares, sh_frame = _ifrs_diluted_shares(t)
        lq = f"{y}FY"
        flags.append("annual filer (20-F): Rev_TTM, t from the latest fiscal year (section 7.4)")
        cites["Rev_TTM"] = [xbrl_citation(t, _concept(p, "revenue", y), f"CY{y}", rev_ttm, f"{fin_cur} millions")]
        cites["t"] = [xbrl_citation(t, _concept(p, "income_tax", y), f"CY{y}", float(a.at[y, "income_tax"]) / 1e6),
                      xbrl_citation(t, _concept(p, "pretax_income", y), f"CY{y}", float(a.at[y, "pretax_income"]) / 1e6)]
        cites["D"] = [xbrl_citation(t, "AdjustedWeightedAverageShares" if "shares_diluted" not in p else
                                    _concept(p, "shares_diluted", y), sh_frame, shares, "shares millions")]
    if not 0.0 <= tax <= 0.40:
        flags.append(f"TTM GAAP ETR {tax:.3f} outside [0, 0.40] (one-off charges); peer median TTM ETR used")
        cites["t_raw"] = cites.pop("t")
        tax = peer_median_tax()
    sigma, cur, scites, sflags = sigma_eps(t)
    flags += sflags
    comparable = sigma is not None and not any("fallback" in f for f in sflags)
    if sigma is None:
        eps = rev_ttm * 0.2 / shares
        sigma = W.SIGMA_FY1_RATIO * abs(eps)
        flags.append("not comparable: sigma_EPS imputed")
    cites["sigma_EPS"] = scites
    if cur != fin_cur and not fin_cur.startswith(cur):
        flags.append(f"I/B/E/S currency {cur} vs XBRL {fin_cur}: per-share figures must be in one currency")
    return Company(t, rev_ttm, tax, shares, sigma, cur, fin_cur, ao, lq, cites, flags, comparable)


def _ifrs_diluted_shares(ticker):
    """20-F filers: latest ifrs-full AdjustedWeightedAverageShares annual frame (diluted weighted shares)."""
    f = xbrl._facts(ticker)
    node = f["facts"].get("ifrs-full", {}).get("AdjustedWeightedAverageShares") or \
        f["facts"].get("us-gaap", {}).get("WeightedAverageNumberOfDilutedSharesOutstanding")
    vals = [v for u in node["units"].values() for v in u if str(v.get("frame", "")).startswith("CY")
            and len(v["frame"]) == 6]
    v = max(vals, key=lambda v: v["frame"])
    return float(v["val"]) / 1e6, v["frame"]


TAX_PEERS = ("LLY", "MRK", "BMY", "PFE", "ABBV", "JNJ", "AMGN", "GILD", "NVO", "AZN")


@lru_cache(maxsize=1)
def peer_median_tax():
    """Median TTM GAAP ETR across shortlist companies whose own ETR lies in [0, 0.40] (fallback, inference)."""
    vals = []
    for t in TAX_PEERS:
        try:
            p = xbrl.panel(t)
            q = p[["income_tax", "pretax_income"]].dropna().iloc[-4:]
            if len(q) == 4:
                r = q.income_tax.sum() / q.pretax_income.sum()
                if 0.0 <= r <= 0.40:
                    vals.append(float(r))
        except Exception:
            continue
    vals.sort()
    n = len(vals)
    return (vals[n // 2] if n % 2 else (vals[n // 2 - 1] + vals[n // 2]) / 2) if vals else 0.16


def _next(q):
    y, n = int(q[:4]), int(q[-1])
    return f"{y + (n == 4)}Q{1 if n == 4 else n + 1}"


# ------------------------------------------------------------------ analyst attention and earnings releases
@lru_cache(maxsize=1)
def scorecard():
    return pd.read_csv(verified("market/priced_in_scorecard.csv"))


@lru_cache(maxsize=1)
def qa_turns():
    d = pd.read_csv(tables("qa_turns.csv"))
    return d[d.role.astype(str).str.lower().str.startswith("analyst")]


def doc_row(doc_id):
    try:
        return db().execute("SELECT * FROM docs WHERE doc_id = ?", (doc_id,)).fetchone()
    except Exception:
        return None


def latest_release_page1(ticker):
    """(doc_id, text) of page 1 of the latest earnings release in the citation index (section 4.4 h_f)."""
    r = db().execute("SELECT doc_id FROM docs WHERE ticker = ? AND doc_type = 'earnings_release' "
                          "ORDER BY filed DESC LIMIT 1", (ticker.upper(),)).fetchone()
    if not r:
        return None, ""
    pg = db().execute("SELECT text FROM pages WHERE doc_id = ? ORDER BY page_no LIMIT 1", (r[0],)).fetchone()
    return r[0], (pg[0] if pg else "")


def fact_by_key(table, row_key, fld="value", value=None):
    """Facts row looked up by its row_key (e.g. policy_exposure row_id R010)."""
    r = db().execute('SELECT * FROM facts WHERE "table" = ? AND row_key = ? AND field = ? LIMIT 1',
                     (table, row_key, fld)).fetchone()
    if r is None:
        return table_citation(table, row_key, fld, value)
    return _fact_row_citation(table, r, r["source_row"], fld, value)


def table_citation(table, row_key, fld, value, licensed=False):
    """A moat-table number that is not a facts row in citations.sqlite: the Citation still exists (table + row key,
    claim_type "number") with status "unverified" and a note, so it is visible but never counts toward E."""
    note = f"derived from moat table {table} row {row_key} field {fld}" + ("; licensed, not shown publicly" if licensed else "")
    return Citation(canonical_id=table, quote=f"{row_key} {fld} = {value}", claim_type="number",
                    value=None if value is None else str(value), doc_title=f"moat table {table}",
                    location=f"row {row_key}", page_scheme="none", license="wrds_licensed" if licensed else "",
                    verification=Verification("unverified", 0.0, _now(), note), confidence_note=note)


# Case-appendix rivals missing from agent.needle.detect.CASE_SETS (review B24). No drug pack exists for these yet,
# so the label detectors cannot compare against them; the product fine-print worker owns adding the packs.
RIVALS_EXTRA = {"LLY": {"mounjaro": ["wegovy pill (oral semaglutide)"], "zepbound": ["wegovy pill (oral semaglutide)"],
                        "trulicity": ["wegovy pill (oral semaglutide)"]}}
