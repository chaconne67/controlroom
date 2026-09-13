# CRETOP Error Retry Exclusion Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** CRETOP 오류 회사를 DB에 재시도 제외 상태로 명시하고 다음 미처리 배치에서 다시 선택하지 않는다.

**Architecture:** 사업자번호를 회사의 유일 조회 키로 보고 `cretop.lead_lookup_status.requery_required`를 재시도 여부의 단일 기준으로 사용한다. 결과 저장 시 오류를 포함한 모든 처리 결과에 `false`를 명시하고, 미처리 선택 쿼리는 `lead_id`와 상태 이름에 관계없이 같은 사업자번호 조회 키의 `false` 기록을 제외한다. 운영자가 재시도를 원할 때만 같은 조회 키의 값을 `true`로 바꾼다.

**Tech Stack:** Python 3.13, psycopg, PostgreSQL, pytest, uv

---

## 변경 계약

1. `present`, `absent`, `ambiguous`, `error` 결과는 모두 DB에 `requery_required=false`로 기록한다.
2. 같은 사업자번호 조회 키에 `requery_required=false` 기록이 있으면 `lead_id`가 다른 중복 리드도 다음 배치에서 제외한다.
3. `requery_required=true`로 명시된 기록만 다시 선택할 수 있다.
4. 기존 `(주)포컴퍼니`는 같은 사업자번호의 리드가 2개이며, 한 행에 이미 `error`, `requery_required=false`가 있으므로 데이터 보정 없이 사업자번호 단위 선택 계약을 적용한다.
5. 브라우저 수집·복구·초기화 경로는 변경하지 않는다.

## SSP 잠금

- 현재 최종 경로: `batch-script-only-collect` → `CretopBatchStore.pending_business_number_leads()` → 원격 `collect-batch` → `remote-batch-fetch` → `CretopBatchStore.save_result()` → `upsert_lookup_status()`.
- 병합 위치: 미처리 대상 선택과 결과 상태 저장 단계.
- 대체 대상: `lead_id`, 상태 목록 `('present', 'absent', 'ambiguous')`, `requery_required=false`를 함께 보던 리드 단위 조건을 사업자번호 조회 키와 `requery_required=false`의 회사 단위 조건으로 대체한다.
- 엔트로피: 새 상태·테이블·실행 경로를 추가하지 않고 기존 플래그의 의미를 일관되게 사용하므로 유지 또는 감소한다.
- 검증 방법: 로컬 계약 테스트와 운영 DB 읽기 전용 조회로 `error/false` 회사가 다음 대상에서 제외됨을 증명한다. 원격 브라우저와 새 배치는 실행하지 않는다.

## 검증 중 발견한 중복 리드

- 사업자번호 `2328800610`의 리드는 2개다.
- 첫 리드에는 `error`, `requery_required=false`가 기록돼 있다.
- 두 번째 리드에는 조회 상태가 없다.
- `lead_id`까지 일치시키는 기존 조건은 두 번째 리드를 다시 선택한다.
- 사업자번호가 회사의 유일 식별값이라는 기존 CRETOP 계약에 맞춰 조회 상태도 사업자번호 단위로 소비한다.

### Task 1: 재시도 제외 DB 계약 고정

**Files:**
- Modify: `scripts/cretop_detail_collection.py:439-549`
- Test: `scripts/test_cretop_detail_collection.py`

- [ ] **Step 1: 반복 추출을 막는 계약 테스트 작성**

장애 비용: 영구 오류 회사를 매 배치 첫 대상으로 다시 조회하면 원격 브라우저 시간과 CRETOP 조회 비용을 반복 소비한다. 안정적인 DB 상태 계약을 고정하기 위해 다음 테스트를 추가한다.

```python
def test_pending_leads_use_requery_required_as_the_only_retry_gate():
    executed = []

    class FakeCursor:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def execute(self, query, params):
            executed.append((query, params))

        def fetchall(self):
            return []

    class FakeDb:
        def cursor(self):
            return FakeCursor()

    store = object.__new__(cretop.CretopBatchStore)
    store.db = FakeDb()

    assert store.pending_business_number_leads(30) == []
    query = " ".join(executed[0][0].split())
    assert "s.lookup_key_value = l.business_number_digits" in query
    assert "s.requery_required = false" in query
    assert "s.lead_id = l.id" not in query
    assert "s.presence_status in" not in query
```

