---
name: exdigm-error-control
description: Use when monitoring, investigating, repairing, or deploying changes for Exdigm operational errors.
---

# 샘의 Exdigm 운영 오류 관리

## 책임

샘은 Exdigm의 `projects.OperationalError`를 직접 조회하고, 새 오류나 처리 내용이 바뀐 오류를 직접 조사해 주인님께 쉽게 보고한다. 별도의 main Codex 작업자에게 조사·수정·배포를 넘기지 않는다.

정기 실행은 **조회·조사·보고만** 한다. 소스·Git·운영 DB·서비스·배포 상태를 바꾸지 않는다. 수정·커밋·배포·운영 데이터 재처리는 주인님의 명시적 지시를 받은 대화에서 샘이 직접 수행한다. 수정 지시가 있으면 `~/controlroom/exdigm/AGENTS.md`의 원격 debug worktree, 검증, 리뷰, 커밋 경계를 따르고, 배포는 별도 명시가 있을 때만 공식 배포 경로로 실행한다.

## 정기 조회

main에서 10분마다 실행되는 Hermes cron이 이 스킬의 정기 진입점이다. cron의 `workdir`는 `~/controlroom/exdigm`, 연속 실행 제한은 3분이므로 한 번에 끝내지 못한 조사는 확인한 사실과 정확한 재개 지점을 보고하고 멈춘다.

1. `~/.gbrain-agent.md`, 프로젝트 `AGENTS.md`, `docs/README.md`와 관련 진행 문서를 확인한다.
2. SSH 대상 `chaconne@49.247.202.197`, debug worktree `/home/chaconne/exdigm-debug`에서 `scripts/debug_workspace.sh shell-readonly`를 사용해 `projects.OperationalError`를 SELECT만 한다. ORM 필드는 현재 모델에서 확인하며 이름을 추측하지 않는다.
3. `~/.hermes/state/exdigm-error-control.json`의 오류별 마지막 보고 `handling_revision`과 비교한다. 상태 파일은 알림 중복 방지용이며 Exdigm DB의 처리 상태를 대신하지 않는다.
4. 다음 항목만 새 조사 대상으로 삼는다.
   - 상태 파일에 없는 `next_action=investigate` 오류
   - `handling_revision`이 마지막 보고보다 증가한 오류
   - 마지막 보고 뒤 새로 생긴 오류 중 조사나 주인님의 판단이 필요한 오류
   과거 `next_action=none`, 성공 완료, 시험용 오류는 새 증거가 없으면 다시 보고하지 않는다.
5. 조사 대상이 없으면 최종 응답을 정확히 `NO_REPLY`로 끝내 전달을 억제한다.

## 조사

오류 문구를 원인으로 단정하지 않는다. `systematic-debugging` 절차로 다음 증거를 가능한 범위에서 직접 확인한다.

- 오류 행의 `summary`, `description`, `context`, `traceback`, `processing_history`, `handling_context`와 연결된 업무 객체
- 오류가 난 현재 코드와 실제 호출자·입력 흐름
- 운영·debug Git 상태와 관련 최근 변경
- 같은 유형의 기존 성공 사례와 관련 진행 문서
- 운영 데이터를 바꾸지 않는 최소 재현 또는 읽기 전용 대조

고객 원문·인증값·개인정보는 보고나 공유 문서에 복제하지 않는다. 조회 권한, 시간, 재현 자료가 부족하면 근본 원인을 확정하지 말고 확인된 사실과 미확인 부분을 구분한다.

## 보고와 체크포인트

보고에는 오류별로 다음만 담는다.

- 오류 ID와 발생 시각
- 무엇이 실패했는지 쉬운 설명
- 사용자 업무에 미친 영향
- 확인한 근본 원인, 또는 아직 원인 후보인 이유
- 권장 해결 방향과 수정·배포 여부
- 주인님이 결정하거나 제공해야 할 것이 있을 때만 구체적인 다음 행동

정기 실행은 수정이나 배포 승인을 전제로 묻지 않는다. 조사 결과 수정이 필요하면 “수정 필요, 미실행”으로 알린다. 이미 검증된 수정이 있어도 주인님의 명시적 배포 지시 전에는 배포하지 않는다.

보고가 실제 전달될 최종 응답에 포함된 뒤 해당 오류의 `handling_revision`, 보고 시각, 조사 결과 요약 해시를 상태 파일에 원자적으로 저장한다. 조사나 전달이 실패하면 성공한 체크포인트로 기록하지 않는다.

## 주인님 지시 후 실행

주인님이 특정 오류의 조사·수정·검증·배포를 지시하면 샘이 현재 대화에서 직접 수행한다. DB의 과거 `next_action`, 자동화 예약, 이전 승인 기록을 현재 지시로 간주하지 않는다. 작업이 끝나면 실제 검증 결과와 남은 위험을 보고하며, 필요할 때 Exdigm의 기존 오류 기록 API로 처리 결과를 남긴다. 기록을 위해 운영 DB를 임의 SQL로 수정하지 않는다.
