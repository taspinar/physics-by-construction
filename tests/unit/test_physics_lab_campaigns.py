"""The campaigns of the Autonomous Physics Lab (F145, Issue #614, criteria 3
and 4): planning and execution through the guarded instrument, the
classical adaptive policy and the scripted sweep, invalid measurements
detected, retried, and recorded, checkpoints and a resume that refuses an
invalid checkpoint, the export with raw data, a report, and an evidence
package naming the execution mode, the evaluator recomputing from the raw
samples, the agent route replayed from its committed fixtures, and the
comparison of routes by the measurements they need."""

import dataclasses
import json
from pathlib import Path

import pytest

from pbc import evidence
from pbc.agents.replay import load_recording
from pbc.instruments import RECORDED, SIMULATED, Refused
from pbc.instruments.channels import ImperfectChannels
from pbc.products.physics_lab import agent_campaign, lab
from pbc.products.physics_lab.bench import make_instrument
from pbc.products.physics_lab.campaign import (
    AMPLITUDE_RESPONSE,
    FREQUENCY_RESPONSE,
    INTERRUPTED,
    LED_PAIR,
    REFINE,
    RETRY,
    SERIES_RLC,
    TRANSIENT,
    Campaign,
    CampaignPlan,
    ResumeRefused,
    Step,
    load_journal,
    next_step,
    resume,
    run_segment,
)

PLAN = CampaignPlan(f0_target=0.00005)
LED = CampaignPlan(circuit=LED_PAIR, protocols=(AMPLITUDE_RESPONSE,))


def instrument(plan=PLAN, seed=3, confirmed=True):
    return make_instrument(plan, SIMULATED, seed=seed, confirmed=confirmed)


# -- the plan -----------------------------------------------------------------------


def test_a_plan_runs_only_the_protocols_of_its_declared_circuit():
    with pytest.raises(ValueError, match="led-pair"):
        CampaignPlan(circuit=LED_PAIR, protocols=(TRANSIENT,))
    with pytest.raises(ValueError, match="unknown circuit"):
        CampaignPlan(circuit="rewired")
    assert CampaignPlan.from_dict(PLAN.to_dict()) == PLAN
    with pytest.raises(ValueError, match="unknown keys"):
        CampaignPlan.from_dict({**PLAN.to_dict(), "rewire": True})


def test_a_step_outside_the_plan_or_the_budget_or_its_basis_is_refused():
    campaign = Campaign(dataclasses.replace(PLAN, budget=1), *instrument())
    with pytest.raises(Refused, match="does not run"):
        campaign.execute(Step(AMPLITUDE_RESPONSE, 1.0, "agent"))
    with pytest.raises(Refused, match="not made"):
        campaign.execute(Step(FREQUENCY_RESPONSE, 5_000.0, REFINE, ("m099",)))
    campaign.execute(Step(FREQUENCY_RESPONSE, 5_000.0, "agent"))
    with pytest.raises(Refused, match="budget"):
        campaign.execute(Step(FREQUENCY_RESPONSE, 5_000.0, "agent"))


# -- the adaptive policy ------------------------------------------------------------


def test_the_adaptive_policy_refines_the_bracket_until_the_target(tmp_path):
    campaign = Campaign(PLAN, *instrument())
    segment = run_segment(campaign, tmp_path / "journal.json")
    assert segment.status == "complete"
    refined = [r for r in campaign.of(FREQUENCY_RESPONSE) if r.step.stage == REFINE]
    assert refined and all(len(r.step.basis) == 2 for r in refined)
    history = lab.width_history(campaign.records)
    assert history[-1][1] <= PLAN.f0_target
    assert len([r for r in campaign.of(TRANSIENT) if r.valid]) >= PLAN.min_ringdowns
    assert segment.output is None  # the output is off after the segment


def test_an_invalid_measurement_is_retried_once_and_never_fitted(tmp_path):
    """A response channel whose rails clip the ring-down's overshoot: every
    ring-down is invalid, each is retried once, the records say why, and
    the budget ends the campaign."""
    plan = dataclasses.replace(PLAN, protocols=(TRANSIENT,), budget=6)
    instrument_, _ = instrument(plan)
    from pbc.products.physics_lab.quality import Rails

    campaign = Campaign(plan, instrument_, Rails(response_v=1.2))
    segment = run_segment(campaign, tmp_path / "journal.json")
    assert segment.status == "budget spent"
    assert not any(r.valid for r in campaign.records)
    assert [r.step.stage for r in campaign.records][:2] == ["repeat", RETRY]
    assert all("response clipped" in r.note for r in campaign.records)
    assert all(r.numbers == {} for r in campaign.records)