- [ ] **Step 2: 테스트가 현재 중복 상태 조건 때문에 실패하는지 확인**

Run:

```bash
uv run pytest -q scripts/test_cretop_detail_collection.py::test_pending_leads_use_requery_required_as_the_only_retry_gate
```

Expected: `s.lead_id = l.id`와 `s.presence_status in` 조건이 남아 있어 FAIL.

- [ ] **Step 3: 미처리 선택 조건을 단일 재조회 플래그로 변경**

`pending_business_number_leads()`의 하위 쿼리를 다음 계약으로 바꾼다.

```sql
and not exists (
  select 1
  from cretop.lead_lookup_status s
  where s.lookup_key_type = 'business_number'
    and s.lookup_key_value = l.business_number_digits
    and s.requery_required = false
)
```

- [ ] **Step 4: 결과 저장 시 재시도 제외 값을 명시적으로 기록**

`upsert_lookup_status()`의 insert와 update가 모두 `false`를 명시하도록 바꾼다.

```sql
insert into cretop.lead_lookup_status (
    lead_id, lookup_key_type, lookup_key_value,
    presence_status, last_lookup_id, requery_required, notes
)
values (%s, 'business_number', %s, %s, %s, false, %s)
on conflict (lead_id, lookup_key_type, lookup_key_value)
do update set
    presence_status = excluded.presence_status,
    last_lookup_id = excluded.last_lookup_id,
    last_checked_at = now(),
    requery_required = false,
    notes = excluded.notes
```

- [ ] **Step 5: 집중 테스트와 관련 회귀 검사**

Run:

```bash
uv run pytest -q scripts/test_cretop_detail_collection.py
uv run ruff check scripts/cretop_detail_collection.py scripts/test_cretop_detail_collection.py
uv run python -m py_compile scripts/cretop_detail_collection.py scripts/test_cretop_detail_collection.py
```

Expected: 모두 PASS.

### Task 2: 실제 DB 계약 검증과 문서 동기화

**Files:**
- Modify: `docs/cretop/final_collection_procedure.md`
- Modify: `/home/chaconne/.codex/skills/cretop-automation/SKILL.md`
- Update: GBrain `agents/rndlog/private/cretop-error-retry-exclusion-20260715`

- [ ] **Step 1: 운영 DB의 오류 기록 확인**

`ceo_loan.cretop.lead_lookup_status`에서 오류 회사가 다음 상태인지 읽기 전용으로 확인한다.

```text
presence_status = error
requery_required = false
```

- [ ] **Step 2: 같은 선택 조건으로 오류 회사 제외 확인**

같은 사업자번호를 가진 리드 2개에 새 `not exists` 조건을 적용했을 때 선택 결과가 0건인지 확인한다.

Expected: `0`.

- [ ] **Step 3: 최종 경로 문서 갱신**

다음 규칙을 기존 데이터 선택 설명에 병합한다.

```text
조회 결과는 상태와 함께 requery_required=false로 기록한다.
미처리 배치는 lead_id와 관계없이 같은 사업자번호 조회 키의 false 기록을 제외한다.
명시적으로 true로 바꾼 기록만 재시도한다.
```

- [ ] **Step 4: 코드리뷰와 변경 범위 확인**

`code-review`로 로컬 diff를 검토하고 다음을 확인한다.

- 브라우저 최종 경로 변경 없음
- 새 테이블·상태·runner 없음
- `AGENTS.md` 변경 제외
- 오류 회사가 다음 배치에서 제외됨

- [ ] **Step 5: 구현 커밋**

```bash
git add scripts/cretop_detail_collection.py scripts/test_cretop_detail_collection.py docs/cretop/final_collection_procedure.md
git commit -m "fix(cretop): exclude terminal errors from retry"
```

스킬과 GBrain은 저장소 밖의 공식 지식 위치에 별도로 동기화한다.

## 승인 후 실행 범위

주인님이 이 계획을 승인하면 구현·검증·코드리뷰·문서화·GBrain 갱신·커밋까지 추가 승인 없이 연속 진행한다. 원격 배포, 새 배치 실행, Chrome 조작은 포함하지 않는다.
