"""A research pipeline that can stop, resume, and branch, on the records of
the evidence contract (F153, lesson RR4; ``docs/discovery-protocol.md``,
"Resumable runs and branches").

A pipeline is a list of stages. Each stage declares the keys of the
configuration it reads and the data files it reads, and turns the output of
the stage before it into its own. Running a stage writes its **state**, a
JSON file under the ledger's root that names the code, the configuration
the stage read, the digest of the state it continued from, the digests of
its data files, and its output, and records an attempt of the
``pbc.evidence`` ledger with that file as its artifact. A stage that raises
``ValueError`` is recorded as a failed attempt with its reason, and the run
of its branch stops there; the failure stays in the ledger.

``Research.resume`` continues a branch only from a state that is still
valid: every state file of its lineage has the digest the ledger recorded,
was written by the current code, with the configuration of the branch, on
data whose digest has not changed, and the last attempt did not fail.
Otherwise it refuses and names every cause. ``Research.fork`` starts a
branch that shares the first stages of its parent, and refuses when a
shared stage read a key the branch changes. The lineage of an attempt is
the chain of the attempts it follows.

A digest establishes identity, not truth: a valid state is the one that was
recorded, not a correct one.
"""

import json
from collections.abc import Callable, Mapping
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from pbc.evidence.records import (
    COMPLETED,
    DERIVED,
    FAILED,
    Artifact,
    Attempt,
    ContractError,
    Ledger,
    RunRecord,
    digest_file,
)

Output = Mapping[str, Any]


def _no_files(configuration: Mapping[str, Any]) -> Mapping[str, Path]:
    return {}


@dataclass(frozen=True)
class Stage:
    """One stage: its name, the configuration keys it reads, the data files
    it reads (a function of those keys), and its function from the output
    of the stage before (empty for the first) and the keys it reads to a
    JSON-able output."""

    name: str
    reads: tuple[str, ...]
    function: Callable[[Output, Mapping[str, Any]], Output]
    files: Callable[[Mapping[str, Any]], Mapping[str, Path]] = _no_files


@dataclass(frozen=True)
class Branch:
    """A line of the investigation: its configuration and, for a fork, the
    parent whose stages up to ``after`` it shares."""

    name: str
    configuration: Mapping[str, Any]
    parent: str | None = None
    after: str | None = None


@dataclass(frozen=True)
class State:
    """What a stage leaves: the branch and stage, the digest of the code it
    ran with, the configuration it read, the digest of the state it
    continued from (``None`` for the first stage), the digests of the data
    files it read, and its output."""

    branch: str
    stage: str
    code: str
    configuration: Mapping[str, Any]
    input: str | None
    data: Mapping[str, str | None]
    output: Output


def _plain(value: Any) -> Any:
    """``value`` as JSON reads it back: tuples become lists."""
    return json.loads(json.dumps(value))


