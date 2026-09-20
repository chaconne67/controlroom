# 메일 분류 Codex Luna CLI 전환 및 Gemini 3.8 Flash 폴백

## 2026-09-20 현행 운영 정본

### 완료 상태

- 운영 반영 커밋: `85632136cee5b846d402968b34777d4f21e6e4da`
- 운영 배포 완료: 2026-09-20 15:53:12 KST
- 운영 기본 분류: OpenAI Codex CLI `gpt-5.6-luna`, reasoning `low`
- 운영 폴백 분류: Gemini API `gemini-3.8-flash`, reasoning `low`
- GitHub `main`, 운영·디버깅 체크아웃과 실행 앱의 커밋이 일치하고 모두 clean이다. 앱·SSE·알림·Nginx와 호스트 작업자 11개, 메일 체커, HTTPS가 정상이다.
- 운영 코드와 메일 체커 사용자로 합성 일반 메일을 실제 Luna CLI 한 번으로 분류해 `normal` 결과와 JSON 계약을 확인했다. Gemini 폴백은 호출되지 않았다.

### 공식 실행 경로

```text
MailChecker
  -> common.llm.call_llm_json
  -> Codex CLI gpt-5.6-luna 1회
     - 인증만 공유하는 전용 CODEX_HOME
     - 빈 LLM 전용 작업 폴더
     - 개발 도구·스킬·브라우저·다중 에이전트 기능 비활성
     - --output-schema로 같은 JSON 스키마 강제
  -> JSON 스키마 및 메일 분류 계약 검사
  -> 정상 후속 처리

Codex 통신 실패 또는 결과 계약 실패
  -> 같은 common.llm.call_llm_json 안에서 Gemini API gemini-3.8-flash 1회
  -> 같은 JSON 스키마 및 메일 분류 계약 검사
  -> 성공하면 정상 후속 처리 계속
  -> Codex 실패 원인과 Gemini 폴백 결과는 기존 OperationalError에 pending으로 기록

Codex와 Gemini 모두 실패
  -> 기존 classification_status=failed 및 재시도 계약 유지
```

업무 연속성과 장애 수리를 분리한다. Codex가 실패해도 Gemini가 메일 분류 업무를 끝내며, 폴백 성공으로 Codex 장애를 숨기지 않는다. 기존 오류 DB 기록은 main 서버의 Codex 자동 수정기가 조사할 수 있는 입력이 된다.

### 책임 구분

- **LLM**: 제목, 본문, 첨부파일 문맥을 해석하고 `resume`, `spam`, `normal`과 기존 필수 결과를 판단한다.
- **공통 LLM 호출 도구**: 공급자 호출, API/CLI 구분, 모델 선택, 엄격한 JSON 스키마, 결과 계약 검사, 한 번의 폴백과 사용량 정규화를 담당한다.
- **MailChecker**: 메일 입력을 전달하고 검증된 결과를 기존 업로드·후보자 처리 흐름에 연결한다.
- **기존 오류 기록기**: Codex 실패 원인, CLI 방식, Luna 모델, Gemini 폴백 성공·실패를 같은 운영 오류 경로에 남긴다.
- **main 서버 Codex**: 기록된 오류를 가져와 원인을 조사하고 승인된 범위에서 수정·검증·커밋한다.

스크립트가 제목 키워드로 메일 의미를 판정하지 않는다. 스크립트는 입력 전달과 기계적으로 확인 가능한 형식·필드·첨부 일치만 검사한다.

### 공통 LLM 모델 목록과 호출 방식

| 공급자 | 모델 | 방식 | 현재 용도·상태 |
|---|---|---|---|
| OpenAI Codex | `gpt-5.6-luna` | CLI | 메일 분류 기본 모델, JSON Schema 실호출·운영 실호출 확인 |
| OpenAI Codex | `gpt-5.6-terra` | CLI | 공통 도구에서 다른 용도로 명시적으로 선택 가능한 모델 |
| OpenAI Codex | `gpt-5.5` | CLI | 기존 JD·자동게시 등 명시적 호출에 유지 |
| Muse | `muse-spark-1.3` | API | 공통 도구에서 선택 가능한 모델, 이전 메일 기본 모델 |
| Muse | `muse-spark-1.3-contributor` | API | 다른 저비용 용도에서 명시적으로 선택 가능한 모델 |
| Gemini | `gemini-3.1-flash-lite` | API | 기존 경량 호출 |
| Gemini | `gemini-3.7-flash` | API | 기존 호출 모델 |
| Gemini | `gemini-3.8-flash` | API | 메일 분류 폴백, 실제 폴백 확인 |
| Gemini | `gemini-embedding-001` | API | 기존 임베딩 호출 |
| Gemini | `gemini-embedding-2` | API | 기존 임베딩 호출 |
| OpenRouter | `minimax/minimax-m3` | API | 기존 OpenRouter 호출 |

더 이상 공급자 목록에 없는 `gemini-2.0-flash` 하드코딩은 제거된 상태를 유지한다. `common/llm.py`의 단일 카탈로그가 현재 모델과 `api`·`cli` 전송 방식의 정본이다.

### CLI 오버헤드 확인과 축소

동일한 합성 이력서 메일과 동일 JSON Schema를 사용해 단계별로 비교했다.

