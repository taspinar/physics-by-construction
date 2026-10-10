// Learner state of the site: which lessons a reader has completed and how they
// answered the self-checks. It lives in this browser's local storage and
// nowhere else. This script makes no request, loads nothing, sets no cookie,
// and is the only script of the site that uses browser storage; the
// built-site checks scan it and watch the page to hold it to that
// (docs/architecture.md, "Learner state"; invariant I16).
//
// Stored under one key, as
//   {"version": 1, "lessons": {"<lesson id>": {"completed": true,
//     "selfCheck": {"done": true, "attempts": 2}}}}
// Lesson ids are the stable ids of the lesson front matter. Data of any other
// version, or data that does not have this shape, is discarded: a reader loses
// their progress, never the page. To change the format, raise VERSION and add
// the function that turns the previous version into the new one to MIGRATIONS.

const KEY = "physics-by-construction:learner-state";
const VERSION = 1;
// MIGRATIONS[n] takes data of version n and returns data of version n + 1.
// No earlier format exists yet.
const MIGRATIONS = {};

// --- The data -------------------------------------------------------------

function emptyState() {
  return { version: VERSION, lessons: Object.create(null) };
}

function cleanEntry(entry) {
  if (entry === null || typeof entry !== "object" || Array.isArray(entry)) {
    return null;
  }
  const clean = {};
  if (entry.completed !== undefined) {
    if (typeof entry.completed !== "boolean") {
      return null;
    }
    clean.completed = entry.completed;
  }
  const check = entry.selfCheck;
  if (check !== undefined) {
    if (
      check === null ||
      typeof check !== "object" ||
      typeof check.done !== "boolean" ||
      !Number.isInteger(check.attempts) ||
      check.attempts < 0
    ) {
      return null;
    }
    clean.selfCheck = { done: check.done, attempts: check.attempts };
  }
  return clean;
}

// The state a stored text stands for, or null when it cannot be used: not
// JSON, not this shape, or a version that cannot be migrated.
export function parseState(text) {
  let data;
  try {
    data = JSON.parse(text);
  } catch (error) {
    return null;
  }
  if (data === null || typeof data !== "object" || !Number.isInteger(data.version)) {
    return null;
  }
  while (data.version < VERSION) {
    const migrate = MIGRATIONS[data.version];
    if (typeof migrate !== "function") {
      return null;
    }
    data = migrate(data);
    if (data === null || typeof data !== "object") {
      return null;
    }
  }
  if (
    data.version !== VERSION ||
    data.lessons === null ||
    typeof data.lessons !== "object" ||
    Array.isArray(data.lessons)
  ) {
    return null;
  }
  const state = emptyState();
  for (const id of Object.keys(data.lessons)) {
    const entry = cleanEntry(data.lessons[id]);
    if (entry === null) {
      return null;
    }
    state.lessons[id] = entry;
  }
  return state;
}

// --- The storage ----------------------------------------------------------

let kept = emptyState(); // what is held when the browser gives no storage
let available = true;

function storage() {
  try {
    return window.localStorage;
  } catch (error) {
    return null;
  }
}

function load() {
  const store = storage();
  if (store === null) {
    available = false;
    return kept;
  }
  let text;
  try {
    text = store.getItem(KEY);
  } catch (error) {
    available = false;
    return kept;
  }
  if (text === null) {
    return emptyState();
  }
  const state = parseState(text);
  if (state === null) {
    try {
      store.removeItem(KEY);
    } catch (error) {
      available = false;
    }
    return emptyState();
  }
  return state;
}

function save(state) {
  kept = state;
  const store = storage();
  if (store === null) {
    available = false;
    return;
  }
  try {
    store.setItem(KEY, JSON.stringify(state));
  } catch (error) {
    available = false;
  }
}

function clear() {
  kept = emptyState();
  const store = storage();
  if (store === null) {
    return;
  }
  try {
    store.removeItem(KEY);
  } catch (error) {
    available = false;
  }
}

function update(change) {
  const state = load();
  change(state);
  save(state);
  return state;
}

function entryOf(state, id) {
  if (!Object.prototype.hasOwnProperty.call(state.lessons, id)) {
    state.lessons[id] = {};
  }
  return state.lessons[id];
}

// --- The page -------------------------------------------------------------

const page = JSON.parse(
  document.getElementById("learner-state-data")?.textContent ?? "{}"
);
const renderers = [];

function element(tag, properties = {}, ...children) {
  const node = document.createElement(tag);
  Object.assign(node, properties);
  node.append(...children);
  return node;
}

function notice() {
  return available
    ? ""
    : " Your browser does not allow this site to store anything, so this lasts only until you leave the page.";
}

function storedNote() {
  const note = element("p", { className: "learner-note" });
  note.append(
    "Saved in this browser only. ",
    element("a", { href: page.explanation, textContent: "What is stored, and how to clear it" }),
    "."
  );
  return note;
}

// The completed status of the lesson of this page, with the control to set it.
// The page has the element, an enhancement with a sentence for readers
// without scripts; the script fills it.
function lessonPanel() {
  const panel = document.getElementById("learner-panel");
  if (!page.lesson || !panel) {
    return;
  }
  const status = element("p", { className: "learner-status", role: "status" });
  const toggle = element("button", { type: "button" });
  panel.setAttribute("role", "group");
  panel.setAttribute("aria-label", "Your progress in this lesson");
  panel.replaceChildren(status, element("p", {}, toggle), storedNote());
  toggle.addEventListener("click", () => {
    update((state) => {
      const entry = entryOf(state, page.lesson);
      entry.completed = !entry.completed;
    });
    renderAll();
  });
  renderers.push((state) => {
    const done = state.lessons[page.lesson]?.completed === true;
    status.textContent = (done ? "You have completed this lesson." : "You have not marked this lesson as completed.") + notice();
    toggle.textContent = done ? "Mark lesson as not completed" : "Mark lesson as completed";
  });
}

