# 메일 분류기 Gemini 3.5 Flash-Lite 폴백 계획

## 목표

- Codex `gpt-5.4` 메일 분류 호출이 기술적으로 실패하면 Gemini `gemini-3.5-flash-lite`가 같은 입력을 한 번 이어서 처리한다.
- 두 공급자가 모두 실패하거나 필수 출력 계약을 만들지 못하면 기존처럼 `classification_status=failed`로 남기고 정상 분류로 위장하지 않는다.
- 이력서 첨부 선택, Drive 업로드, 후보자 저장 규칙은 바꾸지 않는다.

## 공식 모델

- Google Gemini API 모델 ID: `gemini-3.5-flash-lite`
- 상태: GA
- 근거: <https://ai.google.dev/gemini-api/docs/models/gemini-3.5-flash-lite>
- 이 모델에는 폐기된 `temperature`, `top_p`, `top_k`를 보내지 않는다.

## 역할 경계

### LLM 책임

- 현재 이메일의 제목, 본문, 첨부파일 문맥을 해석한다.
- `resume`, `job_description`, `spam`, `normal` 중 하나를 판단한다.
- 기존 JSON 출력 계약을 완성한다.

### 스크립트 책임

- Codex를 기본 공급자로 호출한다.
- Codex가 기술적 오류를 내면 같은 프롬프트와 시스템 지시를 Gemini에 한 번 전달한다.
- 공급자별 모델 ID와 지원 옵션을 정확히 전달한다.
- 응답 JSON과 기존 필수 필드를 검사한다.
- 두 호출이 모두 실패하면 명시적 오류와 실패 상태를 남긴다.

### 출력 계약

- 필수 필드:
  - `mail_type`
  - `is_resume_email`
  - `resume_attachment_names`
  - `use_body_as_resume`
  - `resume_body_text`
  - `spam_filter`
  - `reason`
- 폴백 응답도 기본 응답과 같은 검사기를 통과해야 한다.
- 필수 결과를 만들지 못하면 Drive 업로드로 진행하지 않는다.

## 최종 경로

1. Mailplug 원문과 첨부파일을 파싱한다.
2. 기존 프롬프트로 Codex `gpt-5.4`를 호출한다.
3. Codex 호출이 기술적으로 실패하면 Gemini `gemini-3.5-flash-lite`를 한 번 호출한다.
4. 반환된 JSON과 필수 필드를 기존 검사기로 확인한다.
5. 기존 가드가 업로드할 이력서 원천을 확정한다.
6. 기존 Drive 업로드와 후보자 처리 경로로 전달한다.
7. 두 공급자가 모두 실패하면 원본 메일과 `classification_status=failed`를 보존하고 재시도 대상으로 남긴다.

## 변경 범위

### `common/llm.py`

- 폴백 공급자와 별도로 폴백 모델 ID를 전달할 수 있게 한다.
- Gemini 3.5 Flash-Lite 호출에서는 폐기된 샘플링 옵션을 제외한다.
- 다른 호출자의 기본·폴백 동작은 유지한다.

### `data_extraction/services/mailplug.py`

- 기본 공급자는 `codex_cli`, 기본 모델은 `gpt-5.4`로 유지한다.
- 폴백 공급자를 `gemini`로 지정한다.
- 폴백 모델을 `gemini-3.5-flash-lite`로 지정한다.
- 프롬프트, 분류 라벨, 결과 가드와 저장 규칙은 유지한다.

### 테스트

- 기본 공급자 실패 후 지정한 Gemini 모델로 같은 입력을 다시 호출하는지 확인한다.
- Gemini 3.5 Flash-Lite 호출에 폐기된 샘플링 옵션이 없는지 확인한다.
- 메일 분류 호출이 Codex 기본값과 Gemini 폴백값을 함께 전달하는지 확인한다.
- 두 공급자 실패 시 기존 실패 기록·재시도 계약이 유지되는지 확인한다.
- 기존 이력서·JD·스팸·일반 분류 회귀 테스트를 실행한다.

## 검증 명령

```bash
flock -E 75 -w 55 /tmp/exdigm-pytest.lock uv run --locked pytest -q tests/test_llm.py
flock -E 75 -w 55 /tmp/exdigm-pytest.lock uv run --locked pytest -q tests/test_update_candidates_results.py -k 'mail_classifier or mail_checker or recent_limit'
flock -E 75 -w 55 /tmp/exdigm-pytest.lock uv run --locked pytest -q tests/test_email_spam_rule_distiller.py
uv run --locked python -m tools.code_knowledge catalog_update
```

## 운영 경계

- 이번 승인 범위에는 코드 구현, 테스트, 코드 리뷰, 문서 갱신, 커밋까지 포함한다.
- 운영 배포는 포함하지 않는다.
- 운영 DB의 실패 이메일 재처리는 포함하지 않는다.
- 배포와 UID `32968` 복구는 구현 검증이 끝난 뒤 별도 지시를 받는다.

## 구현 결과

