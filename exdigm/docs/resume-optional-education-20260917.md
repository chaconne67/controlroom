# 학력 미기재 이력서 생성·저장 정책 변경 — 2026-09-17

## 승인된 결과와 범위

주인님은 학력을 생성·저장의 필수조건에서 제외하고, 후보자 DB에 저장한 뒤 학력 누락을 중요한 데이터 이슈로 표시하도록 승인했다. 학력은 원문 근거가 없으면 빈 상태로 보존한다. 이름·후보자 연락처·경력, 신원 매칭, 현재 이력서 선택, 비이력서 제외, 원문·파일 정보 보존을 유지한다.

프로그램 수정·검증·리뷰·기록·커밋과 같은 오류 작업에서 앞서 명시된 운영 배포 지시를 적용한다. 현재 주인님의 명시적 학력 계약 변경 승인을 반영하며 운영 배포를 다시 승인받지 않는다. 이전 정확한 두 파일의 재처리 승인은 이번 추가 원본의 운영 재처리로 확대하지 않는다.

## 기준선과 공식 경로

- 운영 main과 debug detached HEAD는 `a5aa6b02e210f67e21856412174e8b70c2345b7b`, 두 체크아웃 모두 clean이었다.
- 조정실의 기존 `docs/production-server-consolidation-20260916.md` 수정은 보존한다.
- 원문 → 문서 분류 → D8 국문 추출·영문 번역·내용 검사 → 후보자 필드 변환 → 품질·저장 정책 → 공식 DB 저장 → Candidate 검토 사항 표시를 수정한다. 이메일 본문 접수와 복수 후보자 저장의 학력 필수조건도 같은 정책으로 맞춘다.
- 후보자 표시는 기존 `Candidate.review_notice_items`와 `_review_notice_section.html`을 재사용한다. 현재 DB 학력이 비어 있으면 중요 표시를 계산하고, 보완 후 즉시 해제한다. 별도 DB 필드·보고서·위험 판정을 추가하지 않는다.
- 최소 구현 게이트: 2단계에서 멈춤. `rg`로 `validate_extracted_content`, `classify_resume_data`, `build_data_quality`, `compute_overall_confidence`, `save_pipeline_result`, `review_notice_items`, `_selected_body_resume_text`, `resume_rejection_reasons` 및 직접 호출·검사를 확인했다. 기존 역할을 재사용하고 학력에 한정된 조건만 변경한다.
- AI는 문서 의미 판정과 원문 내용 추출·번역을 담당한다. 스크립트는 구조·필수 근거·저장·화면 전달을 담당한다. 원문에 없는 학력을 만들지 않는다.

## 수정 전 검증

공식 `scripts/debug_workspace.sh test`로 저장 정책, 후보자 gate, 추출 공통, 후보자 모델, 업로드, knowledge, updater, 수동 후보자 생성, 정합성, 기본 추출 계약, Step1 검증의 기존 337개가 통과했다. 새 정책 검사에서 학력 누락의 품질 오류·생성 중단·저장 거절·메일 접수 거절을 확인했다. 새 검사 초기 작성의 호출 인자·source_status·placeholder fixture 오류를 바로잡아 프로그램의 실제 거절을 확인했다.

## 구현 결과

학력 미기재를 D8 내용 검사·저장 판정·후보자 gate·메일 본문 선택·복수 후보자 처리에서 거절하지 않는다. 학력 품질 점수는 0으로 보존하되, 선택 정보 부재만으로 전체 신뢰도를 낮추지 않는다. 이름·후보자 본인 연락처·실질적 경력과 다른 품질 조건은 유지한다.

학력이 비어 있는 현재 후보자는 기존 검토 사항에 `중요 — 학력 정보 없음`과 `학력 정보 없음: 후보자에게 학력 정보를 확인해주세요.`를 표시한다. 현재 DB의 학력 관계를 읽어 계산하므로 학력을 보완하면 즉시 해제된다. 별도 누락 필드·DiscrepancyReport·위조 판정·수동 운영 보정을 추가하지 않았다.

## 실제 원본과 검증 결과

