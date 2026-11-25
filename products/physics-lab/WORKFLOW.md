# The reference workflow on the simulator

The steps a learner takes to install the Autonomous Physics Lab and run
every protocol, a campaign with refinement and repeated ring-downs (and
the interlock that refuses it without the confirmation), the agent route
beside the classical ones, and the replay of a measured record, with no
device and no model account. A measurement refused by the quality gate and
retried is not in these commands; the capstone page's experiment runs one. The capstone page SA9 runs the same steps in
its experiment (`pbc.electromagnetism.experiments.autonomous_physics_lab`).
Every command is run from the root of a clone of the repository.

Prerequisites: `git` and `uv` (`docs/development.md`, "One-time setup",
has the installer). Nothing else: no key in the environment, no device, no
network after the install.

## 1. Install

```bash
git clone https://github.com/taspinar/physics-by-construction.git
cd physics-by-construction
uv sync --locked --no-dev
```

`--no-dev` installs what the product needs and nothing of the
development tools; the optional group `physics-lab` (the provider SDKs of
a recording with a model) is not needed for any step here.

## 2. The series RLC campaign

```bash
uv run --locked --no-dev python -m pbc.products.physics_lab campaign \
    --plan products/physics-lab/examples/campaign-series-rlc.toml \
    --circuit-confirmed --out run-rlc
```

Without `--circuit-confirmed` the instrument refuses to switch its output
on and the command says what to confirm: that is the interlock, not an
error. The campaign runs the frequency response (a sweep, then refinement
of the bracket of -90 degrees) and the ring-down (repeated until the
interval of Q is narrow enough) on the simulated bench of the RLC lesson.

Read in `run-rlc/`:

- `report.md`: f0 and Q of each protocol with standard errors; "The
  simulator's checks against the closed form" (both passed); the
  consistency of the two protocols (both agree); the figures
  `frequency-response.svg` and `ringdown.svg`;
- `measurements.csv`: one row per measurement, with its stage (sweep,
  refine, retry, repeat), what it follows from, and, for an invalid one,
  why;
- `raw.csv`: every sample of every acquisition, valid or not;
- `run.json`: the run record with `execution_modes` (`simulated`), the
  plan, the evaluator's checks, and the invalid measurements;
- `evidence.json`: the evaluator's ledger; `checkpoints/`: the checkpoint
  and the journal of the segments.

## 3. The agent route beside the classical ones

```bash
uv run --locked --no-dev python -m pbc.products.physics_lab campaign \
    --plan products/physics-lab/examples/campaign-series-rlc.toml \
    --circuit-confirmed --route agent --out run-agent
```

The agent's trace, `fixtures/agent-campaign-series-rlc.json`, is replayed
call by call against a fresh simulated bench. It was written by a scripted
placeholder policy, not a model (`"placeholder": true`). `report.md` ends
with the comparison of the agent route with the classical adaptive policy
and the scripted sweep, run on fresh benches with the same plan and seed,
by the measurements each needed for the same interval width of f0.

## 4. The LED pair

```bash
uv run --locked --no-dev python -m pbc.products.physics_lab campaign \
    --plan products/physics-lab/examples/campaign-led-pair.toml \
    --circuit-confirmed --out run-led
```

The amplitude response of two LEDs of one colour in anti-parallel behind
100 ohm: `report.md` gives the fitted characteristic (n and the voltage at
1 mA) against the simulated LEDs, and the held-out check (the gain
predicted from the largest amplitude alone at every other amplitude);
`amplitude-response.svg` draws both.

## 5. A campaign's export replayed as a recorded campaign

```bash
uv run --locked --no-dev python -m pbc.products.physics_lab campaign \
    --plan products/physics-lab/examples/campaign-series-rlc.toml \
    --mode recorded --sample run-rlc --out run-rlc-replayed
```

The recorded adapter answers every acquisition from `run-rlc/raw.csv`, in
order; nothing is measured again, and the run record says `recorded`.
This is how a live campaign's export becomes a declared dataset.

## 6. A real circuit's record

```bash
uv run --locked --no-dev python -m pbc.products.physics_lab run \
    --input products/physics-lab/examples/live-pilot.toml \
    --mode recorded --sample data/samples/ad3-rlc-pilot/capacitor \
    --out run-pilot
```

The measured sweep of the physical pilot (the dataset `ad3-rlc-pilot`),
replayed by the first protocol of the lab. `run-pilot/run.json` gives f0
near 47 kHz and Q near 1.55, and the check against the closed form of
the parts' labels (f0 near 50.3 kHz, Q near 3.16) fails: real parts are
not their labels. `docs/datasets/ad3-rlc-pilot.md` is the dataset's
dossier.

## 7. Your own feature

The starter and the ring-down fit by the manual route:
`products/physics-lab/starter/README.md` and
`products/physics-lab/ROUTES.md`.

## Optional

- The local interface on one page, on this machine only:
  `uv run --locked --no-dev python -m pbc.products.physics_lab serve
  --input products/physics-lab/examples/frequency-response.toml`, then
  <http://127.0.0.1:8765/>.
- The capstone page's experiment, which runs steps 2 to 4 and 6 and writes
  the page's figures and numbers:
  `uv run --locked --no-dev python -m
  pbc.electromagnetism.experiments.autonomous_physics_lab results`.
- The live mode and the recording of a model's campaign: `README.md`,
  "Your own instrument (live mode)", and `docs/products.md`.
