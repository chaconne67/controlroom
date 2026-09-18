---
name: resume-evolution-loop
description: "Use when improving resume generation, resume extraction, resume prompts, or related code through sample-by-sample evolution."
---

# Resume Evolution Loop

## Core Rule

Improve by stacking verified blocks. Do not replace a passing baseline unless the user explicitly starts a new experiment group.

The loop goal is one optimized success path, not a pile of experiment traces.

The success target is improving one resume-generation final path across candidates: quality, speed, simplicity, and reproducibility.

## Anti-Drift Gate

Run this gate before every resume prompt, schema, workflow, or generation-code change.

1. Declare the current step as analysis, test, or change. Do not edit during analysis or test. Enter change mode only after items 2-5 are declared; if any cannot be declared, do not edit. If verification reveals a new issue, return to analysis mode.
2. Name the single final path being protected.
3. Before change mode, declare the final path in execution order, including main files/functions, LLM call steps, and verification method. Do not add a step, branch, runner, or repair flow outside that declared path without explicit user approval.
4. Name the step in the declared path where the change will be merged. If it has no merge step, it is an orphan patch and must not be added.
5. Name which existing rule, prompt block, code, file, branch, call, or workflow step in the final path the change replaces, merges, or deletes. If there is no existing element to replace, merge, or delete, the change is growth and may be applied only under the growth condition in item 9.
6. Admit a new resume-generation rule only when it meets the Rule Admission criteria below.
7. Check whether second-stage extraction remains scoped: each worker receives only the relevant section/record source text plus minimal map context.
8. If second-stage extraction receives full source text, all section rules, or the full source map again, reject the change and redesign the path.
9. Do not let the final path grow in files, branches, LLM calls, prompt blocks, or code volume. If growth is unavoidable, remove, merge, or compress existing elements in the same change and show that the final path became smaller or clearer. If you cannot show that, do not apply the change.
10. After merging the change into the declared final path, judge pass or fail only by running that final path. Success from a separate runner, temporary script, manual correction, post-processing-only fix, or bypass path does not count.

Pass criteria:

- the final path is shorter, clearer, or more directly aligned with the scoped extraction contract
- the change has a final-path integration step
- the change replaces, merges, deletes, or compresses existing complexity
- the next sample would use the same path without candidate-specific knowledge
- verification ran the declared final path
- the same root-cause failure does not recur in the verification set
- previously passing cases still pass through the same final path

Fail criteria:

- "just one more check" behavior
- adding a rescue path instead of fixing the declared integration step
- adding an orphan patch
- net growth without removing older complexity
- making prompts larger to compensate for unclear responsibility boundaries
- retesting until stochastic success
- counting a patch path as passing
- treating a single-case pass or temporary success as evolution
- calling the same broad LLM task under a "parallel" label

## Scope Lock

Before edits, write the working lock:

- Purpose
- Allowed changes
- Forbidden changes
- Verification method
- Minimum-code gate

Minimum-code gate:

- Can this be solved inside an existing file, class, function, or prompt block?
- Does any new file, class, helper, or branch reduce real complexity?
- Will the final path stay readable from top to bottom?
- Will test, diagnostic, fallback, or temporary code be removed before completion?

If any answer is no, redesign smaller before editing.

## Execution Environment

Run Exdigm C-group scripts with the project Python environment.

- Work through SSH in `/home/chaconne/exdigm-debug` unless the user explicitly requests an operational run.
- Use `/home/chaconne/exdigm-debug/.venv/bin/python` or `uv run python` in that remote worktree.
- Do not use system `python3` for C-group generation scripts.
- If `ModuleNotFoundError: No module named 'django'` appears immediately, treat it as an execution-environment failure, not a resume-generation failure.
- Rerun the same command with the project Python before recording the sample result.

## One-Sample Loop

Run one sample at a time.

