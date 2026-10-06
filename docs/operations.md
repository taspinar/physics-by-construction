# Operations

The site is static files served by GitHub Pages. There is no server, no
database, no secret, and no learner data to operate. Availability is what
GitHub Pages provides: no SLA and no on-call.

## Health

- The status of the CI workflow on `main` is the only monitor. A red run
  means the last change was not published; the previous deployment stays
  online.
- The published site is the artifact of the latest green run on `main`.

## A bad deployment

1. Preferred: open a pull request that reverts the change. It verifies like
   any other change and redeploys when merged.
2. Faster fallback: in the Actions tab, open the last good run on `main` and
   re-run its `deploy` job. It publishes that run's artifact again while the
   artifact is retained (7 days). `main` then still contains the bad change,
   so follow up with the revert.

## Verification fails for a reason outside the change

| Symptom | Cause | Response |
|---|---|---|
| `lean-build` fails with "Mathlib is not complete after fetching its build cache" | The Mathlib cache server is unreachable and the CI cache had no copy | Re-run the job when the server is back. Verification never compiles Mathlib from source. |
| `preflight` reports a browser build that is not installed, in CI | A new Playwright version and a cache miss | The setup step installs it; re-run. Locally, run the install command the hint shows. |
| CI is much slower than usual | A cache was evicted (GitHub keeps 10 GB per repository) | None needed: the next run on `main` saves the caches again. |
| A CI run exceeds its 12 minute budget repeatedly | A lesson or check became expensive | Follow the order in ADR 003: first reduce the cost, then split the job. Dropping a check needs a new ADR. |

## Caches in CI

| Cache | Key changes when |
|---|---|
| uv packages, including the Quarto download | `uv.lock` changes |
| `~/.elan` (Lean toolchain) | `lean/lean-toolchain` changes |
| `lean/.lake` (Lean packages and Mathlib build products) | the toolchain or `lean/lake-manifest.json` changes |
| `~/.cache/ms-playwright` (browser build) | `uv.lock` changes |

A cache miss makes a run slower, never wrong: every cached item is fetched
again from its pinned source.

## Ownership

The repository owner maintains the site, the workflow, and the repository
settings listed in `docs/deployment.md`.
