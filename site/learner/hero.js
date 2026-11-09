// The hero of the home page (F134, F158; ADR 021 decision 4 as amended).
// Loaded synchronously right after the hero's figure, so it runs before the
// first paint. It shows the pair the `hero` parameter names, or one at
// random, and stacks a hidden copy of every pair in the same place, so the
// block is as tall as the longest pair and the swap moves nothing. Then,
// independently, it creates the one hero image: the one the `hero-image`
// parameter names, or one at random, from the images the build embedded;
// the default stands in <noscript> and is not requested. No other request,
// no storage, no timer, no listener: nothing changes later.
(function () {
  var asked = new URLSearchParams(window.location.search);
  function pick(items, id) {
    return items.filter(function (item) { return item.id === id; })[0] ||
      items[Math.floor(Math.random() * items.length)];
  }
  var copy = document.querySelector(".hero-copy");
  var pairs = document.getElementById("hero-pairs");
  if (copy && pairs) {
    pairs = JSON.parse(pairs.textContent);
    var pair = pick(pairs, asked.get("hero"));
    pairs.forEach(function (p) {
      var ghost = copy.appendChild(document.createElement("div"));
      ghost.className = "hero-pair hero-ghost";
      ghost.setAttribute("aria-hidden", "true");
      [["hero-headline", p.headline], ["hero-subtext", p.subtext]].forEach(function (part) {
        var line = ghost.appendChild(document.createElement("p"));
        line.className = part[0];
        line.textContent = part[1];
      });
    });
    copy.querySelector("h1").textContent = pair.headline;
    copy.querySelector(".hero-subtext").textContent = pair.subtext;
    copy.setAttribute("data-hero", pair.id);
  }
  var figure = document.getElementById("hero-figure");
  var images = document.getElementById("hero-images");
  if (figure && images) {
    var chosen = pick(JSON.parse(images.textContent), asked.get("hero-image"));
    var image = document.createElement("img");
    image.className = "hero-image";
    image.alt = chosen.alt;
    image.width = chosen.width;
    image.height = chosen.height;
    image.src = chosen.src;
    figure.appendChild(image);
    figure.setAttribute("data-hero-image", chosen.id);
  }
})();
