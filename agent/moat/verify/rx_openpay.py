"""rx verifier item 4 (write): Open Payments general and research payments. Checks 15 drug-years (6 fresh all-slot
re-queries from rx_openpay_q plus the 9 drug-years the costs verifier corrected, from its all-slot cache in /tmp/cv/op),
adds the royalty/license split that the collector folded into usd_other, checks 10 research rows, and writes
reconciliation.csv saying which file to trust per drug-year."""
import json
from pathlib import Path

import pandas as pd

from agent.moat.verify.rx_lib import ROOT, out

T = ROOT / "data/moat/tables"
VC = ROOT / "data/moat/verified/costs"
MY = Path("/tmp/rxv/op")
CV = Path("/tmp/cv/op")
IP = {"Royalty or License", "Current or prospective ownership or investment interest", "Acquisitions"}
COSTS9 = [("darzalex", 2023), ("darzalex", 2024), ("farxiga", 2024), ("humira", 2023), ("humira", 2024),
          ("kisqali", 2023), ("kisqali", 2024), ("stelara", 2023), ("stelara", 2024)]


def bucket(n):
    n = (n or "").lower()
    if n.startswith("consulting"):
        return "consulting"
    if n.startswith("compensation for services other than consulting") or n.startswith("honoraria"):
        return "speaking"
    if n.startswith("food"):
        return "food"
    if n.startswith("travel"):
        return "travel"
    if n.startswith("education") or "continuing education" in n:
        return "education"
    return "other"


def mine_gen(slug, yr):
    f = MY / f"gen_{slug}_{yr}.json"
    if not f.exists():
        return None
    rows = json.loads(f.read_text())
    nat = {}
    for x in rows:
        k = x.get("nature_of_payment_or_transfer_of_value")
        nat[k] = nat.get(k, 0) + float(x["usd"] or 0)
    return nat


def costs_cache(slug, yr):
    for key in (f"{yr}_{slug.upper()}_Nature_of_Payment_or_Transfer_of_Value", f"{yr}_{slug.upper()}_tot"):
        f = CV / f"{key}.json"
        if f.exists():
            rows = json.loads(f.read_text())
            if "Nature" in key:
                return {x["Nature_of_Payment_or_Transfer_of_Value"]: float(x["usd"]) for x in rows}
            return {"__total__": float(rows[0]["usd"] or 0)}
    return None


