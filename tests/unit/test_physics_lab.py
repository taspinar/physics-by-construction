"""The simulator vertical slice of the Autonomous Physics Lab (F138): the
documented command runs the protocol end to end and exports raw data, a
report, and an evidence record, the same seed giving the same results; the
scripted baseline needs no model; the agent reaches the instrument only
through the allowlisted, validated operation and replays deterministically
from its trace at the product's fixture location; a changed recorded tool
result fails the replay; the local interface works without a socket and
binds only to the loopback interface."""

import csv
import json
import re
import subprocess
import sys
from dataclasses import replace
from pathlib import Path

import pytest

from pbc import evidence
from pbc.agents.messages import ModelMessage, ToolCall
from pbc.agents.replay import ReplayMismatch, load_recording
from pbc.instruments import InterlockOpen, Refused
from pbc.instruments.recorded import load_sample
from pbc.products.physics_lab import agent, workflow
from pbc.products.physics_lab.__main__ import main
from pbc.products.physics_lab.interface import App, check_host
from pbc.products.physics_lab.protocol import Config, load_config

ROOT = Path(__file__).parents[2]
PRODUCT = ROOT / "products" / "physics-lab"
EXAMPLE = PRODUCT / "examples" / "frequency-response.toml"
FIXTURES = PRODUCT / "fixtures"
TRACES = ("agent-frequency-response.json", "starter-agent.json")
EXPORT = (
    "raw.csv",
    "points.csv",
    "report.md",
    "frequency-response.svg",
    "run.json",
    "evidence.json",
)


@pytest.fixture(scope="module")
def runs(tmp_path_factory):
    """The documented command, twice with the same seed, and once more with
    another, by the baseline; and once by the agent route."""
    root = tmp_path_factory.mktemp("runs")
    outputs = {}
    for name, extra in (
        ("first", []),
        ("second", []),
        ("other-seed", ["--seed", "139"]),
        ("agent", ["--route", "agent"]),
    ):
        out = root / name
        status = main(["run", "--input", str(EXAMPLE), "--out", str(out), *extra])
        outputs[name] = (status, out)
    return outputs


def test_the_command_without_a_confirmation_leaves_the_interlock_open(tmp_path, capsys):
    """MIN2 of review-03: without --input and without --circuit-confirmed
    the command line does not confirm the circuit for the learner."""
    status = main(["run", "--out", str(tmp_path / "open")])
    assert status == 1
    run = json.loads((tmp_path / "open" / "run.json").read_text())
    assert run["status"] == "failed"
    assert "interlock circuit-confirmed is open" in capsys.readouterr().out

    status = main(["run", "--circuit-confirmed", "--out", str(tmp_path / "closed")])
    assert status == 0


def test_the_rerecord_hint_is_the_full_documented_command():
    """MIN1 of review-04: the command the replay-mismatch hint prints names
    the input, which confirms the circuit, and the trace to write."""
    assert "record --provider openai" in workflow.RERECORD
    assert "--input products/physics-lab/examples/frequency-response.toml" in (
        workflow.RERECORD
    )
    assert "--out products/physics-lab/fixtures/agent-frequency-response.json" in (
        workflow.RERECORD
    )
    assert (ROOT / "products/physics-lab/examples/frequency-response.toml").is_file()
    assert ROOT / "products/physics-lab/fixtures" / TRACES[0] == workflow.TRACE


def test_recording_with_an_open_interlock_saves_no_trace(tmp_path, capsys):
    """MIN1 of review-04: without the confirmation nothing is recorded, the
    model is never asked, and the command fails with the diagnostic."""
    trace = tmp_path / "trace.json"
    status = main(["record", "--scripted", "--out", str(trace)])
    assert status == 1
    assert not trace.exists()
    assert "interlock circuit-confirmed is open" in capsys.readouterr().err

    class Unasked:
        model = "never asked"
        secrets = ()

        def complete(self, *arguments):
            raise AssertionError("the model was asked with the interlock open")

    with pytest.raises(InterlockOpen):
        workflow.record_trace(
            Config(), trace, Unasked(), "2026-11-05", placeholder=True
        )
    assert not trace.exists()


def test_a_run_without_a_successful_measurement_saves_no_trace(tmp_path):
    class Answers:
        model = "answers without measuring"
        secrets = ()

        def complete(self, *arguments):
            return ModelMessage("f0 is 5 kHz")

    trace = tmp_path / "trace.json"
    config = Config(circuit_confirmed=True)
    with pytest.raises(Refused, match="no measurement"):
        workflow.record_trace(config, trace, Answers(), "2026-11-05", placeholder=True)
    assert not trace.exists()


