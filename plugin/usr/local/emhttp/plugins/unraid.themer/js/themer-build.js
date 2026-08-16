/* Unraid Themer — theme builder (color picker) on the settings page.
 * External file on purpose: Unraid runs the .page body through markdown, which
 * mangles inline scripts. Handlers are on window for the inline oninput/onclick
 * attributes; on load the pickers are initialised from the CURRENT running theme. */
(function () {
  "use strict";

  function utHex(v) {
    v = (v || "").trim();
    var m = v.match(/^#?([0-9a-fA-F]{6})$/);
    if (m) return "#" + m[1].toLowerCase();
    m = v.match(/rgba?\((\d{1,3})[ ,]+(\d{1,3})[ ,]+(\d{1,3})/i);
    if (m) {
      function h(n) { return ("0" + Math.min(255, parseInt(n, 10)).toString(16)).slice(-2); }
      return "#" + h(m[1]) + h(m[2]) + h(m[3]);
    }
    return null;
  }

  // map each builder slot to the CSS custom properties it drives
  var MAP = {
    bg: ["--background-color", "--ui-bg", "--background"],
    bg2: ["--mild-background-color", "--card", "--popover"],
    surface: ["--header-background-color", "--ui-bg-elevated", "--table-header-background-color"],
    text: ["--text-color", "--ui-text", "--foreground"],
    dim: ["--alt-text-color", "--ui-text-muted"],
    border: ["--border-color", "--ui-border", "--border"],
    accent: ["--link-text-color", "--brand-orange", "--orange-500", "--ui-primary", "--primary", "--ring"],
    accent2: ["--brand-red", "--orange-800", "--accent"]
  };

  function apply(k, hex) {
    var vs = MAP[k] || [];
    for (var i = 0; i < vs.length; i++) document.documentElement.style.setProperty(vs[i], hex);
  }

  // --- WCAG contrast check -------------------------------------------------
  // Eight freely chosen colours reliably produce unreadable pairings, and the
  // generated preset hard-codes white button labels — so a light accent yields
  // buttons nobody can read. These are the pairs that carry actual text.
  var PAIRS = [
    { label: "Text on background", fg: "text", bg: "bg" },
    { label: "Muted text on background", fg: "dim", bg: "bg" },
    { label: "Links (accent) on background", fg: "accent", bg: "bg" },
    { label: "Text on surface", fg: "text", bg: "surface" },
    // the generated preset picks the button label automatically (see
    // themer_button_text in UnraidThemer.page) — mirror that choice here
    { label: "Button label on accent", fg: "auto", bg: "accent" }
  ];

  function lum(hex) {
    var c = [1, 3, 5].map(function (i) {
      var v = parseInt(hex.substr(i, 2), 16) / 255;
      return v <= 0.03928 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4);
    });
    return 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2];
  }
  function ratio(a, b) {
    var l1 = lum(a), l2 = lum(b);
    return (Math.max(l1, l2) + 0.05) / (Math.min(l1, l2) + 0.05);
  }
  // Pick the readable label colour for a filled button: the theme background if
  // it beats white, otherwise white. Same rule as the PHP side.
  function buttonText(accent) {
    var bgField = slotHex("bg") || "#000000";
    if (ratio(bgField, accent) >= 4.5) return bgField;
    return ratio("#000000", accent) >= ratio("#ffffff", accent) ? "#000000" : "#ffffff";
  }

  function slotHex(slot) {
    if (slot.charAt(0) === "#") return slot;
    var t = document.getElementById("cx_" + slot);
    return t ? utHex(t.value) : null;
  }

  window.utContrast = function () {
    var box = document.getElementById("ut-contrast");
    if (!box) return;
    var out = "";
    for (var i = 0; i < PAIRS.length; i++) {
      var p = PAIRS[i], bg = slotHex(p.bg);
      var fg = p.fg === "auto" ? (bg && buttonText(bg)) : slotHex(p.fg);
      if (!fg || !bg) continue;
      // judge the ROUNDED value, otherwise 4.4787 prints "4.5:1" and fails
      var r = Math.round(ratio(fg, bg) * 10) / 10;
      // 4.5 is AA for body text, 7 is AAA; below 4.5 it is a real problem
      var verdict = r >= 7 ? "AAA" : (r >= 4.5 ? "AA" : (r >= 3 ? "large text only" : "unreadable"));
      var ok = r >= 4.5;
      out += "<span class='ut-cc" + (ok ? "" : " bad") + "' title='" + p.label + "'>"
           + "<i style='background:" + bg + ";color:" + fg + ";'>Aa</i>"
           + p.label + " <strong>" + r.toFixed(1) + ":1</strong> " + verdict + "</span>";
    }
    box.innerHTML = out;
  };

  // live preview when the swatch changes
  window.utSync = function (k, hex) {
    var t = document.getElementById("cx_" + k);
    if (t) t.value = hex;
    apply(k, hex);
    window.utContrast();
  };
  // live preview when the hex/rgb text changes
  window.utText = function (k, val) {
    var hex = utHex(val);
    if (hex) {
      var p = document.getElementById("cp_" + k);
      if (p) p.value = hex;
      apply(k, hex);
      window.utContrast();
    }
  };
  window.utFont = function (v) {
    document.documentElement.style.setProperty("--font-sans", v || "");
    document.body.style.fontFamily = v || "";
  };

  // set both inputs for a slot (no live-apply — just populate)
  function set(k, val) {
    var hex = utHex(val);
    if (!hex) return;
    var p = document.getElementById("cp_" + k), t = document.getElementById("cx_" + k);
    if (p) p.value = hex;
    if (t) t.value = hex;
  }

  // initialise the pickers from the CURRENTLY applied theme
  function init() {
    try {
      var cs = getComputedStyle(document.documentElement);
      var b = getComputedStyle(document.body);
      // bg/text from the actually-rendered element colors (always resolved)
      set("bg", b.backgroundColor);
      set("text", b.color);
      // the rest from the theme's CSS variables
      set("bg2", cs.getPropertyValue("--mild-background-color"));
      set("surface", cs.getPropertyValue("--header-background-color"));
      set("dim", cs.getPropertyValue("--alt-text-color"));
      set("border", cs.getPropertyValue("--border-color"));
      set("accent", cs.getPropertyValue("--link-text-color"));
      set("accent2", cs.getPropertyValue("--brand-red"));
    } catch (e) {}
    window.utContrast();
  }

  function boot() { if (document.getElementById("cp_bg")) setTimeout(init, 120); }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", boot, { once: true });
  else boot();
})();