1. Select one sample.
2. Run only the agreed target path.
3. Compare the result with source text and A-group baseline.
4. Run the Quality Judgment Gate below before saying pass.
5. If it passes, distill prompts and code.
6. If it fails, run the failure loop below.
7. Move to the next sample only after the current sample passes or the blocker is reported.

Do not batch-fix several samples at once unless a resume aspect-sweep loop is declared or the user explicitly asks for batch execution without per-sample evolution.

## Sample-Aspect Matrix

Use two complementary evolution axes.

- Sample-first loop: improve one full resume sample through the final path.
- Aspect-sweep loop: improve one fixed resume aspect across multiple samples through the same final path.

Use an aspect-sweep only when one resume aspect is named before testing and every sample uses the same declared final path.

Resume aspects may include strict section preservation, career detail usefulness, achievement separation, date preservation, compensation grouping, editor-section source support, section ownership, rendering fidelity, and prompt responsibility boundaries.

Aspect-sweep method:

1. Name one resume aspect and its pass criteria.
2. Select samples that expose that aspect.
3. Run the existing final path for each sample.
4. Judge only the named aspect from source text, A-group baseline, generated JSON, and DOCX evidence.
5. Group failures by the same root-cause mechanism.
6. Apply only a general change that belongs to the declared final path.
7. Rerun the same aspect set through the same final path.
8. Run full sample-level regression before declaring the workflow improved.

Aspect-sweep success proves only that aspect improved. It does not prove the full resume sample passes.

## Quality Judgment Gate

Do not equate generation success with quality pass. DOCX creation only proves the path ran.

Judge quality directly from evidence. Do not make a script judge semantic quality.

Evidence priority:

1. Source text is the final truth.
2. A-group output is the quality baseline, not the answer key.
3. Generated JSON and DOCX are the evaluated output.
4. If A-group conflicts with source text, source text wins.

Result grades:

- `Pass`: core facts and useful detail are preserved; the resume is usable.
- `Conditional Pass`: only minor or editorial differences remain.
- `Fail`: any critical or major issue remains.
- `Blocked`: source, A-group, or output evidence is insufficient to judge.

Severity:

- `Critical`: identity, contact, company, period, education, certification, compensation, or date is clearly wrong.
- `Major`: a strict section is missing, misplaced, over-compressed, or structurally unusable.
- `Minor`: small wording, formatting, or non-critical detail difference.
- `Editorial`: acceptable editor choice in ambiguous sections.

Strict sections:

- `personal_info`: preserve identity, contact, email, phone, date of birth, and other explicit personal rows.
- `education`: preserve school, degree, major, period, status, and location when present.
- `military`: preserve military or alternative-service fact and period when present.
- `work_experience`: preserve company, period, role, major duties, achievements, and reason-for-leaving when present.
- `certifications`: preserve licenses, certificates, exams, scores, grades, and status.
- `compensation`: preserve current/final and desired-condition groups without moving rows across groups.
- `dates`: preserve source periods or agreed deterministic date calculations.

Editor sections:

- `skills`, `core_competencies`, `self_introduction`, `training`, `awards`, `overseas_experience`, and `misc` may differ from A-group when source-supported.
- Empty `skills` or `core_competencies` is a failure when source text contains explicit skills or clear candidate strengths.
- `overseas_experience` requires source evidence that the candidate physically studied, worked, visited, stayed, or traveled overseas.
- `misc` must not absorb facts owned by strict sections.

Career quality:

- Pass when each career record has the right company, period, role, and enough source-backed duties or achievements to understand the role.
- Fail when a detailed career block is compressed into a few generic bullets and loses important projects, actions, metrics, or outcomes.
- Fail when achievements disappear into duties in a way that hides measurable outcomes.
- Fail when mapped career evidence is left empty or moved to another section.

Quality pass requires all of these:

- the target path completed
- no critical issue
- no major issue
- career detail remains practically useful
- editor-section differences are source-supported and harmless

## Failure Loop

Separate symptom from cause before changing anything.

