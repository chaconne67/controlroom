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
- 애플리케이션 소스와 그 Git 저장소는 기존 운영 서버에 둡니다.
- 중앙 에이전트가 SSH로 원격 저장소를 직접 수정·검증·Git 관리합니다.
- 원격 Codex·Claude에는 개발 지침·스킬·GBrain을 설치하지 않습니다.

## 정본

| 항목 | 값 |
|---|---|
| SSH | `chaconne@49.247.38.186` |
| 실제 저장소 | `/home/chaconne/fundkeeper` |
| 호환 경로 | `/home/work/fundkeeper` → 실제 저장소 |
| GitHub | `git@github.com:reneesoft/fundkeeper.git` |
| 기준 브랜치 | `master` |
| Python | `/home/chaconne/fundkeeper/.venv/bin/python` (3.12) |
| Docker 작업 경로 | `/home/docker` |
| 배포 진입점 | `sudo /home/docker/deploy.sh` |
| 운영 도메인 | `https://coconut.ai.kr` |
| 헬스체크 | `https://coconut.ai.kr/health/` → `ok` |

현재 코드와 이 문서가 다르면 원격 코드를 확인한 뒤 코드에 맞춰 이 문서와 GBrain을 갱신합니다.

## 공식 작업 경로

1. GBrain의 `project/fundkeeper-operating-context`를 확인합니다.
2. SSH로 원격 저장소의 브랜치·변경·미추적 파일을 확인합니다.
3. 요청 범위와 관련된 실제 코드·설정·호출 경로를 읽습니다.
4. 기존 사용자 변경을 보존하고 요청 파일만 최소 수정합니다.
5. 원격 가상환경에서 영향 범위에 맞는 비파괴 검증을 실행합니다.
6. Git diff와 검증 결과를 확인한 뒤 요청 범위만 커밋합니다.
7. 배포는 주인님이 명시적으로 요청한 경우에만 `fundkeeper-deploy` 스킬로 실행합니다.

## 작업별 스킬

- 일반 구조·도메인·원격 개발: `fundkeeper`
- UI·UX·템플릿·Tailwind: `fundkeeper-design-system`
- 운영 배포·복구 확인: `fundkeeper-deploy`
- 코스콤 RA 테스트베드 공통 작업: `testbed-base`
- 수동계좌 잔고 반영: `fundkeeper-client-balance`

## 검증 기준

- 기본 Django 검사: `cd /home/chaconne/fundkeeper && .venv/bin/python manage.py check --settings=fundkeeper.settings.deploy`
- 관련 테스트는 테스트 코드가 운영 DB·외부 주문·파일을 바꾸지 않는지 먼저 확인한 뒤 대상만 실행합니다.
- UI 변경은 Tailwind 빌드와 실제 화면 확인이 모두 필요합니다.
- 운영 확인은 HTTPS 헬스체크와 `docker stack services Coconut`의 두 서비스 `1/1`을 사용합니다.
- 검증하지 못한 항목을 통과했다고 보고하지 않습니다.

## 안전 경계

- `.env`, `.venv`, `data/`, 운영 DB, Docker Swarm, 결제, 증권 주문, 예약 작업은 요청 없이 변경하지 않습니다.
- `xmodules/sh/`는 운영 예약 작업에서 직접 호출되므로 수정 전에 실행 주체와 호출 경로를 확인합니다.
- 테스트 명령도 운영 DB와 외부 API에 영향을 줄 수 있으므로 이름만 보고 실행하지 않습니다.
- 원격 저장소의 사용자 변경과 미추적 파일을 보존합니다.
- 원격 에이전트 지침·사용자 스킬·GBrain 설정을 다시 만들지 않습니다.
- 제품 컨테이너가 호스트 `/home/chaconne/.codex`를 읽고 임시 `CODEX_HOME`으로 상담원·자산명 변환 Codex를 실행하므로, 원격 Codex 설정의 순정 상태는 제품 런타임 계약입니다.

## GitHub 경계

- 원격 Git과 SSH 인증이 저장소 작업의 정본입니다.
- 브랜치를 `main`으로 추정하지 않습니다. 이 저장소의 기준 브랜치는 `master`입니다.
- GitHub 앱이 비공개 저장소를 보지 못하면 로컬 Git 결과로 작업하고, 앱 권한이 필요한 PR·이슈 작업만 권한 부족으로 보고합니다.
