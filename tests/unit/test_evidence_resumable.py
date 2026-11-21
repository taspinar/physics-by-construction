"""A research pipeline that stops, resumes only from a valid state, and
branches with a recorded lineage (F153, lesson RR4)."""

import ast
import json
from pathlib import Path

import pytest

from pbc.data import flume_stages
from pbc.evidence import COMPLETED, FAILED, ContractError, claim_status
from pbc.evidence.records import RunRecord, digest_file
from pbc.evidence.resumable import Research, Stage


def _record(code: str = "code-1") -> RunRecord:
    return RunRecord(
        task="t",
        hypothesis="h",
        assumptions=(),
        protocol_version="1",
        split={},
        seeds=(),
        budgets={},
        code=code,
        configuration="c",
        environment={},
    )


def _source(previous, configuration):
    return {"x": configuration["x"]}


def _scale(previous, configuration):
    if configuration["factor"] == 0:
        raise ValueError("a factor of zero loses the signal")
    return {"y": previous["x"] * configuration["factor"]}


def _add(previous, configuration):
    return {"z": previous["y"] + 1}


STAGES = (
    Stage("source", ("x",), _source),
    Stage("scale", ("factor",), _scale),
    Stage("add", (), _add),
)


def _research(root: Path, code: str = "code-1") -> Research:
    research = Research(STAGES, _record(code), root)
    research.start("main", {"x": 2, "factor": 3})
    return research


def test_a_run_records_one_attempt_and_one_state_per_stage(tmp_path):
    research = _research(tmp_path)
    research.run("main")

    assert [a.id for a in research.ledger.attempts] == [
        "main/source",
        "main/scale",
        "main/add",
    ]
    state = research.state("main/scale")
    assert state.configuration == {"factor": 3}
    assert state.code == "code-1"
    assert state.input == digest_file(tmp_path / "main" / "source.json")
    assert research.state("main/add").output == {"z": 7}


def test_a_stopped_run_resumes_to_the_states_of_an_uninterrupted_one(tmp_path):
    whole = _research(tmp_path / "whole")
    whole.run("main")
    stopped = _research(tmp_path / "stopped")
    stopped.run("main", stop_after="scale")
    assert stopped.ledger.attempt("main/add") is None

    stopped.resume("main")

    for stage in ("source", "scale", "add"):
        assert digest_file(tmp_path / "stopped" / "main" / f"{stage}.json") == (
            digest_file(tmp_path / "whole" / "main" / f"{stage}.json")
        )


def _refusal(research: Research, name: str = "main") -> str:
    with pytest.raises(ContractError) as refused:
        research.resume(name)
    return str(refused.value)


def test_a_resume_from_an_edited_state_is_refused(tmp_path):
    research = _research(tmp_path)
    research.run("main", stop_after="scale")
    path = tmp_path / "main" / "scale.json"
    state = json.loads(path.read_text())
    state["output"]["y"] = 7
    path.write_text(json.dumps(state))

    assert "the state of main/scale changed after it was recorded" in (
        _refusal(research)
    )
    assert research.ledger.attempt("main/add") is None


def test_a_resume_from_a_missing_state_is_refused(tmp_path):
    research = _research(tmp_path)
    research.run("main", stop_after="scale")
    (tmp_path / "main" / "source.json").unlink()

    assert "the state of main/source is missing" in _refusal(research)


def test_a_resume_with_other_code_is_refused(tmp_path):
    research = _research(tmp_path)
    research.run("main", stop_after="scale")
    later = Research(STAGES, _record("code-2"), tmp_path)
    later.branches = research.branches
    later.ledger = research.ledger

    assert "main/source was written by other code" in _refusal(later)


def test_a_resume_with_a_changed_choice_is_refused(tmp_path):
    research = _research(tmp_path)
    research.run("main", stop_after="scale")
    main = research.branches["main"]
    research.branches["main"] = type(main)("main", {"x": 2, "factor": 4})

    assert "a changed choice is a new branch" in _refusal(research)


def test_a_resume_after_a_failed_stage_is_refused_and_the_failure_is_kept(
    tmp_path,
):
    research = _research(tmp_path)
    research.run("main", stop_after="source")
    research.fork("main", "zero", "source", {"factor": 0})
    research.run("zero")

    failed = research.ledger.attempt("zero/scale")
    assert failed.status == FAILED
    assert failed.diagnostics == ("a factor of zero loses the signal",)
    assert "zero/scale failed" in _refusal(research, "zero")
    assert research.ledger.attempt("zero/add") is None


def test_a_resume_with_changed_data_is_refused(tmp_path):
    data = tmp_path / "data.txt"
    data.write_text("1")
    stages = (Stage("source", ("x",), _source, lambda c: {"record": data}),)
    research = Research((*stages, *STAGES[1:]), _record(), tmp_path / "root")
    research.start("main", {"x": 2, "factor": 3})
    research.run("main", stop_after="source")
    data.write_text("2")

    assert "the data record of main/source changed" in _refusal(research)


