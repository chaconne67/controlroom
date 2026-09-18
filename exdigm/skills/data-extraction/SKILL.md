---
name: data-extraction
description: Use when working on Exdigm resume/candidate extraction or the `data_extraction` app.
---

# Data Extraction

exdigm의 이력서·후보자 데이터 추출 파이프라인 판단 규칙. 파일·route·test 탐색은 코드 지도를 먼저 사용하고, 이 스킬은 "어떤 규칙으로 판단할지"에 집중한다.

## Start With Code Knowledge

작업 시작 시 가장 가까운 주제 또는 파일 하나를 선택해 네비게이션 지도를 조회한다.

```bash
uv run --locked python -m tools.code_knowledge code_query --query "데이터 추출"
uv run --locked python -m tools.code_knowledge code_query --query "파일 업로드"
uv run --locked python -m tools.code_knowledge code_query --query "후보자 등록"
uv run --locked python -m tools.code_knowledge code_query --query "이력서 최신 버전"
uv run --locked python -m tools.code_knowledge code_query --query "data_extraction/services/save.py"
```

종료 코드 `3`이면 표현을 구체화한다. 종료 코드 `4`이면 등록된 힌트가 없는 것이므로 `rg`로 현재 코드를 탐색한다. 새 command, route, upload path, 저장 규칙, 테스트가 업무 routing·불변조건·대표 경로를 바꾸면 근거와 함께 관련 canonical GBrain page를 갱신한다.

## Core Objective

최종 완료 기준은 산출물 파일이 아니라 운영 DB의 `FileData`, `Resume`, `Candidate`에 원천 파일 상태, 추출 텍스트, 완성 구조화 JSON, 후보자 연결, 검색 분류축, 실패 사유가 남는 것이다.

기준 처리 순서는 항상 같다.

```text
Drive 파일 확인
→ 처리 대상 판정
→ 다운로드와 텍스트 추출
→ LLM 대상 판정
→ 구조화 JSON 추출
→ 검색 분류축 보강
→ DB 저장
```

## 사례 과최적화 금지 하드 게이트

추출 코드·프롬프트·규칙을 수정하기 전에 다음 잠금을 작성한다.

1. **일반화 근거**: 단일 사례의 값·표현·배치가 아니라 반복 가능한 구조·계약을 수정함을 입증한다.
2. **회귀 대조**: 실패 사례와 원인이 다른 기존 통과 사례를 실제 운영 처리 경로로 수정 전후 대조한다.
3. **판정**: 1과 2를 입증하지 못하거나 수정 대상이 아닌 출력 변화가 검증되지 않으면 수정하지 않는다.

## Execution Boundary

- 웹 요청은 현재 배포된 `Exdigm_exdigm_app` 서비스가 처리한다.
- 중앙 에이전트는 SSH로 `/home/chaconne/exdigm-debug`를 수정·검증한다. `/home/chaconne/exdigm`은 배포와 운영 작업자의 clean 실행 원본이다.
- 운영 DB 진단은 `scripts/debug_workspace.sh shell-readonly`, 저장 검증은 `scripts/debug_workspace.sh test`의 개발 전용 테스트 DB를 사용한다.
- 대량 저장·백필·repair는 운영 데이터 변경이다. 주인님의 명시적 승인 후 운영 체크아웃의 검증된 커밋에서만 실행한다.
- 원격 worker는 대량 파일 산출물 생성기다. 운영 DB 읽기·쓰기·후보자 매칭·현재 프로필 갱신은 활성 운영 서버 책임이다.
- Gemini Batch는 외부 비동기 LLM 작업이지 원격 worker 처리가 아니다.

## DB Source Of Truth

- `FileData`는 Drive 원천 파일 단위 장부다.
- `Resume`은 후보자 1명분 구조화 이력서 단위다.
- `Candidate`는 사람 단위 현재 프로필이다.
- `FileData.extracted_text`, `Resume.structured_json`, `Candidate.current_resume`, `Candidate.current_file_status`가 운영 판단 기준이다.
- 파일시스템의 text, JSON, manifest, batch result는 캐시·작업 산출물·디버깅 자료다.
- 단일 이력서는 `FileData 1개 -> Resume 1개`, 복수 후보자 문서는 `FileData 1개 -> Resume 여러 개`가 된다.

## Save Decision Rules

저장 판정의 단일 기준은 `data_extraction/services/data_decision_policy.py`다. 모든 저장·큐·알림 경로는 이 판정을 재사용해야 한다.

