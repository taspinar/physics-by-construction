# Plan: F105 phase 1 — the SPARC rotation curves: card, dossier, sample, figure (Issue #470)

Phase 1 only: the card, the dossier, the committed sample, its parsing test,
and the reference figure, towards a `go` judged per dossier (owner's approval
and acceptance of the SPARC team's written permission, 2026-11-10, on the
Issue). Phase 2, the AST9 lab, starts only after a `go` and the owner's word.
Roadmap row F105 checked: not retired.

## Steps

1. No download: copy `Rotmod_LTG.zip` from the owner's other session into a
   new empty scratch directory, check its sha256 against the Issue, list the
   members (175, flat, no `..`, no symlinks, largest 5,833 B) before
   extracting, extract five members by exact name, read as text only.
2. Commit as the sample `data/samples/sparc-rotation-curves/`, unmodified:
   `NGC3198`, `NGC2403`, `NGC2841`, `DDO154`, `NGC2903` `_rotmod.dat`
   (10,304 B).
3. Reader and reference figure `src/pbc/data/reference/sparc_rotmod.py`: the
   reader with its header checks; the NFW and pseudo-isothermal halos; the
   fits without a halo and with each halo (`pbc.data.fit.fit_curve`, started
   from a grid); the maximum disk; the Y = 1 normalisation of Vdisk by a ring
   sum of SBdisk; the chi-square profile in Y; an illustrative 5 % error
   floor. Registered in `pbc.data.reference.__main__`.
4. Tests `tests/unit/test_data_sparc_rotmod.py` (parsing; the halo speeds
   against the numerically integrated masses; the normalisation; the
   maximum disk; the dossier's fits; a synthetic galaxy recovered; the cusp
   failing DDO 154; the degeneracy; NGC 2903's bar region), and the lists of
   `tests/unit/test_data_plotting.py` and
   `tests/integration/test_data_checks.py`.
5. The card `data/registry/sparc-rotation-curves.yaml` (licence
   `equivalent-permission`: the written permission of the rights holder,
   ADR 007 addendum), the dossier `docs/datasets/sparc-rotation-curves.md`
   with the ADR 007 checklist and where the model of phase 2 lives, the row
   in `docs/datasets/README.md`. No conversion script: the files are plain
   text.

## Visual deliverables

- Scientific figure: the reference figure of the dataset (the curves of
  NGC 3198 and DDO 154 with the SPARC components and the three fitted models,
  residuals below; the reduced chi-square against a fixed Y for NGC 2403 with
  both halos, with errV and the floor, and the maximum disk; the reduced
  chi-square of every model for the five galaxies). Status `processed`.
  Skills: pbc-scientific-visualization@a70b501
  Validation: every number of the caption and the dossier's table is
  computed by the module and asserted by the tests; the halo formulas are
  checked against numerical integration, the fit against a synthetic
  galaxy. Accessible fallback: the dossier's caption and table give every
  plotted number in text.

## Out of scope

The AST9 lab and the verified model in `pbc.astrophysics` (phase 2);
`SPARC_Lelli2016c.mrt` (not approved); PROBES; ADR 007, the card schema, the
dataset check; the About page (no page uses the sample yet).
