"""DECIDE: value a candidate CEO move on one 24-month cash scale (docs/quant_model.md Section 5).

    EV_m = sum_s p_s [ sum_tau (P_alive CF_in - P_reach CF_out) / (1 + r_mo)^tau  +  TV_24 / (1 + r_mo)^24 ]

evaluate_move(template, params, findings) -> MoveResult with the five numbers (EV, downside cash at risk, payback month,
scenario EV spread, MCDA score), per-scenario monthly cash tables and a citation on every input taken from a finding,
a company filing or a benchmark.  rank_moves() sorts by EV; select_move() applies the Section 5.4 selection rule.

Benchmarks whose source is a URL get a Citation with claim_type "number", verification status "unverified" and
confidence_note "external benchmark". They are not in the citation index, so they never support a number: the
numeric gate (agent.needle.cite.gate) sees them as labelled assumptions ("external benchmark: <name>, <url>",
benchmark_label) and the renderer prints them as [assumption], never as a numbered footnote marker.

Company citations (from the moves file or a finding) are re-verified here against the citation index
(agent.needle.cite.verify.verify); a verification status supplied in the moves JSON or a findings file is discarded
(review C2, decide.py citation_from_dict).
"""

from dataclasses import asdict, dataclass, field, is_dataclass

from agent.needle.cite.locator import Citation, Claim, Verification
from agent.needle.quant import moves as mv
from agent.needle.quant.moves import (COMMERCIAL_MULT_CAP, FAVORABLE_LEVEL_KINDS, MCDA_WEIGHTS, MULT_SCENARIO, P_SCENARIO,
                                      PAYBACK_SEARCH, REGISTRY, SCENARIOS, WACC, WINDOW, get_template, r_monthly)

EXTERNAL = "external benchmark"


# --------------------------------------------------------------------------------------------------------------
# Findings and citations
# --------------------------------------------------------------------------------------------------------------

def normalize_findings(findings):
    """Accept dicts (old findings.jsonl or v2 rows) or schema.Finding objects; drop duplicate ids."""
    out, seen = [], set()
    for f in findings or []:
        d = asdict(f) if is_dataclass(f) and not isinstance(f, type) else dict(f)
        key = d.get("finding_id") or d.get("id")
        if key in seen:
            continue
        seen.add(key)
        out.append(d)
    return out


def finding_id(f):
    return f.get("finding_id") or f.get("id") or ""


def finding_kind(f):
    return f.get("signal_kind") or f.get("kind") or ""


def finding_score(f):
    """FIND's S (v2: key S) or the old engine's score."""
    for k in ("S", "s_score", "score"):
        if f.get(k) is not None:
            return float(f[k])
    return 0.0


_IDX = {}


def _index():
    if "i" not in _IDX:
        from agent.needle.quant import data
        _IDX["i"] = data.index()
    return _IDX["i"]


def reverify(c, index=None):
    """Never trust a supplied status: page citations are re-run through verify(); XBRL citations re-read their frame;
    derived citations keep status 'derived' (they support nothing by themselves); anything else (a table row the
    DECIDE path cannot re-read) becomes unverified."""
    from dataclasses import replace
    if c.page is not None and not c.canonical_id.startswith(("xbrl:", "derived", "benchmark:", "tables/")):
        try:
            from agent.needle.cite.verify import verify
            return verify(replace(c, verification=Verification(), cite_id=""), index or _index())
        except Exception as e:                      # fail closed
            return replace(c, verification=Verification("unverified", 0.0, "", f"verify failed: {e}"))
    if c.canonical_id.startswith("xbrl:") and c.value:
        from agent.needle.quant import data
        concept, _, frame = (c.location or "").rpartition(" ")
        try:
            val = float(str(c.value).replace(",", ""))
            fresh = data.xbrl_citation(c.canonical_id[5:], concept, frame, val, c.unit)
            return replace(c, verification=fresh.verification, confidence_note=fresh.confidence_note)
        except Exception as e:
            return replace(c, verification=Verification("unverified", 0.0, "", f"XBRL re-read failed: {e}"))
    if c.canonical_id == "derived":
        return replace(c, verification=Verification("derived", 0.0, "", c.verification.detail if c.verification else ""))
    return replace(c, verification=Verification("unverified", 0.0, "", "supplied status discarded: DECIDE cannot re-read "
                                                                         "this table row"))


