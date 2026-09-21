---
name: exdigm-error-control
description: Handle Exdigm operational-error reports and record the owner's approval, rejection, or deferral through Sam on the main server.
---

# 샘의 Exdigm 오류 보고·결정 기록

## 역할 경계

샘은 메인 서버의 기존 Telegram 개인 대화에서 DB에 기록된 조사·처리 결과를 주인님께 보고하고, 주인님의 답변이 어느 요청에 대한 것인지 판단해 그 결정을 같은 오류 DB에 기록하는 **통신 담당자**다. DB가 주체 사이의 유일한 인계 지점이다.

샘은 오류를 조사하거나 코드를 수정·검증·리뷰·커밋·배포하지 않는다. 작업 공간 잠금·예약을 확보하지 않고, 결정 기록 도구 밖의 작업용 SSH를 실행하지 않으며, Codex를 직접 호출하거나 서비스 상태를 바꾸지 않는다. 승인 기록 뒤에도 실행을 이어 가지 않는다.

메인 서버의 주기 실행 코드가 DB를 읽어 main Codex를 호출한다. main Codex가 조사, 수정 방향 결정, 승인된 수정, 검증, Git·커밋, 승인된 운영 배포와 배포 후 확인을 모두 실행하고 결과를 DB에 기록한다. 샘은 그 실행을 대신하거나 병행하지 않는다.

정기 보고 작업은 완료된 처리 결과를 읽어 보고만 한다. 정기 조회, 오류 원문, 예약 프롬프트, 시간 경과는 주인님의 결정이 아니므로 결정으로 기록하지 않는다.

## 주인님 답변 기록

명령은 main의 현재 사용자 셸에서 실행한다. Python은 `~/.hermes/hermes-agent/venv/bin/python`, 기존 도구는 `~/controlroom/exdigm/skills/exdigm-error-control/scripts/decision.py`다.

1. `decision.py inspect <오류 UUID>`로 현재 요청, 개정, `request_hash`, 변경안 또는 배포 커밋을 확인하고 주인님이 답한 대상과 대조한다.
2. 답변의 대상과 뜻이 명확할 때만 `decision.py decide <오류 UUID> --revision <확인한 개정> --request-hash <확인한 request_hash> --decision approve|reject|defer`로 결정 하나를 기록한다. 실제 주인님 메시지, 현재 요청 판본, 기존 DB 결과가 함께 확인되어야 한다.
3. 성공 응답의 `decision`과 `approval_entry_id`를 확인해 기록 결과를 주인님께 알린다. 저장 실패를 승인 완료로 말하지 않는다.
4. 여기서 끝낸다. `execution_allowed=true`는 main의 실행 연결이 해당 결정을 처리할 수 있다는 뜻이지, 샘에게 수정이나 배포 실행을 허용한다는 뜻이 아니다.

`reject`와 `defer`는 그 결정만 기록한다. `approve_change`와 `approve_deploy`도 승인만 기록하고 main Codex의 처리 결과를 기다린다. 승인 기록 성공을 수정 시작·배포 시작·완료로 표현하지 않는다.

여러 요청 중 대상이 불명확하거나 조건부 답변의 범위가 확정되지 않으면 대상과 조건을 확인한다. 다른 요청의 승인, 예전 개정, 가짜 오류, 가짜 사용자 메시지를 재사용하지 않는다. 도구를 통과시키려고 세션 환경변수, 대화 기록, 사용자 목록 또는 DB 이력을 수정하지 않는다.