def test_the_confirmed_scripted_recording_saves_its_trace(tmp_path, capsys):
    trace = tmp_path / "trace.json"
    status = main(
        ["record", "--scripted", "--input", str(EXAMPLE), "--out", str(trace)]
    )
    assert status == 0
    assert load_recording(trace).steps


def test_the_sample_command_with_an_open_interlock_fails_with_its_diagnostic(
    tmp_path, capsys
):
    sample = tmp_path / "sample.json"
    assert main(["sample", "--out", str(sample)]) == 1
    assert not sample.exists()
    assert "interlock circuit-confirmed is open" in capsys.readouterr().err


def test_the_documented_command_exports_raw_data_a_report_and_evidence(runs):
    status, out = runs["first"]
    assert status == 0
    for name in EXPORT:
        assert (out / name).is_file(), name
    with (out / "raw.csv").open() as handle:
        rows = list(csv.DictReader(handle))
    assert len({row["point"] for row in rows}) == 19
    assert len(rows) == 19 * (8 * 64 + 1)
    report = (out / "report.md").read_text()
    assert "Execution mode: simulated" in report
    assert "Verdict: within the tolerance" in report
    run = json.loads((out / "run.json").read_text())
    assert run["status"] == "completed"
    assert run["run"]["mode"] == "simulated"
    assert run["check"]["correct"] is True
    ledger = evidence.load(out / "evidence.json")
    assert ledger.record.environment["execution_mode"] == "simulated"
    summary = evidence.summary(ledger, out)
    assert summary.counts["completed"] == 1
    assert summary.correct == 1
    assert [status for _, status in summary.claims] == ["completed"]


def test_the_same_seed_gives_the_same_results(runs):
    first, second, other = (runs[k][1] for k in ("first", "second", "other-seed"))
    for name in ("raw.csv", "points.csv", "report.md", "frequency-response.svg"):
        assert (first / name).read_bytes() == (second / name).read_bytes(), name
    a = json.loads((first / "run.json").read_text())
    b = json.loads((second / "run.json").read_text())
    assert a["check"] == b["check"]
    # Another seed is another run: different noise, the same physics.
    assert (first / "raw.csv").read_bytes() != (other / "raw.csv").read_bytes()
    assert json.loads((other / "run.json").read_text())["check"]["correct"] is True


def test_the_evaluator_reads_the_raw_samples_not_the_routes_points(runs):
    _, out = runs["first"]
    ledger = evidence.load(out / "evidence.json")
    raw = out / "raw.csv"
    original = raw.read_text()
    try:
        raw.write_text(original.replace("0.", "0.5", 1))
        stale = evidence.check(ledger, out)
        assert [i.path for i in stale] == ["raw.csv"]
        claim = ledger.claims[0]
        assert evidence.claim_status(ledger, claim, stale) == "not evaluated"
    finally:
        raw.write_text(original)


def test_the_agent_route_replays_and_keeps_its_answer_unverified(runs):
    status, out = runs["agent"]
    assert status == 0
    run = json.loads((out / "run.json").read_text())
    assert run["route"] == "agent"
    assert run["candidate_answer"]["label"] == "unverified"
    assert run["check"]["correct"] is True
    report = (out / "report.md").read_text()
    assert "The agent's own answer, unverified" in report
    ledger = evidence.load(out / "evidence.json")
    assert [r.label for r in ledger.reports] == ["unverified"]
    # The agent's numbers are not the result: the table is the evaluator's.
    assert run["check"]["metrics"]["points"] == 12.0


def test_the_scripted_baseline_reaches_the_same_protocol_without_a_model(
    runs, monkeypatch, tmp_path
):
    import pbc.agents.providers as providers

    def no_model(*arguments, **keywords):
        raise AssertionError("the baseline asked for a model")

    # The baseline runs here, under the patch: a model it asked for fails it.
    monkeypatch.setattr(providers, "load_client", no_model)
    result = workflow.run(load_config(EXAMPLE), tmp_path / "baseline", route="baseline")
    assert result.status == "completed"
    assert result.candidate_answer is None
    first = json.loads((tmp_path / "baseline" / "run.json").read_text())
    agent_run = json.loads((runs["agent"][1] / "run.json").read_text())
    assert first["protocol"] == agent_run["protocol"]
    assert first["candidate_answer"] is None
    # And in a fresh process, the baseline's run loads no provider module.
    probe = (
        "import sys\n"
        "from pathlib import Path\n"
        "from pbc.products.physics_lab import workflow\n"
        "from pbc.products.physics_lab.protocol import load_config\n"
        f"workflow.run(load_config(Path({str(EXAMPLE)!r})),"
        f" Path({str(tmp_path / 'probe')!r}), route='baseline')\n"
        "print('\\n'.join(sorted(sys.modules)))\n"
    )
    loaded = subprocess.run(
        [sys.executable, "-c", probe], capture_output=True, text=True, check=True
    ).stdout.split()
    providers_loaded = [
        m
        for m in loaded
        if m == "pbc.agents.providers"
        or m.startswith(("pbc.agents.providers.", "pbc.agents.clients"))
        or m.split(".")[0] in {"openai", "anthropic"}
    ]
    assert providers_loaded == []


