"""Export precomputed JSON for the NEEDLE cockpit UI (ui/, Vite + React) into ui/public/data/.

Follows the data contract in docs/ui_spec.md. Read-only over engine outputs; no network, no API key.

  PYTHONPATH=. python -m agent.ui_export            # writes meta.json, league.json, proof.json, companies/<T>.json

Inputs: out/ (findings, rejected, labels tables, ledger, backtest, predictions), data/corpus (pages + manifest),
data/moat (progress, tables, verified CSVs, ai_wrong log), docs (gate2, sealed hash, materiality limits).

Rules this module keeps:
- Contract keys are never renamed; extra keys are added only where useful. NaN/inf become null.
- Every evidence item gets excerpt {before, match, after}: the quote located on its page (or label section) with the
  same whitespace/quote-mark normalization the verifier uses; `match` is the text as printed on the page.
- `stance` and `questions` are deterministic templates over verified findings. Answer text reuses finding sentences
  and impact formulas verbatim; option dollars are sums of impact dollars present in the findings, nothing else.
- proof.sealed.canonical is the exact string agent.needle.audit.seal() hashes, so the browser can recompute sha256.
"""

import ast
import os
import collections
import hashlib
import json
import math
import re
import unicodedata
from pathlib import Path

import pandas as pd

from agent.needle import audit, pages
from agent.needle.detect import CASE_SETS, SHORTLIST

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "out"
MOAT = ROOT / "data" / "moat"
VER = MOAT / "verified"
DRUGS = ROOT / "data" / "corpus" / "drugs"
DEST = ROOT / "ui" / "public" / "data"
SIDE, SIDE_SMALL, MAX_COMPANY_BYTES = 900, 600, 4_000_000
REGEN = "PYTHONPATH=. python -m agent.ui_export"

NAMES = {"MRK": "Merck & Co.", "BMY": "Bristol Myers Squibb", "PFE": "Pfizer", "LLY": "Eli Lilly",
         "NVO": "Novo Nordisk", "ABBV": "AbbVie", "JNJ": "Johnson & Johnson", "AZN": "AstraZeneca",
         "AMGN": "Amgen", "GILD": "Gilead Sciences", "VRTX": "Vertex Pharmaceuticals"}

VERIFIER_RULES = [
    "The quote must appear on the cited page (whitespace-normalized).",
    "For call transcripts, the named speaker must appear before the quote.",
    "Every figure cited must appear on that page.",
    "LLM-written summaries (for example fool.com transcripts) are rejected as sources; only primary documents count.",
    "Label facts must occur verbatim in the drug's DailyMed label (label_sections.md), cited by section.",
    "Transcripts flagged unquotable (duplicate, no speaker names, garbled) are never quoted.",
]

# one honest sentence per moat table, inferred from its header and the collector that built it
TABLE_WHAT = {
    "analyst_topics.csv": "Per company and quarter, how many analyst Q&A turns touched each topic, with an example quote.",
    "company_list_vs_net.csv": "Companies' own published average list vs net price change per year (portfolio level, unaudited).",
    "event_returns.csv": "Abnormal stock returns around each earnings filing date (day 0, days 0 to 1, days -1 to 5).",
    "exec_comp_metrics.csv": "Incentive-plan metrics and weights from proxy statements, with the page they are printed on.",
    "force_summary.csv": "Three-forces exposure per company: IRA-selected revenue share, MFN date, US pledge, tariff exemption, sites, US share.",
    "gtn_proxy.csv": "Per drug and year: Part D gross per unit, Part B ASP, brand NADAC and IRA MFP side by side, with ratios.",
    "head_to_head_pubmed.csv": "PubMed articles naming two or more of the case drugs (possible head-to-head evidence).",
    "head_to_head.csv": "ClinicalTrials.gov studies naming two or more case drugs, with design, phase, status and primary outcome.",
    "ibes_actuals.csv": "I/B/E/S reported actuals (EPS and revenue) per company and period.",
    "ibes_eps_consensus.csv": "I/B/E/S EPS consensus snapshots (mean, median, high, low, count) by forecast period.",
    "ibes_eps_quarterly.csv": "I/B/E/S quarterly EPS consensus snapshots by forecast period.",
    "ibes_ids.csv": "I/B/E/S ticker, CUSIP and company-name mapping used to join WRDS data.",
    "ibes_recommendations.csv": "I/B/E/S analyst recommendation summaries (mean rating, buy/hold/sell shares, revisions).",
    "ibes_revenue_consensus.csv": "I/B/E/S revenue consensus snapshots by forecast period.",
    "indication_timeline.csv": "Every DailyMed label version per drug with its effective date and indication count.",
    "insider_trades.csv": "SEC Form 4 insider transactions (person, role, date, code, shares, price, value).",
    "label_changes.csv": "Section-level changes between consecutive DailyMed label versions, with old and new excerpts.",
    "manufacturing_sites_detail.csv": "FDA establishment registrations matched to each company, with country and operations.",
    "manufacturing_sites.csv": "Count of FDA-registered manufacturing sites per company and country, US vs non-US.",
    "material_agreements.csv": "Material agreements filed as SEC exhibits, with the products they mention.",
    "medicaid_sdud.csv": "Medicaid State Drug Utilization (national) units, prescriptions and reimbursement by quarter.",
    "nadac_history.csv": "Medicaid NADAC weekly pharmacy acquisition cost per unit for brands and their generics, 2020 to 2026.",
    "news_mentions.csv": "Monthly news article counts per company and topic (press-attention proxy).",
    "partb_asp_quarterly.csv": "CMS Part B payment limit per HCPCS dosage unit by quarter (ASP + 6%).",
    "partd_by_year.csv": "Medicare Part D gross spend, units, claims and beneficiaries per drug and year, before rebates.",
    "policy_exposure.csv": "Quoted policy-exposure facts (IRA, MFN, tariffs) per company with document and page.",
    "prices_daily.csv": "Daily adjusted close and volume per ticker.",
    "product_revenue_quarterly.csv": "XBRL product revenue facts per filing, period, product member and geography.",
    "qa_turns.csv": "Every earnings-call Q&A turn with speaker, role, firm and transcript page.",
    "recalls.csv": "FDA enforcement recalls for the case drugs with classification and reason.",
    "rems.csv": "Whether each case drug has an active REMS and its elements (Drugs@FDA).",
    "restatements.csv": "Product revenue values that differ across filings for the same period (candidates, mostly recasts).",
    "sec_comment_letters.csv": "SEC staff comment letters and company replies per company with topics.",
    "subsidiaries.csv": "Subsidiary entities and countries listed in Exhibit 21 of each 10-K.",
    "supplement_approvals.csv": "Drugs@FDA supplement approvals per case drug (submission class, priority, status date).",
    "transcripts_index.csv": "Index of the earnings-call transcripts collected, with source quality and Q&A turn counts.",
    "wac_increases.csv": "California HCAI manufacturer-reported WAC increases over 16% in three years, 2019 to 2026.",
}
LIST_OR_NET = {
    "partd_by_year.csv": "list-like (gross before rebates)", "nadac_history.csv": "list-like (pharmacy acquisition)",
    "medicaid_sdud.csv": "list-like (before Medicaid rebates)", "partb_asp_quarterly.csv": "net-like (ASP)",
    "wac_increases.csv": "list (WAC events)", "company_list_vs_net.csv": "both (company-reported, portfolio level)",
    "gtn_proxy.csv": "both, side by side (proxies; true net is not free)",
}

# stance buckets: which CEO option a finding kind argues for (first match wins)
OPTION_RULES = [
    ("Attack", {"label_broader", "dosing_advantage", "boxed_warning_advantage"}, set()),
    ("Reprice", {"ira_exposed", "spend_per_claim_gap", "ira_selected", "mfn_medicaid"}, {"ira", "mfn", "gtn", "pricing", "340b", "tariff"}),
    ("Partner-or-buy", {"exclusivity_earlier", "label_narrower", "dosing_burden", "boxed_warning_disadvantage",
                        "trial_terminated", "impairment", "faers_serious_rising", "demand_divergence"}, set()),
    ("Defend", None, set()),  # everything else: balance-sheet, margin, disclosure-drift and call findings
]
OPTION_WHY = {
    "Defend": "fix the exposure the filings reveal (channel, receivables, margin, disclosure) before the market prices it",
    "Attack": "press a label, dosing or safety advantage over rivals with prescribers and payers",
    "Reprice": "reset net price and contracting where IRA, MFN or gross-to-net pressure lands",
    "Partner-or-buy": "license or acquire to replace revenue at risk from earlier exclusivity loss, a narrower label or a dropped trial",
}

LEADS = [  # plain-words lead for the headline, by signal kind
    (("dio", "inventory"), "Inventory is building faster than sales"),
    (("dso", "receivables", "rec_gap"), "Customers are taking longer to pay than revenue growth explains"),
    (("rnd",), "R&D spending jumped as a share of revenue"),
    (("gross_margin",), "Gross margin moved sharply"),
    (("etr", "tax_rate"), "The effective tax rate swung"),
    (("impairment",), "A write-down hit the books"),
    (("label_broader",), "The label is broader than rivals'"),
    (("label_narrower",), "The label is narrower than rivals'"),
    (("dosing_advantage",), "Dosing is less frequent than rivals'"),
    (("dosing_burden",), "Dosing is more frequent than rivals'"),
    (("boxed_warning_disadvantage",), "It carries a boxed warning a rival does not"),
    (("boxed_warning_advantage",), "A rival carries a boxed warning it does not"),
    (("exclusivity",), "Exclusivity ends earlier than rivals'"),
    (("ira",), "Medicare price setting reaches this product"),
    (("mfn",), "The MFN agreement reaches Medicaid"),
    (("qa_",), "Management deflected an analyst question"),
    (("risk_", "mdna_"), "The filing wording changed"),
    (("trial",), "A late-stage trial was stopped"),
]

PROVE_WRONG = [  # early signals that would show the call is wrong, by kind
    (("dio", "inventory"), "Inventory days fall back toward the peer median{pm} in the next two 10-Qs."),
    (("dso", "receivables", "rec_gap"), "Receivables growth falls back inside revenue growth in the next two 10-Qs."),
    (("rnd",), "R&D share of revenue returns toward the peer median{pm} in the next two 10-Qs."),
    (("gross_margin",), "Gross margin holds at the prior-year level in the next two quarterly reports."),
    (("etr", "tax_rate"), "The effective tax rate reverts to the prior-year level in the next 10-Q."),
    (("impairment",), "No further impairment on the same asset in the next two filings."),
    (("label", "dosing", "boxed"), "A new DailyMed label version for the product or a rival closes the gap within 12 months."),
    (("exclusivity",), "A settlement, court ruling or new patent listing moves the generic or biosimilar entry date."),
    (("mfn",), "The company's own disclosure puts the Medicaid MFN cost well below this estimate in the next 10-Q."),
    (("ira", "spend_per_claim"), "CMS's next selected-drug list or MFP schedule leaves the product's exposure unchanged."),
    (("qa_", "call_topic"), "Management gives the product-level number analysts asked for on the next earnings call."),
    (("risk_", "mdna_"), "The next 10-K drops or softens the new wording without a matching hit to results."),
    (("trial",), "The sponsor restarts or replaces the stopped trial within 12 months."),
]


