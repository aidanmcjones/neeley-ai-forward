"""verified/secx/insider_summary.csv and insider_open_market.csv from data/moat/tables/insider_trades.csv.

Dedupe: (1) exact duplicate rows inside one accession (parser double rows) dropped; (2) the same transaction
(ticker, person, date, code, shares, price, security, A/D) reported in more than one accession is treated as a
Form 4/A restatement and only the latest accession is kept.
Classes by Form 4 transaction code (non-derivative table only for P/S):
  P = open-market or private purchase, S = open-market or private sale, M = option exercise/conversion,
  F = tax withholding / exercise-price payment with shares, A = grant, G = gift, J/D/I = other.
Officer = role is anything other than plain 'Director' (so 'Director; CEO' counts as officer).
No interpretation of motive.
"""
import csv
from collections import defaultdict

from agent.moat.verify.s_write import ai_wrong, out

SRC = "data/moat/tables/insider_trades.csv"
rows = list(csv.DictReader(open(SRC)))
n0 = len(rows)

seen, exact_dup = set(), 0
r1 = []
for r in rows:
    k = tuple(r[c] for c in ("ticker", "person", "date", "code", "shares", "price", "security", "acq_disp",
                             "owned_after", "accession", "derivative"))
    if k in seen:
        exact_dup += 1
        continue
    seen.add(k)
    r1.append(r)

by_txn = defaultdict(set)
for r in r1:
    by_txn[(r["ticker"], r["person"], r["date"], r["code"], r["shares"], r["price"], r["security"], r["acq_disp"])].add(r["accession"])
amend_drop = 0
r2 = []
for r in r1:
    accs = by_txn[(r["ticker"], r["person"], r["date"], r["code"], r["shares"], r["price"], r["security"], r["acq_disp"])]
    if len(accs) > 1 and r["accession"] != max(accs):
        amend_drop += 1
        continue
    r2.append(r)
form4a_urls = sum(1 for r in rows if "form4a" in r["url"].lower() or "4a-" in r["url"].lower())
print("rows", n0, "exact dup dropped", exact_dup, "amendment dup dropped", amend_drop, "kept", len(r2), "4/A-named urls", form4a_urls)


def officer(role):
    return role.strip() not in ("Director", "") and "10%" not in role or ";" in role


def f(x):
    try:
        return float(x)
    except ValueError:
        return 0.0


om = [r for r in r2 if r["code"] in ("P", "S") and r["derivative"] != "Y"]
detail = []
for r in om:
    detail.append(dict(ticker=r["ticker"], person=r["person"], role=r["role"], is_officer="yes" if officer(r["role"]) else "no",
                       date=r["date"], code=r["code"], side="purchase" if r["code"] == "P" else "sale",
                       shares=r["shares"], price=r["price"], value=round(f(r["value"]), 2), accession=r["accession"], url=r["url"]))

tick = sorted({r["ticker"] for r in r2})
summ = []
for t in tick:
    for y in ("2025", "2026"):
        rs = [r for r in r2 if r["ticker"] == t and r["date"].startswith(y)]
        off = [r for r in rs if officer(r["role"]) and r["derivative"] != "Y"]
        buys = [r for r in off if r["code"] == "P"]
        sells = [r for r in off if r["code"] == "S"]
        dbuys = [r for r in rs if not officer(r["role"]) and r["code"] == "P" and r["derivative"] != "Y"]
        dsells = [r for r in rs if not officer(r["role"]) and r["code"] == "S" and r["derivative"] != "Y"]
        m = [r for r in off if r["code"] == "M"]
        fw = [r for r in off if r["code"] == "F"]
        top = sorted(buys + sells, key=lambda r: -f(r["value"]))[:3]
        row = dict(ticker=t, year=y, officer_open_mkt_buys_n=len(buys), officer_buy_value=round(sum(f(r["value"]) for r in buys)),
                   officer_open_mkt_sells_n=len(sells), officer_sell_value=round(sum(f(r["value"]) for r in sells)),
                   officer_net_open_mkt_value=round(sum(f(r["value"]) for r in buys) - sum(f(r["value"]) for r in sells)),
                   officer_net_open_mkt_shares=round(sum(f(r["shares"]) for r in buys) - sum(f(r["shares"]) for r in sells)),
                   officer_option_exercise_rows=len(m), officer_option_exercise_shares=round(sum(f(r["shares"]) for r in m)),
                   officer_tax_withholding_rows=len(fw), officer_tax_withholding_value=round(sum(f(r["value"]) for r in fw)),
                   director_buy_value=round(sum(f(r["value"]) for r in dbuys)), director_sell_value=round(sum(f(r["value"]) for r in dsells)),
                   last_trade_date_in_data=max((r["date"] for r in rs), default=""))
        for i in range(3):
            if i < len(top):
                r = top[i]
                row[f"top{i+1}"] = f"{r['person']} | {r['role']} | {r['date']} | {'buy' if r['code']=='P' else 'sell'} | ${f(r['value']):,.0f} | {r['url']}"
            else:
                row[f"top{i+1}"] = ""
        summ.append(row)

COLS = list(summ[0].keys())
out("insider_summary.csv", COLS, summ, f"derived: {SRC} (SEC Form 4 XML, url column)")
out("insider_open_market.csv", list(detail[0].keys()), detail, f"derived: {SRC}")
for s in summ:
    print(s["ticker"], s["year"], s["officer_open_mkt_buys_n"], s["officer_buy_value"], s["officer_open_mkt_sells_n"],
          s["officer_sell_value"], s["officer_net_open_mkt_value"], s["last_trade_date_in_data"])
    for i in (1, 2, 3):
        if s[f"top{i}"]:
            print("   ", s[f"top{i}"][:140])