def finding_citations(f, index=None):
    """Citations for a finding, each re-verified (reverify): v2/v3 rows carry `citations`; old rows carry `evidence`
    (doc_id, page, quote)."""
    out = []
    for c in f.get("citations") or []:
        out.append(reverify(c if isinstance(c, Citation) else Citation.from_dict(c), index))
    if out:
        return out
    for ev in f.get("evidence") or []:
        if not ev.get("doc_id"):
            continue
        out.append(Citation(
            canonical_id=ev["doc_id"], page=ev.get("page"), quote=ev.get("quote", ""), claim_type="quote",
            ticker=f.get("ticker", ""), doc_title=ev.get("citation", ""), speaker=ev.get("speaker", ""),
            verification=Verification("unverified", 0.0, "", f"evidence of finding {finding_id(f)}"),
            confidence_note=f"taken from finding {finding_id(f)}"))
    return [reverify(c, index) for c in out]


def _short_title(b):
    head = b.source.split(":")[0].split(";")[0].strip()
    words = head.split()
    return f"{b.name}: " + " ".join(words[:8])


def benchmark_citation(name_or_bench):
    b = REGISTRY[name_or_bench] if isinstance(name_or_bench, str) else name_or_bench
    return Citation(
        canonical_id=f"benchmark:{b.name}", page=None, quote=b.source, claim_type="number",
        value=str(b.value) if not isinstance(b.value, (dict, tuple)) else "table", unit=b.unit, doc_type="benchmark",
        doc_title=_short_title(b), location="file page n/a (external benchmark)", source_url=b.url, deep_link=b.url,
        verification=Verification("unverified", 0.0, "", EXTERNAL + ("" if b.url else " (no URL; spec Section 11.2)")),
        confidence_note=EXTERNAL)


def benchmark_label(name_or_bench):
    """Assumption label for a benchmark number: external, not in the citation index, unverified."""
    b = REGISTRY[name_or_bench] if isinstance(name_or_bench, str) else name_or_bench
    return f"external benchmark: {b.source}, {b.url or 'no URL'} (unverified)" if b.kind != "inference" else \
        f"inference: {b.source}" + (f", {b.url}" if b.url else "") + " (unverified)"


def spec_citation(spec):
    """Citation for a ParamSpec default that carries a source URL or a registered benchmark."""
    if spec.bench and spec.bench in REGISTRY:
        return benchmark_citation(spec.bench)
    if spec.url:
        b = mv.Benchmark(spec.name, spec.default, spec.unit, spec.source, spec.url, spec.kind)
        return benchmark_citation(b)
    return None


def citation_from_dict(d, value=None, unit="", index=None):
    """A company citation from the moves file, verified against the citation index. Any caller-supplied
    `verification` (and cite_id) is discarded, never trusted (review C2: a forged "exact" must not print)."""
    d = dict(d)
    d.pop("verification", None)
    d.pop("cite_id", None)
    d.setdefault("claim_type", "number")
    if value is not None:
        d.setdefault("value", f"{value:,}" if isinstance(value, (int, float)) else str(value))
    d.setdefault("unit", unit)
    d = {k: v for k, v in d.items() if k in Citation.__dataclass_fields__}
    return reverify(Citation(**d), index)


@dataclass
class DecideInput:
    name: str
    value: object
    unit: str = ""
    kind: str = "benchmark"      # finding | benchmark | company | inference | assumption
    finding_id: str | None = None
    citation_ids: list = field(default_factory=list)
    note: str = ""
    derived: dict = field(default_factory=dict)     # gate derived entries when the value is computed from a table row


