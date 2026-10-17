import os, json
import agent.tenk as t
t.MIN_INTERVAL=0.3
print(bool(os.environ.get("SEC_USER_AGENT")), os.environ.get("R2_BUCKET"))
u='https://efts.sec.gov/LATEST/search-index?q=%22upfront%20payment%22%20%22license%20agreement%22&forms=8-K&dateRange=custom&startdt=2024-01-01&enddt=2024-01-31'
try:
    j=t.sec_get(u,as_json=True)
    print(j['hits']['total'], len(j['hits']['hits']))
    print(json.dumps(j['hits']['hits'][0])[:1500])
except Exception as e: print('ERR',e)
