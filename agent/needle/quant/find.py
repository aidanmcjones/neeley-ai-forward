"""FIND: S_f = M_f . O_f . E_f . pi_k(f)   (docs/quant_model.md section 4).

M_f = |dEPS_f| . (1 + r)^(-t_f) / sigma_EPS                  section 4.2
O_f = D_f . 2^(-age / H), D_f = (1-z)(1-h)(1-a)(1-c)(1-s)     section 4.4   (obscurity.py; Needle floor on D)
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


# Robustness knob (league_v3 variant): give anchor rows, which have no fiscal-year consensus line, c = 0.5 as well.
C_ANCHOR_UNINFORMATIVE = False


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
    "litigation": Family("high-litigiousness text change", "T", W.PI_LITIGATION_TEXT, "anchor", True),
    "mdna": Family("MD&A change", "T", W.PI_MDNA, "anchor", False),
    "directional": Family("non-answer / deflection", "C", W.PI_MIN, "directional", False),
    "none_C": Family("repeated deflection / topic surge (no evidence)", "C", W.PI_NONE, "none", False),
    "none_A": Family("ETR / R&D shift or level outlier (no evidence)", "A", W.PI_NONE, "none", False),
    "none_X": Family("outside data: FAERS, demand divergence, distributor (no evidence)", "X", W.PI_NONE, "none", False),
    "ira": Family("contractual: IRA negotiation", "P", W.PI_CONTRACTUAL, "type_c", True, ("ira",)),
    "mfn": Family("contractual: MFN agreement", "P", W.PI_CONTRACTUAL, "type_c", True, ("mfn",)),
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
                     "zero-question calls", "GTN widening", "footnote extractor"]

TOPIC_KEYS = list(OB.TOPIC_WORDS)
# Text and call topics that name an impact channel with its own scored row (review R2). Other topics (pricing, gtn,
# 340b, supply, tariff, litigation, china, guidance) have no channel inputs in the data layer.
TOPIC_CHANNEL = {"ira": "ira", "mfn": "mfn", "generic": "loe"}


def topic_channel(topics):
    """The one impact channel a text or call row's topics map to, or None (no mapping, or several channels)."""
    chans = {TOPIC_CHANNEL[t] for t in topics if t in TOPIC_CHANNEL}
    return chans.pop() if len(chans) == 1 else None


def family_of(sig, topics):
    """Section 4.6 family for a detector Signal."""
    k = KIND.get(sig.kind)
    if sig.kind == "gross_margin_peer_outlier":
        favorable = sig.value is not None and sig.peer_median is not None and sig.value >= sig.peer_median
        return FAM["favorable"] if favorable else FAM["none_A"]
    if favorable_statistical(sig):
        return FAM["favorable"]
    if sig.detector == "drift" and [t for t in topics if t != "other"] == ["litigation"]:
        return FAM["litigation"]     # review A5: only when litigation is the row's only (primary) topic
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


BACKTEST_FLAG = {"inventory": "inventory_outpaces_revenue", "receivables": "receivables_outpace_revenue",
                 "dio": "dio_rising", "dso": "dso_rising", "gm_drop": "gross_margin_drop"}
ANNUAL_TRIGGER = {"inventory_outpaces_revenue": 0.10, "receivables_outpace_revenue": 0.08, "dio_rising": 0.15,
                  "dso_rising": 0.10}   # agent/needle/backtest.py signals_at thresholds


def backtest_fired(sig, fam_key):
    """Does the row satisfy the backtest flag whose lift gives its pi (review A1)? Quarterly rows: re-evaluate
    agent.needle.backtest.signals_at on the XBRL panel at the row's quarter. Annual rows: the row's own value when
    it is that flag's quantity. Peer-level outliers that do not fire take pi_min."""
    from agent.needle import backtest, xbrl
    flag = BACKTEST_FLAG[fam_key]
    per = str(sig.period or "")
    if re.fullmatch(r"\d{4}Q[1-4]", per):
        try:
            return bool(backtest.signals_at(xbrl.panel(sig.ticker), per).get(flag))
        except Exception:
            return False
    if sig.value is None or sig.kind.endswith("_peer_outlier") and fam_key in ("dio", "dso"):
        return False
    if flag == "gross_margin_drop":
        return -sig.value >= 0.02
    return sig.value >= ANNUAL_TRIGGER[flag]


def downgraded(fam):
    """The same family with the backtest lift removed: pi_min (directional route), not diagnostic."""
    return Family(fam.name + " (backtest flag not fired: pi_min)", fam.block, W.PI_MIN, "directional", False,
                  fam.topics)