def _finding_value(f, fld):
    """Pull a $M number (or month) out of a finding's impact for a FeedRule; None when the finding has none."""
    imp = f.get("impact") or {}
    if isinstance(imp.get("d_rev"), dict):
        # FIND v2 row: d_rev comes from agent.needle.quant.impact (the one IRA / MFN / LOE implementation, review
        # S3). FIND signs an adverse revenue change positive; the feeds use negative = loss for "base".
        v = imp["d_rev"].get("base")
        if v is None or (not imp.get("quantified", True) and not v):
            return None
        sign = 1.0 if imp.get("adverse", True) else -1.0
        if fld == "month":
            return None
        return float(v) * sign * (1.0 if fld == "dollars" else -1.0)
    if fld == "dollars":
        v = imp.get("dollars")
        if v is None:
            v = imp.get("delta_rev") or imp.get("dRev")
        if isinstance(v, dict):
            v = v.get("base")
        if v is None:
            return None
        v = float(v)
        return v / 1e6 if abs(v) > 1e6 else v
    if fld == "month":
        v = imp.get("month")
        return None if v is None else float(v)
    v = imp.get("base")
    if isinstance(v, dict):
        v = v.get("delta_rev") or v.get("revenue") or v.get("dRev")
    if v is None:
        v = imp.get("delta_rev")
    if v is None:
        return None
    v = float(v)
    return v / 1e6 if abs(v) > 1e6 else v


# --------------------------------------------------------------------------------------------------------------
# Result structures
# --------------------------------------------------------------------------------------------------------------

@dataclass
class MoveResult:
    name: str
    code: str
    template_name: str
    params: dict
    ev: float
    ev_by_scenario: dict
    in_window_pv: dict
    tv_pv: dict
    car: float
    payback_month: int | None
    spread: float
    mcda: float
    mcda_parts: dict
    tables: dict                     # scenario -> list of monthly rows
    expected_cf: dict                # scenario -> list of undiscounted expected net cash flow per month
    budget: dict                     # line name -> undiscounted 24-month outflow, plus total
    inputs: list
    claims: list
    citations: list
    flags: list
    finding_ids: list
    addressed: list
    p_alive_end: float
    horizon: int
    notes: list
    kill_signals: tuple = ()
    abandon_value: float = 0.0
    wacc: float = WACC
    p_scenario: dict = field(default_factory=lambda: dict(P_SCENARIO))
    rank: int = 0
    status: str = ""
    binding_reason: str = ""
    why: str = ""
    car_parts: dict = field(default_factory=dict)    # {"out": [...], "in": [...]} by month (cash_at_risk_parts)

    def five(self):
        return {"ev": self.ev, "car": self.car, "payback_month": self.payback_month, "spread": self.spread, "mcda": self.mcda}

    def to_dict(self):
        d = {k: v for k, v in self.__dict__.items() if k not in ("claims", "citations")}
        d["claims"] = [c.to_dict() for c in self.claims]
        d["citations"] = [c.to_dict() for c in self.citations]
        d["five"] = self.five()
        return d


# --------------------------------------------------------------------------------------------------------------
# Core arithmetic
# --------------------------------------------------------------------------------------------------------------

def scenario_tables(plan, r_mo):
    """Per-scenario monthly rows and PV pieces for a CashPlan."""
    tables, pv, inwin, tv, exp_cf = {}, {}, {}, {}, {}
    for s in SCENARIOS:
        mult = MULT_SCENARIO[s]
        rows, flows = [], []
        a = b = 0.0
        for m in range(1, plan.horizon + 1):
            i = m - 1
            cin = sum(l.amount[i] * l.prob[i] * (mult if l.scaled else 1.0) for l in plan.lines if l.kind == "in")
            cout = sum(l.amount[i] * l.prob[i] for l in plan.lines if l.kind == "out")
            net = cin - cout
            df = (1.0 + r_mo) ** (-m)
            rows.append({"month": m, "cf_in": cin, "cf_out": cout, "net": net, "df": df, "pv": net * df})
            flows.append(net)
            if m <= WINDOW:
                a += net * df
            else:
                b += net * df
        tables[s], exp_cf[s] = rows, flows
        inwin[s], tv[s], pv[s] = a, b, a + b
    return tables, exp_cf, inwin, tv, pv


def cash_at_risk_parts(plan):
    """(outflow by month, inflow by month) that cash_at_risk nets: months 1..min(24, first readout)."""
    T = min(WINDOW, plan.first_readout or WINDOW)
    mult = MULT_SCENARIO["bear"]
    n = min(T, plan.horizon)
    out, inn = [0.0] * n, [0.0] * n
    for l in plan.lines:
        for i in range(n):
            if l.kind == "out" and not l.avoidable:
                out[i] += l.amount[i] * l.prob[i]
            elif l.kind == "in":
                inn[i] += l.amount[i] * (mult if l.scaled else 1.0)   # pre-failure, so P_alive = 1
    return out, inn


