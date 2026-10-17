"""FIND: S_f = M_f . O_f . E_f . pi_k(f)   (docs/quant_model.md section 4).

M_f = |dEPS_f| . (1 + r)^(-t_f) / sigma_EPS                  section 4.2
O_f = (1 - z)(1 - h)(1 - a)(1 - c)(1 - s) . 2^(-age / H)      section 4.4   (obscurity.py)
E_f = min_j [ 1 - prod_i (1 - g_i) ]                          section 4.5   (evidence.py)
pi_k  excess probability of the family's adverse outcome       section 4.6   (FAMILIES below)

Candidates come from the existing detectors (out/<T>/signals_*.jsonl) plus the IRA channel generator (CMS selected
drugs, section 4.3 b), which the engine does not produce. Every constant is imported from weights.py.
"""

import hashlib
import re
from dataclasses import dataclass, field
from datetime import date

from agent.needle.cite.locator import Claim, Citation
from agent.needle.cite.render import render_markdown
from agent.needle.cite.index import load_index
from agent.needle.cite.verify import verify as cite_verify

from . import data, evidence as EV, impact as IM, obscurity as OB
from . import weights as W


# ------------------------------------------------------------------ pure equations
def materiality(d_eps, t_years, sigma, r=W.R):
    """M_f = |dEPS_f| . (1 + r)^(-t_f) / sigma_EPS (section 4.2). r = 7.85% Damodaran Jan 2026."""
    if not sigma:
        return 0.0
    return abs(d_eps) * (1 + r) ** (-t_years) / sigma


def score(M, O, E, pi, alpha=W.ALPHA, beta=W.BETA, gamma=W.GAMMA):
    """S_f = M^alpha . O^beta . E^gamma . pi (section 4.1; exponents 1 by design, D3)."""
    if min(M, O, E, pi) <= 0:
        return 0.0
    return (M ** alpha) * (O ** beta) * (E ** gamma) * pi


# ------------------------------------------------------------------ signal families (section 4.6 table)
@dataclass(frozen=True)
class Family:
    name: str
    block: str           # A T C G P L X F
    pi: float
    route: str           # backtest | anchor | directional | none | type_c | half | favorable
    diagnostic: bool
    topics: tuple = ()
    has_detector: bool = True


