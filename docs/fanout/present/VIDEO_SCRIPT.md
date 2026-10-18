# Devpost video script (company-neutral)

**No company has been picked.** Slots: [COMPANY], [NEEDLE], [NEEDLE $], [PAGE], [N CAUGHT], [MOVE].

Length: Devpost did not state a limit (docs/kickoff_summary.md line 37). We assume 3 minutes and target 2:45 (about
410 spoken words at 150 a minute). If the form shows a different limit, cut from the 60-second version below.

Required content (Devpost overview, per docs/game_plan.md): introduce the team and name the track and case; explain
the problem and the solution; demo the project and how it uses AI; cover impact and any limitations or next steps.

## Shot list (2:45)

| Time | Visual | Audio (speaker: exact words) | Source for any number |
|---|---|---|---|
| 0:00 to 0:12 | Face cam, both of us; title slide | Parker: "We are Parker Kingsbury and Aidan Jones, Advanced track, pharmaceutical case. This is NEEDLE." | |
| 0:12 to 0:35 | Slide: a 10-K page with a footnote circled | Parker: "Wall Street reads the headline. The story is in the footnotes. But the case warns that AI working from memory gets numbers and quotes wrong. So we built a tool that uses AI to read, then refuses to trust it until code has checked every quote against its page." | Case PDF |
| 0:35 to 0:55 | Screen: League table tab | Aidan: "NEEDLE loads public filings, earnings calls and FDA labels. The AI proposes findings with exact quotes and dollar math. We deep-read four companies and checked all 238 quotes against their pages. All 238 pass." | RT2 "How I tested" |
| 0:55 to 1:25 | Screen: Findings tab, needle row | Parker: "For [COMPANY], our Sharpest Needle is [NEEDLE in two plain sentences]. That is worth about [NEEDLE $]." | docs/fanout/needle/ |
| 1:25 to 1:40 | Screen: click the citation; the page opens with the quote highlighted | Aidan: "Every number opens to its page. Here is page [PAGE], quote highlighted." | |
| 1:40 to 2:00 | Screen: AI caught tab | Aidan: "The AI was confidently wrong [N CAUGHT] times on [COMPANY], and 43 times across the four companies. The code caught each one. Anything it cannot confirm goes to a person, never straight to a slide." | *_ai_caught.jsonl row counts |
| 2:00 to 2:15 | Screen: Proof tab, hash recomputed | Aidan: "Our first backtest looked great. Our AI skeptics broke it, so we show the honest version: these are flags for people, not trading calls. We also sealed seven forecasts before the results came out." | docs/needle_gate2.md; docs/needle_sealed.md |
| 2:15 to 2:30 | Slide: Part 2 move | Parker: "As CEO, [MOVE]. If [KILL SIGNAL] happens in the first six months, we change course." | docs/fanout/part2/ |
| 2:30 to 2:40 | Screen: terminal running the onboard command | Aidan: "And it is reusable: one command points it at any drugmaker." | agent/needle/onboard.py |
| 2:40 to 2:45 | Face cam | Parker: "Next, we time it against an analyst and pilot it with one team. Thanks." | |

Disclosure line on the end card (text only): "Pre-built scaffold disclosed; everything case-specific built during
the event. AI: Claude (claude-opus-5-5) and Claude Code." (DISCLOSURE.md)

## 60-second cut

| Time | Visual | Audio |
|---|---|---|
| 0:00 to 0:08 | Face cam | Parker: "Parker and Aidan, Advanced track, pharma case. This is NEEDLE." |
| 0:08 to 0:25 | League table, then Findings | Aidan: "AI reads a drugmaker's filings and calls. Code checks every quote against its page. All 238 of our quotes pass." |
| 0:25 to 0:40 | Needle row, then click to the page | Parker: "For [COMPANY]: [NEEDLE], worth about [NEEDLE $]. Here is the page." |
| 0:40 to 0:52 | AI caught | Aidan: "The AI was confidently wrong 43 times. The code caught every one." |
| 0:52 to 1:00 | Part 2 slide | Parker: "As CEO, [MOVE]. Thanks." |

## Recording checklist

- 1920 x 1080, browser zoom so table text is readable on a phone
- Captions on (burned in or uploaded) for accessibility
- Cached run only, so nothing waits on the API
- No API keys, .env or terminal history with secrets on screen
- Record the screen first, then add voice, so a fumbled line is cheap to redo
- Upload as unlisted on YouTube or Vimeo by 12:30 pm Sunday; paste the link into Devpost
