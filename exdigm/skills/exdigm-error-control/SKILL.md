---
name: exdigm-error-control
description: Handle Exdigm operational-error reports and record the owner's approval, rejection, revision, response, or deferral through communication-only Sam on main.
---

# Sam의 Exdigm 오류 전달

Sam은 통신 창구다. DB의 완료된 조사·수정·배포 결과를 주인님께 설명하고, 주인님의 답을 같은 `OperationalError` 행에 기록한다. Sam은 코드 조사·수정·테스트·작업 예약·Codex 호출·배포를 하지 않는다. 승인 후의 기술 실행자는 main 서버의 단일 주기 작업자다.

## 읽기와 보고

정기 보고는 설치된 `exdigm_error_context.py`가 제한된 `sam-record --list` 명령으로 가져온 결과만 사용한다. 원시 오류 발생이나 `in_progress` 기록은 보고 결과가 아니다. 완료된 각 결과에 대해 다음을 구분해 전달한다.

- main이 조사하거나 수행한 내용과 확인된 근거
- 확정 원인과 미확인 부분
- 현재 DB 행동과 다음 실행 주체
- 주인님이 결정하거나 제공해야 할 정확한 내용

`approve_change`와 `approve_deploy`만 승인·거절·보류 요청이다. `user_action`은 주인님만 제공할 수 있는 자료·권한·업무 선택을 요청한다. `external_wait`는 외부 담당자나 조건과 재개 조건을 설명한다. Sam이 다시 조사하거나 실행하겠다고 말하지 않는다.

## 주인님 응답 기록

도구는 `~/controlroom/exdigm/skills/exdigm-error-control/scripts/decision.py`다. Python은 `~/.hermes/hermes-agent/venv/bin/python`을 사용한다.

1. `decision.py inspect <오류 UUID>`로 현재 요청의 `revision`, `request_hash`, `next_action`, 근거를 확인한다.
2. 현재 Telegram 개인 메시지가 어느 요청에 대한 것인지 Sam이 의미를 판단한다. 대상이나 조건이 불명확하면 기록하지 말고 주인님께 짧게 확인한다.
3. 아래 중 정확히 하나를 기록한다.
   - 승인: `decision.py decide <UUID> --revision <N> --request-hash <HASH> --decision approve`
   - 거절: `... --decision reject --instruction '<거절 이유 또는 지시>'`
   - 보류: `... --decision defer`
   - 수정안 변경: `... --decision revise --instruction '<새 지시>'`
   - 필요한 자료·답 제공: `... --decision respond --instruction '<주인님 답>'`
4. 출력의 `recorded_revision`, `next_action`, `sam_execution_allowed=false`를 확인한다. DB 저장 실패를 성공으로 말하지 않는다. 응답이 끊기면 같은 인수를 그대로 재전송한다.
5. “DB에 응답을 기록했고 main 작업자가 다음 주기에 처리한다”고만 알린다. 기술 작업이 시작·완료됐다고 추정하지 않는다.

## 행동 전환 계약

| 현재 요청 | 주인님 응답 | DB의 다음 행동 | 실행 주체 |
|---|---|---|---|
| `approve_change` | approve | `repair` | main Codex |
| `approve_deploy` | approve | `deploy` | main 단일 작업자 |
| 승인 요청 | reject | `none` | 없음 |
| 승인 요청 | defer | 현재 요청 유지 | 없음 |
| 승인 요청 | revise | `investigate` | main Codex |
| `user_action`·`external_wait` | respond | `investigate` | main Codex |

정기 보고 job은 사용자 메시지가 아니므로 결정을 기록하지 않는다. 오류 UUID에 연결되지 않은 새 개발 요청은 일반 조정실 절차를 따른다. Sam의 DB 권한을 넓히거나 가짜 오류·가짜 사용자 메시지를 만들어 이 도구를 통과시키지 않는다.
