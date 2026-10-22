// The course atlas, enhanced (F126). Without this script the atlas is
// complete (F125): every concept box links to its panel, the panels link
// every lesson, the views link every lesson by its methods, and the course
// index below lists them all. This script adds, in the two places the page
// declares for it (#atlas-controls before the map, #atlas-selection after
// it):
//
//   - selection: choosing a concept box (pointer or Enter) marks the
//     concept, its relationships, and the concepts at their other ends, and
//     shows its panel under the map; hovering or focusing a box previews
//     the same marks; Escape clears them;
//   - what the map shows: every relationship, the concepts alone, the
//     prerequisites, or the conceptual connections;
//   - zoom, never below the natural size, so that no label shrinks;
//   - a region selector: one course, one path, or the views, focused in the
//     map box with the list of its concepts below;
//   - filters by course, path, method, difficulty, and publication, kept in
//     step with the filters of the course index (learner/path.js) by the
//     events "pbc:set-filters" and "pbc:filters";
//   - the switch above the map marks the part of the page in view and moves
//     keyboard focus to the part it leads to.
//
// It stores nothing, makes no request, sets no cookie, and animates
// nothing. What a selection or a filter shows comes from the page: the
// edges' data-from, data-to, and data-kind, and the data attributes of the
// concept boxes and the lesson plates that the build writes. It draws no
// edge and changes no data; leaving the page forgets every choice.

const map = document.getElementById("atlas-map");
const controlsBox = document.getElementById("atlas-controls");
const selectionBox = document.getElementById("atlas-selection");
const svg = map?.querySelector("svg.atlas-svg");

// The zoom levels; 1 is the natural size, and none is smaller.
const ZOOMS = [1, 1.25, 1.5, 2];
// Below this width the map opens on one region (the phone's focused view).
const NARROW = "(max-width: 40em)";
// The margin around a focused region, in units of the drawing.
const REGION_PAD = 3;
const VIEWS = "views";

const KINDS = {
  all: { label: "All relationships", edges: ["prerequisite", "conceptual", "capstone"] },
  concepts: { label: "Concepts only", edges: [] },
  prerequisite: { label: "Prerequisites", edges: ["prerequisite"] },
  conceptual: { label: "Conceptual connections", edges: ["conceptual"] },
};

const FILTERS = ["course", "path", "method", "difficulty", "state"];

function element(tag, attributes = {}, ...children) {
  const item = document.createElement(tag);
  for (const [name, value] of Object.entries(attributes)) {
    if (name === "text") {
      item.textContent = value;
    } else {
      item.setAttribute(name, value);
    }
  }
  item.append(...children);
  return item;
}

function words(node) {
  return node ? node.textContent.replace(/\s+/g, " ").trim() : "";
}

// The concept a link of this page leads to, or "". Quarto's script may have
// made an in-page link absolute, so the link is read by its parts.
function conceptOf(link) {
  const here = link.origin === window.location.origin && link.pathname === window.location.pathname;
  return here && link.hash.startsWith("#concept-")
    ? decodeURIComponent(link.hash.slice("#concept-".length))
    : "";
}

function box(rect) {
  return ["x", "y", "width", "height"].map((name) => Number(rect.getAttribute(name)));
}

// --- What the page holds ------------------------------------------------------

function read() {
  const nodes = [...svg.querySelectorAll(".atlas-nodes a[data-concept]")];
  const plates = [...svg.querySelectorAll(".atlas-views a.atlas-lesson")];
  const edges = [...svg.querySelectorAll(".atlas-edges [data-kind]")];
  const areas = [...svg.querySelectorAll("g.atlas-area[data-area]")].map((group) => ({
    id: group.dataset.area,
    kind: group.classList.contains("atlas-path") ? "path" : "course",
    title: words(group.querySelector(".atlas-area-title")),
    box: box(group.querySelector(".atlas-area-box")),
  }));
  const views = [...svg.querySelectorAll("g.atlas-view")].map((group) => ({
    id: group.dataset.method,
    title: words(group.querySelector(".atlas-view-title")),
    box: box(group.querySelector(".atlas-view-box")),
  }));
  const lessons = Object.fromEntries(
    plates.map((plate) => [
      plate.dataset.lesson,
      {
        course: plate.dataset.course,
        path: plate.dataset.path,
        methods: plate.dataset.methods.split(" ").filter(Boolean),
        difficulty: plate.dataset.difficulty,
        state: "published",
      },
    ]),
  );
  const kindOf = Object.fromEntries(areas.map((area) => [area.id, area.kind]));
  // A concept's entries are its lessons and, when it has planned slots, one
  // planned entry in its area: the rows the index shows for it.
  const entries = new Map(
    nodes.map((node) => {
      const own = node.dataset.lessons.split(" ").filter(Boolean).map((id) => lessons[id]);
      if (Number(node.dataset.planned) > 0) {
        const area = node.dataset.area;
        own.push({
          course: kindOf[area] === "course" ? area : "",
          path: kindOf[area] === "path" ? area : "",
          methods: [],
          difficulty: "",
          state: "planned",
        });
      }
      return [node, own];
    }),
  );
  const view = svg.viewBox.baseVal;
  return {
    nodes,
    plates,
    edges,
    areas,
    views,
    lessons,
    entries,
    byId: Object.fromEntries(nodes.map((node) => [node.dataset.concept, node])),
    natural: [view.x, view.y, view.width, view.height],
  };
}

