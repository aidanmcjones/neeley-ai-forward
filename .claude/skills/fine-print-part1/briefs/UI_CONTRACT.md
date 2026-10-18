# out/part1 contract (agreed with the UI session)

selection.md: trailing line "sha256: <hex>" covering everything above it. selection.json:
{picked:[T1,T2,T3], reasons:{T:text}, eliminated:{T:one line}, sealed_at, sha256}. Appendix in a separate
file selection_appendix.md so the hash stays valid.

out/part1/<T>/part1.json:
{ticker, name,
 findings:[{n, finding, finding_marked, marker_map:{n:cite_id},
   source:{doc_title, period, page, quote, url, speaker?},
   cites:[evidence objects: cite_id, doc_id, page, quote, url, verify_status, withheld, grade],
   impact:{text, text_marked, math, direction, metric, numeric_check:{status, checked, total, verified, derived, assumed, unsupported}},
   peer, peer_marked, confidence, confidence_reason, obviousness, on_the_record?}],
 sharpest_needle:{finding_n, why, cites},
 product_table:{product, rivals:[..],
   rows:[{row: one of "approved uses" | "boxed warnings and safety" | "dosing and convenience" | "patent and exclusivity timeline" | "pricing and gross-to-net",
          cells:{name:{text, text_marked, cites}}}],
   financial_tie:{text, text_marked, math, cites},
   growth_limiter:{sentence, sentence_marked, cites},
   priced_in:{call: "priced in"|"not priced in"|"untestable", text, text_marked, cites}}}

Only text whose numeric_check.status is "passed" or "no_numbers" is printed by the UI; "failed" records go
to rejected.jsonl with the reason.

out/part1/<T>/trace.jsonl, one JSON per line:
{step, category (one of the eight exact strings below, or "header" on line 1), query,
 documents:[{doc_id, doc_title, page?}], candidate:{text, cites?},
 skeptic_materiality:{round1, round2}, skeptic_obviousness:{round1, round2},
 verdict: survived|killed|narrowed, verdict_reason, finding_n?}
Header line: {step:0, category:"header", categories:[...eight...], ticker, generated_at}.

The eight category strings: "Language drift", "Gross-to-net",
"Inventory and receivables growing faster than revenue", "Segment and product table changes", "Footnotes",
"Earnings-call Q&A", "Product fine print", "Peer contrast".
