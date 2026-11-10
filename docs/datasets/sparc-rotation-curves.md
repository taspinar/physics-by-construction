# Dossier: SPARC rotation curves and mass models of the baryons

Card: `data/registry/sparc-rotation-curves.yaml`. Inspected 2026-11-10 for F105 phase 1 (Issue #470), the measured-data lab AST9; the choice of SPARC over PROBES is in [the dataset research](spike-candidates-2026-11-08.md).

**Decision: go.** Kind: rotation curves of disk galaxies with the circular speeds of their gas and stars. Recorded under the owner's approval of 2026-11-10 on Issue #470 (work towards a `go`, judged on this dossier, with the written permission of the SPARC team that the owner accepted the same day); the checklist at the end names the evidence for each requirement.

## The file inspected

| | |
|---|---|
| Source | the SPARC website, https://astroweb.case.edu/SPARC/ (at astroweb.cwru.edu when the research of 2026-11-08 read it); F. Lelli, S. S. McGaugh, J. M. Schombert; reference paper Lelli, McGaugh and Schombert 2016, AJ 152, 157 (not read for this dossier; nothing here depends on its numbers) |
| File | `Rotmod_LTG.zip`, 110,737 bytes, Last-Modified 2016-03-25, sha256 `0a80cc90714828cc28b7dd57923576714d209f2490328c087c4a4ad607faf588`, md5 `e4c8b92766026770ed35e5889064e12b`. Downloaded on 2026-11-10 by another session of the owner; this session copied it into an empty directory outside the repository and checked the sha256 against Issue #470 before opening it. SPARC publishes no digest; the md5 equals the one of the third-party Zenodo copy (doi 10.5281/zenodo.16284118), which was not deposited by the SPARC team and is not the source |
| Archive | listed before extraction: 175 members, all `<name>_rotmod.dat`, flat (no directory, no absolute path, no `..`, no symlink), 175,149 bytes uncompressed, the largest 5,833 bytes; no readme and no licence text |
| Sample | five members extracted by exact name and committed byte for byte, 10,304 bytes: `NGC3198_rotmod.dat` (2,075 B), `NGC2403_rotmod.dat` (3,384 B), `NGC2841_rotmod.dat` (2,532 B), `DDO154_rotmod.dat` (622 B), `NGC2903_rotmod.dat` (1,691 B); the sha256 of each on the card |
| Not used | `SPARC_Lelli2016c.mrt`, the galaxy table with the inclinations, the distance methods and their errors: not approved by the Issue and not downloaded |
| Accessed | 2026-11-10 |

The five galaxies are chosen for the science: NGC 3198, a spiral with a long flat curve; NGC 2403, a spiral with 73 points and errors as small as 0.21 km/s; NGC 2841, the only one with a bulge, and massive; DDO 154, a gas-rich dwarf; NGC 2903, a barred spiral where the model fails at the centre.

Reader: `pbc.data.reference.sparc_rotmod.read_rotmod`, NumPy's `loadtxt` and a check of the three header lines; no dependency is added and no conversion is needed.

## Schema, units, masks, coverage

| Item | What the record documents | What this dossier established on the files |
|---|---|---|
| Schema | the header lines of each file | ASCII; line 1 `# Distance = <D> Mpc`; line 2 the names `Rad Vobs errV Vgas Vdisk Vbul SBdisk SBbul`; line 3 the units; then one row per radius of eight tab-separated numbers with two decimals, radii increasing |
| Units | line 3: `kpc km/s km/s km/s km/s km/s L/pc^2 L/pc^2` | as stated; the luminosity is solar luminosities at 3.6 µm (the paper, through the research) |
| Mass-to-light normalisation | not in the file; the paper and the website state Vdisk and Vbul at 1 M☉/L☉ at 3.6 µm (as read by the research) | confirmed on every file: Vdisk² r / G at the last radius over the light of SBdisk inside it (a ring sum) is 1.025, 1.021, 1.065, 1.085 and 1.055 for NGC 3198, NGC 2403, NGC 2841, DDO 154 and NGC 2903. A thin disk turns slightly faster than a point of the same mass, so a little above 1 is expected; at 0.5 M☉/L☉ the ratio would be near 0.5. The bulge of NGC 2841 cannot be checked this way: its light lies almost entirely inside the first radius, 3.44 kpc (9 rows with SBbul > 0) |
| Inclination | not in the file | Vobs is already deprojected. The research of 2026-11-08 showed it against PROBES (its first NGC 3198 point is SPARC's times sin 73°); not repeated here, since PROBES is not inspected in this feature. A lab cannot vary the inclination from these files |
| Vgas | sign as written | negative in 6 rows of NGC 3198 and 9 of NGC 2841: the gas pulls outward there (a central hole); the model uses Vgas·\|Vgas\|. 0.00 inside the hole in 3 rows of NGC 3198 and 2 of NGC 2403 |
| Masks, missing values | none | no missing value, no flag; 0.00 for "no component": Vbul and SBbul in the four bulgeless galaxies, SBdisk beyond the photometry (1 to 9 rows per file) |
| Coverage | | NGC 3198 43 points, 0.32–44.08 kpc; NGC 2403 73, 0.16–20.87; NGC 2841 50, 3.44–63.64; DDO 154 12, 0.49–5.92; NGC 2903 34, 0.32–24.96 |
| Distance | line 1 | 13.8, 3.16, 14.1, 4.04 and 6.6 Mpc. The radii scale with D, the light and the gas mass with D², so Vdisk, Vbul and Vgas with √D; Vobs does not. A larger distance lowers the fitted Y |

The parsing test `tests/unit/test_data_sparc_rotmod.py::test_sparc_rotmod_sample_parses` asserts the checksums and sizes, the three header lines, eight tab-separated two-decimal fields per row, the number of rows and the first and last radius, increasing radii, no missing or negative values except Vgas, the rows with negative Vgas, and that only NGC 2841 has a bulge. `test_vdisk_is_the_speed_of_the_light_at_mass_to_light_one` asserts the normalisation.

## Artifact labels

| Artifact | Type |
|---|---|
| Rad, Vobs, errV | `processed-measured` (the SPARC team's curve from published HI and H-alpha velocity fields: tilted rings, folded, deprojected) |
| SBdisk, SBbul | `processed-measured` (Spitzer 3.6 µm photometry, decomposed into disk and bulge by the team) |
| Vgas, Vdisk, Vbul | `modelled-reference` (circular speeds the team computed from the gas and the light, at Y = 1) |
| Distance (line 1) | `processed-measured`, catalogue metadata |
| the fits, halos, maximum disk and Y profile of `pbc.data.reference.sparc_rotmod` | `modelled-reference`, not part of the record |

The figure draws Vobs as points with errV bars; the SPARC components dotted and labelled "(SPARC model)"; the fitted totals as lines, each labelled with its model.

## The mass model

`pbc.data.reference.sparc_rotmod` fits

V²(r) = Vgas·|Vgas| + Y (Vdisk² + Vbul²) + V²halo(r)

with one stellar mass-to-light ratio Y for disk and bulge (the same band), by least squares in the speed with errV as absolute sigma (`pbc.data.fit.fit_curve`), started from the best point of a coarse grid because the chi-square has more than one valley. Three models: **baryons only** (Y free, 0 to 50), the **NFW halo** ρ = ρs / ((r/rs)(1 + r/rs)²), cuspy, and the **pseudo-isothermal halo** ρ = ρ0 / (1 + (r/rc)²), cored, each with Y in 0 to 5 and the halo's radius and density in log space. The halo speeds are the enclosed mass over r (a test integrates the densities numerically); G = 4.3009 × 10⁻⁶ kpc (km/s)² / M☉ from the IAU nominal GM☉.

**Where the model lives.** In phase 1 the model is part of the reference figure, under `src/pbc/data/reference/` as ADR 007 asks. The lab of phase 2 builds on AST2 (modified gravity, `pbc.astrophysics.central_force`: circular orbits in a central force and what an orbit can say about a force law) and AST3 (gravitational lensing, `pbc.astrophysics.lensing`: mass from its effect on light); the verified mass model of the lab belongs beside them as a module of `pbc.astrophysics`, with this module's halos and fits moved there and tested, and the reference figure reading it. Phase 2 decides that, not this feature.

## Reference figure

```
uv run python -m pbc.data.reference sparc-rotation-curves --out sparc.png
```

The code is `src/pbc/data/reference/sparc_rotmod.py`. **Status label: processed** (the curve is the team's processed measurement; the fits are computed here). Panels: the rotation curves of NGC 3198 and DDO 154 with errV, the gas, the stars at the core fit's Y, the core fit's halo, and the three fitted totals, each with the residuals below on the same radius axis; the reduced chi-square of the best halo at each fixed Y for NGC 2403, both halos, with errV and with the floor, and the maximum disk; and the reduced chi-square of every model for all five galaxies, with errV and with the floor.

**Caption.** *Five SPARC galaxies against three mass models. Without a halo, no mass-to-light ratio of the stars fits any of them (reduced chi-square 175 to 1026): the stars and gas fall off where the measured curves stay flat. With a halo of either shape, NGC 3198 and NGC 2841 fit to a reduced chi-square of 1.2 to 1.4. The dwarf DDO 154 tells the shapes apart: the cuspy NFW halo, with its stars switched off, still lies above the two innermost points by 2.5 and 4.6 times their errors (reduced chi-square 8.7); the cored halo fits (2.2). For NGC 2403 the fitted Y is 0.29 with a cusp and 0.76 with a core: the mass-to-light ratio depends on the halo assumed. The errors exclude the inclination and the distance, so the chi-square depends on them; with an illustrative 5 % floor every halo fit but NGC 2903's falls below 1.3.*

| Galaxy | Points | Baryons only: Y, χ²/dof | NFW: Y, rs (kpc), ρs (M☉/pc³), χ²/dof | Pseudo-isothermal: Y, rc (kpc), ρ0 (M☉/pc³), χ²/dof | χ²/dof with the 5 % floor: none / NFW / iso | Maximum disk Y |
|---|---|---|---|---|---|---|
| NGC 3198 | 43 | 1.33, 235 | 0.45 ± 0.05, 14.5, 0.0073, 1.39 | 0.52 ± 0.04, 2.78, 0.049, 1.24 | 17.1 / 0.40 / 0.17 | 0.61 |
| NGC 2403 | 73 | 1.94, 840 | 0.29 ± 0.03, 7.15, 0.024, 9.14 | 0.76 ± 0.01, 3.03, 0.036, 10.70 | 24.3 / 0.44 / 0.58 | 0.86 |
| NGC 2841 | 50 | 2.11, 175 | 1.02 ± 0.02, 47.5, 0.0024, 1.41 | 1.10 ± 0.03, 9.08, 0.017, 1.34 | 19.6 / 0.13 / 0.13 | 1.07 |
| DDO 154 | 12 | 18.9, 1026 | 0.00 (at the bound), 13.4, 0.0018, 8.73 | 0.06 ± 0.20, 1.44, 0.029, 2.19 | 71.6 / 1.23 / 0.30 | 1.47 |
| NGC 2903 | 34 | 0.90, 209 | 0.22 ± 0.03, 4.79, 0.11, 5.95 | 0.30 ± 0.02, 0.94, 0.65, 6.23 | 31.8 / 3.29 / 3.13 | 0.07 |

The ± are the fit's standard errors with errV as absolute sigma; where the reduced chi-square is far above 1 they are too small. Asserted by `test_the_halo_fits_are_the_dossiers`, `test_no_mass_to_light_ratio_fits_without_a_halo`, and `test_the_maximum_disk_touches_the_curve_and_exceeds_it_nowhere`; a synthetic galaxy with a known Y and halo is recovered within two standard errors (`test_a_known_halo_and_mass_to_light_ratio_are_recovered`).

**The degeneracy of Y.** In every free fit of the four spirals, Y and the halo's density are anticorrelated (correlation −0.84 to −0.98): more mass in stars, less in the halo, nearly the same curve. Which Y the data pick depends on what is assumed:

- **The halo's shape.** NGC 2403: 0.29 with a cusp, 0.76 with a core. NGC 3198: 0.45 and 0.52. A cusp puts mass at the centre, where the stars are, and takes Y down.
- **The errors.** With the 5 % floor NGC 2403's Y becomes 0.50 (cusp) and 0.84 (core), and NGC 2903's cusp fit puts Y at 0.
- **Two valleys.** NGC 2403's cored halo has two minima of the chi-square in Y, a halo-dominated disk near Y = 0.08 and a near-maximum disk at 0.76, the second deeper (`test_the_mass_to_light_ratio_depends_on_the_halo_and_the_errors`). Which disk is real is not decided by a rotation curve alone; it needs an independent Y (stellar populations, the vertical motions of the disk).
- **The maximum disk.** The largest Y for which the stars and gas exceed no point's Vobs + errV: 0.61 for NGC 3198, 0.86 for NGC 2403, 1.07 for NGC 2841. The fitted Y of NGC 2841 is at its maximum disk, a high value for 3.6 µm at the adopted 14.1 Mpc; at a larger distance Y would fall.

**What the five galaxies show.**

- **NGC 3198.** The baryons-only fit (Y = 1.33) lies above the curve inside 10 kpc, by 15 to 22 km/s between 4 and 7 kpc (several times errV) and by up to 49 km/s at the uncertain innermost points, and falls 63 km/s short at 44 kpc. Both halos fit; the innermost points (errV up to 36 km/s) lie below both.
- **DDO 154.** The gas dominates the baryons; at the last point it gives 12 % of Vobs², the stars of the core fit 0.1 %. The core fits; the cusp, even with no stars, overshoots the first two points. This is a result for these 12 points under these assumptions, not a measurement of the dark matter's profile.
- **NGC 2903.** The two innermost points lie 64 to 70 km/s below both halo fits (8 to 9 times errV), in the region of the bar, where the research of 2026-11-08 places the cause (gas in a bar does not move on circular orbits); the maximum disk, set by those points, is 0.07. A circular-orbit model does not describe a bar; a lab can leave out the inner points and say so.

## Uncertainty and calibration

- **errV.** Per point, 0.20 to 35.90 km/s in the sample; the median is 0.55 km/s for DDO 154 and 5.93 km/s for NGC 2841. It excludes the inclination's and the distance's uncertainty (the research, from the paper), which the galaxy table lists and the sample does not carry. A smooth model of a well-sampled galaxy (NGC 2403, 73 points, errV down to 0.21 km/s) therefore has a reduced chi-square far above 1 (9 to 11) even when the curve is described to a few km/s.
- **The error floor.** The figure and the table add, as an illustration and not as a property of the record, 5 % of Vobs in quadrature, the order of a few degrees of inclination on a moderately inclined disk (δV/V = cot i δi). With it the reduced chi-square of the halo fits falls to 0.13 to 3.3 and Y moves (above). A lab must state its floor and show that its conclusion survives a change of it.
- **Inclination and distance.** Not in the files. Vobs scales with 1/sin i, so an error of the inclination scales the whole curve; the distance scales the radii and the baryons' speeds (above). Both are systematic for one galaxy, not random per point.
- **One-sided curves.** The curves are averages of the two sides of each disk; asymmetry and non-circular motion (a bar, a warp) are not in the file.
- **The baryons.** Vgas includes the team's correction for helium (the research, from the paper); Vdisk and Vbul assume a disk thickness chosen by the team. No uncertainty is given for them.
- **Calibration.** None is applied here. Y is the free calibration of the stellar mass and is fitted; it is not a measured number.

## What the inference may say

A lab built on these files compares models; it does not measure dark matter. Under the stated assumptions (circular orbits, the team's inclinations and distances, one Y for disk and bulge, spherical halos, errV as the only random error) the stars and gas at any Y cannot produce the flat outer curves, a halo of either shape can, and the cored halo describes DDO 154 better than the cusp. The halo's parameters and Y trade against each other, depend on the halo's shape and on the error floor, and do not single out one disk mass. Other explanations of flat curves (a modified force law, the subject of AST2) are not tested by these fits.

## Rights

| Question | Answer | Source |
|---|---|---|
| Local download | permitted | the SPARC website offers the archive and asks users to cite the SPARC paper (as read by the research of 2026-11-08); the written permission below |
| Redistribution of subsets | permitted | **written permission of the rights holder**: F. Lelli (SPARC team) replied to the owner on 2026-11-10 that the owner may include `Rotmod` files in the public repository as long as the SPARC website and the reference paper are provided (as the Zenodo page does). The owner accepted the reply as the permission on 2026-11-10 ([Issue #470](https://github.com/taspinar/physics-by-construction/issues/470)). The e-mail is private correspondence, kept by the owner, not committed |
| Publication of figures and derivatives | permitted | the reply names the files, not derived figures; the owner decided on 2026-11-10 to read it as covering the figures and animations derived from the files, with the attribution it asks for, and requested no further confirmation (Issue #470) |
| Modification and attribution | permitted with attribution | the permission's two conditions: the SPARC website https://astroweb.case.edu/SPARC/ and the reference paper Lelli, McGaugh and Schombert 2016, AJ 152, 157, on the card, in this dossier, on the figure, and on the lab's page; the files are not modified |

The reply names no licence. The sample is labelled "redistributed with the authors' permission; cite Lelli, McGaugh and Schombert 2016 and link the SPARC website" and is **not** relabelled CC BY. Under the addendum of 2026-11-08 to ADR 007 (Issue #417), a written permission of the rights holder recorded on the card permits a committed sample; the card records the licence as `equivalent-permission`, the existing value of `src/pbc/data/card.py`. The Zenodo copy's CC BY 4.0 is not relied on: the SPARC team did not deposit it. The site's own licences apply to the figures, with the attribution.

## Size, runtime, payload

Sample 10.3 kB in five files, the largest 3.4 kB (caps: 2 MB per file, 8 MB per dataset; all samples together about 24.7 MB of 32). The full archive is 110.7 kB; `./scripts/fetch-data.sh sparc-rotation-curves` downloads it by the card's URL and checksum (the 170 other galaxies). Figure: about 3 to 6 s including the interpreter start (30 fits and 124 fits for the Y profile), about 170 MB peak memory; PNG about 460 kB at 150 dpi. A lesson page that reads the sample and fits the models stays far inside the 30 s warning, the 60 s limit and the 3 MB payload: the data are read at build time and only the figure reaches the browser. CI reads only the committed files.

## The requirements of ADR 007 and where they are met

| Requirement | Evidence |
|---|---|
| 1. An actual small file inspected, checksum, size, version | "The file inspected": the archive's sha256 checked before opening, the members listed, five extracted and committed unchanged; the archive's date and checksum as the version |
| 2. Schema, units, calibration, cadence, masks, coverage | "Schema, units, masks, coverage", including the Y = 1 normalisation confirmed on the files; the parsing test |
| 3. Every artifact labelled, measurement apart from models | "Artifact labels"; the SPARC components and the fits drawn and labelled apart from Vobs |
| 4. Reproducible reference figure from source-controlled code | `src/pbc/data/reference/sparc_rotmod.py`, from the committed sample; `tests/unit/test_data_plotting.py` checks its status and conventions, including the residual panels |
| 5. Rights, four answers with their source | "Rights"; the card's `rights`: the written permission of 2026-11-10 and the owner's acceptance |
| 6. Download, build time, payload | "Size, runtime, payload" |
| 7. Uncertainty and calibration | "Uncertainty and calibration": errV without inclination and distance, the illustrative floor, the one-sided curves, Y as the fitted calibration |
| 8. This dossier with the decision | this file, including what the inference may and may not say |

## Open items

- Phase 2, the AST9 lab, starts only when the owner says so (Issue #470). It decides where the verified mass model lives in `pbc.astrophysics` (above) and whether more galaxies are committed (the archive is 175 kB in all).
- The inclinations and their errors (`SPARC_Lelli2016c.mrt`, 28 kB) are not approved; without them a lab states the inclination as a limit. If the lab needs them, the owner is asked on the Issue.
- PROBES (Zenodo 10456320, CC BY 4.0) is not needed: SPARC reached a `go`.
