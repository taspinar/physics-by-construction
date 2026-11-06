"""The instrument contract of the Part B products (F138; ADR 022 decision 5;
invariant I34; ``docs/products.md``).

``contract`` holds the guarded ``Instrument``, its safety ``Envelope``, the
``Driver`` protocol an adapter implements, and the run record that names the
execution mode. The adapters: ``simulated`` (a deterministic bench over the
series RLC circuit of ``pbc.electromagnetism.circuits``) and ``recorded`` (a
declared sample replayed, never a new experiment). The live adapter, an
optional driver behind its optional dependency group, is F140's; no module
here imports a device driver.
"""

from pbc.instruments.contract import (
    LIVE,
    MODES,
    RECORDED,
    SIMULATED,
    Capture,
    Driver,
    Envelope,
    Instrument,
    InstrumentRun,
    InstrumentTimeout,
    Interlock,
    InterlockOpen,
    Limit,
    OutOfEnvelope,
    Refused,
    Stopped,
    utc_now,
)

__all__ = [
    "LIVE",
    "MODES",
    "RECORDED",
    "SIMULATED",
    "Capture",
    "Driver",
    "Envelope",
    "Instrument",
    "InstrumentRun",
    "InstrumentTimeout",
    "Interlock",
    "InterlockOpen",
    "Limit",
    "OutOfEnvelope",
    "Refused",
    "Stopped",
    "utc_now",
]
