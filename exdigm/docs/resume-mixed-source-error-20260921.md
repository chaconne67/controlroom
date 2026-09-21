# 혼합 언어 이력서 추출 오류 60ead5b9 — 개발 수정·검증 완료, 운영 승인 대기

## 목표와 현재 상태

오류 `60ead5b9-11ab-0359-769d-cff3f675ba66`, 원천 FileData `d7ba0f95-d074-411d-b182-8609836b5fb5`의 정상 구조화 JSON·Resume·Candidate 연결을 확인하고 동일 원인의 재발 경로를 검증한다. 사용자가 2026-09-21 오류 확인 후 `문제해결`을 요청했다.

운영 DB는 `scripts/debug_workspace.sh shell-readonly`의 `exdigm_debug_ro`, `transaction_read_only=on`, `Asia/Seoul`을 확인하고 조회했다. 현재 오류 기록은 **개정 6, `approve_deploy`**이며 `processing_status=succeeded`는 이번 개발 수정·검증의 성공이다. 원래 FileData는 09:33:38 KST 이후 변경되지 않았고 `db_saved_at=null`, `candidate_id=null`, Resume 0건, `needs_resume_processing=false`, `retryable=false`이다. 원래 이력서의 복구는 아직 완료되지 않았다.

수정 커밋은 `d69f50126ee76caacdb7ee7fe6cd2ab62a7c65fe`, 운영 기준은 `efbab7d33ac0c276ae1afe88cda6dbf5b7ee96a2`이다. 후자는 샘이 별도 승인으로 배포한 실패 응답 보관 기능이다. 이번 중복 판단 지시문 변경과 해당 파일 재처리는 아직 운영에 적용하지 않았다.

## 실제 확인한 입력과 실패 경로

- 오류 발생: 2026-09-21 09:33:38 KST.
- 오류 문구: `mixed-language canonical source contract violation after retry: canonical source invalid duplicate evidence`.
- `classification_signals.llm_failure_attempt_count=3`, 공식 `MAX_RETRY_COUNT=2`로 최초 실행과 재시도 두 번을 소진했다. 마지막 시도에서는 중복 정리의 내부 수정 요청 후에도 계약 검사를 통과하지 못했다.
- 원문 추출 산출물은 09:31:24 KST 생성됐다. 당시 처리 manifest는 `text_path`와 `extractor_text_path`를 모두 가지고 있다. 두 번째 경로를 `text_to_pipeline_result`가 우선 읽는다.

| 입력 | 원천 | 행 수 | SHA-256 |
|---|---|---:|---|
| 이전 조사에 사용된 정리 텍스트 | `FileData.extracted_text`, `texts/<drive_id>.txt` | 149 | `eb37453d195184c6abd62812323e72a107f405a24011cbcb20cfb836fc848329` |
| 공식 구조화 단계가 읽는 추출 원문 | `ResumeSourceArtifact.extractor_text`, `texts/extractor/<drive_id>.txt` | 164 | `6dddf5de0e9170a5542ca3309e2af250fdf70adc32ef55a0835b130069ab5530` |

운영 `texts/db-file-status/extractor/<drive_id>.txt`도 164행 원문과 동일하다. 149행과 164행의 차이는 빈 줄 수 차이만이 아니며 여러 위치에서 행 내용·배치가 다르다. 고객 원문은 공유 문서에 복제하지 않는다.

이전 조사 정본은 main `/home/chaconne/.local/state/exdigm-resume-investigation-60ead5b9/result.json`이다. 이 파일은 149행 입력 해시와 canonical 79행·중복 근거 70건 성공을 기록한다. 따라서 이 성공을 실제 실패 입력과 같은 조건의 재현으로 사용하지 않는다. 당시 실패한 모델 응답 원문은 확보되지 않았다.

## 문제해결 기록

### 연속 질문

