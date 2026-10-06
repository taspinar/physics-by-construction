"""Read the required checks from scripts/verify.conf.

Tests of a check run the command that verification really runs, taken from
this file, so a check that is weakened in the configuration fails its test.
"""

import re

from support.paths import SCRIPTS

_CHECK = re.compile(r"^([a-z0-9][a-z0-9-]*):\s*(.*\S)\s*$")


def checks() -> dict[str, str]:
    """Return the checks of verify.conf as name -> command, in file order."""
    result: dict[str, str] = {}
    for line in (SCRIPTS / "verify.conf").read_text().splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        match = _CHECK.match(line)
        if match is None:
            raise ValueError(f"malformed line in verify.conf: {line!r}")
        result[match.group(1)] = match.group(2)
    return result


def command(name: str) -> str:
    """Return the command of one check; fail when the check does not exist."""
    try:
        return checks()[name]
    except KeyError:
        raise AssertionError(f"verify.conf has no check named {name!r}") from None
