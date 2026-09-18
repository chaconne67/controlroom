# CRETOP 회사별 저장과 중단 후 재개

최종 상태(2026-09-18 23:38 KST): 승인된 원래 500개 모두 조회 결과를 보존했고 중앙 DB 저장까지 완료했습니다. 상세 265개 / 검색 결과 없음 235개, 상세 본문 2,120개, 품질 보류 0개입니다. 아래의 수집 중 기록은 당시 상태이며 최종 검증과 복구 경로는 마지막 절을 따릅니다.

2026-09-18 주인님이 회사 한 개의 조회가 끝날 때마다 파일을 저장하고, 재시작하면 저장된 회사 다음부터 이어서 처리하도록 승인했습니다.

## 목적과 범위

기존 수집기는 배치 결과를 메모리에만 모아 마지막에 파일을 썼습니다. 350개 작업은 조정실 PC의 03:04 전원 종료로 최종 결과 파일을 남기지 못했습니다. 운영 DB에서 앞선 150개(상세86개, 조회 결과 없음64개)는 보존됐고, 뒤350개 저장은0건임을 읽기 전용으로 확인했습니다.

공식 서버 `/home/chaconne/projects/ceoloan`의 `scripts/cretop_local.py`와 관련 검증만 수정합니다. 조회·로그인·공용 숨은 브라우저 수명주기·8개 화면 품질검사·`remote-batch-fetch`의 중앙 저장 계약은 보존합니다. DB 스키마·인증정보·제품 웹 배포·예약 작업은 변경하지 않습니다.

## 기준선과 실행 경로

- 서버 `chaconne@49.247.192.127`, main, 시작 commit `efc8f2ddff789084543a6ea7d47f089de8b0ab1d`, Git 작업 상태 깨끗함.
- 수정 전 `scripts/test_cretop_local.py`:12개 통과. 운영 이미지의 Python3.13을 네트워크 없는 별도 컨테이너에서 사용하고, 저장소에 이미 선언된 개발 도구만 임시 검증 경로에 설치했습니다.
- 보호 대상: 저장된150개, 처음 선정한500개 목록, 실패 작업의 증거, 개인 Chrome, 전용 프로필, .env, 운영 서비스와 기존 사용자 변경.
- 공식 경로: 승인 payload → `cretop_local.py collect` → `LocalCollector.collect_one` → 회사마다 `write_result` → 최종 결과 → 기존 정제·전송 → `remote-batch-fetch`의 품질검사·company 저장.
- 최소 구현 게이트:3단계. 기존 `write_result`를 재사용하고 Python 표준 `flush`, `fsync`, `replace`로 기록 확정·파일 교체를 구현합니다. 기존 `JsonResult.write_atomic`에는 기록 확정이 없고 다른 agent 경로의 책임이므로 함께 변경하지 않습니다.

## 저장과 재개 계약

결과 파일은 기존 outbox의 `<run-id>.json`을 유지합니다. 시작 시와 회사 완료 직후 파일을 저장하고, 임시 파일의 기록이 확정된 뒤 기존 결과를 교체합니다. 저장 실패 시 다음 회사로 진행하지 않습니다.

같은 run-id와 같은 payload로 `collect`를 실행하면 저장된 성공 항목의 순서를 검증하고 다음 회사부터 처리합니다. 전체 회사 목록의 지문을 비교해 아직 조회하지 않은 뒷부분의 변경도 거부합니다. 완료 파일은 재조회하지 않습니다. 처리 중 파일은 완료로 보고하지 않습니다. 정상 오류로 멈춘 작업은 실패 증거를 보존하고 기존 스킬대로 새 run-id를 사용합니다.

회사별 파일 저장과 중앙 DB 저장을 구분합니다. 회사별 저장은 PC 전원 종료에 따른 진행 결과 유실을 막습니다. 중앙 DB 저장은 기존 배치 회수·품질검사 경로가 담당합니다.

## 검증과 재개 정보

필수 검증은 회사 간 저장 확인, 자식 프로세스 강제 종료 후 같은 작업 재개, 파일 교체·디스크 기록 실패 시 이전 결과 보존, 회사 목록 변경 거부, 완료 작업의 중복 조회 방지, 정상 오류 증거 보존입니다. 수정 뒤 같은 기존 검증과 관련 검사·코드 리뷰를 완료합니다. 검증한 source만 commit/push하고 조정실 실행본에 적용한 뒤 hash를 확인합니다.

