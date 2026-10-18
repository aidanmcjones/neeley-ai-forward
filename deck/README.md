# Pitch deck

- `Needle_in_the_Haystack_Pitch_Deck.pptx`: the seven-slide deck (six presented, one appendix). Speaker notes carry the Aidan and Parker talk track. The slideshow is set to run in a window for recording.
- `build_deck.py`: builds the deck with python-pptx (`python build_deck.py <out.pptx> <qr.png> hay.png`). It writes the QR code for the public demo, https://aidanmcjones.github.io/needle-demo/. The structure animation path (`MOL`) is absolute to the build machine; point it at `deck/structures/` to rebuild elsewhere.
- `talk_track.py`: the speaker notes as plain text.
- `structures/`: looping animations of the PDB structures on the product slide (3H42, 2P4E, 10SB), rendered with 3Dmol.js. These are Protein Data Bank crystal structures, not AlphaFold models.
- Headings use Baloo 2 (SIL Open Font License); install it for the intended look, or PowerPoint falls back to another font.

Every number on a slide links to its filing or label page. Asterisks mark labelled assumptions.
