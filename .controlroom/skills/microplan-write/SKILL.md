---
name: microplan-write
description: Write or rewrite implementation-ready microplans from an approved master-plan phase map, selected phase, todo item, or narrowly scoped coding task. Use when the user explicitly asks for microplans, detailed implementation plans, task plans, or asks to turn master-plan phases/todos into implementable units. Do not use for broad requests like "make a plan", "create a roadmap", "plan this refactor", or "design a feature plan"; those belong to masterplan-write.
---

# Microplan Write

## Trigger Boundary

Use this skill only after a master plan, phase, or specific implementation todo already exists or the user clearly asks for a detailed implementation unit.

Do not use this skill for broad planning requests. If the user asks for an overall plan, roadmap, refactoring plan, new-feature plan, migration plan, or "plan this topic" without selecting a concrete implementation unit, use `masterplan-write` instead.

A microplan is an implementation handoff artifact. Write it so `microplan-review` can approve it and `microplan-implement` can execute it without rediscovering scope, order, or completion criteria.

## Source Authority

Before writing, identify the current source of intent. When the project has a planning authority index or a named canonical GBrain page, use that source before older docs or search results.

Treat `local-docs/*`, deleted local planning docs, old master plans, and old microplans as historical references unless the current canonical source explicitly promotes them.

Write the microplan into the storage surface implied by the current source. If the project policy says durable plans live in GBrain, write or update GBrain/task artifacts and use local files only when the user asks for them or an execution tool needs temporary files.

When durable plans live in GBrain, microplan writing is not complete until every selected microplan has been saved with `gbrain put` or the available GBrain write tool and the parent package root has been updated with the task slugs and statuses. Do not leave microplans only in the chat response.

The canonical planning-package definition is the GBrain page `reference/gbrain-planning-package-protocol`. The rules below are the working summary. When they conflict with that page, follow the page and update this skill.

Use the topic planning package created or identified by `masterplan-write`:

- Package root slug: the stable topic slug.
- Master plan slug: `{package-root}/master-plan`.
- Microplan slugs: `{package-root}/task-001`, `{package-root}/task-002`, and so on in master-plan phase order.
- Root page task status values: `planned`, `reviewed`, `implementing`, `implemented`, `verified`, `blocked`, `superseded`.
- Root page task fields: slug, title, status, parent phase, dependencies, implemented commit when available, checks, notes.

If the source master plan has no package root, search GBrain for the same topic and either attach the work to the current same-topic package or stop and report that a package root is required before durable microplans can be completed.

If direct GBrain write access is unavailable, stop before presenting the plan as completed and report the exact slug and content for every microplan plus the exact package-root task-list update that must be written. Use temporary local artifacts only as execution handoff files, not as durable planning authority.

## Selection Mode

Choose scope from the conversation and source plan before writing.

- Phase-map mode: If the latest approved or reviewed master plan contains a Microplan Phase Map or microplan artifact candidates, and the user asks to write microplans without naming one phase, write one microplan for every listed phase candidate in master-plan order.
- Single-unit mode: If the user explicitly names one phase, todo, file, bug, or coding task, write only that one microplan.
- Clarification mode: Ask the user only when there is no recent phase map and no selected implementation unit.

In phase-map mode, keep each microplan independently small and implementation-ready. The request creates multiple small artifacts; it does not merge the whole master plan into one large microplan.

## Planning Hierarchy

Use this hierarchy when the work has more than one task:

```text
Context
→ what domain world is correct

Master Plan
→ what order closes that world safely

Phase
→ one meaning axis to close

Task
→ the smallest implementable and verifiable unit
```

Do not treat many phases or tasks as a problem when Context and Master Plan are solid. Context is solid when it states intent, reasons, exclusions, and decision boundaries. Master Plan is solid when it states phase order and what each phase closes. This skill starts below that level: it turns each selected phase or todo into the smallest implementable and verifiable unit.

## Preparation Gate

Before writing the plan, run a short preparation pass inspired by Superpowers brainstorming, but keep it microplan-sized.

Answer these questions from the current source of intent, current code, and the selected phase or task. In phase-map mode, answer them separately for each microplan. Ask the user only when the answer is absent or ambiguous:

- What domain meaning does this task close?
- What is explicitly out of scope?
- What can the next task rely on after this task is complete?
- Which existing code, document, command, or test must be read before implementation?
- Which 1-3 checks prove the task is complete?

