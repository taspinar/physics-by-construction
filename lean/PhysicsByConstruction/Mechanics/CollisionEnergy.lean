import PhysicsByConstruction.Mechanics.Collision
import Mathlib.Algebra.BigOperators.Ring.Finset
import Mathlib.Algebra.BigOperators.Fin
import Mathlib.Data.Fin.VecNotation
import Mathlib.Tactic.Linarith

/-!
# Kinetic energy in the elastic collision of two hard spheres

The momentum lesson's collision rule, as defined in
`PhysicsByConstruction.Mechanics.Collision`, conserves the total momentum for
every direction `n`. This module answers the question that module leaves open,
the kinetic energy:

* `collision_energy_change` gives the change of the total kinetic energy for
  any direction: `2 m₁ m₂ / (m₁ + m₂) · s² · (n · n - 1)`, where `s` is the
  component of the relative velocity along `n`;
* `collision_energy` is the conservation of the kinetic energy for a direction
  of unit length, `dot n n = 1`;
* `unit_direction_exists` shows that the hypotheses of `collision_energy` can
  hold together, in three dimensions;
* `energy_without_approach` is a statement that compiles and is true, and says
  nothing about a collision: its hypothesis excludes every approach along `n`.
  It is kept to show what a compiled proof does not decide.

The statements reuse the definitions `dot`, `firstAfter`, and `secondAfter` of
the momentum module. They are about real numbers and this rule, not about the
Python code.
-/

namespace PhysicsByConstruction.Mechanics

-- ANCHOR: kinetic_energy
/-- The kinetic energy `m |v|² / 2` of a sphere of mass `m` and velocity `v`,
with the squared length `|v|²` written as `dot v v`. -/
noncomputable def kineticEnergy {ι : Type*} [Fintype ι] (m : ℝ) (v : ι → ℝ) : ℝ :=
  m * dot v v / 2
-- ANCHOR_END: kinetic_energy

/-- The scalar product of a difference with a vector. -/
theorem dot_sub {ι : Type*} [Fintype ι] (a b c : ι → ℝ) :
    dot (fun i => a i - b i) c = dot a c - dot b c := by
  simp only [dot, sub_mul, Finset.sum_sub_distrib]

/-- The squared length of `v + t n`. -/
theorem dot_add_smul_self {ι : Type*} [Fintype ι] (v n : ι → ℝ) (t : ℝ) :
    dot (fun i => v i + t * n i) (fun i => v i + t * n i) =
      dot v v + 2 * t * dot v n + t ^ 2 * dot n n := by
  simp only [dot, Finset.mul_sum, ← Finset.sum_add_distrib]
  exact Finset.sum_congr rfl fun i _ => by ring

-- ANCHOR: collision_energy_change
/-- **The change of the total kinetic energy, for any direction `n`.**

It is `2 m₁ m₂ / (m₁ + m₂) · s² · (n · n - 1)`, with `s` the component of the
relative velocity along `n`. It vanishes when `n` has unit length, and when the
spheres do not approach along `n` (`s = 0`); otherwise the rule creates or
destroys energy. -/
theorem collision_energy_change {ι : Type*} [Fintype ι]
    (m₁ m₂ : ℝ) (hm₁ : 0 < m₁) (hm₂ : 0 < m₂) (v₁ v₂ n : ι → ℝ) :
    kineticEnergy m₁ (firstAfter m₁ m₂ v₁ v₂ n)
        + kineticEnergy m₂ (secondAfter m₁ m₂ v₁ v₂ n)
        - (kineticEnergy m₁ v₁ + kineticEnergy m₂ v₂) =
      2 * m₁ * m₂ / (m₁ + m₂) * dot (fun j => v₁ j - v₂ j) n ^ 2 * (dot n n - 1) := by
  have hM : m₁ + m₂ ≠ 0 := by positivity
  set s := dot (fun j => v₁ j - v₂ j) n
  have h₁ : firstAfter m₁ m₂ v₁ v₂ n = fun i => v₁ i + (-(2 * m₂ / (m₁ + m₂) * s)) * n i :=
    funext fun i => by unfold firstAfter; ring
  have h₂ : secondAfter m₁ m₂ v₁ v₂ n = fun i => v₂ i + (2 * m₁ / (m₁ + m₂) * s) * n i :=
    funext fun i => by unfold secondAfter; ring
  have hs' : s = dot v₁ n - dot v₂ n := dot_sub v₁ v₂ n
  unfold kineticEnergy
  rw [h₁, h₂, dot_add_smul_self, dot_add_smul_self]
  rw [hs']
  field_simp
  ring
-- ANCHOR_END: collision_energy_change

-- ANCHOR: collision_energy
/-- **The collision rule conserves the total kinetic energy when the direction
has unit length.**

The masses are positive (`hm₁`, `hm₂`) and `n` has length one (`hn`). The
velocities are arbitrary, in any number of axes. -/
theorem collision_energy {ι : Type*} [Fintype ι]
    (m₁ m₂ : ℝ) (hm₁ : 0 < m₁) (hm₂ : 0 < m₂) (v₁ v₂ n : ι → ℝ)
    (hn : dot n n = 1) :
    kineticEnergy m₁ (firstAfter m₁ m₂ v₁ v₂ n)
        + kineticEnergy m₂ (secondAfter m₁ m₂ v₁ v₂ n) =
      kineticEnergy m₁ v₁ + kineticEnergy m₂ v₂ := by
  have h := collision_energy_change m₁ m₂ hm₁ hm₂ v₁ v₂ n
  rw [hn, sub_self, mul_zero] at h
  linarith
-- ANCHOR_END: collision_energy

-- ANCHOR: unit_direction_exists
/-- **The hypotheses of `collision_energy` can hold together.** Two positive
masses and a direction of unit length exist in three dimensions, so
`collision_energy` is not true merely because its hypotheses contradict each
other. -/
theorem unit_direction_exists :
    ∃ (m₁ m₂ : ℝ) (n : Fin 3 → ℝ), 0 < m₁ ∧ 0 < m₂ ∧ dot n n = 1 :=
  ⟨1, 1, ![1, 0, 0], one_pos, one_pos, by simp [dot, Fin.sum_univ_three]⟩
-- ANCHOR_END: unit_direction_exists

-- ANCHOR: energy_without_approach
/-- **A statement that compiles and says nothing about a collision.**

It is true and its proof is checked, but its hypothesis `hs` says that the
spheres do not approach along `n`. Then the rule changes no velocity, and the
energy is conserved for any direction, of any length. Every collision the
claim is about has `s ≠ 0`, so this theorem says nothing about any of them.
It is here as an example for the review of a statement, not as a result. -/
theorem energy_without_approach {ι : Type*} [Fintype ι]
    (m₁ m₂ : ℝ) (hm₁ : 0 < m₁) (hm₂ : 0 < m₂) (v₁ v₂ n : ι → ℝ)
    (hs : dot (fun j => v₁ j - v₂ j) n = 0) :
    kineticEnergy m₁ (firstAfter m₁ m₂ v₁ v₂ n)
        + kineticEnergy m₂ (secondAfter m₁ m₂ v₁ v₂ n) =
      kineticEnergy m₁ v₁ + kineticEnergy m₂ v₂ := by
  have h := collision_energy_change m₁ m₂ hm₁ hm₂ v₁ v₂ n
  rw [hs] at h
  linarith
-- ANCHOR_END: energy_without_approach

end PhysicsByConstruction.Mechanics
