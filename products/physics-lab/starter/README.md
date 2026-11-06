# Starter: my frequency-response lab

The project you copy to build your own Autonomous Physics Lab. It imports
only components that Physics by Construction verified at the starter's pin:
the instrument contract with its safety envelope (`pbc.instruments`), the
simulated bench over the series RLC circuit, one point of the protocol with
its analysis and the evaluator's check, and the agent harness. The places
for your work are marked `YOUR WORK`:

- `my_lab/sweep.py`, `refine`: which frequencies to measure after the first
  sweep;
- `my_lab/agent.py`, `task`: what the agent is asked to do.

## The pin

`pyproject.toml` installs `pbc` from the repository by its Git address, at
the `rev` it names: the full hash of a verified commit on `main`. The pin
is `pending` now: this starter is new, and its first pin bump, a small
change after the feature that created it merged, sets the pin to the merged
commit. Until then the starter runs only inside the repository, against its
current tree (below); a copy cannot install `pbc` yet.

## Copy it

Copy this directory and the starter's trace, which the tests replay:

```bash
cp -R products/physics-lab/starter my-lab
mkdir my-lab/fixtures
cp products/physics-lab/fixtures/starter-agent.json my-lab/fixtures/
cd my-lab
uv sync
uv run pytest
```

## Inside the repository

```bash
cd products/physics-lab/starter
PYTHONPATH=. uv run --locked --project ../../.. python -m pytest -c pyproject.toml
```

The repository's CI runs the same tests twice: against its current tree,
and at the pin once it is set (`python -m pbc.products.starters`).

## After you change the task

A replay fails when the task differs from the recorded one. Record the
trace again, with the deterministic scripted policy (no model) or with a
model of your own (`uv sync --extra live`, your key in the environment):

```bash
uv run python -m my_lab.agent --scripted --out fixtures/starter-agent.json
uv run python -m my_lab.agent --provider openai --out fixtures/starter-agent.json
```
