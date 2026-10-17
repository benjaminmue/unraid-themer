// Unraid Themer landing page. Progressive enhancement only: the page is
// complete without this file. Adds the light/dark theme filter and copy buttons.
(function () {
  'use strict';

  // Theme filter: cards carry data-mode="dark", "light" or "dark light".
  var filter = document.querySelector('.filter');
  var cards = document.querySelectorAll('#theme-list .theme');
  if (filter && cards.length) {
    filter.hidden = false;
    filter.addEventListener('click', function (e) {
      var btn = e.target.closest('button[data-filter]');
      if (!btn) return;
      var want = btn.getAttribute('data-filter');
      filter.querySelectorAll('button').forEach(function (b) {
        b.setAttribute('aria-pressed', b === btn ? 'true' : 'false');
      });
      cards.forEach(function (card) {
        var modes = card.getAttribute('data-mode').split(' ');
        card.hidden = want !== 'all' && modes.indexOf(want) === -1;
      });
    });
  }

  // Copy buttons for the install URLs.
  if (!navigator.clipboard) return;
  document.querySelectorAll('pre.copyable').forEach(function (pre) {
    var code = pre.querySelector('code');
    var btn = document.createElement('button');
    btn.type = 'button';
    btn.className = 'copy';
    btn.textContent = 'Copy';
    btn.setAttribute('aria-label', 'Copy URL');
    btn.addEventListener('click', function () {
      navigator.clipboard.writeText(code.textContent.trim()).then(function () {
        btn.textContent = 'Copied';
        setTimeout(function () { btn.textContent = 'Copy'; }, 1600);
      }, function () {
        btn.textContent = 'Select it';
      });
    });
    pre.appendChild(btn);
  });
})();
