"""Supply-chain and outside-world detector: what drug makers report vs data management does not control.

  distributor_commentary  McKesson / Cencora / Cardinal filing paragraphs that name the maker, a key brand or the GLP-1
                          class next to inventory / stocking / price / buy-in language (verified page evidence)
  demand_divergence       maker revenue YoY outruns independent demand proxies (FAERS volume) or NADAC prices fall
  faers_serious_rising    FAERS serious-report count up >= 50% YoY (latest 4 quarters vs prior 4) and above rivals
  trial_terminated        Phase 2/3 trials stopped in the last 18 months, with the registry's WhyStopped text

Reads data/corpus (pages, XBRL) and data/outside/*.json written by `python -m agent.needle.outside`; no network here.
Outside-data signals carry meta["data"]["source_url"]; distributor signals carry verified page Evidence.
FAERS is unverified spontaneous reporting (report counts are not incidence, and reporting follows news and litigation);
NADAC is a retail-pharmacy acquisition-cost survey. Both are proxies and are labelled as such in each detail line.
"""

import re
import statistics
from datetime import date, timedelta

from agent.needle import outside, pages, xbrl
from agent.needle.detect import CASE_SETS, cli
from agent.needle.schema import Evidence, Signal

DISTRIBUTORS = ("MCK", "COR", "CAH")
ALIASES = {"MRK": ["Merck"], "BMY": ["Bristol-Myers", "Bristol Myers"], "PFE": ["Pfizer"], "LLY": ["Eli Lilly", "Lilly"],
           "NVO": ["Novo Nordisk", "Novo"], "ABBV": ["AbbVie"], "JNJ": ["Janssen", "Johnson & Johnson"],
           "AZN": ["AstraZeneca"], "AMGN": ["Amgen"], "GILD": ["Gilead"]}
GLP1_BRANDS = {"zepbound", "wegovy", "mounjaro", "ozempic", "trulicity", "foundayo"}
TOPIC = re.compile(r"inventor|stocking|buy-in|buy in|price increase|pricing|destock|specialty|glp-1|channel|"
                   r"purchas|supply|brand manufacturer", re.I)
GLP1_TOPIC = re.compile(r"inventor|stocking|buy-in|price increase|destock|specialty|volume|demand|growth|supply", re.I)
BIZ_STOP = re.compile(r"business|strateg|portfolio|priorit|commercial|sponsor decision|decision by|futility|efficacy|"
                      r"enroll|funding|company decision", re.I)
MAX_ECHO = 5
RANK = {"annual_report": 0, "quarterly_report": 1, "earnings_release": 2}


def _words(s):
    return s.split()


def _window(para, term_re, lo=25, hi=45):
    """A contiguous 25 to 45 word slice of para around the first term match, cut at sentence edges when possible."""
    m = term_re.search(para)
    if not m:
        return None
    sents = re.split(r"(?<=[.;!?])\s+", para)
    # sentence-aligned windows first
    best = None
    for i in range(len(sents)):
        for j in range(i, len(sents)):
            chunk = " ".join(sents[i:j + 1])
            n = len(chunk.split())
            if n > hi:
                break
            if lo <= n <= hi and term_re.search(chunk) and (best is None or abs(n - 35) < abs(len(best.split()) - 35)):
                best = chunk
    if best:
        return best
    w = _words(para)
    pos = len(_words(para[:m.start()]))
    start = max(0, min(pos - 15, len(w) - lo))
    out = " ".join(w[start:start + 38])
    return out if len(out.split()) >= lo and term_re.search(out) else None


def _terms(ticker):
    names = list(ALIASES.get(ticker, []))
    brands = list(CASE_SETS.get(ticker, {}))
    return names, brands