# Detector kinds that restate one underlying metric (a time-series flag and its peer-outlier twin, review S1).
FACT_METRIC = {"receivables_outpace_revenue": "receivables_gap", "rec_gap_peer_outlier": "receivables_gap",
               "inventory_outpaces_revenue": "inventory_gap", "inv_gap_peer_outlier": "inventory_gap",
               "dio_rising": "dio", "dio_peer_outlier": "dio", "dso_rising": "dso", "dso_peer_outlier": "dso",
               "tax_rate_shift": "etr", "etr_peer_outlier": "etr", "rnd_shift": "rnd", "rnd_pct_peer_outlier": "rnd",
               "gross_margin_drop": "gross_margin", "gross_margin_peer_outlier": "gross_margin"}


def fact_key(sig):
    """(ticker, period, underlying metric) for statistical rows; None for rows that are their own fact."""
    m = FACT_METRIC.get(sig.kind)
    return f"{sig.ticker}|{sig.period}|{m}" if m else ""


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
        idx = data.index()
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


def first_public(sig):
    """(date, note): the first public date of the fact, not a later filing that repeats it (review R1, D1 resolved
    toward A). The filing that states the fact is the newest evidence document (an older one is the comparison base,
    e.g. last year's 10-K for a drift row). For financial-statement rows (forensics) the same numbers were public
    earlier in the earnings release for that period, so the earliest release filed after the period end and on or
    before the filing is used when the index has one."""
    dated = [(d, ev.doc_id) for d, ev in ((_filed(ev.doc_id), ev) for ev in sig.evidence) if d]
    if not dated:
        return None, ""
    filed, doc_id = max(dated)
    if sig.detector != "forensics":
        return filed, ""
    r = data.doc_row(doc_id)
    pend = OB.to_date(r["period"]) if r is not None and r["period"] else None
    if pend is None:
        return filed, ""
    rel = data.db().execute("SELECT doc_id, filed FROM docs WHERE ticker = ? AND doc_type = 'earnings_release' AND "
                            "filed > ? AND filed <= ? ORDER BY filed LIMIT 1",
                            (sig.ticker, pend.isoformat(), filed.isoformat())).fetchone()
    if rel is None:
        return filed, ""
    d = OB.to_date(rel[1])
    return d, f"age from first public date {d.isoformat()} (earnings release {rel[0]}), not the filing {filed.isoformat()}"


def stage_split(cites):
    """Inventory stage split (section 4.3 g i): finished-goods share from the inventory note of the cited filing.
    Returns (fg_share or None, detail, citation or None)."""
    idx = data.index()
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