1. 구조화 JSON·Resume·Candidate 연결이 없는 이유는 무엇인가? **확인:** 혼합 언어 원문 정리 단계가 중복 근거 검사 실패로 종료됐다. 오류 호출 경로와 실제 저장 결과가 근거다.
2. 혼합 언어 원문 정리 단계가 중복 근거 검사 실패로 종료된 이유는 무엇인가? **확인:** 수정 요청 뒤 두 번째 모델 응답도 필수 조건을 통과하지 못했다. 코드의 두 번 호출과 `after retry` 오류가 근거다.
3. 수정 요청 뒤 두 번째 모델 응답도 필수 조건을 통과하지 못한 이유는 무엇인가? **미검증:** 당시 원문 응답이 없어 제외할 행, 보존할 대응 행, 중복 설명 중 어느 조건이 잘못됐는지 특정할 수 없다.

### 버드뷰

원문 확보 → 언어 구성 판정 → 사실을 보존한 중복 정리 → 항목별 추출 → 구조화 JSON 저장 → 이력서·후보자 연결이 정상 경로다. 모델은 의미와 중복 여부를 판단하고 프로그램은 참조·범위·유일성·누락·필수 값의 기계적 계약을 검사한다. 최초로 확인된 실패 위치는 중복 정리 결과 검사이며 그 앞의 입력·지시·모델 생성 중 최초 이탈은 미확정이다.

### 결과 대조

**확장:** 기존 결과는 처리 가능한 149행 입력의 성공을 확인했으나 공식 경로는 164행 원문을 전달한다. 따라서 입력 일치를 바로잡은 격리 검증 전에는 일시적 모델 오류나 검사기 결함으로 원인을 확정하지 않는다.

### 실제 입력 재현 뒤 연속 질문

1. 실제 164행에서도 중복 근거 검사 실패로 종료되는 이유는 무엇인가? **확인:** 마지막 모델 응답이 페이지 표시 `L0164`를 중복으로 제외하면서 이름 행 `L0083`을 대응 근거로 지정했다. 비공개 `call-04-response.txt`와 원문 행 대응으로 확인했다.
2. 마지막 모델 응답이 페이지 표시 `L0164`를 중복으로 제외하면서 이름 행 `L0083`을 대응 근거로 지정한 것이 실패하는 이유는 무엇인가? **확인:** `L0083`도 중복으로 제외된 행이라 실제 보존된 근거가 아니다. 서로 다른 내용을 중복으로 판단한 의미 오류와, 제외된 행에 다시 의존한 참조 오류가 함께 있다. 기존 검사기는 이를 정상 차단했다.
3. 서로 다른 내용을 중복으로 판단하고 제외된 행에 다시 의존한 이유는 무엇인가? **확인된 통제 가능 지점:** 생성 지시문은 실제 보존된 행만 대응 근거로 쓸 것, 보존·제외가 겹치지 않을 것, 불확실하면 원문을 보존할 것을 충분히 명시하지 않았다. 이 계약을 같은 생성 단계에 명시한 뒤 원본·페이지 표기 변형·기존 성공 자료를 통과했다. **미검증:** 과거 운영 응답 자체와 모델 내부 판단은 복원할 수 없으며 지시문 보완이 모든 향후 오응답을 제거한다는 보장은 없다.

### 재현 뒤 버드뷰·결과 대조

공식 원문 선택 → 모델의 혼합 언어 중복 판단 → 보존·제외·참조 계약 검사 → 항목별 추출 → 구조화 JSON → 후보자 정보 변환 → 운영 저장이 전체 경로다. 원문 선택은 정상이며, 최초로 직접 확인한 이탈은 생성 단계가 잘못된 중복 관계를 만드는 것이다. 검사 완화나 원문 삭제는 필요하지 않다. 연속 질문과 **일치**하며 수정 책임은 해당 중복 판단을 생산하는 지시문에 있다.

### 근본 원인 판정과 해결책

이번 재현으로 확정한 직접 원인은 모델이 실제 보존되지 않은 행을 중복 근거로 생성한 것이다. 통제 가능한 생성 지시의 부족을 보완하는 3줄 변경을 적용했고, 원본·변형에서 임시 데이터 보정 없이 공식 추출 단계가 필요한 결과를 생산했다. 따라서 확인한 실패 유형에 대한 개발 수정은 유효하다. 다만 과거 실패 응답이 없고 운영 공식 저장까지 실행하지 않았으므로 과거 사건의 세부 원인 및 운영 재발 차단을 확정하지 않는다.

`projects/services/recommendation_resume_ssp.py`의 `GenerateResumePromptBook.mixed_language_source_prompt`에 다음 기존 계약을 명시했다.

