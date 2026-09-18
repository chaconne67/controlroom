# CRETOP SSP Telegram Stop Notification Implementation Plan

> **For agentic workers:** Implement this plan inline in the current session. Do not create a second runner or notification watcher.

**Goal:** CRETOP `collect-batch` SSP가 자체 복구에 실패해 중단될 때 SSP가 텔레그램으로 상황 요약을 정확히 한 번 전송한다.

**Architecture:** 기존 최종 경로의 종료 경계인 `CretopAgent.main()`에 알림을 병합한다. `collect-batch`가 `stopped_on_error=true`를 반환하거나 처리되지 않은 예외가 최상위 경계까지 올라온 경우만 전송한다. 로컬 실행 래퍼는 프로젝트 `.env`의 텔레그램 값 두 개만 원격 전용 비밀 파일로 동기화하며, 별도 감시 프로세스나 후처리 경로는 만들지 않는다.

**Tech Stack:** Python 3.13, `python-dotenv`, Telegram Bot HTTP API, pytest, CRETOP 원격 SSP

---

## 승인 범위

- 구현 파일: `scripts/cretop_agent.py`, `scripts/cretop_detail_collection.py`
- 설정 예시: `.env.example`
- 로컬 비밀 설정: `.env`의 텔레그램 토큰과 채팅 ID
- 계약 검사: 기존 `scripts/test_cretop_agent.py`, `scripts/test_cretop_detail_collection.py`
- 최종 경로 문서: `cretop-automation` 스킬과 관련 GBrain 페이지
- 제외: 새 알림 서비스, 별도 감시 스크립트, Chrome·Windows 생명주기 조작, 실제 데이터 추출 실행

## 최종 경로 잠금

1. **현재 최종 경로**
   - `scripts/cretop_detail_collection.py`
   - `CretopRemoteControl.start_remote_agent_job()`
   - 원격 `scripts/cretop_agent.py`
   - `CretopAgent.main()`
   - `CommandRunner.collect_batch_fast()`
   - 성공 또는 복구 불가 중단 결과를 원격 outbox JSON에 기록
2. **병합 위치**
   - 원격 outbox JSON을 기록하기 직전의 `CretopAgent.main()` 종료 경계
3. **대체·정리 대상**
   - 현재의 “중단 결과 JSON만 기록” 동작을 “중단 결과 기록 + 텔레그램 1회 통지”로 대체
   - 별도 watcher나 회수기 알림 분기는 추가하지 않으므로 공식 실행 경로는 하나로 유지
4. **검증 방법**
   - 로컬 계약 검사에서 중단 결과와 최상위 예외는 각각 1회 전송됨을 확인
   - 정상·검색 결과 없음·복구 가능한 회사별 오류는 전송되지 않음을 확인
   - 전체 CRETOP 테스트와 정적 검사를 통과
   - 원격 배포와 실제 실패 알림 전송은 현재 구현 작업에서 실행하지 않으며, 다음 명시적 원격 실행 때 공식 배치 경로가 소스와 비밀 설정을 함께 배포

## 알림 계약

- 대상 명령: `collect-batch`만 해당
- 발송 조건:
  - 반환 결과에 `stopped_on_error=true`
  - 또는 `collect-batch`의 처리되지 않은 예외가 `CretopAgent.main()`까지 전파
- 제외 조건:
  - `presence_status=absent`
  - 회사별 실패를 복구하고 다음 회사로 계속 진행
  - 페이지 만료 복구 성공
  - 정상 종료
- 메시지 항목:
  - CRETOP SSP 중단 제목
  - 실행 ID
  - 발생 시각
  - 완료 건수, 중단된 회사 순번, 미실행 건수
  - 중단 회사명과 사업자번호가 결과에 있을 때만 표시
  - 사람이 읽을 수 있는 중단 단계와 원인
  - 복구 실패 이유와 현재 화면
- 금지 항목:
  - 토큰
  - 전체 traceback
  - 예외 클래스명, marker 목록, 화면 복사 원문, 재시도 횟수
  - 비밀번호와 환경변수 값
- 기술 정보 보존:
  - 원래 오류와 복구 오류는 결과 JSON에 각각 보존
  - 텔레그램 메시지는 구조화된 운영자 정보만 사용
