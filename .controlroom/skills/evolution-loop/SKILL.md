---
name: evolution-loop
description: "Use when improving prompts, agent instructions, Codex skills, extraction/generation workflows, or LLM-assisted pipelines through evidence-backed evolution."
---

# Evolution Loop

## Core Rule

Improve by stacking verified blocks. Preserve a passing baseline unless the user explicitly starts a new experiment group.

The goal is one final path, not a pile of experiment traces.

The success target is improving one final path across cases: quality, speed, simplicity, and reproducibility.

## Anti-Drift Gate

Run this gate before every prompt, instruction, skill, workflow, LLM-assisted pipeline, or code-path change.

1. Declare the current step as analysis, test, or change. Do not edit during analysis or test. Enter change mode only after items 2-5 are declared; if any cannot be declared, do not edit. If verification reveals a new issue, return to analysis mode.
2. Name the single final path being protected.
3. Before change mode, declare the final path in execution order, including main files/functions, LLM call steps, and verification method. Do not add a step, branch, runner, or repair flow outside that declared path without explicit user approval.
4. Name the step in the declared path where the change will be merged. If it has no merge step, it is an orphan patch and must not be added.
5. Name which existing rule, prompt block, code, file, branch, call, or workflow step in the final path the change replaces, merges, or deletes. If there is no existing element to replace, merge, or delete, the change is growth and may be applied only under the growth condition in item 7.
6. Admit a new rule only when it meets the Rule Admission criteria below.
7. Do not let the final path grow in files, branches, LLM calls, prompt blocks, or code volume. If growth is unavoidable, remove, merge, or compress existing elements in the same change and show that the final path became smaller or clearer. If you cannot show that, do not apply the change.
8. After merging the change into the declared final path, judge pass or fail only by running that final path. Success from a separate runner, temporary script, manual correction, post-processing-only fix, or bypass path does not count.

Pass criteria:

- the final path is shorter, clearer, or more directly aligned with the task contract
- the change has a final-path integration step
- the change replaces, merges, deletes, or compresses existing complexity
- verification ran the declared final path
- the same root-cause failure does not recur in the verification set
- previously passing cases still pass through the same final path

Fail criteria:

- "just one more check" behavior
- adding a rescue path instead of fixing the declared integration step
- adding an orphan patch
- net growth without removing older complexity
- counting a patch path as passing
- making prompts larger to compensate for unclear responsibility boundaries
- retesting until stochastic success
- treating a single-case pass or temporary success as evolution
- renaming broad work as decomposition without reducing each worker's responsibility

## Scope Lock

Before edits, write the working lock:

- Purpose
- Allowed changes
- Forbidden changes
- Verification method
- Minimum-change gate

Minimum-change gate:

- Can this be solved inside the existing artifact, file, prompt block, or workflow step?
- Does any new file, helper, step, or branch reduce real complexity?
- Will the final path stay readable from start to finish?
- Will test, diagnostic, fallback, or temporary material be removed before completion?

If any answer is no, redesign smaller before editing.

## Baseline Setup

Define the comparison basis before the first change.

- Target artifact: the prompt, instruction, skill, code path, workflow, or output being improved.
- Case: one concrete input, task, sample, issue, or scenario.
- Source evidence: raw input, logs, trace, user requirement, expected contract, or external reference that decides correctness.
- Reference baseline: a prior passing output, accepted behavior, production path, gold file, review comment, or user-approved result.
- Pass criteria: the observable condition that proves the case works.
- Regression set: previously passing cases that must stay passing.

Do not treat a reference baseline as an absolute answer when source evidence contradicts it.

## Loop Modes

Choose one mode before testing. Use case-first by default. Use aspect-sweep only when one named aspect needs cross-case pressure.

Both modes must run the same declared final path. A multi-case run is not evolution unless it is an aspect-sweep with one named aspect, or the user explicitly requested non-evolution batch execution.

### Case-First Loop

Use this mode to improve one full case.

1. Select one case.
2. Run only the agreed target path.
3. Compare the result with source evidence and the reference baseline.
4. Judge directly; do not make a script judge semantic quality.
5. If it passes, distill the prompt, instruction, code, or workflow.
6. If it fails, run the failure loop below.
7. Move to the next case only after the current case passes or the blocker is reported.

