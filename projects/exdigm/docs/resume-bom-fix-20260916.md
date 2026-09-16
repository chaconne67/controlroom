# 이력서 인코딩 표시로 인한 추출 종료 수정 — 2026-09-16

## 목표와 승인

- 주인님이 오류 확인 뒤 “수정해”로 코드 수정·검증·리뷰·문서화·커밋을 승인했다.
- 보이지 않는 BOM(U+FEFF)을 이력서 내용으로 세지 않아 정상 내용의 누락 검사를 통과하게 한다.
- 운영 배포와 실패한 운영 FileData의 재처리 상태 변경은 별도 승인 단계다.
- 코드 수정 완료 보고 후 주인님이 “운영 배포”를 명시 승인했다. 수정 커밋 `87683dae`의 일반 앱 배포를 진행하며, 실패 FileData의 수동 재처리 상태 변경은 이번 배포와 구분한다.

## 확인된 현상

- 원천 기록: `data_extraction.FileData:b3240e24-4cfd-45ca-89da-ca41d97f630e`.
- 2026-09-16 17:59:18 KST 다운로드·텍스트 추출 완료, 18:00:52 최종 실패.
- 상세 오류: `ValueError: non-korean canonical source missing refs: ['L0001']`.
- 보관 원문 6,894자에서 첫 행은 BOM 하나이고, 의미 있는 원문은 95개 행이다.
- 최초 시도와 재시도 2회 실패 뒤 대기열에서 제외됐으며 이 파일의 후보자·이력서 저장은 없다.
- 조회는 공식 `shell-readonly`에서 `exdigm_debug_ro`/`transaction_read_only=on`을 확인했다.

## 기준선과 보호 조건

- 실행 위치: `chaconne@49.247.202.197:/home/chaconne/exdigm-debug`.
- 시작 debug: clean detached `dd65eed0446d0589fc643c3faed4cef4cb816d5e`.
- 시작 운영: clean main `f01540043afe563d4f064227a4c79f3feaa206a4`.
- debug의 기존 미배포 잡코리아 5파일 커밋을 보존하며 이번 diff와 배포 범위에 포함하지 않는다.
- 로컬 controlroom의 기존 Hermes 문서·README 변경과 미전송 커밋을 보존한다.
- 본문·행 순서·Word/PDF 배치 좌표, 의미 있는 원문의 완전 포함 조건을 유지한다.
- 모델·프롬프트·AI 호출 수·연락처와 신원 규칙·저장·재시도 정책을 바꾸지 않는다.
- 원래 운영 파일·후보자·오류 기록과 큐 상태를 보존한다.

## 최소 구현과 공식 경로

- 최소 구현 게이트 3단계: `text.py:_decode_bytes`와 `GenerateResumeTools.source_records`를 검색·확인했다.
- 새 파일은 표준 `utf-8-sig` 디코딩으로 BOM을 제외하고 기존 다른 인코딩 fallback을 유지한다.
- 저장 원문을 재사용할 때는 기존 원문 행 생성에서 BOM만 제외한다. 실제 물리 행 번호는 유지한다.
- 경로: 파일 디코딩 → 보관 원문/텍스트 저장 → updater 원문 재사용 → source_records → 국문 기준자료 → 누락 검사 → 기존 후보자 저장 경로.
- 별도 전처리 경로·파서·프롬프트·외부 호출·의존성은 추가하지 않는다.
- 보관 원문을 전체 preprocess 결과로 대체하지 않는다. 전체 preprocess는 내용 중복과 서명 행도 제거한다.
- 변경 대상은 프로그램 2파일, 새 BOM 회귀 테스트 1파일, 이 계획과 README의 작업 링크다.
- 기존 테스트 2파일에 처음 더한 회귀 검사는 고정 보호 검사가 바이트 보존을 요구함을 확인한 뒤 `tests/test_resume_bom.py`로 옮겼다. 기존 18개 보호 파일은 원래 바이트로 보존했고 보호 기준 pin/ref는 바꾸지 않았다.

## 검증

- 기존 기준선 명령: `scripts/debug_workspace.sh test tests/test_extraction_text.py tests/test_resume_knowledge.py tests/test_realtime_file_status_source.py tests/test_update_candidates_results.py --tb=short`.
- 수정 전: **177 passed, 5 warnings**. 기존 검사·기대값을 삭제하거나 완화하지 않는다.
- 추가 검사: UTF-8 BOM/일반 UTF-8/UTF-16/CP949, 별도 BOM 행·이름 앞 BOM·내용 사이 BOM, 물리 행·표/PDF 좌표 보존.
- BOM을 포함한 저장 원문에서도 의미 있는 행만 국문 기준자료에 전달되는 공식 경로를 검증한다.
- 의미 있는 행이 실제로 빠진 경우에는 기존 strict 누락 검사와 재시도 실패 조건을 유지한다.
- 같은 기준선 재실행, 공식 Django 검사, 고정 보호 검사, Ruff·diff·catalog 갱신을 수행한다.
- code-review-loop는 기준 base `dd65eed0`과 이번 프로그램/테스트 3파일 diff 및 직접 소비자만 주 에이전트가 리뷰한다.
- 실제 원본 전체 AI 처리와 후보자 저장 검증의 범위·성공 여부는 자동검사와 구분해 기록한다.