FAM = {
    "inventory": Family("inventory outpaces revenue", "A", W.PI_INVENTORY, "backtest", True, ("inventory",)),
    "dio": Family("days inventory", "A", W.PI_DIO, "backtest", False, ("inventory",)),
    "receivables": Family("receivables outpace revenue", "A", W.PI_RECEIVABLES, "backtest", False, ("receivables",)),
    "dso": Family("days sales outstanding", "A", W.PI_DSO, "backtest", True, ("receivables",)),
    "gm_drop": Family("gross margin drop", "A", W.PI_GROSS_MARGIN_DROP, "backtest", False, ("gross_margin",)),
    "risk": Family("risk-factor change", "T", W.PI_RISK_FACTOR, "anchor", True),
    "litigation": Family("litigation-language change", "T", W.PI_LITIGATION_TEXT, "anchor", True),
    "mdna": Family("MD&A change", "T", W.PI_MDNA, "anchor", False),
    "directional": Family("non-answer / deflection", "C", W.PI_MIN, "directional", False),
    "none_C": Family("repeated deflection / topic surge (no evidence)", "C", W.PI_NONE, "none", False),
    "none_A": Family("ETR / R&D shift or level outlier (no evidence)", "A", W.PI_NONE, "none", False),
    "none_X": Family("outside data: FAERS, demand divergence, distributor (no evidence)", "X", W.PI_NONE, "none", False),
    "ira": Family("contractual: IRA negotiation", "P", W.PI_CONTRACTUAL, "type_c", True, ("ira",)),
    "loe": Family("contractual: loss of exclusivity", "P", W.PI_CONTRACTUAL, "type_c", True, ("generic", "loe")),
    "label": Family("contractual: label fact", "L", W.PI_CONTRACTUAL, "type_c", True),
    "footnote": Family("contractual: booked footnote item", "F", W.PI_CONTRACTUAL, "type_c", True, ("impairment",)),
    "trial": Family("contractual: business-reason trial stop", "F", W.PI_CONTRACTUAL, "type_c", True),
    "favorable": Family("favorable level outlier with no scenario", "A", W.PI_FAVORABLE_LEVEL, "favorable", False),
}
KIND = {
    "inventory_outpaces_revenue": "inventory", "inv_gap_peer_outlier": "inventory",
    "dio_rising": "dio", "dio_peer_outlier": "dio",
    "receivables_outpace_revenue": "receivables", "rec_gap_peer_outlier": "receivables",
    "dso_rising": "dso", "dso_peer_outlier": "dso", "gross_margin_drop": "gm_drop",
    "risk_added": "risk", "risk_intensified": "risk", "risk_removed": "risk", "risk_modified": "risk",
    "mdna_added": "mdna", "mdna_intensified": "mdna", "mdna_modified": "mdna", "mdna_removed": "mdna",
    "qa_deflection": "directional", "qa_repeated_deflection": "none_C", "call_topic_surge": "none_C",
    "tax_rate_shift": "none_A", "etr_peer_outlier": "none_A", "rnd_shift": "none_A", "rnd_pct_peer_outlier": "none_A",
    "faers_serious_rising": "none_X", "demand_divergence": "none_X", "distributor_commentary": "none_X",
    "ira_exposed": "ira", "exclusivity_earlier": "loe", "impairment": "footnote", "trial_terminated": "trial",
    "label_broader": "label", "label_narrower": "label", "boxed_warning_advantage": "label",
    "boxed_warning_disadvantage": "label", "dosing_advantage": "label", "dosing_burden": "label",
    "spend_per_claim_gap": "label",
}
# Families in section 4.6 with no engine detector yet (made visible in findings_v2 via has_detector).
MISSING_DETECTORS = ["misstatement score (Beneish/Dechow)", "opportunistic insider sales", "negative 8-K items",
                     "zero-question calls", "MFN channel candidates", "GTN widening", "footnote extractor"]

TOPIC_KEYS = list(OB.TOPIC_WORDS)


def family_of(sig, topics):
    """Section 4.6 family for a detector Signal."""
    k = KIND.get(sig.kind)
    if sig.kind == "gross_margin_peer_outlier":
        favorable = sig.value is not None and sig.peer_median is not None and sig.value >= sig.peer_median
        return FAM["favorable"] if favorable else FAM["none_A"]
    if favorable_statistical(sig):
        return FAM["favorable"]
    if sig.detector == "drift" and "litigation" in topics:
        return FAM["litigation"]
    return FAM.get(k, FAM["none_X"])


GROWTH_KINDS = {"inventory_outpaces_revenue", "receivables_outpace_revenue", "inv_gap_peer_outlier",
                "rec_gap_peer_outlier", "dio_rising", "dso_rising", "tax_rate_shift"}
LEVEL_KINDS = {"dio_peer_outlier", "dso_peer_outlier", "etr_peer_outlier"}


def favorable_statistical(sig):
    """A statistical row whose sign is good for EPS (receivables growing slower than revenue, ETR falling, margin
    rising) has no adverse scenario: family "favorable level outlier", pi = 0 (section 4.1: only adverse findings
    and quantified favorable ones get M > 0)."""
    if sig.kind in GROWTH_KINDS and sig.value is not None and sig.value < 0:
        return True
    if sig.kind in LEVEL_KINDS and sig.peer_z is not None and sig.peer_z < 0:
        return True
    if sig.kind == "gross_margin_drop" and sig.value is not None and sig.value > 0:
        return True
    return False


def topics_of(sig, fam):
    t = set(sig.meta.get("topics") or [])
    if sig.meta.get("topic") and sig.meta["topic"] != "other":
        t.add(sig.meta["topic"])
    t |= set(fam.topics)
    for key in TOPIC_KEYS:
        if key in sig.kind:
            t.add(key)
    return sorted(t) or ["other"]


