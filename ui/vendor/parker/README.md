# Parker's UI fork (reference copy, not built)

Copied verbatim on 2026-10-18 from Parker's artifact https://claude.ai/artifact/3vXs5G4P7JUi3uBgbhxn1i
(version 1792301635-bcf9), which he built from the version 10 bundle of this app (ui PR #22 at e181231):

- `index-needle5.js`: his patched production bundle (a two-tab nav "Analysis" and "Findings table" at #/findings,
  a thinking state before the Part 1 answer, an analysis layout with a needle lead and ranked findings, a
  one-dimension product compare, footnote-style citations with "Sources (n)" notes). No source for it is in the
  repo; Parker has been asked to commit it so these can be merged properly.
- `house.css`: his style layer (Aptos typeface, quieter chrome, outlined hero chip, footnote and tab styles).
  The same file is linked by the live build from `ui/public/assets/house.css`.
- `index.html`: the page as his artifact served it.

Nothing here is imported by the build. Treat the JS as reference material only.
