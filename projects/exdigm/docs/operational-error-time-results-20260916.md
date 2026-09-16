# 오류 기록의 한국 시간·처리 결과 기록

작성일: 2026-09-16 · 상태: 합동 검증·커밋·push·운영 반영 완료. 아래 과거 대기 기록은 당시 이력이다.

## 최종 적용과 재개 기준 — 2026-09-16

- 주인님이 다른 Exdigm 변경과 합동 배포하고 검증된 테스트 준비본을 보호 기준으로 등록하도록 승인했다. 기존 검사·기대값·보호 목록 18개를 유지했고 이전 pin/ref도 보존했다.
- 수정 커밋 `6dd406439be5a52d5ce1f1660ebd05ca621df715`를 23:36:07 KST에 배포했다. 이후 명단/Hermes 통합 최종 커밋 `de20cf82c962a3acc140e669a67cd350886e9eb2`를 23:52:04 KST에 배포했으며 같은 동작을 유지한다.
- 누락된 테스트 준비 데이터는 기존 migration의 submit_to_client 정의 한 행을 재사용해 준비했다. 기존에 제외됐던 권한 검사까지 포함한 관련 71개를 두 번 통과했고, 최종 통합 733개와 보호 216개가 통과했다.
- 운영 migration 0069 적용, 조회 전용 Django 연결과 새 직접 DB 연결 모두 Asia/Seoul, 실제 반환 시각 +09:00을 확인했다. 원래 오류 49건의 이전 필드 해시를 보존했고 모두 처리 기록 없음/빈 이력을 유지한다. 배포를 개별 오류 해결 성공으로 소급 기록하지 않았다.
- 관리 명령의 실제 쓰기는 격리 테스트 DB에서 검증했고 운영에서는 임의의 처리 이력을 만들지 않았다. 실제 조치와 결과가 확인되면 기존 공식 명령으로 이력을 추가한다.
- 합동 배포·서비스·개인 데이터 보존의 정본은 [최종 통합 기록](auto-posting-other-sites-20260916.md)이다. 이후 재개에서는 과거 차단 기록을 현재 미완료 상태로 해석하지 않는다.

## 목표와 승인 원천

- 주인님의 지시: 시간을 모두 Asia/Seoul로 변경하고 기록 시간도 한국 시간으로 사용한다.
- 주인님의 지시: 오류 처리 결과를 DB에 기록한다.
- 처리 항목 확정: 처리 상태·조치 내용·성공/실패·처리 시각.
- 구현·격리 검증·직접 코드 리뷰·문서화·이번 변경의 커밋을 진행한다. 운영 반영은 검증된 결과를 제시한 뒤 공식 배포 단계에서 진행한다.

## 원하는 동작

- Exdigm의 Django DB 연결 시간대를 Asia/Seoul로 맞춘다. 오류의 occurred_at/created_at/updated_at과 일반 ORM 조회의 시간대 있는 날짜가 +09:00으로 반환된다.
- 공용 오류 감지기의 새 발생 시각과 활성화 시각도 Asia/Seoul로 기록한다. 기존 UTC 표식과 미수집 기록은 시간대 변환으로 읽어 기존 재개 위치를 유지한다.
- 실제 발생 순간과 시각 비교·정렬·기간 조회는 유지한다. PostgreSQL timestamp with time zone의 내부 UTC 저장 구조를 유지하면서 연결과 반환 시간대를 한국 시간으로 통일한다.
- 오류마다 processing_status(처리 기록 없음/처리 중/성공/실패)와 processing_history를 둔다. 기존에 실제로 복구된 오류도 있을 수 있으므로 이력이 없는 상태를 미복구라고 단정하지 않는다.
- 처리 이력 한 항목은 상태, 조치 내용, 성공/실패, 실제 처리 시각, 이력을 DB에 기록한 시각을 담는다. 시각은 모두 +09:00이다.
- 기존 서비스의 공식 기록 함수와 Django 관리 명령 record_operational_error_result로 이력을 추가한다. 같은 오류의 이전 처리 이력과 원래 오류 자료는 보존한다.
- 처리 완료를 추측해 자동으로 성공 표시하지 않는다. 실제 조치·확인 결과를 기록하는 호출자가 상태와 조치 내용을 전달한다.
- 대표/관리자는 기존 orm_read로 상태·이력을 조회한다. 일반 직원의 전역 오류 읽기 권한과 ORM 쓰기 금지는 유지한다.

