/* Needle in the Haystack: wordmark, favicon and copy for Parker's page. Plain script, no build. See README.md. */
(function () {
  "use strict";
  var WORD = "Needle in the Haystack";
  var MARK =
    '<svg class="hay-mark" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64" aria-hidden="true" focusable="false" shape-rendering="geometricPrecision">' +
    '<defs><linearGradient id="hay-g" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#F8D36B"/><stop offset="1" stop-color="#D4902A"/></linearGradient>' +
    '<linearGradient id="hay-s" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#FFFFFF"/><stop offset=".55" stop-color="#CBD3DE"/><stop offset="1" stop-color="#8A95A6"/></linearGradient></defs>' +
    '<path d="M12 30 7 22M22 25 20 16M44 25 48 16M52 31 58 24" stroke="var(--hay-ink,#3C145F)" stroke-width="3.6" stroke-linecap="round"/>' +
    '<path d="M12 30 7 22M22 25 20 16M44 25 48 16M52 31 58 24" stroke="#E9B94B" stroke-width="1.6" stroke-linecap="round"/>' +
    '<path d="M3 58C5 36 16 24 32 24s27 12 29 34Z" fill="url(#hay-g)" stroke="var(--hay-ink,#3C145F)" stroke-width="2.5" stroke-linejoin="round"/>' +
    '<path d="M26 56 36 44M40 54 50 42M30 38 38 30M46 48 54 42" stroke="#B8771F" stroke-width="1.8" stroke-linecap="round"/>' +
    '<path d="M16 49.3 57 7 20 52.7A2.6 2.6 0 0 1 16 49.3Z" fill="url(#hay-s)" stroke="var(--hay-ink,#3C145F)" stroke-width="1.6" stroke-linejoin="round"/>' +
    '<ellipse cx="21.5" cy="47.3" rx=".9" ry="2.3" transform="rotate(41 21.5 47.3)" fill="var(--hay-ink,#3C145F)"/>' +
    '<path class="hay-sheen" d="M24 44 54 11" stroke="#fff" stroke-width="1.3" stroke-linecap="round" opacity=".95"/>' +
    '<path d="M3 58C4 46 9 38 17 34c5 6 6 12 6 24Z" fill="url(#hay-g)" stroke="var(--hay-ink,#3C145F)" stroke-width="2.5" stroke-linejoin="round"/>' +
    '<path d="M9 54 15 46M12 40 17 36" stroke="#B8771F" stroke-width="1.8" stroke-linecap="round"/>' +
    '<path class="hay-glint" d="M57 .5 58.6 5.4 63.5 7 58.6 8.6 57 13.5 55.4 8.6 50.5 7 55.4 5.4Z" fill="#fff" stroke="var(--hay-ink,#3C145F)" stroke-width="1.1" stroke-linejoin="round"/>' +
    '<path class="hay-glint2" d="M49 12.5 49.7 14.3 51.5 15 49.7 15.7 49 17.5 48.3 15.7 46.5 15 48.3 14.3Z" fill="#fff" stroke="var(--hay-ink,#3C145F)" stroke-width=".8" stroke-linejoin="round"/>' +
    "</svg>";
  var ICON =
    "data:image/svg+xml," +
    encodeURIComponent(
      '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64"><rect width="64" height="64" rx="14" fill="#4D1979"/>' +
      '<path d="M8 56C10 38 19 29 32 29s22 9 24 27Z" fill="#E8B84A" stroke="#2A0E45" stroke-width="2.5" stroke-linejoin="round"/>' +
      '<path d="M18 49.3 55 10 22 52.7A2.6 2.6 0 0 1 18 49.3Z" fill="#E6EBF2" stroke="#2A0E45" stroke-width="1.6" stroke-linejoin="round"/>' +
      '<path d="M8 56C9 46 13 40 19 37c4 5 5 10 5 19Z" fill="#E8B84A" stroke="#2A0E45" stroke-width="2.5" stroke-linejoin="round"/>' +
      '<path d="M55 3 56.6 7.9 61.5 9.5 56.6 11.1 55 16 53.4 11.1 48.5 9.5 53.4 7.9Z" fill="#fff" stroke="#2A0E45" stroke-width="1.1" stroke-linejoin="round"/></svg>'
    );

  function wordmark() {
    var hs = document.querySelectorAll("h1.font-display");
    for (var i = 0; i < hs.length; i++) {
      var h = hs[i];
      for (var n = h.firstChild; n; n = n.nextSibling) {
        if (n.nodeType === 3 && n.nodeValue) n.nodeValue = "";
      }
      if (h.getAttribute("data-hay")) continue;
      h.setAttribute("data-hay", "1");
      h.setAttribute("aria-label", WORD);
      h.insertAdjacentHTML("beforeend", MARK + '<span class="hay-word">' + WORD + "</span>");
    }
  }

  function favicon() {
    var link = document.querySelector('link[rel="icon"]');
    if (!link) { link = document.createElement("link"); link.rel = "icon"; document.head.appendChild(link); }
    if (link.getAttribute("href") !== ICON) link.setAttribute("href", ICON);
    if (document.title !== WORD) document.title = WORD;
  }

  function copy() {
    var el = document.querySelector(".th-live .th-label");
    if (el && el.textContent === "Thinking") el.textContent = "Searching the haystack";
    var sums = document.querySelectorAll("details.th-done > summary");
    for (var i = 0; i < sums.length; i++) {
      var t = sums[i].textContent;
      if (t.indexOf("Thought for ") === 0) sums[i].textContent = "Searched the haystack for " + t.slice(12);
    }
    var ta = document.getElementById("chat-input");
    if (ta && ta.getAttribute("placeholder") === "Ask anything") ta.setAttribute("placeholder", "Search the haystack");
  }

  var queued = false;
  function apply() {
    queued = false;
    try { wordmark(); copy(); } catch (e) { /* never break Parker's page */ }
  }
  function schedule() {
    if (queued) return;
    queued = true;
    (window.requestAnimationFrame || window.setTimeout)(apply);
  }
  function start() {
    favicon();
    apply();
    new MutationObserver(schedule).observe(document.body, { childList: true, subtree: true, characterData: true });
    window.addEventListener("hashchange", schedule);
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", start); else start();
})();