def write_state(state: State, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(asdict(state), sort_keys=True, indent=1)
    path.write_text(text + "\n", encoding="utf-8")


def read_state(path: Path) -> State:
    return State(**json.loads(path.read_text(encoding="utf-8")))


@dataclass
class Research:
    """The stages, the branches, and the ledger of one investigation.

    ``record.code`` is the digest of the code the stages run; a state
    written with another digest is not resumed. The state files are written
    under ``root``, and the ledger names them relative to it."""

    stages: tuple[Stage, ...]
    record: RunRecord
    root: Path
    branches: dict[str, Branch] = field(default_factory=dict)
    ledger: Ledger = field(init=False)

    def __post_init__(self):
        self.root = Path(self.root)
        self.ledger = Ledger(self.record)

    @property
    def code(self) -> str:
        return self.record.code

    def _index(self, stage: str) -> int:
        names = [s.name for s in self.stages]
        if stage not in names:
            raise ContractError(f"there is no stage {stage!r}")
        return names.index(stage)

    def _owner(self, branch: Branch, index: int) -> Branch:
        """The branch whose attempt holds stage ``index`` of ``branch``."""
        while branch.parent is not None and index <= self._index(branch.after):
            branch = self.branches[branch.parent]
        return branch

    def attempt_id(self, branch: str, stage: str) -> str:
        owner = self._owner(self.branches[branch], self._index(stage))
        return f"{owner.name}/{stage}"

    def path(self, branch: str, stage: str) -> Path:
        return self.root / branch / f"{stage}.json"

    def state(self, attempt: str) -> State:
        branch, stage = attempt.split("/")
        return read_state(self.path(branch, stage))

    def start(self, name: str, configuration: Mapping[str, Any]) -> Branch:
        """A new branch that runs every stage itself."""
        if name in self.branches:
            raise ContractError(f"there is already a branch {name!r}")
        branch = Branch(name, dict(_plain(configuration)))
        self.branches[name] = branch
        return branch

    # region: fork
    def fork(
        self, parent: str, name: str, after: str, changes: Mapping[str, Any]
    ) -> Branch:
        """A branch that shares the stages of ``parent`` up to ``after`` and
        changes the keys ``changes``. A shared stage must not have read a
        changed key: its output would then belong to the parent's choice."""
        if name in self.branches:
            raise ContractError(f"there is already a branch {name!r}")
        base = self.branches[parent]
        unknown = sorted(set(changes) - set(base.configuration))
        if unknown:
            raise ContractError(f"{parent} has no configuration keys {unknown}")
        for stage in self.stages[: self._index(after) + 1]:
            read = sorted(set(stage.reads) & set(changes))
            if read:
                raise ContractError(
                    f"{stage.name} read {', '.join(read)}, which {name} changes:"
                    f" it cannot be shared; fork before it"
                )
        shared = self.ledger.attempt(self.attempt_id(parent, after))
        if shared is None or shared.status != COMPLETED:
            raise ContractError(f"{parent} has no completed {after} to fork from")
        configuration = {**base.configuration, **_plain(dict(changes))}
        branch = Branch(name, configuration, parent, after)
        self.branches[name] = branch
        return branch

    # endregion: fork

    def lineage(self, attempt: str) -> tuple[str, ...]:
        """``attempt`` and every attempt it follows, back to the first stage."""
        chain = []
        current = self.ledger.attempt(attempt)
        while current is not None:
            chain.append(current.id)
            current = self.ledger.attempt(current.prior[0]) if current.prior else None
        return tuple(chain)

    def _done(self, branch: Branch) -> list[tuple[int, Attempt]]:
        """The recorded attempts of ``branch``'s stages, in stage order."""
        found = []
        for index, stage in enumerate(self.stages):
            attempt = self.ledger.attempt(self.attempt_id(branch.name, stage.name))
            if attempt is None:
                break
            found.append((index, attempt))
        return found

    def run(self, name: str, stop_after: str | None = None) -> None:
        """Run the stages of a branch that has not run yet, up to
        ``stop_after`` (all when ``None``)."""
        branch = self.branches[name]
        done = self._done(branch)
        own = [a for _, a in done if a.candidate == name]
        if own:
            raise ContractError(f"{name} has already run; resume it")
        if done:
            index, attempt = done[-1]
            previous = self.state(attempt.id)
            self._continue(branch, index + 1, attempt, previous, stop_after)
        else:
            self._continue(branch, 0, None, None, stop_after)

    # region: problems
    def problems(self, name: str) -> list[str]:
        """Every reason the states of ``name`` are not a valid place to
        resume from; empty when they are."""
        branch = self.branches[name]
        found = []
        previous: str | None = None
        for index, attempt in self._done(branch):
            stage = self.stages[index]
            if attempt.status == FAILED:
                found.append(
                    f"{attempt.id} failed ({'; '.join(attempt.diagnostics)}):"
                    " the failure is kept; another choice is a new branch"
                )
                break
            (artifact,) = attempt.artifacts
            now = digest_file(self.root / artifact.path)
            if now is None:
                found.append(f"the state of {attempt.id} is missing")
                break
            if now != artifact.sha256:
                found.append(f"the state of {attempt.id} changed after it was recorded")
                break
            state = self.state(attempt.id)
            if state.code != self.code:
                found.append(f"{attempt.id} was written by other code")
            wanted = {k: branch.configuration[k] for k in stage.reads}
            changed = sorted(
                k for k in wanted if state.configuration.get(k) != wanted[k]
            )
            for key in changed:
                found.append(
                    f"{attempt.id} ran with the {key} {state.configuration.get(key)},"
                    f" the branch has {wanted[key]}: a changed choice is a new branch"
                )
            if state.input != previous:
                found.append(f"{attempt.id} did not continue the state before it")
            for label, path in stage.files(state.configuration).items():
                if digest_file(path) != state.data.get(label):
                    found.append(f"the data {label} of {attempt.id} changed")
            previous = artifact.sha256
        return found

    # endregion: problems

    def resume(self, name: str, stop_after: str | None = None) -> None:
        """Continue ``name`` after its last state, if every state of its
        lineage is valid (``problems``); otherwise refuse with the causes."""
        branch = self.branches[name]
        found = self.problems(name)
        if found:
            raise ContractError(f"{name} cannot resume: " + "; ".join(found))
        done = self._done(branch)
        if not done:
            raise ContractError(f"{name} has no state to resume from; run it")
        index, attempt = done[-1]
        self._continue(branch, index + 1, attempt, self.state(attempt.id), stop_after)

    def _continue(
        self,
        branch: Branch,
        first: int,
        prior: Attempt | None,
        previous: State | None,
        stop_after: str | None,
    ) -> None:
        last = len(self.stages) if stop_after is None else self._index(stop_after) + 1
        for index in range(first, last):
            stage = self.stages[index]
            prior = self._stage(branch, stage, prior, previous)
            if prior.status != COMPLETED:
                return
            previous = self.state(prior.id)

    def _stage(
        self,
        branch: Branch,
        stage: Stage,
        prior: Attempt | None,
        previous: State | None,
    ) -> Attempt:
        configuration = {k: branch.configuration[k] for k in stage.reads}
        data = {k: digest_file(p) for k, p in stage.files(configuration).items()}
        follows = (prior.id,) if prior is not None else ()
        attempt_id = f"{branch.name}/{stage.name}"
        try:
            output = _plain(
                stage.function(previous.output if previous else {}, configuration)
            )
        except ValueError as error:
            attempt = Attempt(
                attempt_id,
                branch.name,
                self.ledger.cycle,
                FAILED,
                diagnostics=(str(error),),
                prior=follows,
            )
            self.ledger.add_attempt(attempt)
            return attempt
        state = State(
            branch.name,
            stage.name,
            self.code,
            configuration,
            prior.artifacts[0].sha256 if prior is not None else None,
            data,
            output,
        )
        path = self.path(branch.name, stage.name)
        write_state(state, path)
        artifact = Artifact.of("state", path, self.root, DERIVED)
        attempt = Attempt(
            attempt_id,
            branch.name,
            self.ledger.cycle,
            COMPLETED,
            artifacts=(artifact,),
            prior=follows,
        )
        self.ledger.add_attempt(attempt)
        return attempt

    def rows(self) -> list[tuple[str, str, str, str]]:
        """One row per attempt: its id, the attempt it follows, its status,
        and its reason when it failed."""
        return [
            (
                a.id,
                a.prior[0] if a.prior else "none",
                a.status,
                "; ".join(a.diagnostics) or "",
            )
            for a in self.ledger.attempts
        ]
