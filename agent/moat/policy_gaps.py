from agent.moat.common import OUT, note_gap

(OUT / "gaps" / "policy.jsonl").unlink(missing_ok=True)
G = [
    (None, "IPAY 2028 MFPs and % cuts", "Not published yet: 2028 negotiation (Trulicity, Verzenio, Biktarvy, Orencia, Erleada, Botox, Xeljanz) ends in 2026; only selection-list expenditure recorded"),
    (None, "CMS renegotiation notice", "Only Tradjenta (Boehringer Ingelheim) selected for renegotiation (IPAY 2028); none of the 10 companies; covered by cms_fact_sheet_selected_list_ipay2028.md"),
    ("JNJ", "White House fact sheet for J&J MFN agreement", "No standalone whitehouse.gov fact sheet found; J&J listed as signer in the 2026-04 and 2026-08 fact sheets; terms quoted from the J&J press release"),
    ("ABBV", "White House fact sheet for AbbVie MFN agreement", "No standalone whitehouse.gov fact sheet found; AbbVie listed as signer in 2026-04 and 2026-08 fact sheets; terms quoted from AbbVie press release"),
    ("AMGN", "Overall US investment pledge", "Amgen states $2.5B 2025 US manufacturing capex plus >$40B since 2018 but no forward total pledge in corpus"),
    ("NVO", "Stated post-2029 tariff position in 20-F", "20-F only mentions tariffs generically; no statement on what happens after the exemption"),
    ("AZN", "Post-2029 tariff statement", "20-F has only generic trade-control risk text; deal terms are in the press release"),
    ("JNJ", "Post-2029 tariff statement in 10-K", "10-K does not describe the tariff exemption; only press release says exempt (no end date)"),
    ("MRK", "Post-2029 tariff statement beyond 'delay for three years'", "10-K gives no detail on what happens after the delay"),
    (None, "Section 232 company-specific onshoring/MFN agreement terms", "Terms confidential (e.g. Pfizer release: 'Specific terms of the agreement remain confidential')"),
    (None, "FDA sites file coverage", "drls_reg.txt is CDER drug establishments only (no CBER vaccines/cell therapy-only sites); matching is by name alias on firm and registrant names, includes some CMO sites registered by the company; Amgen/Gilead biologic sites may be undercounted"),
    ("NVO", "IRA share of revenue", "Fast-acting insulin line is a category (includes non-selected insulins); share is an upper bound; US-only revenue by IRA drug not extracted"),
    (None, "Per-drug MFP for IPAY 2026 inflation-adjusted prices", "corpus data/corpus/drugs/*/ira_negotiation.csv has 2027 adjustments (e.g. Eliquis $231 -> $237.25) but only 18 of the 25 selected drugs; not merged into table"),
]
for t, i, r in G:
    note_gap("policy", t, i, r)
print("gaps", len(G))