# ------------------------------------------------------------------ helpers
def finding_id(ticker, kind, first_cite):
    """sha256(ticker|kind|first citation_id)[:12] (section 4.10)."""
    return hashlib.sha256(f"{ticker}|{kind}|{first_cite}".encode()).hexdigest()[:12]


def _filed(doc_id):
    r = data.doc_row(doc_id) if doc_id else None
    if r is None:
        idx = load_index()
        rec = idx.resolve(doc_id) if doc_id else None
        r = rec.row if rec else None
    if r is None:
        return None
    f = OB.to_date(r["filed"]) if r["filed"] else None
    if f:
        return f
    per = str(r["period"] or "")
    m = re.match(r"(\d{4})Q([1-4])", per)
    if m:  # transcript with no date: call about 30 days after quarter end (flagged by caller)
        y, q = int(m.group(1)), int(m.group(2))
        return date(y + (q == 4), (q * 3) % 12 + 1, 30 if (q * 3) % 12 + 1 != 2 else 28)
    return None


def stage_split(cites):
    """Inventory stage split (section 4.3 g i): finished-goods share from the inventory note of the cited filing.
    Returns (fg_share or None, detail, citation or None)."""
    idx = load_index()
    for c in cites:
        if not c.canonical_id or c.canonical_id.startswith(("xbrl:", "tables/", "derived")):
            continue
        for n, (_, text) in idx.pages(c.canonical_id).items():
            fg = re.search(r"Finished (?:products|goods)\s*\$?\s*([\d,]+(?:\.\d+)?)", text)
            wip = re.search(r"Work[- ]in[- ]process\s*\$?\s*([\d,]+(?:\.\d+)?)", text, re.I)
            rm = re.search(r"Raw materials(?: and supplies)?\s*\$?\s*([\d,]+(?:\.\d+)?)", text, re.I)
            if fg and wip and rm:
                v = [float(x.group(1).replace(",", "")) for x in (fg, wip, rm)]
                share = v[0] / sum(v)
                quote = text[fg.start():rm.end()]
                cit = cite_verify(Citation(canonical_id=c.canonical_id, page=n, quote=quote, claim_type="quote"), idx)
                return share, (f"finished {v[0]:,.0f}, WIP {v[1]:,.0f}, raw {v[2]:,.0f}: finished share "
                               f"{share:.1%}"), cit
    return None, "inventory note with a stage split not found", None


# ------------------------------------------------------------------ IRA candidates (section 4.3 b)
ONC = (W.ONC_D_BULL, W.ONC_D_BASE, W.ONC_D_BEAR)
CMS27 = "policy_gov:policy_gov/cms/cms_fact_sheet_selected_list_ipay2027.md"
CMS28 = "policy_gov:policy_gov/cms/cms_fact_sheet_selected_list_ipay2028.md"
NEG26 = "policy_gov:policy_gov/cms/cms_fact_sheet_negotiated_prices_ipay2026.md"
NEG27 = "policy_gov:policy_gov/cms/cms_fact_sheet_negotiated_prices_ipay2027.md"
ONC_ANALOG_QUOTES = [(NEG26, 2, "Imbruvica Pharmacyclics LLC Blood cancers $9,319.00 $14,934.00 38%"),
                     (NEG27, 2, "Ibrance Pfizer Inc. Breast cancer $7,871 $15,741 50%"),
                     (NEG27, 2, "$8,650 $21,744 60%")]
