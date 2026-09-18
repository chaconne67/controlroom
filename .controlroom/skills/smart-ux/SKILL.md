---
name: smart-ux
description: "Use when designing, creating, modifying, or reviewing product UI and user flows for usability, accessibility, or ethical behavioral design."
---

# Smart UX

Use this skill to turn UI work into behavior-aware product design, not only visual styling. The central rule is: good UX changes behavior by lowering friction, clarifying choices, creating honest motivation, and protecting user agency.

## Workflow

Run this sequence before changing UI code and repeat the checklist after changing it.

1. Define one target behavior for the screen and apply the Information Necessity rules to its content.
2. Map that behavior to the Hook loop: trigger, action, variable reward, investment.
3. Apply the UX laws that reduce friction and cognitive load.
4. Satisfy the accessibility requirements.
5. Reject dark patterns and keep persuasion honest.
6. Verify the final UI with the completion checklist.

## Information Necessity

화면은 사용자가 업무를 판단하고 수행하는 곳이다. 내부 구현을 설명하려고 정보를 늘리면 필요한 정보가 묻힌다.

- 문구·수치·배지를 추가하기 전에, 그것을 빼면 사용자의 어떤 판단·행동·현재 상태나 결과 이해에 무엇이 부족해지는지 구체적으로 확인한다. 데이터가 존재하거나 계산했다는 사실, 막연한 친절함은 표시 근거가 아니다. 근거가 없으면 추가하지 않는다.
- 내부 집계·처리 구분을 그대로 노출하지 않는다. 업무에 필요한 경우에만 사용자의 말로 바꾸고, 그 정보가 필요한 판단이나 행동 가까이에 둔다. 가끔 필요한 세부 정보는 기존 상세보기 흐름을 활용하고, 필요 없는 정보를 툴팁·접기 영역으로 옮겨 남기지 않는다.
- 설명이 길어지면 먼저 제목·레이블·정보 배치·조작 흐름을 명확히 한다. 같은 내용을 보조 문구로 반복해 구조의 모호함을 덮지 않는다.
- 클릭할 일이 없다는 이유만으로 정보를 지우지 않는다. 입력 조건·오류 이유·진행 상태·처리 결과처럼 올바른 사용과 상태 이해에 필요한 안내, 접근성 및 명시적 요구사항은 보존한다.
- 판단 근거는 작업 설명에 남기고 제품 화면에 메타 설명으로 추가하지 않는다. 기존 요소를 제거할 때도 같은 기준과 승인된 변경 범위를 적용한다.

## Hook Loop

Design core screens so one useful loop can complete.

| Step | Meaning | UI obligation |
| --- | --- | --- |
| Trigger | Signal that starts the action | Provide one clear CTA, empty-state next step, or notification entry point. |
| Action | Smallest useful action | Reduce clicks and fields. Use defaults and autocomplete when they reflect real user intent. |
| Variable reward | Positive feedback with some freshness | Show completion feedback, progress, new value, or light celebration without manipulating the user. |
| Investment | User effort that increases future value | Make saved settings, profiles, lists, follows, drafts, or preferences visibly accumulate. |

Use variable reward only when it reflects real value. Do not use it to create compulsion, hide costs, or make escape harder.

## Decision Load

- Hick's Law: Reduce simultaneous choices. Group options and use progressive disclosure.
- Miller's Law: Keep navigation, tabs, or dense lists in 5-7 meaningful chunks when possible.
- Tesler's Law: Decide whether the system or the user carries unavoidable complexity. Prefer defaults, inference, and automation when they are accurate.
- Occam / Pragnanz: Remove decorative or duplicate elements that do not help recognition or action.
- Pareto: Put the small set of high-value actions in the strongest locations.

## Interaction

- Fitts's Law: Make frequent or important targets large, close, and easy to reach. Keep touch targets at least 44 by 44 px.
- Doherty Threshold: Preserve perceived responsiveness. For slower work, show immediate loading, skeleton, progress, or optimistic feedback.
- Goal Gradient / Zeigarnik: Use steps, progress, completion percentage, or visible unfinished state when completion matters.
- Serial Position Effect: Place the most important list or nav items where users remember them: first or last.
- Von Restorff: Make one primary action stand out. Avoid multiple competing CTAs.
- Peak-End Rule: Design success, error, and exit moments carefully because they shape the remembered experience.

## Familiarity

- Jakob's Law: Prefer conventions users already know, such as expected navigation, cart, search, save, and home patterns.
- Gestalt grouping: Put related elements near each other, inside a shared region, or under a shared label.
- Similarity: Use consistent shape, color, and placement for the same action or state.
- Postel's Law: Accept flexible input formats when safe. Give strict, clear output and avoid blaming the user for errors.

## Accessibility

Treat these as completion requirements.

- Use semantic HTML: `button`, `nav`, `main`, headings, labels, and native controls where possible.
- Ensure keyboard access: Tab order, Enter/Space activation, and no keyboard traps.
- Keep visible `:focus-visible` styles.
- Give every input and icon button an accessible name.
- Meet contrast: 4.5:1 for body text and 3:1 for large text.
- Keep touch targets at least 44 by 44 px with usable spacing.
- Respect `prefers-reduced-motion`; avoid unavoidable autoplay or excessive motion.
- Use ARIA only when native semantics are insufficient.
- Announce loading, error, and empty states when screen-reader users need the state change.

## Ethical Guardrails

Never implement these patterns. Offer a transparent alternative when requested.

- Hiding or complicating cancellation, deletion, opt-out, unsubscribe, or account closure.
- Charging after a trial without clear prior consent and visible cancellation.
- Guilt-based copy such as manipulative refusal labels.
- Fake urgency, fake scarcity, fake countdowns, or fake social proof.
- Pre-checked consent or extra-charge boxes.
- Misleading button color, placement, or wording that induces mistaken clicks.
- Infinite scroll, autoplay, or reward loops without escape, pause, or control.

Use good friction when it protects the user: destructive-action confirmation, payment summary, undo windows, and review steps for irreversible changes.

## Completion Checklist

Before reporting a UI task complete, verify each item and fix misses in the same final path.

- The screen has one dominant target behavior and one clearly prioritized primary CTA.
- Choices are chunked or progressively disclosed.
- Review visible copy, metrics, and badges against Information Necessity: remove unsupported additions and duplicate explanations; retain information needed to use the screen and understand its state or outcome.
- Main actions are large, close, reachable, and at least 44 by 44 px on touch.
- Loading or latency receives immediate visible feedback.
- Progress, completion, or unfinished state is visible when it motivates completion.
- Success moments provide honest feedback or next value.
- Familiar conventions are preserved unless the product value requires a different pattern.
- Related elements are grouped with clear spacing, alignment, and hierarchy.
- Errors and empty states explain the next action without blaming the user.
- Accessibility requirements above are satisfied.
- No dark pattern is present.

## Source Basis

Sources: "The UX Psychology Behind Apps People Can't Stop Using", Laws of UX, the Hook Model,
accessibility rules, and ethical AI/product UX guardrails.
