# CRETOP Information-Stop Confirm Recovery Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 정보제공중지 팝업의 실제 확인 버튼을 누르고 팝업 소멸을 검증한 뒤 기존 스마트검색 복귀 경로로 다음 기업을 처리한다.

**Architecture:** 기존 `company_data_unavailable` 예외 경로를 유지한다. 예외 본문에 따라 확인 좌표와 소멸 마커만 선택하고, 공용 복구 함수는 마커 소멸 후 기존 상단 스마트검색 복귀 함수를 호출한다.

**Tech Stack:** Python, pytest, pyautogui 기반 원격 데스크톱 어댑터

---

### Task 1: 팝업별 복구 계약 고정

**Files:**
- Modify: `scripts/test_cretop_agent.py`

- [x] **Step 1: 실패 테스트 작성**

```python
def test_information_stop_recovery_uses_popup_button_and_waits_until_dismissed():
    # (960, 694) 클릭 → 정보제공중지 문구 소멸 → 스마트검색 복귀 순서를 검증한다.

def test_unavailable_router_selects_popup_specific_recovery_contract():
    # 정보제공중지와 재무정보 비공개가 각 좌표와 소멸 마커를 전달하는지 검증한다.
```

- [x] **Step 2: 실패 확인**

Run: `uv run pytest -q scripts/test_cretop_agent.py -k 'information_stop_recovery or unavailable_router'`

Expected: 전용 좌표 또는 새 복구 인자가 없어 FAIL.

### Task 2: 기존 예외 복구 단계 수정

**Files:**
- Modify: `scripts/cretop_agent.py`

- [x] **Step 1: 전용 좌표 추가**

```python
INFORMATION_STOP_CONFIRM_POINT = {"x": 960, "y": 694}
```

- [x] **Step 2: 팝업 소멸 검증으로 교체**

```python
popup_outcome = self._click_and_confirm(
    lambda: self.desktop.click(confirm_point["x"], confirm_point["y"]),
    lambda: self._wait_copied_page_marker_absent(
        dismiss_marker,
        interval_seconds=interval_seconds,
        timeout_seconds=timeout_seconds,
    ),
)
```

- [x] **Step 3: 예외 본문별 계약 전달**

```python
information_stop = "정보제공중지" in text
confirm_point = INFORMATION_STOP_CONFIRM_POINT if information_stop else CENTER_CONFIRM_POINT
dismiss_marker = "정보제공중지" if information_stop else "공개되지 않습니다"
```

- [x] **Step 4: 집중 테스트 통과 확인**

Run: `uv run pytest -q scripts/test_cretop_agent.py -k 'information_stop_recovery or unavailable_router or company_failure_recovery'`

Expected: PASS.

### Task 3: 운영 문서와 최종 경로 검증

**Files:**
- Modify: `docs/cretop/final_collection_procedure.md`
- Modify: `/home/chaconne/.codex/skills/cretop-automation/SKILL.md`

- [x] **Step 1: 팝업별 좌표와 성공 조건 기록**

- 정보제공중지와 재무정보 비공개 좌표를 분리한다.
- 상세 마커가 아니라 팝업 문구 소멸을 성공 조건으로 기록한다.

- [x] **Step 2: 전체 CRETOP 단위 테스트 실행**

Run: `uv run pytest -q scripts/test_cretop_agent.py`

Expected: PASS.

- [x] **Step 3: 전체 프로젝트 테스트 실행**

Run: `uv run pytest -q`

Expected: PASS.

- [x] **Step 4: 코드 리뷰 후 커밋**

```bash
git add scripts/cretop_agent.py scripts/test_cretop_agent.py docs/cretop/final_collection_procedure.md docs/superpowers/specs/2026-07-16-cretop-info-stop-confirm-recovery-design.md docs/superpowers/plans/2026-07-16-cretop-info-stop-confirm-recovery.md
git commit -m "fix(cretop): confirm information-stop popup reliably"
```
