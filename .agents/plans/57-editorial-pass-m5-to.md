# Plan: F30 editorial pass, M5 pilot first (Issue #57)

Source: Issue #57, docs/roadmap.md F30, ADR 009, docs/authoring.md "Lesson format 2".

## Scope of this session
M5 only. Acceptance criterion 6 gates M6 to M8 on M5's reviews ("before M6's
Issue is created"), so M6, M7, and M8 follow in their own Issue(s) after the
reviews of M5 are triaged; the human chooses one Issue or three.

## Audit template (reused for M6 to M8)
Per lesson list, with an example each: unmotivated equations, missing
assumptions, unsupported assertions, terse explanations, hand-typed numbers,
descriptive captions, console blocks, missing limits, opening without a
physical question. Record on the Issue before the rewrite.

## Research log format
Per concept: need, candidates opened (URL, section, date), what was checked
(variant, notation, order), accepted or rejected with the reason; the result
goes into site/references.yaml (`statement`, `alternatives`).

## M5 audit (to post on Issue #57)
- Unmotivated: the weights 1, 2, 2, 1 of RK4 (stated, no reason); the complex
  state u = v + i omega x (no reason); "as substituting confirms" for the two
  modified energies (no substitution shown); the stability limit z < 2 of the
  symplectic methods (stated, not derived); |R(iz)|^2 stated without the algebra.
- Missing assumptions: that RK4 is the fixed-step classical method (SciPy's
  adaptive RK45 is a different stepper); "10^-9 m, six orders above round-off"
  asserted by hand.
- Unsupported / terse: "Further reading" names two books without section,
  link, or reason; "a few per cent", "ten times", "about two hundred calls",
  "more than eighty thousand" typed by hand in prose; alt texts hold computed
  values (0.86, 1.19, 0.98, 0.995).
- Hand-typed numbers: about 30 in prose and alt text, see the check.
- Descriptive captions: all four figure captions only name the content.
- Console blocks: nine printed numeric blocks (INTEGRATORS listing, four
  worked-example blocks, three tables of the explorer, solutions).
- No Limits section, no self-check, no figure status, no claim labels, no
  opening physical question.

## Source research (2026-10-10)
Chosen (2): Brorson, LibreTexts chapter 7 (velocity-first symplectic Euler,
oscillator, phase-space area); MIT NMM 2023 "Verlet Integration" (velocity
Verlet from two half steps of semi-implicit Euler).
Rejected: Hairer-Norsett-Wanner and Hairer-Lubich-Wanner books (no public
section; Geneva record is an unspecified extract, all rights reserved);
Lethbridge slides, Helsinki lecture 4 (PDF text not extractable); KSU Class 6
(velocity-first rule and fixed-step RK4 confirmed, but no derivation, so adds
nothing); Wikipedia Verlet (same algorithm, says it assumes position-only
forces; no derivation from symplectic Euler). RK4: no link, the lesson
contains the method; the KSU page confirmed the classical fixed-step form.
Caveat for the reviewers: the passages were read through the fetch tool's
summaries, not by a person; Brorson's alternative-ordering equation has a
typo on the page, and its stability statement (|g| = 1 for |h omega| < 2) is
from that summary.

## Guide gap found (fixed in docs/authoring.md)
A method name with a digit ("Runge-Kutta 4") is a hand-typed number to the
check; the guide now says how to write it.

## Not done / decisions for the human
- M6 to M8: three separate Issues after the M5 pilot, decided by the project
  owner on 2026-10-10; Issue #57 covers the pilot only.
- The audit was posted on Issue #57 on 2026-10-10, with the owner's check of
  the two new references against their pages.
- Numerical results unchanged: the output tables carry the baseline values;
  band edges and the 20-period RK4 end value are shown at the old precision
  or in a different table form.
