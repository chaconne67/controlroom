# CRETOP Deferred Quality Retry Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 상세 섹션 품질검사에 실패한 기업만 DB 미처리로 남기고 나머지 원격 결과 저장을 계속한다.

**Architecture:** 품질검사 예외를 전용 타입으로 구분한다. `fetch_remote_batch()`는 이 예외만 항목별로 잡아 `deferred_items`에 기록하고, DB 저장을 호출하지 않은 채 다음 항목을 처리한다.

**Tech Stack:** Python 3.13, pytest, psycopg, 기존 CRETOP 원격 회수·저장 래퍼

---

### Task 1: 품질 미달 항목 보류 테스트

**Files:**
- Modify: `scripts/test_cretop_detail_collection.py`
- Test: `scripts/test_cretop_detail_collection.py`

- [ ] **Step 1: 실패 테스트 작성**

`fetch_remote_batch()`의 첫 `present` 항목 품질검사가 실패하고 두 번째 항목은 통과하는 가짜 원격 결과를 만든다. 첫 항목이 DB 저장 함수에 전달되지 않고 `deferred_items`에 남으며 두 번째 항목만 저장되는지 단언한다.

- [ ] **Step 2: RED 확인**

Run: `uv run pytest scripts/test_cretop_detail_collection.py -k deferred_quality -q`

Expected: `deferred_items`가 없거나 품질검사 예외가 전파되어 실패

### Task 2: 항목별 보류 구현

**Files:**
- Modify: `scripts/cretop_detail_collection.py`
- Test: `scripts/test_cretop_detail_collection.py`

- [ ] **Step 1: 전용 예외 추가**

`CollectionQualityError(RuntimeError)`를 정의하고 `validate_collection()`이 품질 실패 시 이 예외를 발생시키게 한다.

- [ ] **Step 2: 품질 실패만 보류**

`fetch_remote_batch()`에 `deferred_items`를 추가한다. `present` 항목의 `CollectionQualityError`만 잡아 실행 ID, 리드, 실패 목록을 기록하고 `continue`한다.

- [ ] **Step 3: GREEN 확인**

Run: `uv run pytest scripts/test_cretop_detail_collection.py -k 'deferred_quality or validate_collection' -q`

Expected: 관련 테스트 통과

- [ ] **Step 4: CRETOP 로컬 회귀 검사**

Run: `uv run pytest scripts/test_cretop_detail_collection.py scripts/test_cretop_agent.py -q`

Expected: 전체 통과

Run: `uv run ruff check scripts/cretop_detail_collection.py scripts/test_cretop_detail_collection.py`

Expected: 오류 없음

### Task 3: 기존 배치 회수와 다음 배치 시작

**Files:**
- Runtime artifact: `docs/cretop/detail_collection/20260726_cretop_additional1000/`

- [ ] **Step 1: 기존 배치 재회수**

Run: `uv run python scripts/cretop_detail_collection.py remote-batch-fetch --run-id 20260726_cretop_additional1000`

Expected: 회수 완료, `saved_items=999`, `deferred_items=1`

- [ ] **Step 2: DB 검증**

`ceo_loan.cretop.lookup_runs`, `lead_lookup_status`, 상세 스냅샷을 직접 조회한다.

Expected: 저장 가능한 999건 완료, 사업자번호 `1268144139` 미처리

- [ ] **Step 3: 추가 1,000건 시작**

Run: `uv run python scripts/cretop_detail_collection.py batch-script-only-collect --limit 1000`

Expected: 신규 실행 ID 생성, 선택 1,000건, 원격 작업 시작

- [ ] **Step 4: 대상 포함과 실행 상태 확인**

신규 payload에서 `1268144139` 포함 여부를 확인하고 `remote-batch-status`를 실행한다.

Expected: 품질 미달 기업 포함, 원격 작업 실행 또는 정상 완료 상태

### Task 4: 리뷰와 커밋

**Files:**
- Modify: `scripts/cretop_detail_collection.py`
- Modify: `scripts/test_cretop_detail_collection.py`
- Create: `docs/superpowers/specs/2026-07-27-cretop-deferred-quality-retry-design.md`
- Create: `docs/superpowers/plans/2026-07-27-cretop-deferred-quality-retry.md`

- [ ] **Step 1: 코드 리뷰 루프**

승인된 목적과 로컬 diff만 `code-review-loop`로 검토한다. 승인 finding이 없을 때까지 검증된 결함만 수정한다.

- [ ] **Step 2: 최종 검증**

Run: `uv run pytest scripts/test_cretop_detail_collection.py scripts/test_cretop_agent.py -q`

Run: `uv run ruff check scripts/cretop_detail_collection.py scripts/test_cretop_detail_collection.py`

Expected: 모두 통과

- [ ] **Step 3: 범위 파일만 커밋**

`scripts/cretop_detail_collection.py`, `scripts/test_cretop_detail_collection.py`, 두 문서만 스테이징하고 커밋한다. 기존 사용자 변경은 포함하지 않는다.
