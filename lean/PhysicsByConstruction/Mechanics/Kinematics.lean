import Mathlib.Basic.Real.Basic
import Mathlib.Tactic.Ring
import Mathlib.Tactic.Linarith

/-!
# Constant acceleration

The identity that links speed and distance without mentioning time, the
algebraic fact behind the exact motion that the kinematics lesson compares
its simulations with.

The model is stated as hypotheses: a particle on a line moves with a constant
acceleration `a` exactly when its position and velocity at time `t` are
given by the two formulas below. Nothing is assumed about how the program
computes them.
-/

namespace PhysicsByConstruction.Mechanics

-- ANCHOR: velocity_sq_of_constant_acceleration
/-- **Torricelli's identity.** A particle with constant acceleration `a`,
starting at `x₀` with velocity `v₀`, has at every time `t` the position `x`
and the velocity `v` of the two hypotheses `hx` and `hv`. Then
`v² = v₀² + 2 a (x - x₀)`: the speed is fixed by the distance covered,
whatever the time it took. -/
theorem velocity_sq_of_constant_acceleration
    (x₀ v₀ a t x v : ℝ)
    (hx : x = x₀ + v₀ * t + a * t ^ 2 / 2)
    (hv : v = v₀ + a * t) :
    v ^ 2 = v₀ ^ 2 + 2 * a * (x - x₀) := by
  subst hx hv
  ring
-- ANCHOR_END: velocity_sq_of_constant_acceleration

-- ANCHOR: displacement_of_mean_velocity
/-- The distance covered with constant acceleration equals the mean of the
initial and the final velocity times the time. -/
theorem displacement_of_mean_velocity
    (x₀ v₀ a t x v : ℝ)
    (hx : x = x₀ + v₀ * t + a * t ^ 2 / 2)
    (hv : v = v₀ + a * t) :
    x - x₀ = (v₀ + v) / 2 * t := by
  subst hx hv
  ring
-- ANCHOR_END: displacement_of_mean_velocity

end PhysicsByConstruction.Mechanics