- 보존한 원문과 중복으로 제외한 원문은 겹치지 않는다.
- 대응 근거에는 기준본 또는 추가 번역에 실제 보존한 행만 쓴다. 다른 제외 항목을 근거로 쓰지 않는다.
- 표현·위치가 비슷하다는 이유로 중복으로 판단하지 않는다. 같은 사실의 보존 근거가 없거나 불확실하면 원문을 보존한다.

모델·출력 형식·검사 조건·재시도 횟수·저장 정책은 바꾸지 않았다. 머리말·꼬리말의 고객 정보를 일괄 삭제하거나 이 파일만 특별 처리하지 않았다.

## 기준선·보호·변경

- 시작 시 debug에는 샘의 같은 사건 예약과 미배포 커밋/수정 두 파일이 있었다. 해당 변경을 수정·삭제·초기화하지 않았다.
- 이후 샘이 커밋 `efbab7d33ac0c276ae1afe88cda6dbf5b7ee96a2`를 보관하고 debug를 `649aa4e692556ffe2c84340897fc29350d1d33eb`로 반환했다. 164행 격리 검사 시작 직전에 샘의 별도 승인 배포가 시작돼 기준선 검사에서 안전하게 중단했다. 이 시점에는 본 조사에서 테스트·모델 호출을 실행하지 않았다.
- 샘의 배포 예약 `5f082f33-8646-44bc-a2d4-b10a93d6b300` 해제와 운영·debug의 clean `efbab7d3`를 확인한 뒤 진행했다. 다른 작업의 예약과 변경을 보존했다.
- 보호 불변조건: 실제 원문·추출 메타데이터, 운영 FileData·Resume·Candidate, 검사 기대값, 모델·출력 형식·재시도·저장 정책, 기존 성공 자료의 내용, 다른 작업의 Git 참조와 변경.
- 허용 변경: 위 중복 정리 생성 지시문 3줄과 조사·재개 문서. 추가 성공조건: 실제 164행의 계약 위반을 재현하고 수정 후 원본·동일 원인 변형·기존 성공 자료와 공식 전체 추출의 정상 결과를 확인한다.
- 최소 구현 게이트: 2단계에서 멈춤. 기존 `mixed_language_source_prompt`, `GenerateResumeCtype.create_canonical_source`, `repair_once.workspace_lock`, `scripts/debug_workspace.sh test`를 재사용한다. 새 생성 경로·검사기·의존성을 만들지 않았다. 조사용 응답 관찰은 원래 입력·호출 인수·응답을 바꾸지 않는다.
- 수정 소유 실행 번호는 `09ee723e-409b-4c1e-9b8c-ec23770e59ee`이다. OS 잠금과 예약 아래 수정·검증·커밋했고, 보관 참조와 DB 결과 저장 뒤 debug를 clean 운영 기준으로 반환하고 예약 해제를 확인했다.

## 적용·검증·코드 리뷰

| 검증 | 실제 결과 |
|---|---|
| 수정 전 실제 164행·실제 추출 메타데이터 | 같은 `invalid duplicate evidence` 재현. 마지막 요청·응답과 원문 행 관계 확보 |
| 수정 후 같은 164행·같은 해시 | 보존 83행·중복 근거 81건으로 통과 |
| 공식 전체 추출 `extract_resume_knowledge_from_text`와 `candidate_profile_from_knowledge` | 구조화 JSON·후보자 정보 생성 성공. 경력 3개·학력 2개·자격 4개, 이름·이메일·전화번호 확인. 운영 DB 저장은 미실행 |
| 같은 원인의 입력 변형 | 마지막 페이지 표시 `3 of 5`를 `Page 3 / 5`로 변경한 164행도 83행·중복 81건 통과 |
| 기존 성공 혼합 이력서 대조 | 별도 실제 저장 자료 145행에서 보존 73행·중복 72건. 보존 행 번호와 내용이 기존 저장 결과와 동일 |
| 기존 계약 검사 | `tests/test_recommendation_resume_local_worker.py::test_mixed_source_contract_feedback_is_bounded` 15개 수정 전후 통과 |
| 공식 환경·코드 검사 | `scripts/debug_workspace.sh check` 문제 0건, `tools.code_knowledge catalog_update` 정상·끊어진 참조 없음, `git diff --check` 통과 |
| `code-review-loop` | 주 에이전트가 3줄 diff·중복 생성/수정 요청·기존 검사/직접 소비자를 검토. 승인 finding 0 |

