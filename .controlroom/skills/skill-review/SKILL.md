---
name: skill-review
description: Use when the user says "skill-review", "스킬리뷰", "스킬 점검", or asks to review and revise a Codex skill.
---

# Skill Review

## Core Rule

Review one Codex skill with both `$prompt-guide` and `$skill-writing-guide`, revise it, then review again. Repeat until there are no remaining prompt-quality, skill-writing, metadata, or validation issues.

## Scope

Review only the requested skill folder unless the user names related skills to update.

Always inspect:

- `SKILL.md`
- `agents/openai.yaml` when present
- directly referenced resources that affect the instruction

Do not create extra documentation files.

## Review Loop

1. Read `$prompt-guide`.
2. Read `$skill-writing-guide`.
3. Read the target skill's `SKILL.md`.
4. Read `agents/openai.yaml` if it exists.
5. Review for real behavior risks only:
   - trigger description is too broad, too narrow, or not minimal enough
   - missing reason or replacement behavior for prohibitions
   - hardcoded one-off rules instead of general principles
   - ambiguous actor, object, step, or output
   - repeated terminology for the same concept
   - low-value wording that does not change agent behavior
   - stale examples, stale step numbers, or contradictory workflow rules
   - missing stop condition for risky loops
6. Edit the skill to fix only those issues.
7. Run the skill validator.
8. Re-read the changed sections and repeat from step 5.

Stop only when:

- latest review finds no actionable issues
- `quick_validate.py` passes
- any intentionally skipped check has a concrete reason

## Description Rule

Keep the YAML `description` minimal and trigger-focused. Include only enough wording for Codex to know when the skill should activate. Put workflow details in the body, not the description.

## Editing Rules

- Preserve the skill's original purpose.
- Prefer one clear rule over several exception patches.
- Remove examples when the rule is already clear.
- Keep examples only when they clarify a boundary that a model would otherwise misread.
- Use one term for one object or step.
- Make loops state their exit condition.
- Make stop conditions explicit for approvals, unsafe actions, missing tools, or repeated blockers.

## Validation

Run:

```bash
python3 "<CODEX_SKILL_CREATOR_DIR>/scripts/quick_validate.py" /path/to/skill
```

Resolve `<CODEX_SKILL_CREATOR_DIR>` from the active Codex system skill location. If that native
validator is unavailable, report it and perform the remaining structural checks without inventing a path.

Also check the edited text for:

- unbalanced Markdown fences
- unfinished placeholder markers
- stale step references
- duplicated or conflicting names
- description that contains body-level workflow details

## Report

Report:

- files changed
- final validation result
- remaining risks, if any

Do not include a long review transcript when all issues were fixed.
