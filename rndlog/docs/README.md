# rndlog 조정실 문서

현재 조정실은 `~/controlroom/rndlog`입니다. 실제 서버·코드·DB·GitHub 위치와 운영 경계는 [프로젝트 지침](../AGENTS.md)을 우선합니다.

운영 코드와 고객 자료·업로드 게이트웨이는 main에서 관리하며 위치는 위 지침을 따릅니다. 옛 계획은 현재 승인으로 해석하지 않습니다.

2026-09-13에 보관 위치를 정리했습니다. 문서의 작성일·승인 상태·폐기 여부는 바꾸지 않았습니다. 원문 속 코드·명령 경로는 원래 서버 저장소 기준이며, 이전 위치와 SHA-256은 루트 provenance.json에 있습니다.

## 문서

- [아성 문서 재작성 및 다운로드 등록 — 2026-09-18](plans/2026-09-18-asung-document-regeneration.md) — 새 제작·내부 다운로드 등록과 후속 기본정보 보완의 재개 기록.

- [담당자 역할 셀 편집 — 2026-09-17](plans/2026-09-17-member-role-inline-edit.md) — 이미지 2와 같은 역할 UI 및 HTMX 역할 셀 교체. 격리 환경 검증과 승인 후 운영 배포·실제 운영 편집 GET 확인 완료.
- [운영서버 통합 기록](../../.controlroom/docs/production-server-consolidation-20260916.md) — 대상 `chaconne@49.247.192.127`. 운영 인계는 2026-09-17에 완료됐습니다. 문서의 최신 적용 절과 현재 서버를 확인합니다.
- [2026-09-05-rndlog-admin-management-plan.md](<plans/2026-09-05-rndlog-admin-management-plan.md>)
- [2026-09-05-rndlog-admin-quality-bar.md](<plans/2026-09-05-rndlog-admin-quality-bar.md>)
- [2026-09-06-rndlog-file-upload-tree-plan.md](<plans/2026-09-06-rndlog-file-upload-tree-plan.md>)
- [2026-09-06-rndlog-upload-material-type-plan.md](<plans/2026-09-06-rndlog-upload-material-type-plan.md>)
- [2026-09-08-management-tab-improvement.md](<plans/2026-09-08-management-tab-improvement.md>)
- [company-lookup-quota-execution-plan.md](<plans/company-lookup-quota-execution-plan.md>)
- [corporate-funding-tm-plan.md](<plans/corporate-funding-tm-plan.md>)
- [design-rd-compliance-os.md](<plans/design-rd-compliance-os.md>)
- [implementation-plan.md](<plans/implementation-plan.md>)
- [landing-page-plan.md](<plans/landing-page-plan.md>)
- [2026-04-21-research-app-phase1.md](<superpowers/plans/2026-04-21-research-app-phase1.md>)
- [2026-06-09-marketing-pipeline.md](<superpowers/plans/2026-06-09-marketing-pipeline.md>)
- [2026-07-14-cretop-8004-recovery.md](<superpowers/plans/2026-07-14-cretop-8004-recovery.md>)
- [2026-07-14-cretop-click-marker-retry.md](<superpowers/plans/2026-07-14-cretop-click-marker-retry.md>)
- [2026-07-15-agents-skill-trigger-deduplication.md](<superpowers/plans/2026-07-15-agents-skill-trigger-deduplication.md>)
- [2026-07-15-cretop-company-failure-continue.md](<superpowers/plans/2026-07-15-cretop-company-failure-continue.md>)
- [2026-07-15-cretop-error-retry-exclusion.md](<superpowers/plans/2026-07-15-cretop-error-retry-exclusion.md>)
- [2026-07-15-cretop-expired-page-recovery-routing.md](<superpowers/plans/2026-07-15-cretop-expired-page-recovery-routing.md>)
- [2026-07-15-cretop-funding-reference-summary.md](<superpowers/plans/2026-07-15-cretop-funding-reference-summary.md>)
- [2026-07-15-cretop-smart-search-briefing-path.md](<superpowers/plans/2026-07-15-cretop-smart-search-briefing-path.md>)
- [2026-07-15-cretop-telegram-completion-notification.md](<superpowers/plans/2026-07-15-cretop-telegram-completion-notification.md>)
- [2026-07-15-cretop-telegram-stop-notification.md](<superpowers/plans/2026-07-15-cretop-telegram-stop-notification.md>)
- [2026-07-16-cretop-body-marker-tab-selection.md](<superpowers/plans/2026-07-16-cretop-body-marker-tab-selection.md>)
- [2026-07-16-cretop-concurrent-session-direct-ready-recovery.md](<superpowers/plans/2026-07-16-cretop-concurrent-session-direct-ready-recovery.md>)
- [2026-07-16-cretop-exception-router.md](<superpowers/plans/2026-07-16-cretop-exception-router.md>)
- [2026-07-16-cretop-info-stop-confirm-recovery.md](<superpowers/plans/2026-07-16-cretop-info-stop-confirm-recovery.md>)
- [2026-07-16-cretop-operator-stop-message.md](<superpowers/plans/2026-07-16-cretop-operator-stop-message.md>)
- [2026-07-17-cretop-generic-popup-fallback.md](<superpowers/plans/2026-07-17-cretop-generic-popup-fallback.md>)
- [2026-07-17-cretop-oom-exception-recovery.md](<superpowers/plans/2026-07-17-cretop-oom-exception-recovery.md>)
- [2026-07-24-cretop-generic-close-popup.md](<superpowers/plans/2026-07-24-cretop-generic-close-popup.md>)
- [2026-07-26-ceoloan-migration-phase1.md](<superpowers/plans/2026-07-26-ceoloan-migration-phase1.md>)
- [2026-07-26-funding-admin-handoff.md](<superpowers/plans/2026-07-26-funding-admin-handoff.md>)
- [2026-07-27-cretop-deferred-quality-retry.md](<superpowers/plans/2026-07-27-cretop-deferred-quality-retry.md>)
- [2026-07-30-cretop-local-primary-replication.md](<superpowers/plans/2026-07-30-cretop-local-primary-replication.md>)
- [2026-08-05-rndlog-ceoloan-clone.md](<superpowers/plans/2026-08-05-rndlog-ceoloan-clone.md>)
- [2026-08-08-funding-outbox-controls.md](<superpowers/plans/2026-08-08-funding-outbox-controls.md>)
- [2026-04-20-sample-documents-design.md](<superpowers/specs/2026-04-20-sample-documents-design.md>)
- [2026-06-09-marketing-pipeline-design.md](<superpowers/specs/2026-06-09-marketing-pipeline-design.md>)
- [2026-07-14-cretop-click-marker-retry-design.md](<superpowers/specs/2026-07-14-cretop-click-marker-retry-design.md>)
- [2026-07-15-cretop-expired-page-recovery-routing-design.md](<superpowers/specs/2026-07-15-cretop-expired-page-recovery-routing-design.md>)
- [2026-07-15-cretop-funding-reference-summary-design.md](<superpowers/specs/2026-07-15-cretop-funding-reference-summary-design.md>)
- [2026-07-16-cretop-info-stop-confirm-recovery-design.md](<superpowers/specs/2026-07-16-cretop-info-stop-confirm-recovery-design.md>)
- [2026-07-17-cretop-generic-popup-fallback-design.md](<superpowers/specs/2026-07-17-cretop-generic-popup-fallback-design.md>)
- [2026-07-24-cretop-generic-close-popup-design.md](<superpowers/specs/2026-07-24-cretop-generic-close-popup-design.md>)
- [2026-07-26-ceoloan-server-split-design.md](<superpowers/specs/2026-07-26-ceoloan-server-split-design.md>)
- [2026-07-26-funding-admin-handoff-design.md](<superpowers/specs/2026-07-26-funding-admin-handoff-design.md>)
- [2026-07-27-cretop-deferred-quality-retry-design.md](<superpowers/specs/2026-07-27-cretop-deferred-quality-retry-design.md>)
- [2026-07-30-cretop-local-primary-replication-design.md](<superpowers/specs/2026-07-30-cretop-local-primary-replication-design.md>)
- [2026-08-04-rndlog-ceoloan-clone-design.md](<superpowers/specs/2026-08-04-rndlog-ceoloan-clone-design.md>)
- [2026-08-08-funding-outbox-controls-design.md](<superpowers/specs/2026-08-08-funding-outbox-controls-design.md>)

- [작업공간과 서버 자료 경계](WORKSPACE.md)