## 실제 원본 대조

| 입력 | 수정 전 공식 AI 추출 | 수정 후 공식 AI 추출·후보자 투영 |
|---|---|---|
| 원래 실패 DOC | 26.74초 뒤 같은 `L0001` 누락 오류 | 44.74초, 이름·이메일·전화 및 경력 6건·학력 2건 생성 |
| 기존 저장 성공 PDF | 21.26초, 정상 지식 생성 | 22.70초, 정상 지식·후보자 투영 생성 |

- 기존 성공 파일의 이름·이메일·전화는 전후 같고, 경력 3건·학력 2건도 유지됐다.
- 실처리는 조회 전용 DB 연결에서 기존 `extract_resume_knowledge_from_text`와 `candidate_profile_from_knowledge`를 사용했다. 운영 저장·큐 초기화·Drive 쓰기는 하지 않았다.
- 비공개 실제 원문과 생성 자료는 서버 `.debug/resume-bom-20260916/`의 0600 파일에 보관했다. Git·문서·채팅에는 원문·연락처·비밀값을 넣지 않았다.
- 변경 후 고정 보호 18파일, Django check, Ruff, diff check, catalog current/valid 검사를 통과했다.
- 공용 테스트 잠금은 별도 Hermes 평가 종료 뒤 정상 해제됐다. 잠금·검사·다른 작업을 우회하거나 중단하지 않았다.
- 수정 후 같은 기존 검사와 BOM 회귀 20개: **197 passed, 5 warnings**.
- 공식 `scripts/debug_workspace.sh contracts`: **216 passed, 26 warnings**, 고정 보호 18파일 보존.
- 실제 원본에서 생성한 지식·후보자 자료를 공식 `text_to_pipeline_result` → `save_pipeline_result`에 전달한 개발 테스트 DB 저장 검사: **1 passed, 3 warnings**. Candidate/Resume 생성, FileData의 저장 완료·후보자 연결, Candidate의 현재 이력서·파일 상태 연결, 원문 및 경력 6건·학력 2건 저장을 확인했다.
- 저장 검사는 이미 실제 AI 호출로 검증한 외부 단계의 결과만 재사용했다. 운영 DB 저장이나 전체 운영 worker 재실행의 증거로 대신하지 않는다.
- 마지막 운영 조회: 원래 `updated_at`과 텍스트 SHA-256 유지, 후보자 연결 없음, Resume 0건, 저장 완료/구조화 JSON 없음, 실패 횟수 3회와 큐 종료 상태 유지.
- 메모리에서 이 FileData의 `retryable`/`needs_resume_processing`만 true로 바꾼 공식 `classify_next_action`은 재처리 가능을 반환했다. 실패 이력을 임의 삭제하거나 운영 값을 바꾸지 않은 재개 준비 검증이다.

## 운영 배포 — 2026-09-16 19:57 KST

- 주인님의 “운영 배포” 승인 후 공식 `scripts/deploy/deploy.sh prod`가 19:57:24 KST `prod ok 87683dae`/exit 0으로 완료됐다.
- GitHub main/origin main, 운영 clean main, debug clean detached HEAD, 실행 app/SSE/notification의 `/app/.source-commit`은 모두 `87683dae905f56676bb6f0d4b9916c2d86bcfb0d`로 일치했다.
- 이전 운영 dd65eed0에서 이번 BOM 프로그램/테스트 3파일만 fast-forward 반영했다.
- 새 이미지 `exdigm_app:20260916195601`; 실행 3종의 이미지 ID는 모두 `sha256:4a7b33bee3903f874c0343871cd60ff450b029792c5dbe4748e80f813a628386`다. 두 프로그램 파일의 실행 SHA-256도 검증 판본과 같다.
- 새 이미지의 DOC/DOCX/PDF 실제 파일 전달 계약과 고정 보호 18파일을 통과했다. Django/Nginx 검사도 정상이다.
- 서비스 5개 1/1, app/SSE/notification update completed, 작업자·지원 프로세스 11개 active/jobs 0/drain off, 운영 read-write 명령과 새 PID를 확인했다. HTTPS는 200이다.
- 조회 전용 배포 전후 FileData 전체 행의 해시와 Resume 0건이 같았다. 원본의 본문·실패 3회·종료 큐·후보자 연결 없음 상태를 보존했다.
- 이번 배포는 종료된 파일의 수동 재처리 상태를 바꾸지 않았다. 후보자·이력서 실제 등록은 이 파일 1건 재처리 후 따로 확인해야 한다.
- 비공개 증거: `.debug/resume-bom-20260916/deploy-before-filedata.json`, `deploy-after-filedata.json`, `deploy-runtime-after.json` (0600). 실제 원문·연락처·비밀값은 Git·문서에 포함하지 않는다.