남은350개는 `C:\cretop-local\inbox\20260918_mortgage_detail_350_150806_payload.json`에 동결돼 있습니다. 이 run-id의 수집 원문은 없으므로 새 저장 기능 적용 후 같은 승인 목록으로 시작할 수 있습니다. 이후 전원이 꺼지면 같은 run-id와 payload로 재개하며, 이미 저장된 성공 회사는 재조회하지 않습니다. 운영 서버의 배치 증거 루트는 `/srv/consolidation/data/cretop/detail_collection`입니다.

현재 상태:회사별 저장·재개 구현 완료. 수집기 검증22개와 기존 중앙 저장 직접 소비자4개, 총26개가 통과했습니다. 정상 종료가 아닌 `os._exit(137)` 뒤에 첫 회사의8개 화면이 남고 같은 작업으로 두 번째 회사부터 재개함을 확인했습니다. 기록 확정·파일 교체 실패 시 이전 파일 보존, 아직 처리하지 않은 회사 목록의 변경 거부, 마지막 회사 저장 직후 종료 복구, 완료 작업과 옛 형식 완료 작업의 중복 조회 방지도 확인했습니다. Ruff·diff 검사 통과, 마지막 코드 리뷰에서 승인된 finding과 열린 계약 질문이 없습니다.

서버 commit `5a17fc8`을 `ceoloan/main`에 push했고 조정실 실행본에 적용했습니다. 서버와 실행본의 SHA256은 `7c7667b37760f2ba24f6b60059b4d9f0aaaafbff08d7b8579c60ff01bc09233d`로 같습니다. 조정실 변경 전 source는 `C:\cretop-agent\cretop_local.py.pre-checkpoint-20260918`에 보존했습니다. 운영 웹 이미지는 배포하지 않았고 기존 fetch 모듈을 재사용합니다.

기존 승인된350개를 백그라운드로 재개했습니다. 시작 확인 때2개 회사의 결과가 배치 종료 전에 파일에 저장됐으며, 첫 회사의8개 화면 모두 본문이 남아 있었습니다. 공용 관찰기의 데스크톱 간섭은0건입니다. 중앙 DB의150개 저장과 새 배치의 로컬 파일 저장 개수는 구분합니다. 전체 배치 완료·중단 때 기존 Windows 알림을 요청하며, 에이전트는 이후 계속 조회하지 않습니다.

현재 상태 파일은 `C:\cretop-local\outbox\20260918_mortgage_detail_350_150806_background_status_resume_041132.json`, 관찰 기록은 같은 outbox의 `20260918_mortgage_detail_350_150806_monitor_resume_041132.json`입니다. 이전 상태·관찰 기록·로그는 보존했습니다. 원문 checkpoint는 기존 `20260918_mortgage_detail_350_150806.json`이며, 회사별 저장은 여기서 확인합니다. 전원 종료 후 같은 작업 재개는 적용된 공식 collect에 같은 run-id/payload를 넘겨 실행합니다.

## 코드 리뷰 계약

원천은 이번 회사별 파일 저장·중단 후 재개 승인과 기존 실행 계약입니다. base는 시작commit `efc8f2d`, head는 이번 작업 diff이며, 수정 범위는 두 CRETOP local 파일입니다. 상위 목적은 기존 브라우저 조회 결과를 중단에도 보존해 공식 중앙 저장 경로에 넘기는 것입니다.

- 입력:같은 run-id, 승인된 payload, 숫자10자리 사업자번호. 재개 파일의 mode·개수·항목별 회사와 실행 ID·전체 목록 지문을 대조합니다.
- 절차:시작 상태 저장 → 회사 조회 → 디스크 기록 확정 → 결과 파일 교체 → 다음 회사. 진행 중/완료/정상 오류 중단을 구분합니다. 정상 오류의 실패증거는 덮어쓰지 않습니다.
- 출력:기존 items/lead/result 형식을 유지하고 진행 상태·완료 개수·목록 지문을 추가합니다. 완료 파일은 재조회하지 않으며, 저장 실패에서는 다음 회사로 진행하지 않습니다.
- 직접 영향:collect_batch와 write_result 호출자(company-list), Json 결과 파일을 읽는 fetch_remote_batch와 품질검사. 기존 품질검사·회사 사실·DB 역할·개인 Chrome·인증·150개 저장은 보호합니다.
- 비목표:DB 스키마 변경, 회사별 DB 직접 쓰기, 사이트 이동·좌표·로그인 변경, 운영 웹 배포, 부팅 시 자동 실행·예약 작업 신설.
- 검증:수집기22개 검사와 기존 fetch의 품질 실패 보류·오류 중단 항목 보류·로컬 결과 재사용·원격 작업 정리 생략 검증. 실제 실행본 hash와 공식 CLI의 checkpoint를 적용 후 확인합니다.

