# Part 1 independent verification (AMGN, MRK, PFE)

Verifier: independent agent, 2026-10-17. Inputs read: `out/part1/{AMGN,MRK,PFE}/part1.json`, `out/part1/_blind/<T>/synthesis.json` and `skeptic_*.json`, and the citation index (`agent.moat.cite.get_page` / `verify_quote`, facts table, `data/moat/tables/partb_asp_quarterly.csv`). The writers' reports and scripts were not read. The part1 files were not edited.

Method:
1. Every cite in every block was run through `verify_quote(quote, doc_id, page)`. Table cites (page = null) were matched against the `facts` row named in the locator.
2. Every number in every `*_marked` text was tokenized and checked. A `[n]` number must appear in cite n's quote; unit scaling ($000 to $M, $ to $M) is allowed. A `[derived]` number must equal a `derived` entry whose `expr` was re-evaluated from its operands, and each operand's quote was re-verified on its page. An `[assumption]` number must be in the `assumptions` dict. An unmarked number must sit in a quoted span or equal a cite's value.
3. Anything flagged was opened on the source page by hand. All product cells were checked, more than the 6-per-company sample asked for.
4. Each text was compared with the blind synthesis and skeptic rulings for the ids used.
5. Licenses: no cite or operand citation resolves to a doc with a `license` (Bloomberg) flag.

Scope of the checks:

| | cite instances verified on page | numeric tokens checked | derived recomputes | licensed pages quoted |
|---|---|---|---|---|
| MRK | 98/100 page-verified; 1 withheld quote confirmed by hand; 1 table cite fails | 172 | all reproduce | 0 |
| AMGN | 88/88 | 211 | all reproduce | 0 |
| PFE | 73/73 | 120 | all reproduce | 0 |

---

## MRK (fails: 1)

