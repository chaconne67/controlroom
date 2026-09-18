---
name: forge
description: >
  Use when a plan, design, specification, or decision document needs adversarial
  consensus review before implementation. Triggers: "Forge", "계획 검증",
  "담금질", "forge a plan", or high-cost plans where gaps would be expensive.
---

# Forge — Codex Adversarial Consensus Review

## Core Rule

Forge는 작성자 서브에이전트 1명과 비평가 서브에이전트 2명을 동시에 유지한다.
작성자가 문서를 수정하고, 두 비평가가 같은 맥락으로 리뷰하며, 메인 Codex가
비평을 작성자에게 전달해 판정과 수정을 받는다. 이 라운드를 실행 가능한 지적이
없을 때까지 반복하고, 수용한 변경을 대상 문서에 직접 반영한다.

모든 참여자(오케스트레이터, 작성자, 두 비평가)는 같은 대화 흐름, 같은 최신 문서,
같은 변경 이력, 같은 판정 이력을 공유해야 한다. 맥락 동기화 없이 비평만 반복하면
트집잡기와 방향 이탈이 발생하므로, 매 라운드마다 공유 상태를 갱신해 모든
참여자에게 전달한다.

실패 비용은 비대칭이다. 잘못된 ACCEPT은 공방을 끝내 복구가 어렵고, 잘못된
REBUT은 다음 라운드에서 교정된다. 확신 없으면 REBUT하되, 근거 없는 REBUT은
허용하지 않는다.

## When To Use

- 대규모 구현, 운영 영향, 다단계 프로젝트처럼 나쁜 계획의 비용이 큰 경우
- 단일 리뷰 관점으로는 리스크를 충분히 찾기 어려운 경우
- 사용자가 `Forge`, `계획 검증`, `담금질`을 명시한 경우

## When Not To Use

- 단순 버그 수정, 단일 파일 변경, 구현 경로가 명백한 경우
- 사용자가 계획 단계를 건너뛰라고 한 경우
- 여러 독립 todo를 한꺼번에 처리해야 하는 경우

## Parameters

| Parameter | Required | Description | Default |
| --- | --- | --- | --- |
| `document` | yes | 담금질할 파일 경로 또는 canonical source identifier | none |
| `topic` | yes | slug 식별자. 센티널 마커에 사용 | infer or ask |
| `forge_dir` | no | 임시 산출물 디렉토리 | `tmp/forge/codex/{topic}/` |
| `context` | no | 참조 문서 목록 | none |

Derived:
- `stem`: file stem or safe slug derived from the canonical source identifier
- source document: the live source identified by `document`
- rulings: `{forge_dir}/debate/{stem}-rulings.md`
- sentinel: `<!-- forge:{topic}:{stem}:complete:{ISO 8601 timestamp} -->`, used only for writable file documents

## Source Authority

Forge reviews the current source of truth, not whichever old plan file is easiest
to find. Before preparing context, inspect the project's planning authority rules.

If the target topic is governed by a canonical planning source such as GBrain,
read that source first and treat local document mirrors, deleted repository
plans, old masterplans, and old microplans as historical context unless the
canonical source explicitly promotes them.

Forge debate files are temporary evidence. Apply accepted decisions to the
original `document` when it is a live file source. When the live source is an
external canonical source such as GBrain, update that source or report the exact
canonical update required; do not create a new local plan as the durable record
unless the project explicitly requires it.

## Subagent Roles

Forge uses exactly three live subagents unless the user explicitly requests a
different panel:

- `author`: revises the source document and answers critic findings.
- `critic_a`: reviews from the highest-risk technical or operational lens.
- `critic_b`: reviews from the strongest different lens for the document.

The main Codex is the `orchestrator`. The orchestrator owns shared-state
updates, issue deduplication, rulings, source-document edits, debate-log writes,
and deciding whether the stop condition is met.

Do not use external model CLIs or APIs as reviewers.

Keep the same three subagents across rounds. Use `send_input` for follow-up
rounds so the author and critics retain debate memory instead of restarting as
fresh reviewers.

Choose the two critic lenses from the document's real risk surface, such as
implementation feasibility, domain correctness, operational risk, security and
data integrity, or UX workflow. The two lenses must not duplicate each other.

