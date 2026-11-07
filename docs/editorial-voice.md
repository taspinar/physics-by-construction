# Editorial voice guide

How the prose of a lesson should sound, and how to tell whether a draft does.
It is for the author of a lesson, a reviewer, and an agent drafting a lesson.
`docs/authoring.md` says what a lesson must contain and what the checks
enforce; this guide says how the words around that content should read. The
guide is a draft until F116 integrates its principles into the authoring
guide, the lesson template, and the review rubric, after the pilot of F115 is
approved by the human.

## Objective and non-goals

The objective is better teaching: a lesson that reads like a knowledgeable
person explaining something they find interesting, to a reader they respect,
without giving up any of the rigour of a textbook or any verification of this
project. Three registers are combined:

- **The personal technical blog:** it starts from a question the reader
  might have, says why the topic is worth the effort, and talks to the reader.
- **The university textbook:** every statement is precise, scoped, and
  derived or sourced, and the order of ideas is the order of dependence.
- **This project's standard:** every number, figure, and claim is produced or
  checked by the build, and what is not shown is said so.

Requirements decision 32 (`docs/PROJECT_REQUIREMENTS.md`) and its non-goals
bind this guide:

- The voice is not a uniform register. No lesson is rewritten in a
  conversational or informal tone because the guide exists.
- No jokes or anecdotes are added as a rule, and none are added to fill a
  gap. One that earns its place by teaching is fine.
- No lesson has an identical narrative structure, and this guide is not a
  template. Structures and narratives vary by subject: a lesson about a
  proof, a lesson about a random process, and a lesson about a numerical
  instability do not open, build, or conclude alike, and no outline in this
  guide is to be filled in.
- No relaxation of any scientific standard, and no part of the verification
  pipeline is replaced by an editorial judgement.
- No optimisation against AI-content detectors. A passage is not rewritten
  because it "sounds like a model" but because it teaches worse than a
  version that is better; the test is the reader, not a classifier.
- Nothing scientific changes silently for style (see "What never changes").

## What never changes

A style edit touches sentences. These stay exactly as they are, and a change
to any of them is a different change with its own review:

- **Sections and identifiers.** The format 2 sections of `docs/authoring.md`
  (assumptions, explanation, code, worked examples, exercises, limits, the
  self-check, reproduce this) with their identifiers and order. A conclusion
  or a transition is written inside an existing section; no section is added
  for style.
- **Claims.** The text, the type, the scope, and the evidence of every claim
  label. A rewrite that makes a claim stronger, weaker, or wider than its
  label is a scientific change.
- **Numbers.** Every number comes from an executed cell. A rewrite keeps the
  cell and moves only the words around it; no number is typed by hand.
- **Figures.** The code, the `fig-status`, the alt text's facts, and the
  caption's conclusion. A caption may be made clearer; it may not claim more.
- **References.** The register of references and its entries; "Go deeper"
  keys; no URL typed in a lesson.
- **Checks.** Every check of `docs/authoring.md` passes after the edit, and
  no check is weakened to make a rewrite pass. The author of the edit reads
  the diff for words that moved a claim: *always*, *proves*, *shows*,
  *exactly*, *for every*.

## The principles by part of a lesson

Each part below has the principle, the typical fault found in the lessons,
and two before-and-after examples. The "before" is quoted from the named
lesson and section (some shortened). The "after" is written for this guide
only and is **not applied** to the lesson; it carries no number or claim of
its own and exists to show the move. Lessons are named by title and section.

### 1. Openings

**Principle.** Open with the question, in the reader's terms: what is
puzzling, what goes wrong, what we want to know. Then, in one short
paragraph, say what the lesson will give the reader to answer it. The
technique, the method's name, and the list of what the lesson "derives,
shows, and measures" come after the question has been felt, and only as far as
the reader needs to decide to continue.

