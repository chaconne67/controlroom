---
name: check-master-plan
description: Review a master plan against an intent/context document, focusing on phase order, ambiguous wording, and bad translation from domain meaning into implementation verbs. Use for master plans, refactoring master plans, migration roadmaps, or when the user asks to check whether a master plan matches project intent.
---

# Check Master Plan

## Purpose

Check whether a master plan preserves the intent document's meaning and does not smuggle in unintended implementation actions.

Use this before writing or executing detailed phase plans.

## Inputs

Identify the intent source first:

- Use the context/spec document named by the user.
- If none is named, use the document referenced by the master plan.
- If still unclear, ask one short question.

Then read the master plan and only the relevant intent sections.

## Core Checks

Review phase by phase.

For each phase, check:

1. **Meaning fit**: Does the phase reflect what the intent document actually says?
2. **Order fit**: Does this phase need to happen before later phases can safely proceed?
3. **Boundary fit**: Does it keep detailed implementation inside phase plans?
4. **Verb precision**: Are implementation verbs precise enough?

## Verb Precision Rule

Flag any implementation verb that does not reveal its action type. Examples: `remove`, `delete`, `deprecate`, `cleanup`, `fix`, `align`, `migrate`, `replace`, `retire`, or Korean equivalents like `제거`, `삭제`, `폐기`, `정리`, `맞춘다`, `고정`, `대체`, `통합`.

Force the plan to distinguish:

- **physical delete**: model/field/table/data/file is removed.
- **runtime disuse**: legacy model/field/service/UI path remains but new save/read/UI flow stops using it.
- **logic removal**: automatic behavior is removed, but data/model may remain.
- **data preservation move**: existing data is copied or merged into a target model/field/service before legacy runtime use stops.
- **semantic reinterpretation**: an old field remains but no longer carries the former business meaning.
- **waiting queue**: work is intentionally deferred because an external dependency is missing.

If the intent document only gives meaning, do not infer physical deletion unless it explicitly says so.

False negative is costlier than false positive: one vague master-plan verb can create many wrong micro plans.

## Output

Keep findings concise and phase-indexed:

```text
결론: PASS | FIX

수정 필요:
- Phase N: issue. Why it can be misread. Minimal wording.

유지 가능:
- Phase M: no ambiguity found.
```

Rules:

- Lead with blockers or wording risks.
- Prefer minimal wording changes.
- Do not expand the master plan into implementation detail.
- Do not judge detailed tests, migrations, or file lists unless the master plan includes them.
- If the plan needs deep adversarial consensus because order failure is expensive, recommend Forge separately.

## Common Failure Pattern

Intent says:

> source and tag must not be mixed.

Bad master wording:

> Remove Category.

Better master wording:

> Stop using Category meaning in runtime save/search/UI contracts. Physical deletion is a separate decision.

Reason: The intent fixed semantic separation, not necessarily database deletion.
