p='agent/moat/deals_fetch.py'; s=open(p).read()
s=s.replace("for acc, h in sorted(hits.items(), key=lambda kv: kv[1][\"date\"]):\n    if acc in done:\n        continue",
"for acc, h in sorted(hits.items(), key=lambda kv: kv[1][\"date\"], reverse=(len(sys.argv) > 1)):\n    if acc in done or (OUT / 'deals' / f\"{h['date']}_{acc}.md\").exists():\n        continue")
s=s.replace("[:3] or docs[:1]","[:2] or docs[:1]")
open(p,'w').write(s)
