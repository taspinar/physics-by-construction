# The atlas illustrations

The twelve illustrations of the Course Atlas (F133, Issue #338) are interface
artwork (ADR 021 decision 1): committed as derived WebP files under
`site/assets/atlas/`, each registered in `site/assets/provenance.yaml` with
its origin, licence, master, and the SHA-256 of the master (ADR 021 decision
2). This directory holds the scripts that exist for them. The build, the
verification, and CI never run anything here; the masters are not committed.

| Sequence | Script | Master |
|---|---|---|
| Classical mechanics | `double_pendulum_atlas.py` | `pbc_classical_mechanics_double_pendulum.webp`; the card from `pbc_classical_mechanics_atlas_card_detail.png` |
| Thermodynamics | `render_hot_cold.py` | `pbc_thermodynamics_hot_cold.webp` |
| Waves and optics | `render_waves.py` | `pbc_waves_optics_interference.webp` |
| Electromagnetism | `render_solenoid.py` | `pbc_electromagnetism_solenoid.webp` |
| Fluid dynamics | `generate_fluid_dynamics.py` | `pbc_fluid_dynamics_vortex_street.webp` |
| Quantum physics | `generate_wigner_cat.py` | `pbc_quantum_physics_wigner_cat.webp` |
| Astrophysics | none (registered by its author and date) | `pbc_astrophysics_exoplanet_transit.webp` |
| Condensed matter | `render_phonons.py` | `pbc_condensed_matter_acoustic.webp` |
| The four method paths | `render_part_b.py` with `part_b_textfree.py` | `pbc_part_b_<path>_textfree.png` |

- The owner's scripts (`double_pendulum_atlas.py`, `render_*.py`,
  `generate_*.py`) are committed as delivered on 2026-10-31 and excluded
  from the repository's lint (`pyproject.toml`). Their dependencies (NumPy,
  SciPy, Matplotlib, Pillow, and Numba for the fluid dynamics) are not
  added to the pinned environments.
- `part_b_textfree.py` hides every text object of the Part B figures
  (REJECT, RETAIN, REJECT, and the label 1/r²), after the owner's own
  validation in `render_part_b.py` has passed.
- `derive_assets.py MASTERS [OUT]` writes the card (152 and 228 px wide) and
  panel (400 and 800 px wide) sizes, 4:3, WebP, on the page's paper; run on
  the approved masters it reproduces the committed files byte for byte.
- `regenerate.py [SEQUENCE ...]` is the regeneration check, on demand: it
  runs a sequence's script in a scratch directory and compares the master
  with the hash in the register; where the bytes differ (the renders are not
  promised to be byte-stable across library versions) it compares the
  derived size with the committed file, within a mean of 2 of 255 per
  channel.

Left out of the delivered set: `render_ising.py`, `render_lensing.py` with
`test_lensing.py`, and `render_standing_wave.py`, whose images were not
chosen.
