from agent.moat.common import note_gap
G = [
    ("deal_comps", "party roles", "Licensor/licensee roles are inferred by regex from the upfront sentence; rows with confidence low:role may have the two parties swapped. No LLM extraction was available."),
    ("deal_comps", "10-K note rows", "10-K paragraphs give a month only (day set to 01 when absent), stage is blank unless the quoted sentence names it, and the counterparty is often blank."),
    ("deal_comps", "big pharma deals", "Big pharma rarely files 8-Ks for licensing deals, so the table is skewed to small and mid-cap biotechs; the 10 case companies have 32 8-K deal rows."),
    ("deal_comps", "private-target M&A", "Acquisitions of private companies with undisclosed price are absent by construction."),
    ("deal_benchmarks", "acquisition price-to-trailing-revenue", "Only about 20 acquisitions have a trailing revenue figure in the 8-K text; multiple is price divided by the first historical revenue sentence found and is unreviewed."),
    ("deal_benchmarks", "peak sales note", "Few releases disclose peak sales estimates; deal_value_to_peak_sales_note is mostly blank."),
    ("deal_comps", "EDGAR FTS coverage", "Harvest capped at 1000 hits per month per query and filtered to SIC 2833-2836, 8731; fetch of the last hits may be incomplete if the run was cut for time."),
    ("deal_comps", "R2 upload", "Deal md documents were written locally under data/moat/deals with upload=False for speed; only the two tables are uploaded to R2."),
]
for item, sub, reason in G:
    note_gap("deals", None, f"{item}: {sub}", reason)
print("gaps logged", len(G))
