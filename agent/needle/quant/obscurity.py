"""Obscurity O: probability the finding is not priced in (docs/quant_model.md section 4.4).

O_f = D_f . 2^(-age_f / H),   D_f = (1 - z_f)(1 - h_f)(1 - a_f)(1 - c_f)(1 - s_f)

D is the discussion term (has the market discussed it); the decay term is how long it has been public. The Sharpest
Needle floor applies to D only; decay stays inside S (review R1). Age runs from the first public date of the fact.

z  starter thread (case appendix): 1 if the finding restates it, else 0
h  0.9 if a topic pattern of the finding matches page 1 of the latest earnings release, else 0
a  share of the last up-to-10 calls in which analysts asked about the topic: priced_in_scorecard for its nine
   topics, qa_turns.csv (analyst turns, regex) for every other topic; products use the product name
c  consensus embedding: clip(dcons_dir / |dEPS|, 0, 1) over the I/B/E/S FY mean around the first public date;
   0.5 (uninformative) and flagged "untestable" when the test cannot be run, e.g. that fiscal year's consensus
   first appears after the disclosure (review A12; v2 used 0, the most optimistic value)
s  short sellers: 0 with a flag on every row (no FINRA data in the moat)
H  3 months base, 6 months as the reported sensitivity (review A11)
Each factor is the probability one channel has not priced the fact; channels are assumed independent (D8).
"""

import re
import warnings

warnings.filterwarnings("ignore", message="This pattern is interpreted as a regular expression")
from datetime import date

import pandas as pd

from . import data
from . import weights as W

TOPIC_WORDS = {  # the engine's topic regexes (agent.needle.score.TOPIC_WORDS), reused so topics mean the same thing
    "inventory": r"inventor", "receivables": r"receivable", "gross_margin": r"gross margin|cost of (sales|products)",
    "impairment": r"impairment", "tax": r"tax rate", "rnd": r"research and development",
    "ira": r"Inflation Reduction|negotiat", "mfn": r"most.favou?red|MFN", "tariff": r"tariff",
    "gtn": r"gross.to.net|rebate|net price|pricing", "340b": r"340B", "generic": r"generic|biosimilar|exclusivity",
    "litigation": r"litigation|lawsuit|talc", "supply": r"supply|manufactur", "pricing": r"pric", "china": r"China",
    "guidance": r"guidance",
}
SCORECARD_TOPIC = {  # engine topic -> priced_in_scorecard topic
    "ira": "IRA_negotiation", "mfn": "MFN", "tariff": "tariff", "gtn": "gross_to_net_price",
    "pricing": "gross_to_net_price", "340b": "gross_to_net_price", "generic": "biosimilar_generic",
    "inventory": "inventory_channel", "supply": "inventory_channel", "guidance": "guidance",
}

# Case appendix starter threads: (product regex, set of topics, or None = any topic). A finding restates the thread
# when it names the product (or, with product None, the topic alone) and its topic is in the set.
STARTER = {
    "MRK": [(r"keytruda", {"generic", "loe"}), (r"januvia|janumet|sitagliptin", None)],
    "BMY": [(r"eliquis|opdivo", {"generic", "loe"})],
    "PFE": [(r"ibrance", {"generic", "loe"})],
    "LLY": [(r"mounjaro|zepbound|tirzepatide", {"pricing", "gtn", "mfn"}), (r"orforglipron|pill", None),
            (r"trulicity", {"generic", "loe"})],
    "NVO": [(r"ozempic|wegovy|rybelsus|semaglutide", {"ira"})],
    "ABBV": [(r"humira|skyrizi|rinvoq", {"generic", "loe"})],
    "JNJ": [(r"stelara", {"generic", "loe"}), (None, {"ira"})],
    "AZN": [(r"farxiga|dapagliflozin", {"generic", "loe"})],
    "AMGN": [(r"enbrel|repatha", {"generic", "loe"})],
    "GILD": [],
}


def starter_thread(ticker, text, topics):
    """z_f: 1 if the finding restates the company's case-appendix starter thread, else 0."""
    t = (text or "").lower()
    for prod, tops in STARTER.get(ticker.upper(), []):
        if prod and not re.search(prod, t):
            continue
        if tops is None or set(topics) & tops:
            return 1.0
    return 0.0


def headline(ticker, topics):
    """(h_f, doc_id): 0.9 if any topic pattern matches page 1 of the latest earnings release, else 0."""
    doc_id, text = data.latest_release_page1(ticker)
    if not doc_id:
        return 0.0, None, ["h_f: no earnings release in the index (h = 0, flagged)"]
    pats = [TOPIC_WORDS[t] for t in topics if t in TOPIC_WORDS]
    hit = any(re.search(p, text, re.I) for p in pats)
    return (W.H_VALUE if hit else 0.0), doc_id, []


