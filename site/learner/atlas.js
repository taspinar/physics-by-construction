// The course atlas (F133, docs/atelier.md, "The course atlas"): the address
// follows the sequence a reader opens, and an address opens its sequence, so
// that path/#course-quantum is a bookmark; an anchor of the previous atlas
// opens the sequence that holds it now (data-aliases). Without this module
// the native disclosures, one group of one name, already show one sequence
// at a time. No request, no cookie, no storage.
const sequences = [...document.querySelectorAll("details.atlas-sequence")];
const narrow = window.matchMedia("(max-width: 55.99em)");
let opened = null; // the sequence whose card the reader activated

function openFromAddress() {
  const name = decodeURIComponent(location.hash.slice(1));
  const target = sequences.find((item) => item.id === name || item.dataset.aliases?.split(" ").includes(name));
  if (target && !target.open) target.open = true;
  if (target && target.id !== name) target.scrollIntoView({ block: "start" });
}

for (const item of sequences) {
  item.querySelector("summary").addEventListener("click", () => (opened = item));
  item.addEventListener("toggle", () => {
    if (!item.open || opened !== item) return;
    opened = null;
    history.replaceState(null, "", `#${item.id}`);
    if (narrow.matches) item.scrollIntoView({ block: "start" });
  });
}
window.addEventListener("hashchange", openFromAddress);
openFromAddress();
