"""Read the required checks from scripts/verify.conf.

Tests of a check run the command that verification really runs, taken from
this file, so a check that is weakened in the configuration fails its test.
"""

import re

from support.paths import SCRIPTS

# '<name>: <command>' or '<name> [<group>]: <command>', as verify.sh reads it.
_CHECK = re.compile(
    r"^([a-z0-9][a-z0-9-]*)(?:\s*\[([a-z0-9][a-z0-9-]*)\])?:\s*(.*\S)\s*$"
)
DEFAULT_GROUP = "default"
# The entry of verify.conf that declares no check (ADR 014 decision 11).
SHARD_SIZE = "shard-size"


def _lines() -> list[tuple[str, str, str]]:
    result = []
    for line in (SCRIPTS / "verify.conf").read_text().splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        match = _CHECK.match(line)
        if match is not None and match.group(1) == SHARD_SIZE:
            continue
        if match is None:
            raise ValueError(f"malformed line in verify.conf: {line!r}")
        result.append((match.group(1), match.group(2) or DEFAULT_GROUP, match.group(3)))
    return result


def checks() -> dict[str, str]:
    """Return the checks of verify.conf as name -> command, in file order."""
    return {name: command for name, _, command in _lines()}


def groups() -> dict[str, str]:
    """Return the group of every check of verify.conf, as name -> group."""
    return {name: group for name, group, _ in _lines()}


def command(name: str) -> str:
    """Return the command of one check; fail when the check does not exist."""
    try:
        return checks()[name]
    except KeyError:
        raise AssertionError(f"verify.conf has no check named {name!r}") from None


def shard_size() -> int:
    """Return S, the most lessons of one lesson shard, as verify.conf declares it."""
    found = [
        line.split(":", 1)[1].strip()
        for line in (SCRIPTS / "verify.conf").read_text().splitlines()
        if line.startswith(f"{SHARD_SIZE}:")
    ]
    assert len(found) == 1, "verify.conf declares the shard size once"
    return int(found[0])
