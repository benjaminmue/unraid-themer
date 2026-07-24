/* ============================================================================
 * Unraid Themer — runtime helper
 * Loaded (deferred, same-origin) on every page when the theme is enabled.
 * Does the things CSS cannot:
 *   1. Docker "update available" badge — turns the (non-clickable) status name
 *      into a clear "?" marker with a hover tooltip.
 *   2. Shadow-DOM style bridge — lets a preset push selector-based CSS INTO the
 *      Unraid 7 Vue web-components (open shadow roots), which page CSS can't reach.
 * Everything is defensive: if a hook target is absent, it silently no-ops.
 * ========================================================================== */
(function () {
  "use strict";

  /* ---- 1. Docker "update available" badge -------------------------------- *
   * Unraid flags containers with a pending image update by giving the name
   * <span class="blue-text"> inside #docker_view. That is a STATUS, not a link.
   * We append a small "?" badge with a native tooltip so it reads as "info",
   * not "click me". The Docker tile re-renders async, so we re-run on mutation.
   */
  var BADGE_FLAG = "data-ut-badge";

  function decorateUpdates(root) {
    var scope = root && root.querySelectorAll ? root : document;
    var names = scope.querySelectorAll("#docker_view .blue-text:not([" + BADGE_FLAG + "])");
    for (var i = 0; i < names.length; i++) {
      var el = names[i];
      el.setAttribute(BADGE_FLAG, "1");
      var badge = document.createElement("span");
      badge.className = "ut-update-badge";
      badge.textContent = "?";
      badge.title = "Update available";
      badge.setAttribute("aria-label", "Update available");
      el.appendChild(document.createTextNode(" "));
      el.appendChild(badge);
    }
  }

  // one small style rule for the badge (page-level, safe)
  function injectBadgeStyle() {
    if (document.getElementById("ut-badge-style")) return;
    var s = document.createElement("style");
    s.id = "ut-badge-style";
    s.textContent =
      ".ut-update-badge{display:inline-flex;align-items:center;justify-content:center;" +
      "width:14px;height:14px;margin-left:2px;border-radius:50%;font-size:10px;" +
      "font-weight:700;line-height:1;color:#fff;background:var(--brand-orange,#c67100);" +
      "cursor:help;vertical-align:1px;font-family:var(--font-sans,sans-serif);}";
    (document.head || document.documentElement).appendChild(s);
  }

  /* ---- 2. Shadow-DOM style bridge ---------------------------------------- *
   * Unraid 7 web-components use OPEN shadow roots, so we can push a stylesheet
   * into them. A preset may define window.UNRAID_THEMER_SHADOW_CSS (a string)
   * to style component internals that CSS variables don't cover. No-op if unset.
   */
  function shadowCss() {
    return (typeof window !== "undefined" && window.UNRAID_THEMER_SHADOW_CSS) || "";
  }

  var _sheet = null;
  function getSheet() {
    var css = shadowCss();
    if (!css) return null;
    if (!_sheet && "adoptedStyleSheets" in Document.prototype && "replaceSync" in CSSStyleSheet.prototype) {
      try { _sheet = new CSSStyleSheet(); _sheet.replaceSync(css); } catch (e) { _sheet = null; }
    }
    return _sheet;
  }

  function styleShadowHosts(root) {
    var sheet = getSheet();
    if (!sheet) return;
    var scope = root && root.querySelectorAll ? root : document;
    // Unraid custom elements are prefixed unraid-* / uui-*
    var hosts = scope.querySelectorAll("[data-unraid], unraid-user-profile, unraid-header-os-version, uui-toaster");
    for (var i = 0; i < hosts.length; i++) {
      var sr = hosts[i].shadowRoot;
      if (sr && sr.adoptedStyleSheets && sr.adoptedStyleSheets.indexOf(sheet) === -1) {
        try { sr.adoptedStyleSheets = sr.adoptedStyleSheets.concat(sheet); } catch (e) {}
      }
    }
  }

  /* ---- 3. Dashboard CPU/Net charts -------------------------------------- *
   * SmoothieChart draws to a <canvas> with JS-hardcoded colors (light grey grid,
   * dark labels) — unreadable/harsh on dark themes and unreachable by CSS. Patch
   * the global chart objects to a subtle, theme-neutral grid + themed labels.
   */
  function patchCharts() {
    var ink = (getComputedStyle(document.documentElement)
      .getPropertyValue("--text-color") || "").trim() || "#888";
    ["cpuchart", "netchart"].forEach(function (n) {
      var c = window[n];
      if (c && c.options && c.options.grid) {
        c.options.grid.strokeStyle = "rgba(128,128,128,0.18)";
        c.options.grid.fillStyle = "transparent";
        if (c.options.labels) c.options.labels.fillStyle = ink;
      }
    });
  }

  /* ---- 4. Header web-component icons (bell + menu) ----------------------- *
   * The notifications bell and the hamburger menu live in Unraid's Vue header
   * (OPEN shadow DOM) with their own inline SVGs, unreachable by the CSS icon
   * set. When an icon set is active we swap just those SVGs to match. Fully
   * defensive: only runs on an active set, only replaces the <svg> visual (never
   * the button/handlers), and no-ops on any miss or error.
   */
  var UT_ICONED = "data-ut-iconed";
  var _svgCache = {};                 // name -> svg markup (or null)
  var _headerHits = {};               // icon -> swapped
  var _headerDone = false;            // both bell + menu handled → stop scanning

  // The bottom toolbar (search/logout/terminal/...) is Unraid's own icon font
  // (<b class="icon-u-*">) and is handled by the CSS icon set. Only the top-right
  // notifications bell and the account dropdown live in the Vue header as inline
  // SVGs — match those by accessible name and swap the SVG. Ordered, first wins.
  var HEADER_MAP = [
    [/notif|bell|alert|benachrichtig/,                         "bell"],
    [/dropdown|hamburger|navigation|account|\bmenu\b|menü/,    "menu"]
  ];

  function activeSet() {
    try {
      var l = document.querySelector('link[href*="/plugins/unraid.themer/icons/"][href*=".css"]');
      if (!l) return null;            // icon set = Default → leave the header alone
      var m = /\/icons\/([A-Za-z0-9_-]+)\.css/.exec(l.getAttribute("href") || "");
      return m ? m[1] : null;
    } catch (e) { return null; }
  }

  function loadSvg(name, set, cb) {
    if (name in _svgCache) { cb(_svgCache[name]); return; }
    if (typeof fetch !== "function") { cb(null); return; }
    var base = "/plugins/unraid.themer/icons/svg/";
    var urls = set ? [base + set + "/" + name + ".svg", base + name + ".svg"] : [base + name + ".svg"];
    (function tryNext(i) {
      if (i >= urls.length) { _svgCache[name] = null; cb(null); return; }
      fetch(urls[i]).then(function (r) { return r.ok ? r.text() : Promise.reject(0); })
        .then(function (t) { if (t.indexOf("<svg") < 0) throw 0; _svgCache[name] = t; cb(t); })
        .catch(function () { tryNext(i + 1); });
    })(0);
  }

  function collectShadowRoots(root, acc, depth) {
    if (depth > 8) return acc;
    var els;
    try { els = root.querySelectorAll("*"); } catch (e) { return acc; }
    for (var i = 0; i < els.length; i++) {
      var sr = els[i].shadowRoot;
      if (sr) { acc.push(sr); collectShadowRoots(sr, acc, depth + 1); }
    }
    return acc;
  }

  function accName(el) {
    try {
      var n = el.getAttribute("aria-label") || el.getAttribute("title") || el.title || "";
      if (!n) { var sr = el.querySelector(".sr-only, [class*='sr-only']"); if (sr) n = sr.textContent || ""; }
      return (n + "").toLowerCase();
    } catch (e) { return ""; }
  }

  function swapIcon(target, markup) {
    try {
      if (!target || target.getAttribute(UT_ICONED)) return false;
      var oldSvg = target.querySelector("svg");
      if (!oldSvg) return false;
      var neu = new DOMParser().parseFromString(markup, "image/svg+xml").documentElement;
      if (!neu || neu.nodeName.toLowerCase() !== "svg") return false;
      // Carry the original's sizing. Header SVGs size via classes (Tailwind
      // h-6 w-6), not width/height attrs, so copy the class first and only add
      // explicit width/height when the original actually had them.
      var cls = oldSvg.getAttribute("class"); if (cls) neu.setAttribute("class", cls);
      var w = oldSvg.getAttribute("width"); if (w) neu.setAttribute("width", w);
      var h = oldSvg.getAttribute("height"); if (h) neu.setAttribute("height", h);
      neu.style.color = "currentColor";
      oldSvg.replaceWith(document.importNode(neu, true));
      target.setAttribute(UT_ICONED, "1");
      return true;
    } catch (e) { return false; }
  }

  function markHeaderHit(icon) {
    _headerHits[icon] = true;
    if (_headerHits.bell && _headerHits.menu) _headerDone = true;
  }

  function themeHeaderIcons() {
    if (_headerDone) return;
    var set = activeSet();
    if (!set) return;
    var roots = collectShadowRoots(document, [document], 0);
    for (var r = 0; r < roots.length; r++) {
      var cand;
      try { cand = roots[r].querySelectorAll('button, a, [role="button"]'); } catch (e) { continue; }
      for (var i = 0; i < cand.length; i++) {
        var el = cand[i];
        if (el.getAttribute(UT_ICONED) || !el.querySelector("svg")) continue;
        var n = accName(el);
        if (!n) continue;
        for (var k = 0; k < HEADER_MAP.length; k++) {
          if (HEADER_MAP[k][0].test(n)) {
            (function (target, icon) {
              loadSvg(icon, set, function (m) { if (m && swapIcon(target, m)) markHeaderHit(icon); });
            })(el, HEADER_MAP[k][1]);
            break;
          }
        }
      }
    }
  }

  /* ---- run + observe ----------------------------------------------------- */
  function run(root) {
    injectBadgeStyle();
    decorateUpdates(root);
    styleShadowHosts(root);
    patchCharts();
  }

  function start() {
    run(document);
    // Charts are created by the dashboard script after us → retry a few times.
    [400, 1200, 3000].forEach(function (d) { setTimeout(patchCharts, d); });
    // The Vue header (unraid-user-profile) mounts async from ES modules and may
    // appear well after load → try the bell/menu swap over a longer window.
    themeHeaderIcons();
    [600, 1500, 3000, 5000, 8000, 12000].forEach(function (d) { setTimeout(themeHeaderIcons, d); });
    // Docker tile + web-components mount/re-render after load → observe.
    if (window.MutationObserver) {
      var obs = new MutationObserver(function (muts) {
        for (var i = 0; i < muts.length; i++) {
          if (muts[i].addedNodes && muts[i].addedNodes.length) {
            run(document);
            if (!_headerDone) themeHeaderIcons();  // catch the late-mounting header
            return;
          }
        }
      });
      obs.observe(document.documentElement, { childList: true, subtree: true });
    }
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", start, { once: true });
  } else {
    start();
  }
})();
