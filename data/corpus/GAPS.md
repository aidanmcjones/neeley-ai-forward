# Corpus gaps

Expected documents that are not in data/corpus. Regenerate with `python -m agent.corpus_check`.

## MRK (companies)
- complete against the checklist
- worker notes:
  - 2026Q3 transcript and slides: call scheduled Oct 29 2026, not yet held
  - Press release on IRA Medicare negotiation (Januvia/Keytruda): no merck.com release found
  - Press release on TrumpRx specifically / tariff-only release: not found separately (covered in 2025-12-19 MFN agreement release)
  - Separate investor day / strategy presentation: none found beyond JPM Jan 2026 and ASCO Jun 2026 investor event (AIDS 2026 deck not saved)

## BMY (companies)
- earnings slides: none
- worker notes:
  - presentations/2025Q3_earnings_slides: investor.bms.com / bristolmyers2016ir.q4web.com return HTTP 403 to scripted fetch; no PDF URL found via search
  - presentations/2025Q4_earnings_slides: same as above
  - presentations/2026Q1_earnings_slides: same as above
  - presentations/2026Q2_earnings_slides: same as above
  - transcripts: no official (company IR) transcripts; all four are third_party fool.com (IR site 403)
  - transcripts/2026Q3_transcript: call scheduled Oct 29 2026, not yet happened
  - presentations investor day / strategy: no standalone investor day deck found (Dec 11 2025 hematology event replay only on blocked IR site)
  - policy: Eliquis/Cost Plus Drug press release 2026-04-23 (businesswire.com HTTP 403); no BMS press release found on IRA Medicare negotiation or TrumpRx specifically
  - note: JPM Jan 2026 deck already present as policy/2026-01-12_ef20062582_ex99-1.md (SEC 8-K ex99.1)

## PFE (companies)
- complete against the checklist
- worker notes:
  - transcripts/2026Q3_transcript: Q3 2026 call scheduled Nov 3 2026, not yet happened
  - presentations/investor_day: no separate investor day deck located (JPM 2026 decks saved instead)
  - policy/ press releases on tariffs, standalone US manufacturing, IRA Medicare negotiation: no official Pfizer press release found via search; pfizer.com blocks scripted access (Cloudflare 403)
  - presentations/2026Q3_earnings_slides: Q3 2026 not yet reported

## LLY (companies)
- earnings slides: none
- worker notes:
  - Earnings slides 2025Q3, 2025Q4, 2026Q1, 2026Q2: investor.lilly.com and lilly.gcs-web.com static-files return HTTP 403 to ir_fetch
  - Investor day / strategy presentation: not located (IR site 403)
  - JPM Healthcare Conf Jan 2026 presentation (investor.lilly.com/node/53546): HTTP 403
  - Transcript 2026Q3: call scheduled Oct 29 2026, has not happened
  - Official (company IR) transcripts: none posted/accessible; all transcripts are third_party (roic.ai x3, benzinga x1)
  - Press releases on investor.lilly.com (Nov 2025 US govt agreement official copy, Dec 2025 Zepbound vial price, Jan 2026 Pennsylvania $3.5B plant, Dec 2025 Alabama $6B, May 2026 Indiana $4.5B, Sep 2026 Houston $6.5B): HTTP 403; only Nov 2025 agreement saved via biospace repost (third_party)
  - IRA Medicare negotiation press releases (Trulicity, Verzenio): not searched/found
  - Pharma tariff Lilly-specific press releases: not found

## NVO (companies)
- transcript 2026Q1
- worker notes:
  - transcripts/2026Q1_transcript.md: no free full-text source found (roic.ai 403, fool.com/allmind not indexed); novonordisk.com posts only call recordings, no official transcripts for any quarter
  - transcripts/2026Q3: call is 4-5 Nov 2026, not yet held
  - presentations/2025Q3_earnings_slides.md: official Q3 2025 deck PDF URL not discoverable (guessed paths 404)
  - reports/<period>_financial_report: saved only as HTML news-details page text (about 6k chars, partial); Announcement.pdf not fetched; full text is in EDGAR 6-Ks
  - policy: no Novo press release found for tariffs, US manufacturing investment announcement, or IRA Medicare negotiated price for semaglutide (2027); no separate TrumpRx release found

