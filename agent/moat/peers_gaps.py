from agent.moat.common import note_gap
S = "peers"
for t in ("GSK", "SNY", "TAK"):
    note_gap(S, t, "tables/peer_product_revenue.csv", "20-F product tables are flattened (GSK, SNY: no page breaks in source; TAK layout) and did not parse to product level with the heuristic; only NVS delivered")
note_gap(S, "BBIO", "transcripts 2024Q1-2024Q4, 2025Q2", "MarketBeat/Quartr has no transcript for these; no other free source tried")
note_gap(S, "TAK", "transcript 2025Q2 (Oct 2025 call)", "outside the 2024Q1-2025Q2 window; not a true gap")
note_gap(S, "ROCHE", "quarterly releases", "Used investor slide decks irp*.pdf plus hy25e half-year report; Roche does not publish separate Q1 or 9M PDF reports")
note_gap(S, "BOEHRINGER", "rival_product_statements Jardiance", "no BI document obtainable; statements come from Lilly 10-K FY2025 and 2026Q1/Q2 calls (co-commercializer)")
note_gap(S, "NVS", "transcripts 2026Q1", "only 2026Q2 (Webull/Benzinga, grade C) in corpus; Q1 2026 has no free English source")
note_gap(S, "GSK", "rival_product_statements latest two calls", "2026Q2 call not in corpus; used 2026Q1 and 2025Q3")
