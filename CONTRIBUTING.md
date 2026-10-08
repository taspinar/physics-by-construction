# Contributing

Corrections, suggestions, and lesson ideas are welcome.

## How to contribute

1. Open a GitHub Issue that describes the problem or the proposal. All
   non-trivial changes start from an Issue.
2. Work on a branch, never on `main`. Changes land through pull requests.
3. Run `./scripts/verify.sh` before opening the pull request. The setup it
   needs is in [docs/development.md](docs/development.md#one-time-setup). CI
   runs the same command, and a pull request with a failing check cannot be
   merged.
4. Keep the pull request focused on its Issue and include the verification
   evidence.

To propose a new lesson, open an Issue from the **Lesson proposal** form. The
assessment criteria and the path from an accepted proposal to a merged lesson
are in [docs/content-proposals.md](docs/content-proposals.md).

`AGENTS.md` holds the working rules for this repository. They apply whether a
change is written by a person, with AI assistance, or by an agent.

## What a change must respect

- Code, outputs, figures, and proofs on the site come from the build. Do not
  paste a figure, a number, or a code listing by hand.
- Generated files are never committed.
- Lean proofs contain no `sorry`, no `admit`, and no project-declared axiom.
  A physical assumption is a hypothesis of the theorem.
- The site loads nothing from another website and sets no cookie.

`docs/architecture.md` lists all invariants. To write or change a lesson,
follow [docs/authoring.md](docs/authoring.md) and start from
`docs/lesson-template.qmd`.

## Licence of contributions

By submitting a contribution you agree that it is licensed under the licences
of this repository:

- code, including lesson code, tests, and Lean proofs, under the
  [MIT licence](LICENSE);
- lesson text and figures under the
  [Creative Commons Attribution 4.0 International licence](LICENSE-CONTENT).

This covers lesson proposals and drafts too, including a draft an agent writes
from your proposal. A draft written with an agent is identified as such in its
pull request.

Only contribute material that you have the right to license this way. When
you include third-party material, name its source and licence in the pull
request so it can be attributed on the site. The rules for third-party
material in a lesson are in
[docs/authoring.md](docs/authoring.md#third-party-material).

## Security

Do not put secrets in Issues, pull requests, or commits. See
[SECURITY.md](SECURITY.md) for how to report a security-sensitive finding.