const state = {
  selected: "",
  preview: "",
  show: "all",
  zoom: 0,
  region: "",
  filters: Object.fromEntries(FILTERS.map((key) => [key, ""])),
};

// --- The controls -------------------------------------------------------------

function select(name, label, options, all) {
  const control = element("select", { name });
  control.append(element("option", { value: "", text: all }));
  for (const [value, text] of options) {
    control.append(element("option", { value, text }));
  }
  const field = element("label", { class: "atlas-field" }, `${label} `, control);
  return { field, control };
}

function controls(atlas) {
  const courses = atlas.areas.filter((area) => area.kind === "course");
  const paths = atlas.areas.filter((area) => area.kind === "path");

  // The region selector.
  const region = select("region", "Region", [], "Whole map");
  const groups = [
    ["Physics courses", courses.map((area) => [area.id, area.title])],
    ["Method paths", paths.map((area) => [area.id, area.title])],
    ["Across the curriculum", atlas.views.length ? [[VIEWS, "Lean and method views"]] : []],
  ];
  for (const [label, options] of groups) {
    if (!options.length) {
      continue;
    }
    const group = element("optgroup", { label });
    for (const [value, text] of options) {
      group.append(element("option", { value, text }));
    }
    region.control.append(group);
  }

  // What the map shows.
  const options = element("div", { class: "atlas-show-options" });
  for (const [value, { label }] of Object.entries(KINDS)) {
    const input = element("input", { type: "radio", name: "atlas-show", value });
    input.checked = value === state.show;
    options.append(element("label", {}, input, ` ${label}`));
  }
  const show = element("fieldset", { class: "atlas-show" }, element("legend", { text: "Show" }), options);

  // Zoom.
  const zoomOut = element("button", { type: "button", text: "Zoom out" });
  const zoomIn = element("button", { type: "button", text: "Zoom in" });
  const actual = element("button", { type: "button", text: "Actual size" });
  const level = element("output", { "aria-live": "polite", class: "atlas-zoom-level" });
  const zoom = element(
    "div",
    { class: "atlas-zoom", role: "group", "aria-label": "Zoom" },
    zoomOut,
    level,
    zoomIn,
    actual,
  );

  // The filters, the same as the course index's.
  const levels = [...new Set(Object.values(atlas.lessons).map((item) => item.difficulty))]
    .filter(Boolean)
    .sort()
    .map((value) => [value, `Level ${value}`]);
  const filters = {
    course: select("course", "Course", courses.map((area) => [area.id, area.title]), "All"),
    path: select("path", "Path", paths.map((area) => [area.id, area.title]), "All"),
    method: select("method", "Method", atlas.views.map((view) => [view.id, view.title]), "All"),
    difficulty: select("difficulty", "Difficulty", levels, "All"),
    state: select(
      "state",
      "Publication",
      [
        ["published", "Published"],
        ["planned", "Planned"],
      ],
      "All",
    ),
  };
  const reset = element("button", { type: "button", text: "Show all" });
  const filterForm = element(
    "form",
    { class: "atlas-filter-form", "aria-label": "Filter the map and the course index" },
    ...Object.values(filters).map(({ field }) => field),
    reset,
  );
  filterForm.addEventListener("submit", (event) => event.preventDefault());
  const filterSummary = element("summary", { text: "Filters" });
  const filterBox = element("details", { class: "atlas-filters" }, filterSummary, filterForm);
  const status = element("p", { role: "status", class: "atlas-status" });

  const bar = element(
    "div",
    { class: "atlas-toolbar" },
    element("div", { class: "atlas-region" }, region.field),
    show,
    zoom,
  );
  controlsBox.replaceChildren(bar, filterBox, status);
  controlsBox.classList.add("is-enhanced");
  return { region, show, zoomOut, zoomIn, actual, level, filters, reset, filterSummary, status };
}

