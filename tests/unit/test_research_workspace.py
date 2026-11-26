"""The Scientific Research Workspace (F155 part 1, Issue #619): the
reproduction track's analysis, its typed discrepancies, the registered plan,
the source evidence, the question archive, the follow-up log, the project
end to end, the static view, and the agent reviewer's replay."""

import html
import json
import re
import shutil
from dataclasses import replace

import numpy as np
import pytest

from pbc.agents.replay import ReplayMismatch
from pbc.data import REPO_ROOT, SAMPLES_DIR
from pbc.data.reference.cobe_firas import read_spectrum
from pbc.evidence.records import EVIDENCE_STATUSES
from pbc.products.research_workspace import (
    agent,
    discrepancy,
    firas,
    graph,
    project,
    questions,
    registration,
    reproduction,
    review,
    sources,
)
from pbc.products.research_workspace import log as worklog
from pbc.products.research_workspace import report as rep
from pbc.products.research_workspace.__main__ import main

EXAMPLE = REPO_ROOT / "products/research-workspace/examples/firas"


@pytest.fixture(scope="module")
def spectrum():
    return read_spectrum(SAMPLES_DIR / "cobe-firas-monopole")


@pytest.fixture(scope="module")
def built(tmp_path_factory):
    directory = tmp_path_factory.mktemp("project") / "firas"
    project.run(EXAMPLE, directory)
    return directory


def _copy(built, tmp_path):
    target = tmp_path / "copy"
    shutil.copytree(built, target)
    return target


# -- the analysis -----------------------------------------------------------


def test_the_distortion_shapes_match_derivatives_of_the_distorted_spectra(spectrum):
    closed = firas.shapes(spectrum, 2.725)
    numerical = firas.occupation_shapes(spectrum, 2.725)
    for name in (firas.COMPTON, firas.CHEMICAL):
        scale = np.abs(closed[name]).max()
        assert np.max(np.abs(closed[name] - numerical[name])) / scale < 1e-4, name
    # The y shape changes sign near x = 3.83 (its zero is a known number).
    x = firas.x_of(spectrum.wavenumber, 2.725)
    sign = np.sign(closed[firas.COMPTON])
    crossing = x[np.nonzero(np.diff(sign))[0][0]]
    assert 3.5 < crossing < 3.9


def test_the_fit_recovers_an_injected_distortion_and_refuses_y_with_mu(spectrum):
    injected = {firas.TEMPERATURE: 30e-6, firas.GALAXY: 0.4, firas.COMPTON: 25e-6}
    data = firas.synthetic(spectrum, injected, np.random.default_rng(7))
    result = firas.fit(data, (firas.TEMPERATURE, firas.GALAXY, firas.COMPTON))
    for name, value in injected.items():
        assert abs(result.parameters[name] - value) < 3 * result.errors[name], name
    with pytest.raises(ValueError, match="not fitted together"):
        firas.fit(spectrum, (firas.TEMPERATURE, firas.COMPTON, firas.CHEMICAL))


def test_a_free_dt_absorbs_a_change_of_the_reference(spectrum):
    # Branch b4's point: against 2.728 K the fitted temperature comes back to
    # the file's reference to first order; dT is about -3 mK.
    own = firas.fit(spectrum, (firas.TEMPERATURE, firas.GALAXY))
    other = firas.fit(firas.against(spectrum, 2.728), (firas.TEMPERATURE, firas.GALAXY))
    assert other.parameters[firas.TEMPERATURE] == pytest.approx(-0.003, abs=1e-5)
    assert abs(other.temperature - own.temperature) < 2 * own.errors[firas.TEMPERATURE]


def test_the_positive_control_passes_and_fails_on_understated_uncertainties(
    spectrum,
):
    trial = firas.control(spectrum)
    assert trial.passed
    assert min(trial.recovered_t, trial.recovered_y, trial.zero_covered) >= 90
    # Noise three times the stated 1-sigma: the fit's errors no longer cover
    # it, and the control says so.
    assert not firas.control(spectrum, noise_scale=3.0).passed


