import Lean

/-!
# Axiom audit

Run by `scripts/check-lean.sh`, which puts one `import` line per module of the
project in front of this file and elaborates the result. The file is not a
module of the library.

The audit fails when a declaration of the project

* is itself an `axiom`, or
* depends on an axiom other than the three every Lean proof may use. That
  covers `sorry` and `admit`, which both leave a dependency on `sorryAx`.

A physical assumption therefore has to be a hypothesis of the theorem or a
field of a structure, where the reader can see it.
-/

open Lean Elab Command

/-- The axioms of Lean's standard logic. -/
def standardAxioms : List Name := [``propext, ``Classical.choice, ``Quot.sound]

/-- The prefix of every module of the project. -/
def projectRoot : Name := `PhysicsByConstruction

run_cmd do
  let env ← getEnv
  let mut declarations := 0
  let mut problems : Array MessageData := #[]
  for moduleName in env.header.moduleNames, moduleData in env.header.moduleData do
    unless projectRoot.isPrefixOf moduleName do continue
    for name in moduleData.constNames, info in moduleData.constants do
      declarations := declarations + 1
      if info matches .axiomInfo _ then
        problems := problems.push m!"{moduleName}: '{name}' is declared as an axiom"
        continue
      for ax in ← collectAxioms name do
        if ax == ``sorryAx then
          problems := problems.push m!"{moduleName}: '{name}' uses 'sorry'"
        else unless standardAxioms.contains ax do
          problems := problems.push m!"{moduleName}: '{name}' depends on axiom '{ax}'"
  if declarations == 0 then
    throwError "axiom audit: no declaration of {projectRoot} was imported"
  for problem in problems do
    logError problem
  unless problems.isEmpty do
    throwError "axiom audit failed: {problems.size} problem(s) in {declarations} declarations"
  logInfo m!"axiom audit passed: {declarations} declarations use only {standardAxioms}"