// --- The selected concept and the region's list ------------------------------

function selection() {
  const hint = element("p", {
    class: "atlas-selection-hint",
    text:
      "Choose a concept on the map to see its explanation, its lessons, and its" +
      " relationships here. Escape clears the choice.",
  });
  const announce = element("p", { role: "status", class: "visually-hidden" });
  const panel = element("section", {
    class: "atlas-selected",
    "aria-labelledby": "atlas-selected-name",
    hidden: "",
  });
  const list = element("section", {
    class: "atlas-region-list",
    "aria-labelledby": "atlas-region-title",
    hidden: "",
  });
  selectionBox.replaceChildren(list, hint, announce, panel);
  selectionBox.classList.add("is-enhanced");
  return { hint, announce, panel, list };
}

// The facts of the concept's panel in the page, with what its relationships
// mean on the map.
function fill(panel, atlas, id) {
  const source = document.getElementById(`concept-${id}`);
  const node = atlas.byId[id];
  const name = words(source?.querySelector(".concept-name")) || id;
  const status = words(source?.querySelector(".concept-state"));
  const heading = element("h3", { id: "atlas-selected-name", tabindex: "-1", text: name });
  const close = element("button", { type: "button", class: "atlas-close", text: "Close" });
  close.addEventListener("click", () => clear(atlas, true));
  const head = element(
    "div",
    { class: "atlas-selected-head" },
    element("div", {}, heading, element("p", { class: "concept-state", text: status })),
    close,
  );
  const body = source?.querySelector(".concept-body")?.cloneNode(true) ?? element("div");
  body.classList.add("atlas-selected-body");
  for (const item of body.querySelectorAll("[id]")) {
    item.removeAttribute("id");
  }
  const key = element("p", {
    class: "atlas-selected-key",
    text:
      "On the map: the solid arrows into this concept come from the concepts it" +
      " builds on, the arrows out lead to the concepts that need it, the dashed" +
      " lines with open circles are its conceptual connections, and the dotted" +
      " line with a diamond leads to its capstone project.",
  });
  const more = element(
    "p",
    { class: "atlas-selected-more" },
    element("a", { href: `#concept-${id}`, text: `The panel of ${name} in the list of concepts` }),
  );
  panel.replaceChildren(head, body, key, more);
  panel.hidden = false;
  panel.dataset.concept = id;
  panel.dataset.conceptState = node?.dataset.conceptState ?? "";
}

function regionList(parts, atlas) {
  const { list } = parts;
  const region = state.region;
  if (!region) {
    list.hidden = true;
    list.replaceChildren();
    return;
  }
  const area = atlas.areas.find((item) => item.id === region);
  const items = [];
  let title;
  let index;
  if (area) {
    title = `Concepts in ${area.title}`;
    for (const node of atlas.nodes.filter((item) => item.dataset.area === region)) {
      const id = node.dataset.concept;
      const panel = document.getElementById(`concept-${id}`);
      items.push(
        element(
          "li",
          {},
          element("a", { href: `#concept-${id}`, text: words(panel?.querySelector(".concept-name")) || id }),
          " ",
          element("span", { class: "concept-state", text: words(panel?.querySelector(".concept-state")) }),
        ),
      );
    }
    index = element("a", {
      href: `#${area.kind}-${area.id}`,
      text: `${area.title} in the course index`,
    });
  } else {
    title = "The Lean and method views";
    for (const view of atlas.views) {
      const count = atlas.plates.filter((plate) => plate.closest(`g.atlas-view[data-method="${view.id}"]`)).length;
      items.push(
        element(
          "li",
          {},
          element("a", { href: `#method-${view.id}`, text: view.title }),
          " ",
          element("span", { class: "concept-state", text: `${count} lesson${count === 1 ? "" : "s"}` }),
        ),
      );
    }
    index = element("a", { href: "#methods", text: "Every method in the course index" });
  }
  list.replaceChildren(
    element("h3", { id: "atlas-region-title", text: title }),
    element("ul", {}, ...items),
    element("p", {}, index),
  );
  list.hidden = false;
}

