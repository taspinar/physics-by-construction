"""The experiment and the page of "A proof an agent proposed" (lean 06,
Issue #609): the numbers against the Lean identity, and what the page states
about the compiled proof, the transcript, and the profile for Lean."""

import re
from pathlib import Path

import numpy as np
import pytest
from support.experiments import assert_the_page_and_the_results_agree, run_entry_point

from pbc.mechanics.experiments import agent_proposed_proof as experiment

MODULE = "pbc.mechanics.experiments.agent_proposed_proof"
PAGE = "lean/06-a-proof-an-agent-proposed"
ROOT = Path(__file__).parents[2]
SOURCE = (ROOT / "site" / "lessons" / PAGE / "index.qmd").read_text(encoding="utf-8")
LEAN = (
    ROOT / "lean" / "PhysicsByConstruction" / "Mechanics" / "CollisionEnergy.lean"
).read_text(encoding="utf-8")
WORKFLOW = (ROOT / "docs" / "coding-agent-workflow.md").read_text(encoding="utf-8")
NOT_VERIFIED = re.compile(r"(?ms)^(:{3,}) *\{[^}\n]*\.not-verified[^}\n]*\}.*?^\1 *$")


@pytest.fixture(scope="module")
def results(tmp_path_factory: pytest.TempPathFactory) -> tuple[Path, dict]:
    directory = tmp_path_factory.mktemp("agent_proposed_proof")
    return directory, run_entry_point(MODULE, directory)


def test_the_command_writes_what_the_page_shows(results):
    assert_the_page_and_the_results_agree(PAGE, *results)


def test_the_program_and_the_identity_agree_on_the_hunts_experiments(results):
    _, found = results
    rows = found["tables"]["hunt-instances"]["rows"]
    assert len(rows) == 4
    for row in rows:
        assert row[3] == row[4]
    # A wrong length changes the energy, a unit length does not.
    changes = {(row[0], row[1]): float(row[3]) for row in rows}
    assert changes[("1", "1")] > 0 > changes[("0.5", "0")]
    assert changes[("1", "0")] == changes[("0.6", "0.8")] == 0.0


def test_the_identity_is_independent_of_the_program():
    """The identity's value from its closed form, on a case worked by hand:
    m1 = 1, m2 = 2, v1 = (3, 0), v2 = (-1, 0), n = (1, 1): s = 4, the energy
    before 5.5 J, the change 2 * 2 / 3 * 16 * 1 = 64 / 3 J."""
    change = experiment.identity_change(
        1.0, 2.0, np.array([3.0, 0.0]), np.array([-1.0, 0.0]), np.array([1.0, 1.0])
    )
    assert change == pytest.approx((64 / 3) / 5.5, rel=1e-14)


def test_every_sampled_collision_lies_on_the_curve_of_the_identity():
    lengths, normalised = experiment.sampled_collisions()
    assert np.max(np.abs(normalised - (lengths**2 - 1))) < experiment.DEVIATION_BOUND
    # The sample reaches both sides of the unit length, so a curve that were
    # zero everywhere would fail.
    assert normalised.min() < -0.5 and normalised.max() > 0.5


def test_a_wrong_identity_is_far_from_the_samples():
    lengths, normalised = experiment.sampled_collisions()
    assert np.max(np.abs(normalised - (lengths - 1))) > 1e3 * experiment.DEVIATION_BOUND


def test_the_collision_without_approach_changes_nothing(results):
    _, found = results
    assert found["outputs"]["without-approach"].splitlines() == [
        "approach along n: 0.0 m/s",
        "relative change of the kinetic energy: 0.0",
        "velocities unchanged: True",
    ]


def test_a_direction_and_its_opposite_give_the_same_velocities(results):
    _, found = results
    plus, minus = found["tables"]["opposite-direction"]["rows"]
    assert plus[0] == "1" and minus[0] == "-1"
    assert plus[1:] == minus[1:]


# --- What the page states (the acceptance criteria of Issue #609). ---


def anchors() -> set[str]:
    return set(re.findall(r"(?m)^-- ANCHOR: (\S+)$", LEAN))


def test_every_proof_shown_is_an_excerpt_of_the_compiled_module():
    shown = set(re.findall(r'lean_excerpt\(ENERGY, "([^"]+)"\)', SOURCE))
    assert shown and shown <= anchors()
    # A Lean listing that is not an excerpt stands in a "not verified" block.
    outside = NOT_VERIFIED.sub("", SOURCE)
    assert "```lean" not in outside
    prose = re.sub(r"(?ms)^```\{python\}.*?^```$", "", outside)
    fences = re.findall(r"(?ms)^```.*?^```$", prose)
    assert not [f for f in fences if "theorem " in f]


