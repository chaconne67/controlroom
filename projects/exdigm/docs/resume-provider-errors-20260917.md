# 이력서 번역 요청 오류 — 2026-09-17

## 현재 결과

두 원문에서 운영과 같은 `400 INVALID_ARGUMENT`를 재현했고, 경력 항목 수에 따라 번역 응답 형식의 조건이 늘어나는 문제를 수정했다. 주인님의 명시적 “수정, 운영배포 후 2개 파일 재 처리해” 승인 후 공식 운영 배포와 지정 두 원본의 실제 AI 재추출·운영 DB 저장까지 완료했다. 기존 후보자 연결, 원문·배치 메타데이터·폴더·파일 크기·수동 필드 보존을 공식 읽기 전용 조회로 확인했다.

- 번역 수정 커밋: `d65f6bd17a377f5bb3df06b170e21f11241ad58a`, 부모 `de20cf82c962a3acc140e669a67cd350886e9eb2`.
- 재처리 전 직접 소비자 검토에서 발견한 원본 정보 전달 보완: `a5aa6b02e210f67e21856412174e8b70c2345b7b`, 부모 `d65f6bd1`.
- 최종 debug는 clean detached HEAD, 운영은 clean main이며 GitHub main·앱/SSE/알림 처리기의 실제 `/app/.source-commit`이 모두 최종 `a5aa6b02`다. 공식 배포 완료는 2026-09-17 13:34:56 KST다.
- 두 지정 파일은 각각 새 Resume 1개가 saved이고 기존 Candidate에 연결됐다. 성공 시 기존 공식 함수가 실패 사유를 해제했고 처리 큐는 `db_saved`로 종료됐다. 초기 실패 상태와 원문은 복구 가능한 비공개 백업에 보관한다.

## 운영 배포·지정 재처리 결과

| FileData | 실제 운영 저장 시각 KST | 기존 후보자 | 새 Resume | 이번 원본 저장 내용·대표 선택 |
|---|---|---|---|---|
| `aadcafd0-0d62-490a-891d-abae08709d35` | 2026-09-17 13:36:30.974132 | `90c65d59-fd5b-4efc-a823-428f33dc916d` — 기존 이메일 일치 | `e46fb0a0-7505-4363-b595-e6c8f192a4c1` — saved | 경력 6·학력 3, 이 원본이 현재 대표 |
| `f371c4d3-4552-401b-9399-71e42e34b65f` | 2026-09-17 13:37:50.355120 | `2e9e684c-28af-4846-9796-4c9feface8df` — 기존 명시 연결 유지 | `532988e7-5f37-4f03-9be7-9afe6107aab8` — saved | 경력 7·학력 1, 기존 대표 `ebaa03ee-b1ed-4aa0-b9fe-858a626d1fe5` 유지 |

DOCX의 추출 기준일과 현재 대표의 기준일은 모두 2026-09-17이다. 공식 날짜·원본 등록 순서 비교의 마지막 값은 이번 원본 1789608546.619208, 현재 대표 원본 1789615626.604730으로 현재 대표가 더 나중에 등록됐다. 텍스트 동일에 따른 선택이 아니며 기존 선택 정책으로 이력 저장과 대표 선택을 구분했다. 대표 Resume/FileData/Candidate 연결과 대표 내용에 대응하는 실제 경력·학력 기록을 확인했다.