## 변경 범위와 최소 구현

- main/settings/base.py: 이미 설정된 TIME_ZONE을 Django DATABASES.default.TIME_ZONE에도 적용한다. 플랫폼 기본 기능으로 기존 DB 및 JSON 응답의 날짜를 맞추며 별도 renderer를 만들지 않는다.
- common/operational_errors.py: Python 표준 ZoneInfo로 같은 발생 순간을 Asia/Seoul로 기록하고 기존 표식도 동일 시간대로 읽는다.
- projects/models.py, 신규 projects/migrations/0069_operationalerror_processing.py: 기존 OperationalError에 현재 처리 상태와 추가형 JSON 이력 두 필드만 추가한다. DB 소유자가 현재 연결 DB의 기본 시간대를 Asia/Seoul로 설정해 새 직접 DB 접속에도 적용한다. 운영/개발/테스트 DB 소유자와 기존 timezone 기본값 부재를 SELECT로 확인했다. 역방향 마이그레이션은 원래의 기본값 부재로 복구한다.
- projects/services/operational_errors.py: 기존 안전한 오류 문구 처리와 모델을 재사용해 잠금·트랜잭션 안에서 처리 이력과 현재 상태를 함께 갱신한다.
- projects/management/commands/record_operational_error_result.py: UUID, 상태, 조치 내용, 선택적인 시간대 포함 처리 시각을 받아 공식 서비스에 연결한다. 필수 정보가 없거나 부정확하면 쓰기를 실패시킨다.
- tests/test_operational_error_records.py, tests/test_operational_alerts.py, tests/test_hermes_orm_read.py: 시간대·상태/이력·일반 알림과 권한 보존을 검증한다. UTC 문자열을 기대했던 한 검사는 승인된 한국 시간 출력 조건으로만 바꾼다. 기존 수집기의 시간 문자열 기반 번호는 PostgreSQL 기본 timezone 함수로 원래 번호 표현을 고정해 한국 시간 전환 시 과거 오류와 처리 결과가 중복되지 않게 한다.
- 공용 코드 카탈로그와 오류 기록 읽기 안내를 갱신한다.
- 최소 구현 게이트: 기존 수집·조회·JSON 저장·문구 보호는 2단계, DB 시간대·모델·관리 명령은 4단계, 시간대 변환은 표준 ZoneInfo를 쓰는 3단계에서 멈춘다.
- 검색 근거: TIME_ZONE/USE_TZ, OperationalError, processing_history/processing_status/record_operational_error_result, class .*Result|Processing|Resolution. 현재 전용 처리 결과 구현은 없으며 기존 context는 원래 오류 문맥이어서 그 내용은 보존한다.

## 작업 시작 상태와 보호 조건

- 운영: clean main, 87683dae905f56676bb6f0d4b9916c2d86bcfb0d.
- 개발: 같은 commit의 detached HEAD. 다른 작업의 tests/conftest.py, workflow worker/enqueue 검사, businesspeople 사이트 수정이 진행 중이다. 이 파일은 이번에 편집하거나 stage하지 않는다.
- 조정실 controlroom: 다른 작업이 docs/README.md와 자동게시 계획을 수정 중이다. 해당 내용을 보존한다.
- 기존 오류 id·발생 순간·created_at·원문·호출 경로·문맥, 수집 재개 위치, 중복 감지, 일반 알림, 업무 데이터, 비밀값 보호, 기존 권한을 유지한다.
- DB 인프라·Hermes fleet·운영 데이터 수동 보정·메일/Telegram 발송·새 예약 작업은 이 변경에서 실행하지 않는다.

## 실제 확인과 검증