| Row / cell | What was checked | Result | Defect / note |
|---|---|---|---|
| F1 MRK-c03 IRS NOPA | 10 cites; $1.3B, $260M, 2,470, 65,011, 2,530 on page; 1.56, 0.63 (1,560/2,470=0.632), 2.4% (1.56/65.011), 2.53 recomputed; 2,530 confirmed as the UTB roll-forward (10-K p.131); blind c03 held, "zero mentions" held | PASS | Note: "excludes audit-reserve tax items from non-GAAP EPS" generalizes from a single Q3 2025 release sentence. |
| F2 MRK-c01 inventory | $3.8B/$5.5B/$5.9B, 12,339/10,302, 16,382/15,193, BMY 4,340/4,126 on page; 2.1, 19.8%, 5.2%, 275 (274.9) and 247 (247.497) recomputed | PASS | Note: cite c_197ad7a559 (2025Q1 call p.14, grade C, third-party) has an empty quote because it is withheld; I opened the page and "drug substance and a drug product as we move into 2026 and 2027" is there. |
| F3 MRK-c04 Halozyme | p.118 "Following a one day hearing in December 2025, a preliminary injunction..."; three appeal-date filings (Q2 2026, Q2/Q3 2026, Nov 19 2026) = two slips; 7 counterclaim countries counted; deck p.25 "expect launches in major markets starting in 2026" on page; 68/463=14.7%, 272, 0.4% recomputed | PASS | $68M and $463M are unmarked in impact.text but are cite [2]'s values ("Keytruda Qlex 395 68 463"). Matches blind (the "three slips" claim was refuted, and "slipped twice" is used). |
| F4 MRK-c02 GTN (killed, on record) | $13.3B/$10.0B, $2.5B, 36,510/32,277, BMY "U.S. 53 % 49 %" on page; 3.3 and 5.1% recomputed; BMS contrast caveated "direction-only" as the blind required | PASS | Note: "largely through the early-2025 Januvia list-price cut" is a causal share that no cited number sizes. It matches the blind kill reason. |
| F5 MRK-c09 IRA date (killed, on record) | FY2024 10-K "January 1, 2028" and FY2025 "January 1, 2029 ... decline materially" on page; 18,829/65,011 = 29.0% | PASS | |
| Sharpest Needle why | $1.56B and $0.63 derive from F1 cites; "both skeptics hold c03 in both rounds as the least obvious" matches synthesis | PASS | |
| financial_tie | 395, 4,611 on 10-Q p.28; 5,006 and 7.9% recomputed; CMS rows J9277 2026Q2 32.129 and J9271 2026Q2 61.251 (per 1 MG) checked in partb_asp_quarterly.csv lines 749/744; 12,691, 12,250, +3.6% recomputed | PASS | CMS values are labelled [assumption] and are not page-cited (allowed). |
| growth_limiter | 7.9% derived; "30% to 40% adoption" on Q4 call p.11; Nov 19 2026 hearing | PASS | |
| priced_in | "30% to 40%" quote; table cite priced_in_scorecard#73 share_of_quarters_asked = 1.0 (verified) | PASS | |
| Cell approved uses / Keytruda | cHL quote (label p.5), "Qlex ... solid tumor indications" (10-K p.4), Qvantig carve-out quote | PASS | |
| Cell approved uses / Opdivo, Imfinzi, Tecentriq | label quotes on page | PASS | |
| Cell boxed/safety (4 cells) | "CONTRAINDICATIONS None." on each label page; Qlex hyaluronidase contraindication on p.26 | PASS | |
| Cell dosing / Keytruda | 200/400 mg, 30 min, 395 mg over 1 min, 790 mg over 2 min on label pages | PASS | Note: "2[3][4] minutes" tags cite 3, which says "over 1 minute"; cite 4 supports the 2 minutes. |
| Cell dosing / Opdivo, Imfinzi, Tecentriq | all doses and infusion times on label pages | PASS | |
| Cell patent / Keytruda | 10-K p.16 header confirmed (U.S., EU, Japan, China): Keytruda 2028 / 2031 / 2032-2033 / 2028; Qlex 2043 / 2031 | PASS | Note: Japan "2032-2033" is tagged [assumption] although it is in cite [1]'s quote. The value is correct; the tag is wrong. |
| Cell patent / Opdivo | BMY p.9 "Opdivo (nivolumab) 2028 2030 2031"; Qvantig row "(g)" | PASS | |
| Cell patent / Imfinzi | AZN 20-F p.19 columns confirmed as US, China, EU, Japan: 2031 / 2030 / 2030 / 2033 | PASS | |
| **Cell patent / Tecentriq** | table cite c_3ed2ebed7e `pipeline/loe_calendar.csv#617 company_stated_loe = None` | **FAIL** | The field `company_stated_loe` does not exist for that row in the index. The only fact row is `biosimilar_count = 0` (machine_data). The cell's claim "the Purple Book row is empty" is cited to the LOE calendar, not the Purple Book, so the cite does not support the sentence. |
| Cell pricing / Keytruda | Q2/Q3/Oct 2026 CMS rows match the CSV (32.129/61.251, 31.940/60.645, 32.307/62.253); sample_checks#24 = 32.307 verified; +3.6%, +4.0% (1.0402), +2.5% (1.0250) recomputed; "priced this to drive for the adoption" on Q4 call p.11 | PASS | |
| Cell pricing / Opdivo, Imfinzi, Tecentriq | gtn_proxy rows #31 33.9025, #33 27.91475, #181 87.006, #213 95.3315, all verified; text rounds correctly | PASS | |
| Blind consistency | c02, c09 killed rows carry obviousness high and do not reuse refuted numbers (78% identity not used); c05 "ceiling" not asserted; c10 premium 2.5-4.0% (not 4-6%) used | PASS | |
| Currency / license | $M and $B labels consistent; "($ millions)" stated on raw table numbers; 0 licensed docs | PASS | |

---

## AMGN (fails: 6)

