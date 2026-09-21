# Exdigm 운영 오류 처리 정책

상태: 2026-09-21 축소 정리본. 제품 서버의 `OperationalError` 한 행을 유일한 공용 보드로 사용한다. 별도 Track·Transition 상태표, 별도 배포 작업자, Sam의 기술 실행 책임은 폐기한다.

## 1. 사건 한 건의 경계

`OperationalError` 한 행은 제품 코드가 하나의 안정된 발생 식별자(업무 대상·시도·단계·발생 시각 또는 명시적 occurrence key)로 기록한 **관측 가능한 실패 사건 한 건**이다.

- 한 예외 안에 여러 원인과 실패 단계가 겹쳐 있어도 같은 업무 시도의 같은 실패라면 한 행의 조사 이력으로 다룬다.
- 서로 독립적으로 재시도·수정·승인·종료할 수 있는 실패는 각각 별도 행이다.
- 같은 근본 원인이 여러 행을 만들 수 있다. main Codex는 관련성을 조사 결과에 적을 수 있지만 행을 자동 병합하거나 새 하위 Track을 만들지 않는다.
- 한 행 안의 단계 변화는 `processing_history`, 현재 행동은 `next_action`, 현재 근거는 `handling_context`, 동시성 판본은 `handling_revision`에 기록한다.

이 경계를 자동으로 다시 분류하는 상태 엔진은 두지 않는다. 경계가 잘못 잡힌 경우 main Codex가 근거와 관련 오류 번호를 기록하고, 필요한 경우 주인님께 구체적인 변경 방향을 요청한다.

## 2. 역할과 금지선

| 주체 | 하는 일 | 하지 않는 일 |
|---|---|---|
| Exdigm 제품 코드·서버 | 실패 사실을 `OperationalError`에 기록하고 제한된 행 읽기·결과 기록 명령을 제공 | Codex 호출, 원인 판단, 승인 요청, 수정, 배포, Sam 호출 |
| main 단일 주기 작업자 | DB의 기술 행동을 한 건씩 선택해 Codex 조사·수정·검증을 실행하고, 승인된 정확한 커밋은 공식 배포 경로로 반영하며 결과를 DB에 기록 | 사용자 승인 생성·대행, Sam 직접 호출, 승인 없는 복잡한 변경·배포 |
| main Codex | 조사, 단순 결함 수정, 승인된 복잡한 수정, 배포 후 실제 결과 확인, 공식 검사·리뷰·커밋 | 사용자와 직접 승인 통신, DB 밖의 별도 인계 상태 생성, 임의 운영 배포 |
| Sam(Hermes) | 완료 결과를 읽어 주인님께 보고하고, 현재 Telegram 답변을 승인·거절·보류·수정·자료 제공으로 DB에 기록 | 코드 조사·수정·테스트, 작업 예약, Codex 호출, 배포 |
| 주인님 | 복잡한 수정 방향과 운영 배포를 결정하고 필요한 자료·권한·업무 판단을 제공 | 시스템 내부 실행 절차를 대신 수행할 필요 없음 |

모든 인계는 DB 행을 통해서만 한다. Codex가 Sam을 호출하거나 Sam이 Codex를 호출하지 않는다. 양쪽의 주기 실행이 같은 행의 현재 행동을 읽는다.

## 3. 한 행의 정상 흐름

1. 제품 코드가 오류를 기록한다. 새 실제 오류의 `next_action`은 `investigate`다.
2. main의 `exdigm-repair.timer`가 단일 `repair_once.py`를 실행한다. 한 번에 한 행만 claim하고 `automation_run`, `workspace_reserved=yes`를 같은 행에 기록한다.
3. `investigate`에서 main Codex가 원인과 범위를 조사한다.
   - 기존 계약을 보존하는 단순 결함: 수정·공식 검사·리뷰·커밋까지 진행하고 `approve_deploy`를 기록한다.
   - 구조·업무 규칙·권한·데이터 의미나 여러 선택지가 걸린 변경: 원인·권장안·대안·영향·검증·복구를 갖춘 `approve_change`를 기록한다.
   - 주인님만 제공할 수 있는 자료·권한·업무 선택: `user_action`을 기록한다.
   - 외부 담당자·서비스·조건 대기: `external_wait`를 기록한다.
   - 수정 없이 실제 업무 결과까지 확인됨: 근거와 함께 `none`으로 닫는다.
4. Sam의 10분 보고 작업이 완료 결과를 읽어 주인님께 전달한다. 보고 성공이 확인된 revision만 체크포인트로 소비한다.
5. 주인님 답을 Sam이 같은 행에 기록한다.
   - 변경 승인: `approve_change → repair`
   - 배포 승인: `approve_deploy → deploy`
   - 거절: `→ none`
   - 보류: 현재 승인 요청 유지
   - 수정 지시: `→ investigate`
   - 필요한 자료·답 제공: `user_action|external_wait → investigate`