IMM = (0.65, 0.66, 0.67)   # immunology cycle 1-2 analogs: Otezla 65%, Stelara 66%, Enbrel 67% (ira_cut_check)
IMM_QUOTES = [(NEG27, 2, "$1,650 $4,722 65%"), (NEG26, 2, "$4,695.00 $13,836.00 66%"), (NEG26, 2, "$2,355.00 $7,106.00 67%")]
DIAB = (0.66, 0.71, 0.85)  # diabetes: smallest (Jardiance 66%), same class GLP-1 (Ozempic 71%), largest (Janumet 85%)
DIAB_QUOTES = [(NEG27, 2, "$274 $959 71%")]
ALL_CUTS = (0.38, 0.655, 0.85)  # no same-class analog: cycle 1-2 smallest, median of the 16 in ira_cut_check, largest
K_NET = (0.3, 0.4, 0.5)         # KQ2 cross-check: net hit 0.3-0.5 x list discount for rebated classes

IRA_DRUGS = [
    # ticker, drug, ipay, G (USD m), spend doc, page, spend quote, d, g_pre or None, k, analog quotes, disclosed
    ("LLY", "Verzenio", 2028, 1428.714, CMS28, 1, "Verzenio Breast cancer $1,428,714,000", ONC, W.M_MDP_CATASTROPHIC,
     None, ONC_ANALOG_QUOTES, date(2026, 1, 27)),
    ("LLY", "Trulicity", 2028, 4898.378, CMS28, 1, "multiple cardiovascular risk factors $4,898,378,000", DIAB,
     W.G_PRE_GLP1, None, DIAB_QUOTES, date(2026, 1, 27)),
    ("GILD", "Biktarvy", 2028, 3904.486, CMS28, 1, "Biktarvy Human immunodeficiency virus type 1 infection $3,904,486,000",
     ALL_CUTS, W.M_MDP_CATASTROPHIC, None, [], date(2026, 1, 27)),
    ("BMY", "Orencia", 2028, 2450.065, CMS28, 1, "Orencia Psoriatic arthritis; Rheumatoid arthritis $2,450,065,000",
     IMM, W.G_PRE_IMMUNOLOGY, None, IMM_QUOTES, date(2026, 1, 27)),
    ("JNJ", "Erleada", 2028, 1947.504, CMS28, 1, "Erleada Prostate cancer $1,947,504,000", ONC, W.M_MDP_CATASTROPHIC,
     None, ONC_ANALOG_QUOTES, date(2026, 1, 27)),
    ("PFE", "Xeljanz", 2028, 1013.332, CMS28, 1, "Rheumatoid arthritis; Ulcerative colitis $1,013,332,000", IMM,
     W.G_PRE_IMMUNOLOGY, None, IMM_QUOTES, date(2026, 1, 27)),
    ("ABBV", "Botox", 2028, 1143.070, CMS28, 1, "Spasticity; Other movement disorders $1,143,070,000", ALL_CUTS, None,
     K_NET, [], date(2026, 1, 27)),
    ("BMY", "Pomalyst", 2027, 2069.147, CMS27, 1, "Pomalyst Kaposi sarcoma; Multiple myeloma $2,069,147,000", 0.60,
     W.M_MDP_CATASTROPHIC, None, [(NEG27, 2, "$8,650 $21,744 60%")], date(2025, 11, 15)),
    ("PFE", "Ibrance", 2027, 1984.624, CMS27, 1, "Ibrance Breast cancer $1,984,624,000", 0.50, W.M_MDP_CATASTROPHIC,
     None, [(NEG27, 2, "Ibrance Pfizer Inc. Breast cancer $7,871 $15,741 50%")], date(2025, 11, 15)),
    ("AZN", "Calquence", 2027, 1614.250, CMS27, 1, "Mantle cell lymphoma $1,614,250,000", 0.40, W.M_MDP_CATASTROPHIC,
     None, [(NEG27, 2, "$8,600 $14,228 40%")], date(2025, 11, 15)),
    ("ABBV", "Linzess", 2027, 1937.912, CMS27, 1, "syndrome with constipation $1,937,912,000", 0.75, None, K_NET,
     [(NEG27, 2, "$136 $539 75%")], date(2025, 11, 15)),
    ("ABBV", "Vraylar", 2027, 1085.788, CMS27, 1, "Schizophrenia $1,085,788,000", 0.44, None, K_NET,
     [(NEG27, 2, "$770 $1,376 44%")], date(2025, 11, 15)),
    ("AMGN", "Otezla", 2027, 994.001, CMS27, 1, "Psoriatic arthritis $994,001,000", 0.65, W.G_PRE_IMMUNOLOGY, None,
     [(NEG27, 2, "$1,650 $4,722 65%")], date(2025, 11, 15)),
    ("MRK", "Janumet", 2027, 1082.464, CMS27, 1, "Janumet; Janumet XR Type 2 diabetes $1,082,464,000", 0.85,
     W.G_PRE_GLP1, None, [(NEG27, 2, "Janumet; Janumet XR Merck Sharp & Dohme LLC Type 2 diabetes $80 $526 85%")],
     date(2025, 11, 15)),
    ("NVO", "Ozempic/Rybelsus/Wegovy", 2027, 14426.566, CMS27, 1, "$14,426,566,000", 0.71, W.G_PRE_GLP1, None,
     [(NEG27, 2, "$274 $959 71%")], date(2025, 11, 15)),
]


