"""The command line of the Autonomous Physics Lab slice.

    uv run --locked --extra physics-lab python -m pbc.products.physics_lab \\
        run --input products/physics-lab/examples/frequency-response.toml \\
        --out physics-lab-run

Subcommands:

- ``run``: one run of the protocol (``--route baseline`` or ``agent``,
  ``--mode simulated`` or ``recorded``) and its export;
- ``sample``: write the synthetic sample of the recorded mode;
- ``serve``: the local interface on http://127.0.0.1:8765/ (loopback only);
- ``record``: record the agent's trace, live with ``--provider`` (the
  learner's own key) or with the deterministic scripted policy
  (``--scripted``, a placeholder that is not a model).

The interlock ``circuit-confirmed`` is the learner's own confirmation that
the prepared circuit is connected: ``circuit_confirmed = true`` in the
``--input`` file, or the flag ``--circuit-confirmed``. Without either it
stays open, and the instrument refuses to switch its output on.

The site build and CI never run this program (invariant I33).
"""

import argparse
import sys
import time
from dataclasses import replace
from pathlib import Path

from pbc.instruments import RECORDED, SIMULATED, Refused
from pbc.products.physics_lab import workflow
from pbc.products.physics_lab.protocol import Config, load_config

EXAMPLE = workflow.PRODUCT_DIR / "examples" / "frequency-response.toml"


def _config(arguments) -> Config:
    path = arguments.input
    config = load_config(path) if path is not None else Config()
    if arguments.circuit_confirmed:
        config = replace(config, circuit_confirmed=True)
    if arguments.seed is not None:
        config = replace(config, seed=arguments.seed)
    return config


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m pbc.products.physics_lab")
    commands = parser.add_subparsers(dest="command", required=True)
    for name in ("run", "sample", "serve", "record"):
        command = commands.add_parser(name)
        command.add_argument("--input", type=Path, default=None)
        command.add_argument("--seed", type=int, default=None)
        command.add_argument("--circuit-confirmed", action="store_true")
        if name == "run":
            command.add_argument("--out", type=Path, required=True)
            command.add_argument(
                "--route", choices=workflow.ROUTES, default=workflow.BASELINE
            )
            command.add_argument(
                "--mode", choices=(SIMULATED, RECORDED), default=SIMULATED
            )
            command.add_argument("--sample", type=Path, default=None)
            command.add_argument("--trace", type=Path, default=workflow.TRACE)
        elif name == "sample":
            command.add_argument("--out", type=Path, required=True)
        elif name == "serve":
            command.add_argument("--out", type=Path, default=Path("physics-lab-runs"))
            command.add_argument("--host", default="127.0.0.1")
            command.add_argument("--port", type=int, default=8765)
        else:
            command.add_argument("--out", type=Path, required=True)
            source = command.add_mutually_exclusive_group(required=True)
            source.add_argument("--provider", default=None)
            source.add_argument("--scripted", action="store_true")
    arguments = parser.parse_args(argv)
    config = _config(arguments)

    if arguments.command == "run":
        result = workflow.run(
            config,
            arguments.out,
            route=arguments.route,
            mode=arguments.mode,
            sample=arguments.sample,
            trace=arguments.trace,
            on_point=lambda m: print(
                f"  {m.point.frequency_hz:9.1f} Hz  gain {m.point.gain:7.4f}"
                f"  phase {m.point.phase_deg:8.2f} degrees"
            ),
        )
        print(f"{result.run.mode}: {result.run.label}")
        print((result.out_dir / "report.md").read_text(encoding="utf-8"))
        return 0 if result.status == "completed" else 1
    if arguments.command == "sample":
        try:
            sample = workflow.write_synthetic_sample(config, arguments.out)
        except Refused as reason:
            print(f"refused by the instrument: {reason}", file=sys.stderr)
            return 1
        print(f"wrote {len(sample.captures)} captures to {arguments.out}, declared"
              f" {sample.declaration.origin}")  # fmt: skip
        return 0
    if arguments.command == "serve":
        from pbc.products.physics_lab.interface import App, serve

        serve(App(arguments.out, config, host=arguments.host, port=arguments.port))
        return 0
    if arguments.scripted:
        from pbc.products.physics_lab.agent import ScriptedClient

        client, placeholder = ScriptedClient(config), True
    else:
        from pbc.agents.providers import load_client

        client, placeholder = load_client(arguments.provider), False
    try:
        transcript = workflow.record_trace(
            config,
            arguments.out,
            client,
            time.strftime("%Y-%m-%d"),
            placeholder=placeholder,
        )
    except Refused as reason:
        print(f"not recorded: {reason}", file=sys.stderr)
        return 1
    print(f"recorded {len(transcript.steps)} steps to {arguments.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
