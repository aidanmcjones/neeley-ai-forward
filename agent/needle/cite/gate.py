"""Per-number, fail-closed citation gate.

Hard rule: every number the model outputs carries a citation that resolves to the source page, or is shown as derived
from cited numbers, or is labelled as an assumption. Anything else is not emitted. verify.gate() checked only that a
claim had one verified citation (review C6: one verified quote cleared any number of invented numbers); this gate
checks each number.

    numeric_gate(text_blocks, claims, derived=None, assumptions=None) -> GateResult
    gate_record(record, text_fields, citation_field) -> (record_with_numeric_check, passed)
    gate_document(sections) -> summary

Numbers: agent.needle.cite.numbers.tokenize on every text block (sentence, impact math, peer comparison, table cell,
formula line). Years, dates, period labels, form names, page / section / item numbers, ids and footnote markers are
excluded by the rule documented there. Everything else is classified, first rule that holds wins:

  verified    the number (after scale and sign normalization, numbers.same_number) appears in the cited_text (the
              citation's quote), in its verified value+unit, or in the page text of a citation whose status is
              exact, substring, fuzzy (the ladder already required matching numerals) or number_match. Only
              citations that PASSED verification count; an unverified citation supports nothing.
  derived     the number matches a `derived` entry whose expression re-computes, from operands that are themselves
              supported (a passing citation that carries the operand value, an assumption, or another derived
              entry), to the printed number within DERIVED_REL_TOL (0.5% relative) or the printed precision of the
              number (half a unit of its last digit), whichever is larger.
  assumed     the number matches an `assumptions` entry with a non-empty label.
              In a block whose `where` names a formula ("formula", "math", "impact"), the bare constants 0, 1 and 100
              (no unit, no scale) are assumed with the label "arithmetic constant": "(1 - t)" and "x 100" are
              arithmetic, not facts.
  unsupported anything else, with a reason.

Fail closed: an exception while checking one number marks that number unsupported with reason "gate error: ...";
an exception before tokenizing a block marks the block unsupported. Nothing passes on an error.

Record shape (agreed with the quant and UI workers):
    numeric_check = {status: passed | failed | unchecked, checked, total, verified, derived, assumed,
                     unsupported: [{value, where, reason}]}
  status is "passed" only when unsupported is empty and at least one text block was checked; "unchecked" when there
  was no text to check (the caller must not show an unchecked record either); otherwise "failed".
  total = numbers found; checked = numbers whose check ran to completion (total minus gate errors);
  verified + derived + assumed + len(unsupported) == total.

Derived entry shape (keys are free labels; the number is matched by value):
    derived = {"gap": {"value": 8.0, "unit": "pts", "expr": "(a / b - 1) * 100 - (c / d - 1) * 100",
                       "operands": {"a": cit_a, "b": {"value": 8701, "citation": cit_b},
                                    "c": {"value": 0.65, "assumption": "Pfizer MFN base rate"},
                                    "d": {"derived": "rev_ttm"}}}}
  An operand given as a bare Citation uses its value / unit. `value` is in the units the text prints (pts, %,
  USD millions); `expr` may use + - * / ** parentheses and min, max, abs, round. derived_entry() builds one.
Assumptions shape: {"0.65%": "Pfizer MFN base rate (weights constant)"} or {"k": {"value": 0.3, "label": "..."}}.
"""

import ast
import operator
from dataclasses import dataclass, field

from .locator import Citation
from .numbers import declared_scale, parse_value, same_number, tokenize, tolerance

PASSING = ("exact", "substring", "fuzzy", "number_match")
DERIVED_REL_TOL = 0.005
FORMULA_WORDS = ("formula", "math", "impact")
FORMULA_CONSTANTS = (0.0, 1.0, 100.0)
MAX_DEPTH = 6


@dataclass
class GateResult:
    numeric_check: dict
    numbers: list = field(default_factory=list)   # per number: {value, where, block, start, end, kind, cites, operands, ...}

    @property
    def passed(self):
        return self.numeric_check.get("status") == "passed"

    def to_dict(self):
        return {"numeric_check": self.numeric_check, "numbers": self.numbers}


# ------------------------------------------------------------------ input normalization
def _status(c):
    v = getattr(c, "verification", None)
    if v is None and isinstance(c, dict):
        v = c.get("verification") or {}
    return (v.get("status") if isinstance(v, dict) else getattr(v, "status", "")) or ""


