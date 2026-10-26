# Plan: F82 — Discovering conservation laws and invariants (D13), Issue #294

- Issue: #294 (source: `docs/roadmap.md`, F82); "Detailed implementation
  plan expected: yes, short".
- Branch: `feature/294-discovering-conservation-laws-and`; base `79c58cf`.
- Written by the implementer: no plan existed when the feature started.
- Risk: Level 2 by its paths (one lesson, two modules of `src/pbc/discovery`,
  one experiment, tests, docs); a new lesson's own claims are no trigger.
- Gates: F61, F62, F64, F65, F67, F69 delivered; F113 read as the owner's
  interim full-run gate (up to 110 lessons since 2026-10-24, #281). The site
  has 60 lesson pages; 61 after this feature.

## Design

One format 2 lesson, `site/lessons/agents-llm/11-discovering-conservation-laws`,
id `discovering-conservation-laws`, order 11, `course: mechanics`,
`slot: D13`, methods `simulation` and `llm-agents`.

**The question.** A conserved quantity is a function of the state that keeps
its value along every trajectory and takes different values on different
trajectories. It is looked for as a combination `c · θ(state)` of a public
library of terms `θ`, from trajectories alone; no equation of motion is
fitted or assumed.

**The measure.** The *conservation ratio* of a candidate on a set of
trajectories: the root-mean-square change of `c · θ` about its mean on each
trajectory, divided by `sqrt(Σ c_k² m_k²)` with `m_k` the root-mean-square
size of term `k` on the data: the relative change on the scale of its
terms. An invariant has zero up to the integration error. A candidate whose
terms vanish on the data has no ratio.

**The baseline without a model** (`pbc.discovery.invariants`): the null
space of the matrix of the terms' changes along the trajectories, each
column scaled by `m_k`, by the singular value decomposition; the vectors
whose singular value (divided by the square root of the rows) is at most the
threshold are the candidates, reported in reduced row echelon form so that
each is readable; terms that do not vary on the data are reported apart.

**The verdict of the build on a candidate**, fixed before any run, on
trajectories nobody probed (held-out initial conditions, some beyond the
bounds) under three integration settings (the box's own method and step, the
same method at half the step, and a reference: classical Runge-Kutta at a
fine step):

| Verdict | Rule |
|---|---|
| invariant | ratio at most the tolerance on the held-out trajectories at the reference, and its values differ between trajectories |
| identity | ratio at most the tolerance, and the same value on every trajectory (a property of the state's description, not of the motion) |
| integration artefact | at most the tolerance at the box's own setting, above it at the reference |
| coincidence | at most the tolerance on the trajectories the candidate came from, above it on the held-out ones |
| not conserved | above the tolerance everywhere |
| trivial | its terms do not vary on the held-out trajectories |

**Systems** (each wraps a model of `src/pbc`):

| System | Model | Use |
|---|---|---|
| test oscillator: anisotropic planar harmonic oscillator, symplectic Euler at a coarse step | M11 (`pbc.mechanics.integrators`, the modified energy of `pbc.mechanics.hamiltonian`) | unit test of the criterion: the baseline at the box's setting finds the two modified energies, the verdict rejects them as integration artefacts, the baseline at the reference finds the two known invariants (the energy of each axis); training only on the x axis gives coincidences that held-out trajectories reject |
| the unknown box: a particle in a plane in a hidden central anharmonic potential, velocity Verlet | M11 (`pbc.mechanics.dynamics`, `integrators`) | the agent's run and the baseline with the same budget; known invariants: the energy and the angular momentum; symmetry tested from trajectories (a rotated start gives the rotated trajectory) |
| the heavy symmetric top | M17 (`pbc.mechanics.rigid_body`) | the baseline finds the energy, the vertical and the axial angular momentum, and the identity of the unit axis |
| Burgers' equation in finite volumes | FL9 (`pbc.fluids.finite_volume`, `burgers`) | the totals of u, u², u³: the total of u is kept to round-off by the flux form; the change of the total of u² falls with the cell size before the shock and does not after it |

**The agent's tools** (an `Allowlist` over the box): `trajectory` (four
bounded numbers, the start; one of a budget of 6; returns the state at 8
fixed times), `variation` (13 coefficients; the conservation ratio of the
candidate on each of the agent's own trajectories and pooled; uses no
budget), `submit` (13 coefficients; at most 3 candidates). The hidden
potential, its parameters, and the held-out starts are in no tool, prompt,
or page; a test shows it as in `tests/unit/test_discovery.py`.

**Protocol** (`pbc.discovery.invariant_lab`, fixed before the recording):
budget 6 trajectories, 3 candidates, 12 messages, 4 calls per message,
tolerance 0.01 on the conservation ratio, seed 0, held-out starts and
settings in the box. The score is recomputed from the tool calls: each
submitted candidate's verdict and the number of independent invariants
among them, against the number the baseline finds at the reference.

**Recording.** No provider key is available. As in F66 (accepted by the
owner), the run is recorded by a Claude model in this Claude Code session: a
fresh sub-agent given only the system prompt, the task, and the tool
specifications, choosing every call after reading the results the harness
computed and the session relayed. The fixture's `model` field and the page
say so; a maintainer may replace it with `--record`.

## Discoveries during the work

- **The scale of the ratio.** A first version divided by each term's own
  change; a term that is nearly constant on its own (Lz of the top) was then
  amplified by its tiny change and the baseline returned unreadable
  combinations. The scale is the size of the terms instead, which also makes
  a single conserved term (Lz, a total of Burgers' equation) read as
  conserved. The echelon form of the baseline's basis is taken on the
  scaled coefficients for the same reason.
- **The tolerance** is 0.01, fixed before the recording: the box's own step
  leaves the energy at about 1e-4, and the test oscillator's artefacts are at
  0.04 to 0.06 on the reference; at 1e-3 a stiffness wrong by a fifth of a
  percent already fails.
- **Recording.** Two attempts were discarded before the kept run. A Claude
  Sonnet sub-agent (`claude-sonnet-5-5`) was stopped twice by an API
  safeguard error after its second message. A first Claude Opus sub-agent
  received a relayed result that the session had copied wrongly by hand
  (part of trajectory 4 was taken from trajectory 3; the sub-agent noticed);
  it was discarded. The kept run (`claude-opus-5-5`, 2026-10-26) read each
  result from the file the harness wrote, its only permitted tool, so that
  no result was copied by hand: four messages, eight tool calls, recovered
  (two of two independent invariants). The page says so.

## Visual deliverables

Scientific figures, `simulated`, drawn by `draw_` functions of the
experiment from the tested code, colours from `FIGURE_COLOURS` with marker
or line style as well, alt text without computed values:

- `fig-verdicts` (preview): the conservation ratio of each candidate (the
  agent's, the baseline's, the artefacts) at the three integration settings
  on the held-out trajectories, log scale, the tolerance as a line.
- `fig-burgers-totals`: the relative change of the totals of u and u² over
  time for three cell sizes, the breaking time marked.

Scientific validation: each figure shows quantities a table of the same
lesson prints and a unit test asserts. Accessible fallback: the alt text and
the tables.

Skills: pbc-scientific-visualization@a70b501

## Steps

1. `pbc.discovery.invariants` (library, ratio, baseline, verdicts, systems,
   tools, score) and `tests/unit/test_invariants.py`: the baseline finds the
   known invariants of the test oscillator and rejects its drift artefact;
   coincidences rejected; the truth unreachable.
2. `pbc.discovery.invariant_lab` (protocol, run record, replay, live main)
   and its tests.
3. Record the agent's run; commit `replay.json` next to the page.
4. The experiment `pbc.mechanics.experiments.discovering_conservation_laws`,
   its test, and the lesson page.
5. Docs: `docs/discovery-protocol.md` (invariant discovery), the
   authoring guide's "Discovery lessons" line, `docs/project-map.md`, the
   architecture's package note.
6. Verification: `./scripts/verify.sh --base` (a new lesson).
