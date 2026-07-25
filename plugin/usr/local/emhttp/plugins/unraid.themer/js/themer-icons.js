/* Unraid Themer — Custom Icons page (Settings > Utilities > Themer Icons).
 * External file on purpose: Unraid runs the .page body through its markdown
 * processor, which mangles multi-line inline <script> blocks. Config comes in
 * via data-* attributes on #ut-picker. Handlers are attached to window so the
 * inline onclick/oninput/onchange attributes can reach them. */
(function () {
  "use strict";

  var picker = document.getElementById("ut-picker");
  var UT_WEBURL = picker ? (picker.getAttribute("data-weburl") || "") : "";
  var UT_BUNDLED = [];
  try { UT_BUNDLED = JSON.parse((picker && picker.getAttribute("data-values")) || "[]"); } catch (e) {}
  var UT_TARGET = null;   // input being edited via the picker

  // Unraid's settings framework disables the Apply button until it sees a native
  // change event. The grid picker and file upload set input.value from script,
  // which fires no event — so Apply would stay greyed out. Enable it ourselves on
  // any edit, and dispatch a real change so Unraid's own tracking agrees.
  function utDirty(inp) {
    var b = document.querySelector('input[name="SAVE_ICONS"]');
    if (b) b.disabled = false;
    if (inp) { try { inp.dispatchEvent(new Event("change", { bubbles: true })); } catch (e) {} }
  }
  // typing / editing any per-slot field also arms Apply
  document.addEventListener("input", function (e) {
    if (e.target && e.target.getAttribute && e.target.getAttribute("data-key")) utDirty(null);
  });

  // Live preview for a bundled name (same-origin SVG). URLs and pasted SVG
  // markup are only previewed after Apply (the server validates them first).
  window.utIconPrev = function (inp) {
    var key = inp.getAttribute("data-key");
    var cell = document.querySelector('.ut-own[data-key="' + key + '"]');
    if (!cell) return;
    var span = cell.querySelector("span");
    if (!span) return;
    var v = (inp.value || "").trim().toLowerCase();
    if (v && UT_BUNDLED.indexOf(v) >= 0) {
      var u = UT_WEBURL + "/icons/svg/" + v + ".svg";
      span.style.webkitMask = 'url("' + u + '") center/contain no-repeat';
      span.style.mask = 'url("' + u + '") center/contain no-repeat';
      span.style.backgroundColor = "currentColor";
      span.style.opacity = "1";
      span.innerHTML = "";
    }
  };

  // Read the SVG client-side and put its markup into the slot's text field, so the
  // form stays a normal urlencoded POST (no multipart — Unraid's AJAX form submit
  // cannot send files and would hang). The server sanitizes pasted <svg> markup.
  window.utUploadPrev = function (inp, key) {
    var f = inp.files && inp.files[0];
    if (!f) return;
    var rd = new FileReader();
    rd.onload = function () {
      var svg = String(rd.result || "");
      if (svg.toLowerCase().indexOf("<svg") < 0) { alert("That doesn't look like an SVG file."); inp.value = ""; return; }
      var t = document.querySelector('input[data-key="' + key + '"]');
      if (t) { t.value = svg; utDirty(t); }
      var cell = document.querySelector('.ut-own[data-key="' + key + '"]');
      if (cell) {
        var s = cell.querySelector("span");
        if (s) {
          var uri = "data:image/svg+xml;utf8," + encodeURIComponent(svg);
          s.style.webkitMask = 'url("' + uri + '") center/contain no-repeat';
          s.style.mask = 'url("' + uri + '") center/contain no-repeat';
          s.style.backgroundColor = "currentColor"; s.style.opacity = "1"; s.innerHTML = "";
        }
      }
      inp.value = "";   // reset the file input; the markup now lives in the text field
    };
    rd.readAsText(f);
  };

  window.utOpenPicker = function (key) {
    UT_TARGET = document.querySelector('input[data-key="' + key + '"]');
    document.getElementById("ut-picker-backdrop").style.display = "block";
    document.getElementById("ut-picker").classList.add("open");
    var s = document.getElementById("ut-picker-search");
    s.value = ""; window.utPickerFilter(); s.focus();
  };

  window.utClosePicker = function () {
    document.getElementById("ut-picker-backdrop").style.display = "none";
    document.getElementById("ut-picker").classList.remove("open");
    UT_TARGET = null;
  };

  window.utPick = function (name) {
    if (UT_TARGET) { UT_TARGET.value = name; window.utIconPrev(UT_TARGET); utDirty(UT_TARGET); }
    window.utClosePicker();
  };

  window.utPickerFilter = function () {
    var q = (document.getElementById("ut-picker-search").value || "").toLowerCase().trim();
    var grid = document.getElementById("ut-picker-grid");
    var nodes = grid.children, visibleInGroup = 0, lastGroup = null;
    for (var i = 0; i < nodes.length; i++) {
      var el = nodes[i];
      if (el.classList.contains("ut-pick-group")) {
        if (lastGroup) lastGroup.style.display = visibleInGroup ? "" : "none";
        lastGroup = el; visibleInGroup = 0;
      } else {
        var s = el.getAttribute("data-search") || "";
        var show = !q || s.indexOf(q) >= 0;
        el.style.display = show ? "" : "none";
        if (show) visibleInGroup++;
      }
    }
    if (lastGroup) lastGroup.style.display = visibleInGroup ? "" : "none";
  };

  document.addEventListener("keydown", function (e) { if (e.key === "Escape") window.utClosePicker(); });
})();