If any answer is unclear, resolve it before writing the CRUD table. Do not compensate for unclear intent by adding more implementation tasks.

## Core Shape

Write implementation handoff plans in this order:

1. Domain contract
2. CRUD table
3. Order and dependencies
4. Completion gate

Keep the plan short. For every sentence, ask: "Is this required for implementation or phase handoff?" Remove background, commentary, and nice-to-have detail that does not change what gets built, in what order, or how completion is judged.

Size and scope limits:

- Target 150 lines or fewer.
- Never exceed 180 lines. Split the plan when it would exceed this.
- These limits exist to keep the plan reviewable by `microplan-review` and implementable as one closure unit.
- Include at most 3 leaf implementation tasks in one plan.
- The tasks must share the same meaning axis. If 3 tasks touch different domain meanings, split them.
- Each leaf task must be independently plan-reviewable, implementable, and implementation-reviewable.
- If verification cannot be expressed as 1-3 focused checks, the task is too large.
- Put high-risk work such as deletion, data migration, permission changes, or automatic decision removal in its own small plan when possible.

Closure rule:

- A task is not complete because code changed.
- A task is complete only when the next task can rely on its contract without redefining it.
- Phase-level plans should end with a final leak/check gate when later phases depend on the phase meaning. A leak is old meaning still visible in runtime code, UI text, prompts, commands, tests, or user paths.

## 1. Domain Contract

State what meaning this plan fixes before code changes begin.

Answer:

- What domain concept is being fixed?
- What ambiguity is being removed?
- What must later phases be able to assume without redefining?
- What is explicitly out of scope?

Prefer business meaning over implementation labels. Avoid naming the phase after a specific technical migration unless that migration is the domain purpose.

## 2. CRUD Table

List implementation targets by CRUD impact.

Use a compact table:

| CRUD | Target | Why |
| --- | --- | --- |
| Create | New model, field, service, flow, test fixture, or document artifact | What new capability or contract it creates |
| Read | Audit, query, search, view, report, validation, or discovery point | What existing behavior must be understood or verified |
| Update | Existing model, service, command, UI, prompt, migration, or test | What meaning changes |
| Delete | Legacy model, field, branch, UI, compatibility shim, command, or test assumption | What confusion or obsolete path is removed |

Rules:

- Include only targets that affect implementation order, data preservation, or phase readiness.
- If a target does not change behavior or verification, omit it.
- Separate source/provenance, domain tags, UI labels, status, and workflow state when their meanings differ.

## 3. Order And Dependencies

Explain which CRUD must happen first and why.

Use dependency logic:

- Read before Create when current usage or data shape is uncertain.
- Create before Update when existing data needs a new safe destination.
- Update before Delete when live code still depends on the old structure.
- Delete last when removing old concepts could cause data loss or broken flows.

State blockers plainly. A good order section tells the implementer what is unsafe to do first.

## 4. Completion Gate

Define the conditions for moving to the next phase.

Completion gates should be observable:

- Domain meaning is represented in code.
- Legacy meaning no longer leaks through models, services, UI, prompts, commands, or tests.
- Required data is preserved or intentionally discarded.
- Focused tests or verification commands prove the contract.
- The next phase can rely on the contract without restating it.

Avoid vague gates such as "cleaned up", "improved", or "done". Replace them with conditions that can be checked.

## Frontend And Template Plans

Frontend plans are usually more complex than backend plans because they must close a user path, not just a data or service contract.

For templates, HTMX partials, forms, modals, navigation, or visual workflow changes, write the phase around a user flow or screen meaning, not around a file list.

Add completion gates for:

- What decision or action the user can complete on the screen.
- Which old path is no longer exposed.
- Whether visible wording matches the Context language.
- Whether click, submit, modal, and HTMX response states continue correctly.
- Whether the core action remains usable on narrow/mobile screens when relevant.

Use Playwright, Django client checks, or focused HTML assertions when a backend test cannot prove the user path. Django client or HTML assertions are enough for routing, rendered text, form presence, and permission visibility. Use Playwright for click flows, modals, HTMX swaps, responsive layout, or visual state.

## Writing Style

- Write for implementation, not broad planning or persuasion.
- Prefer tables for scope and short lists for sequence.
- Keep examples local to the current codebase or domain.
- Do not add speculative future features.
- Do not include commit strategy, pull request count, deployment procedure, master-plan phase design, or broad refactoring unless the user asks.
- If the source context contradicts the draft plan, stop and reconcile the domain contract first.