// --- Drawing the state ---------------------------------------------------------

function shownKinds() {
  return KINDS[state.show].edges;
}

function highlight(atlas) {
  const focus = state.preview || state.selected;
  const kinds = shownKinds();
  const related = new Set();
  for (const edge of atlas.edges) {
    const touches = focus && (edge.dataset.from === focus || edge.dataset.to === focus);
    const on = Boolean(touches && kinds.includes(edge.dataset.kind));
    edge.classList.toggle("is-related", on);
    if (on) {
      related.add(edge.dataset.from === focus ? edge.dataset.to : edge.dataset.from);
    }
  }
  for (const node of atlas.nodes) {
    const id = node.dataset.concept;
    node.classList.toggle("is-selected", id === state.selected);
    node.classList.toggle("is-current", id === focus);
    node.classList.toggle("is-neighbour", related.has(id));
  }
  svg.classList.toggle("atlas-has-focus", Boolean(focus));
}

function counts(atlas, id) {
  const found = { needs: 0, needed: 0, conceptual: 0, capstone: 0 };
  for (const edge of atlas.edges) {
    const { kind, from, to } = edge.dataset;
    if (kind === "prerequisite" && to === id) found.needs += 1;
    if (kind === "prerequisite" && from === id) found.needed += 1;
    if (kind === "conceptual" && (from === id || to === id)) found.conceptual += 1;
    if (kind === "capstone" && (from === id || to === id)) found.capstone += 1;
  }
  return found;
}

function plural(count, one, many) {
  return `${count} ${count === 1 ? one : many}`;
}

function view(atlas) {
  let [x, y, width, height] = atlas.natural;
  const area = atlas.areas.find((item) => item.id === state.region);
  if (area) {
    [x, y, width, height] = area.box;
  } else if (state.region === VIEWS && atlas.views.length) {
    const boxes = atlas.views.map((item) => item.box);
    x = Math.min(...boxes.map((b) => b[0]));
    y = Math.min(...boxes.map((b) => b[1]));
    width = Math.max(...boxes.map((b) => b[0] + b[2])) - x;
    height = Math.max(...boxes.map((b) => b[1] + b[3])) - y;
  }
  if (state.region) {
    x -= REGION_PAD;
    y -= REGION_PAD;
    width += 2 * REGION_PAD;
    height += 2 * REGION_PAD;
  }
  const scale = ZOOMS[state.zoom];
  const before = map.scrollWidth > map.clientWidth
    ? (map.scrollLeft + map.clientWidth / 2) / map.scrollWidth
    : 0.5;
  svg.setAttribute("viewBox", `${x} ${y} ${width} ${height}`);
  svg.setAttribute("width", String(Math.round(width * scale)));
  svg.setAttribute("height", String(Math.round(height * scale)));
  map.scrollLeft = before * map.scrollWidth - map.clientWidth / 2;
  map.dataset.region = state.region;

  // What lies outside the region is out of sight, out of the tab order, and
  // out of the accessibility tree.
  const inside = (node) => !state.region || node.dataset.area === state.region;
  for (const node of atlas.nodes) {
    node.classList.toggle("atlas-outside", !inside(node));
  }
  for (const plate of atlas.plates) {
    plate.classList.toggle("atlas-outside", Boolean(state.region) && state.region !== VIEWS);
  }
  for (const edge of atlas.edges) {
    const ends = [atlas.byId[edge.dataset.from], atlas.byId[edge.dataset.to]];
    edge.classList.toggle("atlas-outside", !ends.some((node) => node && inside(node)));
  }
}

function matches(entry, want) {
  return (
    (!want.course || entry.course === want.course) &&
    (!want.path || entry.path === want.path) &&
    (!want.method || entry.methods.includes(want.method)) &&
    (!want.difficulty || entry.difficulty === want.difficulty) &&
    (!want.state || entry.state === want.state)
  );
}

