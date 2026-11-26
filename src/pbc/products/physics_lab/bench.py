"""The lab's guarded instrument for a campaign (F145): the envelope of the
execution mode with both waveforms of the contract, the declared circuit,
and the interlock of the learner's confirmation of that circuit.

The circuit is declared by the plan (``campaign.SERIES_RLC`` or
``campaign.LED_PAIR``) and confirmed by the learner, never changed by the
product: a topology change is a new plan and a new confirmation. The
current bound of the live envelope uses the declared series resistance at
its lower tolerance; it is model-based and holds for the declared circuit
as wired (F140), for the sine and for the square wave (a step of height A
drives at most A / R through either circuit).
"""

import dataclasses
from collections.abc import Callable
from typing import Any

from pbc.instruments import (
    LIVE,
    RECORDED,
    SIMULATED,
    SINE,
    SQUARE,
    Driver,
    Envelope,
    Instrument,
    Interlock,
)
from pbc.instruments.recorded import RecordedBench, RecordedSample
from pbc.instruments.simulated import (
    LED_BENCH_PAIR,
    SimulatedLEDBench,
    SimulatedRLCBench,
)
from pbc.products.physics_lab.campaign import LED_PAIR, SERIES_RLC, CampaignPlan
from pbc.products.physics_lab.protocol import (
    LIVE_CURRENT_LIMIT_A,
    bench_envelope,
    live_envelope,
)
from pbc.products.physics_lab.quality import Rails, rails_for

RESISTANCE_TOLERANCE = 0.01  # of the declared series resistor


def wiring(plan: CampaignPlan) -> str:
    """The circuit the learner confirms, in words."""
    r = plan.series_resistance_ohm
    if plan.circuit == SERIES_RLC:
        return (
            f"W1 -> {r:g} ohm -> the coil -> node A -> the capacitor -> ground;"
            " scope 1+ at W1, 2+ at node A, both minus at ground"
        )
    return (
        f"W1 -> {r:g} ohm -> two LEDs of one colour in anti-parallel -> ground;"
        " scope 1+ at W1, 2+ across the LEDs, both minus at ground"
    )


def confirmation(plan: CampaignPlan, live: bool) -> str:
    """What the learner confirms before the output may go on."""
    text = f"confirm that the declared circuit is connected: {wiring(plan)}."
    if live:
        lowest = plan.series_resistance_ohm * (1.0 - RESISTANCE_TOLERANCE)
        text += (
            f" The {LIVE_CURRENT_LIMIT_A * 1e3:g} mA current bound assumes at least"
            f" {lowest:g} ohm in series; it is computed from the declared circuit,"
            " not measured, and does not hold under other wiring."
        )
    return text + " The product never rewires a circuit."


def lab_envelope(
    plan: CampaignPlan, live: bool, interlocks: tuple[Interlock, ...] = ()
) -> Envelope:
    """The envelope of the bench (simulated) or of the live bench, with the
    sine and the square wave permitted."""
    if live:
        lowest = plan.series_resistance_ohm * (1.0 - RESISTANCE_TOLERANCE)
        envelope = live_envelope(lowest, interlocks)
    else:
        envelope = bench_envelope(interlocks)
    return dataclasses.replace(envelope, waveforms=(SINE, SQUARE))


def simulated_driver(plan: CampaignPlan, seed: int) -> Driver:
    """The simulated bench of the declared topology."""
    if plan.circuit == LED_PAIR:
        return SimulatedLEDBench(pair=LED_BENCH_PAIR, seed=seed)
    return SimulatedRLCBench(circuit=plan.declared_circuit, seed=seed)


def make_instrument(
    plan: CampaignPlan,
    mode: str = SIMULATED,
    *,
    seed: int = 0,
    confirmed: bool = False,
    driver: Driver | None = None,
    sample: RecordedSample | None = None,
    recorded_live: bool = False,
    wrap_driver: Callable[[Driver], Driver] | None = None,
) -> tuple[Instrument, Rails]:
    """The guarded instrument of ``mode`` and the rails of its channels.

    Simulated: the bench of the declared topology with ``seed``. Recorded:
    ``sample`` replayed in order (a campaign repeats settings), under the
    live envelope when it was measured live (``recorded_live``). Live: the
    opened ``driver`` (the caller closes it). The interlock
    ``circuit-confirmed`` is the learner's ``confirmed``; a recorded sample
    drives nothing, so it has none.

    ``wrap_driver`` (simulated mode only) is the hook for changing the bench
    below the guard: it receives the simulated driver and returns the driver
    the instrument is built on, for example a lossy link around it, a call
    log, or a bench holding another circuit. It is applied before the
    ``Instrument`` is built, so the envelope check, the interlock, the
    watchdog, and the stop stay in the instrument above whatever it
    returns; nothing reaches the instrument's driver after it is built. The
    returned driver must keep the simulated mode, so the run record's label
    stays true. A recorded sample is a replay and a live driver is the
    caller's own, so neither is wrapped."""
    if wrap_driver is not None and mode != SIMULATED:
        raise ValueError("only the simulated driver is wrapped (wrap_driver)")
    flag = {"confirmed": confirmed}
    interlock = Interlock(
        "circuit-confirmed", confirmation(plan, mode == LIVE), lambda: flag["confirmed"]
    )
    if mode == SIMULATED:
        built: Any = simulated_driver(plan, seed)
        envelope = lab_envelope(plan, False, (interlock,))
        rails = rails_for(SIMULATED)
    elif mode == RECORDED:
        if sample is None:
            raise ValueError("the recorded mode needs a sample")
        built = RecordedBench(sample, sequential=True)
        envelope = lab_envelope(plan, recorded_live)
        rails = rails_for(LIVE if recorded_live else SIMULATED)
    elif mode == LIVE:
        if driver is None or driver.mode != LIVE:
            raise ValueError("the live mode needs an opened live driver")
        built = driver
        envelope = lab_envelope(plan, True, (interlock,))
        rails = rails_for(LIVE)
    else:
        raise ValueError(f"unknown execution mode {mode!r}")
    if wrap_driver is not None:
        built = wrap_driver(built)
        if getattr(built, "mode", None) != SIMULATED:
            raise ValueError("the wrapped driver must keep the simulated mode")
    return Instrument(built, envelope), rails
