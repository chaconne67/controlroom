# FundKeeper 중앙 조정실

## 조정실

- 작업 위치는 이 프로필을 연결한 현재 프로젝트 폴더이며 기본값은 `~/projects/fundkeeper`입니다. `~`는 Windows의 `USERPROFILE`, macOS·Linux의 `HOME`입니다. 이미 등록된 사용자 지정 경로를 우선합니다.
- 개발 에이전트는 선택한 조정실 장비에서만 실행합니다. 아래 서버의 코드·Git·검증·배포 경로는 SSH로 사용하며 제품 기능의 기존 AI·LLM 실행은 보존합니다.
- 새 세션은 `~/.gbrain-agent.md`를 읽고, 공용 최신 `project/windows-control-tower-operating-context`와 `project/fundkeeper-operating-context`를 확인합니다.
- 아래 Linux 경로와 명령은 명시된 원격 호스트의 셸에서 실행합니다. 조정실 OS에 맞춰 서버 경로를 바꾸거나 운영 코드를 조정실에 복제하지 않습니다.
- 기획·리서치·작업 계획은 `docs/README.md`에서 찾습니다. `docs`는 통합 controlroom 저장소의 `projects/fundkeeper/docs`에 연결되며 기본 정본은 `~/controlroom/projects/fundkeeper/docs`입니다.
- 작업을 이어받을 때는 `docs/README.md`의 진행 중 작업 링크와 해당 계획의 재개 정보를 읽고 실제 서버 Git 상태와 대조합니다. 작업을 마치거나 옮기기 전에 그 계획에 재개 정보를 갱신하며 병렬 작업은 각 계획에서 관리합니다.

## 역할

- 이 폴더는 FundKeeper의 지침·스킬·기획 문서와 장기 기억의 진입점입니다.
- 애플리케이션 소스와 그 Git 저장소는 통합 main에 둡니다.
- 중앙 에이전트가 SSH로 원격 저장소를 직접 수정·검증·Git 관리합니다.
- 원격 Codex·Claude에는 개발 지침·스킬·GBrain을 설치하지 않습니다.

## 정본

2026-09-17 22:33 KST 실제 인계 이후의 운영 주소는 `chaconne@49.247.192.127`입니다. 2026-09-18 00:35 KST 공개 DNS 원본 14개 이름 모두 새 main이고 가비아 권한 서버 3곳 및 Google/Cloudflare에서 이를 확인했습니다. DNS 캐시의 옛 공개 입구와 SQL/CLI/자료 호환 주소는 새 main으로 전달합니다. 옛 서버의 호환 전달·별도 복구 백업·제외 서비스 의존성은 남아 있으므로 DNS 변경만으로 해지/삭제하지 않습니다. 최신 운영 상태·복구 경로는 `~/controlroom/docs/production-server-consolidation-20260916.md` 최신 절과 main `/srv/consolidation/infra/README.md`를 먼저 확인합니다. 과거 GBrain 프로젝트 맥락이나 고유 스킬에 남은 옛 서버·Swarm 배포 명령보다 이 현행 주소를 우선합니다. 옛 운영 writer는 정지·읽기 전용이므로 그 서버에서 배포하거나 DB/자료를 쓰지 않습니다.

| 항목 | 값 |
|---|---|
| SSH | `chaconne@49.247.192.127` |
| 실제 저장소 | `/srv/consolidation/repos/fundkeeper` |
| GitHub / 원격 / 기준 브랜치 | `git@github.com:reneesoft/fundkeeper.git` / `origin` / `master` |
| 앱 실행 위치 | `production-coconut-web-1` 내부 `/home/work/fundkeeper` |
| 통합 Docker 정의 | `/srv/consolidation/infra/compose.production.coconut.json` + `compose.activate.coconut.json`, Compose 프로젝트 `production-coconut` |
| 운영 데이터 | `/srv/consolidation/data/files-standby/coconut-data` |
| 운영 DB | main `migration-replicas-mysql-1` / 앱망 `172.30.41.10:3306` |
| 운영 도메인 | `https://coconut.ai.kr` |
| 헬스체크 | `https://coconut.ai.kr/health/` → `ok` |
| 옛 공개 입구 | `49.247.38.186` → main 전달; 옛 `/home/docker/deploy.sh` 실행 금지 |

