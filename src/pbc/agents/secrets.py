"""Credentials: read from the environment, never shown.

A key is read once, from an environment variable, into a ``Secret`` whose
text form hides it. Everything a model returns goes through ``redact_data``
with the client's secrets before the harness keeps it, and everything that
leaves the harness (an error message, a printed line, a saved recording) goes
through ``redact`` as well.
"""

import os
from typing import Any

REDACTED = "[redacted]"
# Keys shorter than this cannot be told from ordinary words in a text.
_MIN_LENGTH = 8


class MissingKey(RuntimeError):
    """The environment variable that should hold the key is not set."""


class Secret:
    """A credential whose ``str`` and ``repr`` never contain its value."""

    __slots__ = ("_name", "_value")

    def __init__(self, name: str, value: str):
        if len(value) < _MIN_LENGTH:
            raise ValueError(f"the value of {name} is too short to be a key")
        self._name = name
        self._value = value

    @classmethod
    def from_environment(cls, name: str) -> Secret:
        """Read the key from the environment variable ``name``."""
        value = os.environ.get(name, "").strip()
        if not value:
            raise MissingKey(
                f"{name} is not set. Export your key in the shell that runs the"
                " agent; never write it into code, a notebook, or a committed"
                " file."
            )
        return cls(name, value)

    @property
    def name(self) -> str:
        return self._name

    def reveal(self) -> str:
        """The value, for the one place that sends it to the provider."""
        return self._value

    def __repr__(self) -> str:
        return f"Secret({self._name}={REDACTED})"

    __str__ = __repr__

    def __reduce__(self):
        raise TypeError("a Secret is not serialised")


def redact(text: str, *secrets: Secret) -> str:
    """``text`` with every occurrence of each secret replaced."""
    for secret in secrets:
        text = text.replace(secret.reveal(), REDACTED)
    return text


def redact_data(value: Any, *secrets: Secret) -> Any:
    """``value`` (JSON-like data) with every secret replaced in every text.

    Texts inside lists and dictionaries, and dictionary keys, are redacted
    too; numbers, booleans, and ``None`` are returned as they are.
    """
    if isinstance(value, str):
        return redact(value, *secrets)
    if isinstance(value, dict):
        return {
            redact_data(key, *secrets): redact_data(item, *secrets)
            for key, item in value.items()
        }
    if isinstance(value, list | tuple):
        return type(value)(redact_data(item, *secrets) for item in value)
    return value
