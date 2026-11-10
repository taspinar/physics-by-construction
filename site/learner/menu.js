// The menu of the shared header on a narrow screen (F158, round 2 of Issue
// #462; docs/atelier.md, "Header"). Loaded synchronously right after the
// menu, so it runs before the first paint. The menu is a native <details>,
// open in the HTML: the navigation of a reader without scripts. Below the
// break point of the compact header (site.css: 40em) the script closes it
// at load and whenever the viewport narrows to it, opens it when the
// viewport widens past it, and closes it on Escape with the focus back on
// its toggle; the toggle's aria-expanded follows the menu. No request, no
// storage, no timer.
(function () {
  var menu = document.getElementById("pbc-menu");
  if (!menu || !window.matchMedia) { return; }
  var toggle = menu.querySelector("summary");
  var compact = window.matchMedia("(max-width: 39.99em)");
  function fit() { menu.open = !compact.matches; }
  function state() { toggle.setAttribute("aria-expanded", String(menu.open)); }
  menu.addEventListener("toggle", state);
  fit();
  state();
  compact.addEventListener("change", fit);
  menu.addEventListener("keydown", function (event) {
    if (event.key === "Escape" && compact.matches && menu.open) {
      menu.open = false;
      toggle.focus();
    }
  });
})();