| 실행 조건 | 입력 토큰 | 출력 토큰 | 시간 |
|---|---:|---:|---:|
| 기존 전용 홈 + 저장소 작업 폴더 | 13,817 | 128 | 6.88초 |
| 인증만 있는 빈 홈 + 빈 작업 폴더 | 11,987 | 138 | 6.76초 |
| 빈 환경 + 불필요한 개발 도구 기능 비활성 | 9,386 | 128 | 6.38초 |

최소 실행으로 입력 토큰을 4,431개, 약 32% 줄였다. `codex exec`는 개발 에이전트용 CLI이므로 모델 시스템 문맥 자체를 제거하는 문서화된 raw inference 모드는 없다. CLI 사용 계약을 유지하는 범위에서는 현재 설정이 확인된 최소 경로다. 에이전트 문맥까지 없애려면 별도의 직접 API 호출로 전송 방식을 바꾸는 제품 결정이 필요하다.

### 변경 범위와 최소 구현

- 메일 분류 모델 상수만 `gpt-5.6-terra`에서 `gpt-5.6-luna`로 바꾸고, 기존 공통 모델 카탈로그에 Luna를 추가했다.
- 기존 `codex_exec()`, `call_llm_json`, `MailChecker`, Gemini 폴백, `OperationalErrorHandler`, 실패 재시도 계약을 그대로 재사용했다.
- 개인정보 정규화, 분류 프롬프트, JSON Schema, 결과 검사, 첨부 선택, Drive 업로드와 후보자 처리 규칙은 바꾸지 않았다.
- 새 호출기, 워커, 스케줄러, 오류 테이블, 패키지는 만들지 않았다.
- Terra와 Muse 모델 두 개는 다른 용도에서 명시적으로 선택할 수 있도록 공통 카탈로그에 유지했다.

### 검증 근거

- 변경 전후 동일한 메일 분류 집중 검사 32개가 모두 통과했다.
- 공통 LLM 검사 34개, 메일 분류·메일 체커 집중 검사 32개가 각각 통과했다.
- 승인된 보호 기준을 이번 커밋으로 고정하고 보호된 운영 계약 검사 222개를 통과했다. 이전 Terra 기준은 root 전용 백업 파일과 Git 보존 참조에 남겼다.
- Django 시스템 검사, Ruff, diff 검사, 코드 지식 카탈로그 검사와 코드 리뷰 루프가 통과했고 승인된 finding은 없다.
- 실제 Luna CLI 분류 6종이 모두 기대 결과와 일치했다: 이력서 첨부, 본문 이력서, 채용 광고, 일반 일정, 과거 이력서 인용 답장, 플랫폼 거절 알림.
- 6종 실호출 합계는 입력 55,981토큰, 캐시 입력 20,736토큰, 출력 910토큰, 추론 출력 130토큰, 37.214초였다.
- Luna 실패를 강제로 만든 전체 MailChecker 경로에서 실제 Gemini 3.8 폴백이 업무를 끝냈고, Luna 실패 원인과 폴백 성공이 기존 `OperationalError`에 `pending`으로 기록됐다.
- 확장 검사 110개 중 109개가 통과했다. 변경하지 않은 이메일 휴지통 검사의 `RFC822`와 현재 운영 코드의 `BODY.PEEK[]` 기대값 불일치 1개는 부모 커밋에서도 동일하게 재현되어 이번 변경과 구분했다.
- 운영 배포 뒤 GitHub `main`, 운영·디버깅 체크아웃, 앱·SSE·알림 컨테이너가 모두 `85632136cee5b846d402968b34777d4f21e6e4da`로 일치하고 clean이다.
- 운영 코드의 합성 일반 메일은 `codex_cli / gpt-5.6-luna / low` 한 번만 호출되어 `normal`로 끝났고 Gemini 폴백은 사용되지 않았다.
- HTTPS 200, 서비스 5개 1/1, 작업자·지원 프로세스 11개 active·jobs 0·drain off, 메일 체커 active, 배포 뒤 메일 체커 오류 0건을 확인했다.

### 이전 2026-09-20 Terra 운영 단계

커밋 `7eda4e4e37945270530abe198559f31f4ed77cf7`에서는 Codex CLI `gpt-5.6-terra`를 기본 모델로 운영했다. 이 단계에서 CLI 입력 문맥 축소, JSON Schema 강제, Gemini 3.8 Flash 폴백과 오류 기록을 완성했다. 현행 Luna 전환은 같은 단일 실행 경로를 그대로 재사용하고 기본 모델 선택만 바꿨다.

### 이전 2026-09-20 Muse 운영 단계

커밋 `47d66bf3f88d3cc54bee598fcf5639cc50f80f43`에서는 Muse API `muse-spark-1.3`을 기본, Gemini API `gemini-3.8-flash`를 폴백으로 운영했다. 이 단계에서 공통 모델 카탈로그, 폴백 후 업무 지속, 기본 모델 실패의 `OperationalError` 기록 계약을 만들었다. 이후 Terra와 현행 Luna 전환은 그 경로를 재사용하며 기본 공급자만 Codex CLI로 바꿨다.

---

# 2026-07-29 이전 계획 원문 — 현재 비활성

아래 내용은 당시의 Codex CLI `gpt-5.4` 및 Gemini `gemini-3.5-flash-lite` 계획과 검증 기록이다. 현행 운영 방식으로 사용하지 않으며, 위의 **2026-09-20 현행 운영 정본**을 따른다.

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