def cash_at_risk(plan):
    """Spec 5.4: bear scenario, technical failure at the first readout: undiscounted outflow through min(24, readout),
    net of inflows received before then and of avoidable payments."""
    out, inn = cash_at_risk_parts(plan)
    return max(0.0, sum(out) - sum(inn))


def payback_month(exp_by_s, p_s, r_mo, horizon):
    cum = 0.0
    for m in range(1, min(horizon, PAYBACK_SEARCH) + 1):
        x = sum(p_s[s] * exp_by_s[s][m - 1] for s in SCENARIOS)
        cum += x * (1.0 + r_mo) ** (-m)
        if cum >= 0.0:
            return m
    return None


def finding_weight(f):
    """Strategic-fit weight of a finding: M x E (materiality and evidence), not S (review A24). S also holds
    obscurity and the prior, so a well-known material problem (O = 0) would get no fit. FIND v2 rows carry
    vector M and E; old-shape rows fall back to their score."""
    v = f.get("vector") or {}
    if v.get("M") is not None and v.get("E") is not None:
        return float(v["M"]) * float(v["E"])
    return finding_score(f)


def mcda_score(template, plan, findings, addressed_ids, capability, stakeholders, p_s):
    scored = [f for f in findings if finding_kind(f) not in FAVORABLE_LEVEL_KINDS]
    top5 = sum(sorted((finding_weight(f) for f in scored), reverse=True)[:5])
    num = sum(finding_weight(f) for f in scored if finding_id(f) in addressed_ids)
    fit = min(1.0, num / top5) if top5 > 0 else 0.0
    cap = _share(capability, template.required_assets)
    stk = _share(stakeholders, template.deciders)
    mult_w = sum(p_s[s] * MULT_SCENARIO[s] for s in SCENARIOS)
    exe = max(0.0, min(1.0, plan.p_alive_end() * mult_w / COMMERCIAL_MULT_CAP))
    parts = {"strategic_fit": fit, "capability": cap, "execution_risk": exe, "stakeholder_evidence": stk}
    return sum(MCDA_WEIGHTS[k] * v for k, v in parts.items()), parts


def _share(spec, universe):
    """Share of the universe documented. spec: dict name->bool, a list of names held, or None."""
    if not spec:
        return 0.0
    if isinstance(spec, dict):
        vals = list(spec.values())
        return sum(1 for v in vals if (v if isinstance(v, bool) else v.get("held", False))) / len(vals)
    held = set(spec)
    return len(held & set(universe)) / len(universe) if universe else 0.0


# --------------------------------------------------------------------------------------------------------------
# evaluate_move
# --------------------------------------------------------------------------------------------------------------

def table_value(code, name, spec, vals, ctx, bench=None):
    """The verified-table value for one template parameter (agent.needle.quant.verified_tables), or None, in which
    case the research-note constant stays as the labelled fallback."""
    from agent.needle.quant import verified_tables as V
    ctx = ctx or {}
    b = bench or spec.bench
    stage = ctx.get("stage") or vals.get("stage") or "ph3"
    ta = ctx.get("ta") or vals.get("ta")
    try:
        if b in V.MOORE_ROWS:
            return V.moore(b)
        if b == "royalty_late":
            return V.royalty(stage)
        if b == "royalty_early":
            return V.royalty("preclinical")
        if b == "upfront_share":
            return V.licensing_upfront_share(stage)
        if code == "M2" and name == "total_deal_value":
            return V.licensing_total(stage)
        if code == "M2" and name == "p_ph3":
            return V.sertkaya_pos(ta, "Phase 3 to FDA review")
        if code == "M2" and name == "p_nda":
            return V.sertkaya_pos(ta, "FDA review to approval")
        if code == "M1" and name == "equity_value":
            return V.target_ev(ctx["target"]) if ctx.get("target") else V.acquisition_value(stage)
        if code == "M3" and name in ("trial_months", "readout_month", "approval_month") and ctx.get("timing") == "table":
            return V.indication_timing(ta, name)
        if code in ("M4", "M5") and name == "loe_month" and ctx.get("product") and ctx.get("ticker"):
            return V.loe_month(ctx["ticker"], ctx["product"])
    except Exception:
        return None
    return None


