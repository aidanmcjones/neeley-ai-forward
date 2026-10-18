"""I/B/E/S consensus for the onboarded companies (NVS, REGN, VRTX), one WRDS connection (one Duo push).

Writes data/moat/onboard/<T>/ibes_<table>.csv for the six tables in ibes.QUERIES (price targets skipped).
Run:  PYTHONPATH=. python -m agent.moat.ibes_onboard
"""
import psycopg2

from agent.moat import ibes
from agent.moat.common import write

ONBOARD = ["NVS", "REGN", "VRTX"]
SKIP = {"ibes_price_targets"}


def main():
    conn = psycopg2.connect(host="wrds-pgdata.wharton.upenn.edu", port=9737, dbname="wrds", user=ibes.wrds_username(),
                            sslmode="require", connect_timeout=120)
    print("connected to WRDS", flush=True)
    cur = conn.cursor()
    cur.execute("select distinct ticker, oftic, cname, cusip, usfirm, sdates from ibes.idsum "
                "where oftic in %s or cname ilike 'NOVARTIS%%' order by 1", (tuple(ONBOARD),))
    for r in cur:
        print("idsum", r, flush=True)
    cur.close()
    for t in ONBOARD:
        for name, (table, sql, keys) in ibes.QUERIES.items():
            if name in SKIP:
                continue
            cur = conn.cursor()
            try:
                cur.execute(sql, ((t,),) if sql.count("%s") == 1 else ((t,), ibes.SINCE))
                text, n = ibes.to_csv(cur, table, keys)
                write(f"onboard_{t}", f"onboard/{t}/{name}.csv", text, ticker=t, group="market",
                      doc_type="consensus_table", source_url=f"WRDS {table}", quality="licensed_wrds")
                print(f"{t} {name}: {n} rows", flush=True)
            except Exception as e:
                conn.rollback()
                print(f"{t} {name}: FAILED {type(e).__name__}: {str(e)[:200]}", flush=True)
            finally:
                cur.close()
    conn.close()


if __name__ == "__main__":
    main()
