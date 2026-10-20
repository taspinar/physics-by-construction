# Self-hosted fonts

Third-party files, served from the site itself so that no page requests a
font from another origin. The faces and their roles are in
`docs/atelier.md` ("Type").

| File | Font | Version | Licence | SHA-256 |
|---|---|---|---|---|
| `STIXTwoMath-Regular.woff2` | STIX Two Math | 2.13 b171 | SIL Open Font License 1.1 (`OFL.txt`) | `094191335def3f0452c81ec0713cfc2f29bb6af8cecbf79b60881fbf2db97562` |
| `STIXTwoText-Regular.subset.woff2` | STIX Two Text Regular, subset | 2.13 b171 | SIL Open Font License 1.1 (`OFL.txt`) | `710684a2462ec16d72b3bd0d63dd9a79aaf5ff58543660cdc3a38f4f108d56fd` |
| `STIXTwoText-Italic.subset.woff2` | STIX Two Text Italic, subset | 2.13 b171 | SIL Open Font License 1.1 (`OFL.txt`) | `a46cca704183fa46b0c17ceffdda69ad27cb2640095649ac55aecf771795f6c5` |
| `STIXTwoText-SemiBold.subset.woff2` | STIX Two Text SemiBold, subset | 2.13 b171 | SIL Open Font License 1.1 (`OFL.txt`) | `023ec480d28e2443c6292832df446073b1d63802ee2716547159b77e2f06c945` |
| `IBMPlexMono-Regular.woff2` | IBM Plex Mono Regular | 1.1.0 | SIL Open Font License 1.1 (`OFL-IBMPlex.txt`) | `49ce58b41a0e1cb921c0f58d9a5b8b96a2cc21437c7066f3ba4f24873076d131` |

**STIX Two Math and STIX Two Text.** Source: <https://github.com/stipub/stixfonts>,
tag `v2.13b171`, files `fonts/static_otf_woff2/STIXTwoMath-Regular.woff2`
(unmodified) and `fonts/static_otf_woff2/STIXTwoText-<Style>.woff2` (SHA-256
of the upstream files: Regular
`d709865ddc3a546589dd9e83d8157e0a104d1ac6870763331badaa74014db563`, Italic
`082f29daf0efdb1251fece727514b5bd9a12cf32af22990cf50c0c70ab6c2ddb`,
SemiBold `90af809bebec509532250f34b3f37125c52e743bd8f3fa1d856ee0e9e5d4c155`).
`OFL.txt` is the licence of that tag; its only Reserved Font Name is
"TM Math", so the subsets keep their names.

The text faces are subset to Basic Latin, Latin-1, Latin Extended-A and
Additional, the combining marks, Greek, General Punctuation, the super- and
subscripts, the euro sign, the letterlike symbols, the arrows, and the
mathematical operators, with the numeral features the tables use. The
command, run once from the repository root with each upstream file
downloaded into an empty directory `$UPSTREAM` (fontTools is in the locked
environment; its WOFF2 writer needs `brotli`, taken for this command only):

```sh
for style in Regular Italic SemiBold; do
  uv run --with brotli pyftsubset "$UPSTREAM/STIXTwoText-$style.woff2" \
    --unicodes="U+0020-007E,U+00A0-00FF,U+0100-017F,U+0300-036F,U+0370-03FF,U+1E00-1EFF,U+2000-206F,U+2070-209F,U+20AC,U+2100-214F,U+2190-21FF,U+2200-22FF,U+FFFD" \
    --layout-features+=tnum,lnum,pnum,onum,case --flavor=woff2 \
    --output-file="site/assets/fonts/STIXTwoText-$style.subset.woff2"
done
```

The output is the same file on every run (fontTools 4.66.1).

**IBM Plex Mono.** Source: <https://github.com/IBM/plex>, tag
`@ibm/plex-mono@1.1.0`, files
`packages/plex-mono/fonts/complete/woff2/IBMPlexMono-Regular.woff2` and
`packages/plex-mono/LICENSE.txt` (here `OFL-IBMPlex.txt`), unmodified. Its
licence reserves the name "Plex", so the file is served whole (45 kB) and
never subset.

To update a font, replace the file from a newer tag (run the subset command
again for a text face) and update the version and checksums here.
