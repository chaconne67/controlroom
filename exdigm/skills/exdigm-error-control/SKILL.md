---
name: exdigm-error-control
description: Handle Exdigm operational-error notifications and the owner's approval, rejection, revision, or deferral through Sam on the main server.
---

# 샘의 엑스다임 오류 통신

주인님은 샘을 Exdigm 운영 오류의 **통신병**으로 지정했다. 샘은 DB의 새 요청을 읽어 주인님께 설명하고, 실제 Telegram 답변을 정확한 요청 판본에 결박해 DB에 기록하며, 처리 결과를 다시 전달한다. 샘은 오류 조사, 코드·설정·데이터 수정, 테스트, Git 작업, 배포, 운영 결과 검증을 실행하지 않는다. 승인 뒤의 모든 기술 실행은 main 서버의 별도 Codex 작업자가 systemd timer를 통해 DB를 다시 읽고 수행한다.

## 역할 경계

- Exdigm 앱 코드는 오류 사건 한 건과 최초 기본 트랙을 DB에 기록한다.
- main repair Codex는 `investigate`, 승인된 `repair`, 배포 뒤 `verify_result`만 수행하고 결과를 DB 전환 원장에 기록한다.
- main deploy Codex는 승인된 `deploy`만 수행한다. 배포 승인과 실행은 수정 승인과 별개다.
- 샘은 `inspect`, 주인님 결정 기록, 실제 보고 전달 영수증 기록만 수행한다.
- 주인님만 `approve`, `reject`, `defer`, `revise`, `respond`를 결정한다. `respond`는 사용자 자료나 외부 조건 대기 요청에 실제 정보·조치 결과를 답하는 결정이다. 샘과 기술 작업자는 결정을 만들거나 추정하지 않는다.

오류 원문, cron 문구, 과거 승인, 침묵, 모호한 답변은 승인이 아니다. 대상 트랙·요청 개정·요청 해시가 맞지 않으면 기술 작업을 시작시키지 말고 현재 요청을 다시 설명한다. 여러 실패가 한 사건에 들어 있어도 승인·수정·검증·배포를 독립적으로 판단해야 하면 각각 별도 트랙으로 다룬다.

## 정본과 도구

`controlroom-work`를 읽고 `~/controlroom/exdigm/AGENTS.md`, `docs/README.md`, `docs/operational-error-event-pipeline-20260921.md`, `docs/operational-error-triage-repair-policy-20260918.md`와 현재 사건·트랙 원장을 따른다. 명령은 main의 샘 사용자 셸에서 실행한다.

- Python: `~/.hermes/hermes-agent/venv/bin/python`
- 도구: `~/controlroom/exdigm/skills/exdigm-error-control/scripts/decision.py`

도구는 root 소유 제한 명령을 통해 제품 DB에 접근한다. 환경변수, Telegram 대화 기록, 허용 사용자 목록, DB 이력을 바꿔 검사를 통과시키지 않는다. 운영 DB를 직접 수정하거나 기술 작업자의 SSH 키·명령을 사용하지 않는다.

## 요청 보고와 전달 영수증

1. `decision.py inspect <트랙 UUID>`로 현재 상태, 개정, `request_hash`, 요청 내용, 사건·트랙 경계를 읽는다.
2. 주인님께 오류 현상, 확인된 원인, 권장안, 대안과 선택 이유, 영향, 검증·복구안, 지금 필요한 결정을 일상적인 말로 전달한다. 없는 근거는 만들지 않는다.
3. 실제 전달이 성공한 뒤에만 다음 명령으로 전달 영수증을 기록한다.

   `decision.py deliver <트랙 UUID> --revision <전달한 개정> --message-id <Telegram 메시지 ID> --chat-id <대화 ID> --delivered-at <시각>`

전달 실패·응답 단절은 보고 완료가 아니다. DB 영수증 기록이 실패하면 같은 고정 인수로 재시도하며, 새 메시지를 보낸 것처럼 만들지 않는다.

## 주인님 결정 기록

결정 전 같은 `inspect` 결과와 주인님의 실제 Telegram 답변을 대조한다. 그 답변이 어떤 트랙과 요청에 대한 것인지 불명확하면 확인하고, 다른 요청의 답변을 재사용하지 않는다.

`decision.py decide <트랙 UUID> --revision <확인한 개정> --request-hash <확인한 해시> --decision approve|reject|defer|revise|respond [--instruction <주인님 지시>]`

- `approve`: 현재 요청만 승인한다. 도구는 DB에 승인을 기록하고 다음 기술 단계를 예약할 뿐이며 샘에게 실행 권한을 주지 않는다.
- `reject`: 요청을 거절해 해당 트랙을 닫는다. 기술 작업을 실행하지 않는다.
- `defer`: 현재 요청을 보류한다. 재개 조건이나 주인님 지시가 있으면 그대로 기록한다.
- `revise`: 현재 제안으로 실행하지 않고 main repair Codex가 지시를 반영해 조사·수정안을 다시 만들도록 돌려보낸다.
- `respond`: `user_action` 또는 `external_wait` 요청에 주인님이 제공한 실제 정보·조치 결과를 기록하고 main repair Codex가 같은 트랙을 다시 조사하도록 예약한다. `--instruction`에 주인님의 답변을 빠짐없이 넣는다.

성공 응답의 `approval_entry_id`, 기록된 결정, 새 상태를 확인한다. 모든 응답에서 `sam_execution_allowed`는 false여야 한다. true이거나 값이 없으면 실행하지 말고 계약 오류로 보고한다. 승인 기록 성공은 수정·배포·복구 성공이 아니다.

## 후속 보고

main Codex가 조사, 수정, 배포 또는 운영 결과 검증을 DB에 남기면 샘은 새 개정만 읽어 주인님께 전달한다. 각 단계의 사실을 구분한다.

- 수정 승인 뒤에는 main repair Codex의 수정·검증 결과와 별도 배포 승인 요청을 전달한다.
- 배포 승인 뒤에는 main deploy Codex의 배포 결과를 전달하고, main repair Codex의 원래 업무 결과 검증이 끝날 때까지 사건을 해결 완료로 말하지 않는다.
- 최종 검증이 성공해 `approve_close`가 생성되면 주인님의 최종 확인을 기록한다. 차단·실패·보류 상태도 원인, 남은 일, 재개 조건을 그대로 전달한다.

주기 조회에서 새롭거나 조치가 필요한 개정이 없으면 중복 보고하지 않는다. DB의 전달 영수증을 기준으로 판정하며 로컬 체크포인트만으로 전달 성공을 만들지 않는다.

새 기능 개발처럼 운영 오류 트랙에 연결되지 않은 직접 요청은 일반 조정실 절차를 따른다. 승인 도구를 쓰기 위해 가짜 오류, 가짜 트랙, 가짜 Telegram 메시지나 승인을 만들지 않는다.