정상 자동 저장 조건:

- 이름이 있다.
- 검증 가능한 이메일 또는 전화번호가 있다.
- 내용 있는 경력 1개 이상이 있다.

학력은 이력서 생성·접수·후보자 DB 저장의 필수조건이 아니다. 원문에 없으면 빈 배열로 보존하고, 저장된 후보자에는 기존 검토 사항에서 `중요 — 학력 정보 없음`을 표시한다. 현재 DB 학력 정보를 보완하면 누락 표시를 해제한다. 학력을 추정해 만들거나 학력 누락을 위조·위험 판정으로 바꾸지 않는다.

연락처만 없으면 후보자를 만들지 않고 `needs_resume_processing=False`/`missing_contact`로 닫는다. Mailplug 유입이면 직원에게 1회 알림을 보내고, 수정된 파일은 새 Drive/웹 업로드로 다시 유입되어야 한다.

이름 또는 경력이 없거나 여러 필수 정보가 없으면 후보자를 만들지 않고 `needs_resume_processing=False`와 구체적인 `resume_processing_reason`으로 닫는다. 학력과 연락처가 함께 없는 경우는 연락처 누락 정책을 따른다.

커리어 태그와 검색 분류축은 DB 저장 전 완성 JSON에 포함되어야 한다. 후보자 저장 뒤에 별도 장식처럼 붙이면 안 된다.

## Candidate Identity Rules

- 기존 후보자 자동 매칭은 검증 가능한 이메일 또는 전화번호로만 한다.
- 이름만으로 후보자를 병합하지 않는다.
- 마스킹 이메일, 도메인만 있는 이메일, 짧은 번호, placeholder 번호는 매칭 키와 대표 연락처로 쓰지 않는다.
- 수동 업로드, Mailplug/이메일 유입, Drive 변경분 유입은 같은 매칭 규칙을 따라야 한다.
- 현재 프로필 갱신 기준은 `resume_reference_date` → Drive `modified_time` → `Resume.created_at` 순서다.
- 새 Resume이 현재 기준보다 같거나 최신이면 `Candidate.raw_extracted_json`, 기본 필드, 검색 관계, `current_resume`, `current_file_status`를 같은 transaction에서 갱신한다.
- 현재 프로필을 갱신할 때 `Candidate.name`도 새 이력서 추출 이름으로 바뀔 수 있다.
- 더 오래된 Resume이면 `Resume.structured_json`만 저장하고 후보자 현재 프로필은 유지한다.

## Drive Rules

- Drive 폴더 표시명은 `01 DB`, DB/API 라벨은 `01_DB`다.
- `01 DB` root ID는 `0B5RUmpuy60_MNl8wMkF6MF9oMWs`다.
- `DB` root ID는 `1k_VtpvJo8P8ynGTvVWS8DtYtK4gZDF_Y`다.
- `AI_HH` 공유문서함 루트 ID는 `1gPMDc7DZf_sirUx2QYzxRUAekLU0R7hy`다.
- Drive 읽기·목록·다운로드·변경분 싱크 기본 인증은 서비스 계정 `synco-drive-reader@elite-wonder-486114-v4.iam.gserviceaccount.com`이다.
- Drive 업로드 인증은 개인 OAuth다. 기본 토큰 경로는 `.secrets/google_token.json`, client secret은 `.secrets/client_secret.json`이다.
- Mailplug, 수동 이력서 업로드, application 직접 업로드의 운영 유입 폴더는 `01 DB/Unsorted/04`다.
- 코드 기준 단일 업로드 target은 `DriveUploadTarget.RESUME_INTAKE`, folder ID는 `1EUPtQOW4rVRtJ5zlZpCmGe96cZOVFpk_`다.
- 업로드는 `DriveGateway.upload_file_to_target(..., target=DriveUploadTarget.RESUME_INTAKE)`로만 수행하고, 생성 파일의 `parents`가 `[RESUME_INTAKE_TARGET.folder_id]`와 정확히 같은지 검증한다.
- My Drive root, 임의 folder ID, 서비스 계정 업로드 경로를 새로 만들지 않는다.
- `01 DB` 기본 제외 정책은 `ZZ`, `Foreigner`, 루트 직속 파일 8건이다. `01 DB/Unsorted/04`는 이 제외 정책에 걸리면 안 된다.
- 다운로드 차단 파일은 API 우회로 회수하지 않는다. owner 설정 변경 또는 owner 이전을 요청한다.
- 지원 확장자는 `data_extraction/services/supported_formats.py`의 `TEXT_SOURCE_EXTENSIONS`가 단일 기준이다.
- 브라우저 캡처 업로드 경로는 현재 제거되어 있다. `tests/test_browser_capture_removed.py`가 서비스 파일, route, 설정 제거 상태를 회귀 테스트한다.

