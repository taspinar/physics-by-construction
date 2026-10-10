"""Reference figures of the feasibility spikes (F50).

Each module reads a dataset from its committed sample or a downloaded copy and
builds one figure whose status label and caption its dossier states. Figures
are regenerated, never committed (invariant I6)::

    uv run python -m pbc.data.reference gw150914-strain --out figure.png
"""