Use 3 Whys and Zoom-Out / Zoom-In as one linked problem-solving procedure. The chain-question method follows direct mechanisms; the zoom-out reset repairs the chain when its subject is wrong. Together they locate the verified root cause and final-path boundary before any fix is designed.

1. State the observed failure.
2. State the intended behavior in one sentence.
3. Use 3 Whys as one vertical cause chain.
4. If the 3 Whys chain stops being vertical, the next why has no clear subject, or the same failure repeats, run the Zoom-Out / Zoom-In Cause Analysis Reset to choose the correct boundary for the same cause chain.
5. Verify each cause link from source text, A-group baseline, generated JSON, DOCX evidence, logs, or execution records.
6. Mark unverified cause links as assumptions and do not fix while a required link remains unverified.
7. Check existing sources before inventing a new rule.
8. Decide whether the fix belongs in prompt, code, schema, source data, render, or template.
9. Apply the smallest general change.
10. Rerun the same sample.

Existing-source order:

1. Current final path code and prompt book.
2. Previously passing run outputs for the same issue, if available.
3. Original production code and A-group prompts.
4. Relevant GBrain memories.
5. Old experiment files only when the current final path lacks the needed rule.

If an issue already had a passing solution, restore the general rule from that solution before creating a new one.

### Zoom-Out / Zoom-In Cause Analysis Reset

Use this reset inside the 3 Whys chain-question method when the cause chain is no longer vertical, the next why has the wrong subject, or the next move would be another patch. It is cause analysis only, not brainstorming, solution design, or planning.

Stop editing and write the cause-analysis big picture first:

- resume quality objective being protected
- C-group final path in execution order
- input, output, and contract at each step
- source text, A-group baseline, generated JSON, and DOCX evidence
- exact step where the symptom appears
- assumptions that are not yet verified

Then zoom in gradually back into the same chain-question procedure:

1. Pick one boundary or step from the big picture.
2. Make that boundary the subject of the next why.
3. State the single mechanism that could produce the symptom there.
4. Verify that mechanism from evidence or mark it as an assumption.
5. Continue the 3 Whys cause analysis only from that verified boundary.
6. Choose a fix only after the linked procedure reaches a verified root cause.

Do not add a prompt rule, code branch, fallback, or rescue path until the reset identifies the final-path step and the 3 Whys chain reaches a verified root cause.

## Rule Admission

Add a rule only when it is general.

- It applies beyond the current candidate and can recur for similar inputs.
- It does not mention candidate names, company names, candidate-specific values, source coordinates, or exact failed phrases.
- It follows from section meaning, document structure, output contract, or execution responsibility.
- It does not conflict with existing rules and has an integration step in the final path.
- It does not disturb already-passing baseline behavior.
- It keeps semantic judgment in the LLM, not in scripts.

Keep a case-specific observation as notes or report text, not as final prompt/code.

## Prompt Compatibility Gate

Before changing prompts, check whether the new wording conflicts with the existing prompt book or changes a passing behavior.

Run this gate before editing:

1. Use `$prompt-guide` to check hardcoding, missing context, and example quality before editing prompt text.
2. Identify the exact existing rule, section rule, or common block that the new wording touches.
3. State whether the new wording narrows, broadens, replaces, or clarifies that rule.
4. Check for conflict with existing section boundaries, role split, output contract, and previously passing failure-mode rules.
5. If it broadens a rule, name the false-positive risk.
6. If it narrows a rule, name the false-negative risk.
7. If it replaces a rule, explain why the older behavior should no longer stand.
8. If the effect is unclear, do not edit; inspect current code, prompt book, previous passing outputs, or original production prompts first.

Pass criteria:

- The change preserves existing passing behavior unless the user explicitly asked to change it.
- The change fixes the root cause without moving the failure to another section.
- The change is a refinement of the current prompt hierarchy, not a parallel competing rule.
- The change does not contaminate unrelated sections or weaken strict factual preservation.

