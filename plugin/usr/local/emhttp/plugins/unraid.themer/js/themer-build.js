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

  // live preview when the swatch changes
  window.utSync = function (k, hex) {
    var t = document.getElementById("cx_" + k);
    if (t) t.value = hex;
    apply(k, hex);
  };
  // live preview when the hex/rgb text changes
  window.utText = function (k, val) {
    var hex = utHex(val);
    if (hex) {
      var p = document.getElementById("cp_" + k);
      if (p) p.value = hex;
      apply(k, hex);
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
  }

  function boot() { if (document.getElementById("cp_bg")) setTimeout(init, 120); }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", boot, { once: true });
  else boot();
})();
