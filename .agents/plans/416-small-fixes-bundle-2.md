# Plan: small fixes bundle 2 (Issue #416)

Source: Issue #416 and the five Issues it bundles (#397, #203, #362, #381,
#277), each the source of its problem and its evidence. No lesson, no claim,
no `pbc.authoring`, no protected path changes.

Skills: none (no visual deliverable: tests, a test helper, one interface
fix, one check script).

Level 3 by the triggers of items 3 and 5 (a changed assertion, tolerance
lines), with the approval request `.agents/approvals/416.md`; the rest is
Level 2. The full `./scripts/verify.sh` runs last.

## 1. #397: duplicate budget settings

`raw_setting()` of `scripts/check-lesson-pages.sh` collects every line that
sets the key (with the key trimmed, as `tests/support/budgets.py::_read()`
reads it) and fails with "`<file>` sets '`<key>`' N times; a setting is set
once." when there is more than one. Tests in
`tests/integration/test_lesson_budgets.py` feed a table with each setting
twice (equal and different values, with spaces around the key) to both
parsers and expect rejection; a table with each setting once passes both.

## 2. #203: an inline number at its place (the design choice)

`tests/support/experiments.py::compare_with_page` takes the page's source as
an optional third argument; `scripts/check-lesson-pages.sh` and
`tests/e2e/test_lessons.py` pass it.

**Rule.** For every inline read `` `{python} result["name"]` `` of the prose,
its place is up to 3 words before and up to 3 after the expression within its
source block (paragraph, heading, table row, caption line; code cells, div
fences and the front matter are no prose). A word is a letter run of a token
without a digit. The built text is read with each MathML formula replaced by
its LaTeX annotation, so math compares with the source. A cross-reference, a
citation, a link target, an attribute, a footnote mark, a square bracket (a
claim span gets a label at its edge) and any other inline expression end the
place. The other inline reads of the block are written in as their recorded
values. The page must show the value at the place as often as the source
reads it there (a multiset). The old "token anywhere" rule stays for every
number, and is the only rule without a source.

**False negatives (accepted, written in the code):** a number read only in a
code cell (f-string, caption option) keeps the anywhere rule; an inline read
with no word around it in its block has an empty place; a stale value equal
to the new one at the same place.

**False positives (guarded):** rendering that changes the words next to an
expression. Measured on a full local build of the current lessons (the 389
worktree's `site/_site`, sources identical): every experiment run with the
place rule against its built page, and a context-only scan of all 1409
inline reads.

**Tests** (`tests/integration/test_experiment_check.py`): a changed inline
number whose new value is elsewhere on the page fails (and passes the old
rule); a number shown at another place only fails; an absent number is
reported once; a number read twice at one place must be shown twice; math,
a claim span, a link, a cross-reference, emphasis and a curly quote keep the
place, and a stale value there still fails; the places come from the prose
only. The page text of no lesson changes.

## 3. #362: the zero mode

The fix of the Issue comment, applied unchanged: the acoustic zero at k = 0
gets the absolute tolerance omega_max sqrt(n eps); the nonzero modes keep the
default of `np.isclose`; a test shows the rounded zero passes and a moved
mode fails. Other tests that compare a computed zero (`test_materials.py`
lines on `c @ ones`, the squared frequencies at atol 1e-12) compare
eigenvalues or sums, not the square root of a rounded zero, and need no
change.

## 4. #381: the interface's synthetic sample

`App._run` takes the sample from `App._synthetic_sample(config)`: named by
the digest of every setting but the circuit confirmation, written once per
configuration with the interlock closed explicitly (it comes from the
simulated bench, which drives nothing). The CLI `sample` command and
`workflow` are unchanged. Tests: changed low_hz, high_hz, amplitude with the
same seed each make a new sample and complete; the same settings reuse it;
recorded mode runs without the checkbox, simulated still refuses.

## 5. #277: the progress of the curriculum

#284 delivered the Issue; #379 brought back one hard-coded progress check:
the Part B inventory test asserted that the filled path slots are exactly
the inventory's, so the first lesson in a free path slot fails it. It is
rewritten as `part_b_failures(site)`: an inventory lesson that moved or lost
its page, or a lesson outside the inventory in an inventory slot, fails; a
new lesson in a free slot does not. Regression tests on a throwaway copy:
one more lesson in a path slot passes this check and the view check with no
test edit (the old assertion fails on it); a moved inventory lesson and an
outsider in an inventory slot each fail.

## Not in scope

The risk detector, `pbc.authoring`, lessons, #230 m3 to m5, #353.
