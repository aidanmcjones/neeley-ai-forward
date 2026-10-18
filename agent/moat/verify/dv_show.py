"""Print sampled deal rows for hand review: python -m agent.moat.verify.dv_show <start> <count> [full|quote]"""
import json
import sys

from agent.moat.verify.dv_lib import WORK, norm

rows = [json.loads(l) for l in open(WORK / "sample.jsonl")]
core = [r for r in rows if set(r["why"]) - {"bench_n_lt_10", "pr24"}]
extra = [r for r in rows if not set(r["why"]) - {"bench_n_lt_10", "pr24"}]
seq = core + extra
a, n = int(sys.argv[1]), int(sys.argv[2])
mode = sys.argv[3] if len(sys.argv) > 3 else "full"
for o in seq[a:a + n]:
    r = o["row"]
    nm = {k: v for k, v in o["num"].items() if v not in ("on_page", "blank")}
    print(f"## {r['deal_id']} {r['date']} {r['deal_type']} st={r['stage_at_deal']} ta={r['therapeutic_area']} conf={r['confidence']} "
          f"{r['origin']} | LIC/ACQ={r['acquirer_or_licensee']} | LOR/TGT={r['target_or_licensor']} | up={r['upfront_usd_m']} ms={r['milestones_usd_m']} "
          f"tot={r['total_potential_usd_m']} | roy={(r['royalty_terms'] or '')[:90]} | qpage={o['quote_on_page']} {nm or ''} {','.join(o['why'])}")
    q = norm(r["quote"])
    if mode == "full":
        c = o["ctx"]
        i = c.find(q[:60])
        print("   CTX:", c[max(0, i - 120): i + 480] if i >= 0 else c[:600])
    else:
        print("   Q:", q)
print(len(core), len(extra))
