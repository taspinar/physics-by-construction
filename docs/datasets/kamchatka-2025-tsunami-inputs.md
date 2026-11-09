# Dossier: the inputs of the 2025 Kamchatka tsunami capstone

Card: `data/registry/kamchatka-2025-tsunami-inputs.yaml`. Inspected 2026-11-09 for F88 phase 1 (Issue #444), the applied capstone FL10 of the `fluids` course. The choice of these sources (the NCEI event files rather than NDBC's raw files alone, ETOPO 2022 rather than GEBCO_2026) is in [the dataset research](spike-candidates-2026-11-08.md).

**Decision: go.** Kind: the inputs of a teaching-scale tsunami reconstruction: two deep-ocean bottom-pressure records (DART 21416 and 21415), the USGS finite-fault model of the earthquake with its surface deformation, and a cropped bathymetry. Recorded under the owner's approval of 2026-11-09 on Issue #444 (work towards a `go`; record `go` only if every requirement of ADR 007 is covered by evidence). The checklist below names the evidence for each; the limits are in "What the data do not give".

This `go` covers the inputs only. The propagation model, its benchmarks, and any comparison of a model with the DART records are phase 2 of F88, which starts only on the owner's word; until then nothing here claims agreement between a model and the observations. The √(gh) arrival times below check that each record's window holds the tsunami; they are not that comparison.

## The files inspected

| | |
|---|---|
| DART, NCEI | Event directory https://www.ngdc.noaa.gov/hazard/data/DART/20250729_kamchatka/ (files dated 2025-08-11): `dart21416_20250727to20250803_meter.txt` (127,275 B, sha256 `27c5b353afb8361bde9a439767c497062a2a73eff3003bb2d453d61bb647b44b`), `dart21415_20250727to20250803_meter.txt` (132,075 B, sha256 `ef2edd45e649e5e42953e107019620709f9e933d3b4beab8f1c452e200c64642`), `DART_deployment_coord.txt` (3,120 B, sha256 `72f224e7a93d18d5ad564f11f2419b402adb0ab48c1a581fe870936d09c7918b`). Collection doi 10.7289/V5F18WNS |
| DART, NDBC | Historical annual files https://www.ndbc.noaa.gov/data/historical/dart/: `21416t2025.txt.gz` (173,424 B, sha256 `40b3b6891e62f521d83ed17dd085e7c1bf4c646f5ff43a57c0af0b07d6f90989`), `21415t2025.txt.gz` (169,146 B, sha256 `3298af96ed9c30da9522331e76edaf3deeeb360182cf92226f28944ac50e8070`) |
| Finite fault, USGS | Event us6000qw60, product `us6000qw60_1` version 5 (update 1763589364802, file header dated 2025-11-19): `complete_inversion.fsp` (49,217 B, sha256 `0f348e3b7952cdb61a0358aa6abea43f77a7da3d217134ffdf360307d43fa36d`), `surface_deformation.disp` (123,312 B, sha256 `3b3e2568c31d3b1c50bf190554fcd0f0ba1a38be8ff0c454b10756cba33eeddf`); the lengths equal those of ComCat's product record |
| Bathymetry, NCEI | ETOPO 2022 v1, doi 10.25921/fd45-gt74, `ETOPO_2022_v1_60s_N90W180_bed.nc` on NCEI's THREDDS server, OPeNDAP ASCII request `z[7500:4:8999][19200:4:21599]`: 2,463,031 B, sha256 `454b00a5aaaaf4406523e1f39fc38dbd40ea3c6799d5cde209d25b75701bf198`, identical over two requests |
| Accessed | 2026-11-09 |

No source publishes a checksum; the sha256 values were computed on the downloads and are on the card. The sizes equal those the research of 2026-11-08 recorded (NCEI 21416, NDBC 21416, the two USGS files, the ETOPO response). The NDBC file of 21415 and NCEI's deployment list are added here: the first to check the conversion at the second station, the second for the station positions and depths.

**Conversion (ADR 007).** Seven files are committed byte for byte. The ETOPO response is converted once, outside the build, by `tools/datasets/etopo_ascii_to_npy.py` (NumPy only): it refuses an input whose sha256 is not the one above, and since a generated response is not guaranteed to stay byte-identical, it also pins the sha256 of the parsed float32 array (`8bd4f1e5c02b1a39c7706cf6b1c76771c4bbde2716310e55af0f743978bb719d`; `--allow-other-input` accepts a response with another checksum only if its array equals that one). It checks the response's latitude and longitude maps against the cell centres of the crop, rejects a missing value or the fill value −99999, rounds every value to the metre (a change of at most 0.5 m), and writes `etopo2022_60s_bed_35N60N_140E180E_stride4.npy`, int16, 375 × 600, 450,128 B, sha256 `27bf15f585aa7289f2eb90624628f4d30601f49a0be4f2dd6c730b9fae5ead93`. `tools/datasets/README.md` says how to repeat it. A full-resolution crop to average instead of decimate was tried as an OPeNDAP binary request and the server returned an error; the decimated crop is what the research inspected.

Readers of the sample: `pbc.data.reference.kamchatka_tsunami.read_ncei`, `read_ndbc`, `read_stations`, `read_fsp`, `read_disp`, `read_etopo` (NumPy and the standard library's gzip).

## Schema, units, cadence, masks, coverage

| Item | What the source documents | What this dossier established |
|---|---|---|
| NCEI event file | nothing in the directory (no README); the directory names the files `_meter` | 11 whitespace-separated columns: day of year (decimal), year, month, day, hour, minute, second, height (m), tide (m), residual (m), and a column 0.000 throughout; residual = height − tide to 2 × 10⁻⁵ m; day of year consistent with the date; 1,697 rows (21416), 1,761 (21415) |
| NCEI heights | "meter" | **0.670 times NDBC's heights**: see "The double conversion" |
| NCEI coverage | the names say 2025-07-27 to 08-03 | 2025-07-27 00:00 to 07-31 12:00 UTC at both stations |
| NCEI cadence | none | 15 min in normal mode; in event mode 1 min and bursts of 15 s. 21416: 1-min records from 22:00 UTC (−84 min) to +20.6 h, 15-s records from +1.9 to +5.4 min and near +17.4 h. 21415: 15-min records until +36 min, then 1 min to +33.6 h, 15-s records from +103 to +107 min and near +29.9 h |
| NCEI duplicates | none | 13 (21416) and 18 (21415) timestamps occur twice with different values (up to 0.27 m apart on the corrected scale, at 21416 during the shaking); NDBC has two records of two types (15-min and 1-min, or 1-min and 15-s) at each of them; the ratio below is not precise enough (2 cm on the column) to tell which NCEI value comes from which. All rows are kept; neither peak is at a duplicated time |
| NDBC annual file | header `#YY MM DD hh mm ss T HEIGHT`, units line `m`; T is the record type (1: 15-min, 2: 1-min, 3: 15-s) | the whole of 2025: 41,133 rows at 21416 (35,040 / 5,833 / 260 of types 1 / 2 / 3), 38,784 at 21415 (35,040 / 3,600 / 144); 9999.000 marks a missing height (7,064 and 1,803 rows; 108 and 100 between 07-27 and 08-04) |
| NDBC units | m | the height of the water column: its mean over 07-27 to 07-31 is 5788.70 m at 21416 (station depth 5788 m) and 4720.38 m at 21415 (4720 m) |
| Deployment list | position (decimal and DMS) and depth of 26 deployments | UTF-8 (degree signs); 21416 deployment 20250711to20250731 at 48.1258N 163.3755E, 5788 m; 21415 deployment 20240615to20250731 at 50.1255N 171.8737E, 4720 m. The DMS latitude of 46403 reads 2° instead of 52°; that station is not used |
| `.fsp` | the header and column names (`LAT LON X==EW Y==NS Z SLIP RAKE TRUP RISE SF_MOMENT`; X, Y, Z in km, SLIP in m) | three segments, 620 km along strike, 60, 60 and 30 km down-dip, dips 6.5°, 17°, 28°, 186 + 186 + 93 subfaults of 20 × 10 km; SF_MOMENT in N m (their sum 2.2489 × 10²² N m equals the header's Mo 2.2490 × 10²²); maximum slip 39.34 m; subfault depths 7.9 to 44.0 km |
| `.disp` | the header line (east, north, vertical displacement in m) | 1,600 rows, a 40 × 40 grid, longitude fastest, 154.38 to 166.14 E and 48.91 to 56.10 N; steps vary slightly (0.3003 to 0.3017° in longitude, 0.1842 to 0.1845° in latitude); vertical +8.11 m to −4.40 m; up to 1.13 m at its edges |
| ETOPO crop | `z` in metres, positive up, EGM2008; WGS 84; cell-centred (`node_offset 1`) | 375 × 600 cells of 4′ (every fourth 60″ cell), centres 35.0083 to 59.9417 N, 140.0083 to 179.9417 E; −9,573 to +3,808 m; 91.9 % below sea level; no fill value |

The parsing test `tests/unit/test_data_kamchatka_tsunami.py::test_kamchatka_tsunami_sample_parses` asserts the columns, shapes, coverage, cadences, duplicates, record types, missing values, the NDBC mean against the station depth, the fault's segments, and the grids; `test_the_samples_are_the_downloads_and_the_conversion_output` asserts every checksum.

## Artifact labels

| Artifact | Type |
|---|---|
| NCEI event files (height, tide fit, residual) | `processed-measured` (pressure converted to height, the tide fitted and removed by NCEI) |
| NDBC annual files | `processed-measured` (pressure converted to height by NDBC) |
| NCEI's deployment list | `processed-measured` (the surveyed positions and depths) |
| `complete_inversion.fsp`, `surface_deformation.disp` | `modelled-reference` (an inversion of seismic, GNSS and InSAR data and its forward model) |
| the ETOPO crop | `processed-measured` (a gridded compilation of surveys) |
| corrected residuals, conversion ratios, peaks | `processed-measured`, computed here |
| √(gh) arrival times | `modelled-reference`, computed here |

The finite fault's data table (`% Data :` of the `.fsp` header) lists 58 body waves, 58 surface waves, 3 GNSS stations and 1,302 InSAR points, and **0 DART records**: the DART records were not used to make it, so they remain an independent check of a model built from it. The NOAA NCTR tsunami inversion, which is fitted to the same DARTs, is not used for that reason ([the research](spike-candidates-2026-11-08.md)).

## The double conversion

NCEI's event files are in "meters", but their heights are 3878 m at a station 5788 m deep. Two tests on the files:

- **Against the station depth.** The mean NCEI height is 0.67008 (21416) and 0.67005 (21415) times the station depth of NCEI's own list.
- **Against NDBC.** Every NCEI timestamp is also in NDBC's file (1,697 at 21416, 1,761 at 21415). NCEI height / NDBC height is 0.6700026 (median, 21416) and 0.6700025 (21415), and within 3.6 × 10⁻⁶ of 0.670 at every timestamp (at a duplicated time, the nearer of NDBC's two records). The deviation, at most 2 cm on the scale of the water column, drifts smoothly over the five days; the tide fit absorbs a drift that slow, and dividing by 0.670 rather than by the ratio changes the corrected residual by less than 4 × 10⁻⁶ of itself.

0.670 is NDBC's factor of 670 mm of sea water per psia. NDBC's heights are already in metres; NCEI's files apply the factor a second time. The analysis divides NCEI's residual by 0.670 (`NDBC_FACTOR`), so a page states: *heights from NCEI's event files divided by 0.670, because they carry NDBC's pressure-to-height factor twice; NDBC's own files confirm it*. The other way, NDBC's heights with an own tide fit, gives the same sea level; the research found its tide agreeing with NCEI's to 1.8 cm rms and is not repeated here. Notifying NCEI is the owner's action.

## Reference figure

```
uv run python -m pbc.data.reference kamchatka-2025-tsunami-inputs --out kamchatka.png
```

The code is `src/pbc/data/reference/kamchatka_tsunami.py`. **Status label: processed.** Panels: (a) the ETOPO crop around the source with the USGS vertical deformation as contours (uplift solid, subsidence dashed), the epicentre and the two stations; (b) NCEI height / NDBC height − 0.670 at every matched timestamp of both stations; (c, d) the corrected residual at 21416 and 21415 from −30 to +180 min, with the interval of seafloor shaking at 21416 shaded and the two √(gh) arrival times as vertical lines (dashed: from the nearest uplift of at least 1 m; dotted: from the epicentre), labelled `[simulated]` and drawn apart from the record.

**The chain, each step in the code:**

1. **Time.** Minutes after the ComCat origin, 2025-07-29 23:24:52.483 UTC (event page of us6000qw60, read 2026-11-09); the `.fsp` header gives 23:24:50, 2.5 s earlier, and an epicentre 3.9 km from ComCat's 52.4948N 160.2395E.
2. **Correction.** NCEI's residual divided by 0.670.
3. **Shaking.** At 21416 the residual from +1 to +26 min reaches 0.62 m (corrected scale), its sign alternating between consecutive samples: the sensor records the motion of the sea floor (seismic waves), not the sea surface. The peak is searched after +26 min.
4. **Peak and arrival.** The largest corrected residual from +26 to +240 min; the time at which the residual last rises through half that peak before it, interpolated between samples (the last crossing: at 21415 a single sample of 0.235 m at +50.1 min, beside a duplicate of 0.047 m at the same time, is not the arrival).
5. **Arrival estimates.** The time of a long wave, speed √(g h) with h the ETOPO depth of the nearest 4′ cell, integrated every 1 km along the great circle (radius 6371 km); a path through a cell shallower than 1 m is blocked. From the epicentre, and the shortest over the points of the `.disp` grid with uplift of at least 0.5, 1 or 2 m. `test_the_travel_time_is_exact_over_a_flat_sea` checks the integration against the exact value over a uniform depth.

**Caption.** *The inputs of the Kamchatka tsunami of 29 July 2025. Left above: the bathymetry with the uplift and subsidence of the USGS fault model and the two deep-ocean stations. Right above: NCEI's heights are NDBC's heights times 0.670 at every common timestamp, a conversion applied twice; the records below are divided by it. Below: sea level minus tide at DART 21416 and 21415. The tsunami reaches 0.82 m at 21416 32 minutes after the earthquake and 0.35 m at 21415 after 69 minutes; before it, 21416 records the shaking of the sea floor, not the sea. The dashed and dotted lines are long-wave travel times from the nearest uplift and from the epicentre over the ETOPO depths: each record's rise falls between them, so the windows hold the arrivals. No uncertainty per sample is published, so none is drawn; the residual's rms over the day before is 0.020 m at 21416 and 0.007 m at 21415. No model of the wave is compared with the records here.*

| Quantity | 21416 | 21415 |
|---|---|---|
| NCEI / NDBC height, median | 0.6700026 | 0.6700025 |
| largest deviation from 0.670 | 3.5 × 10⁻⁶ | 2.8 × 10⁻⁶ |
| NCEI mean height / station depth | 0.67008 | 0.67005 |
| rms of the corrected residual, the day before | 0.020 m | 0.007 m |
| largest excursion, +1 to +26 min (shaking) | 0.62 m | (15-min records only) |
| peak | **0.818 m at +32.1 min** | **0.352 m at +69.1 min** |
| trough | −0.508 m at +40.1 min | −0.242 m at +112.1 min |
| half-peak crossing | +29.8 min | +66.5 min |
| √(gh) from the nearest uplift ≥ 0.5 / 1 / 2 m | 26.6 / 26.6 / 27.2 min | 60.7 / 60.8 / 61.9 min |
| √(gh) from the epicentre | 40.0 min over 534.3 km | 69.1 min over 849.4 km |

The research of 2026-11-08 found the same peaks (0.818 m at +32.1 min, 0.352 m at +69.1 min) and 40.1 min from the epicentre to 21416. Its 65.8 min for 21415 was an average-depth estimate over 849.4 km; the path-integrated value here is 69.1 min. NCTR's reported 0.85 m at 21416 (as the research recorded) is close to the corrected peak and far from the uncorrected 0.55 m.

| The finite fault | Value |
|---|---|
| Mw from the summed subfault moments | 8.835 (header 8.8347) |
| moment | 2.2489 × 10²² N m |
| segments | 3, 620 km long, 150 km down-dip in all; strike 217° |
| maximum slip | 39.3 m (near 50.2N 157.3E) |
| vertical deformation | +8.11 m (50.39N 159.20E) to −4.40 m (50.39N 157.09E) |
| grid points with uplift ≥ 1 m / subsidence ≥ 1 m | 75 / 39 of 1,600 |

Asserted by `tests/unit/test_data_kamchatka_tsunami.py`: the ratios, the peaks and troughs, the crossings, the noise floor, the shaking, the distances and travel times, their order (nearest-uplift time < half-peak crossing < peak ≤ epicentre time), the moment magnitude, the slip and deformation extremes, the edge values, and the origin-time difference.

## Uncertainty and calibration

**DART.** Neither NCEI nor NDBC publishes an uncertainty per sample or a calibration record of the pressure sensors with these files. What the data show:

- **Resolution and noise.** NDBC heights are given to 1 mm; NCEI's to 0.01 mm on its scaled values. The rms of the corrected residual over the day before the origin, 0.020 m at 21416 and 0.007 m at 21415, is the floor of the tide fit plus noise at 15-minute cadence; it is the scale below which a feature of the record is not significant without further work.
- **The factor.** 0.670 within 3.6 × 10⁻⁶: no uncertainty that matters for sea level.
- **Times.** To the sample: 1 min in event mode (15 s in the bursts). The origin time is ComCat's; its difference from the fault model's, 2.5 s, is negligible here.
- **Shaking.** At 21416 the first 26 minutes are seafloor motion, and their tail may overlap the first rise of the tsunami (the nearest-uplift estimate is +26.6 min). A lab must not read the record before +26 min as sea level.
- **Duplicates.** At a duplicated timestamp the two values come from two record types of NDBC that disagree, by up to 0.27 m during the shaking and up to 0.23 m at 21415 at +35 and +50 min (where the 15-minute record differs from the 1-minute one). Neither peak is affected; a lab that resamples the record must decide which record type it keeps and say so.

**Finite fault.** The product states no uncertainty of slip or deformation; it is one model of several possible (the inversion's data and velocity model are in the `.fsp` header). Its `.disp` grid is 40 × 40 (cells of about 20 km by 20 km), does not reach zero at its edges (up to 1.13 m), and so does not hold the whole deformation, as the research found at the southern tip. Phase 2 must treat it as an assumed initial displacement, state that it is coarse and truncated, and say how a different source would change the result (the capstone's "source uncertainty explained").

**Bathymetry.** ETOPO 2022 gives no uncertainty per cell in this file. The crop takes every fourth cell (4′, about 7.4 km × 4.6 km at 52N): features narrower than that are aliased, not averaged. The nearest cell to 21416 is 5,602 m deep against the station's 5,788 m, and to 21415 4,835 m against 4,720 m (3 % and 2 %). A travel time scales with 1/√h, so a 3 % depth error is 1.5 % of the time, under a minute here; the arrival estimates above vary by about a minute with the uplift level chosen, which is the larger uncertainty.

**The arrival estimates.** Straight great-circle paths, linear non-dispersive long waves, and the nearest cell's depth: they bound the window, they are not a prediction of the waveform. The order nearest-uplift time < rise < peak ≤ epicentre time holds at both stations; at 21415 the peak and the epicentre time coincide (69.1 min), which is a coincidence of this check, not an agreement claimed.

## What the data do not give

- **No validation yet.** This dossier establishes the inputs and their windows. It makes no measured-versus-model comparison and claims no agreement with observations; that is phase 2, after the owner's word, under the lab rule.
- **No uncertainty per sample** of the DART heights, and no calibration record of the sensors.
- **No complete source.** The `.disp` grid is truncated and coarse; the `.fsp` subfaults would allow phase 2 to compute its own deformation (Okada) if the capstone needs it, which is phase 2's choice.
- **No days after 07-31 12:00** in NCEI's files; NDBC's annual files cover them, uncorrected for tides.
- **No full-resolution bathymetry** in the sample: 4′ decimated. The full 60″ grid is on the same server, but a request for the whole crop at full resolution failed here; the card's download is the decimated one.

## Rights

| Question | Answer | Source |
|---|---|---|
| Local download | permitted | US-government works, not subject to copyright: 17 U.S.C. 105 (https://www.copyright.gov/title17/92chap1.html#105). DART: NDBC's disclaimer (https://www.ndbc.noaa.gov/disclaimer.shtml) redirects to https://www.weather.gov/disclaimer, read 2026-11-09: "The information on National Weather Service (NWS) Web pages are in the public domain, unless specifically noted otherwise"; NCEI's collection metadata (doi 10.7289/V5F18WNS, https://www.ncei.noaa.gov/access/metadata/landing-page/bin/iso?id=gov.noaa.ngdc:G10068): "Access to this dataset is unrestricted". USGS: https://www.usgs.gov/information-policies-and-instructions/copyrights-and-credits: "USGS-authored or produced data and information are considered to be in the U.S. Public Domain". ETOPO 2022: its metadata (doi 10.25921/fd45-gt74): "NOAA waives any potential copyright and related rights in these data worldwide through the Creative Commons Zero 1.0 Universal Public Domain Dedication (CC0-1.0)" |
| Redistribution of subsets | permitted | the same terms; the NWS page: "may be used without charge for any lawful purpose" so long as the material is not claimed as one's own, no NOAA endorsement is implied, and modified content is not presented as official government material |
| Publication of figures and derivatives | permitted | the same terms; 17 U.S.C. 403, quoted by the NWS page, asks a work consisting predominantly of NWS material to identify it and state that it is not subject to copyright: the card's `attribution` does so |
| Modification and attribution | permitted, with the citations and the NWS conditions | NCEI's metadata give the citations (DART: "National Oceanic and Atmospheric Administration (2005): Deep-Ocean Assessment and Reporting of Tsunamis (DART(R)) ... doi:10.7289/V5F18WNS"; ETOPO: "NOAA National Centers for Environmental Information. 2022: ETOPO 2022 15 Arc-Second Global Relief Model ... doi 10.25921/fd45-gt74"); the USGS page asks for credit; the card's `attribution` names every source and the changes (÷ 0.670, decimation, rounding) |

The card records the licence as `equivalent-permission` (ADR 007 decision 4), as the TESS card does for NASA's public-domain data: public domain and CC0 grant all four rights that decision 4 asks of CC0 or CC BY. The NCEI collection metadata name no licence; the public-domain status rests on 17 U.S.C. 105 for a NOAA work, which the NWS page states for NDBC's data and ETOPO's metadata states for NCEI's. ETOPO's ocean layer is GEBCO_2022, as the research recorded; ETOPO's metadata name no third-party clause and waive the rights in the whole product.

## Size, runtime, payload

Sample 1,227,697 bytes in eight files (caps: 2 MB per file, 8 MB per dataset; the largest file is the 450 KB array). The reference figure takes about 1.8 s with the interpreter start (reading 0.16 s, the analysis 0.09 s) and about 150 MB peak memory; the PNG is about 590 KB at 150 dpi. A lesson page that reads the sample and draws this figure stays inside the 30 s warning, the 60 s limit, and the 3 MB payload; the files are read at build time and not shipped. Phase 2's propagation runs on this grid; its cost is phase 2's estimate, and the roadmap keeps heavier reruns outside `verify.conf`. The learner's download is the eight files of the card (`./scripts/fetch-data.sh kamchatka-2025-tsunami-inputs`, checked against the card's digests), and the conversion repeats the array byte for byte. CI reads only the committed files.

## The requirements of ADR 007 and where they are met

| Requirement | Evidence |
|---|---|
| 1. An actual small file inspected, checksum, size, version | "The files inspected": every file downloaded, sized, and checksummed; the product version and access date on the card |
| 2. Schema, units, calibration, cadence, masks, coverage | "Schema, units, cadence, masks, coverage" (the double conversion and the end date established on the files); "The double conversion"; the parsing test |
| 3. Every artifact labelled, measurement apart from the model | "Artifact labels"; the figure labels the arrival times `[simulated]` and draws them as vertical lines apart from the record; the fault model is labelled as a model |
| 4. Reproducible reference figure from source-controlled code | `src/pbc/data/reference/kamchatka_tsunami.py`, from the committed sample; `tests/unit/test_data_plotting.py` checks its status and conventions |
| 5. Rights, four answers with their source | "Rights"; the card's `rights` |
| 6. Download, build time, payload | "Size, runtime, payload" |
| 7. Uncertainty and calibration | "Uncertainty and calibration": the noise floor, the factor, the shaking, the duplicates, the fault's coarseness and truncation, the decimated bathymetry and its depth error |
| 8. This dossier with the decision | this file |

## Open items

- Phase 2 (the simulation and benchmark core, then the gated comparison) starts only when the owner says so (Issue #444).
- Notifying NCEI of the ×0.670 double conversion in its event files is the owner's action.
- Further stations of the event directory (21419, 21413, 46402, and others) were not inspected; a comparison that uses them needs their own check of the factor.
