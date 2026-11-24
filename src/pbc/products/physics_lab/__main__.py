"""The command line of the Autonomous Physics Lab slice.

    uv run --locked --extra physics-lab python -m pbc.products.physics_lab \\
        run --input products/physics-lab/examples/frequency-response.toml \\
        --out physics-lab-run

Subcommands:

- ``run``: one run of the protocol (``--route baseline`` or ``agent``,
  ``--mode simulated``, ``recorded``, or ``live``) and its export; the live
  mode opens the learner's own Analog Discovery 3 through the WaveForms SDK
  (``pbc.instruments.analog_discovery``; F140) and closes it at the end;
- ``sample``: write the synthetic sample of the recorded mode;
- ``serve``: the local interface on http://127.0.0.1:8765/ (loopback only);
- ``record``: record the agent's trace, live with ``--provider`` (the
  learner's own key) or with the deterministic scripted policy
  (``--scripted``, a placeholder that is not a model);
- ``campaign`` (F145): a campaign of the plan in ``--plan`` (a TOML file of
  ``products/physics-lab/examples/``) over its protocols, by ``--route
  adaptive``, ``scripted``, or ``agent`` (replayed from its fixture), in
  ``--mode simulated``, ``recorded`` (``--sample``, a campaign's export),
  or ``live``; ``--resume`` continues an interrupted campaign from its
  checkpoint in ``--out``;
- ``record-campaign`` (F145): record an agent campaign's trace on the
  simulated bench with ``--provider``, the recorder's prices, and the
  required ``--spend-ledger``, counting the spend across recordings and
  stopping at ``--ceiling-eur`` (or before a call that would cross it, or
  after a call whose usage the provider does not report), or with
  ``--scripted`` (a placeholder).

The interlock ``circuit-confirmed`` is the learner's own confirmation that
the prepared circuit is connected: ``circuit_confirmed = true`` in the
``--input`` file, or the flag ``--circuit-confirmed``. Without either it
stays open, and the instrument refuses to switch its output on. In the live
mode it covers the pilot's circuit (``workflow.PILOT_CIRCUIT``, W1 -> 100 ohm
-> 1 mH -> 10 nF -> ground) and at least 99 ohm in series, which the 30 mA
current bound assumes; the program prints that text before it opens the
device.

The site build and CI never run this program (invariant I33).
"""

import argparse
import sys
import time
from dataclasses import replace
from pathlib import Path

from pbc.instruments import LIVE, RECORDED, SIMULATED, Refused
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
    _campaign_commands(commands)
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
                "--mode", choices=(SIMULATED, RECORDED, LIVE), default=SIMULATED
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
    if arguments.command in ("campaign", "record-campaign"):
        return _campaign_main(arguments)
    config = _config(arguments)

    if arguments.command == "run":
        driver = None
        if arguments.mode == LIVE:
            from pbc.instruments.analog_discovery import AnalogDiscovery3

            # The learner sees what the confirmation covers (#508 MIN2).
            print(f"circuit-confirmed: {workflow.live_confirmation()}")

            try:
                driver = AnalogDiscovery3()
            except Refused as reason:
                print(f"no live device: {reason}", file=sys.stderr)
                return 1
        try:
            result = workflow.run(
                config,
                arguments.out,
                route=arguments.route,
                mode=arguments.mode,
                sample=arguments.sample,
                trace=arguments.trace,
                driver=driver,
                on_point=lambda m: print(
                    f"  {m.point.frequency_hz:9.1f} Hz  gain {m.point.gain:7.4f}"
                    f"  phase {m.point.phase_deg:8.2f} degrees"
                ),
            )
        finally:
            if driver is not None:
                driver.close()
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


def _campaign_commands(commands) -> None:
    from pbc.products.physics_lab import lab

    campaign = commands.add_parser("campaign")
    campaign.add_argument("--plan", type=Path, required=True)
    campaign.add_argument("--out", type=Path, required=True)
    campaign.add_argument("--route", choices=lab.ROUTES, default=lab.ADAPTIVE)
    campaign.add_argument(
        "--mode", choices=(SIMULATED, RECORDED, LIVE), default=SIMULATED
    )
    campaign.add_argument("--sample", type=Path, default=None)
    campaign.add_argument("--trace", type=Path, default=None)
    campaign.add_argument("--seed", type=int, default=None)
    campaign.add_argument("--circuit-confirmed", action="store_true")
    campaign.add_argument("--resume", action="store_true")
    record = commands.add_parser("record-campaign")
    record.add_argument("--plan", type=Path, required=True)
    record.add_argument("--out", type=Path, required=True)
    source = record.add_mutually_exclusive_group(required=True)
    source.add_argument("--provider", default=None)
    source.add_argument("--scripted", action="store_true")
    record.add_argument("--price-in", type=float, default=None)
    record.add_argument("--price-out", type=float, default=None)
    record.add_argument("--ceiling-eur", type=float, default=50.0)
    record.add_argument("--spend-ledger", type=Path, default=None)


