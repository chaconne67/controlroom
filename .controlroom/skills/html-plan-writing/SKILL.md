---
name: html-plan-writing
description: Use when a plan, master plan, spec, or implementation guide should be written as an HTML document for both browser-based UI/UX review and agent implementation guidance.
---

# HTML Plan Document

## Purpose

Create an HTML plan document that works as both a browser-reviewable UI/UX artifact and an implementation guide for a future agent.

Think of the document as an **interactive manual before implementation**. It is not just a mockup. It lets the user try the intended flow, review UX details, and gives the implementing agent enough guidance to build the feature without guessing.

It has three roles:

- **User-flow manual**: shows what a real user sees, asks, clicks, and gets back.
- **Design/UX review tool**: lets the user inspect wording, layout, state changes, and mobile behavior in a browser.
- **Implementation guide**: records scope, internal boundaries, edge cases, phases, and validation criteria for the next agent.

The HTML is not a full app mockup. It should show only the user experience that the current task will create or change, then separate implementation explanation into document-like sections.

## Core Rule

Build the changed experience, not the surrounding product shell.

Include as visual UI:

- The screen, component, form, modal, tab, workflow, or state that this task changes.
- Scenario controls when reviewers need to inspect state changes.
- Mobile or responsive samples when layout or interaction can differ by viewport.

Do not build as visual UI:

- Existing global sidebar, app header, footer, or navigation that this task will not change.
- Decorative cards for explanation-only text.
- Whole-app chrome just to make the sample look complete.

If context is needed, show a minimal label or lightweight placeholder such as `Settings > Telegram`, not a full layout replica.

## Existing UI Boundary Rule

If the feature is inserted into an existing screen, template, tab, modal, or layout, do not recreate that existing UI as a visual mockup unless the task explicitly changes it.

Show only the new or changed user-facing area. Represent existing context with a minimal label, breadcrumb, or placeholder such as `Profile > Telegram tab selected`.

Existing UI belongs in implementation notes, not the visual preview. State where the new area is mounted, which existing template or component wraps it, and which surrounding UI must remain unchanged.

Example:

- Request: `프로필 화면의 탭들이 있고 Telegram 탭을 선택하면 아래 디자인이 나오도록 구현해라.`
- Visual preview: show only the new Telegram tab content, such as the chat or settings area.
- Implementation notes: reuse the existing profile screen and tab component; render the new component inside the existing Telegram tab panel; do not change the profile tabs themselves.

## Required Page Structure

Use these sections in order:

1. **Title and purpose**: short statement of what the document fixes or designs.
2. **Actual implementation preview**: the only area that should look like the final user-facing UI.
3. **Scenario controls or sample states**: realistic user questions, responses, errors, loading, success, and retry states when relevant.
4. **Mobile/responsive preview**: only the changed area, not the full mobile app shell.
5. **Implementation notes**: document-style explanation for the implementing agent.
6. **Decisions and unknowns**.
7. **Implementation phases**.
8. **Validation checklist**.

## File Location And Naming

Before writing the HTML file, inspect the project instructions that control documentation authority, location, and naming, such as `AGENTS.md`, `CLAUDE.md`, `GEMINI.md`, repository docs rules, or the project's current planning authority index.

Follow project-specific documentation rules over these defaults.

Defaults when no project rule exists:

- Treat the HTML file as a browser-review artifact, not as the durable source of truth for the plan.
- Save HTML plan documents under `tmp/html-review/{topic}/`, not under static UI sample, asset, fixture, seed, template, runtime, or long-term documentation directories.
- Create the topic directory before writing the file.
- Put a broad master plan at `{topic}/마스터플랜-YYYY-MM-DD.html` or `{topic}/master-plan-YYYY-MM-DD.html`.
- Put phase or micro plan HTML under `{topic}/마이크로플랜/` or `{topic}/microplans/` when multiple phase documents are expected.
- Use descriptive topic and file names centered on the user's domain language. In Korean projects, keep the filename mostly Korean and place the date at the end.
- Keep related temporary review reports and validation captures under the same topic directory unless the project has a stronger convention.
- Use `static/`, `assets/`, or `ui-sample/` only for actual reusable app assets or standalone UI samples that are not serving as planning documents.
- After review, distill accepted durable decisions into the project's current canonical planning source. If the project uses GBrain or another external planning authority, update that source instead of promoting the temporary HTML file into repository documentation.

## Separation Rules

- Label the user-facing preview as `실제 구현 화면 샘플`.
- Label agent-only explanation as `구현 메모` or `구현 설명`.
- Mark agent-only explanations with wording such as `실제 화면에는 표시하지 않음`.
- User-facing preview copy must use user meaning, not internal system names.
- Internal system names, architecture, security rules, and edge cases belong only in implementation notes.

Example boundary:

- User-facing preview: `Telegram 업무 비서 만들기`
- Implementation notes: `내부적으로 Hermes 프로필과 Telegram gateway를 설정한다`

## Scenario Rules

Scenarios should be concrete enough for implementation.

Include realistic user questions and system responses, especially for:

- First use
- User confusion
- Missing prerequisites
- Invalid input
- Loading or processing
- Success
- Failure and retry

For UI work, static screenshots are not enough when behavior changes. Provide buttons, tabs, or visible state blocks that let a reviewer inspect the important states in the browser.

## Design Rules

- Follow the project design system when one exists.
- Keep visual fidelity focused on the changed area.
- Avoid visual noise that could make unchanged UI look like part of the implementation request.
- Explanation sections should read like a document, not like product UI.
- If the user asks for a `localhost:8000` URL, serve the HTML through `http://localhost:8000/...` according to the project preview rule.

## Self-Check

Before finishing, verify:

- The visual UI contains only the area that will be implemented or changed.
- Unchanged app shell is absent or reduced to minimal context.
- The implementation notes cannot be mistaken for user-facing UI.
- User-facing copy does not expose internal names.
- Edge cases are visible as scenarios or documented in implementation notes.
- Mobile/responsive behavior is represented when relevant.