리뷰 관점은 변경 diff의 파일 보존·재개 위치·완료 판정, 직접 소비자의 결과 형식·품질검사입니다. 스타일·상위 구조 확대는 finding으로 취급하지 않습니다.

## 2026-09-18 최종 500개 저장과 DB 회수 복구

재개한 350개는 16:21:07에 수집을 마쳤습니다. 상세 179개 / 검색 결과 없음 171개, 오류 0개이며 상세 179개의 8개 화면, 총 1,432개 본문이 모두 파일에 보존됐습니다. 그러나 당시 저장 컨테이너에 `docs/cretop/schema/cretop_structured_schema_20260708.sql`이 없어 `remote-batch-fetch`가 중단됐습니다. 23:33 확인 때 DB는 기존 150개만 보존돼 있었고, 새 350개 저장은 0개였습니다. 원문과 정제 결과는 PC·main에 남아 있어 재조회가 필요하지 않았습니다.

복구 전 기준선: 서버 main 062b42b의 추적 파일 변경 없음(별도 조정실 지침 폴더·파일의 미추적 상태는 보존), 기존 150개 조회 86 present / 64 absent·상세 86개·본문 688개, 새 350개 DB 저장 0개. 수집 원문·동결 payload·개인 Chrome·인증·운영 웹·Compose 정의·DB 권한을 보호합니다. 중앙 fetch·구조화 코드와 SQL은 5a17fc8 이후 변경되지 않았고, 실행 이미지의 중앙 두 모듈도 서버 source와 같은 hash입니다. 최소 구현 게이트 2단계: 기존 Compose 단발 작업과 `remote-batch-fetch`를 재사용합니다.

`.dockerignore`는 `docs/`를 제외하며 운영 앱 이미지에도 SQL이 없습니다. 따라서 공식 경로는 기존 결과 정제·전송 → evidence 루트 bind → schema 디렉터리 읽기 전용 bind → 같은 run-id의 `remote-batch-fetch` → 읽기 전용 DB 검증입니다. 실행할 때 기존 세 Compose 정의의 `run --rm --no-deps -T --entrypoint python`을 쓰며 `-v /srv/consolidation/data/cretop/detail_collection:/app/docs/cretop/detail_collection`에 `-v /home/chaconne/projects/ceoloan/docs/cretop/schema:/app/docs/cretop/schema:ro`를 함께 지정합니다. 단발 환경의 `CRETOP_LOCAL_DB_HOST=postgres`, `CRETOP_LOCAL_DB_PORT=5432`를 유지합니다. 영구 환경·제품 배포·프로그램 코드·DB 구조는 이번 복구로 변경하지 않았습니다.

저장 전 정제 결과와 main 결과 SHA256 `c25d2dca396dbf0594ebb25a6e555c3990aed1379c5d397e8d823f828cbeaf2a`, 350개 회사 목록 일치, 상세 179개 공식 품질검사 통과·보류 0개를 확인했습니다. 기존 SQL이 요구하는 28개 테이블 / 27개 인덱스 / 2개 추가 칼럼은 모두 DB에 이미 있었습니다. 저장 뒤 같은 결과 SHA와 company 구조 지문 `efae893f7a2a8f3548f998ac3f606b16974a6ae538bca7cf7d14f8b43e770d92`가 유지됐습니다.

같은 run-id의 공식 fetch는 350개 저장·already_saved 0개·deferred 0개로 끝났습니다. main `company_main` primary에서 읽기 전용으로 기존 150개 보존, 새 350개 179 present / 171 absent·상세 179개·본문 1,432개·8개 화면 전체 존재를 확인했습니다. 승인 500개 전체는 265 present / 235 absent·상세 265개·본문 2,120개이며 대상별 중복 조회 기록 0개입니다. `remote-batch-fetch`의 fetch_summary는 main 기존 run 디렉터리에 남았습니다.