- 발송 실패:
  - 원래 CRETOP 중단 결과를 가리지 않음
  - 결과 JSON에는 `attempted`, `sent`, 안전한 오류 유형만 기록
  - 텔레그램 URL이나 예외 원문은 기록하지 않음

## 비밀 설정 계약

- 로컬 `.env`에 `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID` 저장
- Git 관리 파일에는 값이 아닌 키 이름만 기록
- 배치 시작 전 두 값이 없으면 원격 작업을 시작하지 않고 명시적으로 실패
- 배치 시작 시 두 값만 임시 파일을 통해 `C:/cretop-agent/.telegram.env`로 전송
- 임시 로컬 파일은 전송 성공·실패와 관계없이 즉시 삭제
- 배포 결과, 명령행, 로그, JSON에는 비밀 값을 포함하지 않음

## 구현 작업

### Task 1: 알림 발송 계약

- [ ] `scripts/cretop_agent.py`에 텔레그램 설정 로드와 메시지 생성·전송 책임을 추가한다.
- [ ] HTTP 요청은 표준 라이브러리로 수행하고 타임아웃을 둔다.
- [ ] `CretopAgent.main()`의 기존 성공·실패 JSON 기록 경계에만 알림 판정을 병합한다.
- [ ] 중단 결과에서 마지막 실패 항목을 찾아 회사와 진행 건수를 요약한다.
- [ ] 알림 시도 결과를 비밀 없는 상태 정보로만 outbox JSON에 남긴다.

### Task 2: 비밀 설정의 원격 전달

- [ ] `.env.example`에 `TELEGRAM_CHAT_ID` 키를 추가한다.
- [ ] 로컬 `.env`에 제공받은 토큰과 채팅 ID를 저장한다.
- [ ] `scripts/cretop_detail_collection.py`가 `collect-batch` 시작 전에 두 설정을 검증한다.
- [ ] 두 설정만 원격 비밀 파일로 전송하고 임시 로컬 파일을 정리한다.
- [ ] 배포 결과에는 비밀 파일 경로와 성공 여부만 남긴다.

### Task 3: 계약 검증

새 테스트가 예방하는 장애는 “SSP가 실제로 중단됐는데 알림이 없거나, 복구 가능한 건마다 중복 알림이 발송되는 장애”다. 외부 메시지 부작용과 운영 자동화의 핵심 중단 계약이므로 새 계약 검사의 반복 가치가 있다.

- [ ] HTTP 호출을 대체한 검사로 중단 결과가 정확히 한 번 발송되는지 확인한다.
- [ ] 처리되지 않은 최상위 예외가 정확히 한 번 발송되는지 확인한다.
- [ ] 정상 결과와 계속 진행 가능한 회사별 오류에는 발송하지 않는지 확인한다.
- [ ] 설정 누락 시 원격 작업 시작 전에 실패하는지 확인한다.
- [ ] 배포 결과와 예외 상태에 토큰·채팅 ID가 포함되지 않는지 확인한다.
- [ ] `uv run pytest -q scripts/test_cretop_agent.py scripts/test_cretop_detail_collection.py`를 실행한다.
- [ ] `uv run ruff check scripts/cretop_agent.py scripts/cretop_detail_collection.py scripts/test_cretop_agent.py scripts/test_cretop_detail_collection.py`를 실행한다.
- [ ] `uv run python -m py_compile scripts/cretop_agent.py scripts/cretop_detail_collection.py`를 실행한다.

### Task 4: 검토와 기록

- [ ] 변경 diff를 `code-review`로 검토하고 발견 사항을 수정한다.
- [ ] `cretop-automation`의 최종 경로와 보안 규칙을 중복 없이 갱신한다.
- [ ] 재사용 가능한 알림 발송·비밀 전달 계약을 GBrain에 기록한다.
- [ ] 이번 작업 파일만 커밋하고 기존 사용자 변경 파일은 제외한다.

## 완료 조건

- 복구 불가 중단만 텔레그램 알림 대상이다.
- 한 SSP 실행에서 중단 알림은 최대 1회다.
- 알림 전송 실패가 원래 중단 결과를 덮지 않는다.
- 비밀 값은 Git, 로그, 결과 JSON, GBrain에 남지 않는다.
- 별도 watcher·runner·후처리 경로가 없다.
- 로컬 검증과 코드리뷰가 통과한다.
- 원격 배포·실전송을 수행하지 않았다는 경계를 완료 보고에 명시한다.
