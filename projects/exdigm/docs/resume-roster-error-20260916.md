# Drive 추천인재 목록의 단일 이력서 처리 오류 — 2026-09-16

## 현재 결과와 범위

- 새 운영 오류의 출처와 실패 경로를 읽기 전용으로 확인하고 실제 AI 응답으로 재현했다.
- 이메일 첨부 유입이 아니라 Drive의 `01 DB/Outplacement/이음길` 폴더에서 수집한 파일이다.
- 주인님이 ‘이건 이력서가 아니니까 처리를 안해야하는거 아닌가’로 범위를 명확히 하고 ‘수정해’로 승인했다. 추천 명단을 비이력서로 제외하는 코드 수정·검증·리뷰·커밋을 완료했다.
- 수정 커밋은 `8084524bdbea4b6cb8de905b7d1398899187140f`이며 `/home/chaconne/exdigm-roster-debug-20260916`의 detached HEAD에 있다. 운영과 origin/main은 기존 `87683dae`다. 이 새 수정의 push·운영 배포·운영 FileData 변경은 실행하지 않았다.
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

- 진단 및 수정 전 기준: debug detached HEAD, 운영 clean main `87683dae905f56676bb6f0d4b9916c2d86bcfb0d`.
- updater는 19:57:11 KST에 해당 운영 체크아웃에서 시작했다. 대상 파일은 그 이후 20:01에 처음 수집됐다.
- 공식 `scripts/debug_workspace.sh shell-readonly -i python`에서 DB 역할 `exdigm_debug_ro`, transaction_read_only=on을 확인했다.
- 보관 원문 53,536자, 물리 행 1,254개, source_records 1,242개, BOM 0개다.
- 보관 원문 SHA-256: `34ac96fc0947c798b760d7a6af891ddc2c75e71a040fb266f6fe99ac6462f95c`.
- 처리용 텍스트 50,276자이며 표 원문의 tabular 행은 330개다.
- 원문 전체의 일반 이메일 패턴 1개, 일반 전화번호 패턴 0개다. 이 수치는 후보자 본인 연락처의 검증 결과를 뜻하지 않는다.
- 진단 전후 FileData 전체 행 SHA-256: `d747115c0ed58857528c9c4fabcc564df55a7106cc80383fc78c1bfd0ee1a6bc`, 바이트 표현 동일, Resume 0개 유지.
- 조정실 시작 main `d09fc1dba81004334659f6f87bddbb51cf68f38a` clean; 변경은 이 문서와 README 링크뿐이다.

## 수정 전 확인된 실패 경로

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

## 수정 전 재현 방법과 한계

- 모델은 기존 `gemini-3.1-flash-lite`를 유지했다. 앱 소스·프롬프트·저장·재시도 정책은 바꾸지 않았다.
- 원문과 응답은 서버 `.debug/resume-roster-3892-20260916/` 아래 0700 디렉터리와 0600 파일로만 보관한다.
- 첫 진단은 6회 호출 제한에서 중단됐으며 운영 오류의 재현 성공으로 세지 않는다.
- 이어진 캐시 재사용 진단에서 API client closed 오류가 발생했다. 이 진단 오류를 운영의 JSON 객체 오류 원인으로 사용하지 않는다.
- 최종 재현은 직렬 호출이 먼저 수행되는 기존 흐름에 맞춰 API client를 초기화하고, 이미 받은 동일 프롬프트 응답 16개를 재사용했다.
- 최종 실행은 논리 호출 34개 중 새 실제 AI 호출 18개, 34.23초였으며 운영과 동일한 ValueError를 재현했다.
- 최종 결과: `continued-primed/result.json`, 호출 요약: `continued-primed/call-summary.json`, 실제 이름 응답: `call-33-response.txt`·`call-34-response.txt`, traceback: `continued-primed/traceback.txt`.
- 생성된 결과를 운영 또는 개발 Candidate로 저장하지 않았다. 진단만 수행했으므로 재발 방지 완료로 판정하지 않는다.

## 승인된 목적·범위와 보호 조건

