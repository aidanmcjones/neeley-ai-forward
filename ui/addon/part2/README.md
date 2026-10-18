# Part 2 add-on for Parker's page

Parker's judge-facing artifact (https://claude.ai/artifact/3vXs5G4P7JUi3uBgbhxn1i) is a hand-patched fork of this
app's version 10 bundle with no source in the repo. Aidan asked for Part 2 to be added to that page as a cued
follow-up, without replacing Parker's app. This folder is that addition: one script, built to
`ui/dist/assets/part2-addon.js`, that his page loads with a single line after his own bundle:

    <script defer src="./assets/part2-addon.js"></script>

What it does, in order:

1. Fetches `./data/part2/index.json`. If there is none, it does nothing (no chip).
2. Watches the chat (a `MutationObserver` on the page) for a Part 1 answer that has finished rendering: the turn
   has his "Ask next" chip row and no live thinking state.
3. Adds one chip to that row, "Part 2: CEO move for <company> (<ticker>)", for the pick the answer is showing.
   The label follows his pick tabs.
4. On click, appends a new chat turn after his list: the user bubble (his bubble classes), a short thinking state
   built from the Part 2 reasoning trace (his `th-live` and `th-done` classes), then the cached Part 2 answer from
   `data/part2/<T>.json` in his house style: `nd-lead` for the move, `nd-sec` sections, `nd-list` items,
   `nd-facts` and `nd-verdict` pairs, `sup.cite-n` footnote numbers and `details.cite-notes` source lists.
   Footnotes are numbered in first-appearance order across the answer, as his Part 1 is.
5. Answer order follows the case's Decide question: the move and its budget; the case (the Part 1 findings it
   rests on, with links back to his `#p1-finding-n` anchors, cost, return, the math step by step, net); two
   rejected alternatives; kill signals for months 6 to 12; why it will work and what the evidence can and cannot
   tell; anything a doctor or patient would see under the label "Student concept, not actual promotional
   material." with the rules checklist; the claims map; the numbers pill; "How it decided" (the trace).

It never touches his bundle, his `house.css` or his state. Its own styles are a small `<style>` block using his
colour variables, so dark mode follows his page. Every string on the page comes from the data files; the one
sentence this file writes is the student-concept label the case requires. Figures the exporter withheld show as
"figure withheld". Links are the sources' public URLs only (never the local viewer).

Build and check:

    cd ui
    ./node_modules/.bin/tsc -p addon/part2/tsconfig.json
    ./node_modules/.bin/vite build --config addon/part2/vite.config.ts

Published to his artifact with: his `index.html` plus the script line, `assets/part2-addon.js`, and
`data/part2/*.json` from `agent/ui_part2_export.py`.