LOW_REBATE = {"Verzenio", "Erleada", "Pomalyst", "Ibrance", "Calquence", "Biktarvy"}   # oncology, HIV

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
    idx = data.index()
    from agent.moat import cite as moat
    rows = data.db().execute("SELECT doc_id FROM docs WHERE ticker = ? AND doc_type IN ('annual_report', "
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
    pi_downgraded: bool = False
    fact_key: str = ""            # one underlying fact = one key (review S1); league keeps one row per key
    not_quantified: str = ""      # reason when the row has no impact channel (review R2): impact None, S = 0

    def to_dict(self):
        body = render_markdown([Claim(self.sentence, [c for c in self.citations if c.page is not None][:6])])
        return {
            "id": self.id, "ticker": self.ticker, "signal_kind": self.kind, "signal_family": self.family.name,
            "has_detector": self.family.has_detector, "detector": self.detector, "block": self.family.block,
            "channel": self.channel, "direction": self.direction, "sentence": self.sentence, "sentence_md": body,
            "impact": None if self.not_quantified else self.impact.to_dict(),
            "impact_channel": self.impact.channel, "not_quantified": self.not_quantified or None,
            "peer": self.peer or {"note": "no peer analogue"}, "vector": self.vector, "S": self.S,
            "confidence": self.confidence, "confidence_reasons": self.confidence_reasons, "flags": self.flags,
            "needle_eligible": self.needle_eligible, "old_S": self.old_S, "fact_key": self.fact_key,
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
    if (fam.route == "type_c" or detector == "mfn_generator") and imp.fiscal_year:
        # rows with a dated fiscal-year impact: the consensus-embedding test is defined; untestable -> 0.5 (A12)
        c, cflags = OB.consensus_embedding(ticker, imp.fiscal_year, disclosed, imp.d_eps.get("base", 0.0), adverse)
    elif C_ANCHOR_UNINFORMATIVE and imp.quantified:
        c, cflags = W.C_UNTESTABLE, [f"c_f set to {W.C_UNTESTABLE} on a row with no fiscal-year line (variant)"]
    else:
        c, cflags = 0.0, ["c_f n/a (no fiscal-year consensus line for this family: anchor rows have no dated year)"]
    flags += cflags
    s = 0.0
    flags.append("s_f no data (FINRA short interest not in moat)")
    if disclosed is None:
        age = W.LOE_AGE_MONTHS_DEFAULT
        flags.append(f"age unknown: set to {W.LOE_AGE_MONTHS_DEFAULT:.0f} months")
    else:
        age = OB.months_between(disclosed, data.AS_OF)
    Dd = OB.discussion(z, h, a, c, s)
    dec = OB.decay(age)
    O = Dd * dec
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
              "c": c, "s": s, "D": Dd, "decay": dec, "age_months": age, "H": W.H_MONTHS, "disclosed": disclosed.isoformat() if disclosed else None,
              "E": E, "E_pages": E_pages, "n_ind": n_ind, "pi": pi, "pi_route": fam.route, "topics": topics}
    first = page_cites[0].cite_id if page_cites else kind
    sc = Scored(ticker, finding_id(ticker, kind, first), kind, sentence, fam, imp.channel, direction, imp,
                peer or {}, vector, S, conf, reasons, flags, list(page_cites) + impact_cites, claims,
                detector=detector, product=product or "")
    sc.needle_eligible = (Dd >= W.NEEDLE_O and E >= W.NEEDLE_E and conf != "LOW" and z == 0
                          and (adverse or imp.quantified) and S > 0)
    return sc


def score_signal(sig, co, panel=None):
    """One detector Signal -> Scored (or None when the family is IRA and the generator covers it)."""
    fam0 = FAM.get(KIND.get(sig.kind, ""), None)
    topics = topics_of(sig, fam0 or FAM["none_X"])
    fam = family_of(sig, topics)
    topics = topics_of(sig, fam)
    pi_downgrade = False
    fk = next((k for k, v in FAM.items() if v is fam), None)
    if fk in BACKTEST_FLAG and not backtest_fired(sig, fk):
        fam, pi_downgrade = downgraded(fam), True
    page_cites = [EV.from_evidence(ev) for ev in sig.evidence]
    flags, diag = [], True
    product = sig.meta.get("product")
    disclosed, age_note = first_public(sig)
    if age_note:
        flags.append(age_note)
    generic = False
    nq_reason = ""
    if fam.route in ("backtest", "anchor", "directional", "none"):
        # Review R2 (A20, B4, A1): the 3%-of-revenue anchor is the size of a backtested margin event, so it applies
        # only to a backtested time-series flag that fired. hit_rates.json has a dose response only by the number of
        # flags (dose_response_full_coverage), not by one flag's strength, so the anchor is flat (D3, a stated limit).
        if fk in BACKTEST_FLAG and not pi_downgrade:
            imp = IM.anchor(co)
            imp.flags.append("anchor flat across flag strength: hit_rates.json has no per-flag dose response (D3)")
        else:
            ch = topic_channel(topics) if sig.detector in ("drift", "calls") else None
            if ch:
                nq_reason = (f"mapped to the {ch} channel: that channel's own row carries the dollars; this row "
                             "corroborates it and is not scored separately (one fact, one row)")
            elif fk in BACKTEST_FLAG:
                nq_reason = "not quantified: backtest flag not fired, so the anchor event size does not apply (R2)"
            else:
                nq_reason = (f"not quantified: no impact channel for {sig.detector} topics {', '.join(topics)} "
                             "(R2: the generic anchor applies only to fired backtest flags)")
            imp = IM.not_quantified(ch or "none", nq_reason)
        if fk in ("inventory", "dio"):
            share, detail, cit = stage_split(page_cites)
            flags.append(f"stage split: {detail}")
            if cit is not None:
                page_cites.append(cit)
            if share is None:
                diag = False
            elif share < 0.5:
                diag = False
                flags.append("capacity build, not channel stuffing")
        if fk in ("receivables", "dso"):
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
    sc.fact_key = fact_key(sig)
    sc.not_quantified = nq_reason
    if pi_downgrade:
        sc.flags.append(f"pi downgraded to pi_min: row does not satisfy the backtest flag "
                        f"{BACKTEST_FLAG[fk]} (review A1)")
        sc.pi_downgraded = True
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
    idx = data.index()
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
        cites = [spend] + analog_cites
        # Spec formula G x (d - g_pre) kept for comparison; the league uses the KQ2 class rule (coordinator
        # review A15): net hit = 1.0 x list discount for low-rebate classes (oncology, HIV), 0.3 / 0.4 / 0.5 x for
        # highly rebated classes.
        imp_spec = IM.ira(co, drug, G if cur_ok else 0.0, d, g_pre, ipay, k_factor=k, cites=cites) \
            if (g_pre is not None or k) else None
        k_cross = (1.0, 1.0, 1.0) if drug in LOW_REBATE else K_NET
        imp = IM.ira(co, drug, G if cur_ok else 0.0, d, None, ipay, k_factor=k_cross, cites=cites)
        imp.flags = [x for x in imp.flags if "no g_pre prior" not in x]
        imp.flags.append(f"IRA net hit = {k_cross} x list discount ({'low-rebate class' if drug in LOW_REBATE else 'rebated class'}; "
                         "KQ2 cross-check, review A15)")
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
        if imp_spec is not None:
            m_spec = materiality(imp_spec.d_eps.get("base", 0.0), imp_spec.t_years, co.sigma)
            sc.vector["dRev_spec_formula"] = imp_spec.d_rev
            sc.vector["M_spec_formula"] = m_spec
            sc.vector["S_spec_formula"] = score(m_spec, sc.vector["O"], sc.vector["E"], sc.vector["pi"])
        out.append(sc)
    return out


# ------------------------------------------------------------------ MFN candidates (section 4.3 c) and tariff note
def _moat_doc_id(path):
    """policy_exposure.csv doc path -> citation index doc_id."""
    p = str(path or "")
    if p.startswith("data/moat/policy_gov/"):
        return "policy_gov:" + p[len("data/moat/"):]
    m = re.match(r"data/corpus/companies/([A-Z]+)/(.+)", p)
    if m:
        return f"{m.group(1)}:{m.group(2)}"
    m = re.match(r"data/moat/companies/([A-Z]+)/.+", p)
    if m:
        return f"{m.group(1)}:{p[len('data/moat/'):]}"
    return p


def _policy_rows(ticker):
    import pandas as pd
    pe = pd.read_csv(data.verified("policy/policy_exposure.csv"), dtype=str)
    fs = pd.read_csv(data.verified("policy/force_summary.csv"), dtype=str)
    return pe[pe.ticker == ticker], fs[fs.ticker == ticker]


def tariff_exposure(ticker):
    """Exposure proxy (coordinator review B9): pct_mfg_sites_outside_us x us_revenue_share, with the 2029-01-20 cliff.
    Not a scored dEPS (outside the 24-month window, section 4.3 d). Returns a dict or None."""
    try:
        _, fs = _policy_rows(ticker)
    except FileNotFoundError:
        return None
    if fs.empty:
        return None
    r = fs.iloc[0]
    out = float(r.pct_mfg_sites_outside_us) / 100 * float(r.us_revenue_share_pct) / 100
    return {"proxy": out, "pct_mfg_sites_outside_us": float(r.pct_mfg_sites_outside_us),
            "us_revenue_share_pct": float(r.us_revenue_share_pct), "exempt_until": r.tariff_exempt_until,
            "note": "exposure proxy only: share of manufacturing sites outside the US x US revenue share; MFN signers "
                    "pay no Section 232 duty until 2029-01-20 (outside the window)"}


# Variant knob for the league_v3 robustness table: True restores the v2 rule (Pfizer's universal 0.65% of US revenue at
# pi = 1 for every company). The league value is the directional rule (review R3, A9, B9).
MFN_UNIVERSAL = False
MFN_DIRECTIONAL = Family("directional: MFN agreement (deal terms confidential)", "P", W.PI_MIN, "directional", False,
                         ("mfn",))
SDUD_MEDICAID_BASIC_REBATE = 0.231   # statutory Medicaid basic rebate for brand drugs (23.1% of AMP), 42 USC 1396r-8


def _policy_cite(row, idx):
    """Page citation for one policy_exposure row, falling back to its facts row when the page quote does not verify."""
    page = int(re.sub(r"\D", "", str(row.printed_page_or_section)) or 1)
    pc = cite_verify(Citation(canonical_id=_moat_doc_id(row.doc), page=page, quote=str(row.quote), claim_type="quote"),
                     idx)
    if pc.verification.ok:
        return pc
    ft = data.fact_by_key("policy/policy_exposure.csv", row.row_id)
    return ft if ft.verification.ok else None


def _eliquis_medicaid_gross():
    """(FY2025 Medicaid gross reimbursement for Eliquis in USD m, Citation) from medicaid_sdud.csv, or (None, None)."""
    import pandas as pd
    try:
        d = pd.read_csv(data.tables("medicaid_sdud.csv"), dtype={"ndc": str})
    except FileNotFoundError:
        return None, None
    e = d[(d.drug.astype(str).str.lower() == "eliquis") & (d.year == 2025)]
    if e.empty or e.quarter.nunique() < 4:
        return None, None
    g = float(e.total_amount_reimbursed.sum()) / 1e6
    return g, data.table_citation("medicaid_sdud.csv", "eliquis|2025Q1-Q4", "total_amount_reimbursed", f"{g:,.1f}M")


def _mfn_quantified(ticker, co, pe, idx):
    """A company-stated or computable MFN size (review D2: NVO's stated sales-growth impact; BMY's Eliquis free to
    Medicaid via SDUD). Returns (Impact, sentence clause, [Citation], [flags]) or None."""
    mfn = pe[pe.force == "MFN"]
    if ticker == "NVO":
        r = mfn[mfn.item.str.contains("Stated", na=False) & mfn.value.str.contains("low single-digit", na=False)]
        if r.empty:
            return None
        row = r.iloc[0]
        c = _policy_cite(row, idx)
        share = (0.01, 0.02, 0.03)   # "low single-digit %": 1 / 2 / 3 percent of sales (inference)
        imp = IM.mfn(co, co.rev_ttm, s=share, cites=[c] if c else [], effective=OB.to_date(row.effective_date),
                     formula=f"company-stated {row.row_id}: low single-digit % x Rev_TTM {co.rev_ttm:,.1f} "
                             f"{co.fin_currency} (1 / 2 / 3%)")
        clause = (f"Novo states a negative low single-digit % impact on {str(row.effective_date)[:4]} global sales "
                  f"growth ({row.row_id}), about {co.fin_currency} {imp.d_rev['bull']:,.0f}M to "
                  f"{imp.d_rev['bear']:,.0f}M on TTM revenue")
        return imp, clause, [c] if c else [], ["MFN size from the company's own statement (review D2)"]
    if ticker == "BMY":
        r = mfn[mfn.item.str.contains("Eliquis free", na=False)]
        g, gc = _eliquis_medicaid_gross()
        if r.empty or g is None:
            return None
        row = r.iloc[0]
        c = _policy_cite(row, idx)
        up = g * (1 - SDUD_MEDICAID_BASIC_REBATE)
        imp = IM.mfn(co, up, s=(1.0, 1.0, 1.0), cites=([c] if c else []) + [gc],
                     effective=OB.to_date(row.effective_date),
                     formula=f"Eliquis FY2025 Medicaid gross reimbursement {g:,.1f} (SDUD) x (1 - basic rebate "
                             f"{SDUD_MEDICAID_BASIC_REBATE}): upper bound on net revenue given up")
        clause = (f"Eliquis is free to Medicaid from {row.effective_date} ({row.row_id}); FY2025 Medicaid gross "
                  f"reimbursement was ${g:,.0f}M (SDUD), at most about ${up:,.0f}M of net revenue a year before the "
                  "Pfizer alliance split")
        return imp, clause, [c] if c else [], ["MFN size computed from SDUD: upper bound (statutory basic rebate "
                                               "only; inflation rebates and the Pfizer alliance split lower it)"]
    return None


def mfn_findings(ticker, co):
    """One MFN candidate per company with a Medicaid MFN term in policy_exposure.csv (review R3, A9, B9).

    Deal texts are confidential, so MFN is scored as a direction: pi = pi_min (the directional floor) and no dollar
    figure in the sentence. M is the Pfizer Medicaid base rate (0.65% of US revenue) as an internal placeholder that
    is never printed. Where the company's own row states or lets us compute a size (NVO stated growth impact; BMY
    Eliquis free to Medicaid via SDUD), the row is sized from that row and cited. The sentence carries the per-company
    facts (agreement date, US investment pledge, TrumpRx prices) as cited context."""
    try:
        pe, fs = _policy_rows(ticker)
    except FileNotFoundError:
        return []
    if fs.empty:
        return []
    mfn = pe[pe.force == "MFN"]
    med = mfn[mfn.item.str.contains("Medicaid", na=False)]
    if med.empty:
        return []
    exact = med[med.item == "Medicaid MFN pricing"]
    row, f = (exact if len(exact) else med).iloc[0], fs.iloc[0]
    idx = data.index()
    pc = _policy_cite(row, idx)
    fact_term = data.fact_by_key("policy/policy_exposure.csv", row.row_id)
    us_share = float(f.us_revenue_share_pct) / 100
    fact_us = data.table_citation("policy/force_summary.csv", ticker, "us_revenue_share_pct", f.us_revenue_share_pct)
    flags = []
    tx = tariff_exposure(ticker)
    if tx:
        flags.append(f"tariff exposure proxy {tx['proxy']:.3f} (sites outside US {tx['pct_mfg_sites_outside_us']:.1f}% "
                     f"x US revenue {tx['us_revenue_share_pct']:.1f}%), exempt until {tx['exempt_until']}: not scored")
    rev_us = co.rev_ttm * us_share
    cur_ok = co.fin_currency.startswith("USD") and co.currency == "USD"
    page_cites = [pc] if pc is not None else []
    if pc is None:
        flags.append("MFN page quote did not verify and no facts row backs it")
    if MFN_UNIVERSAL:   # v2 rule, kept only for the robustness table
        flags += ["MFN (variant): s_MFN is Pfizer's Medicaid base rate applied to every company at pi = 1",
                  "Medicaid MFN terms started in 2026: part of the effect may already be in reported numbers"]
        imp = IM.mfn(co, rev_us if cur_ok else 0.0, cites=[fact_us] + ([fact_term] if fact_term.verification.ok else []))
        sentence = (f"{ticker}'s MFN agreement ({f.mfn_date}) extends MFN pricing to Medicaid: at the Pfizer base rate "
                    f"of 0.65% of US revenue (US share {f.us_revenue_share_pct}%), about ${imp.d_rev['base']:,.0f}M a year.")
        sc = _assemble(co, ticker, "mfn_medicaid", sentence, FAM["mfn"], imp, page_cites, ["mfn"],
                       OB.to_date(f.mfn_date), extra_flags=flags, z_text="mfn", detector="mfn_generator")
        return [sc]
    # per-company context: pledge and TrumpRx prices (cited, never sized)
    ctx, ctx_cites = [], []
    pledge = str(f.us_investment_pledge_usd_bn or "").strip()
    if pledge and pledge.lower() != "nan":
        ctx.append(f"US investment pledge ${pledge}bn")
        ctx_cites.append(data.table_citation("policy/force_summary.csv", ticker, "us_investment_pledge_usd_bn", pledge))
    for _, r in mfn[mfn.item.str.startswith("TrumpRx", na=False)].iterrows():
        ctx.append(f"TrumpRx: {r.value} ({r.row_id})")
        c = _policy_cite(r, idx)
        if c is not None:
            ctx_cites.append(c)
    q = _mfn_quantified(ticker, co, pe, idx)
    head = (f"{ticker} signed an MFN agreement on {f.mfn_date} that extends MFN pricing to Medicaid ({row.row_id})"
            + (f"; {'; '.join(ctx)}" if ctx else ""))
    if q is not None:
        imp, clause, qcites, qflags = q
        flags += qflags
        page_cites += [c for c in qcites if c is not None and c.verification.ok and c not in page_cites]
        sentence = f"{head}. {clause}. Direction: adverse to US net price."
    else:
        imp = IM.mfn(co, rev_us if cur_ok else 0.0, cites=[fact_us])
        imp.flags.append("MFN size is an internal placeholder (Pfizer base rate 0.65% of US revenue), not printed: "
                         "deal terms are confidential (review R3)")
        flags.append("Medicaid MFN terms started in 2026: part of the effect may already be in reported numbers")
        if not cur_ok:
            flags.append("non-USD reporter: USD placeholder not converted, dEPS 0")
        sentence = (f"{head}. Direction: adverse to US net price; size not disclosed (deal terms confidential), so no "
                    "dollar figure is given.")
    sc = _assemble(co, ticker, "mfn_medicaid", sentence, MFN_DIRECTIONAL, imp, page_cites, ["mfn"],
                   OB.to_date(f.mfn_date), extra_flags=flags, z_text="mfn", detector="mfn_generator")
    sc.citations += [c for c in ctx_cites if c not in sc.citations]
    sc.product = ""
    return [sc]