def test_the_agent_has_one_allowlisted_operation_bounded_by_the_envelope():
    config = Config(circuit_confirmed=True)
    instrument = workflow.make_instrument(config)
    log = []
    tools = agent.measurement_tools(instrument, config, log)
    assert [t.name for t in tools.tools] == ["measure"]
    spec = tools.specs()[0].parameters["properties"]
    assert spec["frequency_hz"]["maximum"] == instrument.envelope.frequency.high
    assert spec["amplitude_v"]["maximum"] == instrument.envelope.amplitude.high
    for call in (
        ToolCall("a", "measure", {"frequency_hz": 5e3, "amplitude_v": 50.0}),
        ToolCall("b", "set_output", {"amplitude_v": 1.0}),
        ToolCall("c", "measure", {"frequency_hz": 5e3}),
        ToolCall("d", "measure", {"frequency_hz": "5e3", "amplitude_v": 1.0}),
    ):
        assert not tools.dispatch(call).ok, call
    assert log == []
    assert instrument.counts == {"accepted": 0, "refused": 0}


def test_the_agent_tool_refuses_when_the_interlock_is_open():
    config = Config(circuit_confirmed=False)
    instrument = workflow.make_instrument(config)
    tools = agent.measurement_tools(instrument, config, [])
    result = tools.dispatch(
        ToolCall("a", "measure", {"frequency_hz": 5e3, "amplitude_v": 1.0})
    )
    assert not result.ok
    assert "circuit-confirmed" in result.content["error"]


def test_a_changed_recorded_tool_result_fails_the_replay(tmp_path):
    data = json.loads((FIXTURES / TRACES[0]).read_text())
    data["steps"][1]["results"][2]["content"]["phase_deg"] += 0.5
    changed = tmp_path / "changed.json"
    changed.write_text(json.dumps(data))
    with pytest.raises(ReplayMismatch, match="phase_deg"):
        workflow.run(
            load_config(EXAMPLE), tmp_path / "out", route="agent", trace=changed
        )


def test_a_changed_task_fails_the_replay(tmp_path):
    config = replace(load_config(EXAMPLE), agent_budget=15)
    with pytest.raises(ReplayMismatch, match="task or system prompt"):
        workflow.run(config, tmp_path / "out", route="agent")


@pytest.mark.parametrize("name", TRACES)
def test_the_traces_hold_no_credential_or_provider_request_data(name):
    text = (FIXTURES / name).read_text()
    data = json.loads(text)
    assert set(data) <= {
        "format",
        "model",
        "recorded",
        "system",
        "task",
        "steps",
        "placeholder",
    }
    assert data["placeholder"] is True
    assert "not a model" in data["model"]
    for step in data["steps"]:
        assert set(step) == {"text", "tool_calls", "results"}
    assert not re.search(
        r"(?i)api[_-]?key|authori[sz]ation|bearer|header|sk-[a-z0-9]|token", text
    )
    assert load_recording(FIXTURES / name).steps


def test_the_recorded_mode_replays_the_synthetic_sample_and_says_so(tmp_path):
    config = load_config(EXAMPLE)
    sample = tmp_path / "sample.json"
    workflow.write_synthetic_sample(config, sample)
    result = workflow.run(config, tmp_path / "out", mode="recorded", sample=sample)
    assert result.status == "completed"
    assert result.run.mode == "recorded"
    assert result.run.new_experiment is False
    report = (tmp_path / "out" / "report.md").read_text()
    assert "not a new experiment" in report
    assert "it is not a new experiment" in report
    # The recorded mode cannot measure what the sample does not hold.
    other = replace(config, low_hz=900.0)
    failed = workflow.run(other, tmp_path / "other", mode="recorded", sample=sample)
    assert failed.status == "failed"
    assert "cannot make a new measurement" in failed.diagnostics[0]


def test_there_is_no_live_adapter_yet(tmp_path):
    with pytest.raises(ValueError, match="F140"):
        workflow.run(Config(circuit_confirmed=True), tmp_path, mode="live")


