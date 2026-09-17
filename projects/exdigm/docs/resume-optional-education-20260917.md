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

정책 변경과 운영 배포는 완료했다. 이전에 지정된 정확한 두 파일 재처리는 앞선 작업에서 이미 끝났으며 반복하지 않는다. 이번에 추가 발견된 학력 없는 원본의 운영 재처리는 별도 범위다. 주인님이 위 FileData 한 건의 운영 재처리를 지시하면 원본·대상·연결 행의 복구 가능한 백업과 기준선 비교를 마친 뒤 배포된 커밋의 기존 공식 재처리 경로로 실행하고 Candidate/Resume 저장·중요 표시·원문 및 metadata 보존을 읽기 전용으로 확인한다. 다른 종료 원본으로 확대하지 않는다.

비공개 검증 원문·AI 결과·테스트 로그·뷰 HTML·배포 로그는 서버 `/home/chaconne/exdigm-debug/.debug/optional-education-20260917/`에 보관하며 Git·GBrain에 개인 원문과 비밀값을 넣지 않는다. 현재 정책의 공용 정본은 `project/exdigm-extraction-pipeline`, 배포 정본은 `project/exdigm-deploy-workflow`다.
