# fineprint: qualitative mispricing finder

One goal: find qualitative evidence that something about a company's drugs is mispriced.

A finding is a gap between what the market believes about a drug and what the company's own fine print says:

| Part | What it holds |
|---|---|
| Market belief | The case's starter thread, plus what management says on calls |
| Fine print | A page-verified filing quote or label clause |
| Gap | Why the two disagree, and one line of impact math (one labelled assumption) |

## Pipeline (per ticker, per drug)

1. **Mine** (`agents/nugget-miner.md`): gather every passage on the drug across two 10-Ks, the latest 10-Q, four call transcripts, the label and the Orange or Purple Book. Compare FY24 against FY25 wording, filing against call, and our label against each rival's.
2. **Verify** (`pages.py`): every quote must be found on its cited page. Misses go to `out/<T>/<T>_ai_caught.jsonl`.
3. **Red-team** (`agents/red-team.md`): drop anything already said on a call, priced in, resting on stacked assumptions, or sourced from an untrusted transcript.

Outputs: `out/<TICKER>/`. Corpus: `data/corpus/` (from branch `corpus`).

## Carried over from branch `needle`

- `pages.py`, `schema.py`: the page verifier (now runs as `fineprint.pages`)
- `agents/`: nugget-miner and red-team prompts, paths repointed here
- `out/MRK/`: the 12 verified MRK nuggets and their AI-caught log; `out/red_team_v3_final.md`

Not carried over: detectors, backtest, scoring, league, predictions, trial, ledger. They stay on `needle` for reference.

## Check the verifier

```
python -c "from fineprint.pages import docs, check; from fineprint.schema import Evidence; d=docs('MRK'); e=Evidence(doc_id='MRK:10q_2026Q2.md', page=34, quote='Merck pays a royalty of 2.5% on worldwide net sales of Keytruda', figures=['2.5%']); print(check(e, d), e.citation)"
```
