"""The courtroom: every top finding is argued by a prosecutor, rebutted by a defense playing the company's CFO
(armed only with the company's own filings and calls), and ruled on by a judge. One cached agent.llm.call per role.

Every quote any role cites is checked with the page verifier. A quote that is invented, paraphrased or on the wrong
page is logged to out/<T>/ai_caught.jsonl: the live, genuine "AI was confidently wrong" record.
Judge rulings adjust the finding: "fails" downgrades confidence to low; "survives" keeps it.

Usage:  python -m agent.needle.trial --ticker AZN [--top 5] [--dry-run]     (needs ANTHROPIC_API_KEY unless --dry-run)
"""

import argparse
import json
import re

from agent.needle import audit, pages
from agent.needle.detect import OUT
from agent.needle.schema import Evidence, Finding, read_jsonl, write_jsonl

ROLE_SYSTEM = {
    "prosecutor": ("You are a forensic equity analyst. Argue that the finding is material and NOT priced in, using only "
                   "the documents provided. Every factual claim must carry a quote copied exactly from one document."),
    "defense": ("You are the company's CFO defending against the finding, using only the company's own documents "
                "provided. Argue it is immaterial, already disclosed or already priced in. Quote exactly."),
    "judge": ("You are an impartial judge. Weigh both arguments against the documents only. Rule whether the finding "
              "survives as material and not priced in. Do not introduce facts that are not in the documents."),
}
FORMAT = ('Return ONLY JSON: {"argument": "<=120 words", "quotes": [{"source": "<document id exactly as tagged>", '
          '"quote": "15 to 50 words copied exactly"}]%s}')


def context(finding, docs, extra=4):
    """Cited pages (+/-1) plus a few same-company pages that mention the finding's topics."""
    ctx = {}
    for ev in finding.evidence:
        if ev.doc_id.startswith("drug:"):  # FDA label: cite by document id, verified with labels.verify_label
            slug = ev.doc_id.split(":")[1]
            path = pages.CORPUS / "drugs" / slug / "label_sections.md"
            if path.exists():
                ctx[ev.doc_id] = path.read_text(encoding="utf-8", errors="ignore")[:12000]
            continue
        d = docs.get(ev.doc_id)
        if not d or ev.page is None:
            continue
        for n in (ev.page - 1, ev.page, ev.page + 1):
            if n in d["pages"]:
                ctx[f"{ev.doc_id}#p{n}"] = d["pages"][n][1][:6000]
    topics = [t for t in finding.vector.get("topics", []) if t != "other"]
    pat = re.compile("|".join(re.escape(t) for t in topics), re.I) if topics else None
    if pat:
        hits = sorted(((len(pat.findall(t)), f"{i}#p{n}", t) for i, d in docs.items()
                       if d["row"]["doc_type"] in ("transcript", "quarterly_report", "earnings_release")
                       for n, (_, t) in d["pages"].items()), reverse=True)
        for _, sid, t in hits[:extra]:
            ctx.setdefault(sid, t[:6000])
    return ctx


def _parse(text):
    m = re.search(r"\{.*\}", text, re.S)
    return json.loads(m.group(0)) if m else {}


def _check_quotes(role, out, docs, finding, caught):
    ok = 0
    for q in out.get("quotes", []):
        src = str(q.get("source", ""))
        if src.startswith("drug:"):
            from agent.needle.detect.labels import verify_label
            if verify_label(Evidence(src, None, q.get("quote", ""))):
                ok += 1
            else:
                caught.append({"finding": finding.id, "role": role, "quote": q.get("quote"), "source": src,
                               "verdict": "rejected", "reason": "quote not found in the FDA label"})
            continue
        m = re.fullmatch(r"(.+)#p(\d+)", src)
        if not m:
            caught.append({"finding": finding.id, "role": role, "quote": q.get("quote"), "source": q.get("source"),
                           "reason": "source id is not a real document page"})
            continue
        ev = Evidence(m.group(1), int(m.group(2)), q.get("quote", ""))
        status, reason = pages.check(ev, docs)
        if status == "verified":
            ok += 1
        else:
            caught.append({"finding": finding.id, "role": role, "quote": ev.quote, "source": ev.source(),
                           "verdict": status, "reason": reason})
    return ok


def try_finding(finding, docs, dry_run=False):
    ctx = context(finding, docs)
    claim = (f"FINDING ({finding.ticker}): {finding.finding}\nIMPACT: {finding.impact.get('formula')}\n"
             f"PEER: {finding.peer}\nOBSCURITY: {finding.vector.get('obscurity_note')}")
    if dry_run:
        return {"finding": finding.id, "context_pages": list(ctx), "context_chars": sum(map(len, ctx.values()))}
    from agent.llm import call
    caught = []
    pro = _parse(call(claim + "\n\n" + FORMAT % "", context=ctx, system=ROLE_SYSTEM["prosecutor"])["text"])
    dfn = _parse(call(claim + "\n\nPROSECUTION:\n" + json.dumps(pro) + "\n\n" + FORMAT % "", context=ctx,
                      system=ROLE_SYSTEM["defense"])["text"])
    jdg = _parse(call(claim + "\n\nPROSECUTION:\n" + json.dumps(pro) + "\n\nDEFENSE:\n" + json.dumps(dfn) + "\n\n" +
                      FORMAT % ', "ruling": "survives | fails | unresolved", "reason": "<=60 words"', context=ctx,
                      system=ROLE_SYSTEM["judge"], effort="high")["text"])
    verified = {r: _check_quotes(r, o, docs, finding, caught) for r, o in
                (("prosecutor", pro), ("defense", dfn), ("judge", jdg))}
    return {"finding": finding.id, "prosecutor": pro, "defense": dfn, "judge": jdg,
            "ruling": jdg.get("ruling", "unresolved"), "verified_quotes": verified, "ai_caught": caught}


def run(ticker, top=5, dry_run=False):
    docs = pages.docs(ticker)
    findings = read_jsonl(OUT / ticker / "findings.jsonl", Finding)
    pool = [f for f in findings if f.verdict == "verified"][:top]
    results, caught = [], []
    for f in pool:
        r = try_finding(f, docs, dry_run)
        results.append(r)
        if dry_run:
            continue
        caught += r["ai_caught"]
        if r["ruling"] == "fails":
            f.confidence, f.reason = "low", f"trial: {r['judge'].get('reason', '')}"
        audit.append("verdict", {"finding": f.id, "ruling": r["ruling"], "ai_caught": len(r["ai_caught"])})
    if not dry_run:
        write_jsonl(OUT / ticker / "trials.jsonl", results)
        write_jsonl(OUT / ticker / "ai_caught.jsonl", caught)
        write_jsonl(OUT / ticker / "findings.jsonl", findings)
    return results


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--ticker", required=True)
    ap.add_argument("--top", type=int, default=5)
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    for r in run(a.ticker.upper(), a.top, a.dry_run):
        print(json.dumps({k: r[k] for k in r if k in ("finding", "ruling", "verified_quotes", "context_chars")}))


if __name__ == "__main__":
    main()
