import Mathlib.Basic.Real.Basic
import Mathlib.Tactic.Positivity

/-!
# Pipeline check

One small statement about real numbers. It exists so that every verification
run builds a module against Mathlib, which proves the Mathlib cache path and
the build time before the first proof lesson is written.
-/

namespace PhysicsByConstruction

/-- Kinetic energy `m * v ^ 2 / 2` is non-negative for a non-negative mass. -/
theorem kineticEnergy_nonneg (m v : ℝ) (hm : 0 ≤ m) : 0 ≤ m * v ^ 2 / 2 := by
  positivity

end PhysicsByConstruction
