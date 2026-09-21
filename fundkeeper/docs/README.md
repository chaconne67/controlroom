# fundkeeper 조정실 문서

현재 조정실은 `~/controlroom/fundkeeper`입니다. 실제 서버·코드·DB·GitHub 위치와 운영 경계는 [프로젝트 지침](../AGENTS.md)을 우선합니다.

디자인 시스템·실행 전략·계약·실제 화면 템플릿·제품 Codex 런타임은 서버에 유지합니다.

2026-09-13에 보관 위치를 정리했습니다. 문서의 작성일·승인 상태·폐기 여부는 바꾸지 않았습니다. 원문 속 코드·명령 경로는 원래 서버 저장소 기준이며, 이전 위치와 SHA-256은 루트 provenance.json에 있습니다.

## 문서

- [투자성향 설문 감점 배점안](<plans/2026-09-21-investor-questionnaire-negative-scoring.md>) — 연령·경험·지식·손실감내·지출 의존·운용기간의 음수 배점을 정하고 기존 64점 환산·성향 구간으로 계산을 검증한 설계안입니다. 프로그램·별첨·운영 사이트에는 아직 적용하지 않았습니다.
- [투자성향 설문 최종 문구·심사 기준 대응](<plans/2026-09-21-investor-questionnaire-final-wording.md>) — 심사 항목을 유지하고, 13문항의 선택지를 타사 공개 설문과 대조해 정리합니다. 배점·환산·성향 구간·최종 판정 제한은 기존 그대로입니다. 최종 반영 및 검증 상태는 이 문서가 정본입니다.
- [투자자 프로파일링 전체 문항 의미 검토 이력](<plans/2026-09-21-investor-questionnaire-semantic-review.md>) — 앞선 의미 검토와 미채택 재구성안의 기록입니다. 최종 범위는 위 최종 문구 문서를 따릅니다.
- [2026-09-18 프로파일링 문구 최소 수정 이력](<plans/2026-09-18-investor-questionnaire-consistency-plan.md>) — 당시 네 문구 중심의 변경·검증·푸시 기록입니다. 최신 전수검토와 범위는 위 2026-09-21 문서를 따릅니다.
- [운영서버 통합 기록](../../.controlroom/docs/production-server-consolidation-20260916.md) — main `chaconne@49.247.192.127`로 운영 인계가 완료됐습니다. 최신 적용·복구 절을 확인합니다.
- [2026-09-17 테스트베드 알고리즘 심사 발표 자료](<plans/2026-09-17-testbed-algorithm-review-pt-plan.md>) — 국내ETF·퇴직연금 레시피(1336~1339, 1342, 1343) 심사 PT. HTML은 [presentations/2026-09-testbed-algorithm-review](<presentations/2026-09-testbed-algorithm-review/index.html>)(4차 수정본 26장), PDF는 Drive `MOA/테스트베드3차/심사발표자료`에 있으며 `_v4` 파일이 최신입니다.
- [2026-03-10-chatbot-enhancement-design.md](<plans/2026-03-10-chatbot-enhancement-design.md>)
- [2026-03-10-chatbot-implementation-plan.md](<plans/2026-03-10-chatbot-implementation-plan.md>)
- [2026-07-29-mix-losscut-next-day-execution-plan.md](<plans/2026-07-29-mix-losscut-next-day-execution-plan.md>)
- [2026-07-31-split-order-execution-plan.md](<plans/2026-07-31-split-order-execution-plan.md>)
- [2026-08-01-certbot-domain-and-stack-recovery-plan.md](<plans/2026-08-01-certbot-domain-and-stack-recovery-plan.md>)
- [2026-08-09-fundkeeper-design-system-skill-plan.md](<plans/2026-08-09-fundkeeper-design-system-skill-plan.md>)
- [BAA_UPGRADE_PLAN.md](<../portfolio_baa/files/BAA_UPGRADE_PLAN.md>)
- [BAA_UPGRADE_TODO.md](<../portfolio_baa/files/BAA_UPGRADE_TODO.md>)
- [KRX_plan.md](<../xmodules/research/plan/KRX_plan.md>)
- [fundkeeper_testbed_improvements.md](<../xmodules/test_bed/fundkeeper_testbed_improvements.md>)
