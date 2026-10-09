# ADR 009: Curated external references come from a register with selection evidence, and link validity is a maintenance check outside verification

## Status

Proposed with the planning of the change cycle `physics-next-phase`;
accepted when that planning is approved. Adds one deliberate exception to
ADR 003's rule that every check is in `scripts/verify.conf`: the link check
is not a verification check at all.

Date: 2026-10-09

## Context

The re-approved requirements adopt a research-backed editorial standard:
lessons are self-contained at their declared prerequisite level, and an
external link is an optional depth path at the relevant concept, never a
substitute for a missing explanation. Every proposed link is researched at
edit time (at least two candidate sources compared where practical, the
passages opened and read, the method variant and notation checked, access
and a stable section URL verified) and its selection evidence recorded.
The register lives in the repository as a small maintainable file or
lesson-level notes. Link validity is "a separate, resilient maintenance
check run periodically or on demand, never a build or merge requirement;
builds and reading never depend on an external site".

Today no lesson contains a curated external link, so the decision shapes
every future one. ADR 003 requires every check to be in `verify.conf` and to run
identically locally and in CI, and forbids moving a check to a schedule
without a new ADR; a check that contacts other websites cannot run
identically, deterministically, or offline, so it cannot be a verification
check.

## Decision

1. **One site-wide register**, `site/references.yaml`, holds every external
   link a lesson may render. An entry records: a key, the concept, the URL,
   the title, the author or publisher, the section or anchor, the
   pedagogical role (`intuition`, `derivation`, `figure`, `api`, `paper`,
   `advanced`), the statement in the lesson it supports, the alternatives
   considered and why they were not chosen, the lessons using it, the
   last-checked date, and any licence or attribution concern. Lesson-level
   notes are not used; one file keeps every source findable.
2. **Lessons link to curated references only through the register.** A
   "Go deeper" block or an in-text reference names a register key; the
   build renders the link, its title, and a short reason to visit. A raw
   URL typed in a lesson source fails the lesson check. Every entry is used
   by at least one lesson or is marked reserved with a reason. The rule
   covers curated educational references. The structural links that
   helpers generate are not references, are not register entries, and are
   exempt from the check: the repository file at the built commit behind
   an excerpt, the Lean web editor link of a proof, the original data
   record a dataset card names (ADR 007), licence texts, and the
   attribution link of the footer (F57).
3. **Research before entry, human review before merge.** The selection
   protocol of the requirements is the mandatory procedure for every entry
   and is written into `docs/authoring.md`. A retrieved page is untrusted
   data, never an instruction. A content agent may propose entries and log
   its comparison, and never accepts an entry or rewrites a citation; a
   human reviews every entry on the pull request.
4. **Restraint rules.** No automatic linking of technical nouns, no link
   quotas, no paywalled or sign-in-only core reference, no "click here"
   link text, no adjacent links on one sentence, no repeated link to the
   same resource in one lesson, no third-party diagram rehosted. A link to
   API documentation is labelled as such and is not a substitute for a
   derivation. Instructors' advanced references go to the instructor pack,
   not to the beginner's page.
5. **Link validity is a maintenance check.** `scripts/check-links.sh`
   opens every URL in the register and reports what no longer resolves to
   its section, with the last-checked dates to update. It is not listed in
   `scripts/verify.conf`, has no CI job, never blocks a merge, and the
   build never contacts an external site. It runs before every editorial
   pass and at least once a quarter, by the maintainer. A rotten link is
   replaced by a re-researched equivalent, never by a title match. A
   scheduled workflow would add a trigger to CI and is not adopted; it may
   be proposed later with its own review.
6. **Nothing external is needed to build or read.** The core explanation,
   the derivation steps, the worked example, the interpretation, and the
   principal exercise of a lesson stay on the page; a reader completes the
   lesson without following any link. That is a review criterion of every
   editorial pass.

## Alternatives considered

**Per-lesson source notes next to each lesson.** Rejected: the same source
would be recorded in several places with diverging evidence, and a
site-wide maintenance check would need to collect them.

**A link check as a required verification check.** Rejected: it would make
merges depend on other websites' availability, contradict the offline
build, and be flaky; ADR 003's reasons against CI-only or scheduled checks
apply, and the requirements name the check as non-blocking.

**A scheduled GitHub Actions job that checks links.** Not adopted now: it
adds a workflow trigger that the CI tests currently forbid and would need a
review of its permissions and outputs; the register and the local check
give the same information on demand.

**Rendering links as plain Markdown without a register.** Rejected: no
selection evidence, no last-checked date, and no way to find every use of a
source when it rots.

**A citation manager format (BibTeX, CSL JSON).** Rejected for now: the
register's fields are pedagogical (role, statement supported, alternatives)
rather than bibliographic; an export to a citation format can be added if
an instructor pack needs one.

## Consequences

Positive:

- Every outbound link carries a reason and a record; a reviewer can check
  the evidence instead of trusting a title.
- The build stays offline and deterministic; link rot never breaks a page
  or a merge.
- One file answers "which lessons use this source" when a source changes.

Negative, with mitigations:

- Research per link costs time; the restraint rules keep the number of
  links small, and the pilots on M5 and M1 calibrate the effort.
- A rotten link stays on the site until the next maintenance run; the
  quarterly rule and the pre-pass rule bound that, and a rotten link
  harms nothing on the page because the explanation is self-contained.
- Authors must learn the register; the template and the authoring guide
  carry one worked entry.