def _print_record(record) -> None:
    state = "valid" if record.valid else f"INVALID: {record.note}"
    setting = "" if record.step.setting is None else f" {record.step.setting:g}"
    print(
        f"  {record.id} {record.step.protocol}{setting} ({record.step.stage}): {state}"
    )


def _campaign_main(arguments) -> int:
    from pbc.products.physics_lab import agent_campaign, bench, lab

    plan, seed = lab.load_plan(arguments.plan)
    if getattr(arguments, "seed", None) is not None:
        seed = arguments.seed
    if arguments.command == "record-campaign":
        if arguments.scripted:
            client, placeholder = agent_campaign.ScriptedCampaignClient(plan), True
        else:
            if arguments.price_in is None or arguments.price_out is None:
                print(
                    "a live recording needs --price-in and --price-out (EUR per"
                    " million tokens)",
                    file=sys.stderr,
                )
                return 2
            if arguments.spend_ledger is None:
                print(
                    "a live recording needs --spend-ledger (a file outside the"
                    " repository): the ceiling counts across recordings",
                    file=sys.stderr,
                )
                return 2
            from pbc.agents.providers import load_client

            spent = agent_campaign.spent_so_far(arguments.spend_ledger)
            if spent >= arguments.ceiling_eur:
                print(
                    f"the spend ledger holds EUR {spent:.2f}, at the ceiling of"
                    f" EUR {arguments.ceiling_eur:g}: nothing recorded",
                    file=sys.stderr,
                )
                return 1
            client = agent_campaign.MeteredClient(
                load_client(arguments.provider),
                agent_campaign.Prices(arguments.price_in, arguments.price_out),
                arguments.ceiling_eur,
                spent,
            )
            placeholder = False
        try:
            transcript = lab.record_campaign(
                plan,
                arguments.out,
                client,
                time.strftime("%Y-%m-%d"),
                seed=seed,
                placeholder=placeholder,
            )
        except Refused as reason:
            print(f"not recorded: {reason}", file=sys.stderr)
            return 1
        finally:
            if isinstance(client, agent_campaign.MeteredClient):
                summary = client.summary()
                print(f"spend: {summary}")
                if arguments.spend_ledger is not None:
                    agent_campaign.add_to_ledger(
                        arguments.spend_ledger,
                        {
                            **summary,
                            "fixture": str(arguments.out),
                            "recorded": time.strftime("%Y-%m-%d"),
                        },
                    )
        print(f"recorded {len(transcript.steps)} steps to {arguments.out}")
        return 0
    sample, recorded_live, driver = None, False, None
    if arguments.mode == RECORDED:
        if arguments.sample is None:
            print(
                "the recorded mode needs --sample (a campaign's export)",
                file=sys.stderr,
            )
            return 2
        sample, sample_plan, sample_mode = lab.read_campaign_export(arguments.sample)
        plan, recorded_live = sample_plan, sample_mode == LIVE
    if arguments.mode == LIVE:
        from pbc.instruments.analog_discovery import AnalogDiscovery3

        print(f"circuit-confirmed: {bench.confirmation(plan, live=True)}")
        try:
            driver = AnalogDiscovery3()
        except Refused as reason:
            print(f"no live device: {reason}", file=sys.stderr)
            return 1
    try:
        result = lab.run_campaign(
            plan,
            arguments.out,
            route=arguments.route,
            mode=arguments.mode,
            seed=seed,
            confirmed=arguments.circuit_confirmed,
            sample=sample,
            recorded_live=recorded_live,
            driver=driver,
            trace=arguments.trace,
            resume_from_checkpoint=arguments.resume,
            on_record=_print_record,
        )
    except Refused as reason:
        print(f"refused: {reason}", file=sys.stderr)
        return 1
    finally:
        if driver is not None:
            driver.close()
    print(result.files["report"].read_text(encoding="utf-8"))
    return 0 if result.segment.status == "complete" else 1


if __name__ == "__main__":
    sys.exit(main())
