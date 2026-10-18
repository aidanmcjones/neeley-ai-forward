"""Confirm the verified/policy files are in R2."""
from agent.moat.common import store

s = store()
print("store kind", s.kind)
for f in ["policy_exposure.csv", "force_summary.csv", "ira_cut_check.csv", "manufacturing_sites_verified.csv", "definitions.md"]:
    key = f"moat/verified/policy/{f}.gz"
    try:
        body = s.get(key)
        print(key, "OK", len(body) if body else body)
    except Exception as e:  # noqa: BLE001
        print(key, "ERR", type(e).__name__, str(e)[:120])