def distributor_echo(ticker):
    names, brands = _terms(ticker)
    name_re = re.compile(r"\b(" + "|".join(re.escape(n) for n in names + [b.title() for b in brands] + brands) + r")\b",
                         re.I) if names or brands else None
    glp1 = bool(GLP1_BRANDS & set(brands))
    glp_re = re.compile(r"GLP-1", re.I)
    cands, seen = [], set()
    for dist in DISTRIBUTORS:
        ds = pages.docs(dist)
        for doc_id, doc in ds.items():
            rank = RANK.get(doc["row"]["doc_type"], 3)
            for pg, (_, text) in doc["pages"].items():
                for para in pages.paragraphs(text):
                    by_name = name_re.search(para) if name_re else None
                    by_class = glp1 and glp_re.search(para) and GLP1_TOPIC.search(para)
                    if not ((by_name and TOPIC.search(para)) or by_class):
                        continue
                    # a bare "Novo"/"Lilly" hit inside unrelated words is excluded by \b; require the topic words nearby
                    term_re = name_re if by_name else glp_re
                    quote = _window(para, term_re)
                    if not quote:
                        continue
                    key = quote.lower()[:80]
                    if key in seen:
                        continue
                    seen.add(key)
                    cands.append((rank, -int(str(doc["row"].get("filed") or doc["row"].get("period") or "0")[:4] or 0),
                                  dist, doc_id, pg, quote, "named" if by_name else "glp1_class", ds))
    cands.sort(key=lambda c: (c[6] != "named", c[0], c[1]))
    sigs, per_dist = [], {}
    for rank, _, dist, doc_id, pg, quote, how, ds in cands:
        if per_dist.get(dist, 0) >= 2 or len(sigs) >= MAX_ECHO:
            continue
        ev = Evidence(doc_id=doc_id, page=pg, quote=quote)
        if pages.check(ev, ds)[0] != "verified":
            continue
        per_dist[dist] = per_dist.get(dist, 0) + 1
        what = "names the maker or a key brand" if how == "named" else "discusses the GLP-1 class"
        sigs.append(Signal(ticker=ticker, detector="supply", kind="distributor_commentary", period=str(doc["row"]["period"]) if False else ds[doc_id]["row"]["period"],
                           detail=f"{dist} filing paragraph that {what} next to inventory, pricing or channel language: context for "
                                  f"how {ticker}'s product reaches pharmacies.",
                           evidence=[ev], meta={"distributor": dist, "match": how}))
    return sigs


# ---- outside-data helpers ---------------------------------------------------------------------------------------
def _quarters(slug):
    d = outside.load("faers", slug)
    if not d or d.get("error") or not d["rows"]:
        return None, d
    return d["rows"], d


def _sum(rows, key, a, b):
    return sum(r[key] for r in rows[a:b])


def _faers_change(rows, key="reports"):
    """(latest-quarter YoY, trailing-4Q vs prior-4Q change); None when the base is too thin to mean anything."""
    if len(rows) < 8:
        return None, None
    last = rows[-1][key]
    base_q = rows[-5][key] if len(rows) >= 5 else 0
    q = last / base_q - 1 if base_q >= 30 else None
    cur, prior = _sum(rows, key, -4, None), _sum(rows, key, -8, -4)
    t4 = cur / prior - 1 if prior >= 100 else None
    return q, t4


def _latest_rev_yoy(ticker):
    try:
        p = xbrl.panel(ticker)
        s = xbrl.yoy(p, "revenue").dropna()
        if s.empty:
            return None, None
        return s.index[-1], float(s.iloc[-1])
    except Exception:  # noqa: BLE001
        return None, None


def _nadac_change(slug):
    """Median per-NDC change between the latest price and the price about a year before; (median, n_ndc, data)."""
    d = outside.load("nadac", slug)
    if not d or d.get("error") or not d["rows"]:
        return None
    by = {}
    for r in d["rows"]:
        by.setdefault(r["ndc"], []).append((r["effective_date"], float(r["nadac_per_unit"])))
    newest = max(x[0] for v in by.values() for x in v)
    target = (date.fromisoformat(newest) - timedelta(days=365)).isoformat()
    ch = []
    for ndc, v in by.items():
        v.sort()
        if v[-1][0] < (date.fromisoformat(newest) - timedelta(days=120)).isoformat():
            continue
        old = [x for x in v if x[0] <= target]
        if old and old[-1][1] > 0:
            ch.append((ndc, old[-1][0], old[-1][1], v[-1][0], v[-1][1], v[-1][1] / old[-1][1] - 1))
    if not ch:
        return None
    return {"median_change": statistics.median(c[5] for c in ch), "n_ndc": len(ch), "as_of": newest,
            "ndcs": [{"ndc": c[0], "old_date": c[1], "old": c[2], "new_date": c[3], "new": c[4]} for c in ch[:8]],
            "source_url": d["source_url"]}