- 학력 누락으로 종료된 FileData `f0aab420-a0a7-43d0-895d-ec2d746ba5e7`의 실제 PDF와 보관 텍스트가 일치했고, 학력 출처 지도도 비어 있었다. 수정된 공식 D8·필드 변환 경로의 실제 AI 실행은 32.11초, 경력 2건/학력 0건, 저장 정책 NORMAL/AUTO_SAVE였다. 별도 역량 품질 점수로 진단 fail/0.833이지만 기존 save_flagged 정책으로 저장된다. 학력 누락이 필수조건 실패로 처리되지 않음을 실제 결과로 확인했다.
- 기존 정상 PDF의 실제 AI 실행은 20.12초, 경력 3건/학력 2건, 품질 usable/신뢰도 1이었다. 기존 6개 신원·인구통계·연락처 값은 유지됐다.
- 위 두 실제 AI 결과를 공식 개발 전용 테스트 DB에서 FileData→Pipeline→Candidate/Resume 저장 경로로 재생했다. 2건 모두 DB 저장·현재 이력서 연결·db_saved 큐 종료와 실제 후보자 상세 뷰 전달을 확인했다. 운영 통합 인증은 테스트 환경에 공급하지 않았다.
- 새 학력 정책의 15개 검사에서 학력 None/빈 배열/빈 항목, 이름·연락처·경력 누락, 학력 없는 저장·중요 표시·학력 보완 후 해제, 복수 후보자, 메일 본문과 외부 서명 연락처 거절을 확인했다. 합성 메일 본문은 실제 분류 AI 응답과 공식 guard·본문 선택을 통과했으며 실제 메일을 보내지 않았다.
- 기존 337개와 새 15개 직접 영향 검사는 모두 통과했다. 확장 검사 415개 중 413개가 통과했다. 나머지 2개는 기존 프로젝트 생성 화면 문구와 생성 후 이동 주소 기대값이며, 변경 전 clean a5aa6b02의 같은 검사에서도 실패했다. 이 작업에서 해당 기능·기존 검사를 완화하지 않았다.
- 승인 보호 검사 216개 통과, pin `6dd406439be5a52d5ce1f1660ebd05ca621df715` 및 보호 18파일 유지, Django check·Ruff·diff 검사와 catalog_update current/local valid·broken references 없음 확인. 메인 에이전트 code-review-loop 9개 계약 항목에서 추가 수정 finding이 없었다. 변경한 data-extraction 스킬도 skill-review와 UTF-8 validator를 통과했다.
- 공식 `runserver`의 개발 HTTPS 후보자 화면을 공용 숨김 Chrome으로 직접 확인했다. 빨간 `중요 1건`과 학력 확인 안내가 표시됐다. 이 작업의 runserver·Chrome은 종료했고 프로필과 기존 사용자 작업을 보존했다.

## 운영 반영과 현재 상태

- 기존 같은 오류 작업의 운영 배포 승인과 현재 학력 계약 변경 승인을 적용해 `scripts/deploy/deploy.sh prod`를 실행했다. 2026-09-17 14:49:26 KST에 `prod ok 4df3adb6`, exit 0으로 완료됐다.
- 최종 앱 커밋 `4df3adb6663df138ac4a07c2813095ae0f43576a`, 이미지 `exdigm_app:20260917144803`, SHA `6e3a1a9344d568b10a9f37a694f0d230de5a72f3e26d8052ce8f17cafeb6bc04`. origin/main·운영 clean main·debug clean detached가 같은 커밋이며 실제 app/SSE/notification source commit과 변경 프로그램 10파일 해시가 검증된 debug 코드와 일치했다.
- 서비스 5개가 1/1이고 작업자·지원 프로세스 11개가 active/drain off였다. 실제 updater는 `exdigm-update-candidate-worker.service`, PID296852, `main.settings.deploy`, 드라이런 없음으로 실행됐다. 운영 HTTPS 200과 새 이미지의 문서 계약 검사를 확인했다. DB 인프라·Hermes·서버 이전은 변경하지 않았다.
- 운영 DB의 실제 학력 없는 기존 후보자에서 중요 학력 누락 항목이 계산됨을 공식 읽기 전용 경로로 확인했다. 기존 숨김 운영 Chrome 프로필은 유효한 로그인 세션이 없어 로그인 화면까지만 확인했다. 운영에서 인증된 후보자 화면의 브라우저 확인은 미완료이며, 개발의 동일 화면 직접 확인과 운영 코드·DB 표시 계산 검증을 구분한다. 운영 Chrome은 종료했고 입력 데스크톱·전경은 유지됐다.
- 추가 실패 원본 `f0aab420-a0a7-43d0-895d-ec2d746ba5e7`은 운영에서 종료·미저장 상태를 그대로 보존했다. 실제 AI 검증 전후 및 운영 배포 후의 원본 FileData/Resume 전체 행 snapshot SHA가 `18521c9ba833c4e50ed352ce592e93dfa56f9c7d9003c8d85e09e3ea8b54bb5a`로 동일했다. 기존 OperationalError도 수동 해결 처리하지 않았다.

