import Mathlib.Basic.Real.Basic
import Mathlib.Tactic.Ring
import Mathlib.Tactic.Positivity
import Mathlib.Tactic.FieldSimp
import Mathlib.Tactic.Linarith
import PhysicsByConstruction.Mechanics.EulerOscillator

/-!
# Symplectic Euler on the harmonic oscillator

Symplectic Euler updates the velocity first and moves the particle with the
new velocity. Its energy `springEnergy` is not constant, but a modified energy,
which differs from it by the term `k Δt x v / 2`, is conserved exactly by every
step. This is why the energy of symplectic Euler oscillates and does not grow,
as the numerical integrators lesson shows.

The model and the way the physics enters are those of `EulerOscillator`:
Newton's second law with Hooke's force and the update rule are hypotheses.
-/

namespace PhysicsByConstruction.Mechanics

-- ANCHOR: modifiedEnergy
/-- The modified energy of symplectic Euler with the time step `dt`: the
energy of the spring minus `k dt x v / 2`. -/
noncomputable def modifiedEnergy (m k dt x v : ℝ) : ℝ :=
  springEnergy m k x v - k * dt * x * v / 2
-- ANCHOR_END: modifiedEnergy

-- ANCHOR: symplectic_modified_energy_step
/-- **One symplectic Euler step leaves the modified energy unchanged.**

`hv'` updates the velocity with the acceleration at the old position, and
`hx'` moves the particle with the *new* velocity. `hnewton` is Newton's law
for the spring, `m a = -k x`. -/
theorem symplectic_modified_energy_step
    (m k x v a dt x' v' : ℝ) (hm : 0 < m)
    (hnewton : m * a = -k * x)
    (hv' : v' = v + dt * a)
    (hx' : x' = x + dt * v') :
    modifiedEnergy m k dt x' v' = modifiedEnergy m k dt x v := by
  have ha : a = -k * x / m := by
    field_simp
    linarith [mul_comm m a]
  subst hx' hv' ha
  unfold modifiedEnergy springEnergy
  field_simp
  ring
-- ANCHOR_END: symplectic_modified_energy_step

-- ANCHOR: symplectic_modified_energy_after_steps
/-- **After any number of steps the modified energy is the initial one.**
By induction on the number of steps, from the one-step theorem. -/
theorem symplectic_modified_energy_after_steps
    (m k dt : ℝ) (hm : 0 < m) (x v a : ℕ → ℝ)
    (hnewton : ∀ n, m * a n = -k * x n)
    (hv : ∀ n, v (n + 1) = v n + dt * a n)
    (hx : ∀ n, x (n + 1) = x n + dt * v (n + 1)) (n : ℕ) :
    modifiedEnergy m k dt (x n) (v n) = modifiedEnergy m k dt (x 0) (v 0) := by
  induction n with
  | zero => rfl
  | succ n ih =>
    rw [symplectic_modified_energy_step m k (x n) (v n) (a n) dt _ _ hm
      (hnewton n) (hv n) (hx n), ih]
-- ANCHOR_END: symplectic_modified_energy_after_steps

-- ANCHOR: modified_energy_nonneg
/-- **The modified energy is not negative when the step is small.** For
`k Δt² < 4 m` the quadratic form `m v² - k Δt x v + k x²` has no negative
value, so the conserved quantity bounds the motion: `x` and `v` cannot grow
without limit. -/
theorem modified_energy_nonneg
    (m k dt x v : ℝ) (hm : 0 < m) (hk : 0 < k) (hdt : k * dt ^ 2 < 4 * m) :
    0 ≤ modifiedEnergy m k dt x v := by
  unfold modifiedEnergy springEnergy
  have h1 : 0 ≤ (m * v - k * dt * x / 2) ^ 2 := sq_nonneg _
  have h2 : 0 ≤ k * (4 * m - k * dt ^ 2) * x ^ 2 := by
    have : 0 < 4 * m - k * dt ^ 2 := by linarith
    positivity
  have h3 : 0 ≤ m * (m * v ^ 2 / 2 + k * x ^ 2 / 2 - k * dt * x * v / 2) := by
    nlinarith
  exact nonneg_of_mul_nonneg_right h3 hm
-- ANCHOR_END: modified_energy_nonneg

end PhysicsByConstruction.Mechanics
