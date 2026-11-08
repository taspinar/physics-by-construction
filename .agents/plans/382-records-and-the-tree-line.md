# Plan: records and the `Tree:` line (Issue #382)

Visual deliverables: none. Skills: none (scripts, tests, and process text only).

Level 3: the change touches protected workflow scripts and prompts; the owner
approves the exact head. No approval request is needed, since the protected
paths alone make it Level 3 (ADR 020 decision 3).

## What #389 already delivered (on `main` since PR #415 and #424)

- `risk_request_refresh` in `scripts/lib/risk.sh`: writes the content tree on
  the line `Tree:` of the approval request, leaving the rest of the request
  as it is.
- `apply-triage.sh` calls it after a fix session; `run-feature.sh` before
  every review.
- `.agents/approvals` is in `FINGERPRINT_EXCLUDES`, so correcting the request
  makes no verification or review stale (#266's change).
- `risk_content_tree` names the tree of the content without the request
  (#246's correction 2).

## What remained, and this feature does

1. `review-feature.sh` refused a stale `Tree:` line when it was run on its
   own (outside `run-feature.sh`). It now calls `risk_request_refresh` before
   `risk_assess`, so the line is corrected. A line the script cannot write is
   still refused before the verification runs.
2. `finish-feature.sh` refused a stale `Tree:` line. It now calls
   `risk_request_refresh` before `risk_assess` and commits the corrected
   request; the recorded full run stays valid.
3. The prompts (implementer, reviewer) and `docs/development.md` describe the
   line as a derived value that the scripts write.
4. Tests:
   - `tests/review-feature-test.sh`: a request that names another tree is
     corrected and the review goes on; an edit of the completion record is
     followed by a review that writes the new tree, with no manual edit.
   - `tests/risk-workflow-test.sh`: `finish-feature.sh` corrects a wrong tree,
     commits it, and the full-run count stays the same.
   - Both fail on the scripts of `main`.

## The absorbed Issues

- #266: delivered. Its two changes were already on `main`, and #382 turns
  the remaining refusal into a correction. To be closed after the merge.
- #246: delivered. Correction 1 (#243, closed): `risk_triggers` exempts
  `pytest.mark.parametrize`. Correction 2: `risk_content_tree`. To be closed
  after the merge.
- #326: a different defect (`finish-feature.sh` demands triage of an earlier
  round that a later review dispositioned), so it is left out and stays open.
- #363, #377, #378: findings on the completion records of #340 and #375
  (a criterion marked met before its evidence existed). They are about the
  content of the records, not about a script that derives a value, so they
  are left out and stay with those features.
