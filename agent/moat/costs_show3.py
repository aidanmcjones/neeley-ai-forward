import json
seen = set()
for r in json.load(open("data/moat/scratch/costs_price.json")):
    if r["kind"] == "authorized_generic" and "10k" in r["file"] or r["kind"] == "authorized_generic" and "transcript" in r["file"]:
        key = r["text"][100:160]
        if key in seen:
            continue
        seen.add(key)
        print(r["file"].replace("data/", ""), "p" + r["page"], "|", r["text"][:480])
