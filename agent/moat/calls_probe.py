import sys, requests
from agent.corpus import html_to_text
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/141.0 Safari/537.36"
for i, u in enumerate(sys.argv[1:]):
    try:
        r = requests.get(u, headers={"User-Agent": UA}, timeout=60)
        t = html_to_text(r.text) if r.status_code == 200 else ""
        open(f"/tmp/gd/p{i}.txt", "w").write(t)
        print(r.status_code, len(t), u)
    except Exception as e:
        print("ERR", u, e)