- 쓰기 전 공식 `shell-readonly`로 원본 두 FileData·대상 후보자 2명·기존 연결 데이터 70행을 Django 정식 serializer로 백업했다. 첫 파일은 이메일 유입이며 이번 FileData에 아직 연결되지 않았던 첫 후보자도 연락처 공식 매칭으로 찾아 포함했다. 백업 SHA-256은 `c716f8f3afa6fc3d7d9d5727968d4d80db678a45d1866a2858d3b56af2e26729`다.
- 재처리 직전 전체 FileData 해시·후보자 serializer 결과가 백업과 일치함을 확인했다. 기존 manifest reader가 정확한 두 입력만 읽도록 비공개 작업 폴더를 준비했다. 원문·normalized text·추출 메타데이터·원래 source channel을 그대로 전달했다.
- 배포된 운영 clean checkout과 생산용 환경에서 `scripts/run_workers.sh drain updater`로 진행 작업 종료를 기다린 다음 기존 `realtime_txt_to_db --source manifest --force --workers 1 --limit 2`를 실행했다. force는 명시적으로 요청된 두 종료 원본을 다시 선택하며 문서 판단·출력 검사·매칭·저장 조건을 완화하지 않는다. 기존 배포 잠금과 공식 추출 실행 잠금을 사용했고 자동 작업자는 완료 뒤 undrain했다.
- 공식 실행 `provider-recovery-20260917-approved-two`: 13:36:02.921776 시작, 13:37:50.442095 종료, status=succeeded, processed=2, failed=0, skipped=0. 새 실제 AI 호출을 사용했으며 앞선 테스트 응답을 재사용하지 않았다.
- 13:38:11 KST 공식 읽기 전용 검증: 두 FileData structured·Resume saved·knowledge 계약/해시/모델·기존 후보자·실패 해제·`db_saved` 큐·수동 필드 보존 통과. 원본 13필드와 전체 보관 artifact가 동일했다. 같은 후보자의 기존 FileData 6개는 대표 여부/수정 시각 외 전체 필드가 같고, 보관 원문 7개와 과거 Resume/knowledge 9개가 그대로다.
- 실제 저장 확인 후에만 `projects.services.operational_errors.record_processing_result`로 두 지정 오류의 처리 결과를 succeeded로 각각 1회 추가했다. 최초 오류·원인·발생 시각을 덮어쓰지 않는다. 다른 종료 파일이나 명단 문서는 재처리하지 않았다.
- PowerShell에서 임시 Bash 실행 본문을 전달할 때 마지막 빈 줄에 CR이 붙어 DB 작업 완료 후 wrapper가 exit 1이었다. 공식 추출 실행은 위와 같이 2건 성공이며 실제 DB 검증도 통과했다. 처리 명령을 반복하지 않고 표준 줄끝 정규화와 Bash 구문 검증으로 실행 본문 전달을 정리했다.

## 원본 정보 전달 보완의 기준선과 검증

재처리 전 검토에서 `runners.save_pipeline_to_db`의 primary_file이 파일 ID/이름/MIME/수정일만 전달하고, `save_pipeline_result`는 누락한 parent_folder_id/folder_path/source_root/size를 빈값·기본값으로 update_or_create하는 기존 결함을 확인했다. 원본 정보 보존이라는 이번 목표의 직접 소비자에 한정해 수정했다.

- 시작 기준선: 운영과 debug clean `d65f6bd1`, 직접 영향 검사 166개 통과, 승인 보호 기준 `6dd406439be5a52d5ce1f1660ebd05ca621df715`/18파일.
- 최소 구현 2단계: 기존 `process_resume._save_candidate`의 inventory 전달 계약과 이미 조회하는 FileData를 재사용한다. `runners.py`의 기존 단일 이력서 분기에 5필드 전달만 추가하고 기존 updater 검사에 원본 정보 기대값을 추가했다. 새 함수·모델·의존성·영구 복구 경로는 만들지 않았다.
- 기존 queue 공식 DB 저장 검사에 email_polling/manual_file_upload 두 유입 경로를 적용해 수정 전 두 건 모두 parent_folder_id가 빈값으로 변하는 오류를 확인했다. 수정 후 두 경로와 기존 검사 전체 167개가 통과했고 기존 기대값을 유지했다.
- 보호 계약 216개·Django check·ruff·diff check 통과. catalog=current/valid, broken_references=[]; 메인 code-review-loop의 승인 finding/열린 질문 없음. 근거는 서버 비공개 `code-review-metadata.md`다.
- 최종 공식 prod 배포는 원본 정보 보완과 앞선 번역 수정이 포함된 하나의 최종 커밋을 fast-forward push/적용했다. 이미지 `exdigm_app:20260917133328`, SHA-256 `e6230995b139fb3418e41b19b2c66cb39b4fd31a74e445c8e8e704b377a2e0fc`. 앱의 두 실제 프로그램 파일 SHA-256이 검증된 debug 파일과 같았다.
- 승인 보호 18파일·pin을 유지했고 새 이미지 DOC/DOCX/PDF 실파일 전달 계약이 통과했다. 앱/SSE/알림 처리기/nginx/DB 서비스 5개 1/1, 작업자·지원 11개 active/drain off, HTTPS 200, 운영 read-write 적용을 확인했다. DB 인프라·Hermes·서버 이전은 수행하지 않았다.
- 이번 두 운영 원본에서 같은 번역 400이 사라지고 실제 후보자/이력서 저장이 완료됐다. 장기간 모든 입력의 재발 부재를 관측했다고 주장하지 않는다.

