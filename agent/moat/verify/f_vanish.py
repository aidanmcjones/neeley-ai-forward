"""Products quietly no longer broken out: members that a filing reports and the next filing drops, even for the
comparative period the earlier filing already reported (so it is a presentation choice, not zero sales)."""
import csv, json, collections, re
from agent.moat.verify.f_lib import PANEL, acc_doc, find_value

SUBS = json.load(open("data/moat/scratch/f_subs.json"))
REV = re.compile(r"Revenue")
SKIP = re.compile(r"Other|AllOther|Total|ProductMember$|ServiceMember$|Segment|Collaborat|Alliance|Royalt|Net(product)?sales|Hedg|ProductsAndServices", re.I)

data = collections.defaultdict(lambda: collections.defaultdict(dict))  # ticker -> acc -> {(member_l, start, end, geo): (value, member)}
for r in PANEL:
    if not REV.search(r["concept"]) or not r["product_member"] or ";" in r["product_member"]:
        continue
    k = (r["product_member"].lower(), r["period_start"], r["period_end"], r["geography"])
    data[r["ticker"]][r["accession"]].setdefault(k, (float(r["value_usd"]), r["product_member"]))


def label(m):
    return re.sub(r"(?<=[a-z])(?=[A-Z])", " ", re.sub(r"Member$", "", m.split(":")[-1]))


out = []
for t, by_acc in data.items():
    accs = sorted(by_acc, key=lambda a: SUBS.get(a, {}).get("filed", ""))
    members = collections.defaultdict(list)
    for a in accs:
        for (m, s, e, g), (v, mm) in by_acc[a].items():
            members[m].append(a)
    for m, seen in members.items():
        if SKIP.search(m.split(":")[-1]):
            continue
        last = max(seen, key=lambda a: SUBS.get(a, {}).get("filed", ""))
        later = [a for a in accs if SUBS.get(a, {}).get("filed", "") > SUBS.get(last, {}).get("filed", "")]
        if not later:
            continue
        # comparative periods: periods for m in `last` that a later filing also reports (for any member)
        mrows = {(s, e, g): v for (mm, s, e, g), (v, _) in by_acc[last].items() if mm == m}
        overlap, nxt = {}, None
        for cand in later:
            nper = {(s, e, g) for (_, s, e, g) in by_acc[cand]}
            overlap = {k: v for k, v in mrows.items() if k in nper and abs(v) >= 1e6}
            if overlap:
                nxt = cand
                break
        if not overlap:
            continue
        # rename check: another member in nxt with same value for same period and not in last
        newm = {mm for (mm, s, e, g) in by_acc[nxt]} - {mm for (mm, s, e, g) in by_acc[last]}
        renamed = None
        for (s, e, g), v in overlap.items():
            for (mm, s2, e2, g2), (v2, orig) in by_acc[nxt].items():
                if mm in newm and (s2, e2, g2) == (s, e, g) and abs(v2 - v) < 1.5e6:
                    renamed = orig
        if renamed:
            continue
        # where did it go: buckets in nxt whose value for the same period rose by about v
        best = max(overlap.items(), key=lambda kv: (kv[0][1] - kv[0][0] if False else 0, kv[0][2] == "", kv[0][1], abs(kv[1])))
        (s, e, g), v = best
        dest = []
        for (mm, s2, e2, g2), (v2, orig) in by_acc[nxt].items():
            if (s2, e2, g2) != (s, e, g):
                continue
            old = by_acc[last].get((mm, s, e, g))
            if old and abs((v2 - old[0]) - v) <= max(3e6, 0.05 * abs(v)):
                dest.append(orig)
        if not dest:
            rises = []
            for (mm, s2, e2, g2), (v2, orig) in by_acc[nxt].items():
                if (s2, e2, g2) == (s, e, g) and re.search(r"other", mm.split(":")[-1]):
                    old = by_acc[last].get((mm, s, e, g))
                    if old and v2 - old[0] > 1e6:
                        rises.append(f"{orig} +{(v2 - old[0]) / 1e6:,.0f}M")
                    elif not old:
                        rises.append(f"{orig} (new bucket {v2 / 1e6:,.0f}M)")
            if rises:
                dest = ["group: " + "; ".join(rises)]
        dfirst = min(seen, key=lambda a: SUBS.get(a, {}).get("filed", ""))
        orig_m = next(o for (mm, *_), (_, o) in by_acc[last].items() if mm == m)
        dl, dn = acc_doc(last), acc_doc(nxt)
        pg_last = ";".join(f"p{p}/printed {pr}" for p, pr in find_value(dl, v, near=re.escape(label(orig_m).split()[0]))[:2]) if dl else ""
        pg_next = ""
        if dn and dest and not dest[0].startswith("group"):
            dv = by_acc[nxt][(dest[0].lower(), s, e, g)][0]
            pg_next = ";".join(f"p{p}/printed {pr}" for p, pr in find_value(dn, dv, near="Other|All other")[:2])
        sl, sn, sf = SUBS.get(last, {}), SUBS.get(nxt, {}), SUBS.get(dfirst, {})
        out.append({"ticker": t, "product_member": orig_m, "product": label(orig_m),
                    "first_filing": f"{sf.get('form')} filed {sf.get('filed')} ({dfirst})",
                    "last_filing": f"{sl.get('form')} filed {sl.get('filed')} ({last})",
                    "first_filing_without": f"{sn.get('form')} filed {sn.get('filed')} ({nxt})",
                    "comparative_period": f"{s}..{e}", "geography": g or "total", "value_last_reported_usd": v,
                    "folded_into": ";".join(dest) or "not reconciled", "evidence": (
                        f"{label(orig_m)} printed {v/1e6:,.0f}M for {s}..{e} in the {sl.get('form')} filed {sl.get('filed')}; the next filing "
                        f"({sn.get('form')} {sn.get('filed')}) reports the same period without it"
                        + (f", and {', '.join(label(d) for d in dest)} rose by about that amount" if dest else "")),
                    "citation_last": f"{dl or 'no page-marked copy'} {pg_last}", "citation_without": f"{dn or 'no page-marked copy'} {pg_next}",
                    "n_filings_with": len(set(seen))})
out.sort(key=lambda r: (r["ticker"], -abs(r["value_last_reported_usd"])))
cols = list(out[0].keys())
with open("data/moat/scratch/discontinued_breakouts.csv", "w") as f:
    w = csv.DictWriter(f, cols)
    w.writeheader()
    w.writerows(out)
print(len(out), collections.Counter(r["ticker"] for r in out), sum(1 for r in out if r["folded_into"] != "not reconciled"))