Fail criteria:

- The new rule says the opposite of an existing rule without resolving the conflict.
- The new rule makes a section absorb evidence that another section already owns.
- The new rule is only a reaction to one sample and has no reusable failure mode.
- The new rule improves one sample by risking regression in already passing samples.

If the gate fails, do not patch the prompt. Restore or refine the existing rule instead.

## Generalization Gate

After a meaningful unit of evolution, verify that the changes accumulated into general rules rather than case tuning.

Run this gate:

- after about five sample loops
- before promoting a prompt or code path as the current best path
- after a change that rewrites shared prompt blocks or shared extraction flow
- when a previously passing case fails again

Gate method:

1. Freeze prompt and code during the gate.
2. Audit each new rule for candidate names, company names, exact failed phrases, source IDs, and sample-only wording.
3. Explain each rule as a reusable failure-mode rule without naming the sample that caused it.
4. Rerun the previously passing samples from the current evolution set.
5. Run a holdout set of samples that were not used to tune the current rules.
6. Judge results against source text first and A-group baseline second.
7. Group failures by failure mode, not by candidate.

Pass criteria:

- previously passing samples do not regress
- holdout samples pass at a similar quality level
- the same failure mode improves across multiple samples
- ambiguous editor sections may differ from A-group when source-supported
- strict factual sections preserve source-backed identity, contact, education, work, certification, compensation, and dates

Fail criteria:

- a rule only makes sense when a specific sample is named
- a tuned sample improves while prior passing samples regress
- failures move from one section to another
- narrow prohibitions or examples keep accumulating
- pass depends on rerunning until stochastic success

If the gate fails, do not add another narrow patch. Return to the one-sample failure loop, find the vertical root cause, restore any known successful general rule, then rerun the gate.

## Prompt Distillation

After a passing rerun, distill the prompt change.

- Keep concise imperative sentences.
- Keep necessary prohibitions when they define real section boundaries.
- Remove narrow "do not repeat this failed case" patches.
- Put common rules in common blocks.
- Put section rules only in that section.
- Keep examples only when they clarify a boundary pair.
- Remove examples after the principle is clear.

## Code Distillation

After a passing rerun, distill code changes.

- Keep one final success path.
- Remove temporary runners, diagnostics, traces, and defensive branches.
- Keep prompt responsibility, execution responsibility, and tool responsibility separate.
- Keep scripts mechanical: file IO, source IDs, JSON parsing, shape checks, rendering calls.
- Do not let scripts decide meaning, category, quality, or missing content.
- Preserve user changes.

## Direct Review Only

Review changes directly in the main agent unless the user explicitly asks for a separate reviewer.

- Do not call `code-review` or `code-review-loop`.
- Do not spawn review subagents.
- Do not run `codex exec`, `codex exec review`, Claude, Gemini, or another LLM/agent CLI for review.
- Read the changed files, relevant existing code, and `git diff` yourself.
- Review for functional bugs, regression against the agreed path, prompt hardcoding, semantic judgment in scripts, unnecessary structure, and leftover artifacts.

If a separate reviewer is explicitly requested, the reviewer must be a leaf agent and must not call another LLM, agent, CLI reviewer, thread, handoff, or review skill.

## Reporting

Report after each sample or requested batch:

- sample and target path
- resume aspect and aspect-set result, when an aspect-sweep was used
- pass/fail judgment
- evidence from source text and A-group baseline
- root cause, if failed
- exact general rule or code change applied
- direct review result
- remaining risk or blocker

Before ending, also report these final-path closure checks:

- Did the final path evolve?
- Was any orphan patch or separate path created? The expected answer is no; if yes, remove it or report the blocker.
- Did the target code, prompt, file, or resume-generation workflow stay compact?

Do not describe post-run evaluation as part of the production generation pipeline.

## Resume Reference

For C-group resume generation rules, read `references/cgroup-resume-rules.md`.