## Shared State Packet

Every author and critic message must include a shared state packet:

- source document path and current content or targeted snapshot
- document purpose and author intent
- preserved decisions that should not be relitigated without new evidence
- project constraints and referenced context files
- conversation digest covering the review flow so far
- document change log since round 1
- accepted rulings and already-applied changes
- rebutted rulings with evidence
- current disputed items
- off-scope criteria

The packet is the working memory for the whole panel. The orchestrator must
update it after every author revision and critic review, then send the updated
packet and latest document snapshot to all three subagents before asking for the
next action. This prevents critics from drifting into taste-based or off-purpose
nitpicks while preserving adversarial pressure.

The shared state packet must distinguish:

- current document content
- what changed in the latest author revision
- which critic findings are resolved
- which critic findings remain open
- why rebutted findings should not be reopened without new evidence

## Subagent Execution

Build critic prompts from `references/round1-prompt.md`. Build author response
prompts from `references/author-response-prompt.md`. For follow-up critic
rounds, use `references/followup-prompt.md`.

If the multi-agent tool is not already loaded, use `tool_search` to expose it.
Spawn the three subagents with `multi_agent_v1.spawn_agent`. If tool policy
requires explicit user consent before spawning, ask once before spawning them.
If no subagent tool is available or consent is denied, stop and tell the user
Forge cannot run in this session.

Run both critics independently. Merge duplicate issues by same section and same
root cause. If both critics identify the same issue, raise severity one level.

Send the merged findings to the author. The author must classify each issue as
`ACCEPT`, `REBUT`, or `PARTIAL`, then provide either a source-document patch or
concrete rebuttal evidence. Apply accepted changes to writable live sources
before the next critic round. If the live source is external and cannot be
written directly, apply the accepted change to the debate snapshot and shared
state, record it as `canonical_update_pending` in rulings, and use that updated
snapshot as the current document for the next critic round.

## Output Structure

```text
{forge_dir}/
  debate/
    {stem}.md
    {stem}-rulings.md
    debate-log.json
```

Copy the source content to `{forge_dir}/debate/{stem}.md` before tempering if it
is not already there. For external sources, write a snapshot with the source
identifier and retrieved content. The copy is debate evidence only; final
accepted changes are applied to the live source or reported as the exact
canonical-source update required.

Use `references/consensus-format.md` for `{stem}-rulings.md`.

`debate-log.json` records each round:

```json
{
  "topic": "{topic}",
  "document": "{document path or canonical source identifier}",
  "stages": {
    "{stem}": {
      "status": "completed|in_progress|failed",
      "roles": {
        "author": "{agent_id}",
        "critic_a": "{agent_id}",
        "critic_b": "{agent_id}"
      },
      "rounds": [
        {
          "round": 1,
          "shared_state": {
            "document_snapshot": "summary or path",
            "conversation_digest": "round context summary",
            "document_change_log": ["change summary"],
            "resolved_items": ["issue ids"],
            "open_items": ["issue ids"]
          },
          "issues": [
            {
              "id": "R1-01",
              "severity": "CRITICAL|MAJOR|MINOR",
              "intent_alignment": "aligned|stretching|off-scope",
              "title": "issue title",
              "attack": "red-team argument summary",
              "action": "accepted|rebutted|partial",
              "response": "author response summary",
              "evidence_type": "code_reference|execution_result|data|logical_reasoning",
              "author_accepted": true
            }
          ]
        }
      ],
      "summary": {"rounds": 2, "issues": 3, "accepted": 2, "rebutted": 1}
    }
  }
}
```

Truth source priority:
1. updated debate snapshot and shared state while `{stem}-rulings.md` contains
   `canonical_update_pending`
2. live canonical source identified by `document`
3. sentinel marker for writable file documents
4. `{stem}-rulings.md`
5. `debate-log.json`

## Workflow

1. **Precheck**
   - Confirm the workspace context and source accessibility.
   - For file documents, confirm the file exists.
   - For external canonical sources, confirm the source can be read through its
     configured tool or command.
   - Confirm the document is the current planning authority for the topic, or
     replace it with the current canonical source before review.
   - Confirm subagent tool availability.
   - Select author, critic A, and critic B roles.
   - If a writable file document already ends with the sentinel, stop as complete.