- 원하는 결과: 추천 명단을 상세 이력서 추출에 보내지 않고 FileData에 비이력서 판정과 사유를 남겨 큐를 닫는다. Candidate·Resume을 만들지 않으며 추출 실패·재시도·오류 알림 경로를 호출하지 않는다.
- 변경 범위: `data_extraction/services/text.py`의 문서 판정, `data_extraction/services/runners.py:text_to_pipeline_result`의 D8 진입부, 새 `tests/test_resume_document_routing.py`.
- 실제 개인 이력서는 Excel 형식이거나 이름·연락처가 누락되어도 문서 유형만으로 제외하지 않는다. 필수 정보 검사는 기존 저장 정책의 책임으로 유지한다.
- 복수 사람별 추출·저장 연결은 이번 승인 범위에 포함하지 않는다. 기존 복수 후보자 파서·저장 경로도 변경하지 않는다.
- 단일 이력서 D8·BOM 수정·신원 매칭·수동 필드 우선·원문 및 메타데이터·다운로드 및 텍스트 추출 시각·기존 테스트·보호 계약 18개·다른 작업의 dirty 변경을 보존한다.
- JSON 배열의 첫 항목 선택, 이름·연락처 생성, 필수조건 완화, 파일명이나 확장자에만 맞춘 제외 규칙을 추가하지 않는다.

## 기준선 잠금과 최소 구현

- 수정 시작 시 기본 debug에는 다른 작업의 `tests/conftest.py` 변경 21줄이 있었다. 파일 SHA-256 `63eea9c72eacb5f1715fa23efa45aa3cd1676fb406b6a139dbd01fd19592af25`가 수정 종료 시에도 같다.
- 기존 변경을 건드리지 않고 같은 `87683dae`에서 별도 detached worktree `/home/chaconne/exdigm-roster-debug-20260916`를 만들었다. 잠긴 uv 의존성과 공식 debug 환경·공용 테스트 잠금을 사용했다.
- 작업 중 기본 debug의 자동게시 테스트 2개에도 다른 작업의 변경이 추가됐다. 이 파일들 및 조정실 README의 다른 작업 링크·미추적 자동게시 계획은 보존하고 이번 앱 커밋에 포함하지 않았다.
- 최소 구현 게이트: 5단계에서 멈춤. 실제 `rg`로 `classify_text_document_type`, `GenerateResumeTools.run_llm_text/parse_json_object`, `NON_RESUME_DOCUMENT_KINDS`, `apply_next_action`을 확인하고 재사용했다. 새 의존성·모델·호출 전송부·JSON 파서·DB 모델을 만들지 않았다.
- 일반화 근거: 연락처가 적고 이력서 관련 표 열이 있는 목록은 제한된 구조 신호 때문에 기본값으로 단일 이력서가 된다. 이 기본 통과를 완성된 의미 판정으로 취급하지 않고 원문 전체를 기존 AI에 전달한다.
- 수정 전 공식 테스트 199개 통과. 실제 정상 이력서도 같은 기준 코드에서 기존 AI 추출·후보자 투영에 성공했다.

## 최종 공식 경로와 변경

1. Drive 다운로드·텍스트 추출·보관과 기존 구조 판정은 유지한다.
2. `text_to_pipeline_result`가 원본 extractor text와 처리용 text를 읽는다.
3. 기존 구조 판정에서 `pass_through_by_default`가 있고 기존 텍스트 품질이 충분하면 `resolve_text_document_type`이 전체 원문으로 AI 문서 유형을 판정한다. 명확한 기존 단일 이력서는 추가 호출 없이 같은 D8로 연결한다.
4. AI 출력은 `is_resume` boolean과 비어 있지 않은 `reason`을 가진 객체다. 계약 오류는 실제 응답·오류를 전달해 한 번만 재요청한다. 재실패는 `document_classification_failed/input_classification`으로 남고 provider 오류는 기존 구체적 사유를 보존한다.
5. 비이력서면 FileData의 유형·라우팅·기존 형식의 분류 근거만 갱신한다. `apply_next_action`이 `needs_resume_processing=False`, `resume_processing_reason=non_resume_document`를 저장한다. 상세 D8·knowledge·Candidate·Resume 생성 전에 None을 반환한다.
6. 기존 realtime 소비자는 None을 skip으로 세고 finally에서 claim을 해제한다. 큐 재분류도 기존 비이력서 정책으로 닫힌 상태를 유지한다.
7. 실제 이력서는 변경하지 않은 D8 → pending knowledge → 후보자 투영 → 기존 저장 경로를 사용한다.

## 수정 후 검증 결과

