# Plan: F115 editorial pilot on mechanics 01 to 05 (Issue #375)

Source: Issue #375 and the owner's comment on it ("How this Issue is run"),
`docs/roadmap.md` F115, requirements decision 32, `docs/editorial-voice.md`
(the guide of F114), `docs/authoring.md` ("Lesson format 2").

Skills: none (no new visual deliverable: prose, captions, and alt text of
existing figures only; F32 delivered the diagrams).

## Order of work

One pull request per lesson, as the owner's comment on the Issue sets it:

1. **Pull request 1: lesson 01 only** (`mechanics/01-kinematics-as-a-program`).
   The owner reads it for the register before lessons 02 to 05 are edited.
   This is the first run of the Issue.
2. Pull requests 2 to 5: lessons 02, 03, 04, 05, one each (or in pairs if the
   owner says so on the Issue), each started after the owner has read the one
   before. Every pull request refers to the Issue and does not close it.
3. After all five: the sequence review and the pilot record, with the
   adjustments to the guide, in the last pull request.
4. The approval gate: the owner's explicit approval recorded on the Issue.
   Only then may the Issue close. No sixth lesson is edited, no expansion
   Issue is created.

Relative to F117 (the experiment check on the same files): the edits are
prose only, so they do not conflict with the cells F117 reads; whichever
merges second rebases on the other and repeats the diff evidence below.

## Per-lesson protocol

1. Read the whole lesson against the guide's parts 1 to 7 and its fault
   table, and list findings (weakness, evidence, action, what stays) in the
   handoff note; take the audit's P2 suggestions on the Issue only where the
   guide agrees, and say which were used or left out.
2. Edit prose only: prose paragraphs, captions, alt text, exercise and hint
   wording. Never: a code cell, an inline `{python}` expression, the front
   matter, the text or attributes of a claim span, a section heading or
   identifier, a reference key, `fig-status`, the footer.
3. Diff evidence (recorded in the pull request): for the edited lesson, the
   front matter, every code cell, every inline expression, every claim span,
   every heading line, and every fenced div opener (`:::` lines with
   attributes) are extracted from `main` and from the branch and compared;
   they must be byte-identical. The extraction is a short Python reading of
   the file (code cells between ```` ```{python} ```` and ```` ``` ````,
   inline expressions `` `{python} ...` ``, spans `[...]{.claim ...}`), run
   by the implementer and its result quoted in the pull request.
4. Checks: `./scripts/verify.sh --targeted` (the lesson's single-page render
   and the reproduction of its page), which shows numbers and figures
   unchanged.
5. Review: the independent review of the feature reads the lesson with the
   guide's checklist (findings, not scores) and confirms that no scientific
   statement changed in meaning; its result is recorded on the pull request.

## Completion gates

The criteria for lessons 02 to 05, the sequence review, the pilot record,
and the owner's approval of the pilot are `pending` (gate `post_merge`) in
the record of pull request 1: they wait for the owner's reading of lesson 01
after its merge, by the owner's order on the Issue.
