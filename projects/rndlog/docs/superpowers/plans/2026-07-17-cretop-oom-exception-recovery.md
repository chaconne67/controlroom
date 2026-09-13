# CRETOP OOM Exception Recovery Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** CRETOP V8 OOM 예외가 확인된 경우에만 완료 데이터를 저장하고 Chrome을 사람 방식으로 재시작한 뒤 중단 회사를 다시 수집한다.

**Architecture:** 정상 수집 경로와 기존 예외 분류는 유지한다. 기존 예외처리기가 캡처와 Crashpad 증거로 OOM을 분류하면 배치 루프가 완료 항목만 원자 체크포인트로 저장하고, 승인된 세 좌표로 Chrome 창 종료·작업표시줄 실행·CRETOP 북마크 진입을 수행한 뒤 기존 프리플라이트와 같은 회사 재시도를 사용한다.

**Tech Stack:** Python 3.13, Pillow, pyautogui, Windows Chrome, pytest

---

### Task 1: OOM 증거 판정

**Files:**
- Modify: `scripts/cretop_agent.py`
- Test: `scripts/test_cretop_agent.py`

- [x] OOM 오류 화면 형태와 CRETOP V8 Crashpad 주석이 함께 있을 때만 증거를 반환하는 실패 테스트 작성
- [x] `uv run pytest -q scripts/test_cretop_agent.py -k 'chrome_oom_evidence'`로 RED 확인
- [x] Pillow 화면 구조 판정과 최신 CRETOP V8 덤프 주석 판독 최소 구현
- [x] 같은 명령으로 GREEN 확인

### Task 2: 기존 예외처리기에 OOM 케이스 병합

**Files:**
- Modify: `scripts/cretop_agent.py`
- Test: `scripts/test_cretop_agent.py`

- [x] 본문 재복사 전에 OOM을 판정하고 `restart_chrome_and_retry`를 반환하는 실패 테스트 작성
- [x] 회사당 두 번째 OOM은 `stop_batch`와 정확한 OOM 알림 문맥을 반환하는 실패 테스트 작성
- [x] 두 테스트의 RED 확인
- [x] `_handle_company_exception()`에 OOM 분류만 병합하고 기존 분류 순서는 유지
- [x] 두 테스트의 GREEN 확인

### Task 3: 완료 결과 체크포인트와 동일 회사 재시도

**Files:**
- Modify: `scripts/cretop_agent.py`
- Test: `scripts/test_cretop_agent.py`

- [x] 첫 회사 완료 후 두 번째 회사 OOM을 모의하여 체크포인트에 첫 회사만 저장되는 실패 테스트 작성
- [x] OOM 회사가 재시작 후 같은 순번으로 다시 호출되는 실패 테스트 작성
- [x] RED 확인
- [x] OOM 전용 원자 체크포인트와 배치 루프의 OOM action 처리 구현
- [x] GREEN 확인

### Task 4: 사람 방식 Chrome 재시작

**Files:**
- Modify: `scripts/cretop_agent.py`
- Test: `scripts/test_cretop_agent.py`

- [x] `(1896,20) → (1119,1057) → (514,100)` 순서와 기존 renderer 종료·신규 renderer 생성을 검증하는 실패 테스트 작성
- [x] RED 확인
- [x] Chrome X 클릭, Chrome 창 소멸 확인, 작업표시줄 클릭, Chrome 창 생성 확인, CRETOP 북마크 클릭, renderer PID 교체 확인, 기존 프리플라이트 실행 구현
- [x] GREEN 확인

### Task 5: 회귀 검증·문서·배포

**Files:**
- Modify: `/home/chaconne/.codex/skills/cretop-automation/SKILL.md`
- Modify: GBrain private CRETOP OOM page

- [x] `uv run pytest -q scripts/test_cretop_agent.py`
- [x] `uv run pytest -q`
- [x] `uv run ruff check scripts/cretop_agent.py scripts/test_cretop_agent.py`
- [x] `uv run python -m py_compile scripts/cretop_agent.py`
- [x] 로컬 diff 코드 리뷰 루프 수행
- [x] CRETOP 최종 경로 문서와 GBrain 갱신
- [x] 변경 파일만 커밋
- [x] 원격 배포 SHA-256 일치 확인