현재 완료 상태 정본은 `C:\cretop-local\outbox\20260918_mortgage_detail_350_150806_background_status_db_recovery_20260918_233810.json`이며 기존 500개 index가 이를 가리킵니다. 이전 중단 상태·index·수집 원문·정제 결과는 보존했습니다. 23:38:40 Windows Codex 완료 알림 Show 호출이 정상 반환됐습니다(사용자의 실제 수신·열람은 확인하지 않음). 이 500개에는 추가 수집·재개 작업이 남아 있지 않습니다. 다음 새 배치는 새로운 수집 범위 승인과 동결 대상 선택을 따릅니다.

## 2026-09-19 텔레그램 알림 연결 변경 잠금

주인님은 PC의 기존 봇 설정 C:\Users\chaconne\Desktop\.env를 사용해 알림이 오도록 수정하라고 승인했습니다. 원래 500개는 DB 저장 완료 상태이며 재조회·재저장하지 않습니다. main source base는 062b42be8e36ede479df3e5c489119971e1b715d입니다. 추적 파일 diff는 없고 .agents/, .claude/, AGENTS.md, CLAUDE.md 미추적 상태는 보존합니다. 조정실 controlroom의 기존 문서 변경 4개와 미추적 RNDLOG 계획도 보존합니다.

원하는 결과는 PC 수집 오류 때 중단 알림, 중앙 품질검사와 회사별 DB 저장이 끝난 뒤 완료 알림, 원래 500개 완료 알림의 실제 전달입니다. 변경 범위는 scripts/cretop_agent.py, cretop_local.py, cretop_detail_collection.py 및 직접 관련 테스트입니다. 보호 불변조건은 원문 checkpoint·회사별 fsync 저장·재개 위치·8개 화면 품질검사·DB 저장 계약·legacy 원격 collect-batch 알림·개인 Chrome·계정·회사 데이터·DB 구조/역할·운영 웹·SMS·예약 작업입니다.

공식 경로: PC collect → 회사별 checkpoint → 성공 시 기존 중앙 remote-batch-fetch → 품질검사 → 기존 save_result의 커밋 → 텔레그램 완료 알림과 별도 발송 기록. PC collect 오류/중앙 저장 오류에서는 보존된 회사 수와 중단 단계로 중단 알림을 보냅니다. 기존 send_telegram_batch_notification과 legacy 메시지는 재사용합니다. 동일한 성공 발송 기록이 있으면 API를 다시 호출하지 않고, 실패한 발송은 알림만 재시도하는 batch-notify에서 처리합니다. 이미 완료된 mortgage 묶음은 batch-notify에 동결 payload를 주고 읽기 전용 DB 조회로 대상·상태·8개 화면을 확인해 알립니다. 새 브라우저 runner·HTTP sender·감시 스케줄은 만들지 않습니다.

최소 구현 게이트: 발송과 메시지는 2단계 기존 함수에서 멈춤. 별도 발송 기록은 3단계 표준 json/pathlib/os로 멈춤. 검색한 기존 JsonResult.write_atomic은 AgentPaths의 고정 outbox 경로와 여러 폴더 생성에 묶여 있고 fsync가 없으며, local.write_result는 도메인 수집 모듈의 책임이므로 shared sender에서 역참조하지 않습니다. 필요한 단일 원자적 발송 기록 기능만 추가하며 새로운 의존성은 없습니다.

기준선 검증은 운영 DB·네트워크와 분리된 Python 3.13 앱 이미지에서 기존 검사 236개 통과(운영 DB용 1개 제외)입니다. 같은 검사와 Ruff를 수정 후 다시 실행합니다. 추가 성공조건은 DB 저장 전 완료 미발송, 중단·부분 DB 저장 보고, 품질검사 보류 시 완료 금지, 발송 성공 기록 재사용, 발송 실패 재시도, 비밀값 비노출, 알림 전용 명령의 DB 쓰기 금지입니다. PC 실행본 hash와 중앙 CLI의 실제 API 성공 응답 및 message_id를 확인합니다. 봇 설정 파일은 필요한 2개 키만 전용 비공개 경로로 전달하고 제품 .env는 바꾸지 않습니다. 중앙 운영 웹 이미지는 배포하지 않고 공식 단발 CLI에서 검증된 저장소를 읽기 전용으로 사용합니다.