def _table_input(name, spec, tv, cites, inputs, note=""):
    cites[name] = list(tv.citations)
    inputs.append(DecideInput(name, tv.value, spec.unit, "table", citation_ids=[c.cite_id for c in tv.citations],
                              note=tv.label + (f"; {note}" if note else ""), derived=dict(tv.derived)))


def _bind_params(template, params, findings, finding_ids, context=None):
    """Merge defaults, user values and Part 1 feeds. Returns (values, inputs, citations_by_param, flags, addressed).
    A parameter with a verified-table row (table_value) takes the table value and its facts-row citation; the
    research-note constant is the labelled fallback when no row exists."""
    vals = template.defaults()
    inputs, cites, flags, addressed = [], {}, [], set(finding_ids or [])
    by_id = {finding_id(f): f for f in findings}
    user = {}
    for k, v in (params or {}).items():
        if isinstance(v, dict) and "value" in v:
            user[k] = v
        else:
            user[k] = {"value": v}
    # 1. automatic feeds from Part 1 (only where the user gave no value)
    for rule in template.feeds:
        cands = [f for f in findings if any(finding_kind(f).startswith(p) for p in rule.kinds)]
        explicit = [f for f in cands if finding_id(f) in addressed]
        for f in sorted(explicit or cands, key=finding_score, reverse=True):
            v = _finding_value(f, rule.field)
            if rule.param in template.params and rule.param not in user and v is not None:
                user[rule.param] = {"value": rule.sign * v, "kind": "finding", "finding_id": finding_id(f), "note": rule.note}
                break
        # a matched finding addresses the move even when it carries no dollar path (strategic fit)
        if cands and not explicit and rule.param not in user:
            addressed.add(finding_id(sorted(cands, key=finding_score, reverse=True)[0]))
    # 2. build inputs
    for name, spec in template.params.items():
        u = user.get(name)
        if u is None:
            tv = table_value(template.code, name, spec, vals, context)
            if tv is not None:
                vals[name] = tv.value
                _table_input(name, spec, tv, cites, inputs, f"replaces research-note default {spec.default}")
                continue
            v = spec.default
            c = spec_citation(spec)
            vals[name] = v
            if c is not None:
                cites[name] = [c]
                inputs.append(DecideInput(name, v, spec.unit, "benchmark" if spec.kind != "inference" else "inference",
                                          note=spec.source, citation_ids=[c.cite_id]))
            else:
                kind = "design" if spec.kind == "design" else "assumption"
                inputs.append(DecideInput(name, v, spec.unit, kind, note=spec.source))
                if kind != "design":
                    flags.append(f"unsourced default: {name} = {v} ({spec.source or 'no source'}); state it or replace it")
            continue
        v = u["value"]
        bench = u.get("benchmark")
        # a research-note benchmark the moves file names, or an uncited company number, is replaced by its verified
        # table row; a plain value the caller sets (no kind, no benchmark) is the caller's and is kept
        if not u.get("citation") and not u.get("finding_id") and (bench or u.get("kind") == "company"):
            tv = table_value(template.code, name, spec, vals, context, bench)
            rv = REGISTRY[bench].value if bench in REGISTRY else None
            if tv is not None and (bench is None or rv == v or not isinstance(rv, (int, float))):
                vals[name] = tv.value
                _table_input(name, spec, tv, cites, inputs, f"moves file gave {v}"
                             + (f" (research note {bench})" if bench else ""))
                if tv.value != v:
                    flags.append(f"{name}: verified table value {tv.value:g} replaces the moves-file value {v} "
                                 f"({tv.label})")
                continue
        vals[name] = v
        cl = []
        fid = u.get("finding_id")
        if fid and fid in by_id:
            cl = finding_citations(by_id[fid])
            addressed.add(fid)
        if u.get("citation"):
            cl = cl + [citation_from_dict(u["citation"], v, spec.unit)]
        if u.get("benchmark"):
            cl = cl + [benchmark_citation(u["benchmark"])]
        kind = u.get("kind") or ("finding" if fid else ("company" if u.get("citation") else ("benchmark" if u.get("benchmark") else "assumption")))
        if not cl and v == spec.default:
            c = spec_citation(spec)
            if c is not None:
                cl = [c]
                kind = "benchmark"
        if not cl and spec.kind != "design":
            flags.append(f"uncited input: {name} = {v} ({kind}); no finding or source attached")
        cites[name] = cl
        inputs.append(DecideInput(name, v, spec.unit, kind, finding_id=fid, citation_ids=[c.cite_id for c in cl],
                                  note=u.get("note", "")))
    return vals, inputs, cites, flags, addressed


