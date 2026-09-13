# CRETOP SSP Telegram Completion Notification Implementation Plan

> **For agentic workers:** Implement this plan inline in the current session. Do not create another notifier, watcher, or runner.

**Goal:** CRETOP `collect-batch` SSP가 선택된 회사를 끝까지 처리하면 추출 결과 요약을 텔레그램으로 한 번 전송한다.

**Architecture:** 기존 `CretopAgent.main()`의 텔레그램 종료 경계를 `중단 또는 완료` 단일 판정으로 확장한다. 중단된 실행은 기존 중단 메시지만 보내고, 끝까지 처리한 실행은 정상·검색 결과 없음·회사별 오류 건수를 포함한 완료 메시지만 보낸다.

**Tech Stack:** Python 3.13, Telegram Bot HTTP API, pytest, CRETOP 원격 SSP

---

## 승인 범위

- 구현: `scripts/cretop_agent.py`
- 계약 검사: `scripts/test_cretop_agent.py`
- 문서: `cretop-automation` 스킬과 관련 GBrain 페이지
- 제외: 추출·복구·DB 저장 로직, 로컬 회수기, 새 알림 모듈, 실제 원격 실행, 실제 텔레그램 전송

## 최종 경로 잠금

1. **현재 최종 경로**
   - `scripts/cretop_agent.py`
   - `CretopAgent.main()`이 `collect-batch` 결과를 받음
   - 복구 불가 중단이면 중단 알림 1회 전송
   - outbox 결과 JSON 기록
2. **병합 위치**
   - 기존 `CretopAgent.main()`의 중단 알림 판정 위치
3. **대체·정리 대상**
   - `중단인 경우만 알림` 판정을 `중단이면 중단 알림, 아니면 완료 알림` 단일 판정으로 대체
   - 기존 전송·비밀 설정·HTTP 처리를 재사용하고 별도 경로를 추가하지 않음
4. **검증 방법**
   - 가짜 HTTP 호출로 정상 완료, 일부 회사 오류 완료, 복구 불가 중단을 각각 검증
   - 각 실행에서 알림이 정확히 한 번만 선택되는지 확인
   - 전체 테스트·정적 검사·문법 검사 실행

## 알림 계약

- 정상 완료:
  - 제목: `CRETOP SSP 추출 완료`
  - 실행 ID, 발생 시각, 처리/전체 건수 표시
  - 상세 추출, 검색 결과 없음, 회사별 오류 건수 표시
- 일부 오류 완료:
  - 전체 회사를 끝까지 처리했으면 완료 알림을 전송
  - 회사별 오류가 있으면 `일부 오류 포함` 상태와 오류 건수를 표시
- 중단:
  - `stopped_on_error=true` 또는 최상위 예외이면 기존 중단 알림만 전송
  - 완료 알림은 전송하지 않음
- 검색 결과 없음:
  - 실패가 아니라 완료 집계의 `검색 결과 없음`에 포함
- 알림 실패:
  - 추출 결과와 outbox 기록을 가리지 않음
- 완료 의미:
  - 원격 SSP 추출 완료
  - DB 회수·반영 완료를 뜻하지 않음

## 구현 작업

### Task 1: 완료 알림 계약 검사

새 테스트가 예방하는 장애는 정상 완료 알림 누락, 중단·완료 메시지 중복, 일부 오류 실행의 잘못된 중단 표기다. 외부 메시지 부작용이 있는 운영 완료 계약이므로 반복 검증 가치가 있다.

- [ ] 정상 완료 결과가 완료 알림을 한 번 선택하는 실패 검사를 작성한다.
- [ ] `present`, `absent`, 회사별 오류가 메시지 건수에 정확히 집계되는 실패 검사를 작성한다.
- [ ] `stopped_on_error=true`에서는 중단 알림만 한 번 선택되는 기존 계약을 유지한다.
- [ ] 새 검사들이 현재 코드에서 완료 알림 부재로 실패하는지 확인한다.

### Task 2: 단일 종료 알림 구현

- [ ] 기존 중단 메시지 생성 함수를 완료·중단 이벤트를 받는 단일 메시지 생성 함수로 정리한다.
- [ ] 기존 전송 함수가 선택된 이벤트의 메시지를 보내도록 정리한다.
- [ ] `CretopAgent.main()`에서 `collect-batch` 종료 시 이벤트를 정확히 한 번 선택한다.
- [ ] 중단 결과에는 `stopped`, 끝까지 처리한 결과에는 `completed` 이벤트 상태를 결과 JSON에 기록한다.
- [ ] 알림 실패가 기존 결과의 `ok`, `stopped_on_error`, 오류 내용을 바꾸지 않도록 유지한다.

### Task 3: 검증과 기록

- [ ] `uv run pytest -q scripts/test_cretop_agent.py`를 실행한다.
- [ ] `uv run pytest -q`를 실행한다.
- [ ] `uv run ruff check scripts/cretop_agent.py scripts/test_cretop_agent.py`를 실행한다.
- [ ] `uv run python -m py_compile scripts/cretop_agent.py`를 실행한다.
- [ ] 변경 diff를 `code-review`로 한 번 검토하고 승인된 finding을 수정한다.
- [ ] `cretop-automation`의 알림 규칙을 완료·중단 단일 계약으로 교체한다.
- [ ] GBrain에 재사용 가능한 완료 알림 계약을 기록한다.
- [ ] 이번 작업 파일만 커밋하고 기존 사용자 변경과 임시 DB 파일은 제외한다.

## 완료 조건

- 끝까지 처리한 `collect-batch`는 완료 알림을 한 번 전송한다.
- 일부 회사 오류가 있어도 배치가 끝까지 처리되면 완료 알림에 오류 건수를 표시한다.
- 복구 불가 중단은 중단 알림만 한 번 전송한다.
- 검색 결과 없음은 실패로 표시하지 않는다.
- 비밀값은 메시지 상태, 결과 JSON, Git, GBrain에 남지 않는다.
- 별도 알림 경로가 생기지 않는다.
