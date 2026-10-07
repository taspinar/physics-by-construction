# Physics by Construction

An educational website that teaches physics by constructing it. Every concept
comes with code you can run. The learning path leads from numerical
simulation, through experiments driven by AI agents, to formal proofs in
Lean 4.

Site: <https://taspinar.github.io/physics-by-construction/>

Every code listing, figure, and proof on the site is produced or checked by
the same pipeline that publishes it. A lesson whose code fails or whose proof
does not compile cannot be merged.

## Status

The publishing and verification pipeline and the lesson format are in place,
and the first three lessons of the mechanics course are published: kinematics,
Newton's laws, and projectile motion with drag. The plan for the rest is in
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

## Build and verify

Complete the one-time setup in
[docs/development.md](docs/development.md#one-time-setup): Git, uv, elan, jq,
and a browser build for the site checks. Then one command checks everything
and builds the site:

```bash
./scripts/verify.sh
```

It lints and tests the Python code, builds every Lean proof against Mathlib,
builds the site, checks the built pages, and builds the site a second time to
confirm the output is byte-identical. The built site is in `site/_site/`.
The same command runs in CI on every pull request.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md). Corrections and suggestions are
welcome as issues.

## Licence

- Code, including lesson code, tests, and Lean proofs: [MIT](LICENSE).
- Lesson text and figures:
  [Creative Commons Attribution 4.0 International (CC BY 4.0)](LICENSE-CONTENT).

Third-party material keeps its own licence and is listed on the site's About
page.