def test_the_declared_branch_criterion(spectrum):
    fits = {
        name: firas.run_branch(spectrum, configuration)
        for name, configuration in firas.BRANCHES.items()
    }
    decisions = {d.branch: d for d in firas.decide(fits)}
    assert set(decisions) == {"b1", "b2", "b3", "b4", "b5"}
    assert all(decisions[b].decision == "stop" for b in ("b1", "b2", "b3"))
    assert decisions["b4"].decision == decisions["b5"].decision == "reported"
    assert all(d.reason and d.revisit for d in decisions.values())
    # A parameter that lowers chi-square by more than 4 continues.
    strong = firas.synthetic(spectrum, {firas.COMPTON: 60e-6}, np.random.default_rng(3))
    fits = {
        name: firas.run_branch(strong, firas.BRANCHES[name]) for name in firas.BRANCHES
    }
    assert {d.branch: d.decision for d in firas.decide(fits)}["b2"] == "continue"


# -- discrepancies, registration, sources, questions ------------------------


def test_a_type_needs_its_supporting_check():
    base = discrepancy.Discrepancy("q", "1", "key", "2", discrepancy.NOT_REPRODUCED)
    assert discrepancy.problems(base)  # no type
    assert not discrepancy.problems(replace(base, type=discrepancy.UNEXPLAINED))
    method = replace(base, type=discrepancy.METHOD)
    assert any("needs a recorded check" in p for p in discrepancy.problems(method))
    weak = discrepancy.Check("c", "b4/fit", {}, False)
    assert any(
        "does not support" in p
        for p in discrepancy.problems(replace(method, check=weak))
    )
    strong = replace(weak, supports=True)
    assert any(
        "missing piece" in p
        for p in discrepancy.problems(replace(method, check=strong))
    )
    assert not discrepancy.problems(
        replace(method, check=strong, missing="the calibration")
    )
    reproduced = replace(base, verdict=discrepancy.REPRODUCED, type=discrepancy.INPUT)
    assert any("carries no type" in p for p in discrepancy.problems(reproduced))
    with pytest.raises(discrepancy.DiscrepancyRefused):
        discrepancy.validate([method])


def test_the_registration_must_discriminate_and_has_a_freeze():
    plan = registration.load(EXAMPLE / "registration.toml")
    assert registration.problems(plan) == []
    both = registration.Explanation("M", "another", ("reproduced",))
    found = registration.problems(
        replace(plan, explanations=(*plan.explanations, both))
    )
    assert any("predicted by R, M" in p for p in found)
    one = replace(plan, explanations=plan.explanations[:1])
    assert "fewer than two explanations" in registration.problems(one)
    assert "no withheld (confirmatory) part" in registration.problems(
        replace(plan, withheld=" ")
    )
    assert "no stopping conditions" in registration.problems(replace(plan, stopping=()))
    draft = registration.Freeze(registration.digest(plan), None, "2026-11-25T12:00:00")
    with pytest.raises(registration.RegistrationRefused, match="draft"):
        registration.admit("2026-12-01T10:00:00", draft)
    frozen = replace(draft, commit="abc123")
    with pytest.raises(registration.RegistrationRefused, match="before the freeze"):
        registration.admit("2026-11-24T10:00:00", frozen)
    registration.admit("2026-12-01T10:00:00", frozen)
    assert registration.digest(plan) != registration.digest(replace(plan, rule="x"))


def test_every_published_value_rests_on_checked_words():
    evidence = sources.load(EXAMPLE / "sources.toml")
    register = sources.register_entries()
    assert sources.problems(evidence, register) == []
    changed = [replace(evidence[1], quote="2.725 +- 0.001 K")]
    assert "not in the checked statement" in sources.problems(changed, register)[0]
    unknown = [replace(evidence[0], register="no-such-entry")]
    assert "no register entry" in sources.problems(unknown, register)[0]


