# 이력서 번역 요청 오류 — 2026-09-17

## 현재 결과

두 원문에서 운영과 같은 `400 INVALID_ARGUMENT`를 재현했고, 이력서 경력 항목 수에 따라 번역 응답 형식의 조건이 늘어나는 문제를 수정했다. 원문·모델·번역 지시를 유지한 대조와 수정본의 실제 전체 AI 추출, 격리된 테스트 DB의 공식 저장 경로를 확인했다.

- 프로그램 커밋: `d65f6bd17a377f5bb3df06b170e21f11241ad58a`, 부모 `de20cf82c962a3acc140e669a67cd350886e9eb2`.
- 원격 debug: `/home/chaconne/exdigm-debug`, clean detached HEAD에 위 커밋 보관.
- 확인 시 운영 clean main·실제 앱·GitHub main은 `de20cf82`다. 이 수정의 push·운영 배포는 실행하지 않았다.
- 두 운영 FileData와 보관 원문 전체는 시작 상태와 동일하며, 실패 3회·종료 큐·Resume 0개를 유지한다. 수동 재처리도 실행하지 않았다.

## 대상과 읽기 전용 기준선

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

## 비공개 증거와 재개

서버 `/home/chaconne/exdigm-debug/.debug/provider-failures-20260917/`는 0700, 원문·응답·검사 파일은 0600이다. 원본 스냅샷, 단계별 request/response/failure, schema 단일 인자 대조, 실제 전체 결과, 정상 대조 전후, `test_actual_provider_resume_save.py`, `production-unchanged-after.json`, `code-review.md`를 보관한다. 비공개 임시 fixture는 명령에서 명시할 때만 적용하며 앱 변경에 포함하지 않았다.

1. 이 문서와 GBrain `incident/exdigm-resume-translation-schema-provider-errors-20260917`을 읽고 실제 debug/운영/origin Git·배포 서비스·보호 기준을 다시 확인한다.
2. 배포 요청을 받으면 debug `d65f6bd1`의 검증된 두 파일을 보존한다. 다른 작업의 dirty나 미배포 detached 커밋을 초기화하지 않고 공식 `scripts/deploy/deploy.sh prod`를 사용한다.
3. 운영 actual source commit·HTTPS·Swarm·작업자 상태를 확인한다. 배포만으로 실패 큐는 다시 열리지 않는다.
4. 두 파일의 재처리가 승인되면 정확한 두 FileData·기존 후보자·연결 원문을 복구 가능한 형태로 백업하고 검토한 공식 큐 재개 절차만 적용한다. 범위를 다른 실패 파일로 넓히지 않는다. 첫 파일은 새 후보자 생성 여부, 둘째 파일은 기존 후보자의 연락처·원본 연결·새 Resume·현재 포인터를 확인한다.
5. 운영 실제 저장 결과를 확인한 후에만 오류 처리 완료와 운영 재발 차단 여부를 갱신한다. 현재 판정은 수정본 검증 범위에서 해당 번역 400 경로 차단, 운영 활성화·지정 데이터 복구는 미실행이다.
