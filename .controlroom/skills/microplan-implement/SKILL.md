---
name: microplan-implement
description: Implement one reviewed microplan task with test-first red/green discipline, focused checks, and strict scope control. Use for a single task plan after microplan-review passes, before microplan-verify, or when microplan-batch executes one implementation task.
---

# Microplan Implement

## Purpose

Implement exactly one microplan task.

Use this after `microplan-review` passes. Do not use it for master plans, phase planning, broad refactors, or multi-task batches.

## Inputs

- One task plan artifact.
- Current intent/context source.
- Phase or master plan when referenced by the task.
- Current diff or clean worktree state.

## Core Rule

For behavior changes, bug fixes, and refactors:

1. Write the smallest focused failing test first.
2. Run it and confirm it fails for the expected reason.
3. Write the minimum implementation needed to pass.
4. Run the focused test and confirm it passes.
5. Refactor only after green, while keeping tests green.
6. If a failing test is not practical, record the exception before implementing.
7. If the same failure repeats after two fix attempts, stop patching and identify the root cause before a third attempt.

## Workflow

1. Read the task plan and current intent source.
2. Extract the domain contract, allowed scope, non-goals, completion gate, and verification commands.
3. Identify the narrowest useful test boundary.
4. Follow the red/green/refactor rule.
5. Run the task's verification commands.
6. Run `microplan-verify` against the task plan, intent source, and diff.
7. Fix concrete `FAIL` items only.
8. Report changed files and verification results.

## Guardrails

- Implement only the task.
- Do not add speculative features.
- Do not add backwards-compatibility shims unless the plan requires them.
- Do not broaden tests beyond the task's meaning axis.
- If a non-trivial repeated mistake is solved, report it as a `compound` candidate instead of letting the lesson disappear.
- Preserve unrelated dirty worktree changes.
- If the task plan conflicts with the current intent source or current code, stop and report instead of forcing a stale plan.
- Treat `local-docs/*`, deleted local planning docs, old master plans, and old microplans as historical references unless the current intent source explicitly promotes them.

## Output

```text
구현 결과: DONE | BLOCKED

변경:
- ...

TDD:
- RED: command/result
- GREEN: command/result

검증:
- command — pass/fail/not run

남은 이슈:
- ...
```
