/* Unraid Themer — branding (background image picker). External file on purpose:
 * Unraid runs the .page body through its markdown processor, which mangles
 * multi-line inline <script> blocks. */
(function () {
  "use strict";

  // Unraid's file browser. The global page does not expose openFileBrowser (it is
  // defined inline in the Docker/VM manager), so we ship our own copy. It fills the
  // target field with the picked path and fires a change event (which also arms the
  // settings Apply button). Depends on jQuery + jquery.filetree.js (loaded on the page).
  function openFileBrowser(el, top, root, filter, on_folders, on_files, close_on_select) {
    if (on_folders === undefined) on_folders = true;
    if (on_files === undefined) on_files = true;
    if (!filter && !on_files) filter = "HIDE_FILES_FILTER";
    if (!root.trim()) { root = "/mnt/user/"; top = "/mnt/"; }
    var p = $(el);
    if (p.next().hasClass("fileTree")) return null;          // already open
    var r = Math.floor((Math.random() * 10000) + 1);
    p.after("<span id='fileTree" + r + "' class='textarea fileTree'></span>");
    var ft = $("#fileTree" + r);
    ft.fileTree(
      { top: top, root: root, filter: filter, allowBrowsing: true },
      function (file) {
        if (on_files) { p.val(file); p.trigger("change"); if (close_on_select) ft.slideUp("fast", function () { ft.remove(); }); }
      },
      function (folder) {
        if (on_folders) { p.val(folder.replace(/\/\/+/g, "/")); p.trigger("change"); if (close_on_select) ft.slideUp("fast", function () { ft.remove(); }); }
      }
    );
    ft.css({ left: p.position().left, top: (p.position().top + p.outerHeight()), width: (p.width()) });
    $(document).mouseup(function (e) {
      if (!ft.is(e.target) && ft.has(e.target).length === 0) ft.slideUp("fast", function () { ft.remove(); });
    });
    p.bind("keydown", function () { ft.slideUp("fast", function () { ft.remove(); }); });
    ft.slideDown("fast");
  }

  // Pick an image file from the server (files only, starting at /mnt).
  window.utBrowseBg = function () {
    var f = document.getElementById("ut-bg-src");
    if (f) openFileBrowser(f, "/mnt/", "/mnt/", "", false, true, true);
  };
  window.utBrowseLogo = function () {
    var f = document.getElementById("ut-logo-src");
    if (f) openFileBrowser(f, "/mnt/", "/mnt/", "", false, true, true);
  };
})();
