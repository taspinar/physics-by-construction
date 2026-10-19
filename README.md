# Physics by Construction

An educational website that teaches physics by constructing it. Every concept
comes with code you can run. The learning path leads from numerical
simulation, through experiments driven by AI agents, to formal proofs in
Lean 4.

Site: <https://taspinar.github.io/physics-by-construction/>

<!-- identity:start (written by pbc.authoring.identity) -->
Physics by Construction is a free, open-source educational initiative by [JIDAI](https://jidai.nl/), created by Ahmet Taspinar.
<!-- identity:end -->

Every code listing, figure, and proof on the site is produced or checked by
the same pipeline that publishes it. A lesson whose code fails or whose proof
does not compile cannot be merged.

## Status

The publishing and verification pipeline and the lesson format are in place,
and the site has twenty-five lessons in five strands. The mechanics course has
eight: kinematics, Newton's laws, projectile motion with drag, the
harmonic oscillator, the comparison of numerical integrators, energy
conservation, momentum and collisions, and the capstone Kepler orbit. The
thermodynamics course has three: random walks and diffusion, the kinetic
theory of gases, and entropy from ensembles. One
lesson has an AI agent run an experiment, one builds a gas from many simple
agents with a local rule, and one proves in Lean what the simulations
showed. The plan for the rest is in
[docs/roadmap.md](docs/roadmap.md).

## Repository layout

| Path | Contents |
|---|---|
| `site/` | The website source, a [Quarto](https://quarto.org) project; lessons are in `site/lessons/` |
| `src/pbc/` | The Python package with the reusable lesson code |
| `lean/` | The Lean 4 project with all proofs, built against Mathlib |
| `tests/` | Unit tests, tests of the verification checks, and checks on the built site |
| `scripts/` | Verification and build scripts, and the development workflow |
| `docs/` | Requirements, architecture, roadmap, decisions, and the [authoring guide](docs/authoring.md) |

## Run an experiment

Every lesson has an experiment: a program that computes the figures and
numbers of its page. Running one needs Git and uv and nothing else:

```bash
git clone https://github.com/taspinar/physics-by-construction.git
cd physics-by-construction
uv sync --locked --no-dev
uv run --locked --no-dev python -m pbc.mechanics.experiments.kinematics results
```

The last command writes the figures of the first lesson and its numbers into
`results/`; the last section of every lesson gives its own command. The
[setup page](https://taspinar.github.io/physics-by-construction/reproduce.html)
says what each kind of lesson needs: the replay of an agent lesson, the
optional live run, and the optional Lean toolchain for the proofs.

CI verifies everything on every pull request with `./scripts/verify.sh`: the
tests, every Lean proof, every lesson's experiment, and the site it builds
and checks. What that command runs, and the setup it needs, is the
maintainers' reference in [docs/development.md](docs/development.md).

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md). Corrections and suggestions are
welcome as issues, with no need to contact anyone: use the forms for a
[bug](https://github.com/taspinar/physics-by-construction/issues/new?template=bug.yml), a
[scientific correction](https://github.com/taspinar/physics-by-construction/issues/new?template=scientific-correction.yml),
a [dataset suggestion](https://github.com/taspinar/physics-by-construction/issues/new?template=dataset-suggestion.yml), or a
[lesson proposal](https://github.com/taspinar/physics-by-construction/issues/new?template=lesson-proposal.yml).

## Licence

- Code, including lesson code, tests, and Lean proofs: [MIT](LICENSE).
- Lesson text and figures:
  [Creative Commons Attribution 4.0 International (CC BY 4.0)](LICENSE-CONTENT).

Third-party material keeps its own licence and is listed on the site's About
page.
