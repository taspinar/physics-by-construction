"""The instrument contract of the Part B products (F138; ADR 022 decision 5;
invariant I34; ``docs/products.md``).

``contract`` holds the guarded ``Instrument``, its safety ``Envelope``, the
``Driver`` protocol an adapter implements, and the run record that names the
execution mode. The adapters: ``simulated`` (a deterministic bench over the
series RLC circuit of ``pbc.electromagnetism.circuits``) and ``recorded`` (a
declared sample replayed, never a new experiment). The live adapter, an
optional driver behind its optional dependency group, is F140's; no module
here imports a device driver. The excitation is a sine or, where the
envelope and the driver permit it, a square wave between 0 V and the
amplitude (F145).
"""

from pbc.instruments.contract import (
    LIVE,
    MODES,
    RECORDED,
    SIMULATED,
    SINE,
    SQUARE,
    WAVEFORMS,
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
    driver_waveforms,
    utc_now,
)

__all__ = [
    "LIVE",
    "MODES",
    "RECORDED",
    "SIMULATED",
    "SINE",
    "SQUARE",
    "WAVEFORMS",
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
    "driver_waveforms",
    "utc_now",
]
