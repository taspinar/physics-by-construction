"""``python -m pbc.products.research_workspace <command>``.

- ``run --example DIR --project DIR``: run the reproduction track end to end
  from the inputs in ``DIR`` into a new project directory; writes the
  report, the evidence ledger, and the static view.
- ``verify --project DIR``: check every chain and digest of a project.
- ``view --project DIR --out FILE``: write the static view again.
- ``decide --project DIR --subject S --decision D --reason R --revisit V``:
  a human's decision about a branch, a question, or a finding.
- ``select --project DIR --question KEY --decision D --reason R --revisit V``:
  a new decision about a question, appended to the archive.
- ``accept-finding --project DIR --finding KEY``: accept a proposed finding,
  only through its recomputed check, and once (a second one is refused).
- ``review --project DIR``: replay the agent reviewer from its fixture
  (no model account) and enter its proposed findings.
- ``record --project DIR --out FILE (--scripted | --provider P ...)``: record
  the agent reviewer; a live recording needs ``--spend-ledger`` outside the
  repository and the prices, and stops at the ceiling of EUR 50 counted
  across every recording of this capstone (``MeteredClient`` of the
  physics lab). Sessions hold no key and record nothing live.

No command opens a socket or a device.
"""

import argparse
import json
import sys
import time
from pathlib import Path

CEILING_EUR = 50.0


def _project(parser):
    parser.add_argument("--project", type=Path, required=True)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m pbc.products.research_workspace")
    commands = parser.add_subparsers(dest="command", required=True)
    run = commands.add_parser("run")
    run.add_argument("--example", type=Path, required=True)
    _project(run)
    _project(commands.add_parser("verify"))
    view = commands.add_parser("view")
    _project(view)
    view.add_argument("--out", type=Path, default=None)
    for name in ("decide", "select"):
        command = commands.add_parser(name)
        _project(command)
        if name == "decide":
            command.add_argument("--subject", required=True)
        else:
            command.add_argument("--question", required=True)
        command.add_argument("--decision", required=True)
        command.add_argument("--reason", required=True)
        command.add_argument("--revisit", required=True)
        command.add_argument("--by", default="the learner")
    accept = commands.add_parser("accept-finding")
    _project(accept)
    accept.add_argument("--finding", required=True)
    accept.add_argument("--by", default="the learner")
    _project(commands.add_parser("review"))
    record = commands.add_parser("record")
    _project(record)
    record.add_argument("--out", type=Path, required=True)
    source = record.add_mutually_exclusive_group(required=True)
    source.add_argument("--scripted", action="store_true")
    source.add_argument("--provider", default=None)
    record.add_argument("--price-in", type=float, default=None)
    record.add_argument("--price-out", type=float, default=None)
    record.add_argument("--spend-ledger", type=Path, default=None)
    record.add_argument("--ceiling-eur", type=float, default=CEILING_EUR)
    arguments = parser.parse_args(argv)

    from pbc.products.research_workspace import project

    if arguments.command == "run":
        try:
            path = project.run(arguments.example, arguments.project)
        except project.ProjectRefused as reason:
            print(f"refused: {reason}", file=sys.stderr)
            return 1
        print(f"wrote {path} and {arguments.project / 'view.html'}")
        return 0
    if arguments.command == "verify":
        problems = project.verify(arguments.project)
        for problem in problems:
            print(problem)
        print("verified" if not problems else f"{len(problems)} problems")
        return 1 if problems else 0
    if arguments.command == "view":
        from pbc.products.research_workspace import view

        out = arguments.out or arguments.project / "view.html"
        view.write(project.summary(arguments.project), out)
        print(f"wrote {out}")
        return 0
    if arguments.command in ("decide", "accept-finding"):
        from pbc.products.research_workspace import log as worklog
        from pbc.products.research_workspace import review

        log = worklog.load(arguments.project / "log.json")
        try:
            if arguments.command == "decide":
                log.decide(
                    arguments.subject,
                    arguments.decision,
                    arguments.reason,
                    arguments.revisit,
                    arguments.by,
                )
            else:
                entry = log.findings().get(arguments.finding)
                if entry is None:
                    raise worklog.LogRefused(
                        f"there is no finding {arguments.finding!r}"
                    )
                context = project.context(arguments.project)
                result = review.run_check(entry.content["check"], context)
                log.accept(arguments.finding, result.passed, arguments.by)
        except worklog.LogRefused as reason:
            print(f"refused: {reason}", file=sys.stderr)
            return 1
        project.save_log(arguments.project, log)
        print("recorded")
        return 0
    if arguments.command == "select":
        return _select(arguments, project)
    if arguments.command == "review":
        from pbc.agents.replay import ReplayMismatch
        from pbc.products.research_workspace import agent
        from pbc.products.research_workspace import log as worklog

        context = project.context(arguments.project)
        try:
            transcript = agent.replay_review(context)
        except ReplayMismatch as reason:
            print(
                f"the replay no longer matches its fixture: {reason}", file=sys.stderr
            )
            return 1
        log = worklog.load(arguments.project / "log.json")
        accepted = agent.enter(transcript, context, log, "the recomputed check")
        project.save_log(arguments.project, log)
        print(f"replayed {len(transcript.steps)} steps; accepted {accepted or 'none'}")
        return 0
    return _record(arguments, project)