def _company_selection_quote(ticker, drug):
    """A sentence in the company's own annual or quarterly report that names the drug as selected or negotiated."""
    idx = load_index()
    from agent.moat import cite as moat
    rows = moat.db().execute("SELECT doc_id FROM docs WHERE ticker = ? AND doc_type IN ('annual_report', "
                             "'quarterly_report') ORDER BY filed DESC LIMIT 4", (ticker,)).fetchall()
    first = drug.split("/")[0]
    for (doc_id,) in rows:
        for n, (_, text) in idx.pages(doc_id).items():
            for sent in re.split(r"(?<=[.;])\s+", text):
                if re.search(first, sent, re.I) and re.search(r"selected|negotiat|government-set", sent, re.I) \
                        and 40 <= len(sent) <= 400:
                    c = cite_verify(Citation(canonical_id=doc_id, page=n, quote=sent.strip(), claim_type="quote"), idx)
                    if c.verification.ok:
                        return c
    return None


# ------------------------------------------------------------------ the finding record
@dataclass
class Scored:
    ticker: str
    id: str
    kind: str
    sentence: str
    family: Family
    channel: str
    direction: str
    impact: IM.Impact
    peer: dict
    vector: dict
    S: float
    confidence: str
    confidence_reasons: list
    flags: list
    citations: list            # list[Citation], key claims first
    claims: list               # list[list[Citation]] key claims for E
    old_S: float | None = None
    old_rank: int | None = None
    needle_eligible: bool = False
    detector: str = ""
    product: str = ""

    def to_dict(self):
        body = render_markdown([Claim(self.sentence, [c for c in self.citations if c.page is not None][:6])])
        return {
            "id": self.id, "ticker": self.ticker, "signal_kind": self.kind, "signal_family": self.family.name,
            "has_detector": self.family.has_detector, "detector": self.detector, "block": self.family.block,
            "channel": self.channel, "direction": self.direction, "sentence": self.sentence, "sentence_md": body,
            "impact": self.impact.to_dict(), "peer": self.peer, "vector": self.vector, "S": self.S,
            "confidence": self.confidence, "confidence_reasons": self.confidence_reasons, "flags": self.flags,
            "needle_eligible": self.needle_eligible, "old_S": self.old_S,
            "citations": [c.to_dict() for c in self.citations],
        }


