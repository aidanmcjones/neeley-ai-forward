// Trim layer: tags secondary content by its visible label so trim.css can cut or fade it.
// cut = hidden; fade = dimmed, full strength on hover. The "Full detail" pill turns both off.
(function () {
  var RULES = {
    // section cards, matched on the h2 in their header
    card: {
      "score anatomy": "fade",
      "ira cut check": "fade",
      "data pipeline": "cut",
      "derived tables inventory": "cut",
      "corpus trust": "fade",
      "where the data goes": "fade",
      "(c) revenue forecaster calibration": "fade",
      "(f) limits we state plainly": "fade"
    },
    // sub-blocks, matched on an h3 and applied to its parent
    block: {
      "why": "fade",
      "bucket key": "fade",
      "what the verifier checks": "fade",
      "who decides its fate": "fade",
      "pinned exhibits": "cut",
      "sources": "fade"
    },
    // table rows, matched on the row header
    row: {
      "boxed warning": "cut",
      "rems": "cut",
      "route": "cut",
      "approved uses": "fade",
      "ira status + mfp": "fade",
      "medicare spend (latest)": "fade"
    },
    // table columns, matched on the column header
    col: {
      "latest example": "fade",
      "why rejected": "cut",
      "src": "fade"
    },
    // small text, matched on the start of an element's own text:
    // [prefix, action, levels to climb before tagging, optional tag name]
    text: [
      ["live source card", "cut", 1],
      ["drafted from verified findings by deterministic", "cut", 0],
      ["charts follow the selected row", "cut", 0],
      ["obscurity:", "cut", 0],
      ["data/moat/", "fade", 0],
      ["list-like vs net-like", "cut", 0],
      ["fda-derived date", "fade", 0],
      ["company-stated loe dates", "fade", 0],
      ["trace: what was checked", "fade", 1],
      ["hover an option for the rule", "cut", 0],
      ["drafted from verified findings by rules", "cut", 2, "SPAN"],
      ["student concept, not actual", "fade", 0]
    ],
    // definition-list labels: tag the dt and its dd
    dt: { "why unseen": "fade", "peers": "fade" },
    // long tables, matched on their first column header: rows kept before the rest is cut
    rowLimit: { "finding": 5, "claim": 6 }
  };

  function norm(s) { return (s || "").replace(/\s+/g, " ").trim().toLowerCase(); }
  function tag(el, how) { if (el && !el.dataset.trim) el.dataset.trim = how; }
  function up(el, n) { while (el && n-- > 0) el = el.parentElement; return el; }
  function lookup(map, key) {
    for (var k in map) if (key === k || key.indexOf(k) === 0) return map[k];
  }

  // NEEDLE adaptation: the trim applies to the cockpit routes (#/cockpit...) only; the chat page at #/ is
  // already minimal and keeps its own layout. The pill shows only on cockpit routes.
  function onCockpit() { return /^#\/cockpit/.test(location.hash); }

  function apply() {
    btn.style.display = onCockpit() ? "" : "none";
    if (!onCockpit()) return;
    var main = document.getElementById("main");
    if (!main) return;

    main.querySelectorAll("section.shadow-card > header h2").forEach(function (h) {
      var how = lookup(RULES.card, norm(h.textContent));
      if (how) tag(h.closest("section"), how);
    });

    main.querySelectorAll("h3").forEach(function (h) {
      var how = RULES.block[norm(h.textContent)];
      if (!how) return;
      // a heading inside a big panel only takes the content right after it
      if (norm(h.parentElement.textContent).length > 1500) { tag(h, how); tag(h.nextElementSibling, how); }
      else tag(h.parentElement, how);
    });

    main.querySelectorAll('th[scope="row"]').forEach(function (th) {
      var how = RULES.row[norm(th.textContent)];
      if (how) tag(th.parentElement, how);
    });

    main.querySelectorAll("thead th, th[scope=col]").forEach(function (th) {
      var how = lookup(RULES.col, norm(th.textContent));
      if (!how || th.dataset.trim) return;
      var idx = Array.prototype.indexOf.call(th.parentElement.children, th) + 1;
      var table = th.closest("table");
      tag(th, how);
      table.querySelectorAll("tbody tr > :nth-child(" + idx + ")").forEach(function (td) { tag(td, how); });
    });

    main.querySelectorAll("p, div, span").forEach(function (el) {
      if (el.dataset.trim || el.children.length > 3) return;
      var t = norm(el.textContent).replace(/^[^a-z0-9(\/]+/, "").slice(0, 60);
      for (var i = 0; i < RULES.text.length; i++) {
        var r = RULES.text[i];
        if (r[3] && el.tagName !== r[3]) continue;
        // only a bare label may climb; a wrapper sharing its text would climb too far
        if (r[2] > 0 && el.children.length) continue;
        if (t.indexOf(r[0]) !== 0) continue;
        // a climbed match must stay a small note, never a whole panel
        var target = up(el, r[2]);
        if (target && norm(target.textContent).length <= 600) tag(target, r[1]);
        break;
      }
    });

    main.querySelectorAll("table").forEach(function (table) {
      var first = table.querySelector("thead th, th[scope=col]");
      var keep = first && lookup(RULES.rowLimit, norm(first.textContent));
      if (!keep) return;
      table.querySelectorAll("tbody > tr").forEach(function (tr, i) {
        if (i >= keep) tag(tr, "cut");
      });
    });

    main.querySelectorAll("dt").forEach(function (dt) {
      var how = RULES.dt[norm(dt.textContent)];
      if (how) { tag(dt, how); tag(dt.nextElementSibling, how); }
    });
  }

  function toggle() {
    var root = document.documentElement;
    var off = root.classList.toggle("trim-off");
    btn.textContent = off ? "Trimmed view" : "Full detail";
    btn.setAttribute("aria-pressed", off ? "true" : "false");
  }

  var btn = document.createElement("button");
  btn.type = "button";
  btn.className = "trim-toggle no-print";
  btn.textContent = "Full detail";
  btn.setAttribute("aria-pressed", "false");
  btn.addEventListener("click", toggle);

  var queued = false;
  new MutationObserver(function () {
    if (queued) return;
    queued = true;
    requestAnimationFrame(function () { queued = false; apply(); });
  }).observe(document.documentElement, { childList: true, subtree: true });

  document.addEventListener("DOMContentLoaded", function () {
    document.body.appendChild(btn);
    apply();
  });
  window.addEventListener("hashchange", apply);
})();
