# Nuggets: provenance

The ten `<TICKER>.jsonl` files here are verbatim copies of `docs/nuggets/<TICKER>.jsonl` from Parker's `needle` branch at commit
`b908519f59f78ed7aad86e2d224274d53f423648` ("Nuggets: explicit slide_ready on every row (verified and not on the v3 do-not-use list)",
2026-10-17 17:15 -0500). They are not edited. To check: `git show b908519f59f78ed7aad86e2d224274d53f423648:docs/nuggets/<TICKER>.jsonl | diff - docs/nuggets/<TICKER>.jsonl`.

97 rows in total (ABBV 8, AMGN 11, AZN 11, BMY 7, GILD 9, JNJ 10, LLY 9, MRK 12, NVO 10, PFE 10). Each row is the Finding schema plus
`signal_family`, `obscurity.rung`, `case_fit`, `part2_hook`, `enriches` (the needle-branch id of the detector row it extends, scheme
`<TICKER>-<detector>-<sha256(kind|detail) mod 10^6>` from that branch's `agent/needle/score.py::_stable_id`), `verdict` and
`slide_ready`. The rows carry no `best_needle` field; `best_needle.json` records the per-company best needle named in
`docs/red_team_v3_final.md` (same commit, section (a)), and the loader sets `best_needle` from it.

Run: `python -m agent.needle.quant.run --all --nuggets docs/nuggets/`. Nugget rows go through the same scoring, impact math
(dEPS = dRev x CM x (1 - t) / D on the company's own constants), guards and per-number citation gate as detector rows; see
`docs/fix_notes_2.md` for the rules and the counts.
