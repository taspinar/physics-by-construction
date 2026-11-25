# Assessment rubric

How a learner's Autonomous Physics Lab, or a feature added to it, is
assessed. Each criterion is judged from what the lab exports and what its
tests show, never from what its author or an agent says about it. A
criterion is met, partly met, or not met; the evidence column says what to
open. The scientific acceptance criteria of `README.md` are the floor:
a lab that fails one of them is not assessed further.

| Criterion | Met | Partly met | Not met | Evidence |
|---|---|---|---|---|
| **Safety boundary.** Every operation reaches the bench through the guarded instrument | No route, tool, or script of the learner calls a driver, a shell, or the device directly; a request outside the envelope, before the confirmation, or after a stop is refused before any device call | The boundary holds, but a refusal is caught and ignored, or the output is not switched off on every way out of a segment | Something reaches a driver or the device other than through `Instrument` | The code; a call log below the guard (`pbc.instruments.conformance.CallLog`) in the learner's tests |
| **Distinct protocols.** Each protocol measures different physics | Each protocol has its own excitation, analysis, and check, and the analysis is tested against a closed form or a limiting case | Two protocols share an analysis and differ only in a parameter | One measurement presented as several | The protocol modules and their unit tests |
| **Invalid measurements.** Bad data is detected and never fitted | Every protocol passes each capture through the quality gate; an invalid capture is recorded with its reason, exported, and kept out of every fit; a test injects a fault (lost samples, clipping) and shows it | Detected, but not exported, or retried without limit | An invalid capture reaches a fit | `measurements.csv` (`valid`, `note`), `raw.csv`, `run.json` (`invalid`); a test with an injected fault |
| **Intervals.** Every estimate has a standard error that is the right size | Standard errors from the fit's covariance or the spread of repetitions; a test over many seeds shows the error predicts the scatter | Errors are reported but not tested against the scatter | Estimates without errors | `report.md`; a seeded test |
| **Independent check.** The result is checked by something the route does not see | On the simulator, against the closed form; on a real circuit, the agreement of two protocols or a held-out prediction, with the coverage stated | Only the closed form, also for a real circuit | No check, or the route checks itself | `report.md`, `run.json` (`evaluation`) |
| **Campaign record.** Refinement and repetition are traceable | Every measurement names its stage and the measurements it follows from; checkpoints are written and a resume refuses an invalid one | Stages recorded, no basis or no checkpoint | A sequence of numbers with no record of why | `measurements.csv`, `checkpoints/journal.json` |
| **Fair comparison.** An agent or a new policy is compared with baselines | Against the adaptive policy and the scripted sweep on the same plan and seed, by the measurements needed for a stated interval, with what the comparison cannot show | Compared with one baseline, or at an unstated target | No baseline | `report.md` (the comparison), `run.json` (`comparison`) |
| **Evidence package.** A third party can recompute the results | The export holds the raw samples, the report, the run record with its execution mode, and the evaluator's ledger; the evaluator recomputes from `raw.csv` | The export is complete, but a number of the report is not recomputed | Results without raw data, or a mode that is not named | The export directory; `lab.evaluate` run on it |
| **Honest claims.** The report says what the run shows and no more | Simulated, recorded, and live results are labelled; a placeholder trace is called one; limits are stated once with their scope | A limit is missing | A simulation presented as a measurement, or a scripted trace as a model's | `report.md`, `run.json` (`execution_modes`) |
| **Reproducible.** The same inputs give the same outputs | The same plan and seed give the same `raw.csv` and report; the reference workflow runs from a clean clone without a device or a key | Reproducible, but only with a step not written down | Results that cannot be produced again | `WORKFLOW.md`; two runs compared |

A feature built from the starter (the ring-down fit of `ROUTES.md`) is
assessed by the twelve provided tests, which must pass unchanged, and by
the rows "Intervals" and "Invalid measurements" for what the fit refuses.
