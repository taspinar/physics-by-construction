"""The Autonomous Physics Lab, the product of the capstone SA9: the
simulator vertical slice of F138 (``docs/products.md``).

One protocol, the frequency response of a prepared series RLC circuit, end
to end: ``protocol`` (one point, the analysis, the evaluator's check against
the closed form), ``baseline`` (the scripted route without a model),
``agent`` (the bounded agent route in the ADR 004 harness, with one
allowlisted operation of the instrument contract), ``workflow`` (a run: the
instrument of the chosen execution mode, the route, the evidence ledger, the
export), ``report`` (the report and its figure), ``interface`` (the thin
local interface, loopback only), and ``__main__`` (the command line). The
physical model is ``pbc.electromagnetism.circuits``; the instrument layer is
``pbc.instruments``; this package is the orchestration, and the three stay
apart.
"""