| Row / cell | What was checked | Result | Defect / note |
|---|---|---|---|
| F1 AMGN-c06 TAVNEOS | $2.4B/$2.3B (10-Q p.21), 423 and 36 (10-K p.75), Jan 16 and Apr 27 2026 dates, both recoverability wordings, 544 shares, 143+7, GILD quote; 5.2x (2.4/0.459), $4.23 (2,300/544), $3.34 (x0.79), $3.51 (x0.83), $600M recomputed; blind c06 held both rounds | PASS | Note: ROW $36M is tagged [assumption] but is on the cited page (c_1c1eb40826). |
| F2 AMGN-c02 deductions | 35,148, 41,983, 35,346, 32,026, 10,606/8,405/7,271, 9,958, "54%, 52% and 53%", "timing of payments", GILD "41 % 38 % 250 bps" on page; 54.4%, 52.5%, 2,201, 1,134, 1,067, 10.7%, 771, $1.42, 13 pts recomputed | PASS | |
| F3 AMGN-c03 TEPEZZA | 22%, 381/490, 8,218/7,873, 424/365, -4% on 505, +7% on 886 (six-month basis confirmed on p.40); 84, 345, 4.4%, 24%, 1.1 pts, 20, 62 recomputed; call quote "$490 million in the U.S." on page | PASS | Note: "Q2 volume grew" (the reason the reader's read was dropped) has no cite in this row. |
| F4 AMGN-c05 IRS PR (killed, on record) | $3.6B, $5.1B, $2.0B, $900M, $2.2B, 4,371, years 2010-2012 and 2013-2015 on 10-K pp.84-85; 7.6, 76%, $13.97 recomputed; MRK $1.3B + $260M; "a fifth" = 1.56/7.6 = 0.21 | PASS | |
| **F5 AMGN-c07 profit share** | 721 (UCB/EVENITY p.132), 587 (AZ/TEZSPIRE p.131), 2,100/1,563, 1,478/972, AZN Alliance Revenue 673/436 on page; 349, 1,308, 1,043, 33%, 3.7%, 3.0%, 0.99% recomputed | **FAIL** | The finding states "about a third of the two brands' $1,043M of incremental Amgen-booked sales" as fact. The blind c07 ruling says "the 'third of incremental sales' ratio mixes global profit share with Amgen-booked sales", and the materiality skeptic conceded it. A refuted ratio is restated. |
| **Sharpest Needle why (traceability)** | `why_marked` uses [1], [derived: 1, 2], [derived: 1, 3] | **FAIL** | The SN block has no `marker_map`, so the markers cannot be resolved. By cite order, [derived: 1, 3] for $4.23 would point to the Q2 wording cite, not to the share count. The SN cites also omit the TAVNEOS sales operand (10-K p.75) behind 5.2x. The numbers are correct via F1, but the block is not self-verifying. |
| **Sharpest Needle why (claim)** | "the only surviving ruling that both skeptics held through both rounds with materiality high and obviousness low" | **FAIL** | False. AMGN-c02 has `refuted: false` in all four skeptic files (materiality r1/r2, obviousness r1/r2), and the synthesis rates it materiality high, obviousness low. The company_score also counts 3 material non-obvious survivors. |
| **financial_tie** | 1,663 (U.S. Repatha), 35,148, 41,983, "net selling price to decline by approximately mid-single digits"; 17, 83, 0.11 pts recomputed | **FAIL** | Unlabelled scoping. The 10-K guide sits in the global Repatha paragraph (p.71, after "global Repatha sales") and names no geography. The tie applies it to U.S. sales only ($1,663M, giving $83M). On the $3,016M total it is about $151M, which matches the blind c09 sizing of ~$150M on $3.0B. The U.S.-only base is neither cited nor tagged [assumption], and it understates the effect by about 45%. |
| **growth_limiter** | revascularization label quote; HoFH coverage vs rivals (Repatha 10+, Leqvio 12+, Praluent adults, Lipfendra none); 10-K price guide | **FAIL** | "just as Merck's oral Lipfendra launches with a direct-to-patient cash channel": the cited page (MRK 10-Q p.32) says Merck "will be expanding the program in the future to include Lipfendra", so "launches with" is unsupported. The juxtaposition also implies Lipfendra price pressure, which blind c09 refuted ("no evidence yet that Lipfendra is pressuring price"). |
| priced_in | 10-K guide quote; no numbers | PASS | |
| Cells approved uses (4) | Repatha MACE and HoFH 10+, Praluent event list and HeFH 8+, Leqvio HoFH 12+ (HeFH 12+ also on page), Lipfendra indication and pediatric quotes | PASS | |
| Cells boxed/safety (4) | hypersensitivity quotes; Lipfendra "CONTRAINDICATIONS None." and pregnancy line | PASS | |
| Cells dosing (4) | 140/420 mg, 75/300 mg, 284 mg at 0/3/6 months, 20 mg plus a 30-minute wait, all on label pages | PASS | |
| Cell patent / Repatha | 10-K p.13 "8/27/2029", "5/10/2032" | PASS | |
| Cell patent / Leqvio | NVS 20-F p.39 "Leqvio 2034 5 2035" (columns US, EU) | PASS | Note: the table is patent "Year of Expiration" with footnote 5 "PTE pending". The cell calls it "loss of exclusivity" and drops the PTE caveat. |
| Cell patent / Praluent, Lipfendra | no-date statements; Lipfendra July 2026 approval quote | PASS | |
| Cell pricing / Repatha | Q1 10-Q p.36: 35%, 8%, 7% (global Repatha) | PASS | |
| Cell pricing / Praluent | REGN 10-K p.79 "Praluent - U.S. 262.5 241.7" | PASS | |
| **Cell pricing / Lipfendra** | MRK 10-Q p.32 | **FAIL** | "a cash-price channel at launch" is not on the page. The source says the program will be expanded "in the future" to include Lipfendra. |
| Cell pricing / Leqvio | no-data statement | PASS | |
| Blind consistency (other) | c04 TAVNEOS-not-in-tables error not carried; c05 kept as on-record with obviousness high; c06 5.2x (not 5.6x) and sales from 10-K p.75 used | PASS | |
| Currency / license | $M/$B consistent; AZN "USD millions, printed as $m"; 0 licensed docs | PASS | |

---

## PFE (fails: 0)

| Row / cell | What was checked | Result | Defect / note |
|---|---|---|---|
| F1 PFE-c01 ATTR-CM share | PFE 10-Q p.38 U.S. 1,975/1,976; ALNY p.38 row confirmed as AMVUTTRA United States ($000: 1,511,633/559,310); BBIO p.56 net product revenue ($000: 403,036/108,240); 10-K p.44 3,834/3,547; 3,889.7, 2,643.5, +1,246 (+47.1%), 50.8%, 74.8%, 2,136, 161, 0.32B recomputed; call quotes on page | PASS | Note: BBIO's page gives total net product revenue with no geography. Treating it as U.S. Attruby is reasonable, but the page does not say it. |
| F2 PFE-c04 legal charge | 842/422/1,033/564 (10-Q p.14 and release p.16); $867M (p.46); both materiality wordings (p.27); state courts; 5,699 shares; BMY "5 1 8 259"; 0.148, 469, 25 recomputed; blind c04 held | PASS | |
| F3 PFE-c05 contingent consideration (killed, on record) | 1,790, 2,259, 550, (81), 632, 1,266, 508, 5,733 on page; roll-forward 1,790+550-81 = 2,259 reproduces; $0.096; no CVR double count, as the blind required | PASS | |
| F4 PFE-c02 GTN (killed, on record) | 10-K p.43 deduction table (36,374/33,888), p.58 product revenues, 10-Q p.37 (17,280/16,569, returns 919/639; chargebacks up, Medicare rebates and allowances down confirmed on page), p.5; 38.6%, 41.3%, 2,357, 40.04%, 40.01% recomputed; BMY "32 % 46 %" and "list price reduction for Eliquis in the U.S." on BMY p.31 | PASS | Notes: "$1 billion[3][5]" tags cite 5, which is the returns line (cite 3 carries it). "partly COVID-product mix" has no cite. The finding calls the $2,357M step "flagged in advance" against a $1B guide. |
| F5 PFE-c09 Ibrance (killed, on record) | CMS fact sheet "$7,871 $15,741 50% $2,036,178,000"; 10-K "Ibrance 2027"; Bourla quote; Kisqali $1,578,679,000 and Verzenio $1,428,714,000; $1,018M recomputed; refuted 71% ratio not used | PASS | Note: $7,871 / $15,741 carry no unit (CMS 30-day-supply price). |
| Sharpest Needle why | no numbers; "c01 is the only high-materiality survivor" matches synthesis (c01 high, c04 medium) | PASS | |
| financial_tie | same operands as F1; 50.8%, 74.8%, 1,246, 47% reproduce | PASS | Note: the marker lists cite non-operands ([derived: 1, 2, 3, 6] in text, where 6 = 10-K p.44; [derived: 1, 2, 3, 4] in math, where 4 = the payer-contract sentence). The arithmetic reproduces from cites 1 to 3. |
| growth_limiter | "net price erosion in the U.S. as a result of new payer contracts" with "continued market expansion in the U.S." on the same page; June 1, 2031 generic date (p.29) | PASS | |
| priced_in | no numbers, no cites | PASS | |
| Cells approved uses (3) | Vyndaqel, Attruby, Amvuttra PN and CM quotes on label pages | PASS | |
| Cells boxed/safety (3) | "CONTRAINDICATIONS None." on each; Amvuttra vitamin A quote | PASS | |
| Cells dosing (3) | 80 mg / 61 mg, 712 mg twice daily, 25 mg every 3 months by an HCP | PASS | |
| Cells patent (3) | "2026 (2028 pending PTE)", June 1 2031, BBIO "2031 or 2033", ALNY NCE June 13 2027 and ODE CM March 20 2032 | PASS | |
| Cells pricing (3) | 10-K p.44 Part D redesign quote; BBIO accrued rebates 79,967/45,909 ($000) = $80.0M/$45.9M; Amvuttra HCP quote | PASS | Note: the Amvuttra cell refers to an ALNY 2025Q1 call that it does not cite. |
| Currency / license | $000 converted to $M correctly (ALNY, BBIO); CMS whole dollars converted to $M; 0 licensed docs | PASS | |

---

## Summary

**Fails: MRK 1, AMGN 6, PFE 0 (7 in total). Every cite quote checked is on its page except one MRK table cite. Every derived number re-computes. No Bloomberg-licensed page is quoted.**

**Worst defect: the AMGN Sharpest Needle.** Its stated reason for being the pick, "the only surviving ruling that both skeptics held through both rounds with materiality high and obviousness low", is false. AMGN-c02 has the same profile: not refuted by either skeptic in either round, materiality high, obviousness low. The block also has no `marker_map`, so its numbers cannot be traced from the block itself.

---

## Status (2026-10-18)

All seven fails above were applied and re-gated at quant-model 7eb0dca (AMGN: truthful needle rationale with its own marker_map and the TAVNEOS sales cites, refuted profit-share ratio dropped from finding 5, Repatha financial tie restated on the global base, Lipfendra cash-channel wording matched to Merck's 10-Q; MRK: Tecentriq exclusivity cell cites the row that exists and says no date is in the index; PFE: marker pointers corrected, uncited COVID-mix clause dropped, BridgeBio geography caveat added). The priced-in calls were replaced with gated evidence-graded inferences at a1ddc77 after this report was written, so the "priced_in" rows above describe the earlier "untestable" text. The part1 files have not changed since 7eb0dca.