def evaluate_move(template, params, findings, *, name=None, capability=None, stakeholders=None, finding_ids=None,
                  wacc=WACC, p_scenario=None, why="", abandon_value=None, context=None):
    """Value one candidate move. `template` is a MoveTemplate or a code/alias ("M3", "label_expansion")."""
    if isinstance(template, str):
        template = get_template(template)
    findings = normalize_findings(findings)
    p_s = dict(p_scenario or P_SCENARIO)
    assert abs(sum(p_s.values()) - 1.0) < 1e-9, "scenario weights must sum to 1"
    r_mo = r_monthly(wacc)

    vals, inputs, cites, flags, addressed = _bind_params(template, params, findings, finding_ids, context)
    plan = template.build(vals)
    if abandon_value is not None:
        plan.abandon_value = abandon_value

    tables, exp_cf, inwin, tv, pv = scenario_tables(plan, r_mo)
    ev = sum(p_s[s] * pv[s] for s in SCENARIOS)
    spread = pv["bull"] - pv["bear"]   # EV with p_bull = 1 minus EV with p_bear = 1
    car = cash_at_risk(plan)
    car_out, car_in = cash_at_risk_parts(plan)
    pb = payback_month(exp_cf, p_s, r_mo, plan.horizon)
    mcda, parts = mcda_score(template, plan, findings, addressed, capability, stakeholders, p_s)
    if not addressed:
        flags.append("strategic fit 0: the move addresses no Part 1 finding, so it cannot be recommended (spec 5.2)")
    if not capability:
        flags.append("capability score 0: no cited capability facts supplied")
    if not stakeholders:
        flags.append("stakeholder evidence score 0: no documented decider evidence supplied")

    budget = {}
    for l in plan.lines:
        if l.kind == "out":
            budget[l.name] = sum(l.amount[i] for i in range(min(WINDOW, plan.horizon)))
    budget["total 24-month committed outflow"] = sum(budget.values())

    claims, seen = [], {}
    for inp in inputs:
        cl = cites.get(inp.name) or []
        if cl:
            ok = [c for c in cl if c.verification.ok]
            claims.append(Claim(f"{inp.name} = {_fmt_val(inp.value)} {inp.unit} ({inp.kind})", ok,
                                derived=inp.derived or None, assumptions=input_assumptions(inp, cl)))
            for c in cl:
                seen[c.cite_id] = c
    glob = [("Discount rate", benchmark_citation("wacc")), ("Bear weight", benchmark_citation("p_bear")),
            ("Base weight", benchmark_citation("p_base")), ("Bull weight", benchmark_citation("p_bull")),
            ("Bear multiplier", benchmark_citation("mult_bear")), ("Bull multiplier", benchmark_citation("mult_bull"))]
    for label, c in glob:
        seen[c.cite_id] = c
    claims.append(Claim("scenario weights 0.50 / 0.11 / 0.39, multipliers 0.8 / 1.0 / 1.2, WACC 7.85%", [],
                        assumptions=global_assumptions()))

    return MoveResult(
        name=name or template.name, code=template.code, template_name=template.name, params=vals, ev=ev,
        ev_by_scenario=pv, in_window_pv=inwin, tv_pv=tv, car=car, payback_month=pb, spread=spread, mcda=mcda,
        mcda_parts=parts, tables=tables, expected_cf=exp_cf, budget=budget, inputs=inputs, claims=claims,
        citations=list(seen.values()), flags=flags, finding_ids=sorted(addressed), addressed=sorted(addressed),
        p_alive_end=plan.p_alive_end(), horizon=plan.horizon, notes=plan.notes, kill_signals=template.kill_signals,
        abandon_value=plan.abandon_value, wacc=wacc, p_scenario=p_s, why=why,
        car_parts={"out": car_out, "in": car_in})