def as_citation(c):
    if isinstance(c, Citation):
        return c
    if isinstance(c, dict) and "canonical_id" in c:
        return Citation.from_dict(c)
    return None


def citations_of(claims):
    """Flat list of Citations from Claims, Citations, citation dicts or claim-like dicts with 'citations'."""
    out = []
    for x in claims or []:
        if isinstance(x, Citation) or (isinstance(x, dict) and "canonical_id" in x):
            c = as_citation(x)
            if c is not None:
                out.append(c)
            continue
        cits = getattr(x, "citations", None)
        if cits is None and isinstance(x, dict):
            cits = x.get("citations")
        for c in cits or []:
            c = as_citation(c)
            if c is not None:
                out.append(c)
    return out


def _blocks(text_blocks):
    """[(where, text, unit_context)]."""
    if text_blocks is None:
        return []
    if isinstance(text_blocks, str):
        return [("text", text_blocks, "")]
    if isinstance(text_blocks, dict):
        return [(str(k), "" if v is None else str(v), "") for k, v in text_blocks.items()]
    out = []
    for i, b in enumerate(text_blocks):
        if isinstance(b, str):
            out.append((f"block{i}", b, ""))
        elif isinstance(b, dict):
            out.append((str(b.get("where") or b.get("name") or f"block{i}"), str(b.get("text") or ""),
                        str(b.get("unit") or "")))
        else:
            b = tuple(b)
            out.append((str(b[0]), str(b[1] or ""), str(b[2]) if len(b) > 2 and b[2] else ""))
    return out


def _unit_scale(unit):
    t = parse_value("1", unit) if unit else None
    return t.scale if t else None


# ------------------------------------------------------------------ source texts
class _Pages:
    def __init__(self, index):
        self._index = index
        self._cache = {}

    def idx(self):
        if self._index is None:
            try:
                from .index import load_index
                self._index = load_index()
            except BaseException:           # the sqlite may be absent (SystemExit from agent.moat.cite.db)
                self._index = False
        return self._index or None

    def text(self, c):
        if c.page is None or not c.canonical_id:
            return None
        key = (c.canonical_id, c.page)
        if key not in self._cache:
            got = None
            try:
                ix = self.idx()
                got = ix.get_page(c.canonical_id, c.page) if ix is not None else None
            except BaseException:
                got = None
            self._cache[key] = got[2] if got else None
        return self._cache[key]


def _sources(c, pages, use_page_text):
    """[(basis, NumTok list, ctx_fn)] for one passing citation."""
    out = []
    page = pages.text(c) if use_page_text or c.char_start is not None else None
    q = c.quote or ""
    if q:
        base = declared_scale(page, c.char_start) if page and c.char_start is not None else None
        qctx = lambda pos, q=q, base=base: declared_scale(q, pos) or base      # noqa: E731
        out.append(("quote", tokenize(q, include_years=True), qctx))
    if c.value not in (None, ""):
        t = parse_value(c.value, c.unit)
        if t is not None:
            out.append(("value", [t], lambda pos: None))
    if use_page_text and page:
        out.append(("page", tokenize(page, include_years=True), lambda pos, page=page: declared_scale(page, pos)))
    return out


def _supported_by(tok, cits, pages, use_page_text, claim_ctx=None):
    """(list of (cite_id, basis), closest reason)."""
    hits, why = [], ""
    for c in cits:
        if _status(c) not in PASSING:
            continue
        for basis, toks, ctx in _sources(c, pages, use_page_text):
            found = False
            for s in toks:
                ok, reason = same_number(tok, s, claim_ctx, ctx(s.start))
                if ok:
                    hits.append((c.cite_id, basis))
                    found = True
                    break
                if reason == "sign differs":
                    why = f"a cited source shows {s.raw}: sign differs"
                elif reason.startswith("unit differs") and not why:
                    why = f"a cited source shows {s.raw}: {reason}"
            if found:
                break
    return hits, why


# ------------------------------------------------------------------ derived
_OPS = {ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul, ast.Div: operator.truediv,
        ast.Pow: operator.pow, ast.USub: operator.neg, ast.UAdd: operator.pos}
_FUNCS = {"min": min, "max": max, "abs": abs, "round": round}