def _assemble(co, ticker, kind, sentence, fam, imp, page_cites, topics, disclosed, product=None, peer=None,
              extra_flags=(), z_text=None, diagnostics_pass=True, generic_placeholder=False, detector=""):
    flags = list(extra_flags) + list(imp.flags) + list(co.flags)
    # M
    if not imp.quantified or not imp.adverse and not imp.quantified:
        M = 0.0
    else:
        M = materiality(imp.d_eps.get("base", 0.0), imp.t_years, co.sigma)
    # O
    z = OB.starter_thread(ticker, z_text or sentence, topics)
    h, rel_doc, hflags = OB.headline(ticker, topics)
    if hflags:
        h = OB.headline_imputed(topics)
        flags.append(f"h_f imputed {h:.3f}: no earnings release in the index (shortlist median for these topics)")
    a, a_note, aflags = OB.attention(ticker, topics, product)
    flags += aflags
    adverse = imp.adverse
    if fam.route in ("type_c",) and imp.fiscal_year:
        c, cflags = OB.consensus_embedding(ticker, imp.fiscal_year, disclosed, imp.d_eps.get("base", 0.0), adverse)
    else:
        c, cflags = 0.0, ["c_f n/a (no consensus line item for this family)"]
    flags += cflags
    s = 0.0
    flags.append("s_f no data (FINRA short interest not in moat)")
    if disclosed is None:
        age = W.LOE_AGE_MONTHS_DEFAULT
        flags.append(f"age unknown: set to {W.LOE_AGE_MONTHS_DEFAULT:.0f} months")
    else:
        age = OB.months_between(disclosed, data.AS_OF)
    O = OB.obscurity(z, h, a, c, s, age)
    # E
    claims = [[c_] for c_ in page_cites]
    impact_cites = [c_ for c_ in imp.citations]
    E_pages = EV.evidence_score(claims) if claims else 0.0
    E = E_pages
    if generic_placeholder:
        E = min(E, W.G_ENTAILED)
        flags.append("impact is the generic anchor placeholder (3% of revenue margin event); no page-verified number "
                     f"backs it: E capped at {W.G_ENTAILED}")
    pi = fam.pi
    S = score(M, O, E, pi)
    n_ind = EV.n_independent(page_cites)
    official = any(EV.official_verbatim(c_) for c_ in page_cites) and fam.route == "type_c"
    contradicted = False
    conf, reasons = EV.confidence(E, n_ind, official, generic_placeholder, fam.diagnostic, contradicted,
                                  diagnostics_pass)
    direction = "adverse" if adverse else ("favorable" if fam.route == "favorable" or not imp.quantified else "favorable-quantified")
    vector = {"M": M, "sigma_EPS": co.sigma, "sigma_currency": co.currency, "dEPS_base": imp.d_eps.get("base"),
              "t_years": imp.t_years, "O": O, "z": z, "h": h, "headline_doc": rel_doc, "a": a, "a_source": a_note,
              "c": c, "s": s, "age_months": age, "H": W.H_MONTHS, "disclosed": disclosed.isoformat() if disclosed else None,
              "E": E, "E_pages": E_pages, "n_ind": n_ind, "pi": pi, "pi_route": fam.route, "topics": topics}
    first = page_cites[0].cite_id if page_cites else kind
    sc = Scored(ticker, finding_id(ticker, kind, first), kind, sentence, fam, imp.channel, direction, imp,
                peer or {}, vector, S, conf, reasons, flags, list(page_cites) + impact_cites, claims,
                detector=detector, product=product or "")
    sc.needle_eligible = (O >= W.NEEDLE_O and E >= W.NEEDLE_E and conf != "LOW" and z == 0
                          and (adverse or imp.quantified) and S > 0)
    return sc


