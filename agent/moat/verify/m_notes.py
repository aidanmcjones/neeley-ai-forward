"""Write the verification notes for the market stream (news_mentions meaning, parser rules, caveats)."""
from agent.moat.common import write

NOTES = """# Market stream verification notes (2026-10-17)

## analyst_topics (verified)
- Source: 101 company-quarters (2024Q1 to 2026Q2, JNJ to 2026Q3) from data/corpus and data/moat transcripts. One file per
  quarter, ranked LSEG official PDF > marketbeat/bullfincher > fool/roic > benzinga > allmind (transcript_choice.csv).
- Analyst vs executive: explicit labels first (LSEG "- Analyst", "(Analyst at X)", benzinga "Analyst at"), then a
  cross-quarter executive roster (participants lists, pre-Q&A speakers, titled exec labels) minus every name ever labeled
  or introduced as an analyst at any of the 10 companies, then position (first non-executive speaker after an operator
  or moderator introduction). Fool TAKEAWAYS/SUMMARY/RISKS are skipped (parsing starts at "Full Conference Call Transcript").
- Known residual noise: allmind transcripts (AZN 2025Q4, 2026Q2; NVO 2025Q4, 2026Q2) are machine-diarized with garbled
  text; speakers are anonymous and some answers can be counted as questions. Marketbeat files sometimes attach the wrong
  name to an analyst question (the text is still the question), so analysts_asking is approximate there.
- Topic matching runs on squashed alnum text so spaceless LSEG text (JNJ) still matches; acronyms (IRA, MFN, MFP, GTN, PBM,
  LOE) are case-sensitive; top_products uses company-specific brand lists. matched_terms shows what fired per cell.

## news_mentions (GDELT) - what the counts can and cannot mean
- Each count is the number of English-language online news articles GDELT indexed in that month whose full text contains
  the company string AND any topic term anywhere in the article (no proximity requirement).
- Can mean: relative press attention to a topic for one company over time, and rough cross-company comparison for the
  same topic query.
- Cannot mean: that the article is about the company's exposure (a Merck article listing many drug names counts once);
  articles are not deduplicated across syndication; "Merck" also matches Merck KGaA; "Gilead" and "generic", "inventory",
  "guidance", "pipeline" are broad words; GDELT coverage of trade press and paywalled outlets is partial; counts are not
  normalized by total company coverage (compare to the company's total volume before reading levels).
- Re-run check: two attempts to re-run MRK queries returned HTTP 429 (GDELT allows one request per 5 seconds and the
  collector job was still running), so counts are not independently re-verified yet. At verification time the table held
  5 of 90 company-topic pairs (MRK only).

## event_returns (verified)
- 30 random events recomputed from prices_daily: 30/30 match (abn_day0 = close(-1) to close(0) minus XLV; abn_0_to_1 =
  close(-1) to close(+1); abn_m1_to_5 = close(-2) to close(+5); day 0 = first trading day on or after filed date).
- 113 of 377 rows are exhibits or cover 8-Ks of the same filing; use is_primary == yes (264 events).
- After-close releases (AMGN, GILD, REGN, ALNY, BBIO typical): day-0 return predates the news; use abn_0_to_1.

## IBES
- Revenue (SAL) in millions; USD for all but NVO (DKK). FY1 (fpi=1) maps to fiscal 2026 (fpedats 2026-12-31) for all 10
  at the latest snapshot (2026-08-20). The stale ZEN series (AZN ADR, per-ADR EPS, FY1=2025, last 2026-02-19) must not be
  mixed with AZN (per ordinary share). AZN FY2026 revenue consensus has only 4 estimates.
"""
write("verify_market", "verified/market/VERIFICATION_NOTES.md", NOTES, group="market", doc_type="notes",
      source_url="agent/moat/verify/m_*.py", upload=True)
print("ok")