function filter(atlas, parts) {
  const want = state.filters;
  const active = Object.values(want).some(Boolean);
  let concepts = 0;
  for (const node of atlas.nodes) {
    const keep = !active || atlas.entries.get(node).some((entry) => matches(entry, want));
    node.classList.toggle("is-filtered-out", !keep);
    concepts += keep ? 1 : 0;
  }
  let lessons = 0;
  for (const plate of atlas.plates) {
    const keep = !active || matches(atlas.lessons[plate.dataset.lesson], want);
    plate.classList.toggle("is-filtered-out", !keep);
    lessons += keep ? 1 : 0;
  }
  svg.classList.toggle("atlas-filtered", active);
  const chosen = FILTERS.filter((key) => want[key]).length;
  parts.filterSummary.textContent = chosen ? `Filters (${chosen} chosen)` : "Filters";
  parts.status.textContent = active
    ? `${plural(concepts, "concept", "concepts")} of ${atlas.nodes.length} and` +
      ` ${plural(lessons, "lesson", "lessons")} of ${atlas.plates.length} on the map` +
      " match the filters; the others are faded."
    : "";
}

// --- Actions ----------------------------------------------------------------

let parts;

function choose(atlas, id, { from = "map" } = {}) {
  const node = atlas.byId[id];
  if (!node) {
    return;
  }
  // A concept outside the focused region brings its own region into view.
  if (state.region && node.dataset.area !== state.region) {
    state.region = node.dataset.area;
    parts.region.control.value = state.region;
    view(atlas);
    regionList(parts.selection, atlas);
  }
  state.selected = id;
  state.preview = "";
  highlight(atlas);
  fill(parts.selection.panel, atlas, id);
  parts.selection.hint.hidden = true;
  selectionBox.classList.add("has-selection");
  const name = words(parts.selection.panel.querySelector("h3"));
  const found = counts(atlas, id);
  parts.selection.announce.textContent =
    `${name} selected: it builds on ${plural(found.needs, "concept", "concepts")},` +
    ` ${plural(found.needed, "concept builds", "concepts build")} on it, and it has` +
    ` ${plural(found.conceptual, "conceptual connection", "conceptual connections")}.` +
    " Its panel follows the map.";
  if (from !== "map") {
    node.scrollIntoView({ block: "nearest", inline: "center" });
    parts.selection.panel.querySelector("h3").focus({ preventScroll: true });
  }
  // The panel sits at the foot of the screen: the chosen box stays above it.
  const panelTop = parts.selection.panel.getBoundingClientRect().top;
  const below = node.getBoundingClientRect().bottom - panelTop;
  if (below > -16) {
    window.scrollBy({ top: below + 32, behavior: "instant" });
  }
}

function clear(atlas, returnFocus = false) {
  const id = state.selected;
  state.selected = "";
  state.preview = "";
  highlight(atlas);
  const { panel, hint, announce } = parts.selection;
  panel.hidden = true;
  panel.replaceChildren();
  hint.hidden = false;
  announce.textContent = id ? "No concept selected." : "";
  selectionBox.classList.remove("has-selection");
  if (returnFocus && atlas.byId[id] && !atlas.byId[id].classList.contains("atlas-outside")) {
    atlas.byId[id].focus();
  }
}

function setZoom(atlas, index) {
  state.zoom = Math.max(0, Math.min(ZOOMS.length - 1, index));
  view(atlas);
  parts.level.textContent = `${Math.round(ZOOMS[state.zoom] * 100)}%`;
  parts.zoomOut.disabled = state.zoom === 0;
  parts.zoomIn.disabled = state.zoom === ZOOMS.length - 1;
  parts.actual.disabled = state.zoom === 0;
}

function setRegion(atlas, region) {
  state.region = region;
  parts.region.control.value = region;
  if (state.selected && region && atlas.byId[state.selected]?.dataset.area !== region) {
    clear(atlas);
  }
  map.scrollLeft = 0;
  view(atlas);
  regionList(parts.selection, atlas);
}

function setFilters(atlas, values, announce) {
  for (const key of FILTERS) {
    state.filters[key] = values[key] || "";
    parts.filters[key].control.value = state.filters[key];
  }
  filter(atlas, parts);
  if (announce) {
    document.dispatchEvent(new CustomEvent("pbc:set-filters", { detail: { ...state.filters } }));
  }
}