| 검증 | 결과 |
|---|---|
| 실제 원본 명단, 기존 모델 `gemini-3.1-flash-lite` | 실제 AI 판정 1회로 `non_resume_document`; 상세 D8 호출 0 |
| 표의 셀을 세로 행으로 펼친 변형 | 실제 AI 판정 1회로 비이력서 |
| 시트 제목을 제거한 변형 | 실제 AI 판정 1회로 비이력서 |
| 위 3개 입력의 FileData source → updater | 실제 AI 응답을 재사용한 격리 테스트 DB에서 비이력서 사유 저장, Candidate·Resume 생성 0, 큐 재개 없음 |
| 실제 정상 이력서, 수정 전·후 새 실제 AI 호출 | 이름·영문명·이메일·전화·출생연도·성별 동일, 경력 3개·학력 2개 유지 |
| 정상 이력서의 수정 전·후 실제 AI 결과 저장 | 격리 테스트 DB의 공식 updater·저장에서 각각 Candidate·Resume 연결, 현재 이력서·FileData 링크, 경력 3개·학력 2개 확인 |
| Excel 개인 이력서 | 실제 XLSX 텍스트 추출 후 AI가 `single_resume`으로 판정 |
| 관련 공식 테스트 | 218개 통과: 기존 199 + 새 회귀 14 + 실제 입력/응답 재사용 검사 5 |
| 원본·처리용 텍스트를 운영 보관본과 정확히 맞춘 재검사 | 격리 테스트 DB 검사 5개 통과 |
| 보호 계약 검사 | 216개 통과, pin `fb177d6a02f2a5b5ea14ea6440ad679f4331826a`의 파일 18개 그대로 |
| Django check·ruff·diff check·catalog_update | 오류 없음, 코드 지도 current·valid, 누락/깨진 참조 없음 |
| code-review-loop | unknown 입력의 잘못된 제외 조건 1개 수정, 같은 전체 diff 재검토 승인 finding 0·열린 계약 질문 0 |

- 정상 이력서의 두 독립 실제 AI 실행에서는 `core_competencies` 문구만 달랐다. D8·투영 코드는 바꾸지 않았으며, 보호 신원 및 경력·학력 수와 두 결과의 실제 저장을 각각 확인했다. 전체 AI JSON이 같다고 주장하지 않는다.
- 실제 AI 호출과 격리 DB 저장 검사는 분리했다. 공식 테스트는 외부 인증을 읽지 않으며, 검증된 실제 AI 응답·knowledge·profile만 재사용해 실제 DB 저장 경로를 실행했다.
- 공용 잠금으로 최종 DB 검사가 한 차례 55초 대기 후 종료됐다. 잠금이 풀린 것을 확인한 뒤 공식 명령으로 다시 실행해 완료했다. 다른 작업에 메시지를 보내거나 잠금을 해제하지 않았다.
- 실제 원문·AI 응답·비교·DB 재사용 검사는 별도 worktree `.debug/resume-input-gate/`에 0700/0600으로 보관했다. Git·문서·GBrain에 이력서 내용·연락처·비밀값을 넣지 않았다.

## 운영 상태와 남은 경계

- 수정 종료 시 조회 전용으로 두 FileData 전체 행이 수정 전과 같음을 확인했다. 원본 명단 SHA `d747115c0ed58857528c9c4fabcc564df55a7106cc80383fc78c1bfd0ee1a6bc`, 정상 대조 SHA `94f78ab2a08229865f354be6f85b12e136212e2ecef73f1cf33fd155c7df4982`다.
- 운영 명단은 기존 실패 기록으로 이미 큐가 닫혀 있으며 Candidate 연결 없음·Resume 0개가 유지된다. 운영 행을 비이력서 사유로 소급 변경하지 않았다.
- 검증 범위에서 수정본의 명단 → 단일 이력서 상세 추출 실패 경로는 차단됐다. 운영 재발 차단은 새 커밋을 배포하고 운영 진입 경로를 확인하기 전까지 미검증이다.
- 앱 수정 커밋만 별도 detached worktree에 clean으로 보관했다. 운영 배포·운영 행 재분류는 각각 명시된 승인 범위에서 후속 실행한다.

## 재개

1. 이 문서와 GBrain `incident/exdigm-drive-roster-single-resume-route-20260916`을 읽는다.
2. 실제 debug/운영/origin Git 상태와 대상 FileData를 다시 대조한다. clean만으로 미배포 커밋을 초기화하지 않는다.
3. 검증된 `8084524bdbea4b6cb8de905b7d1398899187140f`를 별도 worktree에서 보존한다. 기본 debug의 dirty 작업을 초기화하거나 미검증 사용자 변경을 함께 커밋하지 않는다.
4. 운영 배포 요청을 받으면 실제 origin/main·운영·기본 debug 변경과 대조하고 승인된 커밋을 보존·통합해 `scripts/deploy/deploy.sh prod`를 사용한다. 운영 Git·HTTPS·Swarm·작업자와 실제 분기를 확인한다.
5. 운영 명단의 제외 사유 변경 요청을 받으면 대상 FileData 1개에 대한 복구 가능한 기준선을 잡고 재분류만 수행한다. 명단을 상세 추출하거나 후보자로 저장하지 않는다.
