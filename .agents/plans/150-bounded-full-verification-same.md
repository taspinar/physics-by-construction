# Plan: F113, bounded full verification by same-machine lesson shards (Issue #150)

Source: Issue #150, ADR 014 decision 11, ADR 012, the human's decisions of 2026-10-14 in
`.agents/handoffs/150.md` (dynamic matrix; build on the store of F61 on main; ci.yml diff in the PR description;
measurements after the workflow is on `main`).

## Design

- **Shares.** `pbc.authoring.shards` derives the lesson shards from the sorted lesson list: `N = ceil(count / S)`,
  `S` from the reserved entry `shard-size: 32` of `scripts/verify.conf`, lesson `i` to shard `i mod N + 1`
  (stable order, sizes differ by at most one, at most `S`, no idle shard). `./scripts/verify.sh --shards` prints the
  shard numbers; the workflow's `plan` job turns them into the matrix of `build` (dynamic; no file lists them).
- **`--shard k/N`** (partial run, implies the group `build`): checks that `N` is the derived one, writes
  `.agents/verification/shard.json`. `build-site.sh` renders the lesson pages of the share that the run executes
  (the share, or share ∩ `execute` of the selection against a base), one `quarto render` per page, into `site/_site`;
  the store restores only the share's reused entries. `check-determinism.sh` does the same from a fresh copy
  (`PBC_SHARD_FILE`). The reproduction test runs for the lessons the shard executed (conftest). Lean builds in full.
- **Part.** After the checks, `pbc.authoring.assemble part` writes `part.json` (shard, lessons, executed, commit),
  `digests.json`, `freeze/` (the share's entries), `site/` (the files of the executed lessons' directories) and
  `files.sha256`; the job uploads it as `lesson-shard-<k>`; no Pages artifact.
- **`--assemble <parts>`** (partial run): `pbc.authoring.assemble verify` requires the parts exactly the derived
  ones, every file as recorded, no link, digests equal to those of the current tree and to each other, the shares
  covering every lesson once, every share entry valid; it builds the union (`digests.json`, `freeze/`) and makes the
  selection against it, which must execute nothing. Then the group `build` runs as today on that selection: the
  Lean build (recreates the record the Lean excerpt reads; chosen over restoring it from a part because it needs no
  new format and is cheap with Mathlib's cache), the build (no lesson cell executes; context regenerated), the second
  build, the previews comparison. After it, `assemble compare` requires every lesson page and file of an executed
  lesson to equal the shard's byte for byte.
- **Workflow.** `plan` (reads the base once on a pull request, prints the matrix) → `build` matrix → `assemble`
  (uploads the Pages artifact, the record, on main the base candidate) → `e2e` → `verify` → `deploy`/`base`.

## Steps

1. `shards.py`, `shard-size`, `--shards`, tests for counts 31..129.
2. `--shard` in verify.sh, `build-site.sh`, `check-determinism.sh`, conftest, second build; tests.
3. `assemble.py` (part, verify, compare), `--assemble`, scripts; tests (missing, extra, altered, duplicate, page differs).
4. `ci.yml` and the tests of the workflow (permissions, groups, no Pages artifact in a shard, matrix equals script).
5. Docs (architecture, deployment, development, project-map), ADR 012 and 014 status, release-readiness note that
   the measurements are pending.
6. Measurements (criteria 1 and 5): need real CI runs after merge; not claimed.
