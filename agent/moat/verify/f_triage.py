"""Classify each restatements.csv row; cite the later filing and the printed page where the revised value prints."""
import csv, json, pickle, re
from agent.moat.verify.f_lib import RESTATE, acc_doc, find_value

SUBS = json.load(open("data/moat/scratch/f_subs.json"))
RECON = pickle.load(open("data/moat/scratch/f_recon.pkl", "rb"))
NOTES = json.load(open("agent/moat/verify/f_notes.json")) if __import__("os").path.exists("agent/moat/verify/f_notes.json") else {}


def label(m):
    m = m.split(":")[-1]
    m = re.sub(r"(?i)member$", "", m)
    return re.sub(r"(?<=[a-z])(?=[A-Z])", " ", m)


def kw(member):
    """Regex keyword to locate the product row near a number."""
    w = label(member).split()
    w = [x for x in w if x.lower() not in ("other", "products", "product", "and", "all", "alliance", "revenue", "revenues")]
    return re.escape(w[0])[:12] if w else "Other"


def fmt(v):
    return f"${v / 1e6:,.1f}M" if abs(v) >= 1e5 else f"{v:g}"


rows = []
for res in RECON:
    r = RESTATE[res["i"]]
    pairs = res["pairs"]
    vals = [v for _, v in pairs]
    accs = [a for a, _ in pairs]
    same_acc = len(accs) != len(set(accs))
    first, last = pairs[0], pairs[-1]
    ftxt = "; ".join(f"{fmt(v)} in {SUBS.get(a, {}).get('form', '?')} filed {SUBS.get(a, {}).get('filed', '?')} ({a})" for a, v in pairs)
    pct = r["concept"].split(":")[1].startswith("Percentage")
    note_key = None
    if pct:
        cls = "parse_artifact"
        expl = ("Concept is a percent-change ratio, not revenue, yet the panel stores it in value_usd; the two filings print different "
                "growth rates because the underlying revenue base was recast. Not a revenue restatement. Values: " + ftxt)
    elif same_acc:
        cls = "parse_artifact"
        expl = ("Both values come from the SAME filing (two XBRL facts for one context at different decimals, e.g. 1,469.8 and 1,470); "
                "the collector treated them as two filings. Values: " + ftxt)
    elif max(vals) - min(vals) <= 0.5e6 + 1e3 or all(round(v / 1e6) == round(vals[0] / 1e6) for v in vals):
        cls = "comparative_presentation"
        expl = ("Rounding only: the earlier filing tags the number to $0.1M, the later one to $1M (or vice versa); same number. Values: " + ftxt)
    else:
        moved = [s for s in res["steps"] if s["gone"] or s["new_members"]]
        real_moved = []
        for s in moved:
            g = {k: v for k, v in s["gone"].items() if v}
            n = {k: v for k, v in s["new_members"].items() if v}
            # drop pure renames (same value both sides)
            gv = sorted(round(v / 1e6) for v in g.values())
            for k, v in list(n.items()):
                for k2, v2 in list(g.items()):
                    if abs(v - v2) < 1e6:
                        n.pop(k, None); g.pop(k2, None); break
            if g or n:
                real_moved.append((s, g, n))
        if real_moved:
            cls = "recast_reclassification"
            parts = []
            for s, g, n in real_moved:
                bits = []
                if g:
                    bits.append("no longer broken out (folded into this line): " + ", ".join(f"{label(k)} {fmt(v)}" for k, v in g.items()))
                if n:
                    bits.append("newly broken out (taken out of this line): " + ", ".join(f"{label(k)} {fmt(v)}" for k, v in n.items()))
                tag = "reconciles" if s["explained"] else "partly reconciles"
                parts.append(f"{SUBS.get(s['old'], {}).get('form','?')} {SUBS.get(s['old'], {}).get('filed','?')} -> "
                             f"{SUBS.get(s['new'], {}).get('form','?')} {SUBS.get(s['new'], {}).get('filed','?')}: {fmt(s['v0'])} -> {fmt(s['v1'])}; "
                             + "; ".join(bits) + f" ({tag} to the change)")
            expl = "Member scope of the bucket changed. " + " | ".join(parts)
        else:
            note_key = f"{r['ticker']}|{r['product_member']}|{last[0]}"
            n = NOTES.get(note_key) or NOTES.get(f"{r['ticker']}|*|{last[0]}") or NOTES.get(f"{r['ticker']}|{r['product_member']}|*")
            if n:
                cls, expl = n["class"], n["explanation"] + " Values: " + ftxt
            else:
                cls, expl = "UNRESOLVED", "Values: " + ftxt
    # citation: later filing doc and printed page where the latest value prints
    doc = acc_doc(last[0])
    page = ""
    if doc and not pct:
        hits = find_value(doc, last[1], near=kw(r["product_member"]) if r["product_member"] else None)
        page = ";".join(f"p{p}/printed {pr}" for p, pr in hits[:3])
    s = SUBS.get(last[0], {})
    cite = f"{r['ticker']} {s.get('form','?')} filed {s.get('filed','?')} acc {last[0]}" + (f" [{doc}] {page}" if doc else " [no page-marked copy]")
    rows.append(dict(r, row_id=res["i"], **{"class": cls, "explanation": expl, "citation": cite, "printed_page": page,
                                            "note_key": note_key or ""}))
cols = ["row_id", "ticker", "concept", "product_member", "geography", "other_dims", "period_start", "period_end", "n_values",
        "min_value", "max_value", "pct_diff", "class", "explanation", "citation", "printed_page", "values_by_accession"]
with open("data/moat/scratch/restatements_triaged.csv", "w") as f:
    w = csv.DictWriter(f, cols, extrasaction="ignore")
    w.writeheader()
    w.writerows(rows)
import collections
print(collections.Counter(x["class"] for x in rows))
with open("data/moat/scratch/f_unresolved.txt", "w") as f:
    for x in rows:
        if x["class"] == "UNRESOLVED":
            print(x["row_id"], x["ticker"], label(x["product_member"]), x["geography"].split(":")[-1], x["other_dims"][-60:], x["period_start"], x["period_end"], x["explanation"][:300], x["printed_page"], file=f)