- 읽기 전용 운영 연결: exdigm_debug_ro, transaction_read_only on, 기존 TimeZone UTC, timestamp with time zone 필드.
- 같은 읽기 전용 계정의 임시 표준 Django 연결에 TIME_ZONE Asia/Seoul을 지정하면 발생/기록 시각 모두 +09:00이며 기존 UTC 값과 동등한 순간임을 확인했다.
- 수정 전후 같은 공식 세 파일을 검사했다. 수정 전 58 passed/1 setup error, 수정 후 추가 검사 포함 68 passed/같은 1 setup error였다. 기존 누락 사례의 정확한 이름은 test_orm_read_scopes_a_four_relation_submission_draft_path다.
- 최종 관련 검사: HERMES_INTEGRATION_ENABLED=true scripts/debug_workspace.sh test tests/test_operational_error_records.py tests/test_operational_alerts.py tests/test_hermes_orm_read.py -k 'not test_orm_read_scopes_a_four_relation_submission_draft_path' --tb=short. 2026-09-16 21:01 KST에 70 passed/1 deselected를 확인했다. 이 1개 검사와 fixture는 변경하지 않았다.
- 기존 submit_to_client fixture 준비 오류는 과거 별도 문제로 분리하고 그 검사·기대값을 수정하지 않는다.
- 추가 검증: 새 오류와 기존 UTC 표식·미수집 오류, 자정 경계와 기간 필터, 현재 상태와 실패→재처리→성공 이력, 원문/created_at 보존, 잘못된 상태·빈 조치·시간대 없는 시각·없는 오류 번호의 쓰기 실패, 비밀값 가림, 공식 관리 명령 실제 개발 DB 쓰기와 공용 ORM 관리자 조회/직원 차단, Notification/NotificationDispatch 0건.
- Django check, migration drift, Ruff, diff check, catalog_update, 주 에이전트의 code-review-loop를 수행한다.

## 재개 정보

- 현재 코드: 원격 debug detached HEAD 87683dae905f56676bb6f0d4b9916c2d86bcfb0d 위의 이번 10개 경로만 수정·신규 작성했다. 커밋·push·운영 배포는 아직 없다. 운영 checkout은 기존 clean main이다.
- 통과: 관련 검사 70개, PostgreSQL 직접 새 연결의 Asia/Seoul 기본값, 오류 발생/기록 시각의 동일 순간 유지·자정 경계, 실패→성공 이력과 원문 보존, 실제 Django 관리 명령의 테스트 DB 기록, 관리자 ORM 조회/직원 차단, 메시지 요청 0건, Django check, migration drift 없음, 해당 파일 Ruff/diff check, catalog current/valid true/깨진 참조 없음.
- 차단: /etc/exdigm/verification-check /home/chaconne/exdigm-debug가 Protected contract changed; stop and obtain explicit contract approval: tests/conftest.py로 종료했다. 이 21줄 수정은 시작 때부터 존재했고 이번 작업에서 편집·stage하지 않았다.
- 다른 작업의 승인 근거: auto-posting-other-sites-20260916.md 3~5/23~28에 공통 테스트 정리와 conftest의 Django flush 보완 승인이 기록돼 있다. 그 작업의 검증·커밋·승인된 보호 기준 정리가 아직 끝나지 않았다. 여기서 해당 변경을 되돌리거나 보호 기준을 임의 갱신하지 않는다.
- 다음 행동: 해당 테스트 정리가 완료된 실제 Git/보호 기준 상태를 확인 → 공용 보호 검사와 관련 검사 → 최종 diff 재검토 → 이번 범위의 검증된 커밋. 운영 배포 단계에서는 다른 미완료 변경을 함께 배포하지 않도록 전체 Git 상태를 확인한다.
- 운영 반영과 기존 실제 오류의 처리 결과 소급 작성은 미실행이다. 실제 오류를 처리한 호출자가 확인한 조치와 결과를 공식 명령으로 기록한다.
- 복구 보관: 원격 .debug/operational-error-time-results-baseline-20260916-204901에 수정 전 7개 파일, .debug/operational-error-time-results-review-20260916-210348에 최신 10개 파일·checksums.json·tracked.patch를 보관했다. patch SHA-256은 660ec919ef0fe026802897d40fea463c2b16a89c34c2b0a626b9c0ef21b126bb다. 신규 관리 명령과 migration은 최신 파일 사본에 포함된다. 현재 active 코드에 이미 적용된 수정이므로 patch를 다시 적용하지 않는다.
- GBrain: default:project/exdigm-operational-error-alerts에 한국 시간·처리 이력 계약과 개발/미배포 경계·보호 검사 차단을 기록하고 재조회로 새 절과 기존 배포 증거 보존을 확인했다.