def test_a_stop_ends_the_run_as_failed_and_reported(tmp_path):
    def stop_after_three(instrument):
        holder["instrument"] = instrument
        count = {"n": 0}

        def on_point(measurement):
            count["n"] += 1
            if count["n"] == 3:
                instrument.request_stop("stopped by the test")

        holder["on_point"] = on_point

    holder = {}

    def on_point(measurement):
        holder["on_point"](measurement)

    result = workflow.run(
        Config(circuit_confirmed=True),
        tmp_path,
        on_point=on_point,
        on_instrument=stop_after_three,
    )
    assert result.status == "failed"
    assert "stopped by the test" in result.diagnostics[0]
    assert len(result.measurements) == 3
    assert "Status: failed" in (tmp_path / "report.md").read_text()
    assert holder["instrument"].stopped


def test_a_stop_on_the_agent_route_ends_the_run_as_failed_and_exported(tmp_path):
    holder = {}

    def keep(instrument):
        holder["instrument"] = instrument

    def on_point(measurement):
        holder["n"] = holder.get("n", 0) + 1
        if holder["n"] == 5:
            holder["instrument"].request_stop("stopped by the test")

    # Triage review-02 MIN1: the stop reaches the agent as a tool error and
    # the replay departs from its trace; the run is failed, not a mismatch.
    result = workflow.run(
        load_config(EXAMPLE),
        tmp_path,
        route="agent",
        on_point=on_point,
        on_instrument=keep,
    )
    assert result.status == "failed"
    assert "stopped by the test" in result.diagnostics[0]
    assert len(result.measurements) == 5
    with (tmp_path / "raw.csv").open() as handle:
        points = {row["point"] for row in csv.DictReader(handle)}
    assert len(points) == 5
    run = json.loads((tmp_path / "run.json").read_text())
    assert run["status"] == "failed"
    assert run["candidate_answer"] is None
    assert "Status: failed" in (tmp_path / "report.md").read_text()
    assert holder["instrument"].stopped


def test_an_open_interlock_on_the_agent_route_ends_the_run_as_failed(tmp_path):
    config = replace(load_config(EXAMPLE), circuit_confirmed=False)
    result = workflow.run(config, tmp_path, route="agent")
    assert result.status == "failed"
    assert "circuit-confirmed" in result.diagnostics[0]
    assert result.measurements == []
    assert (tmp_path / "evidence.json").exists()


# -- the local interface ---------------------------------------------------------


def test_the_interface_binds_only_to_the_loopback_interface():
    for host in ("127.0.0.1", "::1", "localhost"):
        assert check_host(host) == host
    for host in ("0.0.0.0", "192.168.1.20", "::", "example.org"):
        with pytest.raises(ValueError, match="loopback"):
            check_host(host)


FORM = {
    "route": "baseline",
    "mode": "simulated",
    "seed": "138",
    "low_hz": "1000",
    "high_hz": "25000",
    "amplitude_v": "1",
    "circuit_confirmed": "yes",
}

# What the interface's own page sends from http://127.0.0.1:8765/.
LOCAL = {"host": "127.0.0.1:8765", "origin": "http://127.0.0.1:8765"}


def get(app, path):
    return app.handle("GET", path, {}, {"host": LOCAL["host"]})


def post(app, path, form, headers=LOCAL):
    return app.handle("POST", path, {**form, "token": app.token}, headers)


def test_the_interface_shows_configuration_results_and_exports(tmp_path):
    app = App(tmp_path, Config(), threaded=False)
    page = get(app, "/")
    assert page.status == 200
    text = page.body.decode()
    assert "Not a measurement." in text
    assert "<script" not in text
    assert "No run yet" in text
    assert post(app, "/run", FORM).status == 303
    text = get(app, "/").body.decode()
    assert "Within the tolerance of the closed form (f0 within 1%, Q within 3%)" in text
    assert "<svg" in text
    assert 'href="/files/report.md"' in text
    report = get(app, "/files/report.md")
    assert report.status == 200
    assert b"Execution mode: simulated" in report.body
    assert get(app, "/files/../../etc/passwd").status == 404
    assert get(app, "/elsewhere").status == 404


def test_the_interface_reports_failures_with_what_to_do(tmp_path):
    app = App(tmp_path, Config(), threaded=False)
    post(app, "/run", {**FORM, "seed": "abc"})
    text = get(app, "/").body.decode()
    assert "The seed must be a number" in text
    assert 'role="alert"' in text
    post(app, "/run", {k: v for k, v in FORM.items() if k != "circuit_confirmed"})
    text = get(app, "/").body.decode()
    assert "interlock circuit-confirmed is open" in text