def _select(arguments, project) -> int:
    from pbc.research.ideas import Archive

    path = arguments.project / "archive.json"
    entries = project._archive_entries(json.loads(path.read_text(encoding="utf-8")))
    known = {e.idea.key: e.idea for e in entries}
    if arguments.question not in known:
        print(f"refused: no question {arguments.question!r}", file=sys.stderr)
        return 1
    assessments = json.loads((arguments.project / "assessments.json").read_text())
    if arguments.decision == "selected" and assessments[arguments.question]["problems"]:
        print(
            "refused: a question is selected only when its assessment passes: "
            + "; ".join(assessments[arguments.question]["problems"]),
            file=sys.stderr,
        )
        return 1
    archive = Archive()
    archive.entries = list(entries)
    try:
        archive.add(
            known[arguments.question],
            arguments.decision,
            arguments.reason,
            arguments.revisit,
        )
    except ValueError as reason:
        print(f"refused: {reason}", file=sys.stderr)
        return 1
    project._write_json(path, project._archive_data(archive.entries))
    project.write_exports(arguments.project)
    print("recorded")
    return 0


def _record(arguments, project) -> int:
    from pbc.products.physics_lab import agent_campaign
    from pbc.products.research_workspace import agent

    context = project.context(arguments.project)
    if arguments.scripted:
        client, placeholder = agent.ScriptedReviewer(), True
    else:
        if arguments.spend_ledger is None:
            print(
                "a live recording needs --spend-ledger (a file outside the"
                " repository): the ceiling counts across recordings",
                file=sys.stderr,
            )
            return 2
        spent = agent_campaign.spent_so_far(arguments.spend_ledger)
        if spent >= arguments.ceiling_eur:
            print(
                f"the spend ledger holds EUR {spent:.2f}, at the ceiling",
                file=sys.stderr,
            )
            return 1
        from pbc.agents.providers import load_client

        try:
            live = load_client(arguments.provider)
        except (ValueError, ModuleNotFoundError, RuntimeError) as error:
            print(f"no client for {arguments.provider!r}: {error}", file=sys.stderr)
            return 2
        own = getattr(live, "prices_eur_per_mtok", None) or (None, None)
        price_in = own[0] if arguments.price_in is None else arguments.price_in
        price_out = own[1] if arguments.price_out is None else arguments.price_out
        if price_in is None or price_out is None:
            print("a live recording needs --price-in and --price-out", file=sys.stderr)
            return 2
        client = agent_campaign.MeteredClient(
            live,
            agent_campaign.Prices(price_in, price_out),
            arguments.ceiling_eur,
            spent,
        )
        placeholder = False
    try:
        transcript = agent.record(
            context,
            client,
            arguments.out,
            time.strftime("%Y-%m-%d"),
            placeholder=placeholder,
        )
    finally:
        if isinstance(client, agent_campaign.MeteredClient):
            summary = client.summary()
            print(f"spend: {summary}")
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


if __name__ == "__main__":
    raise SystemExit(main())