def sell_in_vs_demand(ticker):
    sigs = []
    q, rev = _latest_rev_yoy(ticker)
    if rev is None:
        return sigs
    for prod in CASE_SETS.get(ticker, {}):
        rows, d = _quarters(prod)
        if rows:
            fq, ft = _faers_change(rows)
            if fq is not None and rev - fq >= 0.15:
                sigs.append(Signal(
                    ticker=ticker, detector="supply", kind="demand_divergence", period=q, value=round(rev - fq, 4),
                    detail=(f"{ticker} total revenue grew {rev:+.1%} YoY in {q} while FAERS reports naming {prod.upper()} moved "
                            f"{fq:+.1%} ({rows[-1]['quarter']} vs a year earlier): a {100 * (rev - fq):.0f}-point gap. FAERS report volume is only a "
                            f"loose proxy for patient use (reports follow news, litigation and label changes), and revenue here is company-wide, "
                            f"so treat this as a prompt to look, not a finding."),
                    meta={"data": {"source_url": d["source_url"], "proxy": "FAERS report count", "product": prod,
                                   "revenue_yoy": rev, "faers_quarter_yoy": fq, "faers_trailing4q_change": ft,
                                   "faers_quarters": rows, "retrieved_at": d["retrieved_at"]}}))
        nd = _nadac_change(prod)
        if nd and nd["median_change"] <= -0.10 and rev > 0:
            sigs.append(Signal(
                ticker=ticker, detector="supply", kind="demand_divergence", period=q, value=round(nd["median_change"], 4),
                detail=(f"NADAC pharmacy acquisition cost for {prod.upper()} fell a median {nd['median_change']:+.1%} over the year to "
                        f"{nd['as_of']} ({nd['n_ndc']} NDCs) while {ticker} reported revenue {rev:+.1%} YoY in {q}. NADAC is a survey of retail "
                        f"pharmacy purchase prices, a proxy for net price pressure, not the maker's realized price."),
                meta={"data": {**nd, "proxy": "NADAC", "product": prod, "revenue_yoy": rev}}))
    return sigs


def safety_signal(ticker):
    sigs = []
    for prod, rivals in CASE_SETS.get(ticker, {}).items():
        rows, d = _quarters(prod)
        if not rows:
            continue
        _, ft = _faers_change(rows, "serious")
        if ft is None or ft < 0.5:
            continue
        rv = {}
        for r in rivals:
            rr, _d = _quarters(r)
            if rr:
                rv[r] = _faers_change(rr, "serious")[1]
        known = {k: v for k, v in rv.items() if v is not None}
        if known and ft <= statistics.median(known.values()):
            continue
        cur, prior = _sum(rows, "serious", -4, None), _sum(rows, "serious", -8, -4)
        sigs.append(Signal(
            ticker=ticker, detector="supply", kind="faers_serious_rising", period=rows[-1]["quarter"], value=round(ft, 4),
            peer_median=round(statistics.median(known.values()), 4) if known else None,
            detail=(f"FAERS serious reports naming {prod.upper()} rose {ft:+.0%} (last 4 quarters {cur} vs prior 4 {prior}); rival change "
                    f"{', '.join(f'{k} {v:+.0%}' for k, v in known.items()) or 'n/a'}. FAERS is unverified spontaneous reporting and "
                    f"report counts are not incidence; reporting surges follow publicity, litigation and new indications."),
            meta={"data": {"source_url": d["source_url"], "product": prod, "serious_last4": cur, "serious_prior4": prior,
                           "rival_changes": rv, "faers_quarters": rows, "retrieved_at": d["retrieved_at"]}}))
    return sigs


def trial_stops(ticker):
    d = outside.load("trials", ticker)
    if not d or d.get("error"):
        return []
    sigs = []
    for r in d["rows"]:
        if not r.get("why_stopped"):
            continue
        sigs.append(Signal(
            ticker=ticker, detector="supply", kind="trial_terminated", period=r["last_update"] or "",
            detail=(f"{r['status'].title()} Phase {'/'.join(p[-1] for p in r['phases'])} trial {r['nct_id']} ({r['title']}); registry reason: "
                    f"{r['why_stopped']} Registry text is sponsor-written; it may understate or reframe the real reason."),
            meta={"nct_id": r["nct_id"], "url": r["url"], "business_reason": bool(BIZ_STOP.search(r["why_stopped"])),
                  "data": {"source_url": r["url"], "registry_query": d["source_url"], "retrieved_at": d["retrieved_at"], **r}}))
    return sigs


def run(ticker):
    t = ticker.upper()
    return distributor_echo(t) + sell_in_vs_demand(t) + safety_signal(t) + trial_stops(t)


if __name__ == "__main__":
    cli("supply", run)