### 알림 변경 코드 리뷰 계약

1. 원천: 이번 알림 수정 승인·기존 봇 파일 지정·프로젝트 지침·변경 전 수집/DB/legacy 발송 계약.
2. 상위 목적: 사실 수집과 중앙 저장의 종료 상태를 기존 수신 대상에 전달; 회사 사실의 생성·판단은 기존 계층 유지.
3. 경계: base 062b42b 대비 3개 스크립트와 직접 테스트 diff, collect CLI, fetch/notify CLI, sender/receipt 직접 소비자.
4. 입력: 검증된 로컬 결과, 동결 payload, 기존 Telegram 키 2개; 비밀값은 출력·발송 기록에 넣지 않음.
5. 절차: checkpoint 또는 DB 커밋 → 종료 상태 확정 → 발송 → 성공/실패 기록; 성공 기록 재사용, 오류 시 기존 예외/보존 상태 유지.
6. 출력: 기존 수집/DB summary 형식 유지, notification 결과 추가; API 승인과 message_id 기록; DB 저장 성공과 발송 실패 구분.
7. 보호: 위 보호 불변조건 및 기존 검사 기대값 유지.
8. 비목표: 브라우저·회사 데이터·DB 구조·제품 배포·SMS·예약 작업 변경, 다른 봇/수신 대상 선택, 500개 재조회.
9. 근거: 기존 236개 검사, 새 알림 계약 검사, Ruff, 실제 실행본 hash, 읽기 전용 500개 DB 확인, Telegram API 결과와 발송 기록.

리뷰 관점은 변경 diff의 완료/중단 판정·발송 기록·예외, 직접 영향 범위의 checkpoint와 fetch summary·legacy sender·CLI 결과입니다. 상위 구조 개선이나 가상 미래 확장은 finding 범위가 아닙니다.

## 2026-09-19 텔레그램 적용·검증과 재개 정보

기존 설정 파일은 주인님이 지정한 Desktop/.env이며 원본은 수정하지 않았습니다. 필요한 TELEGRAM_BOT_TOKEN·TELEGRAM_CHAT_ID 두 값만 PC C:\cretop-agent\.telegram.env(사용자·SYSTEM·관리자만 허용, 상속 차단)와 main evidence 루트 /srv/consolidation/data/cretop/detail_collection/.telegram.env(0600)에 공급했습니다. 인증·제품 .env·Compose 정의·예약 작업은 변경하지 않았습니다.

코드 base 062b42b → da34127, main ceoloan/main에 push했습니다. PC의 cretop_agent.py와 cretop_local.py 실행본을 같은 source hash로 교체했고 이전 두 파일은 .pre-telegram-20260919로 보존했습니다. 이미 끝난 350개의 공식 collect CLI를 적용 후 실행했을 때 1.17초·종료값0으로 checkpoint를 재사용했으며, 보호 파일7개 hash와 전면 창이 유지됐습니다. 회사 재조회·파일 덮어쓰기·추가 완료 알림은 없었습니다.

기존 검사236개와 알림 계약 추가18개, 총254개 통과(운영 DB용 기존1개 제외), Ruff와 git diff --check 통과. 코드 리뷰 첫 라운드에서 비정상 checkpoint의 .get 호출이 원래 오류를 가릴 수 있는 결함과 fetch/읽기 전용 재알림의 파일 건수 표현 차이로 완료 알림이 중복될 수 있는 결함을 확인·수정했습니다. 해당 입력을 검사에 추가했고 마지막 전체 diff 리뷰에는 승인 finding·열린 계약 질문이 없습니다. 기존 legacy 원격 알림·checkpoint·품질검사·fetch 순서 검사도 유지됐습니다.

실제 단발 CLI는 앱 Python 이미지와 기존 Compose jobs 환경을 사용하되, 저장소 전체를 /workspace/ceoloan에 읽기 전용 bind하고 --workdir를 동일하게 둡니다. /app을 덮으면 기존 운영용 media 볼륨 마운트 지점이 없어 시작되지 않았고, source에 evidence 디렉터리도 없었으므로 저장소의 gitignored docs/cretop/detail_collection 빈 마운트 지점을 만들었습니다. 두 실패는 컨테이너 시작 전이었고 Telegram API 발송은 없었습니다. 최종 경로는 /workspace/ceoloan/docs/cretop/detail_collection에 기존 evidence 루트를 별도 bind합니다. 운영 웹 이미지는 그대로이며, CLI는 전체 검증된 source를 읽으므로 알림 변경이 실제 적용됩니다. SQL 자료도 같은 source의 docs/cretop/schema에서 읽습니다.

