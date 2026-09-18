---
name: microplan-review
description: Ultra-light closure review for one small implementation plan before implementation. Use when the user says "microplan-review", "마이크로플랜 리뷰", "구현 계획 검토", or asks to check a single microplan or task artifact before implementing it. Do not use for master plans, roadmaps, whole-project critique, or code review.
---

# Microplan Review

## Purpose

Validate one small implementation plan without expanding it.

Use this for micro plans that should close one meaning unit. Do not run full adversarial review unless the plan involves irreversible deletion, high-cost migration, security, permissions, external billing/API contracts, or master-plan order decisions.

## Core Rule

Review only the next plan to implement.

Do not review the whole project, do not create a debate log, and do not produce a new agreed document. The output is a short pass/fix verdict.

The canonical planning-package definition is the GBrain page `reference/gbrain-planning-package-protocol`. The rules below are the working summary. When they conflict with that page, follow the page and update this skill.

Before the four checks, identify the current source of intent:

- If the user names an intent/context source, use that.
- If the plan references a canonical GBrain page, context page, spec, or task artifact, use that.
- If the plan is a GBrain planning package task such as `{package-root}/task-001`, read the package root and `{package-root}/master-plan` before reviewing the task.
- If durable plans live in GBrain and the plan input is a local file or pasted task from a durable topic, search GBrain for the same-topic package before reviewing. Reuse the current package when found and update its task/root status; if no package root can be identified, ask for the package root instead of completing a local-only review.
- If the project has a planning authority index, use it to find the current canonical source before relying on older docs.
- Treat `local-docs/*`, deleted local planning docs, old master plans, and old microplans as historical references unless the canonical source explicitly promotes them.
- If no intent source is clear, ask one short question for the source.
- If the user wants to proceed without one, review only against the plan's own domain contract and write the limitation in the verdict line.

When reviewing a GBrain planning package task or a local/pasted task bound to a package, update the task page and package root after the verdict:

- `PASS`: set the task status to `reviewed`.
- `FIX`: update the task with the smallest required wording or gate change, then rerun this review.
- `ESCALATE`: set the task status to `blocked` and record the escalation reason.

If direct GBrain write access is unavailable, report the exact task and package-root status updates that must be written; do not present the review as fully recorded.

## Four Checks

Ask only these questions:

1. **Meaning**: Does the plan conflict with the chosen intent source or referenced domain contract?
2. **Scope**: Is it one meaning axis, with at most 3 leaf implementation tasks?
3. **Order**: Does it depend only on completed previous phases, and avoid work that belongs to later phases?
4. **Close**: Are completion gates observable through 1-3 focused checks?

For frontend, template, form, modal, navigation, or HTMX work, apply the Close check to the user path. The gate should prove the relevant screen wording, button/link exposure, form submission, modal state, or HTMX response is correct. If backend tests cannot prove that path, require a focused HTML assertion, Django client check, or Playwright check.

If a concern does not affect one of these four checks, mark it as note or ignore it.

## Severity

Use only three outcomes:

- `PASS`: implement as written.
- `FIX`: a small edit is required before implementation.
- `ESCALATE`: this is not a micro-plan review; use Forge or a deeper review.

Escalate only for irreversible deletion, risky data migration, security/permission changes, external API/cost contracts, unclear domain meaning, or cross-phase order uncertainty.

## Output Format

Keep the answer short:

```text
결론: PASS | FIX | ESCALATE
범위: <intent source name> 기준 | 계획 자체 기준만 확인

닫힘을 막는 문제:
- ...

최소 수정:
- ...

구현 전 확인:
- ...
```

Rules:

- Max 5 issues.
- Prefer 1-3 issues.
- Do not invent improvements.
- Do not request broader refactors.
- Do not expand a 50-line plan into an 80-line plan unless closure truly requires it.
- If the plan needs edits, propose the smallest wording or gate change that closes the issue.

## Good Micro Review

```text
결론: FIX
범위: project/example-canonical-plan 기준

닫힘을 막는 문제:
- 완료 게이트에서 "보류 0건"과 "보류가 있어도 종료 가능"이 충돌합니다.

최소 수정:
- 보류는 후속 phase에 넘기지 않고 별도 조사 task로 분리한다고 한 문장으로 고정합니다.

구현 전 확인:
- 없음.
```

## Bad Micro Review

- Multiple reviewer personas.
- Critical/Major/Minor issue inflation.
- Whole-project critique.
- Rewriting the plan into a large checklist.
- Treating nice-to-have clarity as a blocker.
