# Source corpus: The Fine Print (Advanced pharma case)

Everything Part 1 needs, for all 10 shortlist companies, the rival products' makers, and every drug named in the case appendix. Pulled Sat Oct 17, 2026. Index: `manifest.csv` (one row per document). Holes: `GAPS.md`.

## Layout

| Folder | What |
|---|---|
| `companies/<TICKER>/` | MRK BMY PFE LLY NVO ABBV JNJ AZN AMGN GILD. Full pack. |
| `peers/<TICKER>/` | NVS GSK SNY TAK REGN ALNY BBIO ROCHE BOEHRINGER. Latest annual report, latest calls. |
| `drugs/<drug>/` | 52 products: FDA label by section, Orange Book patents and exclusivity, Purple Book (incl. biosimilars that reference it), Paragraph IV, IRA negotiation and maximum fair price, Medicare Part D/B spending. |

Inside a company folder:

| Path | Source |
|---|---|
| `10k_FY2025.md`, `10k_FY2024.md` (or `20f_`) | SEC EDGAR, two latest annual reports |
| `10q_2026Q1.md`, `10q_2026Q2.md` | SEC EDGAR |
| `earnings/` | 8-K Item 2.02: earnings releases (EX-99.1) and supplements |
| `policy/` | 8-Ks and company press releases on MFN deals, tariffs, US manufacturing, IRA, TrumpRx |
| `6k/` | Foreign filers' current reports with results or policy news |
| `transcripts/<YYYYQn>_transcript.md` | Earnings calls, last 4 quarters (5 for JNJ) |
| `presentations/`, `reports/` | Earnings slides, JPM 2026 / investor day decks, glossy annual reports (PDF kept alongside) |
| `xbrl_companyfacts.json.gz` | SEC XBRL: revenue, inventory, receivables etc. by period, for forensic ratios |

## How to cite

Every document has page markers: `[[page 41 | printed 39]]`. Cite the **printed** number ("BMY 10-K FY2025, p. 39"); the first number is the position in the file. `printed ?` means no folio was found on that page (cover pages, some 8-K exhibits, GSK/SNY SEC 20-Fs, which have no page breaks; use their PDF annual reports instead). Labels are cited by section ("Eliquis label, 5.2 Bleeding"). Each file's header comment holds its source URL and retrieval time.

## Trust levels

- `source_quality` in `manifest.csv`: `official` (SEC, FDA, CMS, company site) or `third_party`.
- **36 of 54 transcripts are third_party** (fool.com, roic.ai, allmind.ai, marketbeat, webull) because most IR sites block scripted downloads. Fine for finding leads. **Before a quote goes in the findings table, check it against Bloomberg/FactSet or the webcast replay.** Official transcripts: MRK, PFE, JNJ (all quarters), GSK, SNY.
- Third-party pages include site navigation text around the call.
- Text was extracted mechanically (we did not paraphrase), but some source pages contain AI-written text. **fool.com transcripts open with TAKEAWAYS / SUMMARY sections written by Motley Fool with LLMs: never quote them.** Quote only from the call itself (after 'Full Conference Call Transcript').
- Known bad files: AZN `transcripts/2026Q1_transcript.md` is actually the Q2 2026 call (duplicate); AZN 2025Q3 has no speaker names; GILD 2025Q3 is garbled. AMGN, NVO and AZN have only 3 distinct calls in 2025Q3 to 2026Q2. See GAPS.md.

## Regenerate

```
python -m agent.public_data          # FDA/CMS bulk files -> data/external (gitignored)
python -m agent.corpus               # SEC filings, page-anchored (needs SEC_USER_AGENT in .env)
python -m agent.drug_pack            # per-drug packs
python -m agent.ir_fetch URL --ticker X --rel transcripts/2026Q2_transcript.md --type transcript --period 2026Q2 --quality official
python -m agent.corpus_check         # manifest.csv + GAPS.md
```

Point `agent/corpus.py` (`COMPANIES`) and `agent/drug_pack.py` (`DRUGS`) at a different company and the same pipeline runs.
