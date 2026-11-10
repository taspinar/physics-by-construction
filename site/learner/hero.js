// The hero image of the home page (F158; ADR 021 decision 4 as amended).
// Loaded synchronously right after the hero's figure, so it runs before the
// first paint. It creates the one hero image: the one the `hero-image`
// parameter names, or one at random, from the images the build embedded;
// the default stands in <noscript> and is not requested. The headline and
// the subtext are the HTML's and are not touched. No other request, no
// storage, no timer, no listener: nothing changes later.
(function () {
  var asked = new URLSearchParams(window.location.search);
  function pick(items, id) {
    return items.filter(function (item) { return item.id === id; })[0] ||
      items[Math.floor(Math.random() * items.length)];
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