The openings of the existing lessons are the strongest part of them: all ten
audited below start from a question (the ink in water, the plucked string, the
thrown ball). The fault is in the second and third paragraphs, which turn into
a table of contents.

**Example 1.1** — *Newton's laws*, introduction, second paragraph.

Before:

> This lesson builds that program in three parts that the rest of the course
> keeps: force models as plain functions, Newton's second law as the function
> that turns their sum into an acceleration, and a stepper with a fixed
> signature, so that a later lesson can swap explicit Euler for a better
> method without touching anything else.

After:

> Three decisions are made here, and the rest of the course lives with them.
> A force is just a function of the state. Newton's law is the one function
> that turns the forces into an acceleration. And the stepper has a fixed
> signature, so that when explicit Euler turns out to be not good enough,
> a better method can take its place and nothing else in the program has to
> be touched.

The after keeps every fact and says why each is there; the reader learns the
reason for the structure instead of its list.

**Example 1.2** — *The wave equation*, introduction, second paragraph.

Before:

> The lesson derives the **wave equation** for a string, turns it into a
> program with centred differences, and then checks the program in the only
> way a numerical method can be trusted: against a case whose exact solution
> is known. Two checks come out of that.

After:

> A scheme can follow the travelling bump faithfully and still be a trap: change
> the time step a little, and the same program fills the string with a zigzag
> that grows until nothing else is visible. We derive the equation, turn it into a program,
> and then find out exactly where the program stops being trustworthy, which
> turns out to depend on the grid in a way we can predict.

The after replaces the method list with the stake, and gives the reader a
reason to want the checks that the before only names.

### 2. Intuition

**Principle.** Before an equation, give the reader something to hold: the
picture, the physical situation, the one idea the equation will write down.
After the equation, say in a sentence what it says. Intuition is not an
analogy added for charm; it is the shortest honest route from what the reader
knows to what the equation states.

**Example 2.1** — *The harmonic oscillator*, "A mass on a spring".

Before:

> A particle of mass $m$ on a spring with the spring constant $k$ feels the
> force $F = -k\,x$, so Newton's second law reads …

After:

> Pull a mass on a spring aside and let go. The further you pulled, the harder
> the spring pulls back, so it overshoots the rest position, is pulled back,
> overshoots again. That one sentence, a pull back in proportion to the
> displacement, is the whole physics; the force $F = -k\,x$ is that sentence
> written down, and Newton's second law then reads …

**Example 2.2** — *Kinematics as a program*, "From rates of change to an update
rule".

Before:

> Velocity is the rate of change of position, and acceleration is the rate of
> change of velocity: [equations] Everything the program needs to know at one
> instant is the triple $(t, x, v)$. That triple is the **state**.

After:

> Freeze the ball at one instant. To say where it will be a moment later you
> need to know where it is and how fast it is moving, and nothing else about
> its past matters. Those two numbers and the clock are the whole
> **state** $(t, x, v)$, and they are linked by the two rates of change
> (position by velocity, velocity by acceleration): [equations]

The after makes "state" a consequence of an observation and not a definition
to memorise.

### 3. Mathematical derivations

**Principle.** Say where the derivation is going before the algebra; give
each step a reason in words, not only in symbols; and state the result in
words afterwards, with what it means for the program. Where a step is short,
show it; "as substitution confirms" is a request to trust the author.

**Example 3.1** — *The harmonic oscillator*, "A mass on a spring".

Before:

> Sine and cosine are the functions whose second derivative is minus
> themselves, scaled, so [solution] solves the equation from any initial
> position $x_0$ and velocity $v_0$, as substitution confirms.

After:

> Differentiate $\cos(\omega t)$ twice and you get $-\omega^{2}\cos(\omega t)$
> back; the same holds for $\sin(\omega t)$. So any mixture of the two solves
> the equation, and the two mixing constants are exactly what is needed to
> match any starting position and any starting velocity: [solution].