## 공식 처리 결과 기록과 조회

- 오류 id는 기존 장부에서 조회한 실제 번호를 사용한다. 운영 DB 쓰기는 해당 오류 처리 작업의 승인 범위를 따른다. 아래는 관리 명령의 형식이며 운영 실행을 뜻하지 않는다.
- 명령: python manage.py record_operational_error_result <오류-UUID> --status succeeded --action '실제 조치와 원래 실패 경로의 검증 결과' --processed-at '시간대가 포함된 실제 처리 시각'. 상태는 in_progress/succeeded/failed다.
- processed-at을 생략하면 기록 호출 시각을 쓴다. 과거 조치라면 실제 시각을 전달한다. 시간대가 없는 시각·빈 조치·허용되지 않은 상태·없는 오류 번호는 쓰기를 실패시킨다.
- 각 이력: status, action, result(success/failure/null), processed_at, recorded_at. 두 시각 모두 +09:00이며 기록 시각은 행 잠금 획득 뒤 샘플링한다. 원래 오류 created_at은 갱신하지 않는다.
- 기존 관리자 ORM 읽기: model projects.OperationalError, action read, fields에 id/created_at/occurred_at/processing_status/processing_history를 선택한다. processing_status로 미기록·처리 중·성공·실패를 필터링할 수 있다. 이 API에 쓰기를 추가하지 않았다.

## 코드 리뷰 계약과 결과

1. 원천: 주인님의 두 지시·처리 항목 답변·이 계획·기존 DB 전용 기록 계약.
2. 역할: 실제 오류와 확인된 조치 결과를 한 장부에 남기며 일반 알림을 보존한다.
3. 경계: 시작 commit 87683dae와 이번 10개 경로의 diff, 직접 수집기·관리 명령·공용 ORM·기본 JSON 반환.
4. 입력: 시간대 있는 실제 오류/처리 시각, 기존 오류 UUID, 허용 상태, 1~8000자 조치, 기존 대표/관리자 읽기 권한.
5. 절차: 기존 감지/수집 → 기존 번호의 오류 저장 → 트랜잭션/행 잠금 안의 결과 추가·현재 상태 갱신 → 기존 읽기. 마이그레이션은 현재 연결 DB의 기본 시간대만 변경한다.
6. 출력: 동일 순간의 +09:00 시각, 기존 오류 번호, 이전 이력을 보존한 조치 결과, 일반 직원 조회 차단, 추가 배달 요청 없음.
7. 보호: 시작 파일 상태·원래 오류 자료·created_at·재개 위치·중복 감지·일반 알림·비밀값·기존 검사.
8. 비목표: 운영 데이터 임의 복구·이력 소급 생성·새 감시/배달/ORM 쓰기·다른 작업의 보호 파일·보호 기준 변경.
9. 증거: 공식 격리 검사와 직접 SQL/명령/ORM 검사, 현재 코드·시작 diff·최소 구현 검색, 아래 재현/수정 대조.

- code-review-loop/code-review를 주 에이전트가 직접 수행했고 별도 에이전트는 사용하지 않았다. 변경 diff와 직접 영향 범위 두 관점을 확인했다.
- 승인 finding 1개: DB 연결 시간대 변경 → timestamptz를 문자열로 cast하는 기존 번호 계산의 표현 변경 → 기존 영수증 미일치 → 같은 오류가 새 번호로 중복 생성된다. 새 실제 수집 회귀 검사에서 UTC로 기록한 처리 완료 오류가 Seoul 전환 뒤 다시 1건 생성됨을 확인했다.
- 수정: 같은 SQL 번호 생성에서 PostgreSQL timezone 함수로 기존 표현을 고정했다. 동일 검사는 수정 후 새 기록 0건/기존 처리 결과 유지로 통과했다. 표시·저장 시각은 계속 한국 시간이다.
- 최신 전체 diff를 같은 계약으로 다시 읽은 최종 패스에 승인된 finding/열린 제품 계약 질문은 없다. 공용 보호 검사 차단이 남아 있어 작업 전체와 리뷰 루프의 완료·커밋·배포는 보류한다.
