# CRETOP Local Primary Replication Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** CRETOP 결과를 로컬 DB에 먼저 확정하고 로컬 동기화 장치가 ceoloan 서버의 수집 데이터만 같은 행으로 복제하는 단일 경로를 만든다.

**Architecture:** 기존 `remote-batch-fetch` 경로를 유지하되 `CretopBatchStore`를 로컬 정본 전용으로 고정한다. 같은 파일 안의 `CretopReplicaSynchronizer`가 로컬 커밋 행을 원격 트랜잭션으로 복제·검증하며, 실패 시 로컬 파일과 DB를 재실행 입력으로 보존한다.

**Tech Stack:** Python 3.13, psycopg 3, PostgreSQL 16, pytest, Ruff

---

## 파일 구조

- `scripts/cretop_detail_collection.py`: 로컬 대상 선정·저장, 원격 결과 회수, 로컬→원격 복제와 검증
- `scripts/cretop_report_pipeline.py`: 보고서·구조화 명령의 로컬 정본 접속
- `scripts/test_cretop_detail_collection.py`: 저장 순서·재실행·복제 계약 회귀 테스트
- `scripts/test_cretop_report_pipeline.py`: 보고서 파이프라인 로컬 접속 계약 테스트
- `docs/superpowers/specs/2026-07-30-cretop-local-primary-replication-design.md`: 승인된 설계
- `docs/cretop/cretop_local_primary_runbook.md`: DB 복구·동기화 운영 절차
- `/home/chaconne/.codex/skills/cretop-automation/SKILL.md`: 검증된 최종 경로 선언

### Task 1: 로컬 정본 접속 계약

**Files:**
- Modify: `scripts/test_cretop_detail_collection.py`
- Modify: `scripts/cretop_detail_collection.py`
- Modify: `scripts/test_cretop_report_pipeline.py`
- Modify: `scripts/cretop_report_pipeline.py`

- [ ] **Step 1: 실패 테스트 작성**

`psycopg.connect`를 기록하는 대역으로 바꾸고 `CretopBatchStore()`가 `127.0.0.1:5433`, DB `ceo_loan`, 사용자 `rndnote`를 사용하며 `CretopReplicaSynchronizer`만 `127.0.0.1:15433`, 사용자 `ceoloan`을 사용하는 테스트를 추가한다. 두 접속점이 같으면 `ValueError("local primary and remote replica endpoints must differ")`가 발생해야 한다.

- [ ] **Step 2: RED 확인**

```bash
uv run pytest scripts/test_cretop_detail_collection.py -k 'local_primary or replica_endpoint' -q
```

기대 결과: 로컬 접속 구성과 복제 클래스가 없어 실패한다.

- [ ] **Step 3: 최소 구현**

`scripts/cretop_detail_collection.py`에 다음 역할을 구현한다.

```python
def local_db_config() -> dict[str, Any]:
    return {
        "host": os.environ.get("CRETOP_LOCAL_DB_HOST", "127.0.0.1"),
        "port": int(os.environ.get("CRETOP_LOCAL_DB_PORT", "5433")),
        "dbname": os.environ.get("CRETOP_LOCAL_DB_NAME", "ceo_loan"),
        "user": os.environ.get("CRETOP_LOCAL_DB_USER", "rndnote"),
        "password": os.environ.get(
            "CRETOP_LOCAL_DB_PASSWORD", os.environ["POSTGRES_PASSWORD"]
        ),
    }


def replica_db_config() -> dict[str, Any]:
    return {
        "host": os.environ.get("CRETOP_REPLICA_DB_HOST", "127.0.0.1"),
        "port": int(os.environ.get("CRETOP_REPLICA_DB_PORT", "15433")),
        "dbname": os.environ.get("CRETOP_REPLICA_DB_NAME", "ceo_loan"),
        "user": os.environ.get("CRETOP_REPLICA_DB_USER", "ceoloan"),
        "password": os.environ.get(
            "CRETOP_REPLICA_DB_PASSWORD", os.environ["POSTGRES_PASSWORD"]
        ),
    }
```

`CretopBatchStore`와 `cretop_report_pipeline.conn()`은 로컬 구성만 사용한다. 기존 의미가 모호한 `CRETOP_DB_*` 기본 경로는 제거한다.

- [ ] **Step 4: GREEN 확인**

```bash
uv run pytest scripts/test_cretop_detail_collection.py scripts/test_cretop_report_pipeline.py -k 'local_primary or replica_endpoint' -q
```

기대 결과: 추가한 접속 계약 테스트가 통과한다.

### Task 2: 기존 저장 결과 해석과 정확한 행 복제

**Files:**
- Modify: `scripts/test_cretop_detail_collection.py`
- Modify: `scripts/cretop_detail_collection.py`

