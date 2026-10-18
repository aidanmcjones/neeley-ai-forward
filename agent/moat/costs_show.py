import json
import sys
kind = sys.argv[1]
for r in json.load(open("data/moat/scratch/costs_mine.json")):
    if r["kind"] == kind:
        print(r["file"].replace("data/", "").replace("/companies", ""), "p" + str(r["page"]), "|", r["text"][:300])