## Queue And Failure Rules

운영 큐는 `FileData.needs_resume_processing`과 `resume_processing_reason` 기준이다.

- `needs_resume_processing=True`: updater가 다시 처리해야 하는 파일이다.
- `resume_processing_reason`: 재처리 또는 종결 사유이며, 예시는 `text_ready_for_llm`, `text_artifact_exists`, `structured_json_without_db_save`, `vision_text_required`, `download_failed_retry`다.
- `needs_resume_processing=False`: 처리 완료, 정책 제외, 권한 차단, 비이력서, 최종 실패처럼 현재 updater가 실행할 일이 없는 상태다.
- `retryable=True`만으로 운영 큐가 되지 않는다. 다시 실행할 파일은 `needs_resume_processing=True`로 남긴다.

Provider 503/429/timeout/empty response는 `needs_resume_processing=True`로 재처리 대상에 남긴다. 권한 차단, Drive `notFound`, 암호화 문서, 빈 텍스트, 비이력서, 구조화 빈값은 `needs_resume_processing=False`와 구체적인 `resume_processing_reason`으로 닫는다.

텍스트가 충분하지 않은 파일은 원본 유형에 따라 분기한다.

- PDF 원본이면 `needs_resume_processing=True`/`vision_text_required`로 남겨 비전 기반 텍스트 추출 기회를 준다.
- PDF가 아니면 `needs_resume_processing=False`/`too_short_text`로 닫는다.
- `classify_extraction_next_actions` 같은 큐 재분류 경로도 파일명, 확장자, MIME type을 함께 전달해야 PDF 여부를 보존한다.

## Text Extraction Quality Rules

텍스트 품질 기준은 `data_extraction/services/text.py`의 `is_resume_text_sufficient()`가 단일 판단 기준이다.

- `MIN_RESUME_TEXT_CHARS` 이상이면 충분한 텍스트다.
- `MIN_COMPACT_RESUME_TEXT_CHARS` 이상이면 이름·연락처·경력·학력 같은 이력서 신호 richness로 보완 판단한다.
- 50자 안팎의 짧은 문자열은 LLM 투입 가능한 이력서 텍스트로 보지 않는다.
- PDF text layer가 짧고 페이지 이미지 면적 신호가 있으면 `classify_pdf_extraction_profile()`이 비전 텍스트 fallback 필요로 분류한다.
- PDF 비전 fallback은 `PDF_VISION_TEXT_ENABLED`, `PDF_VISION_TEXT_MODEL`, `PDF_VISION_TEXT_MAX_TOKENS`, `PDF_VISION_TEXT_MAX_PAGES`, `PDF_VISION_TEXT_RENDER_SCALE` 설정을 따른다.

## LLM And Batch Rules

- 기본 구조화 모델은 `gemini-3.1-flash-lite`다. 사용자가 명시하지 않으면 바꾸지 않는다.
- PDF text layer가 sparse한 이미지형 이력서 텍스트 추출은 `PDF_VISION_TEXT_MODEL`을 쓰고, 미설정이면 `GEMINI_FLASH_LITE_MODEL` 또는 `gemini-3.1-flash-lite`를 쓴다.
- Batch는 Drive 다운로드나 텍스트 추출을 하지 않는다. 이미 만든 manifest와 `texts/<file_id>.txt`만 입력으로 쓴다.
- 긴 프로세스 안에서 요청과 polling을 함께 묶지 않는다. 요청, 회수, 재시도는 분리한다.
- 구조화 LLM 추출은 fail-fast가 기본이다. 한 파일에서 장시간 sleep/backoff로 worker를 붙잡지 않는다.

## Verification

수정 후에는 코드 목차와 focused 테스트를 같이 확인한다.

```bash
uv run --locked python -m tools.code_knowledge code_query --query "데이터 추출"
scripts/debug_workspace.sh test -q data_extraction/tests.py tests/test_realtime_file_status_source.py tests/test_update_candidates_results.py tests/test_optional_resume_education.py
```

상황에 맞는 더 좁은 테스트가 코드 지도에 나오면 그 테스트를 우선 실행한다.