## 재개 범위

### 2026-09-17 추가 운영 재처리 승인과 기준선

주인님이 “실패한 이력서 재처리해”라고 지시했다. 현재 대화에서 다룬 미복구 개인 이력서 4건인 b3240e24-4cfd-45ca-89da-ca41d97f630e, c5610307-98e2-4300-a8a0-9c5de26d3042, 6c26ff02-ec48-4535-8e48-2afbb9f00458, f0aab420-a0a7-43d0-895d-ec2d746ba5e7을 운영 재처리한다. 이미 복구된 aadcafd0/f371c4d3와 비이력서 추천 명단 3892ff70, 대화 밖의 다른 종료 건은 제외한다.

- 새 기준선: 운영 clean main·debug clean detached 모두 4df3adb6663df138ac4a07c2813095ae0f43576a다. 공식 read-only에서 대상 4건은 single_resume/included, Resume 0건·후보자 미연결·미저장·종료 큐·processing false를 확인했다.
- 실제 AI 결과를 기존 strict identify_candidate로 조회했다. c5610307/6c26ff02는 같은 기존 후보자 90276193-0b8a-44a4-9d8c-39b3ded15b35에 이메일로 매칭된다. b3240e24/f0aab420은 기존 매칭이 없다. 이름만으로 병합하지 않는다.
- 보호: 원문·ResumeSourceArtifact 전체 행·파일 ID/이름/MIME/크기/폴더/Drive 기준시각·기존 수동 필드·기존 성공 두 건·추천 명단·대상 밖 종료 행, 코드와 실행 중인 다른 작업을 보존한다. 후보자 현재 원본은 기존 날짜/선택 정책에 맡긴다.
- 최소 구현 게이트: 2단계에서 멈춤. 코드 지도와 실제 runners.py의 load_succeeded_rows/text_to_pipeline_result/save_pipeline_to_db, realtime_txt_to_db.Command, 기존 private production-reprocess-workspace, scripts/render_secret_env.py와 run_workers.sh drain을 확인해 재사용한다. 일회성 백업은 Django serializers를 사용한다. 새 제품 코드·함수·의존성·권한은 만들지 않는다.
- 공식 경로: 정확한 4건만 담은 private manifest의 원문/추출기 원문·metadata → 배포된 운영 checkout의 기존 realtime 명령 → 문서 판정/D8/후보자 변환/정책/공통 저장. force는 지정한 종료 원본 선택만 재개하며 문서·필수 정보·신원·저장 검사는 유지한다.
- 검증: 원본·대상 후보자·직접 연결 행과 수동 값의 복구 가능한 백업 및 해시를 확인한다. 기존 배포 잠금과 공식 DB 추출 잠금을 사용하며, 자동 updater를 drain하고 진행 작업 종료 후 실행한다. 실제 FileData structured/db_saved, Resume saved 및 후보자 연결, 실패 해제·큐 종료, f0aab420 학력 0/중요 표시를 read-only로 확인한다. 마지막에 본 작업이 걸었던 drain만 해제한다.

### 추가 운영 재처리 결과 — 2026-09-17 15:07 KST

