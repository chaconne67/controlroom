# rndlog 조정실 문서

코드·실행 위치: `chaconne@49.247.207.147:/home/chaconne/rndlog-dev`.

운영 코드는 /home/chaconne/rndlog입니다. DB의 고객자료·업로드 게이트웨이와 기존 개발 변경은 유지합니다. 옛 계획은 현재 승인으로 해석하지 않습니다.

2026-09-13에 보관 위치를 정리했습니다. 문서의 작성일·승인 상태·폐기 여부는 바꾸지 않았습니다. 원문 속 코드·명령 경로는 원래 서버 저장소 기준이며, 이전 위치와 SHA-256은 루트 provenance.json에 있습니다.

## 문서

- [진행 중: 새 운영서버 통합](../../../docs/production-server-consolidation-20260916.md) — 대상 `chaconne@49.247.192.127`. 현재 웹은 `49.247.207.147`, DB·자료 정본은 `49.247.45.243`입니다. 2026-09-16 실제 운영 DB는 `company_main`으로 확인했습니다. 자료 SSH 게이트웨이·업로드·문자 예약 작업의 인계가 끝나기 전에는 정본이 이동했다고 판단하지 않습니다.
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
