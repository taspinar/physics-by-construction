# Plan: F140 — the one-instrument desk spike, Issue #508

- Issue: #508 (source: `docs/roadmap.md`, F140; created by hand by the
  owner, 2026-11-13). Scope of this Issue now: the desk spike only.
- Branch: `feature/508-f140-instrument-desk-spike`; base `0406b36`.
- Written by the implementer: no plan existed when the feature started.
- Gate: F138 (the instrument contract and the simulator slice) merged.

## Risk

Level 1: documentation only (this plan, a decision record in
`docs/products.md`, the row of `docs/products.md` in
`docs/project-map.md`). No code, no `products/`, no protected path, no
roadmap change. Should the work need any of these, it stops and says so.
Verification: `./scripts/verify.sh --targeted`, run last.

## Visual deliverables

None (a Markdown table, no figure). `Skills: none (no figure, page, or
diagram; the record is text and one table)`.

## Where the record goes

`docs/architecture.md` names `docs/products.md` as the place of the
products' decision records (F138's questions 19 and 21 are settled there),
so the spike's record is a new section of `docs/products.md`, "Decision
record: the instrument desk spike (F140, 2026-11-13)", not a new file.

## Steps

1. Read the F138 contract (`src/pbc/instruments/contract.py`), the bench
   envelope and protocol (`src/pbc/products/physics_lab/protocol.py`), the
   simulated bench (`src/pbc/instruments/simulated.py`), and the
   requirements (decision 42, "Security and privacy constraints",
   questions 17 and 18), to fix what the protocol needs of a device.
2. Per candidate (Analog Discovery 3, Red Pitaya STEMlab 125-14; a third
   only if the documentation shows it is a serious option), from vendor
   documentation only: operating systems and drivers; Python access (SDK,
   licence, maintenance); acquisition and excitation limits against the
   protocol; calibration; bill of materials; cost with source and date;
   realistic duration; failure handling and its mapping onto the `Driver`
   protocol; the security constraints of local control; the simplest
   viable implementation. Each fact with its URL and date accessed; where
   the documentation is silent, say so.
3. Write the record: comparison table, evidence per item, recommendation
   on questions 17 and 18 with the cost, the limits of the spike.
4. Post a short summary on the Issue for the owner.
5. The owner's additions of 2026-11-13 (supervisor session, for PR
   #509): the conditions of use, the owner's euro price check and the Pro
   Bundle as the recommended variant, the corrected description of the
   AD3's power (an optional external 5 V supply, so a pulled USB cable is
   no guaranteed stop), the first experimental phase (RC/RLC on a
   breadboard, EM5 and EM8, follow-up work), and the possible extensions
   as options; in the same section of `docs/products.md`. Documentation
   only; the curriculum, the risk rules, and the scope stay as they are.
6. `./scripts/verify.sh --targeted`, last.

## Limits

- Documentation and the fake driver only: no purchase, no device, no
  download or installation of vendor software, SDKs, or drivers.
- One session; at most three candidates; prices are indicative and dated
  (they change, and a shop price is not a quote).
- The physical pilot, the live adapter, the Bluesky and QCoDeS comparison,
  and the dataset are out of scope until the owner decides questions 17
  and 18 on the Issue; acceptance criteria 2 to 4 are pending for that.