## 대상과 초기 읽기 전용 기준선

| 발생 시각 KST | FileData | 원본·유입 | 운영 기록 |
|---|---|---|---|
| 2026-09-17 08:49:42.872970 | `aadcafd0-0d62-490a-891d-abae08709d35` | PDF·`email_polling` | 후보자 연결 없음·새 이력서 0개 |
| 2026-09-17 10:32:45.971742 | `f371c4d3-4552-401b-9399-71e42e34b65f` | DOCX·`manual_file_upload` | 기존 후보자 연결 있음·이번 원본의 새 이력서 0개 |

두 건 모두 `provider_call_failed` / `provider_call`, 재시도 횟수 3, `retryable=False`, `needs_resume_processing=False`, `is_processing=False`, `db_saved_at=None`이다. 정확한 제공자 오류는 다음과 같다.

```text
ClientError: 400 INVALID_ARGUMENT. {'error': {'code': 400, 'message': 'Request contains an invalid argument.', 'status': 'INVALID_ARGUMENT'}}
```

운영 조회는 `scripts/debug_workspace.sh shell-readonly -i python`의 `exdigm_debug_ro` / `transaction_read_only=on`으로 수행했다. 연락처·원문·AI 응답은 채팅·Git·GBrain에 넣지 않고 서버 비공개 진단 폴더에 보관했다.

- 첫 FileData 전체 행 SHA-256: `890fc9ae4f16922a4f3606e316fab383c76719faca2a98add97592bbfc01a92a`.
- 둘째 FileData 전체 행 SHA-256: `124dc982ec489493f708be5ff02a277ca2653722fc257710cf9b0b1dd16d1ab6`.
- 작업 종료 시 전체 FileData 값과 ResumeSourceArtifact 배열이 각각 시작 스냅샷과 일치했다. 닫힌 큐와 Resume 수는 그대로다.
- OperationalError: 첫 건 `998b7258-b0df-8317-ceb6-2db33456314f`, 둘째 건 `46006dbb-b700-48fc-ab4a-567055ec3e06`. 조회 시 두 기록은 pending이고 과거 호출 traceback은 비어 있었다. 운영 오류 상태를 resolved로 바꾸지 않았다.

## 원인과 직접 대조

앞서 수정한 명단 제외 처리는 운영 `de20cf82`에 포함돼 있다. 두 원문은 기존의 명확한 개인 이력서 분류를 통과하며 `pass_through_by_default`가 없다. 명단 판정의 추가 AI 호출에서 발생한 오류가 아니다.

저장된 실제 extractor text와 배치 메타데이터를 현재 운영과 같은 코드·설정에 전달했다. 첫 원문 7,754자, 둘째 원문 20,587자다. `extract_resume_knowledge_from_text`의 순수 생성 경로를 공식 읽기 전용 셸에서 실행했고 운영 큐나 후보자는 변경하지 않았다.

실제 흐름은 원문 행 → 언어 판정·국문 원천 구성 → 항목 지도 → 국문 내용 추출 → 항목별 영문 번역 → 신원·출력 검사다. 두 건 모두 경력 항목의 `translate_section`에서 같은 HTTP 400이 발생했다. 언어 판정과 기존 항목 지도·국문 내용 추출은 통과했다.