- [ ] **Step 1: 실패 테스트 작성**

다음 계약을 각각 검증한다.

```python
def test_existing_present_result_resolves_candidate_snapshot_and_company_ids():
    ...


def test_replica_sync_copies_local_rows_in_fk_order_and_verifies_them():
    ...


def test_replica_sync_rolls_back_when_same_business_number_has_another_id():
    ...
```

첫 테스트는 `save_result()`가 기존 `present` 결과에서도 `candidate_id`, `snapshot_id`, `structured.company_id`를 반환해야 한다. 둘째 테스트는 lead → lookup → candidate → snapshot → sections → company → company children → status 순서를 확인한다. 셋째 테스트는 원격 드리프트를 덮어쓰지 않고 실패하는지 확인한다.

- [ ] **Step 2: RED 확인**

```bash
uv run pytest scripts/test_cretop_detail_collection.py -k 'existing_present_result_resolves or replica_sync' -q
```

기대 결과: 기존 결과 ID 해석과 복제 구현이 없어 실패한다.

- [ ] **Step 3: 최소 구현**

`CretopBatchStore.resolve_saved_result()`가 조회 실행 ID로 후보·최신 snapshot·회사 ID를 읽는다. `CretopReplicaSynchronizer`는 정적 테이블 목록과 로컬 SELECT 결과의 실제 column description을 사용해 다음 API를 제공한다.

```python
class CretopReplicaSynchronizer:
    def __init__(
        self,
        local_db: psycopg.Connection[Any],
        replica_db: psycopg.Connection[Any] | None = None,
    ) -> None:
        ...

    def sync_saved_result(
        self,
        lead: dict[str, Any],
        db_result: dict[str, Any],
    ) -> dict[str, Any]:
        ...
```

원격 트랜잭션에서 회사별 파생 테이블을 삭제한 뒤 로컬 행을 기본키 그대로 upsert한다. 복제 직후 같은 WHERE 범위의 `SELECT * ORDER BY 기본키` 결과를 양쪽에서 비교하고 다르면 예외를 발생시킨다.

- [ ] **Step 4: GREEN 확인**

```bash
uv run pytest scripts/test_cretop_detail_collection.py -k 'existing_present_result_resolves or replica_sync' -q
```

기대 결과: 세 계약 테스트가 통과한다.

### Task 3: `remote-batch-fetch`에 선저장·후동기화 병합

**Files:**
- Modify: `scripts/test_cretop_detail_collection.py`
- Modify: `scripts/cretop_detail_collection.py`

- [ ] **Step 1: 실패 테스트 작성**

```python
def test_fetch_saves_locally_before_replica_sync():
    ...


def test_fetch_keeps_local_commit_and_skips_cleanup_on_replica_failure():
    ...


def test_fetch_reuses_local_result_file_when_rerun():
    ...


def test_deferred_quality_item_is_not_synced():
    ...
```

호출 기록은 `save`, `sync`, `cleanup` 순서여야 한다. 복제 실패 테스트는 `save`가 남고 `cleanup`이 호출되지 않으며 run 디렉터리에 `sync_pending_items`가 기록되는지 확인한다. 재실행 테스트는 이미 회수된 결과 파일을 사용해 원격 파일 복사를 요구하지 않아야 한다.

- [ ] **Step 2: RED 확인**

```bash
uv run pytest scripts/test_cretop_detail_collection.py -k 'before_replica or replica_failure or reuses_local_result or deferred_quality_item_is_not_synced' -q
```

기대 결과: 현재 경로에 복제 단계와 로컬 파일 재사용이 없어 실패한다.

- [ ] **Step 3: 최소 구현**

`fetch_remote_batch()`에서 결과 파일이 이미 로컬에 있으면 재사용하고, 각 저장 가능 항목마다 다음 순서를 실행한다.

```python
db_result = store.save_result(lead, materialized)
sync_result = synchronizer.sync_saved_result(lead, db_result)
saved_items.append(
    {
        "run_id": item_run_id,
        "lead_id": lead.get("lead_id"),
        "local_db": db_result,
        "replica_db": sync_result,
    }
)
```

복제 실패는 로컬 결과와 오류를 `sync_pending_items`에 기록하고 Windows 작업 정리를 건너뛴다. 같은 run ID 재실행은 기존 로컬 파일과 `resolve_saved_result()`를 사용한다.

- [ ] **Step 4: GREEN 확인**

```bash
uv run pytest scripts/test_cretop_detail_collection.py -k 'fetch_' -q
```

기대 결과: fetch 관련 테스트가 모두 통과한다.

### Task 4: 최초 데이터 복구와 운영 문서