- 공식 실행 `failed-resume-reprocess-20260917-approved-four`, DataExtractionExecution `ad2d1079-2f1f-4eaf-b71a-e20a0eb0c078`는 15:05:02~15:07:25 KST, succeeded/processed_count 4/failed_count 0, 실제 결과 성공 4·실패 0·누락 0으로 끝났다. 실제 AI를 새로 호출했으며 cold workspace의 정확한 manifest 4개, force, workers 1, limit 4를 사용했다. force는 필수 정보·문서·신원·저장 검사 우회가 아니다.
- 원본·대상 후보자·직접 연결 행·원래 오류의 복구 가능한 직렬화 백업 52행을 보관했다. SHA `4b66d1e909dcc7a9d5de121be08fe326aaf45298080cfa660d7d53f3dfcc20e3`를 확인했고, 실행 직전 read-only 재조회에서 52행 전체와 정확한 대상 manifest를 확인했다.
- b3240e24: 새 후보자 `53b83148-bbce-4a48-bb88-fc03d73789ff`, Resume `8342633b-597d-408d-b344-6aaa28ed7e87`, 경력 6/학력 2, 운영 저장 완료.
- c5610307: 기존 후보자 `90276193-0b8a-44a4-9d8c-39b3ded15b35`, Resume `90064ac6-0ed1-43e6-bb06-f67a146cacd9`, 경력 5/학력 4, 운영 저장 완료.
- 6c26ff02: 같은 기존 후보자, Resume `30eb3e29-9687-453a-9eb8-f0a0c90566f7`, 경력 5/학력 3, 운영 저장 완료. 기존 공식 기준에 따라 현재 후보자는 이 Resume/FileData를 선택했고 두 원본의 구조화 JSON은 각각 남았다.
- f0aab420: 새 후보자 `32955bdb-b009-485b-82e6-25cd519c8de8`, Resume `28337f22-59f2-4c3a-8376-4f7c8a8a15be`, 경력 2/학력 0, 운영 저장 완료. 후보자 DB 학력 관계도 0건이며 `MISSING_EDUCATION` RED/중요 표시를 확인했다. 원문에 없는 학력은 만들지 않았다.
- 공식 read-only에서 4건 모두 FileData structured·db_saved_at·실패 사유 해제·db_saved 종료 큐, Resume saved·후보자 연결·현재 Resume/FileData 일관성을 확인했다. 대상 원문·파일 ID/이름/MIME/크기/폴더/Drive 시각·유입 경로와 ResumeSourceArtifact 전체 행을 보존했다.
- 제외한 8건의 FileData/Resume/SourceArtifact 전체 직렬화 행은 전후 동일했다. SHA `2af1039a3946943050730ab3d5c94a43d94b01e86555641bd71a8fd4dbf4d906`. 기존 매칭 후보자의 manual provenance 필드는 0개였고 값 비교는 유지했다. 이미 복구된 두 파일과 비이력서 추천 명단은 재실행하지 않았다.
- 실제 저장 확인 뒤 기존 `record_processing_result`로 관련 OperationalError 3건에 성공 결과를 각각 1회 추가했다. 6c26ff02에는 별도 오류 행이 없어 같은 이메일의 c5610307 결과에 두 파일 복구를 함께 기록했다. 원래 발생 시각·오류 메시지·본문·traceback·context는 전후 동일하며 처리 상태/이력/updated_at만 변경됐다.
- 초기 SSH 셸 전달 마지막 빈줄에 Windows CR 문자가 붙어 부모 전달 스크립트만 exit 1이었다. 공식 realtime 모듈과 DB 실행 및 실제 저장은 성공했다. trap으로 본 작업의 drain이 해제됐으며 후속 전달은 CR을 정규화해 exit 0으로 실행했다. 저장된 4건을 반복 처리하지 않았다.
- 자동 updater는 정상 active/drain off로 재개됐고 작업자·지원 프로세스 11개 active, 서비스 5개 1/1, HTTPS200을 확인했다. 운영 clean main과 배포 코드 4df3adb6는 유지했다. 이번 재처리는 코드·권한·모델·배포를 바꾸지 않았다.

본 승인 범위의 4건 운영 복구와 보호 검증은 완료했다. 종료 큐를 일괄 재개하거나 이 대화 밖의 실패 건으로 확대하지 않는다. 비공개 백업·manifest·원문·실제 로그·production-verification·오류 결과·closing-readonly 검증은 `/home/chaconne/exdigm-debug/.debug/failed-resume-reprocess-20260917/`(0700/0600)에 보관한다. 아래는 새 재처리 승인 전의 기록이다.

정책 변경과 운영 배포는 완료했다. 이전에 지정된 정확한 두 파일 재처리는 앞선 작업에서 이미 끝났으며 반복하지 않는다. 이번에 추가 발견된 학력 없는 원본의 운영 재처리는 별도 범위다. 주인님이 위 FileData 한 건의 운영 재처리를 지시하면 원본·대상·연결 행의 복구 가능한 백업과 기준선 비교를 마친 뒤 배포된 커밋의 기존 공식 재처리 경로로 실행하고 Candidate/Resume 저장·중요 표시·원문 및 metadata 보존을 읽기 전용으로 확인한다. 다른 종료 원본으로 확대하지 않는다.

비공개 검증 원문·AI 결과·테스트 로그·뷰 HTML·배포 로그는 서버 `/home/chaconne/exdigm-debug/.debug/optional-education-20260917/`에 보관하며 Git·GBrain에 개인 원문과 비밀값을 넣지 않는다. 현재 정책의 공용 정본은 `project/exdigm-extraction-pipeline`, 배포 정본은 `project/exdigm-deploy-workflow`다.