def safe_eval(expr, env):
    """Arithmetic only: numbers, names from env, + - * / **, unary +/-, min/max/abs/round."""
    def ev(n):
        if isinstance(n, ast.Expression):
            return ev(n.body)
        if isinstance(n, ast.Constant) and isinstance(n.value, (int, float)):
            return float(n.value)
        if isinstance(n, ast.Name):
            if n.id not in env:
                raise ValueError(f"unknown operand {n.id}")
            return float(env[n.id])
        if isinstance(n, ast.BinOp) and type(n.op) in _OPS:
            return _OPS[type(n.op)](ev(n.left), ev(n.right))
        if isinstance(n, ast.UnaryOp) and type(n.op) in _OPS:
            return _OPS[type(n.op)](ev(n.operand))
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id in _FUNCS and not n.keywords:
            return float(_FUNCS[n.func.id](*[ev(a) for a in n.args]))
        raise ValueError(f"unsupported expression element {type(n).__name__}")
    return ev(ast.parse(str(expr), mode="eval"))


def derived_entry(value, expr, operands, unit="", label=""):
    """Build a derived-map entry. operands: {name: Citation | (value, Citation) | {'value', 'citation'|'assumption'|
    'derived'}}."""
    ops = {}
    for k, o in operands.items():
        if isinstance(o, tuple):
            ops[k] = {"value": o[0], "citation": o[1]}
        else:
            ops[k] = o
    return {"value": value, "unit": unit, "expr": expr, "operands": ops, "label": label}


def _num(x):
    if isinstance(x, (int, float)):
        return float(x)
    t = parse_value(x)
    if t is None:
        raise ValueError(f"no number in {x!r}")
    return -t.num if t.neg else t.num


def _operand(name, o, derived, assumptions, pages, use_page_text, depth):
    """(value, refs list, problem or '')."""
    if isinstance(o, Citation) or (isinstance(o, dict) and "canonical_id" in o):
        c = as_citation(o)
        o = {"value": c.value, "citation": c, "unit": c.unit}
    if not isinstance(o, dict):
        return _num(o), [], f"operand {name} has no citation, assumption or derivation"
    if "derived" in o:
        key = o["derived"]
        e = (derived or {}).get(key)
        if e is None:
            return None, [], f"operand {name}: derived entry {key!r} not found"
        val, refs, prob = _check_derived(e, derived, assumptions, pages, use_page_text, depth + 1)
        return val, [f"derived:{key}"] + refs, prob
    if "assumption" in o:
        label = str(o.get("assumption") or "").strip()
        return _num(o.get("value")), [f"assumption:{label}"], "" if label else f"operand {name}: assumption has no label"
    c = as_citation(o.get("citation"))
    if c is None:
        return _num(o.get("value")), [], f"operand {name} has no citation, assumption or derivation"
    val = _num(o.get("value") if o.get("value") not in (None, "") else c.value)
    if _status(c) not in PASSING:
        return val, [c.cite_id], f"operand {name}: its citation did not pass verification ({_status(c) or 'none'})"
    text = o.get("text") or (c.value if c.value not in (None, "") else f"{val:,.10g}")
    tok = parse_value(text, o.get("unit", c.unit) or "")
    if tok is None:
        return val, [c.cite_id], f"operand {name}: unparsable value {text!r}"
    hits, why = _supported_by(tok, [c], pages, use_page_text)
    if not hits:
        return val, [c.cite_id], f"operand {name} = {text} is not in its citation" + (f" ({why})" if why else "")
    return val, [c.cite_id], ""


def _check_derived(e, derived, assumptions, pages, use_page_text, depth=0):
    """(recomputed value, refs, problem or '')."""
    if depth > MAX_DEPTH:
        return None, [], "derived entries nest too deep"
    if not e.get("expr"):
        return None, [], "derived entry has no expression to re-compute"
    env, refs = {}, []
    for name, o in (e.get("operands") or {}).items():
        val, r, prob = _operand(name, o, derived, assumptions, pages, use_page_text, depth)
        refs += r
        if prob:
            return None, refs, prob
        env[name] = val
    return safe_eval(e["expr"], env), refs, ""


def _match_derived(tok, derived, assumptions, pages, use_page_text, claim_ctx):
    """(entry key, refs) on success, else (None, reason)."""
    reason = ""
    for key, e in (derived or {}).items():
        if not isinstance(e, dict) or e.get("value") in (None, ""):
            continue
        ev = parse_value(e["value"] if isinstance(e["value"], str) else f"{float(e['value']):.12g}", e.get("unit", ""))
        if ev is None or not same_number(tok, ev, claim_ctx, None)[0]:
            if not (e.get("text") and str(e["text"]).strip() == tok.raw):
                continue
        val, refs, prob = _check_derived(e, derived, assumptions, pages, use_page_text)
        if prob:
            reason = f"derived {key!r}: {prob}"
            continue
        stated = _num(e["value"])
        tol = max(DERIVED_REL_TOL * abs(stated), tolerance(tok))
        if abs(val - stated) > tol:
            reason = f"derived {key!r} re-computes to {val:,.6g}, not {stated:,.6g}"
            continue
        return key, refs
    return None, reason