def test_the_led_campaign_refines_where_the_gain_changes_most(tmp_path):
    campaign = Campaign(LED, *instrument(LED))
    run_segment(campaign, tmp_path / "journal.json")
    refined = [r for r in campaign.records if r.step.stage == REFINE]
    assert len(refined) == LED.amplitude_refinements
    assert all(r.step.setting > 1.4 for r in refined)


# -- checkpoints and resume ---------------------------------------------------------


class StopAfter:
    """Stops the instrument when the n-th record arrives."""

    def __init__(self, n):
        self.n, self.instrument = n, None

    def __call__(self, record):
        if record.id == f"m{self.n:03d}":
            self.instrument.request_stop("stop requested by the learner")


def _interrupted(tmp_path, n=5):
    stop = StopAfter(n)
    instrument_, rails = instrument()
    stop.instrument = instrument_
    checkpoint, journal = tmp_path / "checkpoint.json", tmp_path / "journal.json"
    campaign = Campaign(PLAN, instrument_, rails, checkpoint, (), stop)
    segment = run_segment(campaign, journal)
    return segment, checkpoint, journal


def test_a_stop_ends_the_segment_with_the_output_off_and_a_checkpoint(tmp_path):
    segment, checkpoint, _ = _interrupted(tmp_path)
    assert segment.status == INTERRUPTED
    assert segment.made == ("m001", "m002", "m003", "m004", "m005")
    assert segment.lost is not None  # the step in flight was not kept
    assert segment.output is None
    assert json.loads(checkpoint.read_text())["records"][-1]["id"] == "m005"


def test_a_valid_checkpoint_resumes_and_the_campaign_finishes(tmp_path):
    _, checkpoint, journal = _interrupted(tmp_path)
    campaign = resume(journal, checkpoint, PLAN, instrument(seed=4)[0])
    assert len(campaign.records) == 5
    segment = run_segment(campaign, journal)
    assert segment.status == "complete" and segment.number == 2
    assert [r.id for r in campaign.records][:5] == [
        "m001",
        "m002",
        "m003",
        "m004",
        "m005",
    ]


@pytest.mark.parametrize("check", ["unchanged", "plan", "bench", "interrupted"])
def test_an_invalid_checkpoint_is_refused_before_the_instrument_is_touched(
    tmp_path, check
):
    _, checkpoint, journal = _interrupted(tmp_path)
    plan, instrument_ = PLAN, instrument(seed=4)[0]
    if check == "unchanged":
        checkpoint.write_text(checkpoint.read_text().replace('"m005"', '"m006"'))
    elif check == "plan":
        plan = dataclasses.replace(PLAN, budget=41)
    elif check == "bench":
        instrument_ = make_instrument(LED, SIMULATED, confirmed=True)[0]
    else:
        campaign = resume(journal, checkpoint, PLAN, instrument(seed=4)[0])
        run_segment(campaign, journal)
    with pytest.raises(ResumeRefused) as refused:
        resume(journal, checkpoint, plan, instrument_)
    assert refused.value.check == check
    assert instrument_.counts == {"accepted": 0, "refused": 0}


def test_no_checkpoint_recorded_is_refused(tmp_path):
    with pytest.raises(ResumeRefused) as refused:
        resume(tmp_path / "journal.json", tmp_path / "none.json", PLAN, instrument()[0])
    assert refused.value.check == "recorded"


# -- the export and the evaluator ----------------------------------------------------


@pytest.fixture(scope="module")
def adaptive(tmp_path_factory):
    out = tmp_path_factory.mktemp("adaptive")
    return lab.run_campaign(PLAN, out, seed=3, confirmed=True)