// The question of the self-check as radio buttons with immediate feedback.
function choiceForm(check, container, list) {
  const options = [...list.children].map((item) => ({
    right: item.dataset.correct === "true",
    label: [...item.childNodes].filter(
      (node) => !(node.nodeType === 1 && node.classList.contains("feedback"))
    ),
    feedback: item.querySelector(".feedback"),
  }));
  const name = "self-check-choice";
  const fieldset = element("fieldset", { className: "choice-form" }, element("legend", { textContent: "Choose one answer" }));
  const inputs = options.map((option, index) => {
    const input = element("input", { type: "radio", name, value: String(index) });
    const text = element("span");
    // A single paragraph reads as the text of the label.
    const only = option.label.filter((node) => node.nodeType !== 3 || node.textContent.trim());
    if (only.length === 1 && only[0].localName === "p") {
      text.append(...[...only[0].childNodes].map((node) => node.cloneNode(true)));
    } else {
      text.append(...option.label.map((node) => node.cloneNode(true)));
    }
    fieldset.append(element("div", { className: "choice-option" }, element("label", {}, input, " ", text)));
    return input;
  });
  const result = element("div", { className: "self-check-result", role: "status" });
  const button = element("button", { type: "button", textContent: "Check answer" });
  container.replaceChildren(fieldset, element("p", {}, button), result, storedNote());
  button.addEventListener("click", () => {
    const index = inputs.findIndex((input) => input.checked);
    if (index < 0) {
      result.replaceChildren(element("p", { textContent: "Choose an answer first." }));
      return;
    }
    const option = options[index];
    update((state) => {
      const entry = entryOf(state, page.lesson);
      const attempts = (entry.selfCheck?.attempts ?? 0) + 1;
      const done = option.right || entry.selfCheck?.done === true;
      entry.selfCheck = { done, attempts };
      if (option.right) {
        entry.completed = true;
      }
    });
    result.replaceChildren(
      element("p", {}, element("strong", { textContent: option.right ? "Correct." : "Not quite." })),
      ...(option.feedback ? [...option.feedback.childNodes].map((node) => node.cloneNode(true)) : [])
    );
    renderAll();
  });
  renderers.push((state) => {
    const entry = state.lessons[page.lesson]?.selfCheck;
    check.dataset.done = entry?.done ? "true" : "false";
  });
}

// A self-check without choices: the reader says that they answered it.
function openForm(check, container) {
  const button = element("button", { type: "button" });
  const status = element("p", { className: "self-check-result", role: "status" });
  container.replaceChildren(element("p", {}, button), status, storedNote());
  button.addEventListener("click", () => {
    update((state) => {
      const entry = entryOf(state, page.lesson);
      const done = entry.selfCheck?.done !== true;
      entry.selfCheck = { done, attempts: (entry.selfCheck?.attempts ?? 0) + (done ? 1 : 0) };
      if (done) {
        entry.completed = true;
      }
    });
    renderAll();
  });
  renderers.push((state) => {
    const done = state.lessons[page.lesson]?.selfCheck?.done === true;
    check.dataset.done = done ? "true" : "false";
    button.textContent = done ? "Mark self-check as not done" : "Mark self-check as done";
    status.textContent = done ? "Marked as done in this browser." : "";
  });
}

function selfCheck() {
  const check = document.querySelector(".exercise.self-check");
  const container = document.getElementById("self-check-controls");
  if (!page.lesson || !check || !container) {
    return;
  }
  const list = container.querySelector("ol.choices");
  if (list) {
    choiceForm(check, container, list);
  } else {
    openForm(check, container);
  }
}

// The learning path: the cards of completed lessons are marked, the place of
// the page that is an enhancement shows the count, the lessons completed, and
// the clear-data control.
function pathPage() {
  const container = document.getElementById("progress-controls");
  if (!container) {
    return;
  }
  const summary = element("p", { role: "status" });
  const list = element("ul", { className: "completed-lessons" });
  const clearButton = element("button", { type: "button", textContent: "Clear all stored progress" });
  container.replaceChildren(summary, list, element("p", {}, clearButton));
  let cleared = false;
  clearButton.addEventListener("click", () => {
    clear();
    cleared = true;
    renderAll();
  });
  const cards = [...document.querySelectorAll(".path-card[data-lesson-id]")];
  // One link per lesson: its first card.
  const titles = new Map();
  for (const card of cards) {
    const link = card.querySelector(".lesson-card-title a");
    if (link && !titles.has(card.dataset.lessonId)) {
      titles.set(card.dataset.lessonId, link);
    }
  }
  renderers.push((state) => {
    const completed = [...titles.keys()].filter((id) => state.lessons[id]?.completed === true);
    for (const card of cards) {
      card.dataset.completed = String(completed.includes(card.dataset.lessonId));
    }
    list.replaceChildren(
      ...completed.map((id) => {
        const link = titles.get(id);
        return element("li", {}, element("a", { href: link.getAttribute("href"), textContent: link.textContent }), " (completed)");
      })
    );
    summary.textContent =
      (cleared && completed.length === 0 ? "All stored progress was cleared. " : "") +
      `${completed.length} of ${titles.size} lessons completed.` +
      notice();
  });
}

function renderAll() {
  const state = load();
  for (const render of renderers) {
    render(state);
  }
}

lessonPanel();
selfCheck();
pathPage();
renderAll();
// Another tab of the site changed or cleared the data.
window.addEventListener("storage", (event) => {
  if (event.key === KEY || event.key === null) {
    renderAll();
  }
});