def score_signal(sig, co, panel=None):
    """One detector Signal -> Scored (or None when the family is IRA and the generator covers it)."""
    fam0 = FAM.get(KIND.get(sig.kind, ""), None)
    topics = topics_of(sig, fam0 or FAM["none_X"])
    fam = family_of(sig, topics)
    topics = topics_of(sig, fam)
    page_cites = [EV.from_evidence(ev) for ev in sig.evidence]
    flags, diag = [], True
    product = sig.meta.get("product")
    disclosed = max((d for d in (_filed(ev.doc_id) for ev in sig.evidence) if d), default=None)
    generic = False
    if fam.route in ("backtest", "anchor", "directional", "none"):
        imp = IM.anchor(co)
        generic = sig.detector in ("drift", "calls")
        if fam in (FAM["inventory"], FAM["dio"]):
            share, detail, cit = stage_split(page_cites)
            flags.append(f"stage split: {detail}")
            if cit is not None:
                page_cites.append(cit)
            if share is None:
                diag = False
            elif share < 0.5:
                diag = False
                flags.append("capacity build, not channel stuffing")
        if fam in (FAM["receivables"], FAM["dso"]):
            diag = False
            flags.append("DSO channel-stuffing test: wholesaler-language half not checked (mandatory diagnostic)")
    elif fam is FAM["favorable"]:
        imp = IM.Impact("none", formula="favorable level vs peers: no adverse scenario (section 10.2)",
                        adverse=False, quantified=False)
        imp.d_eps = {"bull": 0.0, "base": 0.0, "bear": 0.0}
    elif fam is FAM["loe"]:
        imp, lflags, disclosed = _loe_impact(sig, co)
        flags += lflags
    elif fam is FAM["footnote"]:
        imp, _ = IM.footnote(co, "impairment_booked")
    elif fam is FAM["trial"]:
        imp = IM.Impact("trial", formula="business-reason trial stop: no in-window revenue path", quantified=False)
        imp.d_eps = {"bull": 0.0, "base": 0.0, "bear": 0.0}
        flags.append("trial stop: pipeline asset, no in-window revenue; dEPS = 0")
    elif fam is FAM["ira"]:
        imp = IM.Impact("ira", formula="IRA row from the label detector; scored by the IRA generator when the drug is "
                                       "in IRA_DRUGS, else already effective", quantified=False)
        imp.d_eps = {"bull": 0.0, "base": 0.0, "bear": 0.0}
        sel = (sig.meta.get("data") or {}).get("product") or {}
        if sel.get("ipay") and int(sel["ipay"]) <= data.AS_OF.year:
            flags.append(f"MFP effective {sel.get('mfp_effective')}: already in reported numbers, dEPS = 0")
    else:  # label facts
        imp = IM.label_unquantified(co, sig.kind)
        disclosed = None
    if disclosed is None and fam.route not in ("type_c",):
        flags.append("disclosure date unknown")
    peer = {"metric_value": sig.value, "peer_median": sig.peer_median, "peer_z": sig.peer_z,
            "rival": sig.meta.get("rival")}
    sc = _assemble(co, sig.ticker, sig.kind, sig.detail, fam, imp, page_cites, topics, disclosed, product=product,
                   peer=peer, extra_flags=flags, diagnostics_pass=diag, generic_placeholder=generic,
                   detector=sig.detector)
    if not sig.evidence:
        sc.flags.append("no page evidence from the detector: E = 0, withheld by the gate")
    return sc


def _loe_impact(sig, co):
    """LOE channel with company-stated dates (10-K patent table, company_stated_loe.jsonl) ahead of the detector's
    Orange/Purple Book date."""
    import json
    flags = []
    meta = sig.meta.get("data") or {}
    prod = (sig.meta.get("product") or "").lower()
    loe_date = OB.to_date(meta.get("product_end"))
    src = "Orange/Purple Book (detector)"
    if data.LOE_CACHE and data.LOE_CACHE.exists():
        for line in data.LOE_CACHE.read_text(encoding="utf-8").splitlines():
            try:
                r = json.loads(line)
            except ValueError:
                continue
            if prod and prod in (r.get("product") or "").lower():
                m = re.search(r"(\d{1,2})/(\d{1,2})/(\d{4})", str(r.get("us_loe")))
                y = re.search(r"(20\d\d)", str(r.get("us_loe")))
                if m:
                    loe_date = date(int(m.group(3)), int(m.group(1)), int(m.group(2)))
                elif y:
                    loe_date = date(int(y.group(1)), 1, 1)
                src = f"company-stated {r.get('form')} {r.get('period')}: \"{(r.get('quote') or '')[:80]}\""
                break
    flags.append(f"LOE date source: {src}")
    rev_pre = _product_revenue(sig.ticker, prod)
    if rev_pre is None:
        flags.append("product revenue not found: LOE not quantified")
        imp = IM.Impact("loe", formula="product revenue missing", quantified=False)
        imp.d_eps = {"bull": 0.0, "base": 0.0, "bear": 0.0}
        return imp, flags, None
    biologic = "purple_book" in json.dumps(meta).lower() and "orange" not in str(meta.get("product_fields", "")).lower()
    imp = IM.loe(co, prod, rev_pre, loe_date or date(2100, 1, 1), biologic)
    return imp, flags, None