**Files:**
- Create: `docs/cretop/cretop_local_primary_runbook.md`
- Modify: `/home/chaconne/.codex/skills/cretop-automation/SKILL.md`

- [ ] **Step 1: 로컬 백업과 원격 스냅샷 생성**

```bash
mkdir -p /home/chaconne/backups/cretop_primary_repair_20260730
docker exec rndnote-db-prod pg_dump -U rndnote -d ceo_loan -Fc -n cretop --no-owner \
  > /home/chaconne/backups/cretop_primary_repair_20260730/local_before.dump
ssh chaconne@49.247.205.170 \
  'docker exec ceoloan-db pg_dump -U ceoloan -d ceo_loan -Fc -n cretop --no-owner' \
  > /home/chaconne/backups/cretop_primary_repair_20260730/remote_current.dump
```

기대 결과: 두 dump가 0바이트보다 크고 `pg_restore --list`가 성공한다.

- [ ] **Step 2: 원격 최신 CRETOP을 로컬 정본으로 복원**

```bash
docker exec -i rndnote-db-prod pg_restore \
  -U rndnote -d ceo_loan --clean --if-exists --no-owner --single-transaction \
  < /home/chaconne/backups/cretop_primary_repair_20260730/remote_current.dump
```

기대 결과: 종료 코드 0이며 로컬 `cretop` 34개 테이블의 총행이 복원 전 원격과 일치한다.

- [ ] **Step 3: 운영 계약 문서화**

runbook에 정본·복제 DB, 백업 위치, 재실행 명령, 직접 조회 검증 SQL, `public` 운영 테이블 제외 규칙을 기록한다. `cretop-automation`의 데이터 기준을 로컬 선저장·로컬 동기화 계약으로 교체한다.

### Task 5: 전체 검증·실제 SSP·리뷰

**Files:**
- Modify: `scripts/cretop_detail_collection.py`
- Modify: `scripts/cretop_report_pipeline.py`
- Modify: `scripts/test_cretop_detail_collection.py`
- Modify: `scripts/test_cretop_report_pipeline.py`
- Modify: `docs/cretop/cretop_local_primary_runbook.md`
- Modify: `/home/chaconne/.codex/skills/cretop-automation/SKILL.md`

- [ ] **Step 1: 전체 자동 검증**

```bash
uv run pytest scripts/test_cretop_detail_collection.py scripts/test_cretop_report_pipeline.py -q
uv run ruff check scripts/cretop_detail_collection.py scripts/cretop_report_pipeline.py scripts/test_cretop_detail_collection.py scripts/test_cretop_report_pipeline.py
```

기대 결과: 테스트 실패 0건, Ruff 오류 0건.

- [ ] **Step 2: DB 직접 대조**

로컬 `rndnote-db-prod/ceo_loan`과 원격 `49.247.205.170/ceo_loan`에서 `public.leads`와 `cretop` 34개 테이블의 스키마·행 수를 직접 조회한다. 원격 `public.funding_*`, 사용자·인증·SMS 행 수가 복구 전과 같은지 확인한다.

- [ ] **Step 3: 실제 1건 최종 경로 검증**

```bash
uv run python scripts/cretop_detail_collection.py batch-script-only-collect \
  --limit 1 --run-id 20260730_cretop_local_primary_canary
uv run python scripts/cretop_detail_collection.py remote-batch-status \
  --run-id 20260730_cretop_local_primary_canary
uv run python scripts/cretop_detail_collection.py remote-batch-fetch \
  --run-id 20260730_cretop_local_primary_canary
```

기대 결과: Windows가 결과 파일을 만들고, 로컬 DB 행의 저장 시각이 먼저 생긴 뒤 원격에 같은 기본키·같은 값이 존재하며 fetch 요약의 복제 검증이 성공한다.

- [ ] **Step 4: 코드 리뷰 루프**

승인된 목적, 기준 `5559840`, 이번 로컬 diff, CRETOP 수집·DB 파일만을 범위로 `code-review-loop`를 실행한다. 승인 finding을 수정하고 같은 전체 diff를 재리뷰해 finding 0건으로 끝낸다.

- [ ] **Step 5: 문서·코드 커밋**

```bash
git add \
  scripts/cretop_detail_collection.py \
  scripts/cretop_report_pipeline.py \
  scripts/test_cretop_detail_collection.py \
  scripts/test_cretop_report_pipeline.py \
  docs/cretop/cretop_local_primary_runbook.md \
  docs/superpowers/specs/2026-07-30-cretop-local-primary-replication-design.md \
  docs/superpowers/plans/2026-07-30-cretop-local-primary-replication.md
git commit -m "fix(cretop): make local DB primary and sync replica"
```

기대 결과: 관련 파일만 포함한 커밋이 생성되고 사용자 작업 파일은 staging되지 않는다.
