"""The published Part B lessons at the base of the curriculum migration
(F136, Issue #370; ADR 022 decision 4): what each lesson's front matter
said at the base commit ``fc6da35`` and the slot it fills since.

Read from ``git show fc6da35:<page>`` when F136 started and written down
here, so that the tests need no history: the migration changes the slot and
nothing else, and every address, identifier, strand, order, and course stays.
The inventory is docs/roadmap.md, "State at the change cycle
`part-b-scientific-products-and-research`".
"""

from typing import NamedTuple

BASE = "fc6da35"


class Moved(NamedTuple):
    page: str  # relative to site/; its built address is page.html
    id: str
    strand: str
    order: int
    course: str
    base_slot: str  # "" for a lesson without a slot
    slot: str  # the slot it fills since F136


LESSONS = (
    Moved(
        "lessons/agents-llm/01-an-agent-runs-an-experiment/index.qmd",
        "agent-experiment",
        "agents-llm",
        1,
        "mechanics",
        "AI0",
        "SA5",
    ),
    Moved(
        "lessons/agents-llm/02-a-counterexample-hunter/index.qmd",
        "counterexample-hunter",
        "agents-llm",
        2,
        "mechanics",
        "AI3",
        "SA7",
    ),
    Moved(
        "lessons/agents-llm/03-three-reviewers/index.qmd",
        "scientific-review",
        "agents-llm",
        3,
        "mechanics",
        "AI4",
        "RR5",
    ),
    Moved(
        "lessons/agents-llm/04-an-experimental-design-agent/index.qmd",
        "experimental-design-agent",
        "agents-llm",
        4,
        "mechanics",
        "D9",
        "MD8",
    ),
    Moved(
        "lessons/agents-llm/05-discovering-a-force-law/index.qmd",
        "black-box-force-law",
        "agents-llm",
        5,
        "mechanics",
        "D1",
        "D1",
    ),
    Moved(
        "lessons/agents-llm/06-prior-knowledge-in-discovery/index.qmd",
        "prior-knowledge-in-discovery",
        "agents-llm",
        6,
        "mechanics",
        "D2",
        "MD1",
    ),
    Moved(
        "lessons/agents-llm/07-a-modified-force-law/index.qmd",
        "modified-force-law",
        "agents-llm",
        7,
        "mechanics",
        "D3",
        "D3",
    ),
    Moved(
        "lessons/agents-llm/08-symbolic-regression/index.qmd",
        "symbolic-regression",
        "agents-llm",
        8,
        "mechanics",
        "D7",
        "MD3",
    ),
    Moved(
        "lessons/agents-llm/09-discovering-differential-equations/index.qmd",
        "discovering-differential-equations",
        "agents-llm",
        9,
        "mechanics",
        "D8",
        "MD4",
    ),
    Moved(
        "lessons/agents-llm/10-equations-from-noisy-trajectories/index.qmd",
        "equations-from-noisy-trajectories",
        "agents-llm",
        10,
        "mechanics",
        "",
        "",
    ),
    Moved(
        "lessons/agents-llm/11-discovering-conservation-laws/index.qmd",
        "discovering-conservation-laws",
        "agents-llm",
        11,
        "mechanics",
        "D13",
        "MD7",
    ),
    Moved(
        "lessons/agents-llm/12-interactive-discovery-benchmarks/index.qmd",
        "interactive-discovery-benchmarks",
        "agents-llm",
        12,
        "mechanics",
        "EV2",
        "AE2",
    ),
    Moved(
        "lessons/agents-llm/13-agent-versus-non-agent-baselines/index.qmd",
        "agent-versus-non-agent-baselines",
        "agents-llm",
        13,
        "mechanics",
        "EV3",
        "AE3",
    ),
    Moved(
        "lessons/agents-llm/14-discovering-gravity/index.qmd",
        "discovering-gravity",
        "agents-llm",
        14,
        "mechanics",
        "D4",
        "D4",
    ),
    Moved(
        "lessons/agents-llm/15-unknown-physical-worlds/index.qmd",
        "unknown-physical-worlds",
        "agents-llm",
        15,
        "astrophysics",
        "D5",
        "D5",
    ),
    Moved(
        "lessons/agents-llm/16-multimodal-physics-reasoning/index.qmd",
        "multimodal-physics-reasoning",
        "agents-llm",
        16,
        "mechanics",
        "AI6",
        "AI6",
    ),
    Moved(
        "lessons/agents-llm/17-interpretable-physics-explanations/index.qmd",
        "interpretable-physics-explanations",
        "agents-llm",
        17,
        "mechanics",
        "AI7",
        "SA8",
    ),
    Moved(
        "lessons/agents-llm/18-discovery-under-noise/index.qmd",
        "discovery-under-noise",
        "agents-llm",
        18,
        "mechanics",
        "D10",
        "MD5",
    ),
    Moved(
        "lessons/agents-llm/19-hidden-variables/index.qmd",
        "hidden-variables",
        "agents-llm",
        19,
        "mechanics",
        "D11",
        "MD6",
    ),
    Moved(
        "lessons/agents-llm/20-generalisation-to-unseen-systems/index.qmd",
        "generalisation-to-unseen-systems",
        "agents-llm",
        20,
        "mechanics",
        "D12",
        "MD9",
    ),
    Moved(
        "lessons/mechanics/09-verifying-scientific-code/index.qmd",
        "verifying-scientific-code",
        "mechanics",
        9,
        "mechanics",
        "AI2",
        "SA2",
    ),
    Moved(
        "lessons/mechanics/10-automated-analysis-pipelines/index.qmd",
        "automated-analysis-pipelines",
        "mechanics",
        10,
        "mechanics",
        "R1",
        "RR4",
    ),
    Moved(
        "lessons/mechanics/12-inverse-physics-parameter-discovery/index.qmd",
        "inverse-physics",
        "mechanics",
        12,
        "mechanics",
        "D6",
        "MD2",
    ),
)