## ABBV (companies)
- earnings slides: none
- worker notes:
  - presentations/2025Q3-2026Q2_earnings_slides: investors.abbvie.com and abbvie.gcs-web.com static-files return HTTP 403 (Akamai); no alternate official slide PDF found
  - presentations/2026-01_jpm_healthcare: AbbVie JPM 2026 was a fireside chat (Jan 14, 2026); no slides posted/found
  - presentations/investor_day: no recent investor day deck found; IR site blocked (403)
  - transcripts/2026Q3_transcript: Q3 2026 call not yet held as of 2026-10-17
  - transcripts/official: IR-site official transcripts unavailable (403); Motley Fool third_party used
  - policy/press_IRA_Medicare_negotiation: no AbbVie press release on IRA negotiation found on news.abbvie.com
  - policy/press_TrumpRx_launch_and_tariff_2025: no separate AbbVie release found beyond 2026-01-12 MFN release

## JNJ (companies)
- complete against the checklist
- worker notes:
  - presentations/2025Q3_earnings_slides.md - Q3 2025 earnings slide deck PDF URL not found on investor.jnj.com (guessed paths 404; only seekingalpha copy)
  - presentations/2026Q3_earnings_slides.md - Q3 2026 earnings slide deck PDF URL not found
  - presentations/2026Q3_sales_supplement.md - Q3 2026 Other Financial Disclosures PDF not at guessed path (3Q26-Other-Financial-Disclosures.pdf 404); 8-K ex99.2 on EDGAR has the data
  - presentations/2026-01_jpm_slides - J&J JPM Jan 2026 had a fireside chat only; no slide deck found (transcript saved instead)
  - presentations/investor_day_2026 - Enterprise Business Review scheduled Dec 8 2026, not yet held; no 2025/2026 investor day deck
  - policy/press_*_ira_negotiation - no J&J press release on IRA negotiation (Stelara/Xarelto/Imbruvica) found; only news coverage and MFP implementation plan PDF
  - policy/press_2025_wilson_nc_biologics_groundbreaking.md - jnj.com page is JS, no text extracted; jnj.com copy of 2026-01-08 MFN release also failed (investor.jnj.com copy saved)
  - policy/press_tariffs_trumprx_standalone - no separate J&J releases; covered by the 2026-01-08 agreement release

## AZN (companies)
- complete against the checklist
- worker notes:
  - MISLABELED: transcripts/2026Q1_transcript.md is NOT the Q1 2026 call. It is a second copy of the H1/Q2 2026 call held Jul 27 2026 (roic.ai page; Operator: 'Half 1 and Q2 2026 Webinar'). Do not cite it as Q1. AZN Q1 2026 call (Apr 29 2026) is missing; official AZ transcripts not published on astrazeneca.com
  - NOT QUOTABLE BY SPEAKER: transcripts/2025Q3_transcript.md (allmind.ai) has no speaker names (every turn is 'Speaker #n'). 2025Q4 and 2026Q2 (allmind.ai) mix 'Speaker #n' and named turns and repeat sentences; confirm the speaker before quoting
  - All transcripts (2025Q3, 2025Q4, 2026Q2) are third_party allmind.ai pages with site chrome; Seeking Alpha 403, MarketBeat 500, financialfilings 403
  - Q3 2026 transcript: results due 30 Oct 2026, not yet held
  - Investor day 2025-2026: none found (only Ambition 2030 investor day from 2024 listed on IR page; not collected)
  - Press release: IRA Medicare negotiation (Farxiga/Calquence) - no AZ official press release found
  - Press release: generic Farxiga - no AZ official press release found
  - Press release: TrumpRx - covered only within 2025-10-10 US government agreement release; no separate release

## AMGN (companies)
- transcript 2025Q3
- worker notes:
  - transcript 2025Q3: official IR (403), insidermonkey (truncated, discarded), fool.com URL not found, seekingalpha/gurufocus/investing/equibles 403, bullfincher 503
  - transcript 2026Q3: call not yet held as of 2026-10-17 (Amgen typically reports early Nov)
  - earnings_slides 2025Q3, 2025Q4, 2026Q1, 2026Q2: investors.amgen.com static-files/event pages return 403 to scripted fetch; no alternate official host found
  - investor_presentation JPM Jan 2026: only announcement notice found (saved as press); deck/webcast on investors.amgen.com 403
  - investor_presentation investor day/business review: not located
  - press release on IRA negotiation of Enbrel/Otezla (2026/2027 selection): no standalone Amgen release found; only 2022 IRA statement + 10-K/10-Q disclosures
  - press release on pharma tariffs: no standalone release; covered within 2025-12-19 MFN release

