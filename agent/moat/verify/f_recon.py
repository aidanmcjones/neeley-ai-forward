"""For each restatement row, compare product members reported for the same period/geo/dims in the old vs new filing,
and test whether the change is explained by members moving in or out of the bucket."""
import json, collections, pickle
from agent.moat.verify.f_lib import PANEL, RESTATE

idx = collections.defaultdict(dict)  # (acc, concept, geo, dims, start, end) -> {member: value}
for r in PANEL:
    idx[(r["accession"], r["concept"], r["geography"], r["other_dims"], r["period_start"], r["period_end"])][r["product_member"]] = float(r["value_usd"])

out = []
for i, r in enumerate(RESTATE):
    v = json.loads(r["values_by_accession"])
    pairs = sorted(((a, float(val)) for val, accs in v.items() for a in accs), key=lambda x: x[0])
    res = {"i": i, "pairs": pairs, "steps": []}
    for (a0, v0), (a1, v1) in zip(pairs, pairs[1:]):
        if v0 == v1:
            continue
        k0 = (a0, r["concept"], r["geography"], r["other_dims"], r["period_start"], r["period_end"])
        k1 = (a1,) + k0[1:]
        m0, m1 = idx.get(k0, {}), idx.get(k1, {})
        gone = {m: m0[m] for m in m0 if m not in m1}
        new = {m: m1[m] for m in m1 if m not in m0}
        delta = v1 - v0
        expl = sum(gone.values()) - sum(new.values())
        res["steps"].append({"old": a0, "new": a1, "v0": v0, "v1": v1, "delta": delta, "gone": gone, "new_members": new,
                             "explained": abs(delta - expl) <= max(2e6, 0.02 * abs(delta)) and (gone or new),
                             "n_old": len(m0), "n_new": len(m1)})
    out.append(res)
pickle.dump(out, open("data/moat/scratch/f_recon.pkl", "wb"))
f = open("data/moat/scratch/f_recon.txt", "w")
for res in out:
    r = RESTATE[res["i"]]
    for s in res["steps"]:
        print(res["i"], r["ticker"], r["product_member"].split(":")[-1], r["geography"].split(":")[-1], r["period_start"], r["period_end"],
              f"{s['v0']/1e6:g}->{s['v1']/1e6:g}", "EXPL" if s["explained"] else "noexp",
              "gone=", {k.split(":")[-1]: v / 1e6 for k, v in s["gone"].items()}, "new=", {k.split(":")[-1]: v / 1e6 for k, v in s["new_members"].items()},
              s["n_old"], s["n_new"], s["old"], s["new"], file=f)