def test_the_selection_reads_no_rating_and_needs_a_passing_assessment():
    budget, asked = questions.load(EXAMPLE / "questions.toml")
    cards = questions.cards_of(
        {n for q in asked for n in q.datasets}, REPO_ROOT / "data/registry"
    )
    assessments = {q.key: questions.assess(q, cards, budget) for q in asked}
    assert questions.selection_problems(asked, assessments) == []
    assert assessments["spectrum-fit"].passed
    assert not assessments["dipole"].feasible
    assert not assessments["energy-release"].falsifiable
    assert not assessments["firas-wmap"].within_budget
    # A self-rating does not change an assessment.
    rated = replace(asked[0], self_ratings={"feasibility": 0})
    assert questions.assess(rated, cards, budget) == assessments[asked[0].key]
    wrong = [replace(asked[3], decision="selected")]
    assert "fails its assessment" in questions.selection_problems(wrong, assessments)[0]
    archive = questions.archive(asked)
    assert [e.decision for e in archive.entries].count("rejected") == 3


# -- the log -----------------------------------------------------------------


def test_a_revision_never_resolves_a_finding_that_asks_for_evidence():
    log = worklog.Log()
    log.find("w", "c", worklog.SCRIPTED, "words", worklog.WORDING, "t0-not-claimed")
    log.find(
        "e", "c", worklog.SCRIPTED, "a fit", worklog.EVIDENCE, "covariance-weighting"
    )
    log.revise(["w", "e"], "the words are changed")
    assert worklog.state(log, "w") == worklog.REWORDED
    assert worklog.state(log, "e") == worklog.OPEN
    log.evidence("e", "covariance-weighting", True, "d")
    assert worklog.state(log, "e") == worklog.RESOLVED
    assert worklog.verify(log.entries) == []
    log.entries[1] = replace(
        log.entries[1], content={**log.entries[1].content, "text": "x"}
    )
    assert any("digest does not match" in p for p in worklog.verify(log.entries))


def test_an_agent_finding_is_accepted_only_through_its_recomputed_check():
    log = worklog.Log()
    entry = log.find("a", "c", "some model", "text", worklog.EVIDENCE, "control")
    assert entry.content["state"] == worklog.PROPOSED
    with pytest.raises(worklog.LogRefused, match="recomputed check"):
        log.accept("a", True, "the learner")
    with pytest.raises(worklog.LogRefused):
        log.accept("a", None, "the learner")
    log.accept("a", False, "the learner")
    with pytest.raises(worklog.LogRefused, match="needs its reason"):
        log.decide("b1", "stop", " ", "", "the learner")


# -- the project end to end --------------------------------------------------


def test_the_reproduction_track_runs_end_to_end_and_verifies(built):
    assert project.verify(built) == []
    data = project.summary(built)
    text = (built / "report.md").read_text()
    lines = [line for line in text.splitlines() if line.startswith(">")]
    assert lines[0] == f"> {rep.BANNER}"
    assert lines[1].startswith("> Claims: 10 (")
    # Every claim has a run or a source link and an evidence status.
    for claim in data["research"].ledger.claims:
        assert claim.runs or claim.sources
        assert data["status"][claim.id] in EVIDENCE_STATUSES
    run_record = json.loads((built / "run.json").read_text())
    assert set(run_record["modes"]) == {"load", "fit", "control", "agent"}
    assert run_record["registration"]["frozen"] is False


def test_the_rows_say_what_the_derived_data_can_and_cannot_reproduce(built):
    rows = project.summary(built)["rows"]
    by = {r.quantity.split(",")[0].split(":")[0]: r for r in rows}
    t0 = by["T0"]
    assert t0.verdict == discrepancy.NOT_REPRODUCED and t0.type == discrepancy.METHOD
    assert t0.check.supports and abs(t0.check.values["shift"]) < 1e-5
    assert by["the uncertainty of T0"].type == discrepancy.UNCERTAINTY
    assert by["the weighted rms deviation from a blackbody"].verdict == "reproduced"
    assert "by construction" in by["the weighted rms deviation from a blackbody"].note
    for head in ("|y| (95 %)", "|mu| (95 %)"):
        assert "statistical only" in by[head].regenerated
        assert "not a better limit" in by[head].note
    assert all(not discrepancy.problems(r) for r in rows)