def test_the_export_holds_raw_data_a_report_and_evidence_with_the_mode(adaptive):
    out = adaptive.out_dir
    for name in (
        "raw.csv",
        "measurements.csv",
        "report.md",
        "run.json",
        "evidence.json",
        "frequency-response.svg",
        "ringdown.svg",
    ):
        assert (out / name).exists(), name
    data = json.loads((out / "run.json").read_text())
    assert data["execution_modes"] == [SIMULATED]
    assert data["run"]["label"].startswith("simulated experiment")
    assert data["verdict"] is True
    ledger = evidence.load(out / "evidence.json")
    assert ledger.record.environment["execution_mode"] == SIMULATED
    assert evidence.check(ledger, out) == ()
    assert "not a measurement" in (out / "report.md").read_text()


def test_the_evaluator_recomputes_from_the_raw_samples(adaptive):
    again = lab.evaluate(adaptive.out_dir / "raw.csv", PLAN, SIMULATED)
    assert again == adaptive.evaluation
    checks = again["simulator_checks"]
    assert checks[FREQUENCY_RESPONSE]["correct"] and checks[TRANSIENT]["correct"]
    assert [a["agree"] for a in again["agreements"]] == [True, True]


def test_an_export_replays_as_a_recorded_campaign_and_is_no_new_experiment(
    adaptive, tmp_path
):
    sample, plan, mode = lab.read_campaign_export(adaptive.out_dir)
    assert plan == PLAN and mode == SIMULATED
    replayed = lab.run_campaign(
        plan, tmp_path / "replayed", mode=RECORDED, sample=sample
    )
    data = json.loads((tmp_path / "replayed" / "run.json").read_text())
    assert data["run"]["mode"] == RECORDED and data["run"]["new_experiment"] is False
    # raw.csv keeps 12 significant digits, so the replay agrees to that.
    for again, before in zip(
        replayed.evaluation["agreements"],
        adaptive.evaluation["agreements"],
        strict=True,
    ):
        assert again["agree"] == before["agree"]
        assert again["sigmas"] == pytest.approx(before["sigmas"], rel=1e-6)


def test_the_comparison_names_the_measurements_each_route_needed(tmp_path):
    adaptive_ = Campaign(PLAN, *instrument())
    run_segment(adaptive_, tmp_path / "a.json")
    scripted = Campaign(PLAN, *instrument())
    run_segment(scripted, tmp_path / "s.json", lab.scripted_policy)
    comparison = lab.compare_routes(
        {
            "adaptive": lab.width_history(adaptive_.records),
            "scripted": lab.width_history(scripted.records),
        }
    )
    routes = comparison["routes"]
    assert comparison["target"] == max(r["final_width"] for r in routes.values())
    assert routes["adaptive"]["needed"] <= routes["adaptive"]["measurements"]
    assert routes["scripted"]["needed"] <= PLAN.sweep_points
    assert routes["adaptive"]["final_width"] < routes["scripted"]["final_width"]


# -- the agent route ------------------------------------------------------------------


@pytest.mark.parametrize(
    "plan_name", ["campaign-series-rlc.toml", "campaign-led-pair.toml"]
)
def test_the_committed_agent_campaigns_replay_against_the_simulated_bench(
    plan_name, tmp_path
):
    """ADR 022 decision 8: every recorded call of the committed fixture is
    executed again on a fresh bench with the plan's seed, and the replay
    fails on any difference."""
    plan, seed = lab.load_plan(lab.EXAMPLES / plan_name)
    trace = lab.trace_path(plan)
    recording = load_recording(trace)
    result = lab.run_campaign(
        plan,
        tmp_path / "agent",
        route=lab.AGENT,
        seed=seed,
        confirmed=True,
        trace=trace,
    )
    assert result.segment.status == "complete"
    assert len(result.records) == sum(
        len(s.message.tool_calls) for s in recording.steps
    )
    # The segment made every measurement of the replay, and the run record
    # and the evidence package say so (#614 review 02, MIN1).
    made = tuple(r.id for r in result.records)
    assert result.segment.made == made
    data = json.loads((tmp_path / "agent" / "run.json").read_text())
    assert data["segment"]["made"] == list(made)
    package = (tmp_path / "agent" / "evidence.json").read_text()
    assert f"complete after {len(made)} measurements" in package
    assert data["candidate_answer"]["label"] == evidence.UNVERIFIED
    assert data["verdict"] is True
    # Every agent result stands beside the classical adaptive policy and the
    # scripted sweep, on fresh benches with the same plan and seed (#614 M1).
    comparison = data["comparison"]
    assert comparison["seed"] == seed and comparison["mode"] == SIMULATED
    assert set(comparison["measurements"]) == {lab.AGENT, lab.ADAPTIVE, lab.SCRIPTED}
    assert comparison["measurements"][lab.AGENT] == len(result.records)
    report = (tmp_path / "agent" / "report.md").read_text()
    assert "## The agent beside the classical routes" in report
    if FREQUENCY_RESPONSE in plan.protocols:
        routes = comparison["routes"]
        assert set(routes) == {lab.AGENT, lab.ADAPTIVE, lab.SCRIPTED}
        assert comparison["target"] == max(r["final_width"] for r in routes.values())
        assert all(r["needed"] <= r["measurements"] for r in routes.values())
        assert f"{comparison['target']:.3g}" in report
    else:
        assert comparison["target"] is None and "counts only" in comparison["note"]
    assert not (tmp_path / "agent" / "checkpoints" / "adaptive-journal.json").exists()


