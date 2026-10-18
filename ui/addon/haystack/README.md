# Needle in the Haystack theme (Parker's artifact)

Theme layer for https://claude.ai/artifact/3vXs5G4P7JUi3uBgbhxn1i. Two plain files, no build:

- `haystack.css`: loads after `house.css`. Wordmark in Baloo 2 (white bubble letters outlined and extruded in the product
  purple), the glistening needle-in-haystack mark, needle underline on the active tab, gold glint for the thinking spark,
  needle glyph on the "Sharpest Needle" and Part 2 eyebrows, haystack glyph on the hero prompt, gold focus ring on the composer.
- `gen_mark.py` + `embed_mark.py`: the mark is generated, not hand drawn. `gen_mark.py <seed>` writes a dense straw haycock
  (170 body straws, 70 rim straws, needle, glint) as `mark.svg`; with `BODY=44 EDGE=22 OUT=mark_lite.svg` a lighter copy for the
  favicon and the hero glyph. `embed_mark.py` writes both into `haystack.js` (MARK, ICON), `haystack.css` (hero glyph) and the
  staged index.html favicon. Data URIs must escape `#` as `%23`.
- `haystack.js`: inserts the mark and the "Needle in the Haystack" word into Parker's `h1.font-display` (his text node is
  blanked, not removed, so React never loses a node), sets the favicon and title, and swaps three strings of copy:
  "Thinking" to "Searching the haystack", "Thought for Ns" to "Searched the haystack for Ns", the composer placeholder to
  "Search the haystack", the hero label "Part 1" to "Find the needle", and renames every visible "Part 2" to "The CEO Move" (tab, chips, eyebrow,
  the pre-filled prompt, footnote labels) through the same pass. Re-applies on every DOM change through one MutationObserver.

Publish list on the artifact: `assets/haystack.css`, `assets/haystack.js`, and in `index.html` the Google Fonts link for
Baloo 2 (replaces Honk), the stylesheet link after `house.css`, the script line after `part2-addon.js`, the favicon.
Parker's bundle, house.css and the Part 2 add-on are not touched.