기존 Django `CheckConstraint` 폐기 예정 경고 3건은 통과 여부와 별도로 남아 있다. 테스트 중 이번 실행이 만든 합성 진단 자료 7건은 생성 시각·시험 모델·5행 입력을 확인해 조사 비공개 디렉터리로 옮겼고 이후 검사는 비공개 `EXDIGM_WORK_ROOT`로 격리했다. 다른 진단 자료는 보존했다.

검증 자료는 Exdigm `/home/chaconne/exdigm-debug/.debug/resume-60ead5b9-20260921/`에 있다. 디렉터리는 700, 원문·응답 파일은 600으로 보관하며 공유 Git·GBrain에 원문이나 개인정보를 복제하지 않는다.

- 요약: `verification-summary.json`.
- 실제 수정 전·후: `result.json`, `after-original/result.json`.
- 전체 추출: `full-entry/result.json`, `knowledge.json`, `profile.json`.
- 변형·기존 성공: `variant-page-expression/result.json`, `control-saved-mixed/result.json`.
- 재처리 준비: `reprocess-preparation.json`, `reprocess-prepared/`, `production-baseline.json`.

## 재발 판정

개발 검증에서 원본과 같은 원인의 변형은 정상 결과를 생산했고 기존 성공 자료도 보존됐다. **운영 경로는 미검증**이며 원래 이력서도 아직 미복구이다. 지시문 변경만으로 모든 모델 오응답이 없어졌다고 일반화하지 않는다. 실제 운영 배포 뒤 지정 원본의 공식 저장·연결을 확인해야 이 사건의 완료를 판정할 수 있다.

## 재개 정보

1. 개정 6의 `approve_deploy`, 정확한 커밋 `d69f50126ee76caacdb7ee7fe6cd2ab62a7c65fe`, 운영 기준과 아래 보관 참조를 다시 대조한다. 주인님의 운영 배포 및 지정 단건 재처리 승인 여부·범위를 확인한다. 배포 실행 소유는 샘이다.
2. 보관 참조는 `refs/operational-repairs/09ee723e-409b-4c1e-9b8c-ec23770e59ee`이다. 승인된 샘이 같은 debug OS 잠금·예약을 확보하고 기존 `exdigm-deploy`와 `scripts/deploy/deploy.sh prod`를 사용한다. 기준이 달라졌으면 원본을 보존하고 새 기준에서 검증한다.
3. 단건 준비 목록은 `load_succeeded_rows(..., force=True, limit=1)`로 정확히 해당 Drive ID 한 건만 선택됨을 확인했다. 164행 추출 원문과 149행 정리 텍스트의 사본·해시를 보존했다. **실행 직전** 최신 FileData·원문과 연락처로 연결될 기존 후보자/이력서/관련 정보를 다시 백업한다. 현재 `production-baseline.json`은 조사 시점 사본이므로 최신 백업을 대신하지 않는다.
4. 현행 공식 단건 진입점은 `data_extraction.services.candidate_update_steps.realtime_txt_to_db` 모듈이다. 위 단건 전용 자료 루트를 `EXDIGM_WORK_ROOT`로 지정하고 `--source manifest --force --workers 1 --limit 1`을 사용한다. 고정 실행 번호·파이프라인 잠금·운영 실행 환경을 확인한다. 예전 문서의 `extract_text_to_db` 관리 명령은 현행 코드에 없다.
5. 구조화 JSON, Resume 생성, Candidate 연결, 저장 완료 시각과 중복 저장 여부를 실제 DB에서 확인한다. 실패하면 먼저 부분 저장과 실패 응답을 확인하고 무조건 재시도하지 않는다. 같은 오류의 후속 이력에 실제 결과를 남긴다.
6. 완료는 원래 운영 결과와 재발 경로의 공식 검증으로 판정한다. 실패 응답 보관 기능의 배포·검사 성공으로 대신하지 않는다.