def _fmt_val(v):
    """An input value as printed: floats from a model feed are rounded (109.34011000000001 -> 109.3), integers and
    cited values keep their printed form."""
    if isinstance(v, (dict, tuple, list)):
        return "table"
    if isinstance(v, float) and not v.is_integer():
        return f"{v:,.1f}" if abs(v) >= 100 else f"{v:.4g}"
    return v


def _vals(v):
    if isinstance(v, dict):
        return [x for y in v.values() for x in _vals(y)]
    if isinstance(v, (tuple, list)):
        return [x for y in v for x in _vals(y)]
    try:
        return [float(v)]
    except (TypeError, ValueError):
        return []


def input_assumptions(inp, cl=()):
    """Assumption labels for an input's value: an external benchmark, an inference, a team assumption, a design
    parameter, or a Part 1 finding's impact. A company input with a passing citation needs none (it verifies)."""
    if inp.kind in ("company", "table") and any(c.verification.ok for c in cl):
        return {}
    bench = [c for c in cl if c.canonical_id.startswith("benchmark:")]
    if bench:
        name = bench[0].canonical_id.split(":", 1)[1]
        label = ("research-note fallback (no verified table row): " + benchmark_label(name)) if name in REGISTRY else \
            f"external benchmark: {bench[0].quote}, {bench[0].source_url or 'no URL'} (unverified)"
    elif inp.kind == "finding":
        label = f"Part 1 finding {inp.finding_id}: impact d_rev base (see the finding's own numeric check)"
    elif inp.kind == "design":
        label = f"design parameter: {inp.note or inp.name}"
    elif inp.kind == "company":
        label = None                                  # a company number whose citation did not verify: unsupported
    else:
        label = f"{inp.kind}: {inp.note or 'team input, no source'}"
    if label is None:
        return {}
    out = {}
    for i, x in enumerate(_vals(inp.value)):
        out[f"{inp.name}#{i}"] = {"value": f"{x:.12g}", "label": label}
        if inp.unit in ("fraction", "probability") or "fraction" in str(inp.unit):
            out[f"{inp.name}#{i}%"] = {"value": f"{x * 100:.12g}", "label": label, "unit": "%"}
    return out


def global_assumptions():
    """Scenario weights, multipliers and WACC: external benchmarks, labelled."""
    out = {}
    for name in ("p_bear", "p_base", "p_bull", "mult_bear", "mult_bull", "wacc"):
        b = REGISTRY[name]
        out[name] = {"value": f"{float(b.value):.12g}", "label": benchmark_label(name)}
        if name == "wacc":
            out["wacc%"] = {"value": f"{float(b.value) * 100:.12g}", "label": benchmark_label(name), "unit": "%"}
    out["mult_base"] = {"value": "1", "label": "design: base scenario revenue multiplier 1.0 (no adjustment)"}
    return out


# --------------------------------------------------------------------------------------------------------------
# Ranking and the selection rule (spec 5.4)
# --------------------------------------------------------------------------------------------------------------

def rank_moves(results, cash=None):
    """Sort by EV, descending; marks `rank` and feasibility (CaR <= cash when cash is given)."""
    ranked = sorted(results, key=lambda r: r.ev, reverse=True)
    for i, r in enumerate(ranked, 1):
        r.rank = i
        r.status = "feasible" if (cash is None or r.car <= cash) else "infeasible"
    return ranked


@dataclass
class Selection:
    """`chosen` is None when no eligible move has a base-case EV above zero; `least_bad` then names the highest-EV
    eligible move. `top` is whichever of the two the report is built on. `rule` is the one-sentence selection rule."""
    chosen: MoveResult | None
    rejected: list
    notes: list
    least_bad: MoveResult | None = None
    rule: str = ""

    @property
    def top(self):
        return self.chosen if self.chosen is not None else self.least_bad


