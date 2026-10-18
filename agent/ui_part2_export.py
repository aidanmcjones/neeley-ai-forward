#!/usr/bin/env python3
"""ui_part2_export: copy the model session's Part 2 ("Decide") deliverable into the judge-facing UI data.

Contract: docs/part2/UI_CONTRACT.md (quant-model) and docs/ui_part2.md (this side). Reads out/part2/<T>/part2.json and
trace.jsonl for every company in out/part2/ and writes ui/public/data/part2/ (index.json, <T>.json, <T>_trace.json)
with the public withholding rule applied to every cite, the same figure gate as Part 1 applied to every sentence, and
the hard checks below. No model call, no network, no API key.

    PYTHONPATH=. python -m agent.ui_part2_export                  # export out/part2 -> ui/public/data/part2
    PYTHONPATH=. python -m agent.ui_part2_export --check          # validate ui/public/data/part2 (exit 1 on errors)
    PYTHONPATH=. python -m agent.ui_part2_export --check --sample # also validate ui/public/data/_sample/part2

Hard checks (a company that fails is listed in index.missing with its errors and is not written; --check exits 1):
- every gated block (move, budget, cost, return, each math step, net, each why_passed, each kill signal, lands_because,
  can_tell, cannot_tell, each promo piece) carries numeric_check with status passed or no_numbers; "passed" carries
  checked > 0 and the breakdown; no failed or unchecked block anywhere;
- every [n] marker in a *_marked field resolves to a cite on that record (unresolved markers are dropped on export);
- exactly two rejected alternatives, each with the move, why_passed and a skeptic lens; at least one kill signal, each
  with signal, threshold and month window; drivers name Part 1 finding numbers that exist in data/part1/<T>.json;
- promo: has_material true needs the exact student-concept label, at least one piece, a claims map row per claim and a
  rules_check that confirms the label and the claims map; has_material false needs empty pieces and claims_map;
- figures: every figure in prose that no passed numeric_check governs and that the gate never passed (in this record or
  in the company's Part 1 record) is replaced by "[figure withheld: not gated]"; a check pass finds none left;
- no "Citation(" or "Claim(" substring, no lost dollar sign, no league / score / robustness words anywhere;
- the trace header names the two lenses; killed candidates print no ungated digits;
- unknown top-level keys are dropped (printed), never passed through.
"""
from __future__ import annotations

import argparse
import copy
import json
import re
import sys
from pathlib import Path

from agent.ui_part1_export import (  # noqa: F401  (shared gate helpers)
    DATA, ExportError, MARK, WITHHELD_FIGURE, _nc_passed, _skeptic_strings, all_problems, fig_key, figures,
    gated_figures, now_iso, read_json, read_jsonl, strip_killed, withhold, withhold_tree, withhold_ungated, walk_marked,
    write,
)

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "out" / "part2"
DEST = DATA / "part2"
SAMPLE_DEST = DATA / "_sample" / "part2"
P1_DEST = DATA / "part1"

PROMPT = "recommend one strategic move for the next 24 months, with a specific budget or commitment of people behind it."
BANNER = "Student concept, not actual promotional material."
LENSES = ["CFO/math", "Decider/compliance"]
VERDICTS = ("survived", "narrowed", "killed")
TYPES = ("license_or_acquire", "pricing_or_coverage", "portfolio_shift", "new_indication", "campaign")
CONTRACT_TOP = {"ticker", "company", "generated_at", "move", "drivers", "case_for", "rejected", "kill_signals", "evidence",
                "promo", "unresolved", "candidates_considered", "skeptic_summary"}
EXPORT_EXTRA = {"numeric_summary", "figures_withheld", "sample"}
# Keys whose strings are identifiers, schedules or labels, never claims: left alone by the figure gate.
EXEMPT_KEYS = {"ticker", "company", "generated_at", "id", "cite_id", "candidate_id", "doc_id", "marker_map", "cites", "cite",
               "type", "skeptic_lens", "month_window", "label", "finding_n", "step", "decider", "lenses", "verdict",
               "support_section", "url", "deep_link", "viewer_link", "quote", "excerpt", "page", "period"}
# Subtrees the figure gate never rewrites: cites, marker maps and the gate's own bookkeeping.
SKIP_KEYS = {"cites", "cite", "marker_map", "numeric_check", "numeric_summary", "skeptic_summary"}
RULES = ("approved_uses_only", "risks_prominent", "h2h_only", "no_testimonials", "labelled", "claims_map_present")


