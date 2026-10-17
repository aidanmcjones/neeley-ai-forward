import csv
import io
import bisect
from collections import defaultdict
from agent.moat.common import write, note_gap, ROOT

ADR = {"ROCHE": "RHHBY", "Roche": "RHHBY"}
SKIP_TYPES = {"drug_reference_data", "fda_label", "transcript", "doc_type"}


def main():
    px = defaultdict(dict)
    with open(ROOT / "data/moat/tables/prices_daily.csv") as f:
        for r in csv.DictReader(f):
            px[r["ticker"]][r["date"]] = float(r["adj_close"])
    dates = {t: sorted(d) for t, d in px.items()}
    bench = px["XLV"]

    def cum(t, d_idx_a, d_idx_b, ds):
        """return of ticker t from close at index a to close at index b."""
        return px[t][ds[d_idx_b]] / px[t][ds[d_idx_a]] - 1

    rows = []
    n_skip = 0
    with open(ROOT / "data/corpus/manifest.csv") as f:
        for m in csv.DictReader(f):
            if m["doc_type"] in SKIP_TYPES or not m["filed"]:
                n_skip += 1
                continue
            t = ADR.get(m["ticker"], m["ticker"])
            if t not in px or not m["filed"] >= "2020-01-01":
                n_skip += 1
                continue
            ds = dates["XLV"]
            i0 = bisect.bisect_left(ds, m["filed"])
            if i0 < 2 or i0 + 5 >= len(ds):
                n_skip += 1
                continue
            if not all(ds[k] in px[t] for k in (i0 - 2, i0 - 1, i0, i0 + 1, i0 + 5)):
                n_skip += 1
                continue

            def ab(a, b):
                return cum(t, a, b, ds) - cum("XLV", a, b, ds)

            vol = None
            rows.append([m["doc_id"], m["ticker"], m["doc_type"], m["form"], m["period"], m["filed"], ds[i0],
                         round(ab(i0 - 1, i0), 5), round(ab(i0, i0 + 1), 5) if False else round(ab(i0 - 1, i0 + 1), 5),
                         round(ab(i0 - 2, i0 + 5), 5), round(cum(t, i0 - 1, i0, ds), 5), "tiingo+manifest",
                         m["doc_id"]])
    # 8-K earnings dates from SEC submissions
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["doc_id", "ticker", "doc_type", "form", "period", "filed", "day0_date", "abn_day0", "abn_0_to_1",
                "abn_m1_to_5", "raw_day0", "source", "source_row"])
    w.writerows(rows)
    write("market", "tables/event_returns.csv", buf.getvalue(), group="market", doc_type="table",
          source_url="data/corpus/manifest.csv + tiingo")
    print(len(rows), "skipped", n_skip)


main()
