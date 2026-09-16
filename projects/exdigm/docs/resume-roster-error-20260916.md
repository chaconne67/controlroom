# Drive 추천인재 목록의 단일 이력서 처리 오류 — 2026-09-16

## 현재 결과와 범위

- 새 운영 오류의 출처와 실패 경로를 읽기 전용으로 확인하고 실제 AI 응답으로 재현했다.
- 이메일 첨부 유입이 아니라 Drive의 `01 DB/Outplacement/이음길` 폴더에서 수집한 파일이다.
- 이 문서는 원인 확인과 다음 수정의 재개 정보다. 이 새 사례의 앱 코드 수정·배포·운영 재처리는 실행하지 않았다.
- 앞서 승인·배포된 BOM 수정 `87683dae`는 별도 원인이다. 원래 BOM 실패 파일의 재처리 대기 상태도 유지한다.

## 운영 사실

- FileData: `3892ff70-fd62-4cde-b5bf-0adce5d5e78b`.
- Drive 파일: `1mYlSKyX9lmcZEMH4lQ-UUM5PbxdlDHRG`.
- 파일명: `이음길HR 추천인재리스트_26.09.xlsx`.
- source_channel: `drive_batch`; 연결된 Mailplug 업로드 기록 0개, ResumeUploadLedger 0개.
- 생성·수집: 2026-09-16 20:01:21 KST / 11:01:21 UTC.
- 다운로드·텍스트 추출: 20:01:27 KST / 11:01:27 UTC.
- 최종 추출 실패: 20:03:59 KST / 11:03:59 UTC.
- 상세 오류: `ValueError: LLM JSON root must be an object`.
- 실패 유형·단계: `resume_knowledge_contract_failed` / `knowledge_validation`.
- 최초 처리와 재시도 2회 실패 후 attempt_count=3, retryable=False, needs_resume_processing=False.
- Candidate 연결 없음, Resume 0개, structured_json 없음, db_saved_at 없음.
- OperationalError: `a8025284-6f47-5e84-e8f4-2df81d753684`; 실제 실패 시각과 알림 기록 생성 시각 11:04:02 UTC를 구분한다.

## 기준선과 직접 증거

- debug detached HEAD, 운영 clean main: `87683dae905f56676bb6f0d4b9916c2d86bcfb0d`.
- updater는 19:57:11 KST에 해당 운영 체크아웃에서 시작했다. 대상 파일은 그 이후 20:01에 처음 수집됐다.
- 공식 `scripts/debug_workspace.sh shell-readonly -i python`에서 DB 역할 `exdigm_debug_ro`, transaction_read_only=on을 확인했다.
- 보관 원문 53,536자, 물리 행 1,254개, source_records 1,242개, BOM 0개다.
- 보관 원문 SHA-256: `34ac96fc0947c798b760d7a6af891ddc2c75e71a040fb266f6fe99ac6462f95c`.
- 처리용 텍스트 50,276자이며 표 원문의 tabular 행은 330개다.
- 원문 전체의 일반 이메일 패턴 1개, 일반 전화번호 패턴 0개다. 이 수치는 후보자 본인 연락처의 검증 결과를 뜻하지 않는다.
- 진단 전후 FileData 전체 행 SHA-256: `d747115c0ed58857528c9c4fabcc564df55a7106cc80383fc78c1bfd0ee1a6bc`, 바이트 표현 동일, Resume 0개 유지.
- 조정실 시작 main `d09fc1dba81004334659f6f87bddbb51cf68f38a` clean; 변경은 이 문서와 README 링크뿐이다.

## 확인된 실패 경로

1. `classify_text_document_type`은 원문과 처리용 텍스트 모두 `single_resume`으로 반환한다.
2. 분류 근거는 roster_score=10, resume_score=6, score=4이며 `many_repeated_contact_rows`와 `pass_through_by_default`가 포함된다.
3. 현재 분류기는 제한된 다수 연락처·인물 신호가 없으면 기본적으로 단일 이력서로 통과시킨다. 이 파일은 추천인재 목록인데 그 경로로 들어간다.
4. realtime `text_to_pipeline_result`는 입력을 무조건 D8 `extract_resume_knowledge_from_text`에 연결한다.
5. D8는 언어 판정 → 국문 원천 행 → 항목별 지도 → 각 항목 추출·번역 → 한 사람의 이름 보완을 실행한다.
6. 실제 재현에서 `ensure_identity → retry_identity → run_llm_json → parse_json_object`가 같은 상세 오류로 실패했다.
7. 이름 보완 첫 응답은 빈 이름의 객체 1개를 담은 배열이었다. 형식 수정 재요청도 객체 68개를 담은 배열을 반환했다.
8. 68개 항목의 name/name_en은 모두 비어 있다. 이는 식별된 후보자 68명을 뜻하지 않는다. 응답의 1,231개 source_ids는 국문 원천의 S 행 기준으로 모두 유효하다.
9. 처리기는 한 사람의 객체를 요구하므로 배열을 거부하며 knowledge 생성·후보자 저장 전에 종료한다.