def _product_revenue(ticker, prod):
    """Latest full-year product revenue (USD m) from product_revenue_quarterly.csv (days >= 360), else None."""
    import pandas as pd
    try:
        d = _prq()
    except Exception:
        return None
    d = d[(d.ticker == ticker) & d.product_member.astype(str).str.lower().str.contains(prod[:6] or "zzz")
          & d.concept.astype(str).str.contains("Revenue") & (d.days >= 360)]
    if d.empty:
        return None
    d = d.sort_values("period_end")
    last = d[d.period_end == d.period_end.iloc[-1]]
    us = last[last.geography.astype(str).str.contains("US|UnitedStates|UNITED", case=False, na=False)]
    return float((us if len(us) else last).value_usd.max()) / 1e6


_PRQ = {}


def _prq():
    import pandas as pd
    if "d" not in _PRQ:
        _PRQ["d"] = pd.read_csv(data.tables("product_revenue_quarterly.csv"), low_memory=False)
    return _PRQ["d"]


def ira_findings(ticker, co):
    """IRA channel candidates for one company (section 4.3 b): one per CMS-selected drug with IPAY 2027 or 2028."""
    idx = load_index()
    out = []
    for (t, drug, ipay, G, sdoc, spage, squote, d, g_pre, k, analogs, disclosed) in IRA_DRUGS:
        if t != ticker:
            continue
        spend = cite_verify(Citation(canonical_id=sdoc, page=spage, quote=squote, claim_type="number",
                                     value=f"{G * 1e6:,.0f}"), idx)
        analog_cites = [cite_verify(Citation(canonical_id=a, page=p, quote=q, claim_type="quote"), idx)
                        for a, p, q in analogs]
        comp = _company_selection_quote(ticker, drug)
        flags = []
        cur_ok = co.fin_currency.startswith("USD") and co.currency == "USD"
        if not cur_ok:
            flags.append(f"USD channel on a {co.fin_currency}/{co.currency} reporter: no cited FX rate; not converted, "
                         "dEPS set to 0")
        imp = IM.ira(co, drug, G if cur_ok else 0.0, d, g_pre, ipay, k_factor=k,
                     cites=[spend] + analog_cites)
        if k is None and isinstance(d, tuple) and d == ALL_CUTS:
            flags.append("no same-class MFP analog: d = cycle 1-2 smallest / median / largest (deviation, see notes)")
        if drug == "Trulicity":
            flags.append("Trulicity loses US exclusivity in 2027 (starter thread); biosimilar entry would end selection")
        if ticker == "GILD":
            flags.append("adjacent to GILD's starter thread (HIV franchise durability): human check before pitching")
        sentence = (f"{drug}'s Medicare price is set by negotiation from January {ipay}: CMS Part B+D spend "
                    f"${G:,.1f}M; base list discount {d[1] if isinstance(d, tuple) else d:.0%}.")
        page_cites = [spend] + ([comp] if comp else [])
        if comp is None:
            flags.append("company filing sentence naming the selection not found: n_ind = 1")
        sc = _assemble(co, ticker, "ira_selected", sentence, FAM["ira"], imp, page_cites, ["ira"], disclosed,
                       peer={"analogs": [c.quote for c in analog_cites]}, extra_flags=flags,
                       z_text=f"{drug} ira negotiation", detector="ira_generator")
        sc.product = drug
        out.append(sc)
    return out
