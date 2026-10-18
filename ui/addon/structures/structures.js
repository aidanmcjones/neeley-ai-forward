/* Needle in the Haystack: 3D structures above each drug name in the product compare.
   Experimental structures from the Protein Data Bank (data/structures/<id>.pdb, waters and hydrogens stripped),
   rendered with 3Dmol.js (loaded from cdnjs on first use). Each card spins, and bobs and tilts in CSS; both
   stop under prefers-reduced-motion and while the card is off screen. Parker's bundle is not touched: cards are
   inserted into his .nd-cmp-col columns and moved back in whenever he re-renders them. */
(function () {
  "use strict";
  var LIB = "https://cdnjs.cloudflare.com/ajax/libs/3Dmol/2.5.5/3Dmol-min.js";
  var DATA = "./data/structures/";
  var TARGET = "#8C6FD1", TARGET2 = "#5AB8AE", DRUG = "#E8B84A";
  var SUGARS = { NAG: 1, FUC: 1, MAN: 1, BMA: 1, GLC: 1, FRU: 1, SO4: 1, GOL: 1, NA: 1, HG: 1, SIN: 1, GOA: 1, EDO: 1, CL: 1, ZN: 1 };
  /* Column name (as Parker renders it) to a structure. "drug" names the chains or ligand that are the drug; the rest is the target. */
  var MAP = [
    { match: /^Repatha/, id: "3H42", what: "PCSK9, the target of Repatha, bound to a neutralizing antibody Fab", chains: { H: TARGET2, L: TARGET2 } },
    { match: /^Praluent/, id: "2P4E", what: "PCSK9, the target of Praluent" },
    { match: /^Leqvio/, id: "2P4E", what: "PCSK9, the target of Leqvio" },
    { match: /^Lipfendra/, id: "10SB", what: "PCSK9 bound to a macrocyclic peptide from the Lipfendra (enlicitide) discovery series", ligands: true },
    { match: /^Keytruda/, id: "5DK3", what: "Pembrolizumab (Keytruda), full-length IgG4 antibody", all: DRUG },
    { match: /^Opdivo/, id: "5WT9", what: "PD-1 bound to the nivolumab (Opdivo) Fab", chains: { H: DRUG, L: DRUG } },
    { match: /^Imfinzi/, id: "5X8M", what: "PD-L1 in complex with durvalumab (Imfinzi)" },
    { match: /^Tecentriq/, id: "5XXY", what: "PD-L1 bound to the atezolizumab (Tecentriq) Fab", chains: { H: DRUG, L: DRUG } },
    { match: /^Vyndaqel/, id: "3TCT", what: "Transthyretin bound to tafamidis (Vyndaqel)", ligands: true },
    { match: /^Attruby/, id: "4HIQ", what: "Transthyretin V122I bound to acoramidis (Attruby)", ligands: true },
    { match: /^Amvuttra/, id: "1F41", what: "Transthyretin, the target of Amvuttra" }
  ];
  var STYLE =
    ".mol-wrap{display:grid;gap:4px;margin:-4px 0 4px}" +
    ".mol{position:relative;width:100%;height:150px;border-radius:8px;overflow:hidden;background:radial-gradient(70% 70% at 50% 45%,rgb(var(--purple)/.10),transparent 72%)}" +
    ".mol canvas{outline:none}" +
    ".mol-stage{width:100%;height:100%;animation:mol-bob 7s ease-in-out infinite;will-change:transform}" +
    ".mol-wrap:nth-of-type(odd) .mol-stage{animation-delay:-2.3s}" +
    ".mol-cap{margin:0;font-size:11px;line-height:1.4;color:rgb(var(--muted))}" +
    ".mol-cap a{color:rgb(var(--purple));text-decoration:none}.mol-cap a:hover{text-decoration:underline}" +
    ".mol-tag{display:block;font-weight:700;letter-spacing:.06em;text-transform:uppercase;font-size:10px;color:rgb(var(--muted))}" +
    "@keyframes mol-bob{0%,100%{transform:translateY(0) rotate(-1.5deg) scale(1)}50%{transform:translateY(-5px) rotate(1.5deg) scale(1.03)}}" +
    "@media (prefers-reduced-motion:reduce){.mol-stage{animation:none}}" +
    "@media print{.mol-wrap{display:none}}";
  var reduce = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  var lib = null, files = {}, cards = {};
  function loadLib() {
    if (lib) return lib;
    lib = new Promise(function (ok, bad) {
      if (window.$3Dmol) return ok(window.$3Dmol);
      var s = document.createElement("script"); s.src = LIB; s.async = true;
      s.onload = function () { ok(window.$3Dmol); }; s.onerror = function () { bad(new Error("3Dmol failed to load")); };
      document.head.appendChild(s);
    });
    return lib;
  }
  function loadFile(id) {
    return files[id] || (files[id] = fetch(DATA + id + ".pdb").then(function (r) { if (!r.ok) throw new Error(id); return r.text(); }));
  }
  function el(tag, cls, text) { var e = document.createElement(tag); if (cls) e.className = cls; if (text) e.textContent = text; return e; }
  function style(entry, viewer) {
    viewer.setStyle({}, { cartoon: { color: entry.all || TARGET } });
    if (entry.chains) for (var c in entry.chains) viewer.setStyle({ chain: c }, { cartoon: { color: entry.chains[c] } });
    viewer.setStyle({ hetflag: true }, {});
    if (entry.ligands) {
      viewer.setStyle({ hetflag: true, not: { resn: Object.keys(SUGARS) } }, { stick: { color: DRUG, radius: 0.32 }, sphere: { color: DRUG, scale: 0.28 } });
    }
  }
  function build(name, entry) {
    var wrap = el("div", "mol-wrap"); wrap.setAttribute("data-mol", name);
    var mol = el("div", "mol"); var stage = el("div", "mol-stage"); mol.appendChild(stage); wrap.appendChild(mol);
    var cap = el("p", "mol-cap"); cap.appendChild(el("span", "mol-tag", "Crystal structure ")); cap.appendChild(document.createTextNode(entry.what + ". "));
    var a = el("a", null, "PDB " + entry.id); a.href = "https://www.rcsb.org/structure/" + entry.id; a.target = "_blank"; a.rel = "noopener"; cap.appendChild(a); wrap.appendChild(cap);
    var card = { wrap: wrap, stage: stage, viewer: null, visible: true };
    cards[name] = card;
    Promise.all([loadLib(), loadFile(entry.id)]).then(function (r) {
      var $3Dmol = r[0];
      var v = $3Dmol.createViewer(stage, { backgroundAlpha: 0, antialias: true });
      v.addModel(r[1], "pdb");
      style(entry, v);
      v.zoomTo({ hetflag: false }); v.zoom(1.2); v.render();
      card.viewer = v;
      spin(card);
      if (window.IntersectionObserver) new IntersectionObserver(function (es) { card.visible = es[0].isIntersecting; spin(card); }, { threshold: 0.05 }).observe(wrap);
    }).catch(function () { cap.textContent = "Structure unavailable: PDB " + entry.id; });
    return wrap;
  }
  function spin(card) {
    if (!card.viewer) return;
    if (card.visible && !reduce) card.viewer.spin("y", 0.55); else card.viewer.spin(false);
  }
  function place() {
    var cols = document.querySelectorAll(".nd-cmp-col");
    for (var i = 0; i < cols.length; i++) {
      var col = cols[i], nameEl = col.querySelector(".nd-cmp-name");
      if (!nameEl || col.querySelector(".mol-wrap")) continue;
      var text = (nameEl.textContent || "").trim(), title = (nameEl.getAttribute("title") || "").trim();
      var name = text || title, entry = null;
      for (var k = 0; k < MAP.length && !entry; k++) if (MAP[k].match.test(text) || MAP[k].match.test(title)) entry = MAP[k];
      if (!entry) continue;
      var card = cards[name];
      var wrap = card ? card.wrap : build(name, entry);
      col.insertBefore(wrap, nameEl);
      if (card && card.viewer) { card.viewer.resize(); card.viewer.render(); }
    }
  }
  var queued = false;
  function schedule() { if (queued) return; queued = true; (window.requestAnimationFrame || setTimeout)(function () { queued = false; try { place(); } catch (e) { /* never break the page */ } }); }
  function start() {
    var st = document.createElement("style"); st.id = "mol-style"; st.textContent = STYLE; document.head.appendChild(st);
    schedule();
    new MutationObserver(schedule).observe(document.body, { childList: true, subtree: true });
    window.addEventListener("hashchange", schedule);
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", start); else start();
})();
