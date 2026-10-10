# Plan: Issue #61, F17 — Further Lean mechanics proofs

- Issue: #61 (source: `docs/roadmap.md`, F17)
- Branch: `feature/61-further-lean-mechanics-proofs`
- Risk: Medium
- Governing documents: the F08 plan (`25-formal-proofs-strand-first.md`),
  `docs/architecture.md` ("Formal proof lesson"), `docs/authoring.md`
- Written by the implementer: no plan existed when the feature started.

## Goal

Two more lessons of the `lean` strand, each proving a property that a
mechanics lesson showed numerically: momentum conservation of the collision
rule of M7, and the modified energy that symplectic Euler (M5) conserves.

## Design

| Piece | Decision | Reason |
|---|---|---|
| `Mechanics/Collision.lean` | `dot`, `firstAfter`, `secondAfter` (the rule of `hard_sphere_collision` on `ι → ℝ`), `collision_momentum`, `collision_impulses`. Masses positive are hypotheses; the direction `n` is arbitrary | Momentum needs no unit length; energy (needs `n·n = 1` and sums) is left out and stated as a limit |
| `Mechanics/SymplecticEuler.lean` | `modifiedEnergy = springEnergy - k dt x v / 2`; one step, `n` steps by induction, and non-negativity for `k dt² < 4m` | Reuses `springEnergy`; the hypotheses mirror `EulerOscillator` |
| L2 `collision-momentum-proved` (lean 2), L3 `symplectic-euler-conserved-energy` (lean 3) | Format 2. Prerequisites: the mechanics lesson (M7 / M5) and L1. Claims typed `formal-theorem` with scope. Each has a figure because the reproduce test compares figure files | F17 scope; format 2 is the template default |
| M5, M7 | Gain L3, L2 under `related` | Related links are one-directional from the prerequisite side (F37) |
| `tests/e2e/test_lean_lesson.py` | Parametrised over the three Lean lessons (regions, hypotheses, modules) | One set of checks for every lean lesson |

## Out of scope

Energy conservation of the collision rule, soft contact, more than two
bodies, bounds on the distance between the modified and the true energy.

## Discoveries

- Format 2 flags "Lean 4" in prose as a typed number; the body says "Lean".
- The reproduce test needs a figure file in every lesson.
- Lean build: all modules with the cache 24 s for `check-lean.sh`; the two new modules compile in about 4 s (budget 3 min).
