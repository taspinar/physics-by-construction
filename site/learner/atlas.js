// The course atlas (F133, Issue #483; docs/atelier.md, "The course atlas"):
// the address follows the sequence a reader opens, and an address opens its
// sequence, so that path/#course-quantum is a bookmark; an anchor of the
// previous atlas opens the sequence that holds it now (data-aliases).
// Opening scrolls the row to the top of the window, because the row that
// was open closes and the page shifts. The native disclosures, one group of
// one name, already show one sequence at a time in Chromium 120, Firefox
// 130, Safari 17.2, and later; for an earlier browser this module closes
// the others when one opens. No request, no cookie, no storage.
const sequences = [...document.querySelectorAll("details.atlas-sequence")];
let opened = null; // the sequence whose row the reader activated

function openFromAddress() {
  const name = decodeURIComponent(location.hash.slice(1));
  const target = sequences.find((item) => item.id === name || item.dataset.aliases?.split(" ").includes(name));
  if (target && !target.open) target.open = true;
  if (target && target.id !== name) target.scrollIntoView({ block: "start" });
}

for (const item of sequences) {
  item.querySelector("summary").addEventListener("click", () => (opened = item));
  item.addEventListener("toggle", () => {
    if (!item.open) return;
    for (const other of sequences) if (other !== item && other.open) other.open = false;
    if (opened !== item) return;
    opened = null;
    history.replaceState(null, "", `#${item.id}`);
    item.scrollIntoView({ block: "start" });
  });
}
window.addEventListener("hashchange", openFromAddress);
openFromAddress();
