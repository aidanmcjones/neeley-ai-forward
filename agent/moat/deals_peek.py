import json, sys, random
f = sys.argv[1]
n = int(sys.argv[2])
rows = [json.loads(l) for l in open(f)]
random.seed(1)
for r in random.sample(rows, min(n, len(rows))):
    print({k: v for k, v in r.items() if k in ("date", "deal_type", "acquirer_or_licensee", "target_or_licensor", "asset", "stage_at_deal", "upfront_usd_m", "milestones_usd_m", "total_potential_usd_m", "confidence")})
    print("   Q:", r["quote"][:260])