# ---------------------------------------------------------------- small helpers
def clean(o):
    """Recursively turn NaN/inf/numpy/pandas values into JSON-safe plain values."""
    if isinstance(o, dict):
        return {str(k): clean(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [clean(v) for v in o]
    if hasattr(o, "item") and not isinstance(o, (str, bytes)):
        try:
            o = o.item()
        except Exception:
            pass
    if isinstance(o, float) and not math.isfinite(o):
        return None
    if o is pd.NaT:
        return None
    return o


def read_json(p, default=None):
    p = Path(p)
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else default


def read_jsonl(p):
    p = Path(p)
    if not p.exists():
        return []
    return [json.loads(x) for x in p.read_text(encoding="utf-8").splitlines() if x.strip()]


_CSV = {}


def csv_rows(p):
    """All rows of a CSV as dicts with NaN -> None (cached)."""
    p = Path(p)
    if p not in _CSV:
        if not p.exists():
            _CSV[p] = []
        else:
            df = pd.read_csv(p, low_memory=False)
            _CSV[p] = clean(df.astype(object).where(df.notna(), None).to_dict("records"))
    return _CSV[p]


def for_ticker(p, ticker, col="ticker"):
    return [r for r in csv_rows(p) if str(r.get(col) or "").upper() == ticker]


def write(path, obj):
    assert_no_repr(obj)
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(clean(obj), ensure_ascii=False, allow_nan=False, separators=(",", ":"))
    path.write_text(text, encoding="utf-8")
    return len(text.encode("utf-8"))


def money(x):
    if x is None:
        return "n/a"
    return f"${x / 1e9:,.2f}B" if abs(x) >= 1e9 else f"${x / 1e6:,.0f}M"


def match_rule(kind, rules):
    for keys, val in rules:
        if any(k in kind for k in keys):
            return val
    return None


WITHHELD = "(impact figure withheld: flagged suspect)"


def _drug(slug):
    return "-".join(w[:1].upper() + w[1:] for w in slug.split("-"))


_MFP_FIX = None
FIX_COUNT = {"mfp_text": 0, "ira_status": 0}


def mfp_fixes():
    """[(averaged value the engine printed, initial MFP)] for drugs whose engine MFP mixed two effective years
    (agent.needle.detect.labels takes the median over every row of the first IPAY, e.g. Eliquis 234.125)."""
    global _MFP_FIX
    if _MFP_FIX is None:
        _MFP_FIX = []
        for p in sorted(DRUGS.glob("*/ira_negotiation.csv")):
            df = pd.read_csv(p, low_memory=False)
            ip = pd.to_numeric(df["IPAY"], errors="coerce")
            rows = df[ip == ip.min()]
            v = pd.to_numeric(rows["Single MFP per 30 DES"], errors="coerce")
            d = pd.to_datetime(rows["MFP Effective Date"], errors="coerce")
            ok = v.notna() & d.notna()
            if not ok.any():
                continue
            avg, init = float(v[ok].median()), float(v[ok & (d == d[ok].min())].median())
            if abs(avg - init) > 0.001:
                _MFP_FIX.append((avg, init))
    return _MFP_FIX


def fix_mfp_text(t):
    """Rewrite an averaged MFP figure printed after 'MFP' or 'MFP/30d' to the initial MFP."""
    for avg, init in mfp_fixes():
        forms = sorted({f"{avg:,.2f}", f"{avg:.2f}", f"{avg:g}"}, key=len, reverse=True)
        pat = r"(MFP(?:/30d)?:? \$?)(" + "|".join(re.escape(x) for x in forms) + r")(?![\d])"
        t, n = re.subn(pat, lambda m: m.group(1) + (f"{init:,.2f}" if "," in m.group(2) or m.group(1).endswith("$")
                                                     else f"{init:.2f}"), t)
        FIX_COUNT["mfp_text"] += n
    return t


def plain(text):
    """Sentence cleanup for display: Python dict text -> plain English, drug names capitalised, odd characters
    normalized. The original stays in finding_raw for the verifier trail."""
    if not text:
        return text
    t = text.replace("\u00a0", " ").replace("\u2011", "-").replace("\u200b", "")

    def dict_to_words(m):
        try:
            d = ast.literal_eval("{" + m.group(1) + "}")
            return "(" + ", ".join(f"{_drug(str(k))} {v:g}" if isinstance(v, (int, float)) else f"{_drug(str(k))} {v}"
                                   for k, v in d.items()) + ")"
        except Exception:
            return m.group(0)

    t = re.sub(r"\(\{([^{}]*)\}\)", dict_to_words, t)
    t = t.replace("MFP/30d None", "MFP/30d not yet published")
    t = fix_mfp_text(t)
    t = re.sub(r"\bdeflected a other question\b", "deflected a question (topic not classified)", t)
    for slug in all_slugs_global():
        t = re.sub(rf"(?<![\w/:.-]){re.escape(slug)}(?![\w-])", _drug(slug), t)
    return t[:1].upper() + t[1:]


def impact_txt(f, proxy=False):
    """' Impact: <formula>.' for stated dollars (or any formula when proxy=True); withheld note when suspect."""
    imp = f["impact"]
    if imp.get("suspect"):
        return " " + WITHHELD
    if imp.get("placeholder"):
        return f" ({imp.get('suspect_note')})" if proxy else ""
    if imp.get("formula") and (imp.get("dollars") or imp.get("quantified") or proxy):
        return f" Impact: {imp['formula']}."
    return ""


# peer basis: kinds whose metric is a year-over-year change while peer_median is a level
CHANGE_VS_LEVEL = {"dio_rising", "dso_rising", "tax_rate_shift", "rnd_shift", "gross_margin_drop"}
CHANGE_VS_CHANGE = {"receivables_outpace_revenue", "inventory_outpaces_revenue", "rec_gap_peer_outlier",
                    "faers_serious_rising", "demand_divergence"}


def peer_basis(kind, finding, peer):
    """(comparable, basis, note) for a finding's peer block."""
    if kind in CHANGE_VS_LEVEL or (kind not in CHANGE_VS_CHANGE and "a year earlier" in finding and "peer median" in finding):
        return False, "yoy_change", ("metric_value is the change vs a year earlier, peer_median is the peers' level; "
                                     "compare the level in the finding text, not these two numbers")
    basis = "yoy_change" if kind in CHANGE_VS_CHANGE else "level"
    if peer.get("metric_value") is None or peer.get("peer_median") is None:
        return False, basis, "no peer median for this signal; metric_value stands alone"
    return True, basis, None


# ---------------------------------------------------------------- quote location (excerpt)
ZW = set("​‌‍﻿­")
TR = {"‘": "'", "’": "'", "“": '"', "”": '"', "–": "-", "—": "-", " ": " "}


def _normmap(text):
    """Normalized copy of text plus, for each normalized char, its index in the original."""
    out, idx = [], []
    for i, c in enumerate(text):
        if c in ZW:
            continue
        c = TR.get(c, c)
        for ch in unicodedata.normalize("NFKC", c):
            out.append(TR.get(ch, ch))
            idx.append(i)
    return "".join(out), idx


def _pattern(q):
    words = [w for w in re.split(r"\s+", q.strip()) if w]
    return r"\s*".join(re.escape(w) for w in words) if words else None


def locate(text, quote):
    """(start, end, how) of quote in text, original coordinates; how in {full, prefix} or None."""
    if not text or not quote:
        return None
    norm, idx = _normmap(text)
    q, _ = _normmap(quote)
    q = " ".join(q.split())
    for cand, how in ((q, "full"), (q[:120], "prefix"), (q[:60], "prefix"), (q[-60:], "suffix")):
        pat = _pattern(cand)
        if pat and len(cand) >= 20:
            m = re.search(pat, norm, flags=re.I)
            if m:
                return idx[m.start()], idx[m.end() - 1] + 1, how
    return None


_PAGES = {}


def page_text(doc_id, page):
    row = pages.manifest().get(doc_id)
    if not row:
        return None, None
    if doc_id not in _PAGES:
        try:
            _PAGES[doc_id] = pages.parse(ROOT / row["path"])[0]
        except Exception:
            _PAGES[doc_id] = {}
    pg = _PAGES[doc_id].get(page)
    return (pg[1], pg[0]) if pg else (None, None)


_LABELS = {}


def label_text(slug, fname):
    key = (slug, fname)
    if key not in _LABELS:
        p = DRUGS / slug / fname
        _LABELS[key] = p.read_text(encoding="utf-8", errors="ignore") if p.exists() else None
    return _LABELS[key]


def excerpt(ev, side):
    """{before, match, after, located, how, scope} for one evidence item."""
    d = ev.get("doc_id") or ""
    scope = "page"
    if d.startswith("drug:"):
        _, slug, fname = d.split(":", 2)
        text, scope = label_text(slug, fname), "label section"
    else:
        text, _ = page_text(d, ev.get("page"))
    if not text:
        return {"before": "", "match": "", "after": "", "located": False, "how": None,
                "scope": "source not found in corpus"}
    hit = locate(text, ev.get("quote") or "")
    if not hit:
        return {"before": text[: 2 * side].strip(), "match": "", "after": "", "located": False, "how": None,
                "scope": scope + " (quote not located; page head shown)"}
    s, e, how = hit
    lo, hi = max(0, s - side), min(len(text), e + side)
    if scope == "label section":  # clip to the enclosing ## section of the label
        heads = [m.start() for m in re.finditer(r"^#{2,4} .*$", text, flags=re.M)]
        lo = max(lo, max([h for h in heads if h <= s], default=0))
        hi = min(hi, min([h for h in heads if h >= e], default=len(text)))
    return {"before": text[lo:s], "match": text[s:e], "after": text[e:hi], "located": True, "how": how,
            "scope": scope}


# ---------------------------------------------------------------- evidence metadata
_GRADES = None


def grade_for(doc_id):
    global _GRADES
    if _GRADES is None:
        _GRADES = {(r["ticker"], r["quarter"]): r for r in csv_rows(VER / "calls" / "transcript_grades.csv")}
    m = re.match(r"([A-Z]+):transcripts/(\d{4}Q\d)", doc_id or "")
    if not m:
        return None, None
    r = _GRADES.get((m.group(1), m.group(2)))
    return (r.get("grade"), r.get("reason")) if r else (None, None)


_LABEL_URL = {}


def label_url(slug):
    if slug not in _LABEL_URL:
        t = label_text(slug, "label_sections.md") or ""
        m = re.search(r"setid=([0-9a-f-]+)", t[:800])
        _LABEL_URL[slug] = f"https://dailymed.nlm.nih.gov/dailymed/drugInfo.cfm?setid={m.group(1)}" if m else None
    return _LABEL_URL[slug]


def doc_label(ev):
    """Citation label of the document (no page), for answer traces."""
    c = ev.get("citation") or ""
    if c:
        c = re.split(r", (?:p\. |file page |Item )", c)[0]
        c = re.sub(r" §[\d.]+.*$| Boxed Warning.*$", "", c)
        return c.strip()
    return ev.get("doc_id")


def enrich_evidence(ev, side):
    d = ev.get("doc_id") or ""
    out = dict(ev)
    if d.startswith("drug:"):
        slug = d.split(":")[1]
        out.update(url=label_url(slug), doc_type="fda_label", source_quality="official", grade=None)
    else:
        row = pages.manifest().get(d) or {}
        g, why = grade_for(d)
        out.update(url=row.get("source_url"), doc_type=row.get("doc_type"),
                   source_quality=row.get("source_quality") or ("official" if row else None), grade=g)
        if why:
            out["grade_reason"] = why
    out["doc_label"] = doc_label(ev)
    out["excerpt"] = excerpt(ev, side)
    return out


# ---------------------------------------------------------------- findings
def detector_of(f):
    parts = f["id"].split("-")
    return parts[1] if len(parts) >= 3 else ""


def signal_links(ticker):
    """{signal detail: [urls]} from out/<T>/signals_*.jsonl meta, for findings that carry no page evidence."""
    out = {}
    for p in (OUT / ticker).glob("signals_*.jsonl"):
        for s in read_jsonl(p):
            meta = s.get("meta") or {}
            urls = [u for u in (meta.get("url"), (meta.get("data") or {}).get("source_url"), meta.get("source"))
                    if isinstance(u, str) and u.startswith("http")]
            if urls and s.get("detail"):
                out.setdefault(s["detail"], list(dict.fromkeys(urls)))
    return out


def build_findings(raw, side, ticker=""):
    top = max([f.get("score") or 0 for f in raw] or [0])
    links = signal_links(ticker) if ticker else {}
    seen, out = {}, []
    for f in raw:
        imp = f.get("impact") or {}
        seen[f["id"]] = seen.get(f["id"], 0) + 1
        uid = f["id"] if seen[f["id"]] == 1 else f"{f['id']}-d{seen[f['id']]}"
        oi = imp.get("ttm_operating_income")
        suspect = bool(imp.get("dollars") and oi and abs(imp["dollars"]) > abs(oi))
        vec = f.get("vector") or {}
        peer = f.get("peer") or {}
        comparable, basis, pnote = peer_basis(f["signal_kind"], f["finding"], peer)
        out.append({
            "id": uid, "source_id": f["id"], "finding": plain(f["finding"]), "finding_raw": f["finding"], "signal_kind": f["signal_kind"], "detector": detector_of(f),
            "score": f.get("score"), "score_norm": round((f.get("score") or 0) / top, 4) if top else None,
            "confidence": f.get("confidence"), "verdict": f.get("verdict"), "reason": f.get("reason"),
            "impact": {"formula": imp.get("formula"), "dollars": imp.get("dollars"), "base": imp.get("base"),
                       "bear": imp.get("bear"), "bull": imp.get("bull"), "line": imp.get("line"),
                       "eps": imp.get("eps"), "i_norm": imp.get("i_norm"),
                       "ttm_operating_income": oi, "suspect": suspect,
                       "suspect_note": ("impact dollars exceed trailing operating income; likely a level-vs-change "
                                        "error in the formula, so it is left out of stance dollars") if suspect else None},
            "peer": {"metric_value": peer.get("metric_value"), "peer_median": peer.get("peer_median"),
                     "z": peer.get("z"), "note": peer.get("note") or pnote, "comparable": comparable,
                     "basis": basis},
            "vector": {k: vec.get(k) for k in ("I_norm", "P", "T", "Z", "D", "O", "E")} |
                      {"obscurity_note": vec.get("obscurity_note"), "topics": vec.get("topics") or [],
                       "prior": vec.get("prior")},
            "hit_rate": f.get("hit_rate") or {}, "outside": f.get("outside") or {},
            "evidence": [enrich_evidence(e, side) for e in f.get("evidence") or []],
            "external_sources": [] if f.get("evidence") else links.get(f["finding"], []),
            "numeric_check": numeric_check(f.get("numeric_check")),
        })
    out.sort(key=lambda x: -(x["score"] or 0))
    return out


# ---------------------------------------------------------------- v2 engine output (agent.needle.quant)
PLACEHOLDER_NOTE = "impact is the generic 3%-of-revenue placeholder; no page-verified number backs it, so it is not summed"


# docs/citations.md: exact / substring / fuzzy / number_match support a number; "derived" citations are computed from
# cited operands (e.g. Q4 = FY minus Q1-Q3, review D11) and are shown; every other status is withheld.
PUBLIC_STATUSES = {"exact", "substring", "fuzzy", "number_match", "derived"}
PAGE_PASS = {"exact", "substring", "fuzzy", "number_match"}   # statuses that may back a derived citation's operands


def derived_operands(c):
    """Operand cite_ids of a derived citation: the structured `operands` list when the engine writes it, else parsed
    from the verification detail ('... (c_0103942818), ...'). Either way the caller checks them against the record."""
    ops = c.get("operands")
    if isinstance(ops, list) and ops:
        return [o if isinstance(o, str) else (o or {}).get("cite_id") for o in ops]
    text = (c.get("verification") or {}).get("detail") or c.get("confidence_note") or ""
    return re.findall(r"\((c_[0-9a-f]{6,})\)", text)
NC_KEYS = ("checked", "total", "verified", "derived", "assumed")


def assert_no_repr(obj, path="$"):
    """Fail the export if any str()-serialised Citation or Claim survives anywhere in the output."""
    if isinstance(obj, str):
        if re.search(r"\bCitation\(canonical_id=|\bClaim\(text=|\bCitation\(|\bClaim\(", obj) and \
                not path.endswith("_md"):  # doc text fields (*_md) may name the classes in prose
            raise ValueError(f"{path} carries a repr string: {obj[:80]}")
    elif isinstance(obj, dict):
        for k, v in obj.items():
            assert_no_repr(v, f"{path}.{k}")
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            assert_no_repr(v, f"{path}[{i}]")


def assert_numeric_checks(obj, path="$"):
    """Fail the export if any record claims 'passed' with checked == 0 or without the verified/derived/assumed
    breakdown, or carries a numeric_check that is not a dict with a status."""
    if isinstance(obj, dict):
        if "numeric_check" in obj:
            nc = obj["numeric_check"]
            if not isinstance(nc, dict) or not nc.get("status"):
                raise ValueError(f"{path}.numeric_check is not a status dict: {nc!r}")
            if nc["status"] == "passed" and (not nc.get("checked") or any(k not in nc for k in NC_KEYS)):
                raise ValueError(f"{path}.numeric_check says passed without a checked count or breakdown")
            if nc["status"] == "no_numbers" and (nc.get("total") != 0 or nc.get("checked") or nc.get("unsupported")):
                raise ValueError(f"{path}.numeric_check says no_numbers but total = {nc.get('total')}")
        for k, v in obj.items():
            assert_numeric_checks(v, f"{path}.{k}")
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            assert_numeric_checks(v, f"{path}[{i}]")


def numeric_check(x):
    """Pass numeric_check through; missing / null / empty / malformed -> {status: unchecked}. A 'passed' with
    checked == 0 or without the verified/derived/assumed breakdown is never trusted as passed."""
    if not isinstance(x, dict) or not x.get("status"):
        return {"status": "unchecked"}
    out = dict(x)
    out.setdefault("unsupported", [])
    if out["status"] in ("passed", "no_numbers") and out.get("total") == 0 and not out.get("checked") \
            and not out["unsupported"]:
        # the gate ran and the record has no numbers: its own status, never shown as "passed"
        return {"status": "no_numbers", "checked": 0, "total": 0, "verified": 0, "derived": 0, "assumed": 0,
                "unsupported": [], "note": "no numbers to check"}
    if out["status"] == "passed" and (not out.get("checked") or any(k not in out for k in NC_KEYS)):
        return {"status": "unchecked", "note": "reported passed without a checked count or breakdown", "raw": x}
    return out


def withhold_reason(c, pool=None):
    """None when the citation may show its quote and links; else the reason. Bloomberg is withheld whatever the
    status; machine_data / unverified / unverified_onboard and any other non-whitelisted status never export text;
    a derived citation is public only when every operand is in `pool` with a passing page status and is itself public."""
    st = (c.get("verification") or {}).get("status")
    if "bloomberg" in (c.get("license") or "").lower():
        return "Bloomberg-licensed source: quote and links withheld from the public export"
    if st == "machine_data" or "machine_data" in ((c.get("raw_doc_type") or "") + (c.get("doc_type") or "")):
        return "machine data, no page copy"
    if st == "derived":
        ops = derived_operands(c)
        pool = pool or {}
        if not ops or any(o not in pool or (pool[o].get("verification") or {}).get("status") not in PAGE_PASS
                          or withhold_reason(pool[o], pool) for o in ops):
            return "operand not page-verified"
        return None
    if st not in PUBLIC_STATUSES:
        return f"citation status {st or 'missing'} is not public (did not verify): quote and links withheld" + \
               (f" ({c['confidence_note']})" if c.get("confidence_note") else "")
    return None


def _resolve_doc(cid):
    """Corpus or moat page file for a v2 canonical_id, or None."""
    if cid in pages.manifest():
        return cid
    return None


def _moat_pages(cid, page):
    """Page text for ids the corpus manifest does not know (policy_gov:..., moat paths)."""
    if ":" not in cid:
        return None
    pre, rel = cid.split(":", 1)
    for base in (MOAT / rel, MOAT / pre / rel, ROOT / "data" / "corpus" / rel, MOAT / "companies" / pre / rel):
        if base.exists() and base.suffix == ".md":
            key = str(base)
            if key not in _PAGES:
                try:
                    _PAGES[key] = pages.parse(base)[0]
                except Exception:
                    _PAGES[key] = {}
            pg = _PAGES[key].get(page)
            return pg[1] if pg else None
    return None


def citation_evidence(c, side, pool=None):
    """One v2 Citation -> evidence item (contract keys plus v2 keys); public withholding rule applied.
    `pool` is {cite_id: citation} for the record, used to check a derived citation's operands."""
    cid = c.get("canonical_id") or ""
    why = withhold_reason(c, pool)
    derived = (c.get("verification") or {}).get("status") == "derived"
    ev = {"doc_id": cid, "page": c.get("page"), "printed": c.get("folio") or "",
          "citation": f"{c.get('doc_title')}, {c.get('location')}" + (
              f" (file page {c['page']})" if c.get("page") and c.get("page_scheme") == "marker" else ""),
          "quote": "" if why else (c.get("quote") or ""), "speaker": c.get("speaker") or "", "figures": [],
          "url": None if why else (c.get("source_url") or None), "deep_link": "" if why else (c.get("deep_link") or ""),
          "viewer_link": (c.get("viewer_link") or "") if (not why or why == "machine data, no page copy")
          else "",
          "doc_type": c.get("raw_doc_type") or c.get("doc_type") or None, "cite_id": c.get("cite_id"),
          "doc_title": c.get("doc_title"), "period": c.get("period"), "location": c.get("location"),
          "claim_type": c.get("claim_type"), "value": c.get("value"), "unit": c.get("unit"),
          "license": c.get("license") or None, "verification": c.get("verification"),
          "confidence_note": c.get("confidence_note") or "", "withheld": bool(why), "withheld_reason": why}
    if (c.get("verification") or {}).get("status") == "number_match" and not why:
        # docs/citations.md: the quote did not verify; the public footnote shows page text around the number
        if c.get("page") is None and c.get("value") not in (None, ""):
            # data row with no page (XBRL frame): show the cited value on its concept, not a quote
            ev["quote"] = f"{c.get('location') or c.get('doc_title')} = {c.get('value')}"
            ev["quote_note"] = "constructed from the cited value (no page); not a verbatim quote"
        else:
            ev["quote"] = ""
            ev["quote_note"] = "the quote did not verify; the number is on the cited page"
    if derived:  # never rendered as a quote: the UI shows "derived from [a][b]"
        ev.update(quote="", deep_link="", viewer_link="", url=None, derived_from=derived_operands(c),
                  derived_expr=None if why else (c.get("quote") or None))
        if why:
            ev["confidence_note"] = ""
            ev["verification"] = {k: v for k, v in (c.get("verification") or {}).items() if k != "detail"}
    row = pages.manifest().get(cid) or {}
    ev["source_quality"] = row.get("source_quality") or ("official" if (row or cid.startswith(("drug:", "policy_gov:", "xbrl:"))) else None)
    g, gwhy = grade_for(cid)
    ev["grade"] = g
    if gwhy:
        ev["grade_reason"] = gwhy
    ev["doc_label"] = c.get("doc_title") or cid
    if why:
        ev["excerpt"] = {"before": "", "match": "", "after": "", "located": False, "how": None,
                         "scope": "withheld", "withheld": True}
    elif derived:
        ev["excerpt"] = {"before": "", "match": "", "after": "", "located": False, "how": None, "scope": "derived"}
    elif c.get("page_scheme") in ("marker", "section") and c.get("page") is not None:
        q = c.get("quote")
        if (c.get("verification") or {}).get("status") == "number_match" and c.get("value"):
            q = str(c["value"])
        if cid.startswith("drug:") or _resolve_doc(cid):
            ev["excerpt"] = excerpt({"doc_id": cid, "page": c["page"], "quote": q}, side)
        else:
            text = _moat_pages(cid, c["page"])
            hit = locate(text, c.get("quote") or "") if text else None
            if hit:
                a, b, how = hit
                ev["excerpt"] = {"before": text[max(0, a - side):a], "match": text[a:b], "after": text[b:b + side],
                                 "located": True, "how": how, "scope": "page"}
            else:
                ev["excerpt"] = {"before": (text or "")[: 2 * side], "match": "", "after": "", "located": False,
                                 "how": None, "scope": "page not resolvable locally" if not text else "page (quote not located)"}
    else:
        ev["excerpt"] = {"before": "", "match": "", "after": "", "located": False, "how": None,
                         "scope": "data row (no page)"}
    return ev


def _usd(x, cur):
    return None if x is None or cur != "USD" else round(x * 1e6, 2)


def first_existing(*paths):
    """First path that exists (engine output preference: v3 > v2 > v1)."""
    return next((p for p in paths if Path(p).exists()), None)


def guard_fields(f):
    """v3 guard and corroboration fields of one row -> (extra flag codes, export dict)."""
    notes = f.get("flags") or []
    codes = []
    if any("one-off" in x and x.startswith("guard") for x in notes):
        codes.append("one_off")
    if f.get("not_quantified"):
        codes.append("not_quantified")
    if f.get("needle_eligible"):
        codes.append("needle_eligible")
    cor = next((m.group(1) for x in notes for m in [re.match(r"corroborates ([0-9a-f]{6,})", x)] if m), None)
    return codes, {"fact_key": f.get("fact_key"), "guard": f.get("guard"),
                   "guard_reason": next((x for x in notes if re.match(r"guard \d+:", x)), None),
                   "not_quantified": f.get("not_quantified"), "impact_channel": f.get("impact_channel"),
                   "corroborates": cor, "numeric_check": numeric_check(f.get("numeric_check")),
                   **({"derived": compact_derived(f["derived"])} if f.get("derived") else {}),
                   **{k: f[k] for k in ("sentence_marked", "assumptions", "aliases", "rejected_by") if f.get(k)}}


def compact_derived(dmap):
    """Gate `derived` map with operand Citations replaced by their cite_id (the Citation is inline in the record's
    citations, exported and withheld there); nested derived / assumption operands are kept as given."""
    def op(v):
        if isinstance(v, dict) and isinstance(v.get("citation"), dict):
            return {"value": v.get("value"), "cite_id": v["citation"].get("cite_id")}
        if isinstance(v, dict) and "cite_id" in v and "verification" in v:
            return {"value": v.get("value"), "cite_id": v.get("cite_id")}
        return v
    return {k: ({**e, "operands": {n: op(v) for n, v in (e.get("operands") or {}).items()}} if isinstance(e, dict) else e)
            for k, e in (dmap or {}).items()}


_MARK = re.compile(r"\[(\d+)\]|\[derived: ([^\]]+)\]|\[constant: ([A-Z0-9_]+)\]|\[assumption(?:: [^\]]*)?\]")
_FOOT = re.compile(r"^\[(\d+)\] (.*?) -- (\"(?:.*)\"|\[licensed text withheld\]|[^-]*?)(?: -- .*?)?(?: · verified: (\w+))?$")


def split_md(md):
    """(marked text, {n: footnote line}) from an engine *_md field ('text[1]...\n\n**Sources**\n\n[1] ...')."""
    if not md:
        return md, {}
    text, _, foot = md.partition("\n\n**Sources**")
    notes = {}
    for line in foot.splitlines():
        m = re.match(r"^\[(\d+)\] (.*)$", line.strip())
        if m:
            notes[int(m.group(1))] = m.group(2)
    return text.strip(), notes


def marker_map(notes, citations):
    """{n: cite_id} matching each footnote '<doc_title>, <location> ... -- "<quote>"' to the record's citations."""
    out, used = {}, set()
    for n, line in sorted(notes.items()):
        head = line.split(" -- ")[0]
        qm = re.search(r' -- "(.*)" -- ', line + " -- ")
        q = qm.group(1) if qm else None
        cand = [c for c in citations if c.get("cite_id") not in used
                and head.startswith(f"{c.get('doc_title')}, {c.get('location')}")]
        hit = next((c for c in cand if q is not None and (c.get("quote") or "") == q), None) or \
              (cand[0] if len(cand) == 1 or (cand and q is None) else None)
        out[n] = hit.get("cite_id") if hit else None
        if hit:
            used.add(hit.get("cite_id"))
    return out


def marker_kinds(text):
    """Counts of marker kinds in a marked text, plus any bracket token the parser does not know."""
    kinds, unknown = collections.Counter(), []
    for m in re.finditer(r"\[[^\]]*\]", text or ""):
        tok = m.group(0)
        if re.fullmatch(r"\[\d+\]", tok):
            kinds["cite"] += 1
        elif tok.startswith("[derived: "):
            kinds["derived"] += 1
        elif tok.startswith("[constant: "):
            kinds["constant"] += 1
        elif tok == "[assumption]":
            kinds["assumption"] += 1
        elif tok.startswith("[assumption: "):
            kinds["assumption_reason"] += 1
        else:
            unknown.append(tok)
    return dict(kinds), unknown


def text_states(text, amount, money=True, forms=None):
    """Does text print `amount` (or one of `forms`)? money=True needs a currency sign or scale word on the token and
    compares absolute values within the printed precision or 0.5%, whichever is larger."""
    if amount is None or not text:
        return False
    from agent.needle.cite.numbers import tokenize, tolerance
    targets = [abs(x) for x in (forms or [amount]) if x is not None]
    for t in tokenize(text):
        if t.kind != "number" or (money and not (t.currency or t.scale)):
            continue
        v = abs(t.value())
        for a in targets:
            if abs(v - a) <= max(tolerance(t, t.scale or 1.0), 0.005 * a):
                return True
    return False


def gate_figures(row, raw):
    """Export impact dollars and the peer metric only when gated text states them (review: no ungated numbers).
    Gated impact text (engine field impact.text / impact_text) wins; until the engine writes it, the finding sentence
    is the only gated text. Otherwise dollars, bear/base/bull and the raw d_* paths are nulled, impact.direction keeps
    the sign and impact.gated is false. peer.metric_value is nulled when the sentence does not print it."""
    imp = row["impact"]
    rimp = raw.get("impact") or {}
    gtext = rimp.get("text") or raw.get("impact_text") or \
        (_MARK.sub("", split_md(raw.get("formula_md"))[0] or "") if raw.get("formula_md") else None)
    if gtext and not raw.get("formula_md"):
        imp["text"] = plain(gtext)
    src = " ".join(x for x in (gtext, raw.get("sentence")) if x)
    amount = imp.get("dollars")
    stated = bool(amount) and text_states(src, amount)
    base = imp.get("base")
    imp["direction"] = None if not base else ("negative" if base < 0 else "positive")
    imp["gated_by"] = "impact.text" if gtext else "sentence"
    if amount and not stated:
        imp["ungated_dropped"] = True
        for k in ("dollars", "base", "bear", "bull", "eps"):
            imp[k] = None
        for k in ("d_rev", "d_oi", "d_eps"):
            imp[k] = None
    imp["gated"] = bool(stated)
    pr = row["peer"]
    mv = pr.get("metric_value")
    if mv is not None:
        forms = [mv, mv * 100]
        if not text_states(raw.get("sentence") or "", mv, money=False, forms=forms):
            pr["metric_value"] = None
            pr["metric_value_gated"] = False
        else:
            pr["metric_value_gated"] = True
    return row


def build_findings_v2(raw, side, ticker, lg, v1):
    """v2 rows -> the same finding shape the v1 path exports, plus v2 keys."""
    top = max([f.get("S") or 0 for f in raw] or [0])
    const = (lg or {}).get("constants") or {}
    cur = const.get("currency") or "USD"
    rev = const.get("Rev_TTM")
    needle_id = ((lg or {}).get("needle") or {}).get("id")
    status = ((lg or {}).get("needle_status") or "").replace(" ", "_")
    company_comparable = (lg or {}).get("comparable", True)
    v1i = {(r["signal_kind"], r["finding"]): r for r in v1}
    seen, out = {}, []
    for f in raw:
        seen[f["id"]] = seen.get(f["id"], 0) + 1
        uid = f["id"] if seen[f["id"]] == 1 else f"{f['id']}-d{seen[f['id']]}"
        imp, vec, peer = f.get("impact") or {}, f.get("vector") or {}, f.get("peer") or {}
        notes = f.get("flags") or []
        placeholder = any("generic anchor placeholder" in x for x in notes)
        d_oi = (imp.get("d_oi") or {})
        base = d_oi.get("base")
        suspect = bool(base and rev and abs(base) > abs(rev))
        gcodes, gexp = guard_fields(f)
        flags = list(gcodes)
        if placeholder:
            flags.append("generic_placeholder")
        if f["id"] == needle_id and status and status != "strict":
            flags.append("provisional")
        if not company_comparable or any("not league-comparable" in x or "not converted" in x for x in notes):
            flags.append("not_league_comparable")
        old = v1i.get((f["signal_kind"], f["sentence"])) or {}
        ov = old.get("vector") or {}
        a, h = vec.get("a"), vec.get("h")
        quiet = (a == 0 and h == 0)
        onote = (f"not in the earnings-release headline and not asked on calls; {vec.get('a_source')}" if quiet else
                 f"raised: headline h {h if h is not None else 'n/a'}, analyst attention a "
                 f"{a if a is not None else 'n/a'}; {vec.get('a_source')}")
        comparable, basis, pnote = peer_basis(f["signal_kind"], f["sentence"], {"metric_value": peer.get("metric_value"),
                                                                             "peer_median": peer.get("peer_median")})
        cits = f.get("citations") or []
        paged = [c for c in cits if c.get("page_scheme") in ("marker", "section")]
        lic = [c for c in cits if c not in paged and (c.get("license") or "")]
        data = [c for c in cits if c not in paged and c not in lic]
        pool = {c.get("cite_id"): c for c in cits}
        evid = [citation_evidence(c, side, pool) for c in (paged or data)]
        out.append({
            "id": uid, "source_id": f["id"], "finding": plain(f["sentence"]), "finding_raw": f["sentence"],
            "signal_kind": f["signal_kind"], "signal_family": f.get("signal_family"), "has_detector": f.get("has_detector"),
            "detector": f.get("detector") or detector_of(f), "block": f.get("block"), "channel": f.get("channel"),
            "direction": f.get("direction"),
            "score": f.get("S"), "score_norm": round((f.get("S") or 0) / top, 4) if top else None,
            "old_score": f.get("old_S"),
            "confidence": (f.get("confidence") or "").lower(), "confidence_reasons": f.get("confidence_reasons") or [],
            "verdict": "verified", "reason": "", "flags": flags, "flag_notes": notes,
            "needle_eligible": f.get("needle_eligible"),
            "impact": {"formula": imp.get("formula"), "dollars": _usd(base, cur),
                       "base": _usd(base, cur), "bear": _usd(d_oi.get("bear"), cur), "bull": _usd(d_oi.get("bull"), cur),
                       "line": imp.get("channel"), "eps": (imp.get("d_eps") or {}).get("base"),
                       "currency": cur, "units": f"{cur} millions (d_rev, d_oi)", "d_rev": imp.get("d_rev"),
                       "d_oi": d_oi, "d_eps": imp.get("d_eps"), "quantified": imp.get("quantified"),
                       "adverse": imp.get("adverse"), "impact_flags": imp.get("flags") or [],
                       "placeholder": placeholder, "suspect": suspect,
                       "excluded": bool(suspect or placeholder or cur != "USD" or f.get("not_quantified")),
                       "suspect_note": ("impact exceeds trailing revenue; left out of stance dollars" if suspect else
                                        PLACEHOLDER_NOTE if placeholder else None)},
            "peer": {"metric_value": peer.get("metric_value"), "peer_median": peer.get("peer_median"),
                     "z": peer.get("peer_z"), "rival": peer.get("rival"), "analogs": peer.get("analogs"),
                     "note": pnote, "comparable": comparable, "basis": basis},
            "vector": {"I_norm": ov.get("I_norm"), "P": vec.get("pi"), "T": ov.get("T"), "Z": peer.get("peer_z"),
                       "D": ov.get("D"), "O": vec.get("O"), "E": vec.get("E"), "obscurity_note": onote,
                       "topics": vec.get("topics") or [], "prior": ov.get("prior"),
                       "signal_family": f.get("signal_family"), "has_detector": f.get("has_detector"),
                       "v2": {"M": vec.get("M"), "O": vec.get("O"), "E": vec.get("E"), "pi": vec.get("pi"),
                              "S": f.get("S"), "old_S": f.get("old_S"),
                              **{k: vec.get(k) for k in ("z", "h", "a", "c", "s", "H", "age_months", "disclosed",
                                                         "E_pages", "n_ind", "pi_route", "a_source", "sigma_EPS",
                                                         "sigma_currency", "dEPS_base", "headline_doc")}}},
            "hit_rate": {}, "outside": {},
            "evidence": evid,
            "data_citations": [citation_evidence(c, side, pool) for c in data] if paged else [],
            "licensed_inputs": {"count": len(lic), "license": sorted({c["license"] for c in lic}),
                                "sources": sorted({c.get("doc_title") or c.get("canonical_id") for c in lic}),
                                "note": "licensed data rows (I/B/E/S via WRDS) used as model inputs; values not exported"} if lic else None,
            "external_sources": [],
            **gexp,
        })
        gate_figures(out[-1], f)
        fr = next((x for x in notes if x.startswith("footnote read:")), None)
        out[-1]["explained_by_footnote"] = bool(fr and "explained by footnote" in fr)
        out[-1]["explained_by_footnote_note"] = fr
        out[-1]["footnote_read"] = f.get("footnote_read") or ({"status": "explained by footnote" if "explained by footnote" in fr
                                                                else "terms found", "text": fr} if fr else None)
        for k in ("nugget", "corroborated_by", "merged_into"):
            if f.get(k):
                out[-1][k] = f[k]
        if f.get("sentence_md") or f.get("formula_md"):
            st_, notes = split_md(f.get("sentence_md"))
            fo_, fnotes = split_md(f.get("formula_md"))
            notes = {**fnotes, **notes}
            row = out[-1]
            row["sentence_marked"] = plain(st_) if st_ else None
            row["formula_marked"] = fo_ or None
            if fo_:
                row["impact"]["text"] = fo_
            row["marker_map"] = marker_map(notes, cits)
            lic_ids = {c.get("cite_id") for c in lic}
            # markers that point at licensed data rows: shown as "licensed source" (values not exported)
            row["marker_licensed"] = sorted(n for n, cid in row["marker_map"].items() if cid in lic_ids)
            k1, u1 = marker_kinds(st_)
            k2, u2 = marker_kinds(fo_)
            row["marker_kinds"] = {"sentence": k1, "formula": k2}
            if u1 or u2:
                row["marker_unknown"] = u1 + u2
                MARKER_UNKNOWN.extend(u1 + u2)
    out.sort(key=lambda x: -(x["score"] or 0))
    return out


def rejected_v2(rows):
    out = []
    for r in rows:
        cits = [c for c in r.get("citations") or [] if c.get("page_scheme") in ("marker", "section")]
        out.append({"finding": plain(r.get("sentence")), "finding_raw": r.get("sentence"), "id": r.get("id"),
                    "signal_kind": r.get("signal_kind"), "verdict": "rejected",
                    "reason": ("numbers unsupported: " + "; ".join(f"{u.get('value')} ({u.get('where')}: {u.get('reason')})"
                                                                   for u in (r.get("numeric_check") or {}).get("unsupported") or [])
                               if r.get("rejected_by") == "numeric_gate" else
                               f"dropped by a review guard: {guard_fields(r)[1]['guard_reason'] or r.get('guard')}"
                               if r.get("guard") == "drop" else
                               "withheld by the evidence gate (E = 0: no page-verified citation). "
                               + "; ".join(x for x in r.get("confidence_reasons") or [] if "fails" in x or "<" in x)),
                    "guard": r.get("guard"), "fact_key": r.get("fact_key"), "numeric_check": numeric_check(r.get("numeric_check")),
                    "rejected_by": r.get("rejected_by"),
                    "unsupported": (r.get("numeric_check") or {}).get("unsupported") or [],
                    **{k: r[k] for k in ("sentence_marked", "aliases") if r.get(k)},
                    "evidence": [{"doc_id": c.get("canonical_id"), "page": c.get("page"), "doc_title": c.get("doc_title"),
                                  "location": c.get("location"), "speaker": c.get("speaker") or "",
                                  "quote": "" if withhold_reason(c) else c.get("quote"),
                                  "withheld": bool(withhold_reason(c)), "withheld_reason": withhold_reason(c),
                                  "verification": c.get("verification")} for c in cits]})
    return out


# ---------------------------------------------------------------- v2 product fine print (agent.needle.quant.product)
def cell_cite(c, side=400, pool=None):
    """Compact public citation for a product/decide cell (same withholding rule as findings)."""
    ev = citation_evidence(c, side, pool)
    keep = ("doc_id", "page", "printed", "citation", "quote", "speaker", "url", "deep_link", "viewer_link", "doc_type",
            "cite_id", "doc_title", "location", "claim_type", "value", "unit", "verification", "confidence_note",
            "withheld", "withheld_reason", "excerpt", "license", "derived_from", "derived_expr")
    return {k: ev.get(k) for k in keep}


def _cite_source(cell):
    cs = cell.get("citations") or []
    if cs:
        c = cs[0]
        why = withhold_reason(c, {x.get("cite_id"): x for x in cs})
        return f"{c.get('doc_title')}, {c.get('location')}" + (f" (citation withheld: {why})" if why else "")
    refs = cell.get("refs") or []
    if refs:
        return "; ".join(f"{r.get('file')} [{r.get('key')}]" for r in refs) + " (table ref, no page citation)"
    return None


def product_v2(ticker, slug):
    """out/<T>/product_<slug>.json -> labels.v2[slug] (public rule applied), or None."""
    d = read_json(OUT / ticker / f"product_{slug}.json")
    if not d:
        return None
    cmp_ = d.get("comparison") or {}
    ents = cmp_.get("entities") or []
    nc_by_where = {it.get("where"): it.get("numeric_check") for it in d.get("numeric_items") or []}
    uncited = {(u.get("row"), u.get("entity")): u for u in d.get("uncited_cells") or [] if isinstance(u, dict)}
    rows = {}
    for row, cells in (cmp_.get("rows") or {}).items():
        rows[row] = {}
        for ent in ents:
            cell = (cells or {}).get(ent["name"])
            if cell is None:
                continue
            unc = uncited.get((row, ent["name"]))
            rows[row][ent["name"]] = {"uncited": bool(unc), "verified": not unc,
                                      "numeric_check": numeric_check((unc or {}).get("numeric_check") or cell.get("numeric_check")
                                                                     or nc_by_where.get(f"{row}/{ent['name']}")
                                                                     or nc_by_where.get(f"empty/{row}/{ent['name']}")), "slug": ent.get("slug"), "value": plain(cell.get("value")) if isinstance(cell.get("value"), str) else cell.get("value"),
                                      "value_raw": cell.get("value"), "detail": clean(cell.get("detail")),
                                      "citations": [cell_cite(c, pool={x.get("cite_id"): x for x in cell.get("citations") or []})
                                                    for c in cell.get("citations") or []],
                                      "refs": cell.get("refs") or [], "empty_reason": cell.get("empty_reason") or "",
                                      "source": _cite_source(cell)}
    fnd = []
    for f in d.get("findings") or []:
        imp = f.get("impact") or {}
        fnd.append({"numeric_check": numeric_check(f.get("numeric_check")), "id": f.get("id"), "finding": plain(f.get("sentence")), "finding_raw": f.get("sentence"),
                    "channel": f.get("channel"), "direction": f.get("direction"),
                    "confidence": (f.get("confidence") or "").lower(), "confidence_reasons": f.get("confidence_reasons"),
                    "impact": ({"formula": imp.get("formula"), "dRev": imp.get("dRev"), "dOI": imp.get("dOI"),
                                "units": "USD", "CM": imp.get("CM"), "gated": True}
                               if numeric_check(f.get("numeric_check")).get("status") == "passed" else
                               {"formula": imp.get("formula"), "dRev": None, "dOI": None, "units": "USD",
                                "CM": imp.get("CM"), "gated": False,
                                "note": "dollar figures withheld: the finding did not pass the numeric gate"}),
                    "peer": f.get("peer"), "flags": f.get("flags"), "obscurity_note": f.get("obscurity_note"),
                    "evidence": [cell_cite(c, pool={x.get("cite_id"): x for x in f.get("citations") or []})
                                 for c in f.get("citations") or []]})
    gl = d.get("growth_limiter") or {}
    return {"product": slug, "entities": ents, "row_titles": cmp_.get("row_titles"), "rows": rows,
            "findings": fnd, "notes": cmp_.get("notes") or [], "context": clean(cmp_.get("context")),
            "growth_limiter": {"numeric_check": numeric_check(gl.get("numeric_check") or nc_by_where.get("growth_limiter")), "sentence": plain(gl.get("sentence")), "sentence_raw": gl.get("sentence"),
                               "priced_in": gl.get("priced_in"), "reasons": gl.get("reasons") or [],
                               "citations": [cell_cite(c, pool={x.get("cite_id"): x for x in gl.get("citations") or []})
                                             for c in gl.get("citations") or []]} if gl else None,
            "numeric_check": numeric_check(d.get("numeric_check")),
            "numeric_items": [{**it, "numeric_check": numeric_check(it.get("numeric_check"))} for it in d.get("numeric_items") or []],
            "table_value_cells": d.get("table_value_cells") or [], "withheld_lines": d.get("withheld_lines") or [],
            "uncited_cells": d.get("uncited_cells") or [], "empty_cells": d.get("empty_cells") or [],
            "source_file": f"out/{ticker}/product_{slug}.json"}


def _v2_values(v2, slug):
    """{field: {value, source, citation?}} for one slug from a product_v2 block (first entity with that slug)."""
    out = {}
    for row, cells in (v2.get("rows") or {}).items():
        cell = next((c for c in cells.values() if c.get("slug") == slug and not c.get("uncited")), None)
        if not cell or cell.get("value") in (None, ""):
            continue
        det = cell.get("detail") or {}
        src = cell.get("source")
        cit = (cell.get("citations") or [None])[0]

        def tref(*names):
            rs = [r for r in cell.get("refs") or [] if any(n in (r.get("file") or "") for n in names)]
            return "; ".join(f"{r['file']} [{r.get('key')}]" for r in rs) + " (table ref, no page citation)" if rs else None

        def put(field, value, table=None, **kw):
            if value is not None:
                t = tref(*table) if table else None
                out[field] = {"value": value, "source": t or src, "citation": None if t else cit, "from": "product_v2", **kw}
        if row == "approved_uses":
            put("indications_count", det.get("count"))
            put("indications", det.get("names"))
        elif row == "safety":
            bw = det.get("boxed_warning")
            put("boxed_warning", (f"Yes: {bw.get('heading')}" if isinstance(bw, dict) else ("Yes" if bw else "No")) if "boxed_warning" in det else None)
            put("rems", det.get("rems"))
        elif row == "dosing":
            put("dosing_frequency_per_year", det.get("doses_per_year"), text=det.get("frequency"))
            put("route", det.get("route"))
        elif row == "timeline":
            cs = det.get("company_stated") or {}
            put("exclusivity_company_stated", cs.get("us_loe"), basis=cs.get("basis"), stated_in=cs.get("source"))
            put("exclusivity_fda_estimate", det.get("protection_end_regulatory"), table=("orange_book", "purple_book"))
        elif row == "pricing":
            g = det.get("gtn_exposure") or {}
            put("gtn_exposure_call", g.get("exposure_call"), table=("gtn_exposure",), confidence=g.get("confidence"))
    return out


# fields where the exporter's own rule wins over a v2 cell (CMS MFP file rule, see mfp_cell)
KEEP_EXPORTER = {"ira_status", "mfp_per_30day", "mfp_latest_per_30day", "partd_spend_latest", "generic_or_biosimilar_status"}


def prefer_v2(comparison_rows, v2_by_product):
    n = 0
    for block in comparison_rows:
        v2 = v2_by_product.get(block["product"])
        if not v2:
            continue
        for slug in [block["product"], *block["rivals"]]:
            vals = _v2_values(v2, slug)
            for r in block["rows"]:
                if r["field"] in vals and r["field"] not in KEEP_EXPORTER:
                    old = r["values"].get(slug) or {}
                    r["values"][slug] = vals[r["field"]] | {"v1_value": old.get("value"), "v1_source": old.get("source")}
                    n += 1
    return n


# ---------------------------------------------------------------- v2 CEO move (agent.needle.quant.decide)
FIVE = ("ev", "car", "payback_month", "spread", "mcda")


def _move_row(m):
    return {"name": m.get("name"), "code": m.get("code"), "template": m.get("template_name"), "status": m.get("status"),
            "rank": m.get("rank"), "ev": m.get("ev"), "ev_by_scenario": m.get("ev_by_scenario"),
            "cash_at_risk": m.get("car"), "payback_month": m.get("payback_month"), "spread": m.get("spread"),
            "mcda": m.get("mcda"), "mcda_parts": m.get("mcda_parts"), "budget": m.get("budget"),
            "binding_reason": m.get("binding_reason") or "", "why": m.get("why"), "flags": m.get("flags") or [],
            "finding_ids": m.get("finding_ids") or [], "addressed": m.get("addressed") or [],
            "kill_signal_ids": m.get("kill_signals") or [], "p_alive_end": m.get("p_alive_end"),
            "notes": m.get("notes") or [], "units": "USD millions", "numeric_check": numeric_check(m.get("numeric_check"))}


def footnote_cite(n, line):
    """Evidence-shaped citation built from a rendered footnote line when decide.json does not carry the Citation
    ('<title>, <location> -- "<quote>" -- [open](url) · ... · verified: <status>'). Public rule applied."""
    head = line.split(" -- ")[0]
    qm = re.search(r' -- "(.*)" -- ', line + " -- ")
    status = (re.search(r"verified: (\w+)\s*$", line) or [None, None])[1]
    url = (re.search(r"\[open\]\((http[^)]+)\)", line) or [None, None])[1]
    licensed = "[licensed text withheld]" in line
    why = ("Bloomberg/licensed source: quote and links withheld from the public export" if licensed else
           None if status in PAGE_PASS else f"citation status {status or 'missing'} is not public: quote and links withheld")
    title, _, loc = head.partition(", ")
    page = (re.search(r"file page (\d+)", head) or [None, None])[1]
    return {"n": n, "cite_id": None, "doc_title": title, "location": loc, "page": int(page) if page else None,
            "quote": "" if why else (qm.group(1) if qm else ""), "url": None if why else url,
            "deep_link": "" if why else (url or ""), "viewer_link": "", "verification": {"status": status},
            "withheld": bool(why), "withheld_reason": why, "from_footnote": True}


def clean_kill(k):
    """Kill-signal row with its baseline [value, [Citation dict...], text] turned into {value, text, cites}; any
    Citation dict elsewhere in the row (context rows) goes through the public rule too."""
    def fix(o):
        if isinstance(o, dict) and "cite_id" in o and "verification" in o:
            return cell_cite(o, pool={o.get("cite_id"): o})
        if isinstance(o, list):
            return [fix(x) for x in o]
        if isinstance(o, dict):
            return {kk: fix(v) for kk, v in o.items()}
        return o
    k = dict(k)
    b = k.get("baseline")
    if isinstance(b, (list, tuple)) and len(b) >= 2:
        raw_c = b[1] if isinstance(b[1], list) else [b[1]] if isinstance(b[1], dict) else []
        cits = [x for x in raw_c if isinstance(x, dict) and "cite_id" in x]
        pool = {c.get("cite_id"): c for c in cits}
        k["baseline"] = {"value": b[0], "text": b[2] if len(b) > 2 else None,
                         "cites": [cell_cite(c, pool=pool) for c in cits]}
    return {kk: (v if kk == "baseline" else fix(v)) for kk, v in k.items()}


def why_it_works(ticker, d):
    """'Why it will work' table from out/<T>/decide.md: one dict per decider row (plain-language column names) with
    the cited evidence for the data column (decide.md's footnotes matched to decide.json's citations, public rule)."""
    p = OUT / ticker / "decide.md"
    if not p.exists():
        return []
    text = p.read_text(encoding="utf-8")
    rows = md_table(text, "## Why it will work")
    _, notes = split_md(text)
    pool, seen = [], set()

    def collect(o):
        if isinstance(o, dict):
            if o.get("cite_id") and "verification" in o and o["cite_id"] not in seen:
                seen.add(o["cite_id"])
                pool.append(o)
            for v in o.values():
                collect(v)
        elif isinstance(o, list):
            for v in o:
                collect(v)
    collect(d)
    mmap = marker_map(notes, pool)
    byid = {c["cite_id"]: c for c in pool}
    out = []
    for r in rows:
        data = r.get("What our data shows (cited)") or ""
        nums = sorted({int(n) for n in re.findall(r"\[(\d+)\]", data)} |
                      {int(n) for m in re.findall(r"\[derived: ([^\]]+)\]", data) for n in re.findall(r"\d+", m)})
        cites = [cell_cite(byid[mmap[n]], pool=byid) if mmap.get(n) in byid else footnote_cite(n, notes.get(n))
                 for n in nums if notes.get(n) or mmap.get(n) in byid]
        out.append({"decider": r.get("Decider"), "what_the_move_needs": r.get("What the move needs"),
                    "what_our_data_shows": data, "what_only_interviews_can_show": r.get("What only interviews can show"),
                    "cites": cites, "markers_unresolved": [n for n in nums if mmap.get(n) not in byid and not notes.get(n)]})
    return out


def apply_decide(ticker, stance, findings, v1=()):
    d = read_json(OUT / ticker / "decide.json")
    moves_file = ROOT / "docs" / "examples" / f"moves_{ticker}.json"
    rej_md = OUT / ticker / "decide_rejected.md"
    dj = OUT / ticker / "decide.json"
    if rej_md.exists() and (not dj.exists() or rej_md.stat().st_mtime >= dj.stat().st_mtime):
        text = rej_md.read_text(encoding="utf-8").strip()
        stance["decide_rejected"] = {"file": f"out/{ticker}/decide_rejected.md", "text": text}
        stance["note"] += (" The CEO-move valuation was rejected by agent.needle.quant.decide_cli (see "
                           f"out/{ticker}/decide_rejected.md), so the stance stays templated: "
                           + " ".join(l for l in text.splitlines() if l and not l.startswith("#")))
        return stance
    if d and not d.get("chosen") and isinstance(d.get("least_bad_move"), dict):
        d = {**d, "chosen": {**d["least_bad_move"], "status": "least_bad"}, "_least_bad": True}
    if not d or not d.get("chosen"):
        stance["note"] += (f" No CEO-move valuation: no docs/examples/moves_{ticker}.json moves file, so the stance "
                           "stays templated.") if not moves_file.exists() else " decide.json missing; stance stays templated."
        return stance
    ids = {f["id"]: f for f in findings} | {f.get("source_id"): f for f in findings}
    by_text = {(f["signal_kind"], f.get("finding_raw")): f for f in findings}
    for r in v1:  # moves files may name old-engine finding ids; map them by kind + sentence
        hit = by_text.get((r.get("signal_kind"), r.get("finding")))
        if hit and r.get("id") not in ids:
            ids[r["id"]] = hit
    ch, rej = d["chosen"], d.get("rejected") or []
    moves = [ch, *rej]
    total = sum(max(m.get("ev") or 0, 0) for m in moves)
    m_ = lambda x: "n/a" if x is None else f"${x:,.1f}M"
    foot, seen = [], {}
    for m in moves:
        for cl in m.get("claims") or []:
            for c in cl.get("citations") or []:
                if c.get("cite_id") not in seen:
                    seen[c.get("cite_id")] = len(foot) + 1
                    foot.append({"n": len(foot) + 1, "move": m.get("name"), "claim": cl.get("text"),
                                 "citation": cell_cite(c, pool={x.get("cite_id"): x for x in cl.get("citations") or []}),
                                 "numeric_check": numeric_check(cl.get("numeric_check"))})
    stance["template"] = {k: stance.get(k) for k in ("headline", "recommended", "decision_needed", "options", "alternatives", "prove_wrong")}
    stance["headline"] = (f"No candidate clears the hurdle; least-bad option: {ch['name']}." if d.get("_least_bad") else
                          f"{ch['name']}: {ch.get('why') or ''}".strip().rstrip(":"))
    stance["recommended"] = ch["name"]
    budget = (ch.get("budget") or {}).get("total 24-month committed outflow")
    stance["decision_needed"] = (f"No move clears zero expected value ({d.get('selection_rule')}). Least-bad option "
                                 f"'{ch['name']}':" if d.get("_least_bad") else f"Approve '{ch['name']}':") + (f" {m_(budget)} committed over 24 months, cash at risk "
                                 f"{m_(ch.get('car'))} against {m_(d.get('cash_and_equivalents'))} cash and equivalents; "
                                 f"expected value {m_(ch.get('ev'))}, payback month {ch.get('payback_month')}.")
    stance["options"] = [{"name": m["name"], "dollars": round((m.get("ev") or 0) * 1e6, 0),
                          "share": round(max(m.get("ev") or 0, 0) / total, 4) if total else None,
                          "rationale": (f"{m.get('why') or ''} EV {m_(m.get('ev'))} (bear {m_((m.get('ev_by_scenario') or {}).get('bear'))}, "
                                        f"bull {m_((m.get('ev_by_scenario') or {}).get('bull'))}), cash at risk {m_(m.get('car'))}, "
                                        f"payback month {m.get('payback_month')}, scenario spread {m_(m.get('spread'))}, "
                                        f"MCDA {m.get('mcda'):.3f}. Dollars = expected value from agent.needle.quant.decide."
                                        + (f" Not chosen: {m['binding_reason']}." if m.get("binding_reason") else "")).strip(),
                          "status": m.get("status"), "code": m.get("code")} for m in moves]
    items = {it.get("where"): it for it in d.get("numeric_items") or []}
    stance["alternatives"] = [{"name": m["name"], "why_rejected": m.get("binding_reason") or "lower expected value",
                               "why_passed": (items.get(f"passed/{m['name']}") or {}).get("text"),
                               **({"cash_at_risk_note": "cash at risk is zero: no committed outflow is unrecovered in the bear case"}
                                  if m.get("car") == 0 else {}),
                               **{k: m.get(k) for k in FIVE}} for m in rej[:2]]
    ks = [clean_kill(k) for k in d.get("kill_signals") or []]
    stance["kill_signals"] = ks
    pw = [f"{k.get('signal')}: {k.get('threshold')} by month {k.get('check_month')} ({k.get('source')}; {k.get('lag')}); "
          f"action: {k.get('action')}" for k in ks]
    stance["prove_wrong"] = (pw + [x for x in stance["template"]["prove_wrong"] if x not in pw])[:max(3, len(pw))]
    cites = [{"finding_id": ids[i]["id"], "i": 0} for i in ch.get("addressed") or ch.get("finding_ids") or []
             if i in ids and ids[i]["evidence"]]
    stance["decide"] = {"as_of": d.get("as_of"), "cash_and_equivalents": d.get("cash_and_equivalents"),
                        "demo": bool(d.get("demo")), "note": d.get("header_note"),
                        "selection_rule": d.get("selection_rule"),
                        "why_it_works_rows": why_it_works(ticker, d),
                        "cash_at_risk_note": (items.get("car_why") or items.get("budget/car_why") or {}).get("text"),
                        "chosen": None if d.get("_least_bad") else ch.get("name"),
                        "least_bad": d.get("least_bad"), "least_bad_move": ch.get("name") if d.get("_least_bad") else None,
                        "numeric_items": [{**it, "numeric_check": numeric_check(it.get("numeric_check"))}
                                          for it in d.get("numeric_items") or []],
                        "withheld_lines": d.get("withheld_lines") or [],
                        "numeric_check": numeric_check(d.get("numeric_check")),
                        "units": "USD millions", "moves": [_move_row(m) for m in moves],
                        "ranked": d.get("ranked"), "selection_notes": d.get("selection_notes") or [],
                        "footnotes": foot, "finding_cites": cites,
                        "unmapped_finding_ids": [i for i in ch.get("finding_ids") or [] if i not in ids],
                        "source_files": [f"out/{ticker}/decide.json", f"docs/examples/moves_{ticker}.json"]}
    if stance["decide"]["moves"]:
        stance["decide"]["moves"][0]["cash_at_risk_note"] = stance["decide"]["cash_at_risk_note"]
    stance["generated_by"] = "decide_v2"
    if d.get("demo"):
        stance["headline"] = f"[Demo] {stance['headline']}"
    stance["note"] = ("CEO move chosen by agent.needle.quant.decide over the moves in docs/examples/moves_"
                      f"{ticker}.json (team inputs, flagged as assumptions): highest expected value after the cash "
                      "feasibility gate, MCDA only when EV intervals overlap. External benchmark inputs are unverified "
                      "and their quotes are withheld under the public rule. Memo points stay drafted from verified "
                      "findings by rules; a model-written memo requires ANTHROPIC_API_KEY."
                      + (f" DEMO: {d.get('header_note')}" if d.get("demo") else ""))
    return stance


def cites_of(f, n=2):
    return [{"finding_id": f["id"], "i": i} for i in range(min(n, len(f["evidence"])))]


def trace_of(fs):
    seen = []
    for f in fs:
        for e in f["evidence"]:
            lab = e.get("doc_label")
            if lab and lab not in seen:
                seen.append(lab)
    return seen


def slugs_in(f):
    t = f["finding"].lower() + " " + " ".join(e["doc_id"] for e in f["evidence"])
    return {s for s in all_slugs_global() if re.search(rf"\b{re.escape(s)}\b", t)}


_ALL_SLUGS = None


def all_slugs_global():
    global _ALL_SLUGS
    if _ALL_SLUGS is None:
        _ALL_SLUGS = sorted({s for cs in CASE_SETS.values() for p, rv in cs.items() for s in [p, *rv]},
                            key=len, reverse=True)
    return _ALL_SLUGS


# ---------------------------------------------------------------- labels comparison
def _v(x):
    if isinstance(x, str):
        if x in ("None", "nan", ""):
            return None
        if x in ("True", "False"):
            return x == "True"
    return x


def _profile(slug):
    try:
        from agent.needle.detect import labels as L
        return L.profile(slug)
    except Exception:
        return None


def mfp_cell(slug, latest=False):
    """Initial (earliest effective) or latest published IRA MFP per 30 days from the CMS MFP file in the drug pack.
    The file lists one row per NDC per effective year; the value is the median across NDCs for that one date."""
    p = DRUGS / slug / "ira_negotiation.csv"
    if not p.exists():
        return None
    df = pd.read_csv(p, low_memory=False)
    df["_d"] = pd.to_datetime(df["MFP Effective Date"], errors="coerce")
    df["_v"] = pd.to_numeric(df["Single MFP per 30 DES"], errors="coerce")
    df = df.dropna(subset=["_d", "_v"])
    if df.empty:
        return None
    d = df["_d"].max() if latest else df["_d"].min()
    v = float(df.loc[df["_d"] == d, "_v"].median())
    return {"value": round(v, 2), "year": int(d.year), "effective": d.strftime("%Y-%m-%d"),
            "source": f"CMS MFP file, effective {d.strftime('%Y-%m-%d')} (data/corpus/drugs/{slug}/ira_negotiation.csv)"}


def comparison(labels_table, gtn_rows):
    gtn = {r["drug"]: r for r in gtn_rows}
    out = []
    for product, block in (labels_table or {}).get("products", {}).items():
        rivals = block.get("rivals") or []
        slugs = [product, *rivals]
        cells = {r["field"]: r for r in block.get("table", [])}
        prof = {s: _profile(s) for s in slugs}

        def tab(field, slug):
            r = cells.get(field)
            if not r:
                return {"value": None, "source": f"'{field}' not in labels_table.json"}
            if slug == product:
                return {"value": _v(r.get("product")), "source": r.get("source")}
            return {"value": _v((r.get("rivals") or {}).get(slug)), "source": (r.get("rival_sources") or {}).get(slug)}

        def prof_cell(slug, key, sub=None, src_default=None):
            P = prof.get(slug)
            if not P or key not in P:
                return {"value": None, "source": "labels.profile() unavailable"}
            node = P[key]
            val = node.get(sub) if sub else node.get("value")
            return {"value": clean(val), "source": node.get("source") or src_default}

        def generic(slug):
            b, pv = tab("Biosimilars referencing", slug), tab("Paragraph IV filings", slug)
            parts = []
            if b["value"] is not None:
                parts.append(f"{b['value']} biosimilars referencing (Purple Book)")
            if pv["value"] is not None:
                parts.append(f"Paragraph IV: {pv['value']}")
            return {"value": "; ".join(parts) or None, "source": f"{b['source']}; {pv['source']}"}

        def dosing(slug):
            c = prof_cell(slug, "dosing_frequency", "doses_per_year")
            c["text"] = tab("Dosing frequency", slug)["value"]
            return c

        def mfp(slug, latest=False):
            c = mfp_cell(slug, latest)
            if c:
                return c
            if latest:
                return {"value": None, "year": None, "source": f"data/corpus/drugs/{slug}/ira_negotiation.csv not in pack (not selected)"}
            P = prof.get(slug)
            if not P or "ira" not in P:
                g = gtn.get(slug) or {}
                return {"value": g.get("ira_mfp_per_30day"), "source": "verified/pricing/gtn_exposure.csv"}
            return {"value": (P["ira"]["value"] or {}).get("mfp_per_30_days"), "source": P["ira"]["source"]}

        def gtn_call(slug):
            g = gtn.get(slug)
            if not g:
                return {"value": None, "source": "no row in data/moat/verified/pricing/gtn_exposure.csv"}
            return {"value": g.get("exposure_call"), "source": "data/moat/verified/pricing/gtn_exposure.csv",
                    "confidence": g.get("confidence")}

        def ira_status(slug):
            c = tab("IRA negotiation", slug)
            first, last = mfp_cell(slug), mfp_cell(slug, latest=True)
            if not first:
                return c
            df = pd.read_csv(DRUGS / slug / "ira_negotiation.csv", low_memory=False)
            ipay = int(pd.to_numeric(df["IPAY"], errors="coerce").min())
            txt = f"Selected IPAY {ipay}, MFP ${first['value']:,.2f}/30 days"
            if last and last["effective"] != first["effective"]:
                txt += f" ({last['year']}: ${last['value']:,.2f})"
            if txt != c["value"]:
                FIX_COUNT["ira_status"] += 1
            return {"value": txt, "source": first["source"], "ira_status_raw": c["value"], "raw_source": c["source"]}

        fields = [
            ("indications_count", "Approved uses (count)", lambda s: tab("Approved indications (count)", s)),
            ("indications", "Approved uses", lambda s: prof_cell(s, "indications")),
            ("boxed_warning", "Boxed warning", lambda s: tab("Boxed warning", s)),
            ("rems", "REMS", lambda s: tab("REMS", s)),
            ("dosing_frequency_per_year", "Doses per year", dosing),
            ("route", "Route", lambda s: tab("Route", s)),
            ("exclusivity_company_stated", "Exclusivity (company-stated)",
             lambda s: {"value": None, "source": "company-stated LOE store (agent/cache/company_stated_loe.jsonl) "
                                                 "is not in this checkout; not guessed"}),
            ("exclusivity_fda_estimate", "Protection ends (FDA data)", lambda s: tab("Protection ends (latest)", s)),
            ("generic_or_biosimilar_status", "Generic / biosimilar status", generic),
            ("ira_status", "IRA negotiation", ira_status),
            ("mfp_per_30day", "IRA MFP per 30 days ($), initial", mfp),
            ("mfp_latest_per_30day", "IRA MFP per 30 days ($), latest published", lambda s: mfp(s, latest=True)),
            ("partd_spend_latest", "Medicare spend (latest year)", lambda s: tab("Medicare spend (latest year)", s)),
            ("gtn_exposure_call", "Gross-to-net exposure call", gtn_call),
        ]
        rows = [{"field": k, "label": lab, "values": {s: clean(fn(s)) for s in slugs}} for k, lab, fn in fields]
        out.append({"product": product, "rivals": rivals, "rows": rows})
    return out


# ---------------------------------------------------------------- price series
def price_series(slugs):
    gp = csv_rows(MOAT / "tables" / "gtn_proxy.csv")
    pd_rows = [r for r in csv_rows(MOAT / "tables" / "partd_by_year.csv") if r.get("mftr") == "Overall"]
    out = {}
    for s in slugs:
        claims = {}
        for r in pd_rows:
            if r.get("drug") == s and r.get("spend_per_claim") is not None:
                y = re.match(r"\d{4}", str(r["period"]))
                if y:
                    claims[int(y.group(0))] = r["spend_per_claim"]
        rows = []
        for r in gp:
            if r.get("drug") != s or r.get("year") is None:
                continue
            y = int(float(r["year"]))
            rows.append({"year": y, "partd_per_unit": r.get("partd_spend_per_unit"),
                         "nadac_brand": r.get("nadac_brand_mean_per_unit"), "asp": r.get("partb_asp_payment_limit"),
                         "mfp_per_unit": r.get("ira_mfp_per_unit"), "mfp_per_30day": r.get("ira_mfp_per_30day"),
                         "partd_per_claim": claims.get(y), "asp_dosage": r.get("partb_asp_dosage"),
                         "nadac_unit": r.get("nadac_pricing_unit")})
        out[s] = sorted(rows, key=lambda x: x["year"])
    return out


# ---------------------------------------------------------------- stance (templated CEO memo)
def option_of(f):
    topics = set(f["vector"].get("topics") or [])
    for name, kinds, tops in OPTION_RULES:
        if kinds is None or f["signal_kind"] in kinds or (topics & tops and f["detector"] == "drift"):
            return name
    return "Defend"


def _counted(f):
    return bool(f["impact"].get("dollars")) and not f["impact"].get("excluded", f["impact"]["suspect"])


def channel_dollars(fs):
    """Dollars an option protects: v1 sums stated impacts; v2 takes the largest impact per impact channel and sums
    across channels, because findings on one channel (e.g. the 3%-of-revenue anchor) restate the same dollars."""
    by = {}
    for f in fs:
        if _counted(f):
            ch = f["impact"].get("line") if f["impact"].get("d_oi") is not None else f["id"]
            by[ch] = max(by.get(ch, 0), f["impact"]["dollars"], key=abs)
    return list(by.values())


def build_stance(ticker, findings, needle, sealed):
    ver = [f for f in findings if f["verdict"] == "verified"]
    opts = {}
    for name, *_ in OPTION_RULES:
        fs = [f for f in ver if option_of(f) == name]
        dol = channel_dollars(fs)
        opts[name] = {"name": name, "fs": fs, "dollars": round(sum(dol), 0) if dol else None,
                      "score_sum": round(sum(f["score"] or 0 for f in fs), 6)}
    total = sum(o["dollars"] or 0 for o in opts.values())
    ranked = sorted(opts.values(), key=lambda o: (-(o["dollars"] or 0), -o["score_sum"]))
    options = []
    for name in ("Defend", "Attack", "Reprice", "Partner-or-buy"):
        o = opts[name]
        with_d = [f for f in o["fs"] if _counted(f)]
        n_fx = sum(1 for f in o["fs"] if f["impact"].get("currency") not in (None, "USD"))
        n_ph = sum(1 for f in o["fs"] if f["impact"].get("placeholder"))
        sus = [f for f in o["fs"] if f["impact"]["suspect"]]
        if o["dollars"]:
            rule = (("Largest impact per impact channel, summed across channels" if any(f["impact"].get("d_oi") is not None for f in with_d)
                     else "Sum of impact dollars") + f", over the {len(with_d)} verified finding(s) in this bucket that state one: "
                    + "; ".join(f"{f['id']} {money(f['impact']['dollars'])}" for f in with_d[:8])
                    + (f"; and {len(with_d) - 8} more" if len(with_d) > 8 else "")
                    + f". Share = this sum / {money(total)} across all four options.")
        else:
            rule = (f"{len(o['fs'])} verified finding(s) argue for this option but none states a direct dollar path "
                    "that can be summed (proxy, placeholder or unconverted currency), so no dollar figure is shown; "
                    f"ranked by summed materiality score {o['score_sum']}.")
        if n_fx:
            rule += f" {n_fx} finding(s) are in the reporting currency ({o['fs'][0]['impact'].get('currency')}) and are not converted to USD."
        if n_ph:
            rule += f" {n_ph} finding(s) carry only the generic 3%-of-revenue placeholder impact and are not summed."
        if sus:
            rule += (" Left out as suspect (impact above trailing operating income): "
                     + "; ".join(f"{f['id']} {WITHHELD}" for f in sus) + ".")
        options.append({"name": name, "dollars": o["dollars"],
                        "share": round(o["dollars"] / total, 4) if o["dollars"] and total else None,
                        "rationale": f"{OPTION_WHY[name][0].upper()}{OPTION_WHY[name][1:]}. {rule}",
                        "n_findings": len(o["fs"]), "score_sum": o["score_sum"],
                        "finding_ids": [f["id"] for f in o["fs"]][:12]})
    rec = ranked[0]["name"]
    alts = [{"name": o["name"],
             "why_rejected": (f"Protects {money(o['dollars'])} vs {money(ranked[0]['dollars'])} for {rec}"
                              if o["dollars"] and ranked[0]["dollars"] else
                              f"Backed by {len(o['fs'])} verified finding(s) (score {o['score_sum']}) vs "
                              f"{len(ranked[0]['fs'])} (score {ranked[0]['score_sum']}) for {rec}, "
                              "with less stated dollar impact") + f"; the move would {OPTION_WHY[o['name']]}."}
            for o in ranked[1:3]]

    lead = match_rule(needle["signal_kind"], LEADS) or "The sharpest needle"
    obsc = needle["vector"].get("obscurity_note")
    headline = f"{lead}: {needle['finding']}" + (f" ({obsc})." if obsc else "")
    bullets = [{"text": needle["finding"] + (" " + WITHHELD if needle["impact"].get("suspect") else ""),
                "cites": cites_of(needle)}]
    if needle["impact"].get("formula") and not needle["impact"].get("suspect"):
        bullets.append({"text": "Impact: " + needle["impact"]["formula"], "cites": cites_of(needle, 1)})
    if obsc:
        bullets.append({"text": "Why it is not priced in: " + obsc, "cites": cites_of(needle, 1)})
    top3 = ver[:3]
    memo_points = [{"text": f["finding"].rstrip(".") + "." + impact_txt(f),
                    "cites": cites_of(f), "finding_id": f["id"]} for f in top3]

    prove = []
    for f in [needle, *ver]:
        t = match_rule(f["signal_kind"], PROVE_WRONG)
        if t:
            pm = f["peer"].get("peer_median")
            pmtxt = ""
            if pm is not None and any(k in f["signal_kind"] for k in ("dio", "rnd")):
                pmtxt = f" ({pm:.0f} days)" if "dio" in f["signal_kind"] else f" ({pm:.1%})"
            t = t.format(pm=pmtxt)
            if t not in prove:
                prove.append(t)
        if len(prove) == 3:
            break
    for p in sealed:
        if p["ticker"] == ticker and len(prove) < 3:
            iv = next((b for b in p.get("basis", []) if "interval" in b), "")
            prove.append(f"Q3 2026 revenue growth lands outside the sealed forecast ({iv}, sha256-committed).")
    kinds = " ".join(f["signal_kind"] + " " + f["detector"] for f in ver[:15])
    deciders = []
    if re.search(r"ira|spend_per_claim|gtn|pricing", kinds) or rec == "Reprice":
        deciders.append("Payers: CMS (Medicare negotiation) and Part D plan sponsors")
    if re.search(r"labels|dosing|boxed|label_", kinds) or rec == "Attack":
        deciders.append("Prescribers: the specialists choosing between this product and its rivals")
    deciders.append("Investors: analysts and holders who will read the next 10-Q and earnings call")
    if re.search(r"labels|exclusivity|boxed|trial|drift", kinds):
        deciders.append("Regulators: FDA (labels, exclusivity) and SEC (disclosure)")
    return {
        "headline": headline, "confidence": needle["confidence"], "bullets": bullets, "options": options,
        "recommended": rec,
        "decision_needed": (f"Approve '{rec}' as {NAMES.get(ticker, ticker)}'s response to the Sharpest Needle "
                            f"(finding {needle['id']}) before the next quarterly filing."),
        "memo_points": memo_points, "alternatives": alts, "prove_wrong": prove[:3], "deciders": deciders,
        "generated_by": "template",
        "note": ("Drafted from verified findings by deterministic rules (agent/ui_export.py): headline from the "
                 "Sharpest Needle, options from finding kinds, dollars only from impact figures stated in findings. "
                 "A model-written draft requires ANTHROPIC_API_KEY, which was not available for this export."),
        "rules": {"option_buckets": {n: (sorted(k) if k else "all other kinds") for n, k, _ in OPTION_RULES},
                  "recommended": "option with the largest summed impact dollars; ties or no dollars: largest summed score",
                  "suspect": "impact dollars above trailing operating income are flagged and left out of sums"},
    }


# ---------------------------------------------------------------- preset questions
def answer(fs, stance=None, exhibits=None, basis="", formulas=True, data_refs=None, empty=""):
    fs = [f for f in fs if f]
    parts = []
    for f in fs:
        s = f["finding"].rstrip(".") + "."
        if formulas or f["impact"].get("suspect"):
            s += impact_txt(f)
        parts.append(s)
    cites = [c for f in fs for c in cites_of(f, 1)]
    return {"stance": stance, "text": " ".join(parts) if parts else empty, "cites": cites, "trace": trace_of(fs),
            "exhibits": exhibits or [], "basis": basis, "data_refs": data_refs or []}


def build_questions(ticker, findings, needle, stance, rejected, cset, forces_row=None):
    ver = [f for f in findings if f["verdict"] == "verified"]
    name = NAMES.get(ticker, ticker)
    product = next(iter(cset), None)
    rivals = cset.get(product, []) if product else []
    qs = []

    def add(q, a):
        qs.append({"id": f"{ticker}-q{len(qs) + 1}", "q": q, "answer": a})

    peer_ex = [{"kind": "peer", "ref": needle["id"]}] if needle["peer"].get("peer_median") is not None else []
    add("What is the Sharpest Needle and why is it not priced in?",
        answer([needle], stance=option_of(needle), exhibits=peer_ex,
               basis="Highest-scoring finding (out/league.json needle_id); obscurity note from its materiality vector.")
        | {"text": needle["finding"].rstrip(".") + ". "
                   + (impact_txt(needle, proxy=True).strip() + " ")
                   + (needle["vector"].get("obscurity_note") or "").capitalize() + "."})

    if product:
        slugs = {product, *rivals}
        lab = [f for f in findings if f["detector"] == "labels" and product in slugs_in(f)][:4]
        ex = [{"kind": "h2h", "ref": product}, {"kind": "timeline", "ref": product}, {"kind": "price", "ref": product}]
        add(f"Compare {product.title()} with {', '.join(r.title() for r in rivals)} on label, dosing and exclusivity",
            answer(lab, exhibits=ex, basis="Label-detector findings naming the product; full side-by-side in labels.comparison.",
                   data_refs=[f"out/{ticker}/labels_table.json"],
                   empty="No label finding names this product; see the side-by-side table."))

    force = {"ira": [], "mfn": [], "tariff": []}
    for f in ver:
        tops = set(f["vector"].get("topics") or [])
        for k in force:
            if k in tops or k in f["signal_kind"] or f.get("channel") == k:
                force[k].append(f)
    hardest = max(force, key=lambda k: (len(force[k]), sum(f["score"] or 0 for f in force[k])))
    pick = sorted({f["id"]: f for k in force for f in force[k]}.values(), key=lambda f: -(f["score"] or 0))
    pick = sorted(force[hardest], key=lambda f: -(f["score"] or 0))[:2] + [f for f in pick if f not in force[hardest]][:1]
    add(f"Which of the three forces hits {name} hardest?",
        answer(pick, stance="Reprice" if hardest in ("ira", "mfn") else None,
               basis=(f"Verified findings tagged per force: IRA {len(force['ira'])}, MFN {len(force['mfn'])}, "
                      f"tariff {len(force['tariff'])}; the most-tagged force ({hardest.upper()}) leads. "
                      "Exposure figures are in forces (verified/policy/force_summary.csv)"
                      + (f": IRA-selected share of revenue {fr.get('ira_share_of_total_revenue_pct')}%, MFN date "
                         f"{fr.get('mfn_date')}, tariff exempt until {fr.get('tariff_exempt_until')}, "
                         f"{fr.get('pct_mfg_sites_outside_us')}% of manufacturing sites outside the US, US revenue "
                         f"share {fr.get('us_revenue_share_pct')}%." if (fr := forces_row or {}) else ".")),
               data_refs=["data/moat/verified/policy/force_summary.csv", "data/moat/verified/policy/ira_cut_check.csv"],
               empty="No verified finding is tagged with IRA, MFN or tariff; see the forces table."))

    quiet = [f for f in ver if f["detector"] == "calls"][:2] + \
            [f for f in ver if any(x in (f["vector"].get("obscurity_note") or "") for x in ("only in filings", "not asked on calls"))
             and f["detector"] != "calls"][:2]
    add("What did analysts never ask about?",
        answer(quiet, basis="Call-detector findings (deflections, topic surges) plus the top findings whose obscurity "
                            "note says they appear only in filings or data; topic streaks in never_asked.",
               data_refs=["data/moat/verified/market/never_asked.csv", "data/moat/verified/market/priced_in_scorecard.csv"],
               exhibits=[{"kind": "peer", "ref": f["id"]} for f in quiet if f["peer"].get("peer_median") is not None][:1]))

    dec = stance.get("decide")
    byid = {f["id"]: f for f in findings}
    opt = (stance.get("template") or {}).get("recommended") or stance["recommended"]
    rec_fs = ([byid[c["finding_id"]] for c in dec["finding_cites"]] if dec else []) or \
             [f for f in ver if option_of(f) == opt][:3]
    add("What would the CEO do and what would prove it wrong?",
        answer(rec_fs, stance=stance["recommended"],
               exhibits=[{"kind": "peer", "ref": f["id"]} for f in rec_fs if f["peer"].get("peer_median") is not None][:1],
               basis=(f"Chosen move '{stance['recommended']}' from out/{ticker}/decide.json (EV, cash at risk, payback, "
                      "spread, MCDA in stance.decide); text is the findings it addresses, or the findings behind the "
                      f"template option {opt} when none map; kill signals are stance.prove_wrong." if dec else
                      f"Findings behind the recommended option ({stance['recommended']}); the early warning signals are "
                      "stance.prove_wrong."), data_refs=["stance"] + ([f"out/{ticker}/decide.json"] if dec else [])))

    rej_txt = " ".join(f"Rejected: {plain(r['finding']).rstrip('.')}. Reason: {r.get('reason') or 'n/a'}." for r in rejected[:3])
    nh = [f for f in findings if f["verdict"] == "needs_human"]
    add("Where was the AI wrong, and how did we catch it?",
        {"stance": None,
         "text": rej_txt or (f"The page verifier rejected no {ticker} claim in this run; "
                             f"{len(nh)} finding(s) are held for a human (verdict needs_human) instead of being shown as verified."),
         "cites": [], "trace": [], "exhibits": [],
         "basis": "Rejected claims from out/<T>/rejected.jsonl (verbatim with the verifier's reason); the 45-row log of "
                  "data-stream errors is proof.ai_wrong.",
         "data_refs": [f"out/{ticker}/rejected.jsonl", "data/moat/verify/ai_wrong.jsonl"]})

    pr = [f for f in findings if f["signal_kind"] in ("ira_exposed", "spend_per_claim_gap")][:3]
    if product:
        add(f"How exposed is {product.title()} to gross-to-net and Medicare price setting?",
            answer(pr, stance="Reprice" if pr else None, exhibits=[{"kind": "price", "ref": product}],
                   basis="IRA and Part D spend findings; price series from data/moat/tables/gtn_proxy.csv.",
                   data_refs=["data/moat/verified/pricing/gtn_exposure.csv", "data/moat/tables/gtn_proxy.csv"],
                   empty="No IRA or spend-per-claim finding for this product; see the price series."))
    fx = [f for f in ver if f["detector"] == "forensics"][:3]
    add("What do the balance-sheet numbers say against peers?",
        answer(fx, exhibits=[{"kind": "peer", "ref": f["id"]} for f in fx if f["peer"].get("peer_median") is not None][:2],
               basis="Verified forensics findings (inventory, receivables, margin, R&D, tax) ranked by score.",
               empty="No verified forensics finding."))
    return qs


def _uid(findings, sid):
    """Exported id of the finding whose engine id is sid (ids may carry a -dN suffix), else sid."""
    return next((f["id"] for f in findings if (f.get("source_id") or f["id"]) == sid), sid) if sid else None


def mark_no_needle(qs, no_needle):
    if no_needle and qs:
        a = qs[0]["answer"]
        a["text"] = ("No row qualifies as the Sharpest Needle (needle status: none). The top-scored row: " + a["text"])
        a["basis"] = "league needle status none; " + a["basis"]
    return qs


# ---------------------------------------------------------------- company file
def company(ticker, league_row, sealed, side, lg2=None):
    """Company file; prefers v2 engine output (findings_v2.jsonl + league_v2 row), falls back to v1."""
    fpath = first_existing(OUT / ticker / "findings_v3.jsonl", OUT / ticker / "findings_v2.jsonl")
    raw2 = read_jsonl(fpath) if fpath else []
    v1 = read_jsonl(OUT / ticker / "findings.jsonl")
    if raw2:
        findings = build_findings_v2(raw2, side, ticker, lg2, v1)
        needle_id = ((lg2 or {}).get("needle") or {}).get("id")
        rpath = first_existing(OUT / ticker / "rejected_v3.jsonl", OUT / ticker / "rejected_v2.jsonl")
        rej_out = rejected_v2(read_jsonl(rpath) if rpath else [])
        engine = LEAGUE_VERSION.get("v", "v2")
    elif v1:
        findings = build_findings(v1, side, ticker)
        needle_id = (league_row or {}).get("needle_id")
        rej_out = None
        engine = "v1"
    else:
        return None
    byid = {f["id"]: f for f in findings}
    status = ((lg2 or {}).get("needle_status") or "").replace(" ", "_")
    needle = byid.get(needle_id) or findings[0]
    no_needle = engine != "v1" and status == "none"
    rejected = rej_out if rej_out is not None else read_jsonl(OUT / ticker / "rejected.jsonl")
    cset = CASE_SETS.get(ticker, {})
    slugs = list(dict.fromkeys([s for p, rv in cset.items() for s in [p, *rv]]))
    gtn = [r for r in csv_rows(VER / "pricing" / "gtn_exposure.csv") if r.get("drug") in slugs or r.get("company") == ticker]
    labels = read_json(OUT / ticker / "labels_table.json", {}) or {}
    labels = dict(labels)
    labels["comparison"] = comparison(labels, gtn)
    v2p = {}
    for prod in cset:
        b = product_v2(ticker, prod)
        if b:
            v2p[prod] = b
    if v2p:
        labels["v2"] = v2p
        labels["v2_cells_preferred"] = prefer_v2(labels["comparison"], v2p)
    PRODUCT_LOG[ticker] = sorted(v2p)
    stance = apply_decide(ticker, build_stance(ticker, findings, needle, sealed), findings, v1)
    NONE_NOTE = "No row qualifies as the Sharpest Needle (needle status: none); the top-scored row is shown instead."
    if no_needle and stance.get("generated_by") == "template":
        stance["headline"] = f"{NONE_NOTE} {stance['headline']}"
    sig_counts = {p.stem.replace("signals_", ""): sum(1 for x in p.read_text().splitlines() if x.strip())
                  for p in sorted((OUT / ticker).glob("signals_*.jsonl"))}
    forces = for_ticker(VER / "policy" / "force_summary.csv", ticker)
    cvg = for_ticker(VER / "market" / "consensus_vs_guidance.csv", ticker)
    return {
        "ticker": ticker, "name": NAMES.get(ticker, ticker), "needle_id": None if no_needle else needle["id"],
        "engine": engine, "findings_file": str(fpath.relative_to(ROOT)) if raw2 else "out/<T>/findings.jsonl",
        "top_row_id": needle["id"],
        "needle_status": ((lg2 or {}).get("needle_status") or "").replace(" ", "_") or None,
        "league_v2": {k: (lg2 or {}).get(k) for k in ("rank", "L", "top5_sum", "N_eff", "blocks", "largest_share",
                                                      "n_blocks", "comparable", "company_flags", "tariff_exposure",
                                                      "old_score", "old_rank", "constants")} if lg2 else None,
        "case_set": cset, "signals_count": sig_counts,
        "findings": findings,
        "rejected": rej_out if rej_out is not None else [{"finding": plain(r.get("finding")), "finding_raw": r.get("finding"), "reason": r.get("reason"), "verdict": r.get("verdict"),
                      "signal_kind": r.get("signal_kind"), "id": r.get("id"),
                      "evidence": [{k: e.get(k) for k in ("doc_id", "page", "quote", "speaker")} for e in r.get("evidence", [])]}
                     for r in rejected],
        "labels": labels,
        "forces": forces[0] if forces else None,
        "priced_in": for_ticker(VER / "market" / "priced_in_scorecard.csv", ticker),
        "never_asked": for_ticker(VER / "market" / "never_asked.csv", ticker),
        "consensus_vs_guidance": cvg[0] if cvg else None,
        "ira_cut_check": for_ticker(VER / "policy" / "ira_cut_check.csv", ticker),
        "comment_letters": for_ticker(VER / "secx" / "comment_letter_findings.csv", ticker),
        "discontinued_breakouts": for_ticker(VER / "filings" / "discontinued_breakouts.csv", ticker),
        "transcript_grades": for_ticker(VER / "calls" / "transcript_grades.csv", ticker),
        "gtn_exposure": gtn,
        "price_series": price_series(slugs),
        "stance": stance,
        "questions": mark_no_needle(build_questions(ticker, findings, needle, stance, rejected, cset,
                                                    forces[0] if forces else None), no_needle),
        "sealed_forecast": next((p for p in sealed if p["ticker"] == ticker), None),
        "findings_table": (ft := findings_table(ticker, raw2 or v1, side, findings)),
        **({"needle_rule": ft.get("needle_rule"),
            "needle_id_rule": _uid(findings, ft.get("needle_id")),
            "needle_source": {"plain_rule": "rule", "rule": "rule", "red_team": "red_team"}.get(ft.get("needle_source"),
                                                                                              ft.get("needle_source")),
            "needle_reason": ft.get("needle_reason"),
            "plain_rule_needle_id": _uid(findings, ft.get("plain_rule_needle_id")),
            "red_team_needle_id": _uid(findings, ft.get("red_team_needle_id")),
            "red_team_nugget_id": ft.get("red_team_nugget_id")} if ft and ft.get("needle_rule") else
           {"needle_rule": (lg2 or {}).get("needle_rule")} if (lg2 or {}).get("needle_rule") else {}),
    }


# ---------------------------------------------------------------- meta, proof
def tracker_data():
    """progress.json plus the hand-kept STATUS/STAGES/no_source block (latest copy: data/moat/tracker.html)."""
    prog = read_json(MOAT / "progress.json", {}) or {}
    extra = {}
    t = MOAT / "tracker.html"
    if t.exists():
        m = re.search(r"const DATA = (\{.*?\});\s*$", t.read_text(encoding="utf-8"), flags=re.M)
        if m:
            try:
                extra = json.loads(m.group(1))
            except Exception:
                extra = {}
    if not extra:
        try:
            from agent.moat import progress_page as pp
            extra = {"status": pp.STATUS, "stages": pp.STAGES, "part1": pp.PART1, "part2": pp.PART2,
                     "no_source": pp.NO_SOURCE}
        except Exception:
            extra = {}
    return prog, extra


def tables_index():
    out = []
    for p in sorted((MOAT / "tables").glob("*.csv")):
        try:
            df = pd.read_csv(p, low_memory=False)
            rows = len(df)
            src = None
            for col in ("source", "url"):
                if col in df.columns and df[col].notna().any():
                    src = str(df[col].dropna().iloc[0])
                    break
        except Exception:
            rows, src = None, None
        out.append({"name": p.name, "rows": rows, "what": TABLE_WHAT.get(p.name, "Derived table (see its header)."),
                    "list_or_net": LIST_OR_NET.get(p.name), "source": src})
    return out


def limits(no_source):
    text = (ROOT / "docs" / "materiality_spec.md").read_text(encoding="utf-8")
    sec = text.split("## 8.", 1)[1] if "## 8." in text else ""
    out = [l.strip()[2:].strip() for l in sec.splitlines() if l.strip().startswith("- ")]
    out.append("Forensic signals predict margin compression, not hard events (revenue drops or impairments); lift on "
               "hard events is statistically indistinguishable from 1 (out/backtest/hit_rates.json).")
    out.append("Findings marked needs_human passed no automatic check that would let us call them verified; they are "
               "shown, labelled, and never used for stance dollars.")
    out.append("The CEO memo in this export is drafted from verified findings by rules, not written by a model.")
    for miss, who, proxy in no_source:
        out.append(f"No free source for {miss.lower()} (sold by {who}); our proxy: {proxy}.")
    return out


def corpus_stats():
    m = pd.read_csv(ROOT / "data" / "corpus" / "manifest.csv", low_memory=False)
    tr = m[m.doc_type == "transcript"]
    grades = csv_rows(VER / "calls" / "transcript_grades.csv")
    drugs = [p for p in DRUGS.iterdir() if p.is_dir() and not p.name.startswith("_")]
    return {"docs": int(len(m)), "companies": int(m[m.group == "companies"].ticker.nunique()),
            "peers": int(m[m.group == "peers"].ticker.nunique()), "drugs": len(drugs),
            "drugs_with_label": sum(1 for p in drugs if (p / "label_sections.md").exists()),
            "transcripts": int(len(tr)), "transcripts_official": int((tr.source_quality == "official").sum()),
            "transcripts_graded": len(grades),
            "transcript_grades": {g: sum(1 for r in grades if r.get("grade") == g) for g in ("A", "B", "C")},
            "pages": int(m.pages.fillna(0).sum()),
            "source_quality": {k: int(v) for k, v in m.source_quality.value_counts().items()},
            "doc_types": {k: int(v) for k, v in m.doc_type.value_counts().items()}}


def md_table(text, after=None):
    """Rows of the first markdown table in text (after the heading `after`, if given) as dicts keyed by header."""
    if after and after in text:
        text = text.split(after, 1)[1]
    lines = [l for l in text.splitlines()]
    i = next((k for k, l in enumerate(lines) if l.strip().startswith("|")), None)
    if i is None:
        return []
    head = [h.strip() for h in lines[i].strip().strip("|").split("|")]
    rows = []
    for l in lines[i + 2:]:
        if not l.strip().startswith("|"):
            break
        cells = [c.strip() for c in l.strip().strip("|").split("|")]
        rows.append(dict(zip(head, cells)))
    return rows


def _md_plain(t):
    return re.sub(r"\*\*(.+?)\*\*", r"\1", t or "").strip()


def ai_wrong_cases():
    """docs/ai_in_the_build.md 'When the AI was wrong' table -> rows with their file/commit citations."""
    p = ROOT / "docs" / "ai_in_the_build.md"
    if not p.exists():
        return []
    out = []
    for r in md_table(p.read_text(encoding="utf-8"), "## When the AI was wrong"):
        ref = r.get("File or commit", "")
        out.append({"n": int(r["#"]) if r.get("#", "").isdigit() else r.get("#"), "date": r.get("Date"),
                    "ai_claimed": r.get("What the AI claimed"), "caught_by": r.get("Caught by"), "fix": r.get("Fix"),
                    "evidence": ref, "evidence_refs": re.findall(r"`([^`]+)`", ref) +
                    re.findall(r"\b[0-9a-f]{7}\b", re.sub(r"`[^`]+`", "", ref)),
                    "source": "docs/ai_in_the_build.md"})
    return out


def honest_limits():
    """docs/honest_limits.md: the limits table plus the 'Further limits' bullets."""
    p = ROOT / "docs" / "honest_limits.md"
    if not p.exists():
        return []
    text = p.read_text(encoding="utf-8")
    out = [{"limit": r.get("Limit"), "sentence": (r.get("Sentence for the pitch") or "").strip('"'),
            "proxy": r.get("Proxy we use"), "source": "docs/honest_limits.md"} for r in md_table(text)]
    for l in text.split("Further limits", 1)[-1].splitlines() if "Further limits" in text else []:
        m = re.match(r"^- \*\*(.+?)\*\*\s*(.*)$", l.strip())
        if m:
            out.append({"limit": m.group(1).rstrip("."), "sentence": _md_plain(m.group(2)).strip('"'),
                        "proxy": None, "source": "docs/honest_limits.md"})
    return out


def proof(rules, lims):
    sealed = read_json(OUT / "predictions" / "sealed_2026Q3.json", {}) or {}
    body = {k: v for k, v in sealed.items() if k != "sha256"}
    canonical = audit.canonical(body)
    doc = (ROOT / "docs" / "needle_sealed.md").read_text(encoding="utf-8") if (ROOT / "docs" / "needle_sealed.md").exists() else ""
    m = re.search(r"sha256=([0-9a-f]{64})", doc)
    return {
        "backtest": {"hit_rates": read_json(OUT / "backtest" / "hit_rates.json"),
                     "gate2_md": (ROOT / "docs" / "needle_gate2.md").read_text(encoding="utf-8"),
                     "examples": read_json(OUT / "backtest" / "examples.json", [])},
        "calibration": read_json(OUT / "predictions" / "calibration.json"),
        "blind": read_json(OUT / "predictions" / "blind_JNJ_2026Q3.json"),
        "sealed": {"file": sealed, "canonical": canonical, "doc_hash": m.group(1) if m else None,
                   "file_hash": sealed.get("sha256"),
                   "recomputed": hashlib.sha256(canonical.encode("utf-8")).hexdigest(),
                   "how": "sha256 over the UTF-8 bytes of `canonical` = json.dumps(file minus sha256, sort_keys=True, "
                          "ensure_ascii=False, separators=(',', ':')) as in agent.needle.audit.seal()"},
        "ai_wrong": read_jsonl(MOAT / "verify" / "ai_wrong.jsonl"),
        "ai_wrong_cases": ai_wrong_cases(),
        "how_we_did_it_md": (ROOT / "docs" / "how_we_did_it_quant.md").read_text(encoding="utf-8")
        if (ROOT / "docs" / "how_we_did_it_quant.md").exists() else None,
        "ai_in_the_build_md": (ROOT / "docs" / "ai_in_the_build.md").read_text(encoding="utf-8")
        if (ROOT / "docs" / "ai_in_the_build.md").exists() else None,
        "verifier_rules": rules, "limits": lims,
    }


# ---------------------------------------------------------------- main
def main():
    DEST.mkdir(parents=True, exist_ok=True)
    league = read_json(OUT / "league.json", []) or []
    lrow = {r["ticker"]: r for r in league}
    lpath = first_existing(OUT / "league_v3.json", OUT / "league_v2.json")
    league2 = read_json(lpath, []) if lpath else []
    LEAGUE_VERSION["v"] = "v3" if lpath and lpath.name == "league_v3.json" else "v2"
    LEAGUE_VERSION["file"] = str(lpath.relative_to(ROOT)) if lpath else None
    l2 = {r["ticker"]: r for r in league2}
    sealed = (read_json(OUT / "predictions" / "sealed_2026Q3.json", {}) or {}).get("predictions", [])
    tickers = list(SHORTLIST) + [t for t in CASE_SETS if t not in SHORTLIST]
    sizes, stats, written = {}, {}, []
    for t in tickers:
        data = company(t, lrow.get(t), sealed, SIDE, l2.get(t))
        if data is None:
            print(f"{t}: no out/{t}/findings.jsonl, no company file")
            continue
        assert_numeric_checks(data)
        assert_no_repr(data)
        path = DEST / "companies" / f"{t}.json"
        n = write(path, data)
        if n > MAX_COMPANY_BYTES:
            data = company(t, lrow.get(t), sealed, SIDE_SMALL, l2.get(t))
            n = write(path, data)
        sizes[f"companies/{t}.json"] = n
        written.append(t)
        evs = [e for f in data["findings"] for e in f["evidence"]]
        stats[t] = {"engine": data["engine"], "findings": len(data["findings"]),
                    "high_confidence": sum(f["confidence"] == "high" for f in data["findings"]),
                    "evidence_withheld": sum(bool(e.get("withheld")) for e in evs),
                    "verified": sum(f["verdict"] == "verified" for f in data["findings"]),
                    "rejected": len(data["rejected"]), "evidence": len(evs),
                    "located": sum(e["excerpt"]["located"] for e in evs)}
        COMPANY_CACHE[t] = data
        print(f"{t}: {stats[t]} {n / 1e6:.2f} MB")

    prog, extra = tracker_data()
    no_source = extra.get("no_source") or []
    lims = limits(no_source)
    ok, n, bad = audit.verify_chain()
    onboarded = [t for t in written if t not in SHORTLIST]
    league_t = (sorted(league2, key=lambda r: r.get("rank") or 99)[0]["ticker"] if league2 else
                league[0]["ticker"] if league else SHORTLIST[0])
    pick, default_warn = picked_ticker(), None
    # no league fallback: without a valid pick the cockpit routes to the first shortlist ticker alphabetically
    # and the chat treats default_ticker_source "unpicked" as no company selected
    if pick and pick in written and pick in SHORTLIST:
        default_t, default_src = pick, "pick"
    else:
        default_t, default_src = sorted(t for t in written if t in SHORTLIST)[0], "unpicked"
        if pick:
            default_warn = f"NEEDLE_TICKER={pick} is not one of the ten shortlist companies; treated as unpicked"
    LEAGUE_VERSION["leader"] = league_t
    pending = []
    for t in CASE_SETS:
        if t not in SHORTLIST and t not in written:
            cs = read_json(OUT / t / "case_set.json", {}) or {}
            pending.append({"ticker": t, "name": NAMES.get(t, cs.get("registrant", t)), "case_set": cs.get("case_set"),
                            "packs": cs.get("packs"), "has_findings": False,
                            "note": f"onboarded (out/{t}/case_set.json) but no out/{t}/findings.jsonl yet; no company file"})
    allf = [f for t in written for f in COMPANY_CACHE[t]["findings"]]
    meta = {
        "as_of": prog.get("as_of"), "built_at": pd.Timestamp.now(tz="UTC").isoformat(),
        "default_ticker": default_t, "default_ticker_source": default_src,
        **({"default_ticker_warning": default_warn} if default_warn else {}),
        "honest_limits": honest_limits(),
        "league_internal": True, "league_leader": LEAGUE_VERSION.get("leader"),
        "league_note": ("league.json, league_robustness and the S equation are internal triage only; the pitch-facing "
                        "outputs are pitch_outputs (findings table ranked by dollar impact, Sharpest Needle, product "
                        "fine print, CEO move)."),
        "pitch_outputs": ["findings_table", "needle", "product", "decide"],
        "findings_table_available": [t for t in written if COMPANY_CACHE[t].get("findings_table")],
        "engine": LEAGUE_VERSION["v"] if league2 else "v1", "league_file": LEAGUE_VERSION.get("file"),
        "league_robustness": read_json(OUT / "league_v3_robustness.json"),
        "companies": [{"ticker": t, "name": NAMES.get(t, t)} for t in written if t in SHORTLIST],
        "onboarded": onboarded, "onboarding_pending": pending,
        "totals": {"verified": sum(f["verdict"] == "verified" for f in allf),
                   "rejected": sum(stats[t]["rejected"] for t in written),
                   "findings": len(allf), "high_confidence": sum(f.get("confidence") == "high" for f in allf),
                   "needs_human": sum(f["verdict"] == "needs_human" for f in allf)},
        "ledger": {"ok": bool(ok), "n": n, "bad": bad},
        "corpus": corpus_stats(),
        "moat": {"as_of": prog.get("as_of"), "coverage": prog.get("companies", {}), "buckets": prog.get("buckets", []),
                 "status": extra.get("status", {}), "tables": tables_index(), "no_source": no_source,
                 "stages": extra.get("stages", []), "part1": extra.get("part1", []), "part2": extra.get("part2", []),
                 "ai_wrong_count": len(read_jsonl(MOAT / "verify" / "ai_wrong.jsonl"))},
        "case_sets": CASE_SETS, "verifier_rules": VERIFIER_RULES, "limits": lims,
        "evidence_located": stats, "regenerate": REGEN,
        "v2_status": {"decide_v2": [t for t in written if COMPANY_CACHE[t]["stance"].get("generated_by") == "decide_v2"],
                      "products_v2": PRODUCT_LOG,
                      "products_missing": {t: sorted(set(CASE_SETS.get(t, {})) - set(PRODUCT_LOG.get(t, [])))
                                           for t in CASE_SETS if set(CASE_SETS.get(t, {})) - set(PRODUCT_LOG.get(t, []))}},
    }
    sizes["meta.json"] = write(DEST / "meta.json", meta)
    sizes["league.json"] = write(DEST / "league.json", league_v2_rows(league2) if league2 else
                                 [r | {"name": NAMES.get(r["ticker"], r["ticker"]),
                                       "sharpest_needle": plain(r.get("sharpest_needle")),
                                       "sharpest_needle_raw": r.get("sharpest_needle")} for r in
                                  sorted(league, key=lambda r: -(r.get("score") or 0))])
    sizes["proof.json"] = write(DEST / "proof.json", proof(VERIFIER_RULES, lims))
    write_readme(sizes, stats, meta)
    print(f"total {sum(sizes.values()) / 1e6:.2f} MB -> {DEST}")


COMPANY_CACHE = {}


def picked_ticker():
    """NEEDLE_TICKER from the environment, else from the repo .env (only that key is read); None when unset."""
    v = os.environ.get("NEEDLE_TICKER")
    if not v and (ROOT / ".env").exists():
        for line in (ROOT / ".env").read_text(encoding="utf-8", errors="ignore").splitlines():
            if line.strip().startswith("NEEDLE_TICKER="):
                v = line.split("=", 1)[1].strip().strip("'\"")
    return (v or "").strip().upper() or None


def findings_table(ticker, raw_findings, side, exported=()):
    """out/<T>/findings_table.json (cited findings ranked by dollar impact; one shared footnote list in the .md)
    -> company findings_table. Markers map to cite_ids through the shared footnotes, matched against every
    citation of the ticker's findings. dEPS, dOI and the analyst share are model outputs labelled [assumption]."""
    d = read_json(OUT / ticker / "findings_table.json")
    if d is None:
        return None
    rows = d.get("rows") if isinstance(d, dict) else d
    md = OUT / ticker / "findings_table.md"
    _, notes = split_md(md.read_text(encoding="utf-8")) if md.exists() else (None, {})
    pool, seen = [], set()
    for f in raw_findings:
        for c in f.get("citations") or []:
            if c.get("cite_id") not in seen:
                seen.add(c.get("cite_id"))
                pool.append(c)
    mmap = marker_map(notes, pool)
    lic = {c.get("cite_id") for c in pool if c.get("license")}
    uid = {}
    for f in exported:
        uid.setdefault(f.get("source_id") or f["id"], f["id"])
    by_id = {f.get("id"): f for f in raw_findings}
    out = []
    for i, r in enumerate(rows or []):
        fid = r.get("finding_id") or r.get("id")
        src = by_id.get(fid) or {}
        st = r.get("sentence_marked") or split_md(src.get("sentence_md"))[0]
        fo = r.get("formula_marked") or split_md(src.get("formula_md"))[0]
        nums = sorted({int(n) for t in (st or "", fo or "") for n in re.findall(r"\[(\d+)\]", t)} |
                      {int(n) for t in (st or "", fo or "") for m in re.findall(r"\[derived: ([^\]]+)\]", t)
                       for n in re.findall(r"\d+", m)})
        k1, u1 = marker_kinds(st)
        k2, u2 = marker_kinds(fo)
        MARKER_UNKNOWN.extend(u1 + u2)
        out.append({"rank": r.get("rank", i + 1), "rank_basis": r.get("rank_basis") or d.get("rank_basis"),
                    "finding_id": uid.get(fid, fid), "source_id": fid, "signal_kind": r.get("signal_kind"),
                    "direction": r.get("direction"), "channel": r.get("channel"),
                    "sentence": plain(r.get("sentence")), "sentence_marked": plain(st) if st else None,
                    "impact_marked": fo or None,
                    "d_eps_base_abs": r.get("d_eps_base_abs"), "d_oi_base_abs": r.get("d_oi_base_abs"),
                    "analyst_share_asked": r.get("analyst_share_asked"),
                    "analyst_share_source": r.get("analyst_share_source"),
                    "assumption_fields": ["d_eps_base_abs", "d_oi_base_abs", "analyst_share_asked"],
                    "confidence": (r.get("confidence") or "").lower(), "not_quantified": r.get("not_quantified"),
                    "needle": r.get("needle"), "needle_blocked": r.get("needle_blocked"),
                    "peer_text": r.get("peer_comparison_marked") or r.get("peer_comparison"),
                    "peer_comparison": r.get("peer_comparison"),
                    "nugget": r.get("nugget"), "corroborated_by": r.get("corroborated_by"), "merged": r.get("merged"),
                    **{k: v for k, v in (lambda f: {"explained_by_footnote": f["explained_by_footnote"],
                                                     "explained_by_footnote_note": f["explained_by_footnote_note"],
                                                     "footnote_read": f["footnote_read"]})(
                        next((x for x in exported if (x.get("source_id") or x["id"]) == fid),
                             {"explained_by_footnote": False, "explained_by_footnote_note": None,
                              "footnote_read": None})).items()},
                    "marker_map": {n: mmap.get(n) for n in nums},
                    "marker_licensed": [n for n in nums if mmap.get(n) in lic],
                    "marker_kinds": {"sentence": k1, "formula": k2},
                    "numeric_check": numeric_check(r.get("numeric_check") or src.get("numeric_check"))})
    return {"rank_basis": d.get("rank_basis"), "needle_rule": d.get("needle_rule"), "needle_id": d.get("needle_id"),
            **{k: d.get(k) for k in ("needle_source", "plain_rule_needle_id", "red_team_needle_id",
                                     "red_team_nugget_id", "needle_reason", "merged_rows")},
            "note": d.get("note"), "numeric_check": numeric_check(d.get("numeric_check")),
            "failed": d.get("failed") or [], "rows": out, "footnotes_n": len(notes),
            "marker_unresolved": sorted(n for n, c in mmap.items() if not c),
            "source_file": f"out/{ticker}/findings_table.json"}
MARKER_UNKNOWN = []
LEAGUE_VERSION = {}
PRODUCT_LOG = {}


def league_v2_rows(league2):
    """league_v2.json -> the league.json contract (score = L), plus v2 keys and needle_status."""
    out = []
    for r in sorted(league2, key=lambda r: r.get("rank") or 99):
        t = r["ticker"]
        fs = (COMPANY_CACHE.get(t) or {}).get("findings", [])
        nd = r.get("needle") or {}
        out.append({"ticker": t, "name": NAMES.get(t, t), "score": r.get("L"), "n_findings": r.get("n_findings"),
                    "n_verified": sum(f["verdict"] == "verified" for f in fs), "n_rejected": r.get("n_withheld"),
                    "high_confidence": sum(f["confidence"] == "high" for f in fs),
                    "sharpest_needle": plain(nd.get("sentence")), "sharpest_needle_raw": nd.get("sentence"),
                    **({"needle_rule": r["needle_rule"]} if r.get("needle_rule") else {}),
                    "needle_id": nd.get("id") or None, "needle_status": (r.get("needle_status") or "").replace(" ", "_"),
                    "needle_confidence": (nd.get("confidence") or "").lower(), "needle_S": nd.get("S"),
                    "rank": r.get("rank"), "top5_sum": r.get("top5_sum"), "N_eff": r.get("N_eff"),
                    "blocks": r.get("blocks"), "comparable": r.get("comparable"),
                    "company_flags": r.get("company_flags"), "old_score": r.get("old_score"),
                    "old_rank": r.get("old_rank"), "n_withheld": r.get("n_withheld"),
                    "tariff_exposure": r.get("tariff_exposure"),
                    **{k: r.get(k) for k in ("n_scored", "n_not_quantified", "n_guarded", "v2_L", "v2_rank") if k in r}})
    return out


def write_readme(sizes, stats, meta):
    lines = ["# ui/public/data", "",
             "Precomputed JSON for the NEEDLE cockpit (contract: docs/ui_spec.md). Generated by `agent/ui_export.py`; "
             "do not edit by hand.", "", "Regenerate from the repo root:", "", "```", REGEN, "```", "",
             "| File | Size | Contents |", "|---|---|---|",
             f"| meta.json | {sizes['meta.json'] / 1e3:,.0f} KB | totals ({meta['totals']['findings']} findings, "
             f"{meta['totals']['verified']} verified, {meta['totals']['rejected']} rejected), ledger "
             f"({meta['ledger']['n']} records, ok={meta['ledger']['ok']}), corpus ({meta['corpus']['docs']} docs), moat "
             f"coverage + {len(meta['moat']['tables'])} tables, case sets, verifier rules, {len(meta['limits'])} limits |",
             f"| league.json | {sizes['league.json'] / 1e3:,.0f} KB | {len(stats)} companies ranked by score |",
             f"| proof.json | {sizes['proof.json'] / 1e3:,.0f} KB | backtest (hit rates, gate-2 text, examples), "
             "calibration, J&J blind test, sealed forecasts with the canonical string and hashes, "
             f"{meta['moat']['ai_wrong_count']} ai_wrong rows |"]
    for t, s in stats.items():
        lines.append(f"| companies/{t}.json | {sizes[f'companies/{t}.json'] / 1e6:.2f} MB | {s['findings']} findings "
                     f"({s['verified']} verified), {s['rejected']} rejected, {s['evidence']} evidence items "
                     f"({s['located']} quotes located on the page), stance, questions, labels, price series |")
    lines += ["", f"Total: {sum(sizes.values()) / 1e6:.2f} MB.", "",
              "Notes: `stance.generated_by` is `template` (no ANTHROPIC_API_KEY at export). Excerpts are about "
              f"{SIDE} characters either side of the quote ({SIDE_SMALL} if a company file would exceed 4 MB). "
              "Onboarded tickers without findings are listed in meta.onboarding_pending and get no company file.", "",
              "Engine: v2 (out/<T>/findings_v2.jsonl, rejected_v2.jsonl, out/league_v2.json) when present, else v1. "
              "Public rule: a citation that is unverified or Bloomberg-licensed exports no quote, excerpt, deep link or "
              "viewer link (`withheld: true` + reason); WRDS-licensed data rows are summarised in `licensed_inputs` "
              "(count and table names only)."]
    (DEST / "README.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