**Example 3.2** — *Kinematics as a program*, "How large is the error?".

Before (one run-on paragraph):

> One step drops terms of size $\Delta t^{2}$, so a step adds an error of at
> most $C\,\Delta t^{2}$ … This bound is an argument for the order, not yet a
> measurement; the examples measure it. Explicit Euler is a **first-order**
> method: halve the time step and the error at time $T$ halves, at twice the
> work.

After (same argument, in the order of the reasoning):

> How does the error depend on the step? Count. One step drops terms of size
> $\Delta t^{2}$, so it adds at most $C\,\Delta t^{2}$. Reaching a fixed time $T$ takes
> $T/\Delta t$ steps, so the errors add up to at most $C\,T\,\Delta t$: *one
> power of $\Delta t$ is lost in the adding.* That is what **first order**
> means, and it is the practical rule: halve the step, halve the error, pay
> twice the work. This is an argument; the first worked example is the
> measurement.

### 4. Computational experiments

**Principle.** An experiment starts from a question and a prediction: what
do we expect to see, and what would count as seeing something else? Say that
before the cell, say what the cell does only as far as the reader needs, and
keep the description of the cell's mechanics out of the opening sentence.

**Example 4.1** — *Kinematics as a program*, "A ball thrown straight up".

Before:

> A ball leaves a hand above the ground, moving upward, and we follow it
> until shortly before it is back at that height. The cell sets the numbers,
> runs the simulation, and evaluates the exact motion at the same instants.

After:

> Will the program notice its own error? A ball thrown straight up has an
> exact motion we can write down, so any gap between the program and the exact
> curve belongs to the method. We follow the ball from the hand to
> nearly its return and put the program next to the exact curve at the same
> instants.

**Example 4.2** — *The harmonic oscillator*, "Three periods".

Before:

> The time step is a fraction of the period, which makes $\omega\,\Delta t$ the
> quantity to watch; the cell starts with 64 steps per period.

After:

> The derivation makes a prediction we can fail: every step multiplies the
> energy by the same factor, so after any number of steps the energy is that
> factor to that power. The cell runs the oscillator with several time steps
> and puts the growth it measured next to the growth the factor predicts. If
> they disagree, either the derivation or the program is wrong, and we want
> to know which.

### 5. Interpreting results

**Principle.** After every number, table, or figure, one sentence says what it
means for the question of the lesson: a comparison, a consequence, a
surprise. Reporting a value is not interpreting it. A limit on what a result
shows belongs where it applies, stated once with its scope, and is kept in
"Limits" in full; the interpretation says what the result *does* show first.

**Example 5.1** — *Kinematics as a program*, "How large is the error?" (the
figure after the claim on the first-order result).

Before:

> The straight lines are the visible form of the first-order result; they say
> nothing about time steps far smaller or larger than the ones plotted.

After:

> Halve the step and the error halves: that is what a line of slope one means,
> and both motions show it. The picture covers the steps that were drawn; what
> happens for much smaller ones is the question of the Limits section.

**Example 5.2** — *The harmonic oscillator*, "Three periods" (after the table
of growth against step).

Before:

> The observed order tends to one, from below: [mechanism] … The first
> exercise asks what one per cent costs.

After:

> A finer step lowers the growth but never turns it off, and never changes its
> sign: every step adds energy and none takes it away. That is the real
> problem with explicit Euler on an oscillation; the size of the step is only
> how fast it shows. What it costs to keep the growth down to a tolerance is
> the first exercise.

Interpretation that already works, for comparison: *Random walks and
diffusion*, the claim on the fraction of walkers within a radius ends "The two
checks use the same $D$, so together they say that the walkers spread by the
law and in the shape that the step rule predicts." It combines two results
and says what they mean together.

### 6. Transitions

**Principle.** A transition tells the reader why the next thing follows from
this one: a gap just exposed, a question just raised, a tool just made. It
does not say only where the next thing is. Point the other way too: when a
result depends on an earlier lesson, say what from it is being used and not
only that it exists. Say each hand-off once.

