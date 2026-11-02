// The hero of the home page (F134, ADR 021 decision 4). Loaded synchronously
// right after the hero's copy, so it runs before the first paint: it shows
// the pair the `hero` parameter names, or one at random, from the pairs the
// build embedded, and stacks a hidden copy of every pair in the same place,
// so the block is as tall as the longest pair and the swap moves nothing.
// No request, no storage, no timer, no listener: nothing changes later.
(function () {
  var copy = document.querySelector(".hero-copy");
  var data = document.getElementById("hero-pairs");
  if (!copy || !data) return;
  var pairs = JSON.parse(data.textContent);
  var asked = new URLSearchParams(window.location.search).get("hero");
  var pair = pairs.filter(function (p) { return p.id === asked; })[0] ||
    pairs[Math.floor(Math.random() * pairs.length)];
  pairs.forEach(function (p) {
    var ghost = document.createElement("div");
    ghost.className = "hero-pair hero-ghost";
    ghost.setAttribute("aria-hidden", "true");
    [["hero-headline", p.headline], ["hero-subtext", p.subtext]].forEach(function (part) {
      var line = ghost.appendChild(document.createElement("p"));
      line.className = part[0];
      line.textContent = part[1];
    });
    copy.appendChild(ghost);
  });
  copy.querySelector("h1").textContent = pair.headline;
  copy.querySelector(".hero-subtext").textContent = pair.subtext;
  copy.setAttribute("data-hero", pair.id);
})();