def test_the_post_hoc_rule_of_the_figure_never_reads_as_confirmatory(built):
    # The owner's review of 2026-11-25: the 1-sigma rule of the residual
    # figure was set after a scratch fit had been seen.
    plan = registration.load(EXAMPLE / "registration.toml")
    post_hoc = {c.quantity for c in plan.criteria if c.post_hoc}
    assert post_hoc == {
        "the residual figure",
        "sigma_y, the statistical uncertainty of y",
        "sigma_mu, the statistical uncertainty of mu",
    }
    data = project.summary(built)
    rows = {r.quantity: r for r in data["rows"]}
    assert rows["the residual figure"].post_hoc
    assert not any(r.post_hoc for q, r in rows.items() if q not in post_hoc)
    label = discrepancy.POST_HOC_LABEL
    claims = {c.id: c for c in data["research"].ledger.claims}
    number = list(rows).index("the residual figure") + 1
    assert label in claims[f"row-{number}"].text
    assert sum(label in c.text for c in claims.values()) == len(post_hoc)
    report = (built / "report.md").read_text()
    figure_line = next(
        x for x in report.splitlines() if x.startswith("| the residual figure")
    )
    assert f"| reproduced ({label}) |" in figure_line
    assert f"- Row {number}: " in report and "Post-hoc rule: " in report
    page = (built / "view.html").read_text()
    assert f'<span class="post-hoc">{html.escape(label)}</span>' in page
    assert page.count('class="post-hoc"') == len(post_hoc)
    # A registration without the reason leaves the row unmarked.
    plain = replace(
        plan, criteria=tuple(replace(c, post_hoc="") for c in plan.criteria)
    )
    assert not any(r.post_hoc for r in reproduction.mark_post_hoc(data["rows"], plain))
    assert (
        discrepancy.from_dict(discrepancy.as_dict(rows["the residual figure"]))
        == rows["the residual figure"]
    )


def test_the_statistical_sigmas_of_y_and_mu_are_compared_with_the_paper(built):
    # Review 01 of #619, M1: the bound rule alone showed y and mu reproduced
    # while their statistical uncertainties differ from the paper's.
    evidence = sources.by_id(sources.load(EXAMPLE / "sources.toml"))
    rows = {r.quantity: r for r in project.summary(built)["rows"]}
    for name, key, ratio in (("y", "y_value", 0.60), ("mu", "mu_value", 0.86)):
        row = rows[f"sigma_{name}, the statistical uncertainty of {name}"]
        published = float(evidence[key].uncertainty)
        assert row.verdict == discrepancy.NOT_REPRODUCED
        assert row.type == discrepancy.UNCERTAINTY and row.check.supports
        assert row.check.values["published_sigma"] == published
        assert abs(row.check.values["ratio"] - ratio) < 0.01
        assert reproduction.COVARIANCE_FINDING in row.note
        assert "section 3.3" in row.terms[0]
        assert row.post_hoc and not discrepancy.problems(row)
        # The registered bound rule keeps its verdict.
        bound = rows[f"|{name}| (95 %)"]
        assert bound.verdict == discrepancy.REPRODUCED
        assert f"sigma_{name}" in bound.note
    assert "review-covariance-weighting" in worklog.load(built / "log.json").findings()


def test_a_statistical_sigma_that_rounds_to_the_published_one_reproduces(spectrum):
    fit = firas.fit(spectrum, (firas.TEMPERATURE, firas.GALAXY, firas.COMPTON))
    error = fit.errors[firas.COMPTON]
    near = sources.Source(
        "y_value", "q", 0.0, error * 1.05, "1", "1 sigma", "r", "p", "w"
    )
    row = reproduction.sigma_row(firas.COMPTON, "b2", fit, near, 1e-6, "1e-6")
    assert row.verdict == discrepancy.REPRODUCED and not discrepancy.problems(row)
    far = replace(near, value=1.0, uncertainty=error * 2)
    row = reproduction.sigma_row(firas.COMPTON, "b2", fit, far, 1e-6, "1e-6")
    assert row.verdict == discrepancy.NOT_REPRODUCED
    assert row.type == discrepancy.UNEXPLAINED


def test_a_failed_control_makes_every_row_not_evaluated(spectrum):
    evidence = sources.by_id(sources.load(EXAMPLE / "sources.toml"))
    failed = firas.Control(100, {}, 50, 50, 50, 90)
    rows = reproduction.rows(spectrum, {}, failed, evidence)
    assert {r.verdict for r in rows} == {discrepancy.NOT_EVALUATED}