def test_the_module_keeps_the_theorems_the_page_names():
    for name in (
        "collision_energy",
        "collision_energy_change",
        "unit_direction_exists",
        "energy_without_approach",
    ):
        assert re.search(rf"(?m)^theorem {name}\b", LEAN), name
    for forbidden in ("sorry", "axiom ", "#eval", "run_cmd", "set_option"):
        assert forbidden not in LEAN.split("-/", 1)[1], forbidden


def test_the_transcript_is_marked_not_verified_with_the_agent_and_the_date():
    blocks = [m.group(0) for m in NOT_VERIFIED.finditer(SOURCE)]
    transcript = [b for b in blocks if "Example transcript" in b]
    assert len(transcript) == 1
    assert re.search(r"Agent: \S", transcript[0])
    assert re.search(r"Date: \d{4}-\d{2}-\d{2}", transcript[0])
    assert "given to\nthe agent as instructions" in transcript[0]
    assert "Example transcript" not in NOT_VERIFIED.sub("", SOURCE)


def test_the_page_states_what_a_compiled_proof_does_and_does_not_establish():
    section = SOURCE.split("{#what-it-establishes}")[1].split("\n### ")[0]
    assert "establishes, with the certainty" in section
    assert "It does not establish:" in section
    for point in (
        "that the statement is the claim",
        "anything about the program",
        "anything about real spheres",
    ):
        assert point in section, point


def test_the_page_and_the_workflow_document_state_the_profile_for_lean():
    for rule in (
        "Dependencies before the start.",
        "One new file.",
        "Compiling is running.",
        "The audit after the build.",
    ):
        assert rule in SOURCE, rule
        assert rule in WORKFLOW, rule
    for rule in (
        "A scratch checkout.",
        "An allowlist of commands.",
        "No network beyond the agent's own provider.",
        "A budget, set before the start.",
        "Read every diff before you run it.",
    ):
        assert rule in SOURCE, rule
    for command in ("#eval", "run_cmd", "initialize", "native_decide", "lakefile.lean"):
        assert command in SOURCE and command in WORKFLOW, command


ALLOWLIST = (
    "only if it contains nothing but the allowed forms",
    "Anything else is refused, listed or not",
)
INLINE_EXECUTION = (
    "run_tac",
    "run_meta",
    "run_elab",
    "by_elab",
    "#eval!",
    "macro_rules",
    "elab_rules",
)


def _rule_3(text: str) -> str:
    return " ".join(
        text.split("**Compiling is running.**")[1].split("\n4. **")[0].split()
    )


def test_rule_3_for_lean_is_an_allowlist_with_the_inline_execution_forms():
    """Review 01, M1: a list of refused commands missed run_tac and the
    other forms that run code without defining anything."""
    plan = (
        ROOT / ".agents" / "plans" / "609-agent-assisted-theorem-proving.md"
    ).read_text(encoding="utf-8")
    for name, text in (("page", SOURCE), ("workflow", WORKFLOW), ("plan", plan)):
        rule = _rule_3(text)
        for phrase in ALLOWLIST:
            assert phrase in rule, (name, phrase)
        for form in INLINE_EXECUTION:
            assert f"`{form}`" in rule, (name, form)
    not_allowed = " ".join(SOURCE.split("## Not allowed")[1].split("```")[0].split())
    assert "anything but the allowed forms" in not_allowed
    for form in (*INLINE_EXECUTION, "syntax", "elab", "attribute"):
        assert re.search(rf"(?<![\w#!]){re.escape(form)}(?![\w!])", not_allowed), form


def test_the_module_uses_only_the_forms_rule_3_allows():
    allowed = re.compile(
        r"(import|namespace|section|end|open|variable"
        r"|theorem|lemma|def|noncomputable def)\b"
    )
    body = re.sub(r"(?s)/-.*?-/", "", LEAN)
    body = re.sub(r"--[^\n]*", "", body)
    top_level = [line for line in body.splitlines() if line and not line[0].isspace()]
    assert top_level
    for line in top_level:
        assert allowed.match(line), line
    for form in (
        "@[",
        "attribute",
        "run_tac",
        "by_elab",
        "#eval",
        "set_option",
        "sorry",
        "axiom ",
    ):
        assert form not in body, form