def test_the_interface_runs_the_recorded_mode_with_its_banner(tmp_path):
    app = App(tmp_path, Config(), threaded=False)
    post(app, "/run", {**FORM, "mode": "recorded"})
    text = get(app, "/").body.decode()
    assert "Not a new experiment." in text
    assert 'class="mode recorded"' in text


def test_the_interface_replays_a_new_sample_for_changed_settings(tmp_path):
    # #381: the sample was cached by its seed alone, so a changed range or
    # amplitude with the same seed replayed a stale sample and failed with
    # "cannot make a new measurement".
    app = App(tmp_path, Config(), threaded=False)
    recorded = {**FORM, "mode": "recorded"}
    post(app, "/run", recorded)
    assert app.state.status == "finished", app.state.error
    first = set(tmp_path.glob("synthetic-sample-*.json"))
    assert len(first) == 1
    for change in ({"low_hz": "900"}, {"high_hz": "30000"}, {"amplitude_v": "0.5"}):
        post(app, "/run", {**recorded, **change})
        assert app.state.status == "finished", (change, app.state.error)
        assert app.state.result.status == "completed", change
    samples = set(tmp_path.glob("synthetic-sample-*.json"))
    assert len(samples) == 4 and first < samples
    # The same settings again reuse their sample; the confirmation of the
    # circuit is no setting of the sample.
    post(app, "/run", {**recorded, "low_hz": "900", "circuit_confirmed": "no"})
    assert app.state.status == "finished", app.state.error
    assert set(tmp_path.glob("synthetic-sample-*.json")) == samples
    # Each sample holds the settings it was written for.
    lowest = min(
        min(capture.frequency_hz for capture in load_sample(path).captures)
        for path in samples
    )
    assert lowest == pytest.approx(900.0)


def test_the_interface_runs_the_recorded_mode_without_the_circuit_confirmed(
    tmp_path,
):
    # #381: writing the sample ran the simulated bench with the interlock of
    # the circuit, although the recorded mode is exempt from it.
    app = App(tmp_path, Config(), threaded=False)
    unconfirmed = {k: v for k, v in FORM.items() if k != "circuit_confirmed"}
    post(app, "/run", {**unconfirmed, "mode": "recorded"})
    assert app.state.status == "finished", app.state.error
    assert app.state.result.run.mode == "recorded"
    assert "Not a new experiment." in get(app, "/").body.decode()
    # The simulated mode still needs the confirmation.
    post(app, "/run", unconfirmed)
    assert "interlock circuit-confirmed is open" in get(app, "/").body.decode()


@pytest.mark.parametrize(
    "headers",
    [
        {"host": "127.0.0.1:8765", "origin": "http://evil.example"},
        {"host": "127.0.0.1:8765", "origin": "http://127.0.0.1:9999"},
        {"host": "127.0.0.1:8765", "origin": "null"},
        {"host": "127.0.0.1:8765", "referer": "http://evil.example/page"},
        {"host": "127.0.0.1:8765"},  # neither Origin nor Referer
        {"host": "evil.example:8765", "origin": "http://evil.example:8765"},
        {"origin": "http://127.0.0.1:8765"},  # no Host
    ],
)
def test_the_interface_refuses_a_post_from_another_origin(tmp_path, headers):
    """A page of another origin, or a rebound foreign domain, can neither
    start a run nor supply the confirmation of the circuit (F138, MIN1)."""
    app = App(tmp_path, Config(), threaded=False)
    for path in ("/run", "/stop"):
        assert post(app, path, FORM, headers).status == 403
    assert app.state.status == "idle"
    assert not any(tmp_path.iterdir())


def test_the_interface_refuses_a_post_without_its_token(tmp_path):
    app = App(tmp_path, Config(), threaded=False)
    for form in (FORM, {**FORM, "token": "guessed"}):
        assert app.handle("POST", "/run", form, LOCAL).status == 403
    assert app.state.status == "idle"
    assert app.token in get(app, "/").body.decode()


def test_the_interface_refuses_a_foreign_host_also_for_a_read(tmp_path):
    """DNS rebinding: a foreign domain resolved to 127.0.0.1 reads nothing."""
    app = App(tmp_path, Config(), threaded=False)
    response = app.handle("GET", "/", {}, {"host": "evil.example:8765"})
    assert response.status == 403
    assert app.token.encode() not in response.body


def test_the_interface_accepts_its_own_page_by_referer_or_loopback_name(tmp_path):
    app = App(tmp_path, Config(), threaded=False)
    own = {"host": "localhost:8765", "referer": "http://localhost:8765/"}
    assert post(app, "/run", FORM, own).status == 303
    assert app.state.status == "finished"