def _is_block(x):
    return isinstance(x, dict) and ("text" in x or "text_marked" in x or "numeric_check" in x)


def _ok_nc(x):
    return isinstance(x, dict) and x.get("status") in ("passed", "no_numbers")


# ---------------------------------------------------------------- figure gate
def _strings_of(d):
    """The prose strings of one record (not its cites, ids or marker map), markers stripped."""
    out = []
    for k, v in d.items():
        if k in EXEMPT_KEYS:
            continue
        if isinstance(v, str):
            out.append(MARK.sub("", v))
    return out


def gated_set(rec, p1rec):
    """Every figure a passed numeric_check vouches for: the company's Part 1 gated set plus the prose of every
    Part 2 record whose own numeric_check passed."""
    out = set(gated_figures(p1rec or {}))

    def walk(x):
        if isinstance(x, dict):
            if _nc_passed(x.get("numeric_check")):
                for s in _strings_of(x):
                    out.update(fig_key(t) for t in figures(s))
            for k, v in x.items():
                if k not in ("cites", "cite", "marker_map"):
                    walk(v)
        elif isinstance(x, list):
            for v in x:
                walk(v)
    walk(rec)
    return out


def gate_record(rec, gated):
    """Withhold every ungated figure in prose that no passed numeric_check governs. Returns the count."""
    n = 0

    def walk(x, governed):
        nonlocal n
        if isinstance(x, dict):
            g = governed or _nc_passed(x.get("numeric_check"))
            for k, v in list(x.items()):
                if k in SKIP_KEYS:
                    continue
                if isinstance(v, str):
                    if k in EXEMPT_KEYS or g:
                        continue
                    x[k], m = withhold_ungated(v, gated)
                    n += m
                else:
                    walk(v, g)
        elif isinstance(x, list):
            for v in x:
                walk(v, governed)
    walk(rec, False)
    return n


def gate_problems(rec, gated, path="$"):
    """After export: no prose outside a passed block may still carry an ungated figure."""
    errs = []

    def walk(x, governed, p):
        if isinstance(x, dict):
            g = governed or _nc_passed(x.get("numeric_check"))
            for k, v in x.items():
                if k in SKIP_KEYS:
                    continue
                if isinstance(v, str):
                    if k in EXEMPT_KEYS or g:
                        continue
                    bad = [t.raw for t in figures(MARK.sub("", v)) if fig_key(t) not in gated]
                    if bad:
                        errs.append(f"{p}.{k} prints figures the gate did not pass: {bad[:4]}")
                    if re.search(re.escape(WITHHELD_FIGURE) + r"[\s,;/-]*" + re.escape(WITHHELD_FIGURE), v):
                        errs.append(f"{p}.{k} shows two withheld markers in a row")
                else:
                    walk(v, g, f"{p}.{k}")
        elif isinstance(x, list):
            for i, v in enumerate(x):
                walk(v, governed, f"{p}[{i}]")
    walk(rec, False, path)
    return errs


# ---------------------------------------------------------------- company
def numeric_summary(rec):
    """The sum of every block's numeric_check: passed when at least one block counted numbers, else no_numbers."""
    acc = {"checked": 0, "total": 0, "verified": 0, "derived": 0, "assumed": 0}
    blocks = passed = 0

    def walk(x):
        nonlocal blocks, passed
        if isinstance(x, dict):
            nc = x.get("numeric_check")
            if isinstance(nc, dict):
                blocks += 1
                if nc.get("status") == "passed":
                    passed += 1
                    for k in acc:
                        v = nc.get(k)
                        acc[k] += v if isinstance(v, (int, float)) else 0
            for k, v in x.items():
                if k not in ("cites", "cite"):
                    walk(v)
        elif isinstance(x, list):
            for v in x:
                walk(v)
    walk(rec)
    if passed and acc["checked"]:
        return {"status": "passed", **{k: int(v) for k, v in acc.items()},
                "note": f"{passed} of {blocks} blocks carry numbers; all page-checked"}
    return {"status": "no_numbers", "note": f"{blocks} blocks, none states a number"}


