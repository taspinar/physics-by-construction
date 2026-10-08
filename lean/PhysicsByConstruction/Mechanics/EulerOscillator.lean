import Mathlib.Basic.Real.Basic
import Mathlib.Tactic.Ring
import Mathlib.Tactic.Positivity
import Mathlib.Tactic.FieldSimp
import Mathlib.Tactic.Linarith

/-!
# Explicit Euler on the harmonic oscillator

One step of explicit Euler multiplies the energy of a mass on a spring by
`1 + (k / m) Δt²`, whatever the state and however small the step. This is the
factor that the harmonic oscillator lesson measures numerically.

The model is a particle of mass `m > 0` on a spring of constant `k > 0` in
one dimension. The physics is stated as hypotheses of the theorems: Newton's
second law with Hooke's force, and the update rule of explicit Euler. The
statements are about this model, not about the Python code that simulates it.
-/

namespace PhysicsByConstruction.Mechanics

-- ANCHOR: springEnergy
/-- The mechanical energy of mass `m` on a spring `k`, at position `x` with
velocity `v`: kinetic `m v² / 2` plus potential `k x² / 2`. -/
noncomputable def springEnergy (m k x v : ℝ) : ℝ :=
  m * v ^ 2 / 2 + k * x ^ 2 / 2
-- ANCHOR_END: springEnergy

-- ANCHOR: euler_energy_step
/-- **One explicit Euler step multiplies the energy by `1 + (k / m) Δt²`.**

The state `(x, v)` is advanced to `(x', v')` by the rule of explicit Euler,
`hx'` and `hv'`, in which the acceleration `a` is the one at the old state.
`hnewton` is Newton's second law with the force of the spring, `m a = -k x`. -/
theorem euler_energy_step
    (m k x v a dt x' v' : ℝ) (hm : 0 < m)
    (hnewton : m * a = -k * x)
    (hx' : x' = x + dt * v)
    (hv' : v' = v + dt * a) :
    springEnergy m k x' v' = (1 + k / m * dt ^ 2) * springEnergy m k x v := by
  have ha : a = -k * x / m := by
    field_simp
    linarith [mul_comm m a]
  subst hx' hv' ha
  unfold springEnergy
  field_simp
  ring
-- ANCHOR_END: euler_energy_step

-- ANCHOR: euler_energy_grows
/-- **The energy never decreases, and grows when anything moves.** With a
positive mass and spring constant, a step of non-zero size multiplies a
positive energy by a factor greater than one. -/
theorem euler_energy_grows
    (m k x v a dt x' v' : ℝ) (hm : 0 < m) (hk : 0 < k)
    (hnewton : m * a = -k * x)
    (hx' : x' = x + dt * v)
    (hv' : v' = v + dt * a)
    (hdt : dt ≠ 0) (hE : 0 < springEnergy m k x v) :
    springEnergy m k x v < springEnergy m k x' v' := by
  rw [euler_energy_step m k x v a dt x' v' hm hnewton hx' hv']
  have : 0 < k / m * dt ^ 2 := by positivity
  nlinarith
-- ANCHOR_END: euler_energy_grows

-- ANCHOR: euler_energy_after_steps
/-- **After `n` steps the energy has been multiplied by `(1 + (k / m) Δt²)ⁿ`.**

`x` and `v` are the positions and velocities after each step, `a` the
accelerations at those states. The hypotheses say that every step is an
explicit Euler step of the spring. -/
theorem euler_energy_after_steps
    (m k dt : ℝ) (hm : 0 < m) (x v a : ℕ → ℝ)
    (hnewton : ∀ n, m * a n = -k * x n)
    (hx : ∀ n, x (n + 1) = x n + dt * v n)
    (hv : ∀ n, v (n + 1) = v n + dt * a n) (n : ℕ) :
    springEnergy m k (x n) (v n) =
      (1 + k / m * dt ^ 2) ^ n * springEnergy m k (x 0) (v 0) := by
  induction n with
  | zero => simp
  | succ n ih =>
    rw [euler_energy_step m k (x n) (v n) (a n) dt _ _ hm (hnewton n) (hx n) (hv n),
      ih, pow_succ]
    ring
-- ANCHOR_END: euler_energy_after_steps

end PhysicsByConstruction.Mechanics