**Example 6.1** — *Kinematics as a program*, "How large is the error?".

Before (two sentences within fifteen lines):

> This is a prediction the program has to reproduce: the first worked example
> compares it with the simulation in the digits shown. […] The derivation
> above is the proof for the model; the first worked example recomputes it
> with the program.

After (once, at the end of the passage, with the reason):

> The derivation is a proof for the model; whether the *program* behaves like
> the model is a different question, and the first worked example asks
> it: it recomputes the lag, to the digits shown.

**Example 6.2** — *Projectile motion with drag*, "The range against the
launch angle".

Before:

> How far the best angle moves below $45^\circ$ depends on the ratio of the
> launch speed to the terminal speed, as the third exercise shows.

After:

> So the best angle is lower with drag. How much lower depends on how strongly
> drag matters, which the ratio of the launch speed to the terminal speed
> measures: a slow throw hardly feels the air, a fast one feels it all along.
> The third exercise puts numbers on that.

For comparison, a transition that works: *Newton's laws*, "Worked examples"
(after the figure of the path with drag): "For the quadratic drag of a ball in air there is none,
and the next lesson shows how to trust a simulation without it." It names the
gap, then the lesson that fills it.

### 7. Conclusions

**Principle.** A lesson should end an explanation with what the reader can
now do or understand that they could not before, tied back to the opening
question, and with what remains open. The formats of this project have no
conclusion section and none is to be added: write the conclusion as the last
paragraph of the "Worked examples" section, before "Limits", so that the
limits, the self-check, and the exercises follow it. Where a lesson already
states a rule, as *Numerical integrators* does after its cost table, that is a
conclusion; it needs to be the last thing said there, not the middle.

**Example 7.1** — *Projectile motion with drag*, end of "The range against
the launch angle" (the last words before Limits).

Before: see Example 6.2 (the paragraph ends on a pointer to an exercise).

After:

> We began by asking at what angle to throw a ball to make it go furthest,
> and no formula answers that with drag. A simulation we had first checked in
> the cases we can calculate gave an answer anyway: lower than $45^\circ$,
> and by an amount that depends on the ball. The check is why we believe
> the answer; the answer is what the check was for.

**Example 7.2** — *Kinematics as a program*, end of the last worked example
(before Limits).

Before (the last prose of the section):

> The straight lines are the visible form of the first-order result; they say
> nothing about time steps far smaller or larger than the ones plotted.

After:

> We can now measure how wrong the program is, and the measurement matches the
> prediction: the error of explicit Euler is proportional to the time step. The
> next lesson makes the acceleration depend on the state, and then the exact
> answer disappears. What stays is the habit this lesson teaches: compare the
> program with something you can calculate by hand.

## Earlier articles: the register to learn from

These are articles of the author at ataspinar.com, chosen each for a quality
the lessons lack. They are quoted in a sentence or less or paraphrased, and
they are examples of a *direction*, not a tone to copy: the articles are
looser with scope and evidence than a lesson may be, and lessons keep their
standards. The articles read for this guide are the sources committed to the
author's blog repository, since the published pages render their text with
JavaScript.

1. **"A guide for using the Wavelet Transform in Machine Learning"**
   (2018-12-21), introduction and ending. *Quality: it begins with what the
   previous method cannot do.* The Fourier approach "works surprisingly well",
   then fails for signals whose frequencies change, "That's too bad, since most
   of the signals we see in real life are non-stationary in nature", and
   that failure is the reason for the article. Lesson openings start
   with the question but rarely with the failure that makes the method
   necessary. The ending is also honest about what is left to the reader:
   "A lot will depend on the choices you make" (which wavelet, which level),
   and it warns against treating the papers as final. A conclusion that names
   the open choices is more useful than one that restates the result. Use for
   parts 1 and 7.