def _qa_share(ticker, pattern):
    q = data.qa_turns()
    q = q[q.ticker == ticker.upper()]
    quarters = sorted(q.quarter.dropna().unique())[-W.ATTENTION_QUARTERS:]
    if not quarters:
        return None, 0
    q = q[q.quarter.isin(quarters)]
    pattern = re.sub(r"\((?!\?)", "(?:", pattern)   # non-capturing groups for pandas
    asked = q[q.text.astype(str).str.contains(pattern, case=False, regex=True)].quarter.nunique()
    return asked / len(quarters), len(quarters)


def attention(ticker, topics, product=None):
    """(a_f, source note, flags). Product findings: share of quarters an analyst named the product. Topic findings:
    the most-asked of the finding's topics (scorecard first, qa_turns regex otherwise)."""
    flags = []
    if product:
        a, n = _qa_share(ticker, re.escape(product))
        if a is not None:
            return a, f"qa_turns: analysts named {product} in {round(a * n)} of {n} quarters", flags
    sc = data.scorecard()
    best, note = None, ""
    for t in topics:
        st = SCORECARD_TOPIC.get(t)
        if st:
            row = sc[(sc.ticker == ticker.upper()) & (sc.topic == st)]
            if len(row):
                v = float(row.iloc[0].share_of_quarters_asked)
                if best is None or v > best:
                    best, note = v, f"priced_in_scorecard {ticker} {st}: {v:.1f}"
                continue
        if t in TOPIC_WORDS:
            v, n = _qa_share(ticker, TOPIC_WORDS[t])
            if v is not None and (best is None or v > best):
                best, note = v, f"qa_turns regex '{TOPIC_WORDS[t]}': {round(v * n)} of {n} quarters"
    if best is None:
        flags.append("a_f imputed: no measurable topic (peer median of scorecard topics)")
        best = float(sc.share_of_quarters_asked.median())
        note = "imputed: scorecard median"
    return best, note, flags


def consensus_embedding(ticker, fiscal_year, disclosed, d_eps, adverse=True):
    """(c_f, flags). c = clip(dcons_dir / |dEPS|, 0, 1); dcons = change in the FY I/B/E/S mean EPS from the last
    statpers before to the first statpers after the disclosure, signed in the finding's direction."""
    if not d_eps or fiscal_year is None or disclosed is None:
        return W.C_UNTESTABLE, [f"c_f untestable (no dEPS, year or date): set to {W.C_UNTESTABLE}, uninformative (A12)"]
    _, _, c = data._ibes()
    rows = c[(c.oftic == ticker.upper()) & (c.fpedats.astype(str).str.startswith(str(fiscal_year)))
             & (c.measure == "EPS")].sort_values("statpers")
    d = disclosed.isoformat()
    before, after = rows[rows.statpers < d], rows[rows.statpers >= d]
    if before.empty or after.empty:
        return W.C_UNTESTABLE, [f"c_f untestable (FY consensus first appears after the disclosure): set to "
                                f"{W.C_UNTESTABLE}, uninformative, not 0 (review A12)"]
    b, a = before.iloc[-1], after.iloc[0]
    delta = float(a.meanest - b.meanest)
    dirn = -delta if adverse else delta
    flags = []
    acts, _, _ = data._ibes()
    ann = acts[(acts.oftic == ticker.upper()) & (acts.anndats > b.statpers) & (acts.anndats < a.statpers)]
    if len(ann):
        flags.append("c_f confounded (earnings announced between the two statpers)")
    return max(0.0, min(1.0, dirn / abs(d_eps))), flags


def decay(age_months, H=None):
    """2^(-age / H). H defaults to weights.H_MONTHS read at call time (so a sensitivity run can change it)."""
    H = W.H_MONTHS if H is None else H
    return 2 ** (-max(age_months, 0.0) / H)


def discussion(z, h, a, c, s):
    """D_f = (1 - z)(1 - h)(1 - a)(1 - c)(1 - s): the non-decay part of O, where the Needle floor applies (R1)."""
    return (1 - z) * (1 - h) * (1 - a) * (1 - c) * (1 - s)


def months_between(a, b):
    return (b - a).days / 30.4375


def obscurity(z, h, a, c, s, age_months, H=None):
    """O_f = D_f . decay (section 4.4)."""
    return discussion(z, h, a, c, s) * decay(age_months, H)


def to_date(s):
    if isinstance(s, date):
        return s
    try:
        return date.fromisoformat(str(s)[:10])
    except ValueError:
        return None


SHORTLIST = ("MRK", "BMY", "PFE", "LLY", "NVO", "ABBV", "JNJ", "AZN", "AMGN", "GILD")


def headline_imputed(topics):
    """h_f when the company has no earnings release in the index (NVO, AZN today): the shortlist median of h for the
    same topics among companies that do have one, so absence of a source is not read as obscurity."""
    vals = []
    for t in SHORTLIST:
        doc_id, text = data.latest_release_page1(t)
        if not doc_id:
            continue
        pats = [TOPIC_WORDS[x] for x in topics if x in TOPIC_WORDS]
        vals.append(W.H_VALUE if any(re.search(p, text, re.I) for p in pats) else 0.0)
    if not vals:
        return 0.0
    vals.sort()
    n = len(vals)
    return vals[n // 2] if n % 2 else (vals[n // 2 - 1] + vals[n // 2]) / 2