def keep_dataset_links(obj):
    """A machine-data cite (CMS rows cited by locator) keeps its public dataset URL as viewer_link: the public rule
    withholds the quote and the deep link, never the dataset the row comes from."""
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k == "cites" and isinstance(v, list):
                for c in v:
                    if isinstance(c, dict) and c.get("verify_status") == "machine_data" and c.get("url") and not c.get("viewer_link"):
                        c["viewer_link"] = c["url"]
            else:
                keep_dataset_links(v)
    elif isinstance(obj, list):
        for v in obj:
            keep_dataset_links(v)


def build_company(raw, ticker, p1rec):
    """The exported record: contract keys only, cites withheld, markers repaired, ungated figures withheld."""
    rec = copy.deepcopy(raw) if isinstance(raw, dict) else {}
    extra = sorted(set(rec) - CONTRACT_TOP)
    for k in extra:
        rec.pop(k)
    if extra:
        print(f"note: {ticker}: dropped keys outside the contract: {extra}")
    rec["ticker"] = rec.get("ticker") or ticker
    promo = rec.get("promo")
    if isinstance(promo, dict):
        rows = []
        for r in promo.get("claims_map") or []:
            if not isinstance(r, dict):
                continue
            r = dict(r)
            c = r.pop("cite", None)
            cites = [x for x in (r.get("cites") or []) if isinstance(x, dict)]
            if isinstance(c, dict):
                cites.insert(0, c)
            r["cites"] = cites
            rows.append(r)
        promo["claims_map"] = rows
    keep_dataset_links(rec)
    withhold_tree(rec)
    walk_marked(rec, fix=True)
    budget = (rec.get("move") or {}).get("budget") if isinstance(rec.get("move"), dict) else None
    if isinstance(budget, dict) and not _nc_passed(budget.get("numeric_check")):
        budget["amount_usd"] = None  # a figure the gate never checked
        budget["people"] = None
    gated = gated_set(rec, p1rec)
    rec["figures_withheld"] = gate_record(rec, gated)
    rec["numeric_summary"] = numeric_summary(rec)
    return rec


def _block_problems(b, p, errs, need_text=True):
    if not isinstance(b, dict):
        errs.append(f"{p} is not a gated block")
        return
    if need_text and not (b.get("text") or b.get("text_marked")):
        errs.append(f"{p} has no text")
    if not _ok_nc(b.get("numeric_check")):
        errs.append(f"{p}.numeric_check is not passed or no_numbers")