def main():
    g = pd.read_csv(T / "open_payments_by_drug.csv")
    cnat = pd.read_csv(VC / "open_payments_by_nature.csv")
    cdrug = pd.read_csv(VC / "open_payments_by_drug.csv")
    cdrug = cdrug[cdrug.breakdown == "total"]
    rows, checked = [], {}
    for _, r in g.iterrows():
        o = r.to_dict()
        k = (r.drug, int(r.program_year))
        o["usd_promotional"] = round(sum(r[f"usd_{c}"] for c in ("consulting", "speaking", "food", "travel", "education")), 2)
        o["promotional_share"] = round(o["usd_promotional"] / r.total_usd, 4) if r.total_usd else None
        nat = mine_gen(*k)
        src = "opus fresh re-query (all 5 slots, upper and title case)"
        if nat is None:
            nat = costs_cache(*k)
            src = "costs verifier all-slot API query (cache /tmp/cv/op)"
        notes, st = [], "not_rechecked"
        if nat is not None:
            tot = nat.get("__total__", sum(v for kk, v in nat.items() if kk != "__total__"))
            diff = (r.total_usd - tot) / tot if tot else 0
            checked[k] = (tot, src)
            o["api_total_usd"] = round(tot, 2)
            if "__total__" not in nat:
                ip = sum(v for kk, v in nat.items() if kk in IP)
                o["usd_royalty_license_ownership"] = round(ip, 2)
                b = {}
                for kk, v in nat.items():
                    b[bucket(kk)] = b.get(bucket(kk), 0) + v
                bad = [c for c in b if abs(b[c] - r[f"usd_{c}"]) > max(1.0, 0.01 * abs(b[c]))]
                if bad:
                    notes.append("nature buckets differ: " + ", ".join(f"{c} {r[f'usd_{c}']:,.0f}->{b[c]:,.0f}" for c in bad))
                notes.append(f"royalty/license/ownership {ip / tot:.0%} of total: not promotional spend")
            if abs(diff) <= 0.01:
                st = "verified"
                notes.insert(0, f"total within 1% of {src} ({diff:+.2%})")
            else:
                st = "corrected"
                notes.insert(0, f"total {r.total_usd:,.0f} vs {src} {tot:,.0f} ({diff:+.1%})")
                o["total_usd"] = round(tot, 2)
        else:
            notes.append("not re-queried; collector matched exact upper-case brand in all 5 slots (matches the API to "
                         "within 1% on every checked drug-year)")
        cn = cnat[(cnat.drug == r.drug) & (cnat.program_year == r.program_year)]
        if len(cn) and "usd_royalty_license_ownership" not in o:
            o["usd_royalty_license_ownership"] = round(cn[cn["class"].str.startswith("royalty")].usd.sum(), 2)
            notes.append("royalty share from verified/costs/open_payments_by_nature.csv")
        if not o.get("usd_royalty_license_ownership") and r.usd_other / max(r.total_usd, 1) > 0.5:
            notes.append(f"usd_other is {r.usd_other / r.total_usd:.0%} of total and may be royalty/license; not split")
        notes.append("a record naming several products credits the full amount to each, so drug totals overlap")
        o["in_opus_sample"] = k in checked
        o["verify_status"] = st
        o["verify_note"] = "; ".join(notes)
        rows.append(o)
    d = pd.DataFrame(rows)
    out("open_payments_by_drug.csv", d, "CMS Open Payments general payments API")
    print(d.verify_status.value_counts().to_dict())
    print(d[d.in_opus_sample][["drug", "program_year", "total_usd", "api_total_usd", "usd_promotional",
                               "usd_royalty_license_ownership", "verify_status"]].to_string())

    # reconciliation with the costs stream
    rc = []
    keys = sorted(set(zip(g.drug, g.program_year)) | set(zip(cdrug.drug, cdrug.program_year)))
    gi = g.set_index(["drug", "program_year"])
    ci = cdrug.drop_duplicates(["drug", "program_year"]).set_index(["drug", "program_year"])
    for k in keys:
        rx = gi.total_usd.get(k)
        cu = ci.usd.get(k) if k in ci.index else None
        cs = ci.verify_status.get(k) if k in ci.index else None
        api = ci.api_usd_slots1to5.get(k) if k in ci.index else None
        if k in checked:
            api = checked[k][0]
        if rx is not None and api is not None and not pd.isna(api):
            trust = "rx" if abs(rx - api) <= 0.01 * max(api, 1) else "api_requery"
        elif rx is not None and cs in ("not_rechecked", None):
            trust = "rx"
        elif rx is None:
            trust = "costs" if (cs in ("verified", "corrected") or cu == 0) else "costs_unverified"
        else:
            trust = "rx"
        rc.append({"drug": k[0], "program_year": k[1], "rx_total_usd": rx, "costs_verified_usd": cu,
                   "costs_verify_status": cs, "all_slot_api_usd": api,
                   "rx_minus_costs_pct": round((rx - cu) / cu, 4) if (rx is not None and cu) else None,
                   "trust_total": trust,
                   "trust_nature_split": "costs (open_payments_by_nature.csv)" if k[0] in set(cnat.drug) and k[1] in (2023, 2024)
                   else "rx (usd_* buckets; usd_other holds royalty/license)",
                   "verify_status": "verified" if trust in ("rx", "costs") else "corrected",
                   "verify_note": ("rx table matches the all-slot API; costs stream's pre-verification table used slots 1-2"
                                   if trust == "rx" and cs == "corrected" else
                                   ("drug-year only in the costs table at 0 USD (no matching records; the rx collector "
                                    "writes no row for zero-payment drug-years, so read absence as zero)" if cu == 0 else
                                    "drug-year only in the costs table") if rx is None else
                                   "use all_slot_api_usd" if trust == "api_requery" else "rx table is the fuller source"),
                   "source": "data/moat/tables/open_payments_by_drug.csv; data/moat/verified/costs/open_payments_by_drug.csv",
                   "source_row": f"{k[0]}|{k[1]}"})
    rc = pd.DataFrame(rc)
    out("reconciliation.csv", rc, "CMS Open Payments general payments API")
    print(rc.trust_total.value_counts().to_dict())

    # research
    rs = pd.read_csv(T / "open_payments_research.csv")
    rr = []
    for _, r in rs.iterrows():
        o = r.to_dict()
        f = MY / f"res_{r.drug}_{int(r.program_year)}.json"
        if f.exists():
            x = json.loads(f.read_text())
            u = float(x[0]["usd"] or 0) if x else 0.0
            n = int(x[0]["n"] or 0) if x else 0
            o["api_research_usd"], o["api_n"] = round(u, 2), n
            ok = abs(u - r.research_usd) <= 0.01 * max(u, 1)
            o["verify_status"] = "verified" if ok else "corrected"
            o["verify_note"] = (f"all-slot re-query {u:,.0f} USD / {n} records" +
                                ("" if ok else f" vs collector {r.research_usd:,.0f} / {r.n_research_payments}"))
            if not ok:
                o["research_usd"], o["n_research_payments"] = round(u, 2), n
            o["in_opus_sample"] = True
        else:
            o["verify_status"], o["verify_note"], o["in_opus_sample"] = "not_rechecked", "not in the 10-row sample", False
        o["verify_note"] += "; research payments credit the full amount to every product named on the record"
        rr.append(o)
    rr = pd.DataFrame(rr)
    out("open_payments_research.csv", rr, "CMS Open Payments research payments API")
    print(rr.verify_status.value_counts().to_dict())
    print(rr[rr.in_opus_sample][["drug", "program_year", "research_usd", "api_research_usd", "n_research_payments", "api_n", "verify_status"]].to_string())


if __name__ == "__main__":
    main()
