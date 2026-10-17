"""I/B/E/S consensus for the 10 shortlist companies, from TCU's WRDS (stream `ibes`).

Answers "is it priced in?": what the Street expects for revenue and EPS (FY1 to FY3), how that changed month by
month, recommendations, price targets and the surprise history. Every row keeps the WRDS table and its key columns
as `source` / `source_row`, so a slide can cite "I/B/E/S consensus via WRDS, statperiod 2026-09-17".

Auth: libpq reads the password from ~/.pgpass (never read here); WRDS sends a Duo push on connect.
Run:  python -m agent.moat.ibes
"""

import csv
import io
from pathlib import Path

import psycopg2

from agent.moat.common import write

TICKERS = ["MRK", "BMY", "PFE", "LLY", "NVO", "ABBV", "JNJ", "AZN", "AMGN", "GILD"]
SINCE = "2023-01-01"


def wrds_username():
    for line in (Path.home() / ".pgpass").read_text().splitlines():
        if "wrds" in line and not line.startswith("#"):
            return line.split(":")[3]
    raise RuntimeError("no wrds line in ~/.pgpass")


def to_csv(cur, table, keys):
    cols = [d[0] for d in cur.description]
    out = io.StringIO()
    w = csv.writer(out)
    w.writerow(cols + ["source", "source_row"])
    n = 0
    for row in cur:
        rec = dict(zip(cols, row))
        w.writerow(list(row) + [f"WRDS {table}", "|".join(f"{k}={rec.get(k)}" for k in keys)])
        n += 1
    return out.getvalue(), n


QUERIES = {
    # IBES ticker map: official ticker (oftic) -> IBES ticker, so ADRs and renamed tickers resolve
    "ibes_ids": ("ibes.idsum",
                 "select distinct ticker, oftic, cname, cusip, sdates from ibes.idsum where oftic in %s and usfirm in (0, 1)",
                 ["ticker", "oftic", "sdates"]),
    # EPS consensus, annual periods FY1 to FY3 (fpi 1 to 3), monthly snapshots
    "ibes_eps_consensus": ("ibes.statsum_epsus",
                           "select s.ticker, s.oftic, s.statpers, s.fpi, s.fpedats, s.measure, s.numest, s.meanest, "
                           "s.medest, s.stdev, s.highest, s.lowest, s.actual, s.curcode from ibes.statsum_epsus s "
                           "where s.oftic in %s and s.fpi in ('1','2','3') and s.statpers >= %s",
                           ["ticker", "statpers", "fpi", "fpedats"]),
    # Revenue and other non-EPS measures (SAL = sales/revenue, EBT, NET, GPS), annual FY1 to FY3
    "ibes_revenue_consensus": ("ibes.statsum_xepsus",
                               "select s.ticker, s.oftic, s.statpers, s.fpi, s.fpedats, s.measure, s.numest, s.meanest, "
                               "s.medest, s.stdev, s.highest, s.lowest, s.actual, s.curcode from ibes.statsum_xepsus s "
                               "where s.oftic in %s and s.fpi in ('1','2','3') and s.measure in ('SAL','EBT','NET','GPS') "
                               "and s.statpers >= %s",
                               ["ticker", "statpers", "fpi", "measure", "fpedats"]),
    # Quarterly EPS consensus (fpi 6 to 8 = next three quarters) for surprise context
    "ibes_eps_quarterly": ("ibes.statsum_epsus",
                           "select s.ticker, s.oftic, s.statpers, s.fpi, s.fpedats, s.numest, s.meanest, s.medest, "
                           "s.highest, s.lowest from ibes.statsum_epsus s where s.oftic in %s and s.fpi in ('6','7','8') "
                           "and s.statpers >= %s",
                           ["ticker", "statpers", "fpi", "fpedats"]),
    # Reported actuals (EPS and revenue) with announcement dates
    "ibes_actuals": ("ibes.act_epsus",
                     "select a.ticker, a.oftic, a.pends, a.pdicity, a.measure, a.value, a.anndats, a.curr_act "
                     "from ibes.act_epsus a where a.oftic in %s and a.pends >= %s",
                     ["ticker", "pends", "pdicity", "measure"]),
    # Recommendation summary (1 = strong buy ... 5 = sell)
    "ibes_recommendations": ("ibes.recdsum",
                             "select r.ticker, r.oftic, r.statpers, r.meanrec, r.medrec, r.numrec, r.buypct, "
                             "r.holdpct, r.sellpct, r.numup, r.numdown from ibes.recdsum r where r.oftic in %s "
                             "and r.statpers >= %s",
                             ["ticker", "statpers"]),
    # Price target summary
    "ibes_price_targets": ("ibes.ptgsumu",
                           "select p.ticker, p.statpers, p.horizon, p.estcur, p.numest, p.meanptg, p.medptg, "
                           "p.highptg, p.lowptg from ibes.ptgsumu p join (select distinct ticker from ibes.idsum "
                           "where oftic in %s) i on i.ticker = p.ticker where p.statpers >= %s",
                           ["ticker", "statpers", "horizon"]),
}


def main():
    conn = psycopg2.connect(host="wrds-pgdata.wharton.upenn.edu", port=9737, dbname="wrds", user=wrds_username(),
                            sslmode="require", connect_timeout=120)
    print("connected to WRDS", flush=True)
    tick = tuple(TICKERS)
    for name, (table, sql, keys) in QUERIES.items():
        cur = conn.cursor()
        try:
            cur.execute(sql, (tick,) if "%s" in sql and sql.count("%s") == 1 else (tick, SINCE))
            text, n = to_csv(cur, table, keys)
            write("ibes", f"tables/{name}.csv", text, group="market", doc_type="consensus_table",
                  source_url=f"WRDS {table}", quality="licensed_wrds")
            print(f"{name}: {n} rows", flush=True)
        except Exception as e:
            conn.rollback()
            print(f"{name}: FAILED {type(e).__name__}: {str(e)[:200]}", flush=True)
        finally:
            cur.close()
    conn.close()


if __name__ == "__main__":
    main()