def _match_assumption(tok, assumptions, claim_ctx):
    for key, a in (assumptions or {}).items():
        if isinstance(a, dict):
            label, raw, unit = str(a.get("label") or "").strip(), a.get("value", key), a.get("unit", "")
        else:
            label, raw, unit = str(a or "").strip(), key, ""
        at = parse_value(raw if isinstance(raw, str) else f"{float(raw):.12g}", unit)
        if at is None:
            continue
        if same_number(tok, at, claim_ctx, None)[0] or str(raw).strip() == tok.raw:
            if label:
                return label
    return None


# ------------------------------------------------------------------ the gate
def _empty_check(status="unchecked"):
    return {"status": status, "checked": 0, "total": 0, "verified": 0, "derived": 0, "assumed": 0, "unsupported": []}


def numeric_gate(text_blocks, claims, derived=None, assumptions=None, index=None, use_page_text=True):
    """Classify every number in text_blocks against the passing citations in claims. See the module docstring.
    text_blocks: str | [str | (where, text[, unit]) | {where, text, unit}] | {where: text}; `unit` is a context such
    as a table column's 'USD millions'. claims: Claims, Citations or their dicts (all their citations are pooled)."""
    blocks = _blocks(text_blocks)
    if not any(t.strip() for _, t, _ in blocks):
        return GateResult(_empty_check("unchecked"))
    pages = _Pages(index)
    chk = _empty_check("failed")
    nums = []
    try:
        cits = citations_of(claims)
    except Exception as e:                                      # fail closed
        cits = []
        chk["unsupported"].append({"value": None, "where": "citations", "reason": f"gate error: {e}"})
    for where, text, unit in blocks:
        try:
            toks = tokenize(text)
            ctx = _unit_scale(unit)
        except Exception as e:                                  # fail closed: the block is unsupported
            chk["unsupported"].append({"value": text[:40], "where": where, "reason": f"gate error: {e}"})
            continue
        formula = any(w in where.lower() for w in FORMULA_WORDS)
        for tok in toks:
            chk["total"] += 1
            rec = {"value": tok.raw, "where": f"{where}@{tok.start}", "block": where, "start": tok.start,
                   "end": tok.end, "kind": "unsupported", "cites": [], "operands": []}
            try:
                hits, why = _supported_by(tok, cits, pages, use_page_text, ctx)
                if hits:
                    rec.update(kind="verified", cites=[h[0] for h in hits], basis=[h[1] for h in hits])
                else:
                    key, refs = _match_derived(tok, derived, assumptions, pages, use_page_text, ctx)
                    if key is not None:
                        rec.update(kind="derived", derived=key, operands=refs)
                    else:
                        dwhy = refs                             # (None, reason) from _match_derived
                        label = _match_assumption(tok, assumptions, ctx)
                        if label is None and formula and not tok.unit and tok.scale is None and not tok.currency \
                                and tok.num in FORMULA_CONSTANTS:
                            label = "arithmetic constant"
                        if label is not None:
                            rec.update(kind="assumed", label=label)
                        else:
                            rec["reason"] = dwhy or why or "no passing citation, derivation or assumption carries this number"
                chk["checked"] += 1
            except Exception as e:                              # fail closed
                rec.update(kind="unsupported", reason=f"gate error: {type(e).__name__}: {e}")
            if rec["kind"] == "unsupported":
                chk["unsupported"].append({"value": rec["value"], "where": rec["where"], "reason": rec["reason"]})
            else:
                chk[rec["kind"]] += 1
            nums.append(rec)
    chk["status"] = "passed" if not chk["unsupported"] else "failed"
    return GateResult(chk, nums)


# ------------------------------------------------------------------ records and documents
def _get(record, path):
    cur = record
    for part in str(path).split("."):
        if isinstance(cur, dict):
            cur = cur.get(part)
        else:
            cur = getattr(cur, part, None)
        if cur is None:
            return None
    return cur


