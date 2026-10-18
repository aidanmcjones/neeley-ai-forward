import json
from agent.moat.verify.f_lib import RESTATE, ACC_FORM, ACC_PERIOD, acc_doc

out = open("data/moat/scratch/f_restate_dump.txt", "w")
for i, r in enumerate(RESTATE):
    v = json.loads(r["values_by_accession"])
    parts = []
    for val, accs in sorted(v.items(), key=lambda kv: min(kv[1])):
        for a in accs:
            parts.append(f"{float(val)/1e6:g}@{ACC_FORM.get(a,'?')}:{ACC_PERIOD.get(a,'?')}:{(acc_doc(a) or '-').split('/')[-1]}")
    print(i, r["ticker"], r["concept"].split(":")[1][:12], r["product_member"].split(":")[-1], r["geography"].split(":")[-1],
          r["other_dims"].replace('"', "")[-50:], r["period_start"], r["period_end"], r["pct_diff"], " | ".join(parts), file=out)