기존 복수 후보자 응답 파서와 `ingest_multi_candidate_payload` 저장 경로는 존재한다. 그러나 현재 realtime D8 생산 경로는 해당 payload를 만들지 않는다. 관측 오류의 구조 원인은 목록 문서의 입력 범위와 한 사람의 이력서 출력 범위가 맞지 않은 채 연결된 것이다. 과거 운영 3회 전체의 AI 응답은 보관되지 않아 각 시도의 정확한 호출 지점은 소급 확정하지 않는다.

## 재현 방법과 한계

- 모델은 기존 `gemini-3.1-flash-lite`를 유지했다. 앱 소스·프롬프트·저장·재시도 정책은 바꾸지 않았다.
- 원문과 응답은 서버 `.debug/resume-roster-3892-20260916/` 아래 0700 디렉터리와 0600 파일로만 보관한다.
- 첫 진단은 6회 호출 제한에서 중단됐으며 운영 오류의 재현 성공으로 세지 않는다.
- 이어진 캐시 재사용 진단에서 API client closed 오류가 발생했다. 이 진단 오류를 운영의 JSON 객체 오류 원인으로 사용하지 않는다.
- 최종 재현은 직렬 호출이 먼저 수행되는 기존 흐름에 맞춰 API client를 초기화하고, 이미 받은 동일 프롬프트 응답 16개를 재사용했다.
- 최종 실행은 논리 호출 34개 중 새 실제 AI 호출 18개, 34.23초였으며 운영과 동일한 ValueError를 재현했다.
- 최종 결과: `continued-primed/result.json`, 호출 요약: `continued-primed/call-summary.json`, 실제 이름 응답: `call-33-response.txt`·`call-34-response.txt`, traceback: `continued-primed/traceback.txt`.
- 생성된 결과를 운영 또는 개발 Candidate로 저장하지 않았다. 진단만 수행했으므로 재발 방지 완료로 판정하지 않는다.

## 다음 수정의 목적과 보호 조건

- D8에 보내기 전에 한 사람의 이력서, 복수 사람의 이력서 문서, 추천 명단·안내 표를 구분하는 책임을 확인한다.
- 문서 의미와 사람별 원문 귀속은 AI가 판단한다. 파일명 키워드나 연락처 개수만으로 의미를 확정하지 않는다.
- 기존 라우팅·복수 후보자·저장 구현을 검색하고 재사용 가능성을 먼저 검토한다.
- 사람별 실제 이력서가 있는 문서는 사람별 근거와 출력 범위를 맞춰 기존 저장 경로로 연결한다.
- 필수 이름·검증 가능한 본인 연락처·실질 경력·학력을 만들지 못하는 명단은 구체적 종결 이유를 남긴다. 이름이나 연락처를 만들어 저장하지 않는다.
- JSON 배열에서 첫 항목만 골라 성공으로 만들거나, 이름 필수조건을 완화하거나, 이 파일명에만 맞춘 제외 규칙을 추가하지 않는다.
- 단일 이력서의 기존 D8 경로, BOM 수정, 이메일·전화번호 신원 매칭, 수동 필드 우선, 원문 보존, 기존 성공 사례와 고정 보호 검사 18개를 유지한다.
- 수정 전후 공식 debug 테스트, 실제 이 명단·일반 명단·사람별 이력서 문서·기존 성공 이력서 검증과 code-review-loop를 수행한다.
- 운영 배포와 이 FileData 재처리 상태 변경은 구체적 코드·검증 결과와 함께 승인 범위를 각각 확인한다.

## 재개

1. 이 문서와 GBrain `incident/exdigm-drive-roster-single-resume-route-20260916`을 읽는다.
2. 실제 debug/운영/origin Git 상태와 대상 FileData를 다시 대조한다. clean만으로 미배포 커밋을 초기화하지 않는다.
3. 새 원인의 수정 요청·범위를 확인하고 목록 판정 및 사람별 처리 연결의 최소 구현을 잠근다.
4. 검증된 코드만 커밋하고, 명시된 운영 배포·운영 재처리 범위에서 각각 공식 경로를 사용한다.
