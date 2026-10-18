import time
import requests
D = "b7678d15-1cac-51b6-9c8f-4b36d4f8f21f"
N = "Name_of_Drug_or_Biological_or_Device_or_Medical_Supply_{}"
for k in (1, 2, 5):
    body = {"properties": [{"expression": {"operator": "sum", "operands": ["Total_Amount_of_Payment_USDollars"]}, "alias": "usd"}],
            "conditions": [{"groupOperator": "or", "conditions": [{"property": N.format(i), "value": "WEZLANA", "operator": "="} for i in range(1, k + 1)]}],
            "limit": 5, "count": False, "results": True, "schema": False, "keys": True, "format": "json"}
    t = time.time()
    try:
        r = requests.post(f"https://openpaymentsdata.cms.gov/api/1/datastore/query/{D}", json=body, timeout=120)
        print(k, r.status_code, round(time.time() - t, 1), r.text[:100], flush=True)
    except Exception as e:
        print(k, "ERR", round(time.time() - t, 1), e, flush=True)
