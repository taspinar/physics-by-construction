// The learning path page, enhanced (F64). Without this script the page is
// complete: every course is a disclosure that opens by hand, and the links
// above the courses lead to each course, path, and method. This script
//
//   - opens the disclosure that the address points into, so that a link to a
//     course or a lesson of the page lands on the lessons, and
//   - offers filters by course, method path, method, difficulty, and
//     publication state that hide the rows that do not match.
//
// The filters of the course atlas (learner/atlas.js, F126) are the same
// filters: after it applies them this script announces the values with the
// event "pbc:filters" on the document, and it takes values that the atlas
// sends with "pbc:set-filters". Either script works without the other.
//
// It stores nothing, makes no request, and sets no cookie. The filters only
// hide rows of the page; the search index is built from the page when the
// site is rendered, so it is the same with or without them.

const rows = () => [...document.querySelectorAll("[data-state][data-course], [data-state][data-home]")];

function openDisclosuresAround(target) {
  for (let node = target; node; node = node.parentElement) {
    if (node.tagName === "DETAILS") {
      node.open = true;
    }
  }
}

// A link to a course, a path, or a method opens the course it points to.
function openForHash() {
  const id = decodeURIComponent(window.location.hash.slice(1));
  const target = id ? document.getElementById(id) : null;
  if (!target) {
    return;
  }
  openDisclosuresAround(target);
  const lessons = target.querySelector(":scope details.course-lessons");
  if (lessons) {
    lessons.open = true;
  }
}

function option(value, text) {
  const item = document.createElement("option");
  item.value = value;
  item.textContent = text;
  return item;
}

function select(name, label, options) {
  const field = document.createElement("label");
  field.append(`${label} `);
  const control = document.createElement("select");
  control.name = name;
  control.append(option("", "All"));
  for (const [value, text] of options) {
    control.append(option(value, text));
  }
  field.append(control);
  return { field, control };
}

function filters() {
  const container = document.getElementById("path-filters");
  if (!container) {
    return;
  }
  const items = rows();
  const courses = [...document.querySelectorAll(".course-panel")].map((panel) => {
    const heading = panel.closest("section")?.querySelector("h3");
    return [panel.dataset.course, heading ? heading.textContent.trim() : panel.dataset.course];
  });
  const paths = [...document.querySelectorAll("section[id^='path-'] > h3")].map((heading) => [
    heading.parentElement.id.replace(/^path-/, ""),
    heading.textContent.trim(),
  ]);
  // A method path's lessons are the ones its section lists; a path filter
  // keeps them wherever the page lists them, and the path's planned slots.
  const inPath = Object.fromEntries(
    paths.map(([id]) => [
      id,
      new Set(
        [...document.querySelectorAll(`section#path-${id} [data-lesson-id]`)].map(
          (item) => item.dataset.lessonId,
        ),
      ),
    ]),
  );
  const methods = [...document.querySelectorAll("section[id^='method-'] > h3")].map((heading) => [
    heading.parentElement.id.replace(/^method-/, ""),
    heading.textContent.trim(),
  ]);
  const levels = [...new Set(items.map((item) => item.dataset.difficulty).filter(Boolean))]
    .sort()
    .map((level) => [level, `Level ${level}`]);
  const controls = {
    course: select("course", "Course", courses),
    path: select("path", "Path", paths),
    method: select("method", "Method", methods),
    difficulty: select("difficulty", "Difficulty", levels),
    state: select("state", "Publication", [
      ["published", "Published"],
      ["planned", "Planned"],
    ]),
  };
  const form = document.createElement("form");
  form.className = "path-filter-form";
  form.setAttribute("aria-label", "Filter the lessons of the page");
  form.addEventListener("submit", (event) => event.preventDefault());
  for (const { field } of Object.values(controls)) {
    form.append(field);
  }
  const reset = document.createElement("button");
  reset.type = "button";
  reset.textContent = "Show all";
  form.append(reset);
  const status = document.createElement("p");
  status.setAttribute("role", "status");
  container.replaceChildren(form, status);

  const apply = () => {
    const want = Object.fromEntries(Object.entries(controls).map(([key, { control }]) => [key, control.value]));
    let shown = 0;
    for (const item of items) {
      const home = item.dataset.course || item.dataset.home;
      const matches =
        (!want.course || home === want.course) &&
        (!want.path ||
          (item.dataset.lessonId
            ? inPath[want.path]?.has(item.dataset.lessonId)
            : item.dataset.home === want.path)) &&
        (!want.method || (item.dataset.methods || "").split(" ").includes(want.method)) &&
        (!want.difficulty || item.dataset.difficulty === want.difficulty) &&
        (!want.state || item.dataset.state === want.state);
      item.hidden = !matches;
      if (matches) {
        shown += 1;
        if (Object.values(want).some(Boolean)) {
          openDisclosuresAround(item);
        }
      }
    }
    status.textContent = Object.values(want).some(Boolean)
      ? `${shown} entries match the filters.`
      : "";
    document.dispatchEvent(new CustomEvent("pbc:filters", { detail: want }));
  };
  for (const { control } of Object.values(controls)) {
    control.addEventListener("change", apply);
  }
  reset.addEventListener("click", () => {
    for (const { control } of Object.values(controls)) {
      control.value = "";
    }
    apply();
  });
  // The atlas's filters: take every value it sends, then apply.
  document.addEventListener("pbc:set-filters", (event) => {
    for (const [key, { control }] of Object.entries(controls)) {
      control.value = event.detail[key] || "";
    }
    apply();
  });
}

openForHash();
window.addEventListener("hashchange", openForHash);
filters();
