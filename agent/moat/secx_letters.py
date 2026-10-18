import re
from agent.moat.secx_lib import *

TOPICS = {"revenue recognition": r"revenue recognition|ASC 606", "gross-to-net": r"gross[- ]to[- ]net|rebate|chargeback|returns",
          "segments": r"segment", "non-GAAP": r"non-?GAAP", "contingencies": r"contingenc|litigation|loss accrual",
          "collaboration": r"collaborat|royalt", "intangibles/impairment": r"impairment|intangible|goodwill",
          "taxes": r"income tax|tax rate|valuation allowance", "acquisitions": r"acquisition|business combination",
          "confidential treatment": r"confidential treatment|redact", "debt/liquidity": r"liquidity|debt|covenant"}


def main():
    rows = []
    for t, cik in ciks().items():
        _, fs = filings(cik, "2019-01-01")
        for f in [x for x in fs if x["form"] in ("CORRESP", "UPLOAD")]:
            url = url_of(cik, f["accession"], f["primary_doc"])
            try:
                raw = sec_get(url)
            except Exception as e:
                note_gap("secx", t, f"letter {f['accession']}", repr(e))
                continue
            text = raw[:400000]
            kws = [k for k, p in TOPICS.items() if re.search(p, text, re.I)]
            rel = f"companies/{t}/sec_letters/{f['filed']}_{f['form']}_{f['accession']}.md"
            save_doc(rel, url, raw, t, "sec_comment_letter", f)
            rows.append({"ticker": t, "date": f["filed"], "form": f["form"], "accession": f["accession"],
                         "topics": ";".join(kws), "url": url, "path": "data/moat/" + rel})
        print(t, sum(1 for r in rows if r["ticker"] == t), flush=True)
        write_csv("tables/sec_comment_letters.csv", ["ticker", "date", "form", "accession", "topics", "url", "path"], rows)


if __name__ == "__main__":
    main()
