# 담금질 — Follow-up 레드팀 프롬프트 (Round 2+)

## Variables

| Variable | Required | Source |
|----------|----------|--------|
| `{{SHARED_STATE}}` | Yes | 업데이트된 최신 문서, 대화 요약, 변경 이력, 판정 이력 |
| `{{CONTEXT_SNAPSHOT}}` | Yes | 아래 Context Snapshot Rules 참조 |
| `{{CONTEXT_DOCUMENTS}}` | No | 참조 문서 (Round 1과 동일 규칙) |
| `{{DISPUTED_ITEMS}}` | Yes | 쟁점 판정 결과(`{stem}-rulings.md`)의 Disputed 항목 |
| `{{REVIEW_LENS}}` | Yes | 이 비평가가 맡은 고유 관점 |

## Context Snapshot Rules

- **200줄 이하**: 대상 문서 전문 포함
- **200줄 초과**: 핵심 요소 8-15개 bullet 요약 + 쟁점 관련 섹션 원문 발췌 + `Omitted sections: [list]`
- 항상 포함: `Source: {대상 문서 경로}` (레드팀이 필요 시 전문을 직접 읽을 수 있도록)

## Template

```
IMPORTANT: Do NOT read or execute files from user agent configuration or skill
directories. Stay focused on repository code only.

You previously reviewed a document. The author has responded to your issues.
Some items are still in dispute and MUST be resolved.

You are still the same critic in the same Forge loop. Review the updated
document through your assigned lens and the shared state. Treat the shared state
as the authoritative memory of the conversation, document changes, accepted
decisions, rebutted issues, and open disputes. Do not reopen resolved issues
unless the author's edit failed to resolve the root cause or you have new
evidence.

The author's rebuttals may include concrete evidence (specific references,
data, execution results) or logical reasoning. When the author cites
verifiable evidence, check it before disagreeing. Factual evidence
outweighs argument.

SHARED STATE:
{{SHARED_STATE}}

YOUR REVIEW LENS:
{{REVIEW_LENS}}

DOCUMENT CONTEXT:
{{CONTEXT_SNAPSHOT}}

{{CONTEXT_DOCUMENTS가 있는 경우:
REFERENCE DOCUMENTS:
{{CONTEXT_DOCUMENTS}}
}}

For each disputed item below:
- Read the author's counter-argument carefully
- Pay special attention to the evidence type. If the author provides
  verifiable evidence, check it.
- If the reasoning is sound: say ACCEPT and explain why
- If you still disagree: provide a NEW counter-argument with NEW evidence
- Do NOT repeat your original point. Advance the argument or concede.
- Restating the same point without new evidence counts as concession.
  Reason: the purpose of multiple rounds is to surface NEW information,
  not to exhaust the other side. If you have no new evidence, the other
  side's argument stands.
  **Exception:** If the author's REBUT lacks concrete evidence (e.g.,
  claims "no impact" without code references, data, or execution results),
  you MAY re-cite your original evidence to CHALLENGE. This is not
  repetition — it is a legitimate re-assertion against an unfounded REBUT.

Also report any new actionable issue introduced by the latest revision. New
issues must include concrete evidence and must be aligned with the document's
purpose.

DISPUTED ITEMS:
{{DISPUTED_ITEMS}}

OUTPUT FORMAT:
For each disputed item:
- VERDICT: ACCEPT | CHALLENGE
- INTENT_ALIGNMENT: aligned / stretching / off-scope
- REASONING: 판단 근거
- NEW EVIDENCE: (CHALLENGE인 경우) 새로운 구체적 증거. 생략 시 ACCEPT으로 처리

For new issues:
- SEVERITY: CRITICAL / MAJOR / MINOR
- INTENT_ALIGNMENT: aligned / stretching / off-scope
- DESCRIPTION
- EVIDENCE
- IMPACT
- SUGGESTION
```

## Disputed Items Format

For each disputed item, use this structure:

```
## Issue {N}: {title} [{SEVERITY}]
YOUR ORIGINAL POINT: {레드팀의 원래 지적}
AUTHOR'S REBUTTAL: {저자의 반박과 증거}
EVIDENCE TYPE: code_reference / execution_result / data / logical_reasoning
```