기존 번역 요청은 모든 문자열 경로를 JSON Schema의 개별 property와 required 목록에 중복 열거한다. 항목이 많은 경력은 입력 내용뿐 아니라 제공자에게 보내는 형식 조건도 함께 늘어난다. [Gemini 공식 문서](https://ai.google.dev/gemini-api/docs/generate-content/structured-output?hl=en)는 큰 스키마의 거절 가능성과 `additionalProperties`에 문자열 형식 조건을 지정할 수 있음을 설명한다. 정확한 허용 항목 수나 바이트 한계는 확정하지 않는다.

| 동일 요청의 대조 | PDF 경력 | DOCX 경력 |
|---|---:|---:|
| 번역 문자열 항목 | 121개 | 112개 |
| 기존 native schema JSON 길이 | 13,132자 | 11,878자 |
| 보관된 같은 prompt·모델·인자의 기존 schema 재호출 | 같은 400, 0.70초 | 같은 400, 0.70초 |
| native schema만 고정 문자열 map으로 변경 | 175자 | 175자 |
| 결과 | 121개 모두 일치·빈값 없음, 9.61초 | 112개 모두 일치·빈값 없음, 13.75초 |

전체 원문에 대한 재현과 한 인자만 바꾼 대조로 입력에 따라 커지는 번역 형식 조건을 원인으로 확인했다. 단순 서비스 장애·정상 이력서의 명단 오인·연락처 누락으로 처리하지 않는다. 운영 과거 3회 각각의 요청은 보관되지 않았으므로 각 시도의 정확한 중간 AI 출력까지 소급 확인했다고 주장하지 않는다.

## 승인 범위·보호 조건·최소 구현

이어진 이력서 추출 수정 요청의 범위에서 코드 수정·검증·리뷰·기록·커밋을 수행한다. 운영 배포 및 종료된 두 행의 재처리는 별도로 명시된 범위에서 진행한다.

- 변경: `projects/services/recommendation_resume_ssp.py:GenerateResumeCtype.translate_section`의 native schema 구성, `tests/test_recommendation_resume_local_worker.py`의 항목 증가 회귀 검사 하나.
- 보호: 원문과 물리 행·PDF/Word 메타데이터·BOM 처리, 문서 유형/명단 제외, 국문 내용과 구조, 날짜·기간·출처 ID, 신원·연락처·후보자 매칭·저장 필수조건, 기존 모델과 호출 경로, 기존 검사 기대값, 승인 보호 파일 18개.
- 시작 상태: debug와 운영 모두 clean, debug detached HEAD와 운영/GitHub main은 `de20cf82`. 다른 작업 파일을 수정하거나 포함하지 않았다.
- 최소 구현 게이트: 2단계에서 멈춤. 실제 `rg`로 기존 `translate_section`, `english_translation_prompt`, `run_llm_json`, 문자열 map 응답과 exact-path 검사, 관련 회귀 검사를 확인하고 재사용했다. 새 모델·프롬프트·전송부·파서·DB 모델·복구 경로·의존성은 추가하지 않는다.
- 형식 조건은 고정 `translations` 객체와 string 값으로 표현한다. 전체 항목 경로와 국문 section은 기존 prompt로 전달한다. 응답의 경로 집합 일치·비어 있지 않은 문자열 검사는 기존 코드 그대로다. 잘못된 응답은 실제 오류를 포함해 한 번 재요청하고 재실패 시 저장 전에 중단한다.
- 번역 내용의 의미 판단은 기존 AI가 맡으며 스크립트가 번역을 추정·보정하거나 누락을 허용하지 않는다. 항목 지도 단계의 native schema는 그대로다.

## 수정 전후 검증

| 확인 | 결과 |
|---|---|
| 기존 직접 영향 검사 | 수정 전 282개, 수정 후 새 검사 포함 283개 통과 |
| 새 증가 회귀 검사 | 1·128·1,024개 전부 지시에 전달·결과에 반영, 형식 조건은 동일. 수정 전 실패·후 통과 |
| 누락·추가 항목·빈값·잘못된 유형·구조/기간 보존 | 기존 기대값 그대로 통과 |
| PDF 원문 수정본 전체 실제 AI 추출·후보자 출력 | 27.54초 성공, 유효한 신원/연락처·경력 6개·학력 3개 |
| DOCX 원문 수정본 전체 실제 AI 추출·후보자 출력 | 76.69초 성공, 유효한 신원/연락처·경력 7개·학력 1개 |
| 기존 정상 PDF 실제 AI 추출 수정 전후 | 21.05초 / 19.37초 성공, 이름·영문명·출생연도·성별·이메일·전화 동일, 경력 3개·학력 2개 유지 |
| 위 두 입력과 정상 대조 전후의 공식 저장 | 별도 테스트 DB의 FileData 원문 → updater → pending knowledge → 실제 후보자 필드 변환 → 저장 4개 통과. Candidate/Resume/current 포인터·경력/학력·원문 보존 확인 |
| 승인 보호 계약 | 216개 통과, `6dd406439be5a52d5ce1f1660ebd05ca621df715` 보호 파일 18개·기준 pin 그대로 |
| Django check·ruff·diff check | 통과 |
| 공식 catalog_update | catalog_changed=false, current·valid, broken_references=[] |
| 메인 에이전트 code-review-loop | 변경 전체와 직접 호출/소비자 검토, 승인 finding 없음·열린 계약 질문 없음 |

실제 AI 추출과 공식 DB 저장 검사는 분리했다. 테스트에서는 외부 인증을 읽지 않고 실제 생성된 D8 결과와 핵심역량 분류 AI 결과만 재사용했다. 필드 변환·필수조건·DB 저장은 실제 코드를 실행했다. 독립된 AI 실행의 전체 JSON이나 핵심역량 문구가 바이트 단위로 같다고 주장하지 않는다.

수정 전 넓게 선택한 추천 이력서 작업자 검사 9개는 재사용 테스트 DB의 `submit_to_pm` 기준 코드 부재로 실패했다. 기존 migration의 동일한 정의를 준비하는 비공개 fixture를 쓰고 수정 전후 같은 조건으로 282/283개를 확인했다. 보호 `tests/conftest.py`나 기대값은 바꾸지 않았다. 세션 fixture의 우선순위 때문에 첫 준비가 적용되지 않아 고유 autouse fixture로 수정했다. `--create-db`는 제한된 debug 역할의 NOCREATEDB로 실행할 수 없어 실패했고 권한을 늘리거나 우회하지 않았다. 기존 두 개발 DB가 남아 있음을 조회로 확인했다.

비공개 저장 검사는 후보자 필드 변환에 포함된 별도 핵심역량 AI 응답 재사용을 처음 누락해 기존 정상 대조까지 `GEMINI_API_KEY not set`으로 실패했다. 실제 이미 생성된 해당 응답을 재사용하도록 진단 코드를 바로잡았고 최종 4개를 통과했다. 운영 키를 테스트에 공급하거나 프로그램 오류를 숨기지 않았다.

## 비공개 증거와 초기 재개 절차

서버 `/home/chaconne/exdigm-debug/.debug/provider-failures-20260917/`는 0700, 원문·응답·검사 파일은 0600이다. 원본 스냅샷, 단계별 request/response/failure, schema 단일 인자 대조, 실제 전체 결과, 정상 대조 전후, `test_actual_provider_resume_save.py`, `production-unchanged-after.json`, `code-review.md`를 보관한다. 비공개 임시 fixture는 명령에서 명시할 때만 적용하며 앱 변경에 포함하지 않았다. 추가 증거는 `production-reprocess-backup/database-rows.json`, `production-reprocess-backup/summary.json`, `production-reprocess-result.json`, `production-reprocess-after-rows.json`, `production-operational-error-results.json`, `production-reprocess.log`, `deploy-final.log`, `code-review-metadata.md`다. 진단 폴더는 debug에만 두고 운영 build context에는 공급하지 않았다.

아래는 초기 검증 후 작성한 승인 대기 재개 절차의 이력이다. 현재는 명시적 추가 승인, 최종 운영 배포, 두 지정 원본 재처리, 실제 저장 검증과 오류 처리 기록까지 완료했다. 현재 재개 시 두 원본을 다시 처리하거나 종료 큐를 임의로 열지 않고 이 문서의 운영 결과와 최신 서버 상태를 대조한다.

1. 이 문서와 GBrain `incident/exdigm-resume-translation-schema-provider-errors-20260917`을 읽고 실제 debug/운영/origin Git·배포 서비스·보호 기준을 다시 확인한다.
2. 배포 요청을 받으면 debug `d65f6bd1`의 검증된 두 파일을 보존한다. 다른 작업의 dirty나 미배포 detached 커밋을 초기화하지 않고 공식 `scripts/deploy/deploy.sh prod`를 사용한다.
3. 운영 actual source commit·HTTPS·Swarm·작업자 상태를 확인한다. 배포만으로 실패 큐는 다시 열리지 않는다.
4. 두 파일의 재처리가 승인되면 정확한 두 FileData·기존 후보자·연결 원문을 복구 가능한 형태로 백업하고 검토한 공식 큐 재개 절차만 적용한다. 범위를 다른 실패 파일로 넓히지 않는다. 첫 파일은 새 후보자 생성 여부, 둘째 파일은 기존 후보자의 연락처·원본 연결·새 Resume·현재 포인터를 확인한다.
5. 운영 실제 저장 결과를 확인한 후에만 오류 처리 완료와 운영 재발 차단 여부를 갱신한다. 현재 판정은 수정본 검증 범위에서 해당 번역 400 경로 차단, 운영 활성화·지정 데이터 복구는 미실행이다.