def test_the_baselines_need_the_simulated_bench():
    comparison = lab.baseline_comparison(PLAN, RECORDED, 0, True, [])
    assert comparison["target"] is None and comparison["routes"] == {}
    assert "no baseline in the recorded mode" in comparison["note"]


def test_a_stop_during_the_agent_replay_fails_the_segment_with_its_reason(tmp_path):
    plan, seed = lab.load_plan(lab.EXAMPLES / "campaign-series-rlc.toml")
    stop = StopAfter(3)

    def hold(campaign):
        stop.instrument = campaign.instrument

    result = lab.run_campaign(
        plan,
        tmp_path / "agent",
        route=lab.AGENT,
        seed=seed,
        confirmed=True,
        on_record=stop,
        on_campaign=hold,
    )
    assert result.segment.status == "failed"
    assert "halted" in result.segment.diagnostics[0]
    assert len(result.records) == 3
    assert result.segment.made == tuple(r.id for r in result.records)
    # The journal, run.json and evidence.json carry one status and reason.
    last = load_journal(tmp_path / "agent" / "checkpoints" / "journal.json")[-1]
    assert last["status"] == "failed"
    assert list(last["diagnostics"]) == list(result.segment.diagnostics)
    run = json.loads((tmp_path / "agent" / "run.json").read_text(encoding="utf-8"))
    assert run["segment"]["status"] == "failed"
    assert list(run["segment"]["diagnostics"]) == list(result.segment.diagnostics)
    (attempt,) = evidence.load(tmp_path / "agent" / "evidence.json").attempts
    assert attempt.diagnostics == ("failed after 3 measurements", *last["diagnostics"])


def test_the_metered_client_stops_at_the_ceiling_with_what_was_recorded():
    class Counting:
        model, secrets = "counting", ()

        def __init__(self):
            self.inner = agent_campaign.ScriptedCampaignClient(PLAN)
            self.last_usage = None

        def complete(self, system, conversation, tools):
            self.last_usage = {"input_tokens": 1_000_000, "output_tokens": 0}
            return self.inner.complete(system, conversation, tools)

    metered = agent_campaign.MeteredClient(
        Counting(),
        agent_campaign.Prices(10.0, 30.0),
        ceiling_eur=25.0,
        spent_before=5.0,
    )
    campaign = Campaign(PLAN, *instrument())
    tools = agent_campaign.campaign_tools(campaign)
    from pbc.agents.loop import run

    transcript = run(
        metered,
        tools,
        agent_campaign.SYSTEM,
        agent_campaign.task(PLAN),
        PLAN.budget + 2,
    )
    summary = metered.summary()
    assert summary["calls"] == 2 and summary["stopped_at_ceiling"]
    assert summary["spent_total_eur"] == 25.0
    assert "ceiling" in transcript.steps[-1].message.text
    assert len(campaign.records) == 8  # the two sweep messages, then the stop


