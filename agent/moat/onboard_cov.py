"""Print the coverage buckets for one onboarded ticker or drug (agent.moat.progress terms).

python -m agent.moat.onboard_cov REGN
python -m agent.moat.onboard_cov drug:dupixent
"""
import json
import sys

from agent.moat import progress

for k in sys.argv[1:]:
    b = progress.onboard_drug_buckets(k[5:]) if k.startswith("drug:") else progress.onboard_buckets(k)
    print(k, json.dumps({x: f"{v['have']}/{v['need']} {v.get('note', '')}".strip() for x, v in b.items()}, indent=1))
