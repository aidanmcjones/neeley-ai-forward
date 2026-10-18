---
name: corpus-cite
description: Find, read and quote-verify text in data/corpus (filings, transcripts, labels) with page cites. Use for any task that searches the corpus or puts a quote, figure or page number into a finding, nugget, slide or message.
---

# Corpus search and citation

One helper replaces hand-rolled grep, sed and verifier one-liners. Run from the repo root:

```bash
C=.claude/skills/corpus-cite/cite.py
python -I $C find AMGN "rebate|chargeback" --types annual_report,quarterly_report --max 20
python -I $C page AMGN AMGN:10k_FY2025.md 88
python -I $C quote AZN:20f_FY2025.md 88 "EXACT TEXT" --figures "10,237;8,302" [--speaker "Name"]
python -I $C row MRK-nugget-002             # every evidence quote of one nugget row
python -I $C file docs/nuggets/AZN.jsonl    # every row; exit 1 if any quote fails
```

`find` prints `doc_id N=<file page> printed=<P>`. `quote` takes the file page N and returns the citation string. Exit code 0 means verified.

## Layout (details: data/corpus/README.md, read only if needed)
- `companies/<T>/` MRK BMY PFE LLY NVO ABBV JNJ AZN AMGN GILD: `10k_FY2025.md`, `10k_FY2024.md` (or `20f_`), `10q_2026Q1.md`, `10q_2026Q2.md`, `earnings/`, `policy/`, `transcripts/<YYYYQn>_transcript.md`, `presentations/`, `reports/`, `xbrl_companyfacts.json.gz`.
- `peers/<T>/` NVS GSK SNY TAK REGN ALNY BBIO ROCHE BOEHRINGER. `drugs/<drug>/` 52 label, patent, IRA and spending packs.
- doc_ids look like `PFE:10k_FY2025.md`. Check exact ids in `manifest.jsonl` or the folder's `sources.jsonl`.

## Citation rules
- Page marker `[[page N | printed P]]`: the verifier uses N, humans cite P ("BMY 10-K FY2025, p. 39"). `printed ?` (GSK and SNY SEC 20-Fs): cite their PDF annual report under `reports/` instead.
- The quote must be verbatim from that page (whitespace normalized), and every figure must appear inside it. Never paraphrase in a quote field. If a figure is not on a page, it does not exist. Never cite from memory.
- Transcripts: official only for MRK, PFE, JNJ, GSK, SNY. Others are third_party (lower trust, fine for leads). Never quote fool.com TAKEAWAYS or SUMMARY text; quote only after "Full Conference Call Transcript". If the speaker check fails on a long prepared remark, cite the filing.
- Known bad files: AZN `transcripts/2026Q1_transcript.md` is really Q2 2026; AZN 2025Q3 has no speaker names; GILD 2025Q3 is garbled.
- Label tables in `out/<T>/labels_table.json` mix orphan exclusivity with patent expiry: use the 10-K patent table or Orange or Purple Book files for dates.
- Log every quote that fails (claimed vs what the page said) to `docs/nuggets/<T>_ai_caught.jsonl` when working on nuggets.