2. **"An introduction to solving differential equations numerically"**
   (2022-04-05), introduction. *Quality: it says why to read it, and what it
   leaves out.* It states the author's reason for writing, asks "Why should
   you read this blog-post?", and promises to keep the mathematics to a
   minimum: "No mathematics just for the sake of mathematics!" It then builds
   the topic in steps, from ordinary equations and fitting a line towards
   differential equations, each section resting on the one before. Lessons
   assume the reader sees why a derivation is needed; they seldom say. Use for
   parts 2 and 3.
3. **"Sentiment Analysis with the Naive Bayes Classifier"** (2016-02-15),
   opening and ending. *Quality: it starts from where the reader just was, and
   restates a rule in plain words before the formula.* It opens from the
   bag-of-words model of the previous post, describes the rule in words ("Simple
   enough!"), then shows what the new model changes and why, and ends with a
   "Next blog" paragraph that names what the next article will test. The
   hand-offs between parts say what comes next *and why*. Use for parts 5 and
   6.

The articles also supply the register's good habits: a first-person voice
that says "we" for the work and "I" for a judgement, direct address
("you"), and a plain restatement after a formula. These are available to a
lesson, never required of it.

## Recurring faults and how to spot them

| Fault | What it looks like | How to detect it in a draft |
|---|---|---|
| **Boilerplate introduction** | The opening could be pasted onto another lesson: "This lesson …", a list of what is derived, shown, and measured, no question. | Replace the lesson's subject with another in the first two paragraphs. If they still read true, it is boilerplate. Check that the first sentence is a question or a situation, and that the second paragraph says why, not what. |
| **Repetition** | The same framing, hand-off, or caveat appears twice in a section, or in the introduction, the section, and Limits. | Pick the three most distinctive phrases of a paragraph (for example "says nothing about", "no real … is measured", "the first worked example") and search the lesson for them. A caveat appears in full once, in Limits, and elsewhere at most as a clause with its scope. |
| **Needlessly defensive wording** | A result is surrounded by "only", "not yet", "does not prove", "says nothing", "in the cases run", and the reader cannot tell what *is* shown. | Underline every hedge. A hedge is kept when it names a condition that can fail (a scope, an assumption, a number of runs). A hedge with no stated condition is removed, or replaced by the condition. Then read the sentence for what it asserts: if nothing is asserted, the sentence is the fault. |
| **Monotonous sentence structure** | Ten sentences in a row that begin the same way ("The …", "This …") and have the same length and shape; every paragraph runs claim, reason, caveat. | Read the first four words of ten consecutive sentences, and the length of each. Three in a row with the same opening or a fixed rhythm is a finding. Reading a paragraph aloud finds it quickly. |
| **Conclusions that do not interpret** | A number, table, or figure is followed by a statement of its content or a pointer to an exercise, not by what it means. | For each sentence with a number, ask "so what?" and see whether the sentence answers it: a comparison, a consequence, a decision. The last paragraph of "Worked examples" is read for what the learner can now do. |
| **Method before question** | An explanation that starts with the definition or the formula and later gives the reason. | Find the first equation of a section and read what precedes it. If nothing says why the reader needs it, add the question or the picture. |
| **Roadmap paragraph** | A paragraph that lists what later sections do. | Delete it. If the lesson reads the same without it, it was only a map; keep one sentence of it when the reader needs to know what is coming. |

## Draft editorial review checklist

For the editorial reviews of F115 (F116 makes it the rubric). A review is a
list of findings, **not a score**: a lesson, a section, or a sequence is
never given a number, a grade, or a ranking. For every finding the reviewer
writes four things:

1. **The weakness, named.** From the fault table above, or a new one with a
   name. Not "unclear" but "boilerplate introduction".
2. **The evidence.** The passage quoted, with the lesson, the section, and
   the line; for a pattern, two or three instances.
3. **The action.** One concrete change that the author can make (a sentence
   to cut, a question to lead with, a hand-off to rewrite), written as a
   proposal. A finding that cannot be acted on is rewritten until it can.
4. **The check that stays.** What the change must not touch: the claims,
   numbers, identifiers, figures, and references of the passage.

The reviewer also answers, in words and with evidence, for each part:

- **Opening:** does the first paragraph put a question or a situation before
  a technique? Could it be moved to another lesson?
- **Intuition and derivation:** does the reader get a picture or an idea
  before the equation, and the result in words after? Is each step motivated?
- **Experiment and interpretation:** is there a prediction before the cell
  and a meaning after the result? Does every figure and table have a
  sentence of interpretation?
- **Transitions:** does each hand-off say why the next part follows? Is any
  said twice?
- **Conclusion:** does the lesson end by answering its opening question and
  naming what remains open?
- **Voice:** is the register right for this subject and this reader? Is any
  informality, joke, or anecdote there only to sound friendly?
- **Fidelity:** does anything in the draft assert more, less, or something
  other than the lesson's claims and numbers? If so it is a scientific
  finding and goes to the physics review, not into the style review.
- **The sequence:** read as a connected sequence, do the lessons build on each
  other, and is anything repeated across lessons?

A review may end with no finding for a part; it says so and gives the
passage that shows the part works. The outcome of a review is the findings,
what the author did with each, and what was declined and why.

## Audit of openings and conclusions

The evidence the principles answer: the openings and the closing prose of
the five pilot lessons (mechanics 01 to 05) and of one lesson of each other
strand that has lessons (thermodynamics, waves, agents-abm, agents-llm,
lean). "Closing prose" is the last prose of the "Worked examples" section
before "Limits", where a conclusion would stand; every audited lesson then
continues to Limits, the exercises, and the last section, with no section of
conclusion, as the format requires.

| Lesson | Opening | Closing prose of the worked examples |
|---|---|---|
| Kinematics as a program | Starts from a question (where is the ball?), then a definition paragraph, then a goal. Good. | Ends on a hedge: the lines "say nothing about" other time steps. No conclusion. |
| Newton's laws | Starts from the gap with lesson 1 (the acceleration depends on the state). Second paragraph is a roadmap in three parts. | Ends on the shape of the drag curve and a good hand-off to the next lesson. Closest to a conclusion of the five. |
| Projectile motion with drag | Starts from the coupling of the motions, then states that closed forms are gone. Question of the best angle comes in paragraph two. Good. | Ends on a pointer to an exercise, not on the answer to the opening question. |
| The harmonic oscillator | Starts from the exercise that left a loose end, then names the system. Second paragraph states the result before the reader has the question. | Ends on a pointer to the first exercise. |
| Numerical integrators | Three long paragraphs before the first cell; strong first paragraph (the million orbits); the third paragraph lists three questions. | The rule of the lesson is stated (in "Cost: a millimetre after two periods") but not as the last thing the reader meets; the section closes on widget cells. |
| Random walks and diffusion | Ink and smell: the best opening of the audit; the second paragraph is a roadmap and "no real ink is measured". | Ends on a combined interpretation of two checks: what they mean together. Works. |
| The wave equation | Plucked string, reflection, the question of the equation. Good; the second paragraph is a method list. | Ends on what happens past the limit, and at exactly the limit. Works. |
| Particles in a box | Pressure and the speed curve as properties of the many. Strong. The disclaimers (statistical checks, "No real gas is measured here") are long. | Ends on a caveat on the pooled histogram. No conclusion. |
| An agent runs an experiment | The tennis ball, then the model and the loop. Good. Two paragraphs on what the model is *not* given before the point of the recording. | Ends on how to run the live command and handle the key. Procedural; the finding of the lesson is in the self-check. |
| Proving what the simulation showed | The question "true for every step, or only the ones we tried?" Good, and a strong second paragraph. | Ends with a short interpretation of the figure ("the theorem is the reason"); the lesson's conclusion is in the exercise. |

What the audit shows, and the principles it answers:

- **Openings are good; the second paragraph is not.** All ten start from a
  question. At least seven (Newton's laws, the harmonic oscillator, numerical
  integrators, random walks, the wave equation, particles in a box, and the
  Lean lesson) turn the second or third paragraph into a list of what the
  lesson will do (Principle 1).
- **No audited lesson concludes.** Three end the worked examples on a hedge or
  a procedure (kinematics, particles in a box, an agent runs an experiment),
  two on a pointer to an exercise (projectile motion, the harmonic
  oscillator), one on widget cells (numerical integrators), and none on a
  statement of what was learned that returns to the opening question
  (Principle 7). Four end on an interpretation or a hand-off (Newton's laws,
  random walks, the wave equation, the Lean lesson), the closest to a
  conclusion.
- **Hand-offs repeat.** In kinematics the first worked example is announced
  twice within fifteen lines of "How large is the error?" (Example 6.1;
  fault: repetition). The audit read the introductions and closing prose,
  not whole lessons, so it is evidence for these two places only.
- **Interpretation is uneven.** Where a lesson computes a number it usually
  explains the mechanism; it less often says what the number settles
  (Principle 5).

## Pages that are not lessons

This section is for the introduction of a course or a method path
(`site/introductions/`, F156), the learning journey of the atlas and About
(F157), and the copy of Home (F158). They share the register of the guide
(precise, scoped, written to a reader who is respected) but they do not
teach a result, so they have rules of their own.

- **What such a page may claim.** It may say why a subject matters, what a
  sequence asks, what the lessons do, and why they come in their order. It
  claims nothing that a lesson does not show: no number, equation, or
  result appears on an introduction except as the lesson that shows it, and
  a sentence that a lesson page contradicts is a defect of the introduction.
  A claim about the method says what the lessons do, for example that a
  worked run of a model is a written example and not a live call, and does
  not stretch to what an agent can do in general.
- **An AI result is never a discovery.** A page that mentions an agent says
  that the world is a toy world and that the evidence is the lesson's, and
  never describes a result of an agent as a discovery of physics.
- **How it refers to lessons and evidence.** Always by reference
  (`{slot:...}`, `{sequence:...}`, `{term:...}`), never by a hand-written
  title or link, so that a retitled lesson or a planned lesson that is
  published is followed by itself. A planned lesson is named as planned and
  is never described as if it existed; a page says "planned" where it names
  one. Evidence is pointed to (the lesson, the glossary), not restated.
- **It never repeats a lesson list by hand.** The lesson list, the counts,
  the prerequisites, the capstone, and the published or planned state are
  derived from the curriculum file and the front matter. Prose does not
  count lessons or slots, and does not enumerate them as a catalogue; it
  uses a few of them to say something about the order.
- **Voice.** Inline Markdown only, in short paragraphs. Open with the
  question or the use of the subject, not with a description of the page.
  No promise ("master", "everything you need"), no boilerplate transition
  repeated from page to page, no sentence that would fit any course if its
  name were changed. A sequence that has no capstone project says so.
- **Staying true.** A later feature that adds, moves, retitles, or removes a
  lesson of a sequence re-reads its introduction in the same pull request.

## Sources used for this guide

- Lessons read: mechanics 01 to 05, thermodynamics 01, waves 01, agents-abm
  01, agents-llm 01, and lean 01 (see "Audit"); examples above are drawn from
  mechanics 01 to 04 and from projectile motion, random walks, and the
  wave equation as noted.
- Articles read: the three of "Earlier articles" above.
- `docs/PROJECT_REQUIREMENTS.md`, decision 32 and the non-goal on editorial
  voice; `docs/authoring.md`, "Sections" and "Lesson format 2".