def company_problems(rec, t, p1rec=None, sample=False):
    errs, warns = [], []
    if not isinstance(rec, dict):
        return [f"{t}: record is not an object"], warns
    if rec.get("ticker") != t:
        errs.append(f"ticker {rec.get('ticker')!r} is not {t}")
    if not rec.get("company"):
        errs.append("company name missing")
    unknown = sorted(set(rec) - CONTRACT_TOP - EXPORT_EXTRA)
    if unknown:
        errs.append(f"keys outside the contract: {unknown}")
    mv = rec.get("move")
    _block_problems(mv, "move", errs)
    if isinstance(mv, dict):
        if mv.get("type") and not (mv["type"] in TYPES or str(mv["type"]).startswith("other:")):
            warns.append(f"move.type {mv['type']!r} is not a contract type")
        _block_problems(mv.get("budget"), "move.budget", errs)
        b = mv.get("budget")
        if isinstance(b, dict) and not _nc_passed(b.get("numeric_check")) and (b.get("amount_usd") is not None or b.get("people") is not None):
            errs.append("move.budget states amount_usd or people without a passed numeric_check")
    drivers = rec.get("drivers")
    if not isinstance(drivers, list) or not drivers:
        errs.append("drivers is empty")
    else:
        have = {int(f.get("n")) for f in (p1rec or {}).get("findings") or [] if isinstance(f, dict) and str(f.get("n")).isdigit()}
        for i, d in enumerate(drivers):
            n = d.get("finding_n") if isinstance(d, dict) else None
            if not isinstance(n, int):
                errs.append(f"drivers[{i}].finding_n is not an integer")
            elif have and n not in have:
                errs.append(f"drivers[{i}].finding_n {n} is not a finding in data/part1/{t}.json")
            elif not have:
                warns.append(f"drivers[{i}].finding_n {n} could not be checked: data/part1/{t}.json not exported")
    cf = rec.get("case_for")
    if not isinstance(cf, dict):
        errs.append("case_for missing")
    else:
        _block_problems(cf.get("cost"), "case_for.cost", errs)
        _block_problems(cf.get("return"), "case_for.return", errs)
        steps = cf.get("math_steps")
        if not isinstance(steps, list) or not steps:
            errs.append("case_for.math_steps is empty")
        else:
            for i, s in enumerate(steps):
                _block_problems(s, f"case_for.math_steps[{i}]", errs)
        if cf.get("net") is not None:
            _block_problems(cf.get("net"), "case_for.net", errs)
    rej = rec.get("rejected")
    if not isinstance(rej, list) or len(rej) != 2:
        errs.append(f"rejected must hold exactly two alternatives, found {len(rej) if isinstance(rej, list) else rej!r}")
    else:
        for i, r in enumerate(rej):
            if not isinstance(r, dict) or not r.get("move"):
                errs.append(f"rejected[{i}] has no move")
                continue
            _block_problems(r.get("why_passed"), f"rejected[{i}].why_passed", errs)
            if r.get("skeptic_lens") not in LENSES:
                errs.append(f"rejected[{i}].skeptic_lens {r.get('skeptic_lens')!r} is not one of {LENSES}")
    ks = rec.get("kill_signals")
    if not isinstance(ks, list) or not ks:
        errs.append("kill_signals is empty")
    else:
        for i, k in enumerate(ks):
            if not isinstance(k, dict):
                errs.append(f"kill_signals[{i}] is not an object")
                continue
            for f in ("signal", "threshold", "month_window"):
                if not k.get(f):
                    errs.append(f"kill_signals[{i}].{f} missing")
            if not _ok_nc(k.get("numeric_check")):
                errs.append(f"kill_signals[{i}].numeric_check is not passed or no_numbers")
    ev = rec.get("evidence")
    if not isinstance(ev, dict):
        errs.append("evidence missing")
    else:
        if not ev.get("decider"):
            errs.append("evidence.decider missing")
        for f in ("lands_because", "can_tell", "cannot_tell"):
            _block_problems(ev.get(f), f"evidence.{f}", errs)
    pr = rec.get("promo")
    if not isinstance(pr, dict) or not isinstance(pr.get("has_material"), bool):
        errs.append("promo.has_material must be true or false")
    else:
        pieces, claims, rc = pr.get("pieces") or [], pr.get("claims_map") or [], pr.get("rules_check") or {}
        if pr["has_material"]:
            if pr.get("label") != BANNER:
                errs.append(f"promo.label must be exactly {BANNER!r}")
            if not pieces:
                errs.append("promo.has_material is true but pieces is empty")
            for i, p in enumerate(pieces):
                if not isinstance(p, dict) or not (p.get("body") or p.get("body_marked")):
                    errs.append(f"promo.pieces[{i}] has no body")
                elif not _ok_nc(p.get("numeric_check")):
                    errs.append(f"promo.pieces[{i}].numeric_check is not passed or no_numbers")
            if not claims:
                errs.append("promo.has_material is true but claims_map is empty")
            for i, r in enumerate(claims):
                if not isinstance(r, dict) or not r.get("claim") or not r.get("support_section"):
                    errs.append(f"promo.claims_map[{i}] needs claim and support_section")
                elif not (r.get("cites") or r.get("cite")):
                    errs.append(f"promo.claims_map[{i}] has no cite")
            if not isinstance(rc, dict) or rc.get("labelled") is not True or rc.get("claims_map_present") is not True:
                errs.append("promo.rules_check must confirm labelled and claims_map_present")
            for k in RULES:
                if isinstance(rc, dict) and rc.get(k) is not True:
                    warns.append(f"promo.rules_check.{k} is {rc.get(k)!r}: the UI withholds the piece unless risks_prominent and labelled are true")
        else:
            if pieces or claims:
                errs.append("promo.has_material is false but pieces or claims_map is not empty")
    ss = rec.get("skeptic_summary")
    if not isinstance(ss, dict) or any(not isinstance(ss.get(k), int) for k in VERDICTS):
        errs.append("skeptic_summary needs integer killed, narrowed, survived")
    if not isinstance(rec.get("candidates_considered"), int):
        errs.append("candidates_considered must be an integer")
    for i, u in enumerate(rec.get("unresolved") or []):
        if not isinstance(u, dict) or not u.get("topic"):
            errs.append(f"unresolved[{i}] has no topic")
    if "numeric_summary" in rec and not _ok_nc(rec["numeric_summary"]):
        errs.append("numeric_summary is not passed or no_numbers")
    return errs, warns