def test_every_number_of_the_report_resolves_to_its_record(built):
    data = project.summary(built)
    _, written = project.render_markdown(data)
    assert written and rep.number_problems(written, data["records"]) == []
    altered = json.loads(json.dumps(data["records"]))
    altered["b1/fit"]["chi2"] += 1.0
    assert rep.number_problems(written, altered)


def test_a_changed_state_or_input_is_found_and_the_failed_attempt_kept(built, tmp_path):
    copy = _copy(built, tmp_path)
    state = copy / "states" / "b1" / "fit.json"
    state.write_text(state.read_text().replace('"chi2": 45', '"chi2": 46'))
    (copy / "inputs" / "sources.toml").write_text("changed\n")
    found = project.verify(copy)
    assert any("the input sources.toml changed" in p for p in found)
    assert any("b1/fit changed after it was recorded" in p for p in found)
    research = project.open_research(built)
    failed = research.ledger.attempt(f"{graph.FAILED_BRANCH}/fit")
    assert failed.status == "failed"
    assert "not fitted together" in failed.diagnostics[0]


def test_a_changed_rule_of_the_outcome_code_is_named_by_verify(
    built, tmp_path, monkeypatch
):
    # Issue #623: the code identity covered only the stages, so a changed
    # rule constant left a project verifying with rows of the old rule.
    run_record = json.loads((built / "run.json").read_text())
    assert run_record["outcome_code"] == graph.outcome_code_digest()
    package = tmp_path / "package"
    shutil.copytree(graph.PACKAGE, package, ignore=shutil.ignore_patterns("*.pyc"))
    rules = package / "reproduction.py"
    text = rules.read_text()
    assert "BOUND_REPRODUCED = 1.5\n" in text
    rules.write_text(
        text.replace("BOUND_REPRODUCED = 1.5\n", "BOUND_REPRODUCED = 1.6\n")
    )
    monkeypatch.setattr(graph, "PACKAGE", package)
    found = project.verify(built)
    assert len(found) == 1 and found[0].startswith("the outcome code changed")
    # Only the changed file is named (Issue #628): a message that listed
    # every module would pass a check for the name alone.
    assert "changed: reproduction.py)" in found[0]
    assert "review.py" not in found[0]
    # The stage code is unchanged, so no state reads as written by other code.
    assert not any("other code" in p for p in found)


def test_a_run_without_the_outcome_digest_does_not_verify(built, tmp_path):
    copy = _copy(built, tmp_path)
    run_record = json.loads((copy / "run.json").read_text())
    del run_record["outcome_code"]
    (copy / "run.json").write_text(json.dumps(run_record))
    assert any("no digest of the outcome code" in p for p in project.verify(copy))


def test_every_module_of_the_workspace_is_classified_for_the_outcome_digest():
    # A new module must be put in the outcome code or named as recording
    # nothing; it is never left out of the digest by default.
    modules = {p.name for p in graph.PACKAGE.glob("*.py")}
    stages = {"firas.py", "graph.py"}
    classified = set(graph.OUTCOME_MODULES) | set(graph.NOT_OUTCOME) | stages
    assert modules == classified
    assert not set(graph.OUTCOME_MODULES) & set(graph.NOT_OUTCOME)