- 상태: 구현 및 로컬 검증 완료, 운영 미배포
- 기본 공급자: Codex `gpt-5.4`
- 폴백 공급자: Gemini `gemini-3.5-flash-lite`
- 공통 LLM·메일 분류 1차 계약 테스트: 22개 통과
- 메일 분류·재시도 집중 테스트: 23개 통과
- 스팸 분류 회귀 테스트: 6개 통과
- 실제 Gemini 폴백 단건 검증:
  - 강제로 Codex 기술 실패 발생
  - Gemini가 `mail_type=resume` 반환
  - `is_resume_email=true` 반환
  - `Candidate_CV.pdf`를 이력서 첨부로 선택
- 코드 목차: 깨진 참조 없음
- 코드 리뷰: 승인된 finding 없음

## 운영 배포 및 이메일 복구 계획

### 승인 대기 범위

- 운영 배포 공식 명령 `scripts/deploy/deploy.sh prod`를 실행한다.
- 로컬 `main`은 현재 운영 기준 `f11691e7`보다 46개 커밋 앞서 있다.
- 배포 정책상 특정 커밋만 골라내지 않고 46개 전체와 이 계획 문서 변경을 함께 배포한다.
- 주요 동반 변경에는 프로젝트 후보자 추천·발굴 화면, 후보자 검색·임베딩, 자동 게시 보정, 후보자 사진 복구가 포함된다.

### 이메일 복구 최종 경로

1. 운영 배포 스크립트가 `main` 전체를 push하고 운영 서버를 fast-forward한다.
2. 앱과 호스트 워커를 공식 배포 순서로 갱신한다.
3. 운영 Mailplug 체커가 `classification_status=failed`인 Jessica 계정 UID `32968`을 자동 재시도한다.
4. Codex 사용 한도 오류 뒤 Gemini `gemini-3.5-flash-lite`가 같은 이메일을 분류한다.
5. 기존 첨부 선택 경로가 `(CV)Jeehyeon Lee.pdf`를 Drive 이력서 유입 폴더에 업로드한다.
6. 기존 collector와 후보자 updater가 `FileData`, `Resume`, `Candidate`를 처리한다.

### 완료 조건

- 이메일 장부:
  - `is_resume_email=true`
  - `uploaded_count=1`
  - `classification_status=failed` 제거
- 업로드 장부:
  - 해당 이메일의 `MailplugUploadRecord` 1건 이상
  - Drive ID와 `file_data_id` 존재
- 파일 장부:
  - `FileData`가 해당 업로드와 연결
  - `needs_resume_processing=false`
  - 성공이면 `resume_processing_reason=db_saved`
- 이력서·후보자:
  - `Resume.structured_json` 존재
  - 연락처·경력·학력 저장 조건 충족 시 `Candidate` 생성 또는 기존 후보자와 연락처로 연결
- 운영 상태:
  - HTTPS 정상
  - 앱·워커 정상
  - 메일 체커 active
  - `--mailplug-dry-run` 없음

### 정상 종결 예외

- 이력서 원문에 유효한 연락처가 없으면 후보자를 임의 생성하지 않는다.
- 이 경우 `missing_contact`로 정상 종결하고 직원 알림 상태까지 확인한다.
- 중복 파일이면 새 후보자를 중복 생성하지 않고 기존 Drive/FileData 연결 결과를 확인한다.

### 중단 조건

- 운영 워크트리가 dirty
- fast-forward 불가
- 배포 스크립트 검증 실패
- 메일 체커가 dry-run
- Gemini 분류 실패
- Drive 업로드 또는 후보자 저장 경로 실패

## 배포 전 UID 32968 단건 복구 대안

### 성격

- 운영 배포 없이 해당 이메일만 처리하는 1회성 운영 복구다.
- 영구 폴백 구현의 배포·검증으로 간주하지 않는다.
- 다른 실패 이메일과 Codex 사용 한도 재발 경로는 닫지 않는다.

### 실행 경로

1. 운영 서버의 현재 코드를 그대로 사용한다.
2. Jessica 계정에서 `include_checked=true`로 원문을 읽고 UID `32968` 하나만 선택한다.
3. 현재 프로세스 안에서만 메일 분류 공급자를 Gemini로 지정한다.
4. 모델은 `gemini-3.5-flash-lite`를 지정한다.
5. 기존 `MailChecker.classify_mailplug_message()`의 프롬프트와 출력 검사기를 실행한다.
6. 기존 `MailChecker.ingest_message_to_drive()`로 분류 기록과 Drive 업로드를 수행한다.
7. 기존 collector·후보자 updater가 `FileData`, `Resume`, `Candidate`를 처리하도록 기다린다.

### 금지 범위

- DB 필드를 직접 수정하지 않는다.
- 첨부파일을 수동으로 Drive에 올리지 않는다.
- 임시 스크립트나 새 관리 명령을 만들지 않는다.
- UID `32968` 이외의 이메일을 처리하지 않는다.
- Gemini 분류가 실패하면 다른 우회 경로를 추가하지 않고 중단한다.

### 완료 조건

- 이메일 장부가 이력서로 분류되고 업로드 수가 1 이상이다.
- 해당 이메일의 업로드 장부와 Drive ID가 생긴다.
- `FileData`가 연결되고 최종 처리 사유가 남는다.
- 저장 조건을 충족하면 `Resume`과 `Candidate`가 생성 또는 연결된다.
- 저장 조건을 충족하지 못하면 `missing_contact` 등 정책상 종결 사유를 그대로 보고한다.
