"""The tool allowlist: the whole of what a model can make the harness do.

A lesson declares an ``Allowlist`` of ``Tool`` objects, each wrapping one
function of ``pbc`` with typed, bounded parameters. A call is checked first
(``Tool.validate``) and executed only when it passes. Nothing is looked up by
a name the model chooses except in the allowlist's own dictionary, so a model
cannot reach any other function, module, file, or process.
"""

import math
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Any

from pbc.agents.messages import ToolCall, ToolResult, ToolSpec


class ToolRejected(ValueError):
    """A call that was not executed, with the reason."""


@dataclass(frozen=True)
class Parameter:
    """One argument of a tool: a number between two bounds (inclusive)."""

    name: str
    description: str
    low: float
    high: float
    integer: bool = False

    def validate(self, value: Any) -> float | int:
        # bool is an int in Python; "true" is not a number of metres.
        if isinstance(value, bool) or not isinstance(value, int | float):
            raise ToolRejected(
                f"{self.name} must be a number, got {type(value).__name__}"
            )
        if self.integer and not isinstance(value, int):
            raise ToolRejected(f"{self.name} must be an integer, got {value!r}")
        if isinstance(value, float) and not math.isfinite(value):
            raise ToolRejected(f"{self.name} must be finite, got {value!r}")
        # An int is compared as an int: one too large for a float (JSON allows
        # it) must be refused, not converted.
        if not self.low <= value <= self.high:
            shown = f"{value:g}" if isinstance(value, float) else str(value)
            raise ToolRejected(
                f"{self.name} must be between {self.low:g} and {self.high:g},"
                f" got {shown}"
            )
        return value

    def schema(self) -> dict[str, Any]:
        return {
            "type": "integer" if self.integer else "number",
            "description": self.description,
            "minimum": self.low,
            "maximum": self.high,
        }


@dataclass(frozen=True)
class Tool:
    """An allowlisted function of ``pbc``.

    ``function`` takes the validated parameters as keyword arguments and
    returns a mapping from result names to numbers.
    """

    name: str
    description: str
    parameters: tuple[Parameter, ...]
    function: Callable[..., Mapping[str, float]]

    def validate(self, arguments: Any) -> dict[str, float | int]:
        """The arguments if they are exactly the declared ones, each within
        its bounds; otherwise raise ``ToolRejected``."""
        if not isinstance(arguments, dict):
            raise ToolRejected(
                f"the arguments must be an object, got {type(arguments).__name__}"
            )
        declared = {parameter.name: parameter for parameter in self.parameters}
        unknown = sorted(str(key) for key in arguments if key not in declared)
        if unknown:
            raise ToolRejected(f"unknown arguments: {', '.join(unknown)}")
        missing = sorted(name for name in declared if name not in arguments)
        if missing:
            raise ToolRejected(f"missing arguments: {', '.join(missing)}")
        return {
            name: parameter.validate(arguments[name])
            for name, parameter in declared.items()
        }

    def spec(self) -> ToolSpec:
        return ToolSpec(
            name=self.name,
            description=self.description,
            parameters={
                "type": "object",
                "properties": {p.name: p.schema() for p in self.parameters},
                "required": [p.name for p in self.parameters],
                "additionalProperties": False,
            },
        )


class Allowlist:
    """The tools of one lesson, by name."""

    def __init__(self, tools: tuple[Tool, ...]):
        names = [tool.name for tool in tools]
        if len(set(names)) != len(names):
            raise ValueError(f"duplicate tool names in {names}")
        self._tools = {tool.name: tool for tool in tools}

    @property
    def tools(self) -> tuple[Tool, ...]:
        return tuple(self._tools.values())

    def specs(self) -> tuple[ToolSpec, ...]:
        return tuple(tool.spec() for tool in self.tools)

    def dispatch(self, call: ToolCall) -> ToolResult:
        """Validate ``call`` and run it, or return the reason it was refused.

        The name is only a key into the allowlist: a name that is not in it
        is rejected without looking anything else up. A function that
        refuses its input (``ValueError``, ``RuntimeError``) gives an error
        result as well; any other exception is a bug and propagates.
        """
        tool = self._tools.get(call.name) if isinstance(call.name, str) else None
        if tool is None:
            return self._refused(call, f"{call.name!r} is not an allowed tool")
        try:
            arguments = tool.validate(call.arguments)
        except ToolRejected as reason:
            return self._refused(call, str(reason))
        try:
            content = dict(tool.function(**arguments))
        except (ValueError, RuntimeError) as reason:
            return self._refused(call, str(reason))
        return ToolResult(call_id=call.id, name=call.name, ok=True, content=content)

    @staticmethod
    def _refused(call: ToolCall, reason: str) -> ToolResult:
        return ToolResult(
            call_id=str(call.id),
            name=str(call.name),
            ok=False,
            content={"error": reason},
        )