// The switch: the part of the page in view is marked, and following a link
// moves keyboard focus to the part it leads to.
function enhanceSwitch() {
  const links = [...document.querySelectorAll(".atlas-switch a")].filter(
    (link) => link.pathname === window.location.pathname && link.hash,
  );
  const targets = links
    .map((link) => [link, document.getElementById(decodeURIComponent(link.hash.slice(1)))])
    .filter(([, target]) => target);
  const focusable = (target) => {
    if (target.matches("[tabindex], a, button, input, select, summary")) {
      return target;
    }
    const heading = target.querySelector("h2, h3") ?? target;
    heading.setAttribute("tabindex", "-1");
    return heading;
  };
  for (const [link, target] of targets) {
    link.addEventListener("click", () => {
      requestAnimationFrame(() => focusable(target).focus({ preventScroll: true }));
    });
  }
  const ordered = [...targets].sort(([, a], [, b]) =>
    a.compareDocumentPosition(b) & Node.DOCUMENT_POSITION_FOLLOWING ? -1 : 1,
  );
  let pending = false;
  const mark = () => {
    pending = false;
    let current = null;
    for (const [link, target] of ordered) {
      if (target.getBoundingClientRect().top <= window.innerHeight * 0.4) {
        current = link;
      }
    }
    for (const [link] of targets) {
      if (link === current) {
        link.setAttribute("aria-current", "location");
      } else {
        link.removeAttribute("aria-current");
      }
    }
  };
  window.addEventListener(
    "scroll",
    () => {
      if (!pending) {
        pending = true;
        requestAnimationFrame(mark);
      }
    },
    { passive: true },
  );
  mark();
}

function start() {
  const atlas = read();
  parts = controls(atlas);
  parts.selection = selection();
  map.classList.add("is-enhanced");

  // Selection by pointer and keyboard: a concept box selects its concept.
  svg.addEventListener("click", (event) => {
    const node = event.target.closest("a[data-concept]");
    if (node) {
      event.preventDefault();
      choose(atlas, node.dataset.concept);
    }
  });
  const preview = (event) => {
    const node = event.target.closest?.("a[data-concept]");
    state.preview = node ? node.dataset.concept : "";
    highlight(atlas);
  };
  svg.addEventListener("pointerover", preview);
  svg.addEventListener("pointerleave", () => {
    state.preview = "";
    highlight(atlas);
  });
  svg.addEventListener("focusin", preview);
  svg.addEventListener("focusout", () => {
    state.preview = "";
    highlight(atlas);
  });

  // A concept link in the panel or the region's list selects that concept.
  selectionBox.addEventListener("click", (event) => {
    const link = event.target.closest("a[href]");
    const id = link && !link.closest(".atlas-selected-more") ? conceptOf(link) : "";
    if (id) {
      event.preventDefault();
      choose(atlas, id, { from: "list" });
    }
  });
  for (const box of [map, selectionBox, controlsBox]) {
    box.addEventListener("keydown", (event) => {
      if (event.key === "Escape" && state.selected) {
        event.preventDefault();
        clear(atlas, true);
      }
    });
  }
  map.addEventListener("keydown", (event) => {
    if (event.altKey || event.ctrlKey || event.metaKey) {
      return;
    }
    const step = { "+": 1, "=": 1, "-": -1, _: -1 }[event.key];
    if (step) {
      event.preventDefault();
      setZoom(atlas, state.zoom + step);
    } else if (event.key === "0") {
      event.preventDefault();
      setZoom(atlas, 0);
    }
  });

  // What the map shows.
  parts.show.addEventListener("change", (event) => {
    state.show = event.target.value;
    svg.dataset.show = state.show;
    highlight(atlas);
  });

  // Zoom.
  parts.zoomOut.addEventListener("click", () => setZoom(atlas, state.zoom - 1));
  parts.zoomIn.addEventListener("click", () => setZoom(atlas, state.zoom + 1));
  parts.actual.addEventListener("click", () => setZoom(atlas, 0));

  // The region.
  parts.region.control.addEventListener("change", (event) => setRegion(atlas, event.target.value));

  // The filters, in step with the course index.
  for (const { control } of Object.values(parts.filters)) {
    control.addEventListener("change", () => {
      const values = Object.fromEntries(
        FILTERS.map((key) => [key, parts.filters[key].control.value]),
      );
      setFilters(atlas, values, true);
    });
  }
  parts.reset.addEventListener("click", () => setFilters(atlas, {}, true));
  document.addEventListener("pbc:filters", (event) => setFilters(atlas, event.detail, false));

  svg.dataset.show = state.show;
  setZoom(atlas, 0);
  setRegion(atlas, window.matchMedia(NARROW).matches && atlas.areas.length ? atlas.areas[0].id : "");
  enhanceSwitch();
}

if (map && svg && controlsBox && selectionBox) {
  start();
}
