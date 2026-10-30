"""Lesson AI6: a model answers questions about four still pictures.

Each picture is a verified figure of the site, drawn by its own lesson's
``draw_`` function: a sketch of the forces on a falling particle and the
velocity of that particle (Newton's laws), the field of two charges
(electric fields), and the calibrated strain of GW150914 with its noise
spectrum (gravitational-wave strain, a measurement under CC BY 4.0). The
questions ask for object properties, spatial relations, and counterfactual
predictions; the build computes every answer from the physics code
(``key``) and scores the recorded answers (``pbc.agents.vision``).

The questions, the prompts, the three simulated pictures, and the replay are
in ``pbc.agents.multimodal_questions``, which reads no data; this module adds
the measured picture, its part of the key, and the live run.

Two runs of the same model on the same task: with the pictures, and without
them (the system prompt says so), the control for what the pictures add.

Run it live on your machine (needs ``OPENAI_API_KEY`` and the optional
dependency)::

    uv run --extra openai python -m pbc.agents.multimodal_lab

Record the replay fixtures of the lesson from a live run (maintainer)::

    uv run --extra openai python -m pbc.agents.multimodal_lab --record
"""

import argparse
import datetime
import sys
from functools import cache
from pathlib import Path

import numpy as np

from pbc.agents.loop import Step, run
from pbc.agents.messages import Picture
from pbc.agents.multimodal_questions import (
    CONDITIONS,
    DETECTORS,
    DIRECTORY,
    MAX_STEPS,
    MEASURED_CAPTION,
    QUESTIONS,
    SIMULATED,
    TASK,
    simulated_key,
)
from pbc.agents.replay import save_recording
from pbc.agents.secrets import Secret, redact
from pbc.agents.vision import Source, answer_sheet
from pbc.data.gwstrain import amplitude_spectrum
from pbc.mechanics.experiments import gravitational_wave_strain as strain


@cache
def strains():
    """The committed strain of both detectors."""
    return strain.load_strain()[0]


def draw_strain():
    """Picture D, drawn by the lesson on gravitational-wave strain."""
    return strain.draw_calibrated_strain(strains())


MEASURED = Source(
    "D",
    "gravitational-wave-strain",
    "fig-calibrated-strain",
    MEASURED_CAPTION,
    draw_strain,
)
SOURCES = (*SIMULATED, MEASURED)


def pictures() -> tuple[Picture, ...]:
    """The four pictures, drawn again by their lessons' code."""
    return tuple(source.picture() for source in SOURCES)


def measured_key() -> dict[int, float]:
    """The answers about the measured picture (questions 10 and 11), from
    the amplitude spectrum of the committed strain."""
    spectra = {name: amplitude_spectrum(s) for name, s in strains().items()}

    def mean_in(name, low, high):
        f, a = spectra[name]
        return float(np.mean(a[(f >= low) & (f <= high)]))

    def peak_in(name, low, high):
        f, a = spectra[name]
        inside = (f >= low) & (f <= high)
        return float(a[inside].max()), float(f[inside][np.argmax(a[inside])])

    lower = min(DETECTORS, key=lambda n: mean_in(n, 12.0, 25.0))
    return {
        10: DETECTORS.index(lower) + 1,
        11: max(peak_in(name, 400.0, 700.0) for name in spectra)[1],
    }


def key() -> dict[int, float]:
    """The answer to every question. Options are numbered from 1."""
    return simulated_key() | measured_key()


def _show(step: Step, *secrets: Secret) -> None:
    if step.message.text:
        print(redact(step.message.text, *secrets))
    for call, result in zip(step.message.tool_calls, step.results, strict=False):
        print(
            redact(
                f"  {call.name}({call.arguments}) -> {dict(result.content)}", *secrets
            )
        )


def main(argv: list[str] | None = None) -> int:
    """The live entry point: run both conditions and optionally record them."""
    from pbc.agents.providers import PROVIDER, load_client

    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument(
        "--record",
        action="store_true",
        help=f"write each run to {DIRECTORY}/replay-<condition>.json",
    )
    options = parser.parse_args(argv)
    try:
        client = load_client(PROVIDER)
    except RuntimeError as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    today = datetime.date.today().isoformat()
    for condition in CONDITIONS:
        print(f"\n== {condition.title} ({client.model}) ==\n")
        transcript = run(
            client,
            answer_sheet(QUESTIONS),
            condition.system,
            TASK,
            MAX_STEPS,
            on_step=lambda step: _show(step, *client.secrets),
            pictures=pictures() if condition.with_pictures else (),
        )
        if options.record:
            path = Path(DIRECTORY) / condition.fixture
            save_recording(path, transcript, today, *client.secrets)
            print(f"\nRecorded to {path}. Review it before you commit it.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
