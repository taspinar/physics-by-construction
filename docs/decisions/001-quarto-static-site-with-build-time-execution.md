# ADR 001: Quarto as the site generator, with build-time execution and MathML equations

## Status

Accepted with the approval of the project bootstrap planning.

Date: 2026-10-06

## Context

The requirements fix the product shape: a static site on GitHub Pages whose
lessons combine prose, equations, Python code, figures, exercises, and Lean
proofs. Several requirements constrain the site technology directly:

- Code shown on the site is the code CI ran, and figures on the site are the
  figures that code produced.
- All text, code, equations, and static figures work without JavaScript, and
  equations use accessible markup.
- WCAG 2.1 AA, responsive layout, no third-party CDNs, deterministic output.
- Lean proofs are displayed with syntax highlighting.
- JavaScript is used only for optional interactive visualizations.
- Toolchains are pinned and one local command reproduces the site.
- The maintainer works mainly in Python and authors with AI agents, so the
  lesson format should be plain text and widely documented.

The generator is the hardest decision to reverse: every lesson is written in
its format.

## Decision

Use **Quarto** to build the site from a project in `site/`.

- Lessons are `.qmd` files: Markdown with YAML front matter and executable
  Python cells. Quarto executes every lesson in the locked Python environment
  on every build. Execution results are not cached in the repository (no
  `freeze`), see ADR 002.
- Equations are rendered at build time with `html-math-method: mathml`, so
  they are native MathML: no JavaScript and readable by assistive technology.
  A math font is self-hosted. An equation Pandoc cannot convert fails the
  build.
- Code is highlighted at build time. Lean highlighting comes from a KDE syntax
  definition vendored in the repository and registered through Quarto's
  `syntax-definitions` option, because Pandoc has none built in.
- Interactive visualizations are dependency-free JavaScript ES modules served
  from the site itself. Each one enhances a static figure that is already in
  the page. There is no Node toolchain and no bundler in the MVP.
- The Quarto version is pinned through the `quarto-cli` Python package in
  `uv.lock`, so the Python lock file is the single place that pins the site
  toolchain.
- Quarto features that need JavaScript to reveal content (tabsets, collapsible
  callouts) are not used for lesson content. Solutions use the HTML `details`
  element. Client-side MathJax and KaTeX are not used.

## Alternatives considered

**Astro (or Astro Starlight) with a custom Python build step.** Strongest on
the front end: no JavaScript by default, validated content schemas, built-in
Lean highlighting, build-time KaTeX. Rejected because it executes nothing: the
project would have to build and maintain its own bridge for executing lesson
code, capturing outputs and figures, and inlining computed values, which is
the core of the "code CI ran" requirement. It also adds Node as a third pinned
toolchain and lacks scholarly features (cross-references, citations, theorem
and exercise environments) that Quarto provides.

**Sphinx with MyST-NB (the Jupyter Book 1 stack).** Python-native, executes
content, and Pygments highlights Lean. Rejected because equations depend on
client-side MathJax by default; build-time rendering needs either image output
with poor accessibility or a Node-based prerender step.

**Jupyter Book 2 (MyST Markdown engine).** Rejected for the MVP because its
static HTML output relies on client-side hydration, and its execution and
theming story is still changing quickly.

**MkDocs Material.** Good reading experience, but it does not execute code and
its equation rendering is client-side.

**Verso (Lean's documentation tool).** Best possible Lean rendering, with
elaborated hovers. Rejected because the site is mostly Python and prose, and
Verso does not execute Python or produce figures.

**A hand-written generator.** Rejected: the largest maintenance cost for no
requirement that the options above cannot meet.

## Consequences

Positive:

- Executed cells make "the code shown is the code that ran" the default
  behaviour of the format, not an extra mechanism.
- Two toolchains to pin (Python including Quarto, and Lean), installed
  through uv and elan. The complete local prerequisites, which also cover the
  verification tooling, are listed in the architecture under "Toolchains and
  pinning".
- Equations are accessible and need no script.
- Cross-references, citations, and exercise and theorem environments are
  available for scholarly content.

Negative, with mitigations:

- Pandoc converts a subset of LaTeX to MathML, and MathML rendering is less
  polished than KaTeX in some browsers. Lessons stay within the supported
  subset; the build fails on unconvertible equations; F01 verifies rendering
  in current browsers.
- The Lean syntax definition is vendored and must be maintained by the
  project. Highlighting is token colouring only.
- Quarto's default theme uses JavaScript for the mobile navigation toggle.
  Content stays readable without JavaScript, and previous, next, and learning
  path links must work without it (checked in F01 and F03).
- The learning path page and lesson headers need custom templates or a
  pre-render script, because Quarto does not validate custom front matter. A
  separate check validates lesson metadata (F02, F03).
- Some Quarto outputs may embed build-time values. F01 must configure or
  normalise them for deterministic output.
- `quarto-cli` downloads the Quarto binary at install time, so the binary is
  pinned by version, not by a hash in `uv.lock`.

Revisit this decision if build-time MathML proves inadequate for lesson
equations, or if the later adaptive learning phase needs more client-side
structure than self-hosted ES modules can reasonably provide.
