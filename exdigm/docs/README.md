# exdigm 조정실 문서

현재 조정실은 `~/controlroom/exdigm`입니다. 실제 서버·코드·DB·GitHub 위치와 운영 경계는 [프로젝트 지침](../AGENTS.md)을 우선합니다.

운영 코드는 /home/chaconne/exdigm입니다. 원문에 적힌 코드·명령 상대 경로는 해당 서버 저장소 기준입니다.

2026-09-13에 보관 위치를 정리했습니다. 문서의 작성일·승인 상태·폐기 여부는 바꾸지 않았습니다. 원문 속 코드·명령 경로는 원래 서버 저장소 기준이며, 이전 위치와 SHA-256은 루트 provenance.json에 있습니다.

## 진행 중 작업

- [Mailplug 앱 비밀번호 변경 뒤 계정 접속 실패의 오류장부 기록 — 개발 커밋·검증 완료, 운영 배포 승인 대기](operational-error-alerts-20260914.md)

- [혼합 언어 이력서 추출 오류 60ead5b9 — 수정·검증·운영 반영 승인, 샘플 확인으로 후보자 등록 제외·공유 서버 정리 완료 대기](resume-mixed-source-error-20260921.md)

- [전체 시스템 보안 점검 — 내부 보고서·개선 계획 보관 안내](security-audit-20260920.md)

- [이력서 검수 마크다운 표시 — 개발 수정·실제 화면·보호 검사 완료, 운영 배포 승인 대기](markdown-display-fix-20260918.md)

- [학력 선택 정책 — 운영 반영·실패 개인 이력서 4건 재처리·실제 저장 및 중요 표시 확인 완료](resume-optional-education-20260917.md)

- [이력서 번역 요청 오류 2건 — 수정·운영 배포·지정 원본 재처리 및 저장 확인 완료](resume-provider-errors-20260917.md)

- [이력서 BOM 처리 수정 — 운영 배포·중단 파일 재처리·실제 저장 완료](resume-bom-fix-20260916.md)

- [Hermes MCP 조회 개선 — 직원 6명 운영 반영·기록 보존 완료, 시간대·인증값 후속은 별도](hermes-mcp-read-improvement-20260916.md)

- [LinkedIn 문자·이메일 인증 — LinkedIn만 운영 배포 완료, 실제 받은 코드 확인 대기](linkedin-verification-20260916.md)

- [자동게시 에이전트 — 잡코리아 운영 배포 완료, 실패 공고 재시도는 미실행](jobkorea-adaptive-workplace-20260916.md)

- [운영 오류 문제해결 — 배포 정리·파일 수집9건 복구, 후속 내용 추출·메일·개인 연결 잔여](operational-errors-fix-20260915.md)

## 최근 완료 작업

- [메일 분류 Codex Luna CLI·Gemini 3.8 폴백 — 운영 반영·실제 분류·폴백 및 오류 DB 기록 검증 완료](mail_classifier_gemini_fallback_plan_20260729.md)

- [자동게시 간결 제목·익명 소개20자·여섯 사이트 제약 — 운영 반영·활성5사이트 최종 입력·원본 보존 확인](incruit-title-limit-alerts-20260918.md)

- [이력서의 정해진 접수 실패·담당 컨설턴트 보완 안내 — 운영 반영·본문 이메일 링크·지정 원본 종결·웹 알림 1회 전송 확인](resume-expected-rejection-notification-20260918.md)

- [자동게시·오류 기록·명단 판정·Hermes 합동 배포 — de20cf82 운영 반영·733개 검사·6명 실제 조회 확인](auto-posting-other-sites-20260916.md)

- [오류 기록 한국 시간·처리 결과 — 운영 반영·과거 오류 보존 완료](operational-error-time-results-20260916.md)

- [Drive 추천인재 목록 제외 — 운영 반영 완료, 과거 실패 행은 보존](resume-roster-error-20260916.md)

- [운영 오류·작업 실패 DB 기록 — 운영 배포·실제 DB 기록·메시지 없음 확인 완료](operational-error-alerts-20260914.md)

- [Hermes 기본 모델 3.8 Flash 갱신 — 직원 6개 운영 반영·도구 호출·보존 검증 완료](hermes-model-update-20260915.md)

- [김두영 후보자 이름·이력서 혼입 해결 — 운영 복구·재발 검증 완료](candidate-identity-mismatch-20260914.md)

- [자동 게시의 조기 실패 구조 개선 — 운영 반영·5개 사이트 입력 검증 완료](auto-posting-recovery-design-20260914.md)

- [잡코리아 게시 실패 해결 — 운영 배포·실게시 완료](jobkorea-industry-failure-20260914.md)

## 문서

- [auto_posting_consultant_profile_plan.md](<auto_posting_consultant_profile_plan.md>)
- [auto_posting_root_cause_fix_plan_20260806.md](<auto_posting_root_cause_fix_plan_20260806.md>)
- [auto_posting_status_visibility_plan.md](<auto_posting_status_visibility_plan.md>)
- [candidate_contact_search_plan_20260806.md](<candidate_contact_search_plan_20260806.md>)
- [client_industry_detail_select_plan_20260809.md](<client_industry_detail_select_plan_20260809.md>)
- [exdigm-introduction-video-script.md](<exdigm-introduction-video-script.md>)
- [exdigm-marketing-story-copy.md](<exdigm-marketing-story-copy.md>)
- [posting-spacing-review.md](<local/artifacts/posting-spacing-review.md>)
- [DEVELOPMENT-ACCESS.md](<local/DEVELOPMENT-ACCESS.md>)
- [candidate-search-ux-proposal-2026-09-08.md](<local/results/candidate-search-ux-proposal-2026-09-08.md>)
- [RESUME-INTAKE-20260911.md](<local/RESUME-INTAKE-20260911.md>)
- [mail_classifier_gemini_fallback_plan_20260729.md](<mail_classifier_gemini_fallback_plan_20260729.md>)
- [reputation_review_llm_plan_20260723.md](<reputation_review_llm_plan_20260723.md>)