중앙 저장 시 사용 경로는 다음과 같습니다. 먼저 위 빈 마운트 지점이 있는지 확인합니다. 같은 이미지·검증 source hash를 사용하며 old Windows로 접속하지 않고 PC가 넘긴 local_uia 결과를 재사용합니다.

```bash
sudo -n docker compose \
  -f /srv/consolidation/infra/compose.production.ceoloan.json \
  -f /srv/consolidation/infra/compose.activate.ceoloan.json \
  -f /srv/consolidation/infra/compose.jobs.ceoloan.json \
  run --rm --no-deps -T --entrypoint python --workdir /workspace/ceoloan \
  -e CRETOP_LOCAL_DB_HOST=postgres -e CRETOP_LOCAL_DB_PORT=5432 \
  -v /home/chaconne/projects/ceoloan:/workspace/ceoloan:ro \
  -v /srv/consolidation/data/cretop/detail_collection:/workspace/ceoloan/docs/cretop/detail_collection \
  web -m scripts.cretop_detail_collection remote-batch-fetch --run-id <run-id>
```

완료 파일에는 회사별 저장을 먼저 확정하고 중앙 fetch가 DB 저장 후 자동으로 알림을 보냅니다. 수집 CLI는 성공 때 알림을 미리 보내지 않으며, 중단 때 원문과 별도 telegram_stopped 기록을 보존합니다. 중앙 fetch의 예외는 기존 예외를 그대로 유지하면서 이전 커밋 수를 중단 알림으로 보냅니다. 발송 실패는 DB 성공을 되돌리지 않고 notification.sent=false와 error_type으로 기록합니다. 알림 재시도는 위 동일 작업 환경에서 command만 batch-notify로 바꿉니다. --payload-file 없이 기존 fetch_summary를 사용하면 DB를 다시 저장하지 않습니다. 완료 mortgage 묶음은 --payload-file <동결 payload>를 주면 읽기 전용 DB로 대상·사업자번호·상태·8개 화면·중복을 확인합니다. 성공 발송 기록을 재사용하는 동작은 확인됐으며, Telegram 승인 직후 기록 저장 전에 프로세스가 강제 종료되는 구간까지 exactly-once를 보장하지는 않습니다.

원래500개 대상은 기존 part001/002/003과 재개350 payload를 연결해 원래 baseline.selected_business_numbers 500개와 순서까지 일치함을 확인했습니다. 알림용 동결 payload SHA256 638c92aae67409729a9ba3c6a492d6e4bd49d4fc389803edd292063b2b8b09a1, 파일명 20260917_mortgage_detail_500_140241_notification_payload.json입니다. 공식 batch-notify에서 company_main을 read-only로 조회했고 저장500·present265·absent235·본문2120·중복0을 재확인했습니다. 회사 사실·DB 구조의 쓰기는 없었습니다.

2026-09-19 01:24:03 KST 텔레그램 API가 sent=true·message_id=65로 완료 알림을 승인했습니다. 같은 공식 명령을 다시 실행했을 때 read-only 확인 후 reused=true·동일 message_id=65를 반환했고 추가 API 호출은 없었습니다. main의 원래500 run 디렉터리에서 telegram_completed.json을 보존하며, PC에도 C:\cretop-local\outbox\20260917_mortgage_detail_500_140241_telegram_completed.json으로 회수했습니다. 기존500 background_status index에 별도 Telegram 결과를 연결했고 이전 index는 background_status_before_telegram_20260919.json으로 보존했습니다. API 발송 승인까지 확인했으며 실제 사용자 기기의 표시·열람은 확인 대상이 아닙니다.

현재 요청의 남은 변경·배치 실행·감시 작업은 없습니다. 새 수집은 다음 대상 범위를 승인받아 동결하고 기존 hidden browser/collect → 위 중앙 fetch 경로를 사용합니다. 알림 설정만 바뀐다면 주인님이 지정한 원본에서 두 실행 위치를 동기화하고 값을 로그·문서·Git에 쓰지 않습니다.