## GILD (companies)
- complete against the checklist
- worker notes:
  - NOT QUOTABLE: transcripts/2025Q3_transcript.md (fool.com) is garbled machine transcription about half normal length (e.g. 'Operator: Our next Rough.', operator lines attributed to analysts). Use for leads only; verify any quote against the webcast replay
  - transcripts/2025Q3,2025Q4,2026Q1: only third-party (fool.com); no official Gilead transcript found on IR site (Gilead posts prepared remarks, not full transcript).
  - transcripts/2026Q2: third-party roic.ai (Alphastreet copy was overwritten at same rel path; sources.jsonl has two rows for it); no fool.com version found.
  - transcripts/2026Q3: call not yet held as of 2026-10-17 (typically late Oct).
  - presentations: no standalone investor day / strategy day found (Gilead has not held one recently); JPM Jan 2026 deck saved.
  - policy: Gilead press statement on Biktarvy IRA selection (Jan 2026) not found; only news coverage.
  - policy: Gilead TrumpRx-specific release not found beyond Dec 19 2025 MFN agreement release; no tariff-specific Gilead release found.
  - policy: businesswire.com copies return HTTP 403 (used gilead.com instead).

## NVS (peers)
- complete against the checklist
- worker notes:
  - transcripts/2026Q1_transcript.md: no English full-text free source (only statementdog 202/Chinese, intellectia paywalled)
  - Q3 2026 transcript: not yet held (before Oct 17 2026)
  - policy: no Novartis release found on Kisqali/Cosentyx IRA negotiation (CMS list Jan 27 2026 only third-party)
  - policy: no Novartis release found specifically on tariffs or Kisqali/Leqvio pricing
  - presentations/2025-11_investor_day.md: only the 35-page deck at meet-novartis-management-2025-presentation.pdf; verify it is the full deck

## GSK (peers)
- complete against the checklist
- worker notes:
  - transcripts/2026Q2_transcript.md: not found (gsk.com transcript not located; gurufocus 403, statementdog 202)
  - presentations ViiV 2025-2026 investor deck: none found; only 2023-09 deck saved
  - policy: April 2026 definitive Section 232 agreement has no standalone press release (covered in Q1 2026 6-K)

## SNY (peers)
- complete against the checklist
- worker notes:
  - Sanofi-hosted press release for the May 2025 US$20bn US investment (only BioSpace third-party copy saved)
  - Tariff-specific standalone Sanofi press release (covered only in MFN release and 6-Ks)

## TAK (peers)
- complete against the checklist
- worker notes:
  - FY2025 Q4 official call transcript (takeda.com) not found; only MarketBeat third-party saved
  - Q4 FY2025 slides saved are the pre-amendment 2026-05-13 version (superseded by 2026-06-05 AMITIZA-amended version, URL not found)
  - Q4/Q1 data books (separate Excel/PDF) not collected
  - Takeda-specific MFN agreement / tariff / US manufacturing press release not found (no Takeda MFN deal located; $30B US pledge only on earnings call)
  - Entyvio-specific lifecycle/SC pen/biosimilar presentation not found
  - Q1 FY2026 official takeda.com Q&A transcript not found (Webull/Motley Fool copy saved)
  - Businesswire Q1 FY2026 press release blocked (403)

## REGN (peers)
- complete against the checklist
- worker notes:
  - Q2 2026 earnings slides (July 2026 corporate deck on reportify is JS page; IR site 403)
  - Official LSEG IR transcripts Q1/Q2 2026 (investor.regeneron.com 403; third-party copies saved)

## ALNY (peers)
- complete against the checklist
- worker notes:
  - Q2 2026 earnings slides (investor site 403 / not located)
  - Pricing/payer access vs Vyndamax press release 2025-2026 (none found as primary source; capella TTR webinar PDF fetch returned HTML wrapper, not saved)
  - Q2 2026 earnings slides (gcs-web IR 403)

## BBIO (peers)
- complete against the checklist
- worker notes:
  - Q2 2026 earnings slides (no Q2 deck on q4cdn; only June 2026 corporate deck saved)
  - Q1/Q2 2026 official IR transcript (using third-party MarketBeat/Webull Motley Fool copies)

## BOEHRINGER (peers, non-SEC)
- 2 documents

## ROCHE (peers, non-SEC)
- 12 documents

## Drugs
- label PDFs: DailyMed redirects scripted PDF downloads; labels are cited by section number from label_sections.md, which links the DailyMed setid.