2. **Prepare Context**
   - Read the target source content.
   - Read relevant project instruction or context files only as needed.
   - Apply context snapshot rules: files under 200 lines may be included in full;
     longer files should be summarized with relevant excerpts and source paths.

3. **Spawn Panel**
   - Spawn one author subagent and two critic subagents.
   - Send each subagent the shared state packet.
   - Tell critics their assigned lens and off-scope criteria.

4. **Critic Review**
   - Run both critic subagents independently.
   - Save combined findings to `debate/round-1-redteam.md`.
   - Merge duplicate issues by same section and same root cause.
   - If both critics identify the same issue, raise severity one level.
   - Discard off-scope findings unless they include concrete evidence that the
     document purpose or preserved decisions are wrong.

5. **Author Rebuttal And Revision**
   - Send merged critic findings to the author.
   - Require the author to evaluate each issue independently.
   - `ACCEPT`: issue has real impact; record the source-document change.
   - `REBUT`: no real impact; provide concrete evidence.
   - `PARTIAL`: part of the issue is valid; specify accepted action.
   - Evidence priority: `code_reference` > `execution_result` > `data` >
     `logical_reasoning`.
   - Apply the author's accepted changes to writable live sources.
   - If an external canonical source cannot be written directly, apply accepted
     changes to the debate snapshot and shared state, record
     `canonical_update_pending` in rulings, and use that snapshot as the current
     document for follow-up review.
   - Save to `debate/round-{N}-author.md`, update rulings and debate log.

6. **Follow-up Rounds**
   - Update the shared state packet with the author response, applied changes,
     resolved findings, open findings, and latest document snapshot.
   - Send the updated source document and updated shared state packet back
     to both critics.
   - Ask critics to review the revised document, not only disputed items.
   - Critics may keep prior issues open only with new evidence or a showing that
     the author's edit failed to resolve the root cause.
   - Repeating the same argument without new evidence counts as concession,
     except when the author rebuttal had no concrete evidence.
   - Send new or still-valid findings back to the same author subagent.
   - Send the same updated shared state packet to the author before requesting
     the next revision.
   - Repeat author revision and critic review until the stop condition is met.

7. **Stop Condition**
   - Complete when both critics report no actionable aligned issues.
   - Complete when remaining findings are all off-scope, taste-based, or repeated
     without new evidence.
   - Escalate to the user if a CRITICAL issue remains disputed after 5 rounds.
   - Escalate to the user if any issue remains disputed after 6 total rounds.

8. **Finalize**
   - Apply accepted changes directly to the live file document when `document`
     is a writable file source.
   - For external canonical sources, update that source with its configured tool
     or report the exact accepted update if direct write is unavailable.
   - Append the sentinel marker only to writable file documents.
   - Mark rulings COMPLETE and debate log completed.
   - Delete temporary `debate/round-*` files after completion.

## Red-Team Issue Format

Each issue must include:
- `SEVERITY`: CRITICAL / MAJOR / MINOR
- `INTENT_ALIGNMENT`: aligned / stretching / off-scope
- `DESCRIPTION`: what is wrong
- `EVIDENCE`: quoted text or concrete source
- `IMPACT`: when and how it breaks
- `SUGGESTION`: how to fix

`off-scope` issues do not block completion unless they prove the stated document
purpose or preserved decisions are themselves wrong.

## Author Response Format

```markdown
### Issue {N}: {title} [{SEVERITY}]
- **Action:** ACCEPT | REBUT | PARTIAL
- **Evidence type:** code_reference | execution_result | data | logical_reasoning
- **Response:** 판정 근거와 증거
- **Source-document change:** ACCEPT/PARTIAL인 경우 적용할 변경
```

## Checklist

- [ ] Precheck complete.
- [ ] Author, critic A, and critic B subagents spawned.
- [ ] Shared state packet sent to every participant each round.
- [ ] Round findings saved and deduplicated.
- [ ] Author rebuttal recorded with evidence.
- [ ] Accepted author changes applied to the live source or reported as the exact canonical update required.
- [ ] Rulings and debate log updated.
- [ ] Writable file documents updated with accepted changes and sentinel marker.