def test_the_metered_client_stops_after_a_call_with_no_reported_usage():
    class Silent:
        model, secrets, last_usage = "silent", (), None

        def __init__(self):
            self.inner = agent_campaign.ScriptedCampaignClient(PLAN)
            self.calls = 0

        def complete(self, system, conversation, tools):
            self.calls += 1
            return self.inner.complete(system, conversation, tools)

    silent = Silent()
    metered = agent_campaign.MeteredClient(
        silent, agent_campaign.Prices(10.0, 30.0), ceiling_eur=50.0
    )
    first = metered.complete(agent_campaign.SYSTEM, [], [])
    again = metered.complete(agent_campaign.SYSTEM, [], [])
    assert silent.calls == 1  # the provider is never called again
    assert first.tool_calls == () and again.tool_calls == ()
    assert "no token usage" in first.text
    summary = metered.summary()
    assert summary["stopped_at_ceiling"] and not summary["usage_reported_on_every_call"]


def test_the_metered_client_stops_before_a_call_that_would_cross_the_ceiling():
    class Dear:
        model, secrets = "dear", ()

        def __init__(self):
            self.inner = agent_campaign.ScriptedCampaignClient(PLAN)
            self.last_usage = None
            self.calls = 0

        def complete(self, system, conversation, tools):
            self.calls += 1
            self.last_usage = {"input_tokens": 1_000_000, "output_tokens": 0}
            return self.inner.complete(system, conversation, tools)

    dear = Dear()
    metered = agent_campaign.MeteredClient(
        dear, agent_campaign.Prices(10.0, 30.0), ceiling_eur=25.0
    )
    metered.complete(agent_campaign.SYSTEM, [], [])  # EUR 10
    metered.complete(agent_campaign.SYSTEM, [], [])  # EUR 20; a third would be 30
    stop = metered.complete(agent_campaign.SYSTEM, [], [])
    assert dear.calls == 2 and metered.spent == 20.0
    assert "would cross" in stop.text and stop.tool_calls == ()


def test_a_live_recording_needs_a_spend_ledger(tmp_path, capsys):
    from pbc.products.physics_lab.__main__ import main

    code = main(
        [
            "record-campaign",
            "--plan",
            str(lab.EXAMPLES / "campaign-series-rlc.toml"),
            "--out",
            str(tmp_path / "trace.json"),
            "--provider",
            "openai",
            "--price-in",
            "1",
            "--price-out",
            "1",
        ]
    )
    assert code == 2 and "--spend-ledger" in capsys.readouterr().err
    assert not (tmp_path / "trace.json").exists()


def test_the_spend_ledger_accumulates_across_recordings(tmp_path):
    ledger = tmp_path / "spend.json"
    assert agent_campaign.spent_so_far(ledger) == 0.0
    agent_campaign.add_to_ledger(ledger, {"cost_eur": 1.25})
    agent_campaign.add_to_ledger(ledger, {"cost_eur": 2.5})
    assert agent_campaign.spent_so_far(ledger) == 3.75


def test_the_agent_sees_no_circuit_value(tmp_path):
    campaign = Campaign(PLAN, *instrument())
    tools = agent_campaign.campaign_tools(campaign)
    texts = json.dumps([s.__dict__ for s in tools.specs()], default=str)
    for hidden in ("resistance", "inductance", "capacitance", "closed form"):
        assert hidden not in texts
    assert {t.name for t in tools.tools} == {"measure_point", "measure_ringdown"}
    assert SERIES_RLC not in agent_campaign.task(PLAN)
    assert next_step(PLAN, []) == Step(FREQUENCY_RESPONSE, 1_000.0, "sweep")


def test_lost_samples_are_detected_in_every_protocol(tmp_path):
    from pbc.instruments.channels import Dropouts

    plan = dataclasses.replace(PLAN, budget=4)
    instrument_, rails = instrument(plan)
    instrument_._driver = ImperfectChannels(  # a lossy link below the guard
        instrument_._driver, {}, Dropouts(bursts=4, length=30, seed=1)
    )
    campaign = Campaign(plan, instrument_, rails)
    run_segment(campaign, tmp_path / "journal.json")
    assert campaign.records and not any(r.valid for r in campaign.records)
    assert all("lost" in r.note for r in campaign.records)


def test_the_openai_client_reads_the_tokens_of_a_response():
    from pbc.agents.clients.openai import parse_usage

    assert parse_usage({"usage": {"prompt_tokens": 120, "completion_tokens": 30}}) == {
        "input_tokens": 120,
        "output_tokens": 30,
    }
    assert parse_usage({"choices": []}) is None


