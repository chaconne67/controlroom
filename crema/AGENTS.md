# Crema 프로젝트

## 조정실

- 작업 위치는 현재 조정실 루트의 실제 `crema` 폴더입니다. 모든 OS의 PC·노트북·main 서버 조정실은 `~/controlroom/crema`입니다. `~`는 Windows의 `USERPROFILE`, macOS·Linux의 `HOME`입니다.
- 새 세션은 전역 `~/.gbrain-agent.md`를 먼저 읽고, 이 `AGENTS.md`를 읽은 뒤 작업합니다.
- 기획·리서치·작업 계획은 `docs/README.md`에서 찾습니다. 정본은 현재 프로젝트의 실제 `docs` 폴더이며 GitHub controlroom 저장소의 `crema/docs`와 같은 위치입니다. 2026-09-25 이전 이름은 `agent-client`였습니다.
- 작업을 이어받을 때는 `docs/README.md`의 진행 중 계획과 재개 정보를 읽고 실제 Git 상태와 대조합니다. 작업을 마치거나 옮기기 전에 그 계획의 재개 정보를 갱신합니다.

## 역할

- Crema는 대화형 AI 에이전트 데스크톱 앱과 계정·홈페이지 서버로 이루어진 제품입니다. 제품 방향은 `docs/crema-제품기획-2026-09-25.md`, 진행 중 계획은 `docs/README.md`를 따릅니다.
- 한 GitHub 저장소 `chaconne67/crema`(공개, `main`)에 데스크톱 앱과 서버(`server/`)가 함께 있습니다.

## 정본

| 구분 | 정본 |
|---|---|
| GitHub | `git@github.com:chaconne67/crema.git`, 브랜치 `main` |
| 데스크톱 앱 개발 | 조정실 Windows PC `~/projects/crema` (Tauri 2 + JS, Rust) |
| 설치 파일·릴리스 | GitHub Actions `Windows installer` 워크플로(깨끗한 Windows에서 빌드·설치·검증). 릴리스는 `v*` 태그로 이 경로에서만 만든다 |
| 서버 코드 | 같은 저장소의 `server/` (Django) |
| 서버 실행 위치 | main `chaconne@49.247.192.127:/home/chaconne/projects/crema` |
| 도메인 | `https://crema-agent.site` |
| 서버 배포 정의 | `/srv/consolidation/infra/compose.production.crema.json` + `compose.activate.crema.json`, Compose 프로젝트 `production-crema` |
| 운영 DB | main `migration-replicas-postgres-1` / `crema` |
| 비밀값 | main `/srv/consolidation/secrets/crema.env` (Git·로그·출력 금지) |
| 로고·앱 아이콘 | `docs/icons/crema-c-bubble.svg` (채택) |

## 지켜야 할 것

- **데스크톱 앱의 설치·실행·확인은 Claude 격리 밖에서 합니다.** Claude 데스크톱 앱은 MSIX 격리 환경이라, 그 셸에서 띄운 프로그램은 AppData가 `%LOCALAPPDATA%\Packages\Claude_…\LocalCache`로 바뀝니다. `Invoke-CimMethod -ClassName Win32_Process -MethodName Create`로 띄운 프로세스에서 설치·실행하고, 결과는 AppData가 아닌 경로(예: `~/backups`)에 써서 읽습니다. 격리 안에서 얻은 성공은 검증으로 인정하지 않습니다.
- 앱 데이터 식별자는 `local.agentclient.prototype`, 저장 키는 `agent-client:*`입니다. 대화 기록이 끊기므로 바꾸지 않습니다.
- 서버 배포는 ziin과 같은 Compose·edge·인증서 방식으로 합니다. 기존 제품의 공개 주소와 DB 권한을 바꾸지 않고, edge 설정은 재읽기 전에 검사합니다.
