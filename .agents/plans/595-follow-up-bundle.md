# Plan: Issue #595, the bundle of ten follow-up Issues

One pull request for #569, #578, #579, #584, #589, #590, #593, #596, #597
and #598, by the owner's request of 2026-11-21; #596 to #598 were added the
same day ("Meenemen"). Each Issue keeps its own acceptance criteria.

The page texts of #578 (AE5), #597 (RR3) and #598 (RR1) select the teaching
skill; the other Issues change tests, comments, captions and code only.

Skills: pbc-physics-teaching@7f34987

Visual deliverables: none. No figure, diagram, or layout changes.

## Risk

Level 3, by two triggers. A published claim changes: #597 narrows what
RR3 says of its passages and labels (the quotations are checked, the labels
are one coding agent's reading, no person or second annotator), and #598
narrows what RR1 says its archive check finds (not a removed last entry,
not a chain recomputed after an edit). An existing test assertion changes:
`tests/unit/test_research_literature.py` asserted the status "verified
passage", which #597 removes. `.agents/approvals/595.md` records it. No
protected path; no tolerance or budget in an experiment file; no new file
next to a lesson page. The seven first Issues alone stay as described in
their sections: no published claim of AE5, RR2, RR5 or SA6 changes.

## #569: the coding-agent boundary for the scripts the self-tests reach

- **Fix.** `tests/unit/test_coding_agent_boundary.py` gains
  `direct_starts`, which finds a code line that uses an agent program as a
  command word, outside a heredoc, a string without a command
  substitution, a presence check (`have`, `command -v`, `which`, `hash`,
  `type -p`), a case label, or the words of a loop; and a test that applies
  it to every script a self-test of `scripts/verify-workflow.conf` reaches,
  except `tests/*-test.sh` and the launcher.
- **Tests.** The planted lines of both kinds; today's tree passes
  (`scripts/doctor.sh`, `tests/lib-fakes.sh`, `scripts/start-planning.sh`
  are in the reach and not flagged); a planted `claude -p` line in
  `scripts/doctor.sh` makes the boundary test itself fail.
- **Docs.** `docs/coding-agent-workflow.md` section 10 states the widened
  check in the test's terms.
- **Defect class swept.** A guard that checks a convention for the
  launcher but not for what reaches it: the other reach-based checks of the
  file (credentials, installers) already scan the whole self-test reach.

## #578: AE5 says D2's run was another model

- **Fix.** The opening says D2's run was Claude Sonnet, the trials are
  Claude Opus, the question is how often this model recovers on this task,
  and the published run is compared, not repeated. The prediction moment
  before `ae5-trials` names both models.
- **Teaching.** AI-agent archetype: the kind of evidence (recorded runs of
  another model) is stated at once, before the prediction, so the moment
  asks the question the table can answer.
- **Defect class swept.** A framing that presents the trials as repeats of
  D2: the variant "Repeated" (the task, at other seeds) and the self-check
  feedback were read; neither needs a change.

## #579: two stale statements

- **Fix.** The plan of #570 drops the `site.css` clause; the comment above
  `CLIP_FILE_LIMIT` says 3 MB limits the on-demand data and 5 MB the
  initial payload plus the on-demand data.
- **Defect class swept.** Other budget comments in the measurement tests:
  none restates the two budgets.

## #584: library modules on the instrument contract

- **Fix.** New tests in `tests/unit/test_products_boundary.py`: the set of
  library modules under `src/pbc` that import `pbc.instruments` (by their
  import statements, without the contract's package, the product, and the
  experiments) is derived and holds `pbc.electromagnetism.campaign`; each
  is held to the experiments' import rule; planted forbidden imports are
  found.
- **Defect class swept.** A module that names the contract only in text
  (`pbc.electromagnetism.measurement`) is not in the set.

## #589: the SA6 docstring

- **Fix.** "(here: within two)" becomes "(here: within one)", the bound the
  test asserts.

## #590: RR5, a narrowing after an acceptance

- **Fix.** `decision` reports the claim as it stood at the last
  acceptance (the narrowings before it); `claim_of` stays the current
  claim. `steer`, which the page shows, is unchanged.
- **Test.** Accept, narrow, and the decision still names the full claim; a
  new acceptance names the narrower one.

## #593: RR2, a checked plan that could crash

- **Fix.** `_baselines` refuses a grid of fewer than 2 runs.
  `Withheld.settings` takes the bounds of the varied range, and `execute`
  clips each withheld scan to them, so no setting outside what the
  specification was checked against is run.
- **Tests.** Grid runs 1 and 0 are refused, 2 accepted; a laboratory whose
  angle bound lies near the route's best angle: unclipped, the scan makes a
  refused call; clipped, the plan completes with the in-range settings.
- **Defect class swept.** Other divisions by a count from the plan:
  `Withheld.settings` divides by `fraction`, which `_count` requires to be
  positive.

## #596: RR1, the caption of the assessment table

- **Fix.** The caption says "an idea the laboratory cannot run reaches no
  later check", which is what `assess` does (only an infeasible idea stops
  early).
- **Defect class swept.** General statements about the order of checks in
  the three pages of F152: the figure's alt text of RR1 describes the dots
  only for the spin row; RR3's "checked in order" matches `label`, which
  returns at the first failed assumption; RR2 has none.

## #597: RR3, the review log's statuses and the annotator

- **Fix.** `review_log` gives each entry two statuses: `quotation`
  ("quotation checked against its page" for a held passage, "not held" for
  a proposal) and `label_status` ("annotated by one annotator, not
  independently checked", or "awaiting human review" when nobody read it).
  `ANNOTATED_BY` names the coding agent of F152 (Claude Opus, 2026-11-20).
  The page's opening, review-log paragraph, Limits, the scopes of the three
  claims that rest on labels, the outcome, the description, and the heading
  "A verified passage" say what the check covers and that the labels rest
  on one agent's reading; `corpus`, `literature`, `pbc.research`,
  `docs/architecture.md` and `docs/project-map.md` likewise.
- **Tests.** The statuses and what each rests on; a passage without an
  annotation awaits review; the annotator is named as the coding agent.
- **Defect class swept.** Words of F152's three lessons that claim more
  than a check performs, or a person where the coding agent acted: RR1's
  "a person's view" of interest (the judgement's author is the page's
  author) becomes "its author's view", and "one person's view" in its
  Limits "one author's view". RR2: none found.

## #598: RR1, what the archive check finds

- **Fix.** The Issue's second option: the claim is narrowed. The module
  and `verify_archive` docstrings, the page's archive section, its Limits,
  the scope of the tampering claim, the outcome, and the description say
  that an edit or removal before the last entry is found when the digests
  after it were not recomputed, and that a removed last entry or a
  recomputed chain is not.
- **Test.** Both cases pass the check, as the page states.