def _text_blocks_of(record, text_fields):
    blocks = []
    for f in text_fields:
        v = _get(record, f)
        if v is None:
            continue
        if isinstance(v, (list, tuple)):
            blocks += [(f"{f}[{i}]", str(x)) for i, x in enumerate(v) if x is not None]
        elif isinstance(v, dict):
            blocks += [(f"{f}.{k}", str(x)) for k, x in v.items() if isinstance(x, (str, int, float))]
        else:
            blocks.append((f, str(v)))
    return blocks


def gate_record(record, text_fields, citation_field, derived=None, assumptions=None, index=None):
    """(copy of record with 'numeric_check', passed) for a findings-style dict. text_fields may be dotted paths
    ('impact.formula'); citation_field names the list of citation dicts or Citations. derived / assumptions default to
    record['derived'] / record['assumptions']. passed is True only for status 'passed'."""
    out = dict(record)
    try:
        cits = _get(record, citation_field) or []
        res = numeric_gate(_text_blocks_of(record, text_fields), cits,
                           derived if derived is not None else record.get("derived"),
                           assumptions if assumptions is not None else record.get("assumptions"), index=index)
        out["numeric_check"] = res.numeric_check
    except Exception as e:                                      # fail closed
        out["numeric_check"] = dict(_empty_check("failed"),
                                    unsupported=[{"value": None, "where": "record", "reason": f"gate error: {e}"}])
    return out, out["numeric_check"]["status"] == "passed"


def merge_checks(checks):
    """Document-level numeric_check from per-item checks: counts summed, unsupported concatenated; passed only when
    every item passed; unchecked when no item was checked."""
    m = _empty_check("unchecked")
    any_checked = False
    for c in checks:
        for k in ("checked", "total", "verified", "derived", "assumed"):
            m[k] += c.get(k, 0)
        m["unsupported"] += list(c.get("unsupported", []))
        if c.get("status") != "unchecked":
            any_checked = True
        if c.get("status") == "failed":
            m["status"] = "failed"
    if m["status"] != "failed":
        m["status"] = "passed" if any_checked and not m["unsupported"] else ("unchecked" if not any_checked else "failed")
    return m


def _items(sections):
    if isinstance(sections, dict):
        for name, items in sections.items():
            for i, it in enumerate(items if isinstance(items, (list, tuple)) else [items]):
                yield name, i, it
    else:
        for i, it in enumerate(sections or []):
            yield "", i, it


def gate_document(sections, index=None):
    """Gate a decide or product document. sections: {section name: [item, ...]} or [item, ...]; an item is a Claim
    (text + citations, optional .derived / .assumptions), a dict {where, text, citations, derived, assumptions, unit}
    or a tuple (where, text, citations). Returns {passed, numeric_check (document level), items: [{where, text, passed,
    numeric_check, numbers}], failed: [where, ...]}. Empty-text items are skipped (nothing to emit)."""
    items, checks = [], []
    for sec, i, it in _items(sections):
        where, text = None, ""
        try:
            if isinstance(it, tuple):
                where, text, cits = it[0], it[1], it[2] if len(it) > 2 else []
                der = ass = None
                unit = ""
            elif isinstance(it, dict):
                where, text, cits = it.get("where") or it.get("name"), it.get("text"), it.get("citations") or []
                der, ass, unit = it.get("derived"), it.get("assumptions"), it.get("unit") or ""
            else:
                where, text, cits = None, getattr(it, "text", ""), getattr(it, "citations", []) or []
                der, ass, unit = getattr(it, "derived", None), getattr(it, "assumptions", None), ""
            where = where or (f"{sec}[{i}]" if sec else f"item{i}")
            if not (text or "").strip():
                continue
            res = numeric_gate([(str(where), str(text), unit)], cits, der, ass, index=index)
            chk = res.numeric_check
            nums = res.numbers
        except Exception as e:                                  # fail closed
            where = where or (f"{sec}[{i}]" if sec else f"item{i}")
            chk = dict(_empty_check("failed"), unsupported=[{"value": None, "where": str(where),
                                                              "reason": f"gate error: {e}"}])
            nums = []
        checks.append(chk)
        items.append({"where": str(where), "text": text, "passed": chk["status"] == "passed", "numeric_check": chk,
                      "numbers": nums})
    doc = merge_checks(checks)
    return {"passed": doc["status"] == "passed", "numeric_check": doc, "items": items,
            "failed": [x["where"] for x in items if not x["passed"]]}
