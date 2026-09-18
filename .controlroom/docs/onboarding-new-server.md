# Controlroom 장비 준비

PC·노트북의 조정실 루트는 `~/projects`이며 공통 도구는 `~/projects/.controlroom`에 둡니다. Ubuntu main 서버는 아래 `--main-server` 옵션으로 기존 코드 저장소에 지침·스킬만 추가합니다. Windows의 `~`는 USERPROFILE, macOS·Linux는 HOME입니다.

Git, Python 3.12 이상, [GitHub CLI (`gh`)](https://cli.github.com/), 비공개 Controlroom 저장소의 읽기 권한을 준비합니다. PC·노트북의 일반 설치에는 Venture 저장소 읽기 권한도 필요합니다. Windows는 Git for Windows와 PowerShell, Linux·macOS는 Bash와 curl을 사용합니다.

새 장비에서 GitHub 인증을 한 번 설정합니다. 아래 두 명령은 두 OS에서 같습니다.

```text
gh auth login --hostname github.com --git-protocol https
gh auth setup-git --hostname github.com
```

이후 OS에 맞는 **한 줄만 실행하면 다운로드부터 설치까지 진행**합니다. 비공개 저장소이므로 GitHub 인증을 사용해 설치 스크립트를 받습니다. 인증이나 다운로드가 실패하면 설치를 시작하지 않습니다.

새 기기의 앱 로그인·SSH 키·프로젝트 서버 접근은 해당 장비에서 준비합니다. 개발 에이전트는 조정실에서 실행하며 서버의 실제 제품 코드·데이터·배포 경로를 설치기로 옮기지 않습니다.

## Windows PowerShell

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -Command "& ([scriptblock]::Create((Invoke-RestMethod -Headers @{Authorization=('Bearer ' + (gh auth token --hostname github.com)); Accept='application/vnd.github.raw+json'} -Uri 'https://api.github.com/repos/chaconne67/controlroom/contents/.controlroom/install.ps1?ref=main' -ErrorAction Stop).TrimStart([char]0xFEFF))) -Agent windows-control"
```

## PC·노트북의 macOS·Linux Bash

```bash
(set -e; installer="$(mktemp)"; trap 'rm -f "$installer"' EXIT; curl -fsSL -H "Authorization: Bearer $(gh auth token --hostname github.com)" -H "Accept: application/vnd.github.raw+json" "https://api.github.com/repos/chaconne67/controlroom/contents/.controlroom/install.sh?ref=main" -o "$installer"; bash "$installer" windows-control)
```

## Ubuntu main 서버

기존 `~/projects/<프로젝트>`에 실제 코드 저장소가 있으면 다음 명령을 사용합니다.

```bash
script=$(curl -fsSL -H "Authorization: Bearer $(gh auth token)" https://raw.githubusercontent.com/chaconne67/controlroom/main/.controlroom/install.sh) && bash -c "$script" -- --main-server
```

Controlroom 원본·도구는 `~/.local/share/controlroom/source`에 두며 제품 루트에 공통 `.git`을 만들지 않습니다. 실제로 존재하는 프로젝트 Git을 확인해 기존 `AGENTS.md`·`CLAUDE.md`에 관리 구역을 추가하고 `.agents/skills`, `.claude/skills`만 갱신합니다. manifest의 프로젝트 스킬과 제품의 자체 `skills`를 사용하고 동명 스킬은 프로젝트 원본을 우선합니다. 기존 지침 본문·개인 스킬과 코드·Git 전체·docs·원본 skills·환경·고객 자료는 보존합니다. 제품 Git은 clone·pull·push하지 않습니다.

다른 프로젝트 루트는 명령 끝에 `--workspace "$HOME/operating-projects"`를 붙입니다. 사용자 HOME 안의 기존 실제 폴더를 지정합니다. 역할명은 기본값 `windows-control`을 사용하므로 입력하지 않아도 됩니다. 옵션은 저장되므로 이후 명령에 반복해서 입력하지 않습니다. main에 없는 프로젝트 저장소는 생성하지 않습니다. 기존 옛 조정실 폴더도 이동·삭제하지 않습니다. 이 옵션은 에이전트 프로그램 설치·로그인·예약 실행을 대신하지 않습니다.

## 설치 후

새 터미널에서 `controlroom verify`를 실행합니다.

```bash
controlroom pull
controlroom push "변경 설명"
```

설치기는 최신본을 먼저 확보한 뒤 교체할 에이전트 자산을 `~/backups/controlroom`에 압축 백업하고 적용합니다. 적용 실패 시 자동 복구합니다. main 모드의 pull·verify·push는 에이전트 자산만 다루며 제품 Git을 변경하지 않습니다. 프로젝트에서 추가한 지침 본문은 해당 제품 소유로 유지합니다. 공통 자산을 수정·전송하려면 별도 Controlroom 원본을 편집합니다.

이미 설치한 장비에서는 `controlroom pull`을 사용합니다. 일반 설치의 설치기는 `~/projects/.controlroom`, main 모드는 `~/.local/share/controlroom/source/.controlroom`에 있습니다. 기기를 옮기기 전 계획의 재개 정보를 갱신하고 검토한 변경을 push합니다.