# ---------------------------------------------------------------- trace
def build_trace(lines, ticker, gated):
    if not lines:
        raise ExportError("trace.jsonl is empty")
    head = lines[0] if lines[0].get("category") == "header" or lines[0].get("step") == 0 else {}
    steps = [copy.deepcopy(s) for s in (lines[1:] if head else lines) if isinstance(s, dict)]
    out = {"ticker": head.get("ticker") or ticker, "generated_at": head.get("generated_at"),
           "lenses": head.get("lenses") or LENSES, "steps": []}
    counts = {v: 0 for v in VERDICTS}
    for s in steps:
        s = {k: v for k, v in s.items() if k in ("step", "candidate_id", "move", "type", "skeptic_cfo", "skeptic_decider", "verdict", "reason", "cites")}
        withhold_tree(s)
        killed = s.get("verdict") == "killed"
        fn = (lambda x: strip_killed(x, gated)) if killed else (lambda x: withhold_ungated(x, gated))
        n = 0
        for k in ("move", "reason"):
            if isinstance(s.get(k), str):
                s[k], m = fn(s[k])
                n += m
        for k in ("skeptic_cfo", "skeptic_decider"):
            if s.get(k) is not None:
                s[k], m = _skeptic_strings(s[k], fn)
                n += m
        s["figures_withheld"] = n
        if s.get("verdict") in counts:
            counts[s["verdict"]] += 1
        out["steps"].append(s)
    out["summary"] = {**counts, "candidates": len(out["steps"])}
    return out


def trace_problems(tr, t, gated):
    errs = []
    if not isinstance(tr, dict):
        return [f"{t}_trace.json is not an object"]
    if tr.get("ticker") != t:
        errs.append(f"trace ticker {tr.get('ticker')!r} is not {t}")
    if list(tr.get("lenses") or []) != LENSES:
        errs.append(f"trace lenses {tr.get('lenses')!r} are not {LENSES}")
    for i, s in enumerate(tr.get("steps") or []):
        p = f"steps[{i}]"
        if s.get("verdict") not in VERDICTS:
            errs.append(f"{p}.verdict {s.get('verdict')!r} is not one of {VERDICTS}")
        if "figures_withheld" not in s:
            errs.append(f"{p} carries no figures_withheld count")

        def chk(text, where):
            if isinstance(text, str):
                bad = [x.raw for x in figures(text) if fig_key(x) not in gated]
                if bad:
                    errs.append(f"{p}.{where} prints figures the gate did not pass: {bad[:4]}")
                if s.get("verdict") == "killed" and re.search(r"\d", re.sub(re.escape(WITHHELD_FIGURE), "", text)) and bad:
                    errs.append(f"{p}.{where}: killed candidate prints digits")
        chk(s.get("move"), "move")
        chk(s.get("reason"), "reason")
        for k in ("skeptic_cfo", "skeptic_decider"):
            _skeptic_strings(s.get(k), lambda x, k=k: (chk(x, k), (x, 0))[1])
    return errs


# ---------------------------------------------------------------- bundle
def bundle_problems(t, rec, tr, p1rec, sample=False):
    errs, warns = company_problems(rec, t, p1rec, sample)
    gated = gated_set(rec, p1rec)
    errs += gate_problems(rec, gated)
    errs += trace_problems(tr, t, gated)
    errs += all_problems({f"{t}.json": rec, f"{t}_trace.json": tr})
    return errs, warns


