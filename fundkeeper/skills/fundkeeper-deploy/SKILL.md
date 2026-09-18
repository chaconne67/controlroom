---
name: fundkeeper-deploy
description: Use when deploying FundKeeper/Coconut or checking its Docker Compose deployment, production health, logs, or recovery state.
---

# FundKeeper 배포

현재 대상은 main `chaconne@49.247.192.127`, 실제 코드 저장소는 `/home/chaconne/projects/fundkeeper`, 기준 브랜치는 `master`다. 현행 연결·데이터·복구 계약은 프로젝트 AGENTS.md와 `/srv/consolidation/infra/README.md`를 먼저 확인한다.

운영 Compose는 `/srv/consolidation/infra/compose.production.coconut.json`과 `compose.activate.coconut.json`, 프로젝트는 `production-coconut`, 웹은 `production-coconut-web-1`, 프런트는 `production-coconut-nginx-1`이다. 캐시는 기존 예약 실행의 전용 이미지와 `compose.cache.coconut.json`을 사용한다.

## 배포 범위

주인님이 해당 코드 변경의 운영 배포를 요청했을 때 실행한다. 저장소 상태·diff·배포할 커밋·이미지와 현재 운영 컨테이너의 image/ID/StartedAt, 정본 DB·자료 경로를 먼저 확인한다. 기존 사용자 수정·미추적 파일과 다른 제품·예약 작업을 보존한다.

Compose는 고정된 이미지 ID를 사용한다. 코드 커밋만 바꾸고 `up`을 실행하면 새 코드가 배포되는 것이 아니다. 해당 변경의 정적 파일·이미지 빌드 경로를 실제 Dockerfile/기존 절차와 대조하고, 검증한 이미지 ID를 승인된 서비스 정의에만 연결한다. 기존 이미지 ID는 복구에 사용할 수 있도록 보존한다.

이전 Swarm 배포 스크립트와 전체 stack 제거·prune은 현재 실행 경로가 아니다. 전체 자동 stage/commit/push를 배포에 섞지 않는다. Git 저장과 운영 반영 결과를 별도로 확인한다.

## 운영 확인

- HTTPS `https://coconut.ai.kr/health/`의 본문 `ok`와 웹의 healthy, 프런트의 running을 확인한다.
- 변경된 실제 기능·화면을 공식 진입점에서 확인한다. 결제·증권 주문·외부 전송·유료 AI 시험은 해당 승인 범위에서만 실행한다.
- 실패하면 해당 제품의 로그·상태를 보존한다. 원인 확인 없이 재배포하지 않고, 현재 데이터·권한을 확인한 후 기존 제품별 복구 경로를 사용한다.
