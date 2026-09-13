# CRETOP Operator Stop Message Implementation Plan

> **For agentic workers:** Implement inline without another approval. The user approved the operator-facing message contract in the preceding conversation.

**Goal:** Make every future CRETOP stop notification explain the failed stage, operational cause, recovery result, current screen, and exact batch progress without exposing internal exception text.

**Architecture:** The browser step that detects a failure produces structured operator context while retaining the technical exception in the JSON log. `collect_batch_fast()` preserves the original failure and recovery failure separately. `build_telegram_batch_message()` renders only the structured fields and never parses or forwards raw exception messages.

**Tech Stack:** Python 3.13, pytest, Telegram Bot HTTP API

---

## Approved message contract

```text
[CRETOP SSP 작업 중단]

실행 ID: <run id>
발생 시각: <local timestamp>
진행: <completed>건 완료 / <ordinal>번째 처리 중 중단 / <unstarted>건 미실행

회사: <company>
사업자번호: <business number>

중단 단계: <operator stage>
원인: <operator reason>
복구 결과: 실패 — <operator recovery reason>
현재 화면: <short classified screen>
```

- Do not include exception class names, marker arrays, raw copied text, tracebacks, or retry counters.
- Keep those technical values in the outbox JSON and log.
- Do not hardcode a company, business number, run ID, or one error string.

## Files

- Modify: `scripts/cretop_agent.py`
- Modify: `scripts/test_cretop_agent.py`
- Modify: `docs/superpowers/plans/2026-07-15-cretop-telegram-stop-notification.md`
- Modify: `/home/chaconne/.codex/skills/cretop-automation/SKILL.md`
- Update: GBrain CRETOP Telegram stop-notification rule

### Task 1: Lock the operator contract

- [x] Add a failing message test for the observed 72nd-company stop payload.
- [x] Assert exact progress semantics: 71 completed, 72nd stopped, 28 unstarted.
- [x] Assert original failure stage/reason is shown separately from recovery failure.
- [x] Assert technical exception names and raw marker text are absent.
- [x] Add a second failing test for a different stage to prevent case-specific formatting.

### Task 2: Produce structured failure context

- [x] Preserve the last copied screen as an exception attribute instead of only embedding it in a message string.
- [x] Classify mechanically observable screens into short labels such as search result count, detail page, Smart Search, landing, relogin, and unknown screen.
- [x] Attach stage and operator reason at existing SSP boundaries: preflight, landing reset, Smart Search entry/reset, company search, detail entry, Briefing entry, each detail section, and company recovery.
- [x] Preserve stage context when click-marker retries exhaust.
- [x] Store `failure` and `recovery_failure` dictionaries alongside existing technical fields.

### Task 3: Replace Telegram rendering

- [x] Remove `오류 유형` and raw `상황` output from stopped messages.
- [x] Render the approved fields from structured failure context only.
- [x] Use a safe operator fallback when a completely unexpected exception lacks structured context.
- [x] Leave completion messages unchanged.

### Task 4: Verify and document

- [x] Run focused Telegram and CRETOP tests.
- [x] Run the complete project test suite and Ruff.
- [x] Review the scoped diff for raw-error leakage, wrong progress counts, lost technical JSON, and case-specific branches.
- [x] Update the CRETOP skill, plan, and GBrain rule.
- [x] Commit only this task's files.

Remote deployment and live Telegram delivery are outside this code-change request.
