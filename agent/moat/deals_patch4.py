p = 'agent/moat/deals_build.py'
s = open(p).read()
s = s.replace('''    if r["date"] < "2020-01-01":
        continue''', '''    if r["date"] < "2020-01-01" or r["date"] > "2026-10-17":
        continue
    if r["origin"] == "10k_note":
        r["stage_at_deal"] = stage_of(r.get("quote") or "")''')
s = s.replace("from agent.moat.deals_lib import amounts, sentences", "from agent.moat.deals_lib import amounts, sentences, stage_of")
s = s.replace('''        if 0.3 <= m <= 60:''', '''        if 0.3 <= m <= 60 and abs(m - 1) > 0.03 and abs(v - r["total_potential_usd_m"]) > 0.5:''')
# drop per-row multiples from the benchmark table: keep the aggregate only
a = s.index("for r, v, m, s in mult:\n    out.append")
b = s.index("if mult:\n    ms_")
s = s[:a] + s[b:]
s = s.replace('acq = [r for r in kept if r["deal_type"] == "acquisition" and r.get("total_potential_usd_m")]',
              'acq = [r for r in kept if r["deal_type"] == "acquisition" and r.get("total_potential_usd_m") and r["origin"].split("+")[0] != "10k_note"]')
s = s.replace('''    row_ids=" ".join(r["deal_id"] for r, _, _, _ in mult)))''', '''    row_ids=" ".join(f"{r['deal_id']}(price {r['total_potential_usd_m']:.0f}m/rev {v:.0f}m)" for r, v, _, _ in mult)))''')
open(p, 'w').write(s)