# -- the interface ---------------------------------------------------------------------


def _app(tmp_path):
    from pbc.products.physics_lab.interface import App
    from pbc.products.physics_lab.protocol import Config

    return App(tmp_path, Config(), threaded=False)


def _post(app, path, form):
    headers = {"host": "127.0.0.1:8765", "origin": "http://127.0.0.1:8765"}
    return app.handle("POST", path, {**form, "token": app.token}, headers)


def _get(app, path):
    return app.handle("GET", path, {}, {"host": "127.0.0.1:8765"})


def test_the_interface_runs_a_campaign_and_shows_its_results(tmp_path):
    app = _app(tmp_path)
    page = _get(app, "/").body.decode()
    assert "Run a campaign" in page and "never" in page
    response = _post(
        app,
        "/campaign",
        {
            "plan": "campaign-led-pair.toml",
            "route": "adaptive",
            "circuit_confirmed": "yes",
        },
    )
    assert response.status == 303
    page = _get(app, "/").body.decode()
    assert "Campaign by the adaptive route" in page
    assert "held-out" not in page or "agrees" in page
    assert "agrees with the gain at every other amplitude" in page
    assert _get(app, "/campaign-files/raw.csv").status == 200
    assert _get(app, "/campaign-files/../run.json").status == 404


def test_the_interface_reports_an_unconfirmed_circuit_with_what_to_do(tmp_path):
    app = _app(tmp_path)
    _post(app, "/campaign", {"plan": "campaign-series-rlc.toml", "route": "scripted"})
    page = _get(app, "/").body.decode()
    assert "The campaign did not finish" in page
    # The guidance is right for every route: only the adaptive and scripted
    # routes resume; the agent route replays from the start (review 04, S1).
    assert "The agent route replays its trace from the start" in page
    assert "interlock" in page and "circuit was not confirmed" in page


def test_the_interface_refuses_a_campaign_from_another_origin(tmp_path):
    app = _app(tmp_path)
    headers = {"host": "127.0.0.1:8765", "origin": "http://evil.example"}
    response = app.handle("POST", "/campaign", {"token": app.token}, headers)
    assert response.status == 403
    assert app.campaigns.state.status == "idle"


def test_a_recording_with_a_local_model_needs_no_prices(tmp_path, monkeypatch):
    """``record-campaign`` takes the prices of a client that has its own (the
    local client, at zero, #615) and asks the recorder for them otherwise."""
    import pbc.agents.providers as providers
    from pbc.products.physics_lab.__main__ import main

    plan_path = (
        Path(__file__).parents[2]
        / "products/physics-lab/examples/campaign-led-pair.toml"
    )
    plan, _ = lab.load_plan(plan_path)

    class Local:
        model, secrets = "a-local-model", ()

        def __init__(self, prices):
            self.inner = agent_campaign.ScriptedCampaignClient(plan)
            self.last_usage = None
            if prices is not None:
                self.prices_eur_per_mtok = prices

        def complete(self, system, conversation, tools):
            self.last_usage = {"input_tokens": 500, "output_tokens": 20}
            return self.inner.complete(system, conversation, tools)

    asked = []

    def load(provider):
        asked.append(provider)
        return Local((0.0, 0.0) if provider == "local" else None)

    monkeypatch.setattr(providers, "load_client", load)
    ledger = tmp_path / "spend.json"
    command = ["record-campaign", "--plan", str(plan_path), "--spend-ledger"]
    out = tmp_path / "local.json"
    assert main([*command, str(ledger), "--out", str(out), "--provider", "local"]) == 0
    entry = json.loads(ledger.read_text())["recordings"][0]
    assert entry["model"] == "a-local-model" and entry["calls"] > 0
    assert entry["cost_eur"] == 0.0 and entry["input_tokens"] > 0
    assert entry["prices_eur_per_mtok"] == {"input": 0.0, "output": 0.0}
    # A client without prices of its own needs the recorder's.
    other = ["--out", str(tmp_path / "other.json"), "--provider", "openai"]
    assert main([*command, str(ledger), *other]) == 2
    assert asked == ["local", "openai"]