현재 코드와 이 문서가 다르면 원격 코드를 확인한 뒤 코드에 맞춰 이 문서와 GBrain을 갱신합니다.

## 공식 작업 경로

1. GBrain의 `project/fundkeeper-operating-context`를 확인합니다.
2. SSH로 원격 저장소의 브랜치·변경·미추적 파일을 확인합니다.
3. 요청 범위와 관련된 실제 코드·설정·호출 경로를 읽습니다.
4. 기존 사용자 변경을 보존하고 요청 파일만 최소 수정합니다.
5. main의 앱 이미지·독립 테스트 환경에서 영향 범위에 맞는 비파괴 검증을 실행합니다. 호스트 `.venv`는 아직 없습니다.
6. Git diff와 검증 결과를 확인한 뒤 요청 범위만 커밋합니다.
7. 배포는 주인님이 명시적으로 요청한 경우에만 실행합니다. `fundkeeper-deploy`에 남은 옛 Swarm·전체 stack/prune 명령을 실행하지 말고 main의 해당 제품 Compose 정의와 scoped 배포·복구 경로를 먼저 대조합니다.

## 작업별 스킬

- 일반 구조·도메인·원격 개발: `fundkeeper`
- UI·UX·템플릿·Tailwind: `fundkeeper-design-system`
- 운영 배포·복구 확인: `fundkeeper-deploy`
- 코스콤 RA 테스트베드 공통 작업: `testbed-base`
- 수동계좌 잔고 반영: `fundkeeper-client-balance`

## 검증 기준

- 코드 검증 위치는 main `/srv/consolidation/repos/fundkeeper`입니다. 호스트 `.venv`는 없으며 기존 Coconut 앱 이미지의 Python과 운영 DB/외부 주문에서 분리한 테스트 환경으로 Django 검사·관련 테스트를 실행합니다.
- 관련 테스트는 테스트 코드가 운영 DB·외부 주문·파일을 바꾸지 않는지 먼저 확인한 뒤 대상만 실행합니다.
- UI 변경은 Tailwind 빌드와 실제 화면 확인이 모두 필요합니다.
- 운영 확인은 HTTPS 헬스체크와 main `production-coconut-web-1`의 healthy 및 `production-coconut-nginx-1`의 running 상태를 사용합니다.
- 검증하지 못한 항목을 통과했다고 보고하지 않습니다.

## 안전 경계

- `.env`, `.venv`, `data/`, 운영 DB, Docker Swarm, 결제, 증권 주문, 예약 작업은 요청 없이 변경하지 않습니다.
- `xmodules/sh/`는 운영 예약 작업에서 직접 호출되므로 수정 전에 실행 주체와 호출 경로를 확인합니다.
- 테스트 명령도 운영 DB와 외부 API에 영향을 줄 수 있으므로 이름만 보고 실행하지 않습니다.
- 원격 저장소의 사용자 변경과 미추적 파일을 보존합니다.
- 원격 에이전트 지침·사용자 스킬·GBrain 설정을 다시 만들지 않습니다.
- 제품 컨테이너는 main의 private `secrets/coconut-codex`를 `/root/.codex:ro`, 기존 `data/product-codex-0.153.4`를 `/opt/product-codex:ro`로 읽고 임시 `CODEX_HOME`으로 기존 제품 AI를 실행합니다. 원본 ChatGPT 인증·모델·코드는 런타임 계약이며 개발 에이전트/조정실 지침을 이 경로에 설치하지 않습니다.

## GitHub 경계

- 원격 Git과 SSH 인증이 저장소 작업의 정본입니다.
- 브랜치를 `main`으로 추정하지 않습니다. 이 저장소의 기준 브랜치는 `master`입니다.
- GitHub 앱이 비공개 저장소를 보지 못하면 로컬 Git 결과로 작업하고, 앱 권한이 필요한 PR·이슈 작업만 권한 부족으로 보고합니다.
