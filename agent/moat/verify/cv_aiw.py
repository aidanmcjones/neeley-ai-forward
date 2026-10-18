"""Costs verifier: add the ratio-scope entries to ai_wrong.jsonl and drop duplicate costs-stream entries left by
reruns (keeps the last entry per table+row_key; other streams untouched)."""
import json

from agent.moat.verify.pe_lib import AIW

ADD = [
    {"stream": "costs", "table": "company_cost_structure.csv (ratio summary)", "row_key": "AZN sga/revenue FY2021-25",
     "what_the_ai_said": "AZN SG&A/revenue 33.9 to 41.9% (includes distribution)",
     "what_the_source_says": "ifrs-full:SellingGeneralAndAdministrativeExpense excludes distribution costs (separate DistributionCosts "
                             "line, 446 to 579M); the reported line instead includes intangible amortisation that AZN strips from Core "
                             "SG&A (Q4 2025 reported 5,492M vs Core 4,453M)",
     "error_type": "scope_mislabel", "severity": "medium", "how_caught": "companyfacts DistributionCosts tag + AZN FY2025 results 6-K",
     "count": 5, "example_source": "data/corpus/companies/AZN/6k/2026-02-10_a3234s.md"},
    {"stream": "costs", "table": "company_cost_structure.csv (ratio summary)", "row_key": "NVO sga/revenue",
     "what_the_ai_said": "NVO SG&A not tagged, no ratio",
     "what_the_source_says": "sales and distribution costs are on the 20-F income statement (DKK 37,008m FY2021 to 64,310m FY2025, "
                             "untagged); with administrative costs the SG&A-equivalent is 29.2% (FY2021) to 22.7% (FY2025) of sales",
     "error_type": "missed_data", "severity": "low", "how_caught": "read NVO 20-F income statements", "count": 5,
     "example_source": "data/moat/companies/NVO/20f_FY2023_d2.md p.50"},
]


def main(extra=()):
    lines = [json.loads(x) for x in AIW.read_text().splitlines() if x.strip()]
    lines += list(ADD) + list(extra)
    out, seen = [], {}
    for e in lines:
        if e.get("stream") == "costs":
            seen[(e["table"], e["row_key"])] = e
    done = set()
    for e in lines:
        if e.get("stream") != "costs":
            out.append(e)
            continue
        k = (e["table"], e["row_key"])
        if k in done:
            continue
        done.add(k)
        out.append(seen[k])
    AIW.write_text("".join(json.dumps(e) + "\n" for e in out))
    print(len(out), sum(1 for e in out if e.get("stream") == "costs"))


if __name__ == "__main__":
    main()