def test_the_uncertainty_type_of_a_bound_rests_on_a_quoted_term(spectrum):
    # Issue #624: the branch between 1.5 and 3 times the published bound
    # asserted its check and named an unquoted Galactic-model term.
    evidence = sources.by_id(sources.load(EXAMPLE / "sources.toml"))
    fit = firas.fit(spectrum, (firas.TEMPERATURE, firas.GALAXY, firas.COMPTON))
    fit = replace(fit, parameters={**fit.parameters, firas.COMPTON: 0.0})
    published = replace(evidence["y"], value=fit.bound(firas.COMPTON) / 2.0)
    systematic = evidence["y_systematic"]
    assert sources.problems([systematic], sources.register_entries()) == []
    row = reproduction.bound_row(
        firas.COMPTON, "b2", fit, published, 1e-6, "1e-6", systematic
    )
    assert row.verdict == discrepancy.NOT_REPRODUCED
    assert row.type == discrepancy.UNCERTAINTY and not discrepancy.problems(row)
    assert row.check.supports == reproduction.band_supports(row.check.values)
    assert row.check.values["systematic"] == 4e-6
    assert systematic.quote in row.terms[0] and "Galactic" not in row.terms[0]
    # The recorded numbers decide: outside the band, or without a systematic
    # term, they do not support the type.
    for changed in ({"bound": row.check.values["published"]}, {"systematic": 0.0}):
        assert not reproduction.band_supports({**row.check.values, **changed})
    # Without a quoted term the row is unexplained, never typed by assertion.
    bare = reproduction.bound_row(firas.COMPTON, "b2", fit, published, 1e-6, "1e-6")
    assert bare.type == discrepancy.UNEXPLAINED and bare.check is None
    assert not discrepancy.problems(bare)
    mu = evidence["mu_systematic"]
    assert sources.problems([mu], sources.register_entries()) == []
    assert mu.value == 1e-5


def test_a_project_is_never_overwritten(built):
    with pytest.raises(project.ProjectRefused, match="not empty"):
        project.run(EXAMPLE, built)
    assert main(["run", "--example", str(EXAMPLE), "--project", str(built)]) == 1


def test_the_view_is_static_and_shows_the_statuses_of_the_records(built):
    data = project.summary(built)
    page = (built / "view.html").read_text()
    assert "<script" not in page.lower() and "http://" not in page
    assert html.escape(rep.BANNER, quote=True) in page
    for claim in data["research"].ledger.claims:
        status = data["status"][claim.id]
        css = status.replace(" ", "-")
        cell = (
            f'<td role="cell" data-label="Claim">{claim.id}</td>'
            f'<td role="cell" data-label="Status"><span class="status status-{css}">'
            f"{status}</span>"
        )
        assert cell in page, claim.id
    assert 'alt="Two panels' in page
    # At phone width a table scrolls in its own box: the box takes the focus
    # and is named by the caption above it, which wraps at the screen.
    boxes = re.findall(
        r'<p class="caption" id="(t-[0-9a-f]+)">[^<]+</p><div class="scroll"'
        r' role="region" tabindex="0" aria-labelledby="\1"><table'
        r' role="table" aria-labelledby="\1">',
        page,
    )
    assert len(boxes) == page.count("<table") and len(set(boxes)) == len(boxes)


def test_the_commands_record_decisions_in_the_chains(built, tmp_path):
    copy = _copy(built, tmp_path)
    args = ["--project", str(copy)]
    assert (
        main(
            [
                "decide",
                *args,
                "--subject",
                "b2",
                "--decision",
                "stop",
                "--reason",
                "as the criterion",
                "--revisit",
                "a covariance fit",
            ]
        )
        == 0
    )
    assert (
        main(
            [
                "select",
                *args,
                "--question",
                "dipole",
                "--decision",
                "selected",
                "--reason",
                "r",
                "--revisit",
                "v",
            ]
        )
        == 1
    )
    assert (
        main(
            [
                "select",
                *args,
                "--question",
                "dipole",
                "--decision",
                "rejected",
                "--reason",
                "not now",
                "--revisit",
                "option C",
            ]
        )
        == 0
    )
    assert main(["verify", *args]) == 0


# -- the agent reviewer ------------------------------------------------------


def test_the_reviewer_fixture_replays_and_its_findings_need_their_checks(built):
    context = project.context(built)
    recording = agent.load_recording(agent.FIXTURE)
    assert recording.placeholder and recording.model.startswith("placeholder")
    transcript = agent.replay_review(context)
    assert agent.proposed(transcript) == ["covariance-weighting"]
    log = worklog.Log()
    assert agent.enter(transcript, context, log, "the check") == [
        "agent-covariance-weighting"
    ]
    # A finding the agent proposes for a check that passes stays proposed.
    step = transcript.steps[-1]
    claimed = replace(step.message, text="FINDINGS: control, no-such-check")
    fake = replace(
        transcript, steps=(*transcript.steps[:-1], replace(step, message=claimed))
    )
    log = worklog.Log()
    assert agent.enter(fake, context, log, "the check") == []
    assert log.findings()["agent-control"].content["state"] == worklog.PROPOSED
    assert "agent-no-such-check" not in log.findings()