def select_move(results, cash=None):
    """(1) feasibility gate CaR <= cash, (2) argmax EV, (3) if the top two [EV_bear, EV_bull] intervals overlap prefer
    the higher MCDA, (4) a move whose EV is at or below zero is never chosen: when no eligible move has EV > 0 the
    result has chosen None and least_bad = the highest-EV eligible move. Returns the selection, the next two moves by
    the same rule (each with its binding reason) and the one-sentence rule applied."""
    ranked = rank_moves(results, cash)
    feas = [r for r in ranked if r.status == "feasible"]
    infeas = [r for r in ranked if r.status == "infeasible"]
    notes = []
    if not feas:
        raise ValueError("no feasible move: every candidate's cash at risk exceeds cash and equivalents")
    # spec 5.2: a move that addresses no Part 1 finding cannot be recommended; it is chosen only when no feasible
    # move addresses one (then the WARNING below says so)
    unfit = [r for r in feas if not r.addressed]
    order = [r for r in feas if r.addressed] or list(feas)
    if len(order) < len(feas):
        notes.append("moves that address no Part 1 finding are not eligible to be chosen (spec 5.2): "
                     + ", ".join(r.name for r in unfit))
    cleared = order[0].ev > 0      # order is EV-descending, so the best eligible EV decides whether any move clears
    tie = ""
    if cleared and len(order) > 1:
        a, b = order[0], order[1]
        lo_a, hi_a = a.ev_by_scenario["bear"], a.ev_by_scenario["bull"]
        lo_b, hi_b = b.ev_by_scenario["bear"], b.ev_by_scenario["bull"]
        if max(lo_a, lo_b) <= min(hi_a, hi_b) and b.mcda > a.mcda:
            if b.ev > 0:
                order[0], order[1] = b, a
                notes.append(f"EV intervals of {a.name} and {b.name} overlap; chose the higher MCDA ({b.mcda:.3f} vs {a.mcda:.3f})")
                tie = f"EV ranges overlap ({a.name} vs {b.name}); selected on MCDA score {b.mcda:.3f} vs {a.mcda:.3f}"
            else:
                notes.append(f"EV intervals of {a.name} and {b.name} overlap but {b.name} has EV at or below zero, "
                             "so the MCDA tie-break does not apply")
    top = order[0]
    top.status = "chosen" if cleared else "least_bad"
    # why a higher-EV move was not picked: the cash gate and the strategic-fit rule, stated before the EV/MCDA step
    excl = [f"Cash gate excluded {r.name}" for r in infeas if r.ev > top.ev]
    excl += [f"Strategic-fit rule excluded {r.name} (addresses no Part 1 finding)" for r in unfit
             if r not in order and r.ev > top.ev]
    if cleared:
        rule = "; ".join(excl + [tie or ("Selected on EV" if not excl else "selected on EV among the rest")])
    else:
        rule = "; ".join(excl + [f"No candidate has EV above zero, so none is chosen; {top.name} is the least-bad "
                                 "option on EV"])
    rule = rule[0].upper() + rule[1:]
    rest = order[1:] + [r for r in unfit if r not in order] + infeas
    rejected = rest[:2]
    for r in rest:
        r.status = "rejected" if r in rejected else r.status
        if r.status == "infeasible" or (cash is not None and r.car > cash):
            r.binding_reason = f"cash at risk {r.car:,.1f} exceeds cash and equivalents {cash:,.1f}"
        elif not r.addressed and top.addressed:
            r.binding_reason = "addresses no Part 1 finding, so it cannot be recommended (spec 5.2)"
        elif r.ev < top.ev and r.mcda > top.mcda and _overlap(r, top):
            r.binding_reason = f"lower EV ({r.ev:,.1f} vs {top.ev:,.1f}); intervals overlap and MCDA does not rescue it"
        elif r.ev < top.ev:
            r.binding_reason = f"lower EV ({r.ev:,.1f} vs {top.ev:,.1f})"
        else:
            r.binding_reason = f"lower MCDA under overlapping EV intervals ({r.mcda:.3f} vs {top.mcda:.3f})"
        if r.ev <= 0 and "EV at or below zero" not in r.binding_reason:
            r.binding_reason += "; EV at or below zero"
        if r.payback_month is None and "payback" not in r.binding_reason:
            r.binding_reason += "; payback beyond 120 months"
    if any(f.startswith("strategic fit 0") for f in top.flags):
        notes.append(f"WARNING: {top.name} addresses no Part 1 finding and cannot be recommended (spec 5.2)")
    if cleared:
        return Selection(top, rejected, notes, None, rule)
    return Selection(None, rejected, notes, top, rule)


def _overlap(a, b):
    return max(a.ev_by_scenario["bear"], b.ev_by_scenario["bear"]) <= min(a.ev_by_scenario["bull"], b.ev_by_scenario["bull"])
