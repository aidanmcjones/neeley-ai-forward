import json, gzip, os
from agent.tenk import Store
import boto3
s = Store()
print(s.bucket, s.kind)
r = s.get("index/8k_0000078003.jsonl")
print(r[:800] if r else None)
# list keys in neeley bucket index/
resp = s.s3.list_objects_v2(Bucket=s.bucket, Prefix="index/")
print([o["Key"] for o in resp.get("Contents", [])][:30])
# catalyst bucket
c = boto3.client("s3", endpoint_url=s.s3.meta.endpoint_url, aws_access_key_id=os.environ["R2_ACCESS_KEY_ID"],
                 aws_secret_access_key=os.environ["R2_SECRET_ACCESS_KEY"], region_name="auto")
for p in ["10k/date=2024-01", "10k/date=2026-0", "8k/"]:
    try:
        rr = c.list_objects_v2(Bucket="catalyst-lab-archive", Prefix=p, MaxKeys=5)
        print(p, rr.get("KeyCount"), [o["Key"] for o in rr.get("Contents", [])])
    except Exception as e:
        print(p, "ERR", e)
