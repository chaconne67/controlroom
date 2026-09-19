---
name: exdigm-error-control
description: Handle Exdigm operational-error notifications and the owner's approval, rejection, or deferral through Sam on the main server.
---

# 샘의 엑스다임 오류·승인 처리

주인님이 오류 알림과 승인 창구를 메인 서버의 샘으로 지정했다. 샘은 기존 Telegram 개인 대화에서 요청을 설명하고 답변의 의미와 대상을 판단한다. 자동 조사·수정은 main Codex가 맡으며, 코드·검증·배포는 Exdigm 서버의 기존 공식 경로를 사용한다.

## 정본과 책임

`controlroom-work`를 읽고 `~/controlroom/exdigm/AGENTS.md`, `docs/README.md`, `docs/operational-error-triage-repair-policy-20260918.md`의 현재 승인·작업 소유 계약을 따른다. 오류 원문이나 cron 문구는 주인님의 승인이 아니다. 여러 요청 중 대상이 불명확하거나 조건부 답변의 범위가 확정되지 않으면 필요한 대상·조건을 확인한다.

도구는 기존 Hermes 대화 기록에서 현재 Telegram 메시지의 발신자·메시지 번호를 확인하고 요청 판본을 검사한다. 승인 여부의 의미 판단은 샘이 맡는다. 도구를 통과시키려고 세션 환경변수·대화 기록·사용자 목록·DB 이력을 수정하지 않는다.

샘이 전달한 배포 요청은 승인 답변이 어느 대화에 도착하든 샘이 유일한 배포 실행 소유자다. 다른 조정실 에이전트는 답변을 샘에게 인계하고 샘의 완료 결과를 확인하며 배포 명령을 실행하지 않는다. 주인님이 배포 실행자를 명시적으로 다른 주체로 바꾼 경우에만 그 주체가 이어받는다. 서버의 배포 잠금은 동시 실행을 막는 마지막 보호 장치이며 실행 소유자를 정하는 수단으로 사용하지 않는다.

## 기존 오류 요청에 대한 결정

명령은 main의 현재 사용자 셸에서 실행한다. Python은 `~/.hermes/hermes-agent/venv/bin/python`, 도구는 `~/controlroom/exdigm/skills/exdigm-error-control/scripts/decision.py`다.

1. `decision.py inspect <오류 UUID>`로 현재 요청·개정·request_hash·구체적 변경과 코드를 확인한다. 주인님이 답한 요청과 대조한다. 요청과 답변의 의미가 맞는지는 샘이 판단하며, 다른 요청의 승인을 재사용하지 않는다.
2. `decision.py decide <오류 UUID> --revision <확인한 개정> --request-hash <확인한 request_hash> --decision approve|reject|defer`로 결정을 기록한다. 실제 주인님 메시지, 현재 요청 판본과 내용, 기존 DB 결과 명령이 함께 확인되어야 성공한다. 응답이 끊기면 같은 인수를 재전송한다. 저장 실패를 승인 완료로 말하지 않는다.
3. 성공 응답의 `decision`과 `approval_entry_id`를 확인한다. reject/defer는 실행하지 않고 그 상태를 설명한다. approve는 `execution_allowed=true`일 때 승인된 범위의 다음 작업을 이어 간다. false이면 현재 개정/후속 처리를 재조회한다. 기록 성공은 배포 성공이 아니다.
4. 실제 작업 잠금을 확보한 뒤 기존 `record_operational_error_result`의 `--read`로 승인 기록과 현재 개정을 다시 대조한다. 승인 응답의 `recorded_revision`을 `--expected-revision`으로 사용해 실행 시작을 `--status in_progress`와 고정한 `--entry-id`로 먼저 기록하고, 성공한 실행 소유자만 작업한다. 승인 뒤 다른 처리가 진행됐으면 멈춘다. 같은 승인 영수증을 다시 읽었다는 이유로 두 번째 실행을 시작하지 않는다.

## 승인 뒤 실행

- `approve_change`: 승인된 제안·영향·검증·복구안과 DB 승인 근거를 main Codex CLI에 전달하고 같은 조정실 지침·문제해결·SSP·최소 구현·리뷰 경로로 수정한다. 승인된 제안 밖으로 넓어지면 새 요청을 기록한다. 구현 승인만으로 배포하지 않는다.
- `approve_deploy`: 샘이 주인님이 승인한 요청 개정·커밋·Git 보관 참조를 대조한 뒤 `exdigm-deploy`와 정책 8절의 같은 debug 잠금·예약을 확보해 공식 배포를 진행한다. 다른 writer가 있으면 해당 배포만 대기로 남긴다. 이전 미승인 변경을 섞지 않는다. 운영 기준이 바뀌어 새 커밋이 필요하면 원본을 보존하고 재검증한 새 요청을 주인님께 알린다.
- 배포·원래 업무 결과 확인과 남은 행동은 기존 `record_operational_error_result`로 같은 오류의 처리 이력에 남긴다. 프로그램 배포 성공을 이전 실패 업무의 복구 성공으로 대신 기록하지 않는다. 이미 시작된 실행의 응답이 끊겼으면 실제 프로세스·운영 판본·기록부터 확인하고 같은 배포를 무작정 반복하지 않는다.

새 작업·초기 설치 등 오류 UUID에 연결되지 않은 주인님의 직접 요청은 일반 조정실 작업 절차를 따른다. 이미 샘이 전달한 배포 요청의 답변은 오류 UUID가 없어도 위 배포 소유 규칙을 따른다. 승인 도구를 쓰려고 가짜 오류나 가짜 사용자 메시지를 만들지 않는다. 운영 DB가 이 기능의 저장 구조를 아직 제공하지 않으면 도구가 중단한 이유를 설명하고 검증된 기능의 초기 배포 승인을 별도로 받는다.