def test_a_replayed_review_or_a_repeated_acceptance_records_one_acceptance(
    built, tmp_path, capsys
):
    # Review 01 of #619, MIN2: each replay of the review, and each repeated
    # accept-finding, appended another identical acceptance.
    copy = _copy(built, tmp_path)
    args = ["--project", str(copy)]

    def acceptances():
        log = worklog.load(copy / "log.json")
        return [
            e
            for e in log.of(worklog.DECISION)
            if e.content["decision"] == worklog.ACCEPTED
        ]

    assert main(["review", *args]) == 0
    assert main(["review", *args]) == 0
    assert "accepted none" in capsys.readouterr().out.splitlines()[-1]
    assert [e.content["subject"] for e in acceptances()] == [
        "agent-covariance-weighting"
    ]
    finding = ["--finding", "agent-covariance-weighting"]
    assert main(["accept-finding", *args, *finding]) == 1
    assert "already accepted" in capsys.readouterr().err
    assert len(acceptances()) == 1
    assert main(["verify", *args]) == 0


def test_an_edited_fixture_no_longer_replays(built, tmp_path):
    data = json.loads(agent.FIXTURE.read_text())
    data["steps"][0]["results"][0]["content"]["value"] = 123.0
    edited = tmp_path / "edited.json"
    edited.write_text(json.dumps(data))
    with pytest.raises(ReplayMismatch):
        agent.replay_review(project.context(built), edited)


def test_the_scripted_review_checks_are_recomputed(built):
    context = project.context(built)
    results = {r.name: r for r in (review.run_check(n, context) for n in review.NAMES)}
    assert results["independent-refit"].passed
    assert results["covariance-weighting"].passed is False
    hidden = [replace(r, note="") for r in context.rows]
    assert (
        review.run_check("by-construction-stated", replace(context, rows=hidden)).passed
        is False
    )
    claimed = [
        replace(r, verdict="reproduced", type=None, check=None)
        if r.quantity.startswith("T0")
        else r
        for r in context.rows
    ]
    assert (
        review.run_check("t0-not-claimed", replace(context, rows=claimed)).passed
        is False
    )


# -- the boundary ------------------------------------------------------------

FORBIDDEN = {
    "socket", "ssl", "http", "urllib", "requests", "httpx", "aiohttp",
    "subprocess", "multiprocessing", "ctypes", "pickle", "openai", "anthropic",
    "webbrowser", "pbc.agents.clients", "pbc.instruments",
}  # fmt: skip
LAZY = {"pbc.agents.providers", "pbc.products.physics_lab.agent_campaign"}


def _imports(tree) -> list[tuple[str, bool]]:
    """Every imported module, and whether the import is at module level."""
    import ast

    found = []
    top = {id(node) for node in tree.body}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            found += [(alias.name, id(node) in top) for alias in node.names]
        elif isinstance(node, ast.ImportFrom) and node.module:
            found.append((node.module, id(node) in top))
    return found


def test_the_workspace_opens_no_socket_device_or_provider_at_import():
    # The view is a static file: no server, no socket, no device; a provider
    # client and the physics lab's metered client only lazily, in ``record``.
    import ast

    package = REPO_ROOT / "src/pbc/products/research_workspace"
    for path in sorted(package.glob("*.py")):
        for module, top in _imports(ast.parse(path.read_text())):
            root = module.split(".")[0]
            assert root not in FORBIDDEN and module not in FORBIDDEN, (path, module)
            assert not any(module.startswith(f + ".") for f in FORBIDDEN), (
                path,
                module,
            )
            if module in LAZY:
                assert path.name == "__main__.py" and not top, (path, module)


def test_the_control_figure_shows_the_seeds_the_control_counts(spectrum):
    values = firas.pulls(spectrum)
    trial = firas.control(spectrum)
    assert int(np.sum(np.abs(values[firas.TEMPERATURE]) <= 2)) == trial.recovered_t
    assert int(np.sum(np.abs(values[firas.COMPTON]) <= 2)) == trial.recovered_y
