# 3D drug structures (Parker's artifact)

`structures.js` puts an experimental 3D structure above each drug name in the product compare columns
(`.nd-cmp-col > .nd-cmp-name`) on https://claude.ai/artifact/3vXs5G4P7JUi3uBgbhxn1i. Rendering is 3Dmol.js 2.5.5
from cdnjs, loaded on first use. Each card spins about its vertical axis and bobs and tilts in CSS; motion stops under
prefers-reduced-motion and while the card is off screen. Cards are cached per column name and moved back into the
column whenever Parker's React tree re-renders it, so WebGL contexts are not recreated.

Structures are Protein Data Bank crystal structures, not AlphaFold models (none of these drugs has an AlphaFold
entry; antibodies and small molecules are not in the AlphaFold database). Files live at `data/structures/<id>.pdb`
with waters, hydrogens and remarks stripped (10SB converted from mmCIF). Every caption names what the structure is and
links the PDB entry.

| Column | PDB | What is shown |
| --- | --- | --- |
| Repatha | 3H42 | PCSK9 bound to a neutralizing antibody Fab (the target; evolocumab itself has no public structure) |
| Praluent | 2P4E | PCSK9, the target |
| Leqvio | 2P4E | PCSK9, the target (Leqvio is an siRNA) |
| Lipfendra | 10SB | PCSK9 bound to a macrocyclic peptide from the enlicitide discovery series |
| Keytruda | 5DK3 | Pembrolizumab, full-length IgG4 |
| Opdivo | 5WT9 | PD-1 bound to the nivolumab Fab |
| Imfinzi | 5X8M | PD-L1 in complex with durvalumab |
| Tecentriq | 5XXY | PD-L1 bound to the atezolizumab Fab |
| Vyndaqel / Vyndamax | 3TCT | Transthyretin bound to tafamidis |
| Attruby | 4HIQ | Transthyretin V122I bound to acoramidis |
| Amvuttra | 1F41 | Transthyretin, the target (Amvuttra is an siRNA) |

Publish list: `assets/structures.js`, `data/structures/*.pdb`, and one script line in `index.html` after `haystack.js`.
