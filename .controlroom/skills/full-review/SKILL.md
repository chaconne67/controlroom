---
name: full-review
description: Run a comprehensive multi-aspect review of a pull request or local diff. Use when the user asks for full-review, comprehensive PR review, broad review, or wants comments, tests, errors, types, code quality, and simplification checked together.
---

# Full Review

Run a broad review across independent quality dimensions, then aggregate the results into an action plan.

## Source

This skill was adapted from the Claude `pr-review-toolkit:review-pr` command copied from the production server. The original command is preserved at `references/claude-review-pr-command.md`.

Specialized reviewer references:

- `references/comment-analyzer.md`
- `references/pr-test-analyzer.md`
- `references/silent-failure-hunter.md`
- `references/type-design-analyzer.md`
- `references/code-reviewer.md`
- `references/code-simplifier.md`

Read only the references for review aspects that apply to the current change.

## Review Aspects

- `comments`: Check added or changed comments, docstrings, and documentation against the code.
- `tests`: Check behavioral test coverage quality and critical gaps.
- `errors`: Check error handling, swallowed exceptions, fallback behavior, and user-visible failures.
- `types`: Check newly added or materially changed types and invariants.
- `code`: Check project instructions, functional bugs, and general correctness.
- `simplify`: Check whether recently changed code can be made clearer while preserving behavior.
- `all`: Run every applicable aspect.

Default to `all` unless the user names specific aspects.

## Workflow

1. Determine scope:
   - For local changes, start with `git status --short` and `git diff --name-only`.
   - For a PR, use `gh pr view` and `gh pr diff`.
   - Respect user-provided file or aspect limits.
2. Select applicable aspects:
   - Always include `code`.
   - Include `tests` when tests or testable behavior changed.
   - Include `comments` when comments, docstrings, or docs changed.
   - Include `errors` when exception handling, fallback logic, API boundaries, jobs, or user-facing failures changed.
   - Include `types` when domain models, dataclasses, schemas, TypeScript types, or validation contracts changed.
   - Include `simplify` after correctness-focused passes, not before them.
3. Execute review passes:
   - If multi-agent tools are available, dispatch independent reviewers for applicable aspects and provide only the target scope plus the matching reference file.
   - If multi-agent tools are unavailable, run the passes sequentially yourself using the matching references.
4. Aggregate results:
   - Deduplicate overlapping findings.
   - Promote only issues with concrete evidence and practical impact.
   - Separate critical issues, important issues, suggestions, and strengths.
5. Provide recommended action:
   - Tell the user what to fix first.
   - Mention verification or re-review steps only when useful.

## Output Shape

Use this structure:

```markdown
**Critical Issues**
- ...

**Important Issues**
- ...

**Suggestions**
- ...

**Strengths**
- ...

**Recommended Action**
1. ...
```

If there are no findings in a section, omit that section.