def check_dir(d, sample=False):
    d = Path(d)
    errs, warns = [], []
    idx = read_json(d / "index.json")
    if not idx:
        return [f"{d}/index.json missing or unreadable"], warns
    if bool(idx.get("sample")) != sample:
        errs.append(f"{d}/index.json sample is {idx.get('sample')}, expected {sample}")
    avail, missing = idx.get("available"), idx.get("missing")
    if not isinstance(avail, list) or not isinstance(missing, list) or not isinstance(idx.get("picked"), list):
        return errs + ["index.json must carry picked, available and missing lists"], warns
    listed = [m.get("ticker") for m in missing if isinstance(m, dict)]
    for t in idx["picked"]:
        if (t in avail) == (t in listed):
            errs.append(f"picked {t} must be in exactly one of available and missing")
    p1dir = P1_DEST if not sample else DATA / "_sample" / "part1"
    for t in avail:
        rec, tr = read_json(d / f"{t}.json"), read_json(d / f"{t}_trace.json")
        if rec is None or tr is None:
            errs.append(f"{d}/{t}.json or {t}_trace.json missing")
            continue
        e, w = bundle_problems(t, rec, tr, read_json(p1dir / f"{t}.json"), sample)
        errs += e
        warns += w
    for t in listed:
        if (d / f"{t}.json").exists() or (d / f"{t}_trace.json").exists():
            errs.append(f"{t} is listed missing but a stale file is on disk")
    return errs, warns


def export(src=OUT, dest=DEST):
    src, dest = Path(src), Path(dest)
    dirs = sorted(p for p in src.iterdir() if p.is_dir() and (p / "part2.json").exists()) if src.is_dir() else []
    p1idx = read_json(P1_DEST / "index.json") or {}
    picked = [t for t in (p1idx.get("picked") or []) if isinstance(t, str)]
    tickers = picked + sorted(p.name for p in dirs if p.name not in picked)
    if not dirs:
        print(f"{src} holds no <T>/part2.json yet (Part 2 is still being written); nothing written.")
        return 0
    ok, missing = {}, []
    for t in tickers:
        pj, tj = src / t / "part2.json", src / t / "trace.jsonl"
        if not pj.exists():
            missing.append({"ticker": t, "reason": "writing", "absent": ["part2.json"]})
            continue
        p1rec = read_json(P1_DEST / f"{t}.json")
        try:
            rec = build_company(read_json(pj), t, p1rec)
            tr = build_trace(read_jsonl(tj) if tj.exists() else [], t, gated_set(rec, p1rec))
            errs, warns = bundle_problems(t, rec, tr, p1rec)
        except (ExportError, ValueError, TypeError, AttributeError) as e:
            errs, warns = [str(e)], []
        for w in warns:
            print(f"warning: {t}: {w}")
        if errs:
            missing.append({"ticker": t, "reason": "failed checks", "errors": errs[:20]})
            print(f"ERROR: {t} not written:\n  " + "\n  ".join(errs[:20]))
        else:
            ok[t] = (rec, tr)
    dest.mkdir(parents=True, exist_ok=True)
    for m in missing:
        for name in (f"{m['ticker']}.json", f"{m['ticker']}_trace.json"):
            (dest / name).unlink(missing_ok=True)
    for t, (rec, tr) in ok.items():
        write(dest / f"{t}.json", rec)
        write(dest / f"{t}_trace.json", tr)
    index = {"generated_at": now_iso(), "prompt": PROMPT, "picked": tickers, "available": [t for t in tickers if t in ok],
             "missing": missing, "sample": False, "contract": "docs/part2/UI_CONTRACT.md", "source": "out/part2"}
    write(dest / "index.json", index)
    print(f"wrote {dest}: index.json; available {index['available']}; missing {[(m['ticker'], m['reason']) for m in missing]}")
    return 1 if any(m["reason"] == "failed checks" for m in missing) else 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--check", action="store_true", help="validate the exported files instead of writing")
    ap.add_argument("--sample", action="store_true", help="with --check: also validate ui/public/data/_sample/part2")
    ap.add_argument("--src", default=str(OUT))
    ap.add_argument("--dest", default=str(DEST))
    a = ap.parse_args(argv)
    if a.check:
        bad = 0
        targets = []
        if Path(a.dest).joinpath("index.json").exists():
            targets.append((Path(a.dest), False))
        elif not a.sample:
            print(f"{a.dest} not exported yet (out/part2 has not landed); nothing to check.")
        if a.sample and SAMPLE_DEST.joinpath("index.json").exists():
            targets.append((SAMPLE_DEST, True))
        for d, smp in targets:
            errs, warns = check_dir(d, smp)
            for w in warns:
                print(f"warning: {w}")
            for e in errs:
                print(f"ERROR: {e}")
            print(f"{d}: {len(errs)} errors, {len(warns)} warnings")
            bad += bool(errs)
        return 1 if bad else 0
    try:
        return export(a.src, a.dest)
    except ExportError as e:
        print(f"ERROR: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
