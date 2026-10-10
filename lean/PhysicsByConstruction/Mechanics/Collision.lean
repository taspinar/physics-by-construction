import Mathlib.Basic.Real.Basic
import Mathlib.Tactic.Ring
import Mathlib.Tactic.FieldSimp
import Mathlib.Tactic.Positivity
import Mathlib.Data.Fintype.BigOperators

/-!
# Momentum in the elastic collision of two hard spheres

The collision rule of the momentum lesson (`hard_sphere_collision`) gives the
velocities after two hard spheres collide elastically: the component of the
relative velocity along the line of centres reverses and everything else is
unchanged. This module proves that the rule conserves the total momentum, in
every component and for every choice of velocities and direction.

The model is two particles of masses `m₁` and `m₂` with velocities in `ι → ℝ`
(`ι` is the set of coordinate axes). The direction `n` is any vector. The proofs
do not need it to have length one: the momentum is conserved for every
direction, and the unit length matters only for the energy, which this module
does not prove. The statements are about this rule, not about the Python code.
-/

namespace PhysicsByConstruction.Mechanics

-- ANCHOR: collision_rule
/-- The scalar product of two vectors of `ι → ℝ`. -/
def dot {ι : Type*} [Fintype ι] (a b : ι → ℝ) : ℝ :=
  ∑ i, a i * b i

/-- The velocity of the first sphere after the collision:
`v₁' = v₁ - 2 m₂ / (m₁ + m₂) ((v₁ - v₂) · n) n`. -/
noncomputable def firstAfter {ι : Type*} [Fintype ι]
    (m₁ m₂ : ℝ) (v₁ v₂ n : ι → ℝ) : ι → ℝ :=
  fun i => v₁ i - 2 * m₂ / (m₁ + m₂) * dot (fun j => v₁ j - v₂ j) n * n i

/-- The velocity of the second sphere after the collision:
`v₂' = v₂ + 2 m₁ / (m₁ + m₂) ((v₁ - v₂) · n) n`. -/
noncomputable def secondAfter {ι : Type*} [Fintype ι]
    (m₁ m₂ : ℝ) (v₁ v₂ n : ι → ℝ) : ι → ℝ :=
  fun i => v₂ i + 2 * m₁ / (m₁ + m₂) * dot (fun j => v₁ j - v₂ j) n * n i
-- ANCHOR_END: collision_rule

-- ANCHOR: collision_momentum
/-- **The collision rule conserves the total momentum, along every axis.**

The masses are positive (`hm₁`, `hm₂`), which makes `m₁ + m₂` non-zero for the
division of the rule. The direction `n` is arbitrary. -/
theorem collision_momentum {ι : Type*} [Fintype ι]
    (m₁ m₂ : ℝ) (hm₁ : 0 < m₁) (hm₂ : 0 < m₂) (v₁ v₂ n : ι → ℝ) (i : ι) :
    m₁ * firstAfter m₁ m₂ v₁ v₂ n i + m₂ * secondAfter m₁ m₂ v₁ v₂ n i =
      m₁ * v₁ i + m₂ * v₂ i := by
  have hM : m₁ + m₂ ≠ 0 := by positivity
  unfold firstAfter secondAfter
  field_simp
  ring
-- ANCHOR_END: collision_momentum

-- ANCHOR: collision_impulses
/-- **The two spheres receive equal and opposite changes of momentum.** The
impulse on the first sphere is the negative of the impulse on the second,
which is Newton's third law for the collision as a whole. -/
theorem collision_impulses {ι : Type*} [Fintype ι]
    (m₁ m₂ : ℝ) (hm₁ : 0 < m₁) (hm₂ : 0 < m₂) (v₁ v₂ n : ι → ℝ) (i : ι) :
    m₁ * (firstAfter m₁ m₂ v₁ v₂ n i - v₁ i) =
      -(m₂ * (secondAfter m₁ m₂ v₁ v₂ n i - v₂ i)) := by
  have hM : m₁ + m₂ ≠ 0 := by positivity
  unfold firstAfter secondAfter
  field_simp
  ring
-- ANCHOR_END: collision_impulses

end PhysicsByConstruction.Mechanics
