# OperationalError 한 건의 사람 포함 처리 흐름

작성일: 2026-09-21 KST  
목적: 과도하게 구현된 Track·Transition·별도 배포 작업자를 제거하고, 기존 오류 행 하나를 통해 제품·main Codex·Sam·주인님이 각자의 일만 하게 한다.

## 최종 구조

```text
Exdigm 제품 코드
  └─ 실패 사실을 OperationalError 한 행에 기록
          ↓ main 1분 주기 조회
main 단일 작업자 → Codex 조사·수정·검증 → 같은 행에 결과/요청 기록
          ↓ Sam 10분 주기 조회
Sam → 주인님께 설명
          ↓ 실제 Telegram 답변
Sam → 승인·거절·보류·수정 지시·자료 제공을 같은 행에 기록
          ↓ main 1분 주기 재조회
main 단일 작업자 → DB에 지정된 repair/deploy/verify 실행 → 같은 행에 결과 기록
          ↓
Sam 보고 → 주인님 확인 → 근거 있는 종료
```

직접 호출선은 없다. 제품은 main이나 Sam을 호출하지 않고, Codex와 Sam도 서로 호출하지 않는다. 각자는 DB의 현재 행동과 새 이력만 읽는다.

## 이번 축소 변경

### 제품 저장소

- 유지: `OperationalError`, `record_processing_result`, `record_operational_error_result`
- 제거: `OperationalErrorTrack`, `OperationalErrorTransition`, `resolution_status`, 별도 파이프라인 관리 명령·서비스
- 추가하지 않음: 큐 서버, 메시지 브로커, 새 오류 DB, 제품 서버의 Codex·Hermes·systemd 작업자
- 마이그레이션: 잘못 일괄 대기열에 올린 과거 행을 원래 행동으로 복원하고, 중지된 예약을 이력에 남겨 해제한 뒤 추가 표를 삭제

### main 조정실

- 유지·확장: `repair_once.py` 하나와 `exdigm-repair.service`·timer 하나
- 제거: `pipeline_once.py`, `deploy_once.py`, `exdigm-deploy.service`·timer, 별도 deploy 계정 실행 경로
- 조사·수정·업무 결과 확인은 Codex가 수행한다.
- 배포는 Codex의 자유 명령이 아니라 같은 작업자가 DB 승인 계약을 제한 배포 명령에 전달하는 결정론적 단계다.

### Sam

- 정기 작업: 제한된 DB 결과 목록을 읽고 Telegram으로 보고
- 사용자 답변: 오류 UUID·revision·request hash와 실제 Telegram 메시지를 묶어 DB에 기록
- 제거: debug 작업 공간 접근, 수정·검증·커밋·배포 책임, Codex 재호출, 별도 역할 차단 hook

## 단계별 예시

| revision | DB 행동 | 행위자 | 기록되는 것 |
|---:|---|---|---|
| 1 | investigate | 제품 | 원래 오류 사실 |
| 2 | investigate/in_progress | main 작업자 | 실행 번호와 작업 공간 예약 |
| 3 | approve_change | main Codex | 원인, 권장 수정안, 영향, 검증, 복구 |
| 4 | repair | Sam | 주인님의 승인 메시지 증명과 결정 |
| 5 | repair/in_progress | main 작업자 | 새 실행 번호와 예약 |
| 6 | approve_deploy | main Codex | 검증된 commit, 검사 증거, 보관 ref |
| 7 | deploy | Sam | 주인님의 정확한 commit 배포 승인 |
| 8 | deploy/in_progress | main 작업자 | 배포 실행 소유 |
| 9 | verify_result | main 작업자 | 공식 배포 결과와 운영 commit |
| 10 | none 또는 후속 행동 | main Codex | 원래 실패 업무의 실제 결과 |

단순 결함이면 revision 3에서 main Codex가 바로 수정·검증·커밋하고 `approve_deploy`로 갈 수 있다. 주인님이 수정안을 바꾸면 `investigate`, 보류하면 승인 요청을 그대로 유지하며, 거절하면 근거를 남기고 `none`으로 끝낸다.

## 2026-09-21 정리 작업의 잠금·백업

- 자동 실행 동결: main의 repair/deploy timer 및 service 정지, Sam 10분 job 일시 중지
- 운영 DB 백업: `/mnt/pgdata/exdigm/backups/manual/operational-error-cleanup-20260921T193447+0900/operational-error-tables.dump`
- 백업 SHA-256: `65d550f8a9663fb79067c96d50b1a58b4ea690117420ae29e0b56020e338b8ba`
- 백업 대상: `django_migrations`, `projects_operationalerror`, 추가 Track·Transition 표의 schema+data
- 기준선: 66개 오류 행, 66개 Track, 222개 Transition. 추가 표와 원래 오류 행의 투영 불일치는 0건이었다.
- 중지된 실행 `5887d92d-18ea-4b3a-bb00-f73448fa9ac3`은 프로세스·잠금·결과 부재를 대조한 뒤 이전 예약만 해제했다. 코드·배포 결과는 없었다.