6. main 작업자가 다음 주기에 DB를 다시 읽는다.
   - `repair`: 승인된 범위만 수정·검증·리뷰·커밋하고 `approve_deploy` 기록
   - `deploy`: 같은 작업자가 결정론적 제한 명령으로 승인된 커밋만 공식 배포하고 `verify_result` 기록
   - `verify_result`: main Codex가 원래 실패 업무의 실제 산출물·상태·외부 효과를 확인하고 종료 또는 후속 행동 기록
7. Sam이 결과를 다시 보고한다. 실제 필수 결과가 확인돼야 `none`으로 종료한다. 코드 배포 성공만으로 업무 복구를 선언하지 않는다.

## 4. DB 행동의 의미

| `next_action` | 다음 담당 | 의미 |
|---|---|---|
| `investigate` | main Codex | 증거 수집·원인 판단·허용된 단순 수정 |
| `repair` | main Codex | 주인님이 승인한 복잡한 수정 범위 실행 |
| `approve_change` | 주인님↔Sam | 구체적 수정 방향 결정 대기 |
| `approve_deploy` | 주인님↔Sam | 정확한 검증 커밋의 운영 배포 결정 대기 |
| `deploy` | main 단일 작업자 | 승인된 커밋의 공식 배포 |
| `verify_result` | main Codex | 원래 업무 결과 확인 |
| `user_action` | 주인님↔Sam | 주인님만 제공할 수 있는 입력 대기 |
| `external_wait` | Sam 보고, 외부 담당 | 외부 조건과 재개 조건 대기 |
| `none` | 없음 | 근거 있는 종료 또는 명시적 거절 |

`in_progress`는 현재 작업 소유 표시일 뿐 별도 단계가 아니다. 완료·실패 결과는 `processing_history`에 추가하고 기존 오류 원문을 덮어쓰지 않는다. `entry_id`와 `expected_revision`으로 응답 유실 재전송은 멱등 처리하고, 다른 판본의 결과는 거부한다.

## 5. 작업 공간과 배포 보호

- 실제 코드는 제품 서버의 `/home/chaconne/exdigm-debug`에서만 수정한다. 운영 체크아웃은 직접 수정하지 않는다.
- main 작업자 하나가 DB claim, `runtime/operational-repair.lock`, `runtime/operational-repair.json`을 함께 소유한다.
- 검증 커밋은 `refs/operational-repairs/<automation-run>`에 보존하고 debug를 운영 기준 커밋으로 되돌린 뒤 승인 대기한다.
- 배포 승인 뒤 같은 main 작업자가 새 claim과 같은 OS 잠금을 잡는다. 제품 서버의 제한 배포 명령은 DB 승인 영수증·오류 UUID·revision·커밋·보관 ref·현재 예약을 모두 대조한 뒤 `scripts/deploy/deploy.sh prod`만 실행한다.
- 별도 `exdigm-deploy.service`·timer·Codex는 두지 않는다.
- 중단 시 시간 경과만으로 예약을 빼앗지 않는다. 실행 자료, 프로세스, DB revision, debug HEAD·dirty 상태, 보관 ref, 운영 HEAD를 대조한 뒤 같은 실행을 재개하거나 명시적으로 해제한다.

## 6. Sam의 통신 계약

Sam은 제한된 `sam-record` 연결만 사용한다. 이 연결은 완료 결과 목록, 승인에 필요한 안전한 행 정보, 주인님 응답 기록만 허용한다. 원시 traceback·제품 셸·debug 쓰기·배포 명령을 제공하지 않는다.

결정은 실제 주인님의 현재 Telegram 개인 메시지와 오류 UUID·revision·request hash에 묶는다. 정기 cron, 요약 메시지, 다른 사용자·대화, 과거 판본은 승인이 아니다. 기록 결과에는 항상 `sam_execution_allowed=false`를 반환한다.

## 7. 완료 조건

정리는 다음을 모두 직접 확인해야 완료다.

- 제품 DB 백업과 기존 처리 이력 보존
- Track·Transition·resolution 상태 구조 제거 후 기존 `OperationalError` 행 수·원문·유효 이력 보존
- 제품 코드가 오류 기록만 하고 자동 에이전트를 실행하지 않음
- main에 `exdigm-repair.service`·timer 하나만 존재하며 별도 deploy timer가 없음
- Sam 설치본에 코드 수정·배포 경로가 없고 제한된 DB 읽기·응답 기록만 가능
- 오류 한 건의 조사 결과 → Sam 보고 → 주인님 응답 기록 → main의 다음 행동 전환을 실제 제한 경로로 검증
- 배포가 포함된 경우 정확한 승인 커밋, 운영 HEAD, 서비스·HTTPS, 원래 업무 결과를 각각 구분해 확인

현재 작업의 실행 증거와 재개 상태는 같은 날짜의 `operational-error-event-pipeline-20260921.md`에 기록한다.