## 코드 리뷰 계약과 결과

- 원천: 주인님의 “수정해”, 위 목표·보호 조건, 변경 전 공식 디코딩·원문 행 생성·strict 누락 검사.
- 상위 목적: 내용 없는 인코딩 표시를 정상 원문으로 넘기지 않으며, 모든 의미 있는 이력서 행을 추출·저장에 전달한다.
- 경계: base `dd65eed0`, 프로그램 2파일과 `tests/test_resume_bom.py`, 디코더의 직접 독자와 원문 행·국문 기준자료 소비자.
- 입력: UTF-8/기존 fallback 인코딩의 문서 바이트, 보관 원문의 별도/접두/중간 BOM, 실제 물리 행에 연결된 Word/PDF 좌표.
- 절차: BOM 제외 후 기존 디코딩·행 번호/좌표 연결·언어 판정·번역·누락 복구·strict 검사 순서를 유지한다.
- 출력: BOM만 있는 행에는 source id를 주지 않으며, 의미 있는 내용·순서·좌표와 실제 내용 누락의 실패 계약은 유지한다.
- 보호·비목표: 모델·프롬프트·AI 호출 추가·신원/저장/재시도·운영 데이터·다른 게시 코드·보호 파일 및 pin/ref를 바꾸지 않는다.
- 관점: 변경 diff와 직접 호출/소비 관계만 검사한다. 새 디코딩은 BOM 없는 UTF-8 및 fallback을 유지하며, 행마다 BOM을 제외하므로 물리 행과 배치 인덱스는 이동하지 않는다.
- 주 에이전트의 마지막 단일 code-review pass: 승인 finding 0개, material contract question/계약 변경 질문 0개. 잠근 범위의 필수 검증이 모두 통과해 code-review-loop를 완료했다.

## 재개 정보

- 상태: 프로그램 두 줄 수정·회귀 20개·실제 원본 전후 대조·정적/보호 검사·직접 리뷰·공식 자동검사·개발 DB 저장 검사 완료.
- 공유 worktree의 잡코리아 작업이 주인님의 별도 배포 승인을 받아 dd65eed0 배포를 요청했다. BOM 세 파일만 stash `bba73edd6800fc8f82d30fa1a21c9c8b42c446ae`에 보존해 HEAD를 바꾸지 않고 clean 상태를 인계했다.
- 보존 파일과 SHA-256 manifest는 비공개 `.debug/resume-bom-20260916/tested-change-backup/`에도 따로 보관했다. 잡코리아 작업에는 clean/HEAD/stash 상태를 회신했다.
- 검증 때의 세 파일과 SHA-256이 같은 Git tree로 수정 커밋 `87683dae905f56676bb6f0d4b9916c2d86bcfb0d`를 만들었다. parent는 dd65eed0, 보존 ref는 `refs/heads/fix/resume-bom-20260916`다. Git의 별도 임시 index로 만들었으며 공유 HEAD·index·worktree는 dd65eed0 clean 상태를 유지했다.
- 잡코리아 작업이 2026-09-16 19:03:41 KST `prod ok`/exit 0과 원래 데이터 보존 검증 완료를 회신했다. 이번 BOM 변경은 그 운영 배포에 포함되지 않았다.
- 해제 회신 후 공식 debug를 `87683dae` clean detached HEAD로 복원했다. 세 파일은 검증 때 SHA-256과 같고 보호 18파일 및 catalog current/valid를 다시 확인했다. stash와 비공개 사본은 보존했다.
- 현재 운영 checkout/GitHub/실행 앱은 `87683dae`, debug도 같은 clean detached HEAD다. 19:57:24 KST 공식 배포와 실제 runtime 검증을 완료했다.
- 잡코리아와 Hermes의 문서 부분 커밋이 끝나 index를 해제했다. 이번 계획과 README의 BOM 항목만 범위 커밋하며 다른 작업의 내용은 포함하지 않는다.
- 다음 운영 작업: 이 FileData 1건 재처리에 대한 주인님 승인 → 운영 원문/상태/신원 재확인 → 백업 유효성 확인 → 해당 파일만 정상 updater 큐로 복귀 → FileData/Resume/Candidate 저장과 현재 연결 확인.
- 운영 배포는 승인·완료했다. 이 FileData 1건의 수동 재처리 상태 변경은 실행하지 않았다.
- 공식 controlroom push는 동시 작업의 범위 커밋이 모두 끝나 전체 clean을 확인한 뒤 잡코리아 작업이 한 번 담당하기로 조율했다. BOM 애플리케이션 push/배포는 이 문서 동기화와 별개다.
