# UI trim layer

Parker asked for a broad trim: cut or fade up to 40% of the detail on every NEEDLE screen, so the
headline needle, dollar impact, stance and citations carry the page. This folder holds that trim as
a drop-in layer for the React cockpit build. It does not change the bundle or `fit.css`.

- `trim.js` tags secondary content by its visible label (card heading, h3, table row or column
  header, small-text prefix). It reruns on DOM changes, so it survives route and company switches.
- `trim.css` hides `data-trim="cut"` and dims `data-trim="fade"` (full strength on hover).
- A "Full detail" pill (bottom right) turns the trim off for judge Q&A. Hidden in print.

## Wire it into the build

Copy both files into the Vite app's `public/assets/`, then add after the `fit.css` link in
`index.html`:

```html
<link rel="stylesheet" href="./assets/trim.css">
<script src="./assets/trim.js"></script>
```

## What it trims

| Screen | Cut | Faded |
|---|---|---|
| Briefing | empty live source card, engine footnote, "charts follow row" line, findings past 5 | score anatomy, why unseen, peers line, Why list |
| Product | boxed warning, REMS, route rows; obscurity lines; list-vs-net footnote | approved uses, IRA status, timeline legend |
| Forces | source-file footnote, latest example column | abnormal return column, IRA cut check |
| Proof | why-rejected column, rejected claims past 6 | verifier checklist, (c) calibration, (f) limits |
| Data moat | data pipeline, derived tables inventory | bucket key, corpus trust, where the data goes |
| Memo | rules footnote box, empty pinned exhibits | who decides its fate, sources |
| Ask | none | trace line |

Rules live at the top of `trim.js`; renaming a card heading in the app means updating its rule.

Preview (private to Parker until shared): https://claude.ai/artifact/S42wnbZcb2inf26s864eEe
