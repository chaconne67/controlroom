# KMH Agent Kit

## 운영체제별 한 줄 설치

### Windows — Git Bash

[Git for Windows 공식 다운로드](https://git-scm.com/install/windows)에서 설치하면 Git Bash가 함께 설치됩니다. 설치가 끝나면 Git Bash를 열고 아래 한 줄을 그대로 붙여 넣습니다.

```bash
curl -fsSL https://raw.githubusercontent.com/chaconne67/kmh-agent-kit/main/install.sh | bash -s -- windows-control
```

셸 설치기가 공개 HTTPS 주소에서 키트를 내려받고, Windows를 감지하면 저장소의 `install.ps1`을 내부에서 호출합니다. 사용자가 PowerShell 단계를 따로 실행할 필요는 없습니다.

### macOS — Terminal

```bash
curl -fsSL https://raw.githubusercontent.com/chaconne67/kmh-agent-kit/main/install.sh | bash -s -- windows-control
```

### Linux — Bash

```bash
curl -fsSL https://raw.githubusercontent.com/chaconne67/kmh-agent-kit/main/install.sh | bash -s -- windows-control
```

세 운영체제 모두 같은 조정실 등록 이름인 `windows-control`을 사용합니다. 이 이름은 호환용 역할 이름이며 Windows에서만 쓸 수 있다는 뜻이 아닙니다.

설치가 끝나면 터미널을 새로 엽니다. 이후에는 모든 운영체제에서 다음 두 명령만 사용합니다.

```text
kitpull
kitpush
```

위 세 기본 명령의 첫 다운로드와 clone은 공개 HTTPS를 사용하므로 GitHub SSH 키가 없어도 시작할 수 있습니다. GitHub 쓰기 인증과 GBrain·프로젝트 서버의 새 장비 SSH 등록은 각각 해당 기능을 사용하기 전에 준비합니다.

### 조정실에서 복원되는 범위

| 항목 | 위 한 줄의 현재 결과 |
|---|---|
| `kmh-agent-kit` | 새 장비는 공개 HTTPS로 `~/kmh-agent-kit`에 clone. 현재 PC의 origin은 기존 SSH 주소 유지 |
| Codex·Claude Code·Hermes | 전역 지침과 공용 스킬 연결 |
| GBrain | `windows-control` 카드를 연결하고, 장비 SSH 등록이 되어 있으면 공용 문서 조회까지 검증 |
| 프로젝트 폴더 | 다섯 조정 폴더를 만들고 kit 프로필 연결. `venture`가 없으면 GitHub에서 clone |
| 대화 세션 | 동기화하지 않음 |

스킬 동기화 대상은 직접 만든 사용자 스킬과 키트의 프로젝트 스킬입니다. Codex 기본 스킬,
플러그인 캐시, 키트에 없는 별도 프로그램 스킬은 해당 프로그램이 관리합니다. 같은 이름의 옛
사용자 스킬이 남아 있으면 최초 설치가 삭제하지 않고 백업한 뒤 키트 원본을 연결합니다.

## 개요

KMH Agent Kit은 조정실의 휴대 가능한 작업 환경을 담는 GitHub 정본입니다. 개발 에이전트는 조정실에서만 실행하고 서버는 기존 코드·빌드·테스트 명령을 SSH로 수행합니다. 프로젝트 기획 원본은 비공개 `control-room-docs` 저장소(`projects/_control-docs`)로 관리하며, 이 공개 키트에 복제하지 않습니다. 코드와 함께 배포·검증하는 자료와 제품 AI 런타임은 서버에 유지합니다. `AGENTS.md`, `CLAUDE.md`, 공용·프로젝트 스킬, GBrain 카드와 프로젝트 진입 구조를 연결합니다. 작업 중 확정한 결정과 재사용할 디버깅 지식은 전역 지침에 따라 GBrain에 기록하며 대화 원문은 복사하지 않습니다.

설치 명령에 넣는 값은 장비의 호스트명이 아니라 **등록 이름**입니다. 등록 이름이 사용할 GBrain 공간·접근 정책·카드를 결정합니다.

먼저 현재 상황을 구분합니다.

| 상황 | 사용할 설치 방식 |
|---|---|
| 새로운 프로젝트 역할을 처음 등록 | `--new`로 공간·정책·카드까지 생성 |
| 이미 등록된 역할을 새 장비에 설치하거나 재설치 | 아래 서버별 표의 기존 등록 이름 사용 |

경계가 헷갈릴 때는 다음 두 사례로 판단합니다.

- `abc_project` 역할 자체가 처음이면 `abc-project`를 `--new`로 등록합니다.
- `abc-project`가 이미 등록되고 카드가 저장소에 반영된 뒤 장비만 추가한다면 `./install.sh abc-project`를 사용합니다.

GBrain 등록 이름은 영문 소문자·숫자·중간 하이픈으로 된 1~32자입니다. 밑줄은 허용되지 않으므로 `abc_project`의 등록 이름은 `abc-project`입니다.

최초 설치가 끝난 뒤에는 서버 이름을 다시 입력하지 않습니다.

```bash
kitpull
kitpush
```

## 신규 등록 이름 만들기

새로운 `abc_project` 역할 자체를 처음 등록할 때는 중앙 Linux 환경에서 다음 한 줄을 실행합니다.

```bash
curl -fsSL https://raw.githubusercontent.com/chaconne67/kmh-agent-kit/main/install.sh | bash -s -- --new abc-project
```

이 명령은 다음 작업을 완료합니다.

1. 공용 스킬과 전역 지침 설치
2. 중앙 GBrain에 `abc-project` 전용 공간과 접근 정책 생성
3. `abc-project` GBrain 카드 생성·연결
4. 중앙 GBrain SSH 프록시 연결
5. 카드와 정책 연결 검증

실제 생성 전에 내용을 확인하려면 한 줄 설치 후 dry-run을 사용합니다.

```bash
~/kmh-agent-kit/install.sh --new abc-project --dry-run
~/kmh-agent-kit/install.sh --new abc-project
```

새 장비에서 등록까지 마치려면 다음 접속 조건을 갖춰야 합니다.

- GitHub에서 이 저장소를 clone할 수 있어야 합니다.
- `chaconne@49.247.45.243`에 비밀번호 없이 SSH 접속할 수 있어야 합니다.

운영 서버는 에이전트 키트의 자동 설치·배포 대상이 아닙니다. Coconut·RNDLOG·CEO Loan·Exdigm 운영 서버는 현재 상태를 유지합니다. 다른 서버에 설치하는 기능은 남겨 두되, 장비별로 명시적으로 선택한 경우에만 실행합니다.

## 그 외

### 가능한 명령

| 명령 | 용도 |
|---|---|
| `kitpull` | `origin/main`을 fast-forward로 받은 뒤 등록 자산과 프로젝트 프로필 재설치 |
| `kitpush` | 허용 범위를 검사하고 원격 변경 위에 재배치한 뒤 `origin/main`으로 push |
| `./install.sh main` | 중앙 DB·GBrain 역할 설치 |
| `./install.sh fundkeeper` | FundKeeper 역할 설치 |
| `./install.sh judy` | Judy WSL 역할 설치 |
| `./install.sh --new abc-project` | 신규 등록 이름의 공간·정책·카드 생성 후 설치 |
| `./install.sh --new abc-project --dry-run` | 신규 생성 내용을 변경 없이 미리 확인 |
| `./install.sh` | GBrain 카드 없이 공용 스킬·전역 지침만 설치 |
| `./install.sh --project ~/projects/exdigm exdigm` | 프로젝트 프로필만 별도로 연결 |
| `./install.sh --project ~/projects/rndlog rndlog` | 중앙 RNDLOG 조정실 연결 |
| `./install.sh --project ~/projects/ceoloan ceoloan` | 중앙 CEO Loan 조정실 연결 |
| `./install.sh --help` | 설치 명령 표시 |

이전 `--gbrain` 형식은 기존 자동화의 호환을 위해서만 유지합니다. 새 설치에는 위 표의 공식 명령을 사용합니다.

### 등록 이름과 프로젝트 경로

최초 `./install.sh <등록 이름>`이 등록 이름을 해당 저장소의 Git 로컬 설정에 저장합니다. 이 값은 커밋되지 않으므로 장비마다 독립적으로 유지됩니다.

Linux·macOS의 기존 심볼릭 링크 설치는 첫 `kitpull` 또는 `kitpush`에서 현재 GBrain 카드 경로를 읽어 등록 이름을 한 번 복구할 수 있습니다. Windows 카드는 하드링크라서 경로를 역으로 읽을 수 없습니다. Windows의 Git 로컬 등록값이 없으면 README 첫 화면의 Git Bash 한 줄을 다시 실행합니다.

- 두 명령은 항상 로컬 `main`과 `origin/main`만 사용합니다. 추적 브랜치가 없거나 잘못돼 있으면 `origin/main`으로 복구합니다.
- `kitpull`: 작업 폴더가 깨끗할 때만 fast-forward한 뒤 등록 자산과 저장된 프로젝트 프로필을 실제 환경에 다시 연결합니다.
- `kitpush`: 공용 파일, 현재 등록 이름의 카드, 매칭 도메인만 커밋·push합니다. `main`과 `windows-control` 등록은 중앙 조정 역할이므로 모든 도메인을 다룰 수 있습니다.
- 프로젝트 전용 등록에 다른 도메인의 변경이 함께 있으면 `kitpush`는 변경 경로를 표시하고 중단합니다.
- 원격 변경이 먼저 있으면 `kitpush`가 로컬 커밋을 `origin/main` 위에 재배치합니다. 충돌하면 재배치를 취소하고 로컬 커밋을 보존한 채 중단합니다.

### 신규 등록 작동 원리

`./install.sh --new abc-project`는 다음 순서로 실행됩니다.

1. `gbrain-cards/abc-project.md` 범용 카드 생성
2. 중앙 GBrain에 `abc-project` 소스 생성
3. 중앙 기본 소스를 `default`로 복구하고 공용 조회 검증
4. `agents/abc-project/private` 읽기·쓰기 정책 등록
5. 현재 서버에 공용 자산·카드·`gbrain-abc-project` 프록시 설치
6. 실제 정책 조회로 연결 검증

같은 등록 이름의 기존 공간·정책·카드는 덮어쓰지 않습니다. 기존 정책이 예상한 접근 범위와 다르면 자동 수정하지 않고 중단합니다.

생성된 카드는 저장소의 신규 파일로 남습니다. 다른 서버도 같은 카드를 받게 하려면 내용을 검토한 뒤 커밋·push합니다.

### 서버별 자동 프로젝트 연결

| 등록 이름 | 자동 연결되는 프로젝트 프로필 |
|---|---|
| `main` | `~/projects/<프로필명>`과 저장소 프로필 이름이 일치하는 모든 프로젝트 |
| `windows-control` | 계약에 적힌 다섯 조정 폴더를 생성·연결하고, `venture`가 없으면 공식 저장소 clone |
| `fundkeeper` | `~/fundkeeper`의 `fundkeeper` 프로필 |
| 그 외 | 같은 이름의 프로젝트 폴더와 프로필이 모두 있을 때 연결 |

`./install.sh --project <경로> <프로필>`로 연결한 위치는 저장소의 로컬 Git 설정에 기록됩니다. 이후 `kitpull`과 `kitpush`가 해당 프로필을 다시 연결합니다.

`windows-control`의 폴더 정본은 `manifests/windows-control-projects.tsv`입니다. `ceoloan`, `exdigm`, `fundkeeper`, `rndlog`, `ziin`은 폴더를 만든 뒤 kit의 프로젝트 지침과 스킬을 연결합니다. `venture`는 자체 `AGENTS.md`, `CLAUDE.md`, 스킬과 소스 코드를 함께 가진 별도 Git 저장소이므로, 폴더가 없을 때만 공개 HTTPS로 clone하고 기존 폴더나 미커밋 작업은 건드리지 않습니다.

FundKeeper 조정 폴더에는 코스콤 Testbed의 공통·알고리즘 설명서·ETF·리밸런싱 스킬도 함께 연결됩니다.

운영 서버에는 프로젝트 프로필·공용 지침·GBrain 카드를 자동 설치하지 않습니다. 중앙 조정 장비의 프로젝트 폴더에만 프로필을 연결해도 운영 저장소를 관리할 수 있습니다.

### 설치 파일 연결 방식

| 설치 대상 | 저장소 원본 | 실제 사용 위치 |
|---|---|---|
| 공용 스킬 | `skills/common/` | Claude `~/.claude/skills`, Codex `~/.agents/skills`, Hermes는 Windows `%LOCALAPPDATA%\hermes\skills`·Linux/macOS `~/.hermes/skills` |
| 전역 지침 | `claude/CLAUDE.md`, `codex/AGENTS.md` | Claude `~/.claude/CLAUDE.md`, Codex `~/.codex/AGENTS.md` |
| 프로젝트 스킬 | `projects/` | 프로젝트의 `.claude/skills/`, `.agents/skills/` |
| GBrain 카드 | `gbrain-cards/` | `~/.gbrain-agent.md` |
| 원격 GBrain 프록시 | `gbrain/bin/gbrain-remote-proxy` | 프로젝트 전용 등록의 `~/.local/bin/gbrain-abc-project`; `windows-control`은 카드의 공용 SSH 명령 사용 |

Linux·macOS에서는 저장소 원본을 실제 사용 위치에 심볼릭 링크합니다. Windows에서는 디렉터리에 junction, 파일에 하드링크를 사용합니다. 링크가 아닌 기존 파일은 삭제하지 않고 `~/.kmh-agent-kit-backup-날짜-시각/`에 보존합니다.

### 업데이트

키트를 설치한 Linux·macOS·Windows PowerShell·CMD·Git Bash에서 같은 명령을 사용합니다.

```bash
kitpull
```

수정한 공용·도메인 자산을 올릴 때도 서버 이름 없이 실행합니다. 커밋 메시지는 생략할 수 있습니다.

```bash
kitpush
kitpush "설명할 커밋 메시지"
```

### 설치 확인

Windows PowerShell:

```powershell
python -X utf8 "$HOME\kmh-agent-kit\scripts\check-skill-deps.py"
Get-Command kitpull, kitpush
git -C "$HOME\kmh-agent-kit" config --local --get kmh-agent-kit.agent
fsutil hardlink list "$HOME\.gbrain-agent.md"
```

정상이라면 등록 이름은 `windows-control`이고, 하드링크 목록에는 현재 카드와 `kmh-agent-kit\gbrain-cards\windows-control.md`가 함께 표시됩니다.

Linux·macOS:

```bash
python3 ~/kmh-agent-kit/scripts/check-skill-deps.py
readlink ~/.gbrain-agent.md
git -C ~/kmh-agent-kit config --local --get kmh-agent-kit.agent
```

신규 `abc-project` 정책 확인:

```bash
gbrain-abc-project policy
```

중앙 GBrain 확인:

```bash
~/.gbrain/bin/gbrain_with_google_env.sh doctor --fast
```

### Windows 터미널

최초 설치는 README 최상단의 Git Bash 한 줄만 사용합니다. 설치 뒤에는 사용자 PATH의 `kitpull.cmd`·`kitpush.cmd`를 PowerShell·CMD·Git Bash에서 사용할 수 있습니다. Windows에는 Linux 전용 systemd 서비스를 설치하지 않습니다.

Coconut·RNDLOG·CEO Loan·Exdigm 운영 서버에서는 위 설치 명령을 자동으로 실행하지 않습니다.

### 저장소에 포함하는 범위

| 포함 | 포함하지 않음 |
|---|---|
| 공용 스킬과 전역 지침 | API 키·비밀번호·OAuth 토큰 |
| 프로젝트 프로필 | GBrain 데이터베이스와 백업 덤프 |
| GBrain 카드와 실행 래퍼 | Exdigm·Rndlog·Ceoloan 실제 서비스 코드 |
| 구조 검사와 설치 문서 | 한 서버에서만 쓰는 로컬 전용 자산 |

상세한 신규 서버 점검은 [New Server Onboarding](docs/onboarding-new-server.md), 스킬 관리 방법은 [Skill Management](docs/skill-management.md), 장애 해결은 [Troubleshooting](docs/troubleshooting.md)을 봅니다.