### Aspect-Sweep Loop

Use this mode to improve one fixed aspect across multiple cases; it is not batch fixing or broad regression.

1. Name one aspect and its pass criteria before testing.
2. Select cases that expose that aspect.
3. Run the same final path for every case.
4. Judge only the named aspect from source evidence and the reference baseline.
5. Group failures only when they share the same root-cause mechanism.
6. If failures have different mechanisms, split the sweep or return to case-first.
7. Apply only a general change that belongs to the declared final path.
8. Rerun the same aspect set through the same final path.
9. Run full case-level regression before declaring the workflow improved.

Aspect-sweep success proves only that aspect improved. It does not prove the full case passes.

## Failure Loop

Separate symptom from cause before changing anything.

Use 3 Whys and Zoom-Out / Zoom-In as one linked problem-solving procedure. The chain-question method follows direct mechanisms; the zoom-out reset repairs the chain when its subject is wrong. Together they locate the verified root cause and final-path boundary before any fix is designed.

1. State the observed failure.
2. State the intended behavior in one sentence.
3. Use 3 Whys as one vertical cause chain.
4. If the 3 Whys chain stops being vertical, the next why has no clear subject, or the same failure repeats, run the Zoom-Out / Zoom-In Cause Analysis Reset to choose the correct boundary for the same cause chain.
5. Verify each cause link from source evidence, logs, traces, inputs, outputs, or execution records.
6. Mark unverified cause links as assumptions and do not fix while a required link remains unverified.
7. Check existing sources before inventing a new rule.
8. Decide whether the fix belongs in prompt wording, agent instruction, code, schema, tool use, data, rendering, or workflow order.
9. Apply the smallest general change.
10. Rerun the same case or the same aspect set through the declared final path.

Existing-source order:

1. Current final path and active instructions.
2. Previously passing outputs for the same failure mode, if available.
3. Production or user-approved baseline, if available.
4. Relevant project memory, durable decisions, or prior postmortems.
5. Old experiment files only when the current final path lacks the needed rule.

If a failure mode already had a passing general solution, restore or refine that solution before creating a new rule.

### Zoom-Out / Zoom-In Cause Analysis Reset

Use this reset inside the 3 Whys chain-question method when the cause chain is no longer vertical, the next why has the wrong subject, or the next move would be another patch. It is cause analysis only, not brainstorming, solution design, or planning.

Stop editing and write the cause-analysis big picture first:

- objective being protected
- final path in execution order
- input, output, and contract at each step
- source evidence and reference baseline
- exact step where the symptom appears
- assumptions that are not yet verified

Then zoom in gradually back into the same chain-question procedure:

1. Pick one boundary or step from the big picture.
2. Make that boundary the subject of the next why.
3. State the single mechanism that could produce the symptom there.
4. Verify that mechanism from evidence or mark it as an assumption.
5. Continue the 3 Whys cause analysis only from that verified boundary.
6. Choose a fix only after the linked procedure reaches a verified root cause.

Do not add a rule, branch, fallback, or rescue path until the reset identifies the final-path step and the 3 Whys chain reaches a verified root cause.

## Rule Admission

Add a rule only when it is general.

- It applies beyond the current case and can recur for similar inputs.
- It does not mention case-specific identifiers, values, wording, or one-off artifacts.
- It follows from the task contract, responsibility boundary, input structure, output schema, or verified failure mode.
- It does not conflict with existing rules and has an integration step in the final path.
- It preserves already-passing baseline behavior unless the user asked to change it.
- It keeps semantic judgment in the LLM, not in scripts.

Keep a case-specific observation as notes or report text, not as final prompt, instruction, or code.

## Compatibility Gate

Before changing a prompt, instruction, skill, or shared workflow rule, check whether the new wording conflicts with the existing hierarchy or changes passing behavior.

Run this gate before editing:

1. If the change touches prompt text, run `$prompt-guide` on hardcoding, missing context, and example quality first; then identify the exact rule, section, block, file, or workflow step the change touches.
2. State whether the change narrows, broadens, replaces, or clarifies that rule.
3. Check for conflict with role split, output contract, tool responsibility, and previously passing failure-mode rules.
4. If it broadens a rule, name the false-positive risk.
5. If it narrows a rule, name the false-negative risk.
6. If it replaces a rule, explain why the older behavior should no longer stand.
7. If the effect is unclear, do not edit; inspect current artifacts, prior passing outputs, or the production path first.

Pass criteria:

- The change preserves existing passing behavior unless the user explicitly asked to change it.
- The change fixes the root cause without moving the failure to another part of the workflow.
- The change refines the current hierarchy instead of adding a competing rule.
- The change does not weaken factual preservation, output contracts, or tool boundaries.

Fail criteria:

- The new rule says the opposite of an existing rule without resolving the conflict.
- The new rule makes one step absorb responsibility that another step owns.
- The new rule reacts only to one case and has no reusable failure mode.
- The new rule improves one case by risking regression in already passing cases.

If the gate fails, do not patch the artifact. Restore or refine the existing rule instead.

## Generalization Gate

After a meaningful unit of evolution, verify that changes accumulated into general rules rather than case tuning.

Run this gate:

- after about five case loops
- before promoting a prompt, instruction, skill, code path, or workflow as the current best path
- after an aspect-sweep changes the final path
- after a shared rule or shared workflow step changes
- when a previously passing case fails again

Gate method:

1. Freeze the target artifact during the gate.
2. Audit each new rule for case-specific identifiers, wording, and sample-only artifacts.
3. Explain each rule as a reusable failure-mode rule without naming the case that caused it.
4. Rerun the regression set.
5. Run holdout cases that were not used to tune the current rules when available.
6. Judge results against source evidence first and the reference baseline second.
7. Group failures by failure mode, not by case.

Pass criteria:

- Previously passing cases do not regress.
- Holdout cases pass at a similar quality level when available.
- The same failure mode improves across more than one case or follows from a verified contract.

Fail criteria:

- A rule only makes sense when a specific case is named.
- A tuned case improves while prior passing cases regress.
- Failures move from one responsibility boundary to another.
- Narrow prohibitions or examples keep accumulating.
- Pass depends on luck, retries, or an unrecorded manual step.

If the gate fails, do not add another narrow patch. Return to the case-first failure loop, find the vertical root cause, restore any known successful general rule, then rerun the gate.

## Distillation

After a passing rerun, distill the change.

- Keep one final success path.
- Remove temporary runners, diagnostics, traces, and defensive branches.
- Keep prompts and instructions concise.
- Keep necessary prohibitions when they define real boundaries.
- Put shared rules in shared instructions.
- Put local rules only where the local responsibility lives.
- Keep examples only when they clarify a boundary pair.
- Remove examples after the principle is clear.

## Mechanical Boundary

Use scripts and deterministic tools only for mechanical work.

- Mechanical work: file IO, command execution, parsing, schema checks, diffing, rendering, test running, and structural validation.
- Semantic work: meaning, category, quality, missing-content judgment, priority, correctness against source evidence, and whether a rule is general.

If a decision needs semantic interpretation, make the LLM decide from evidence instead of encoding the judgment as a branch or fallback.

## Review

Review the final change before reporting.

- Read the changed artifact and nearby rules directly.
- Check for prompt hardcoding, responsibility drift, stale examples, conflicting terms, unnecessary structure, and leftover artifacts.
- Run the active repository or workspace validation required by the user or project.
- If active instructions require a separate review skill, run that required process after the evolution change.

## Reporting

Report after each case-first run, aspect-sweep, or user-requested non-evolution batch:

- case and target path
- aspect and aspect-set result, when an aspect-sweep was used
- pass/fail judgment
- source evidence and reference baseline used
- root cause, if failed
- general rule or implementation change applied
- regression or holdout result
- review result
- remaining risk or blocker

Before ending, also report these final-path closure checks:

- Did the final path evolve?
- Was any orphan patch or separate path created? The expected answer is no; if yes, remove it or report the blocker.
- Did the target code, prompt, instruction, skill, file, or workflow stay compact?

Do not describe post-run evaluation as part of the production workflow.