def test_a_fork_shares_the_stages_before_it_and_records_its_lineage(tmp_path):
    research = _research(tmp_path)
    research.run("main")
    research.fork("main", "double", "source", {"factor": 2})
    research.run("double")

    assert research.lineage("double/add") == (
        "double/add",
        "double/scale",
        "main/source",
    )
    assert research.ledger.attempt("double/source") is None
    assert research.state("double/add").output == {"z": 5}


def test_a_fork_from_an_edited_shared_state_is_refused(tmp_path):
    research = _research(tmp_path)
    research.run("main", stop_after="source")
    path = tmp_path / "main" / "source.json"
    state = json.loads(path.read_text())
    state["output"]["x"] = 5
    path.write_text(json.dumps(state))
    research.fork("main", "double", "source", {"factor": 2})

    with pytest.raises(ContractError, match="source changed after it was recorded"):
        research.run("double")
    assert research.ledger.attempt("double/scale") is None


def test_a_fork_under_other_code_is_refused(tmp_path):
    research = _research(tmp_path)
    research.run("main", stop_after="source")
    later = Research(STAGES, _record("code-2"), tmp_path)
    later.branches = research.branches
    later.ledger = research.ledger
    later.fork("main", "double", "source", {"factor": 2})

    with pytest.raises(ContractError, match="main/source was written by other code"):
        later.run("double")
    assert later.ledger.attempt("double/scale") is None


def test_a_fork_records_the_digest_of_the_state_it_read(tmp_path):
    research = _research(tmp_path)
    research.run("main", stop_after="source")
    research.fork("main", "double", "source", {"factor": 2})
    research.run("double")

    assert research.state("double/scale").input == digest_file(
        tmp_path / "main" / "source.json"
    )


def test_a_fork_after_a_stage_that_read_the_changed_key_is_refused(tmp_path):
    research = _research(tmp_path)
    research.run("main")

    with pytest.raises(ContractError, match="scale read factor"):
        research.fork("main", "double", "scale", {"factor": 2})
    assert "double" not in research.branches


def test_a_branch_that_has_run_is_resumed_not_run_again(tmp_path):
    research = _research(tmp_path)
    research.run("main", stop_after="source")

    with pytest.raises(ContractError, match="resume it"):
        research.run("main")


def _imported_modules(name: str, src: Path) -> set[str]:
    """The project modules ``name`` imports by name, directly or through
    each other, as paths relative to ``src``."""
    found, todo = set(), [name]
    while todo:
        module = todo.pop()
        parts = module.replace(".", "/")
        path = next(
            (
                p
                for p in (src / f"{parts}.py", src / parts / "__init__.py")
                if p.is_file()
            ),
            None,
        )
        if path is None or path.relative_to(src).as_posix() in found:
            continue
        found.add(path.relative_to(src).as_posix())
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            if isinstance(node, ast.ImportFrom) and (node.module or "").startswith(
                "pbc"
            ):
                todo.append(node.module)
                todo.extend(f"{node.module}.{a.name}" for a in node.names)
            elif isinstance(node, ast.Import):
                todo.extend(a.name for a in node.names if a.name.startswith("pbc"))
    return found


def test_the_code_identity_covers_every_module_the_stages_import():
    src = Path(flume_stages.__file__).parents[2]

    assert set(flume_stages.SOURCES) == _imported_modules("pbc.data.flume_stages", src)


# The flume investigation of the lesson.


@pytest.fixture(scope="module")
def flume(tmp_path_factory):
    root = tmp_path_factory.mktemp("flume")
    research = flume_stages.investigation(root)
    research.run("main", stop_after="window")
    research.resume("main")
    flume_stages.branch_out(research)
    flume_stages.evaluate(research)
    return research


def test_the_resumed_main_branch_reproduces_the_committed_report(flume):
    expected = flume_stages.EXPECTATION.read_text().splitlines()
    lines = flume.state("main/report").output["lines"]

    assert lines == expected[: flume_stages.REPORT_LINES]
    claim = next(c for c in flume.ledger.claims if c.id == "reproduces-the-report")
    assert claim_status(flume.ledger, claim) == COMPLETED


def test_every_alternative_branch_descends_from_the_main_record(flume):
    for name in flume_stages.ALTERNATIVES:
        last = [a for a in flume.ledger.attempts if a.candidate == name][-1]
        assert flume.lineage(last.id)[-1] == "main/load"


def test_the_window_beyond_the_record_fails_and_stays_in_the_ledger(flume):
    failed = flume.ledger.attempt("end-40/window")

    assert failed.status == FAILED
    assert "not inside the record, 0 to 30 s" in failed.diagnostics[0]
    assert flume.ledger.attempt("end-40/estimate") is None


def test_the_negative_claim_is_kept_with_the_status_failed(flume):
    claim = next(c for c in flume.ledger.claims if c.id == "window-does-not-matter")

    assert set(claim.runs) == {"end-10/estimate", "end-12/estimate"}
    assert claim_status(flume.ledger, claim) == FAILED
    assert all(
        abs(s) > flume_stages.WITHIN for s in flume_stages.shifts(flume).values()
    )


def test_the_flume_states_name_the_record_by_its_digest(flume):
    state = flume.state("main/load")

    assert state.data == {
        "record": digest_file(
            flume_stages.flume_analysis.DATA_DIR / flume_stages.MAIN["data"]
        )
    }