## 재개 및 완료 기록

제품 축소는 `26a2cb30c491983f8e25809e9f88312afd141c17`로 2026-09-21 20:37 KST에 공식 운영 배포됐다. 운영 오류 66개 행은 보존됐고, Track·Transition 표와 `resolution_status` 열은 제거됐다. 배포 뒤 행동 분포는 `none 59`, `investigate 5`, `approve_deploy 1`, `external_wait 1`이며 활성 작업공간 예약은 0건이다. 운영 Swarm 서비스는 모두 1/1이고 `https://office.exdigm.com/`과 로그인 경로는 HTTP 200을 반환했다.

Controlroom 축소 판본은 `98ec8684d7cec3f7c2d77f2497d2a0cfc9a24175`다. main에는 `exdigm-repair` 단일 service·timer와 하나의 제한 계정만 남겼다. 별도 deploy service·timer·설정·DB 기록 키·개인키는 제거했고 계정은 잠갔다. Sam의 역할 차단 hook은 제거했으며, 설치된 monitor·checkpoint·skill·decision 파일은 Controlroom 정본과 SHA-256이 같다. Sam은 제한 DB 명령만 사용한다.

main·Sam 변경 전 복구본은 `/var/backups/exdigm-operational-cleanup-e49f9d64/`에 root 0700 폴더와 0600 파일로 보관했다. `main-runtime-before.tar.gz` SHA-256은 `2a28f7343aad2a8bc79e455d2e55243300fe5778b9c8541685a7650b7124c30a`, `main-run-evidence-before.tar.gz`는 `a1d9aa2e06aedfad277b05aeb5bad1335f8150c92f7e92fca721a5fc88b4ca90`다. 제품 제한 접근 복구본 `product-access-before.tar.gz`는 제품 서버의 같은 백업 폴더에 있고 SHA-256은 `cec86a02b700e7914e127907e602b19fa62b693713552ab05e5a892113e7b34d`다.

1. ~~제품과 controlroom 축소 diff의 관련 검사를 통과시킨다.~~ 완료
2. ~~코드 리뷰와 skill 리뷰에서 확인된 결함을 고치고 재검사한다.~~ 완료
3. ~~제품 축소 마이그레이션을 공식 배포하고 DB 행·이력 보존, 추가 표 제거, 서비스·HTTPS를 확인한다.~~ 완료
4. ~~main의 단일 작업자와 Sam의 제한 통신 경로를 설치한다. 별도 deploy unit·키·runtime은 백업 후 제거한다.~~ 완료
5. ~~실제 제한 계정으로 read/claim/decision/deploy 계약을 검증한다. 승인이나 실제 운영 변경을 가장하지 않는다.~~ 완료. main preflight는 운영·debug `26a2cb30` 일치를 확인했고 승인 없는 deploy 명령은 거절됐다. Sam은 현재 요청 두 건의 revision·request hash를 읽었지만 응답을 기록하지 않았다.
6. ~~timer와 Sam job은 안전한 대기열 상태를 확인한 뒤에만 재개한다.~~ 완료. main timer와 Sam 10분 job은 active다.
7. 실제 오류 한 건의 자연 흐름도 확인했다. 오류 `da629c53-6d34-2a93-646b-c655c28bec50`을 main 실행 `e41e5b7b-1f0e-40c2-a184-a2b151a07a43`이 가져가 진단 저장 계약 결함을 수정했다. 집중 검사 13개와 Django check를 통과한 `1aba84c20a068b5fa046a9a8c531a31e4714dcde`를 `refs/operational-repairs/e41e5b7b-1f0e-40c2-a184-a2b151a07a43`에 보관하고 DB revision 3의 `approve_deploy`로 기록했다. 운영 배포는 하지 않았고 작업공간은 clean `26a2cb30`으로 복귀했으며 예약·OS 잠금은 해제됐다. Sam 실행 `90526e5b18a542ebb49824edaa266a49`는 이 결과를 포함한 새 완료 결과를 기존 Telegram 대화로 전달했고, 21:02 KST 영수증은 `delivered`, 오류 없음이다. 이후 실제 주인님 응답과 deploy·verify는 자연 흐름에서 계속 처리한다.

정리 구현과 첫 실제 main 처리·Sam 전달까지 완료했다. 테스트 행을 운영 오류인 것처럼 만들거나 주인님의 승인을 대신 기록하지 않았다. 남은 것은 주인님의 실제 결정 이후 이어지는 deploy·verify 단계이며, 이는 이 정리 작업에서 가짜 승인으로 닫지 않는다.
