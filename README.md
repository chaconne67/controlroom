# Controlroom

조정실의 공통 지침·스킬·프로젝트 계획을 관리합니다. **PC·노트북은 `~/projects`에 조정실을 설치**하고, **Ubuntu main 서버는 `--main-server`로 기존 코드 저장소에 에이전트 지침·스킬만 추가**합니다. Windows의 `~`는 사용자 폴더, macOS·Linux는 HOME입니다.

## 처음 설치하거나 최신본 적용

Git, Python 3.12 이상과 GitHub SSH 키 인증을 준비합니다. 인증은 사용자가 설정하며, 설치기는 키나 인증 설정을 변경하지 않습니다. Controlroom 저장소의 읽기 권한이 필요하고 PC·노트북의 일반 설치에는 Venture 저장소 읽기 권한도 필요합니다. Windows는 Git for Windows와 PowerShell, Linux·macOS는 Bash를 사용합니다.

**설치·`kitpull`·`kitpush` 모두 Git SSH를 사용합니다.** `gh`나 HTTP 토큰은 필요 없습니다. OS에 맞는 **한 줄만 실행하면 다운로드부터 설치와 명령 등록까지 진행**합니다. 인증이나 다운로드가 실패하면 설치를 시작하지 않습니다.

### Windows — PowerShell

```powershell
$d="$env:USERPROFILE\.local\share\controlroom\source"; if (!(Test-Path "$d\.git")) { git clone git@github.com:chaconne67/controlroom.git $d; if ($LASTEXITCODE) { throw 'Download failed' } }; & "$d\.controlroom\install.ps1"
```

### Windows — 명령 프롬프트(CMD)

CMD에서는 이 한 줄을 사용합니다. 같은 설치기를 호출하고 현재 CMD에도 명령 경로를 등록하므로, 완료 직후 `kitpull`·`kitpush`를 그대로 입력합니다. `.cmd` 확장자를 붙이지 않아도 됩니다.

```cmd
powershell -NoProfile -Command "$d=$env:USERPROFILE+'\.local\share\controlroom\source'; if (!(Test-Path ($d+'\.git'))) { git clone git@github.com:chaconne67/controlroom.git $d; if ($LASTEXITCODE) { exit $LASTEXITCODE } }; & ($d+'\.controlroom\install.ps1')" && set "PATH=%USERPROFILE%\.local\bin;%PATH%"
```

### PC·노트북의 macOS·Linux — Bash

```bash
d=~/.local/share/controlroom/source; { [ -d "$d/.git" ] || git clone git@github.com:chaconne67/controlroom.git "$d"; } && bash "$d/.controlroom/install.sh" && . "$HOME/projects/.controlroom/shell/kit-aliases.sh"
```

설치기는 최신본을 먼저 받아 확인하고 기존 대상을 압축 백업한 뒤 적용합니다. 한 줄 명령이 끝나면 같은 터미널에서 바로 `kitpull`과 `kitpush`를 사용할 수 있습니다. `kitpull --verify`로 설치 상태를 확인합니다. PC·노트북의 최종 저장 위치는 `~/projects`이며 별도의 `~/controlroom` 체크아웃은 필요하지 않습니다. 이미 설치한 장비에서 다시 실행해도 최신본을 적용합니다.

### Ubuntu main 서버 — 코드 보존 설치

기존 `~/projects/<프로젝트>`에서 코드가 운영되고 있고 GitHub SSH 인증이 되어 있으면 다음 한 줄로 처음 설치합니다. `gh` 설치나 토큰 입력은 필요 없습니다.

```bash
d=~/.local/share/controlroom/source; { [ -d "$d/.git" ] || git clone git@github.com:chaconne67/controlroom.git "$d"; } && bash "$d/.controlroom/install.sh" --main-server && . "$d/.controlroom/shell/kit-aliases.sh"
```

한 줄 명령이 끝나면 같은 터미널에서 바로 `kitpull`과 `kitpush`를 사용합니다. 기존 설치나 미완료 설치가 있어도 같은 한 줄을 다시 실행할 수 있습니다. 이후 갱신은 `kitpull`을 사용합니다.

- 공통 원본·도구는 `~/.local/share/controlroom/source`에 보관합니다. 기존 프로젝트 폴더는 그대로 사용합니다.
- 실제 Git 저장소가 있는 프로젝트만 선택해 `AGENTS.md`·`CLAUDE.md`의 관리 구역과 `.agents/skills`, `.claude/skills`를 갱신합니다. 기존 지침 본문과 개인 스킬은 보존합니다.
- 프로젝트별 manifest의 스킬과 해당 코드 저장소의 원본 `skills`를 사용합니다. 같은 이름이면 프로젝트 원본을 우선합니다.
- 제품의 `.git`, 브랜치·원격, 코드, `docs`, 원본 `skills`, 환경·고객 자료는 변경하지 않습니다. Venture를 포함해 제품 저장소를 clone·pull·push하지 않습니다.
- 이후 `kitpull`과 `kitpush`는 이 모드를 유지합니다. `kitpush`는 별도 Controlroom 원본만 전송하며 제품 코드나 로컬 프로젝트 지침 본문을 수집하지 않습니다.

프로젝트 루트가 다르면 위 명령의 `--main-server` 바로 뒤에 `--workspace "$HOME/operating-projects"`를 붙입니다. 사용자 HOME 안의 기존 실제 폴더를 지정합니다. 역할명은 기본값 `windows-control`을 사용하므로 입력하지 않아도 됩니다. 에이전트 앱 로그인과 프로젝트 서버 SSH 접근은 각 장비에서 준비합니다. 이 옵션은 에이전트 프로그램 자체를 설치하거나 자동 실행을 활성화하지 않습니다.

## 일상 동기화

```bash
kitpull
kitpush "변경 설명"
```

- `kitpull`: 일반 설치는 지침·도구·계획과 등록된 Venture 코드를 갱신합니다. main 서버 모드는 에이전트 자산만 갱신합니다. 교체 대상의 기존 내용은 먼저 압축 백업합니다.
- `kitpush`: 검토한 Controlroom 원본을 GitHub로 보내고 앱의 사본을 갱신합니다. 일반 설치는 Venture의 이미 만든 커밋도 전송하지만 main 서버 모드는 제품 Git을 변경하지 않습니다. 충돌하면 rebase를 취소해 로컬 커밋을 보존합니다.

설치 상태만 확인하려면 `kitpull --verify`를 사용합니다. 파일을 갱신하지 않고 실제 폴더 구조와 앱에서 읽는 지침·스킬의 내용을 검사합니다. Windows·macOS·Linux 모두 같은 두 명령을 사용합니다.

기기를 옮기기 전 현재 계획에 목표·승인 범위, 실제 서버/저장소·브랜치·커밋, 남은 변경, 마지막 검증 결과와 다음 행동을 기록하고 push합니다. 다음 장비에서는 pull 후 계획과 실제 서버 상태를 대조합니다.

## PC·노트북의 실제 구조

```text
~/projects/                 Controlroom Git 저장소의 실제 루트
├── .controlroom/           공통 설치기·지침·스킬·운영 설명
├── ceoloan/                AGENTS.md, CLAUDE.md, docs/, skills/
├── exdigm/
├── fundkeeper/
├── rndlog/
├── testbed/
├── ziin/
└── venture/                별도 Venture 코드 Git 저장소
```

GitHub와 각 장비는 같은 상대 경로를 사용합니다. 프로젝트 문서는 바로 `<프로젝트>/docs`에 있고 스킬 원본은 `<프로젝트>/skills`에 있습니다. 공통 스킬 원본은 `.controlroom/skills`입니다. 문서·지침·스킬 원본에 연결 폴더나 하드링크를 만들지 않습니다. 앱이 요구하는 `.agents/skills`, `.claude/skills` 등에는 설치기가 실제 파일을 복사합니다. 배치 목록은 `.controlroom/manifests/skills.json` 한 곳입니다.

main 서버 모드는 위 조정실 구조를 코드 루트에 덮어쓰지 않습니다. 별도 원본의 프로젝트 지침·스킬을 기존 코드 저장소에 배치하고 제품 Git과 문서 구조를 유지합니다. main에 없는 Exdigm 코드 저장소는 새로 만들지 않으며 기존 전용 서버의 작업 경로를 사용합니다. 실제 운영 상태·자동 수정 권한은 [자동 수정 방침](exdigm/docs/operational-error-triage-repair-policy-20260918.md)을 따릅니다. 이 설치 옵션의 추가는 운영서버에 적용을 마쳤다는 뜻이 아닙니다.

개발 에이전트는 조정실에서 실행합니다. 서버의 제품 코드·Git·데이터·미디어·빌드·테스트·배포는 각 프로젝트의 기존 SSH 절차와 실제 서버 경로를 따릅니다. Venture의 업무 스킬은 Venture 저장소의 `skills`가 원본입니다. 조정실 Git은 Venture와 고객 자료·환경 파일·인증 정보를 자동 수집하지 않습니다.

## 백업과 복구

백업은 **`~/backups/controlroom/<날짜>-<번호>.zip`**에 보관합니다. 교체할 폴더 전체와 숨김 파일·Git 상태·로컬 변경을 포함하고 압축 파일의 내용까지 검사합니다. 외부 자료를 가리키는 링크는 연결 정보만 보관하며 외부 자료를 따라가거나 지우지 않습니다. 다운로드·사전 검사에 실패하면 기존 설치는 건드리지 않습니다. 적용 중 실패하면 같은 백업에서 자동으로 이전 상태를 복구합니다.

일반 업데이트는 다운로드한 최신본을 적용하는 것이 목적입니다. 같은 이름의 옛 파일과 최신본에서 없어진 관리 파일은 교체·정리합니다. Venture의 환경 파일·고객 자료·독립 실행 자료, 플러그인·시스템·사용자 개인 스킬과 다른 Hermes의 기존 스킬은 유지합니다. 추가로 과거 상태를 직접 복원할 때:

```bash
kitpull --restore "백업 ZIP의 전체 경로"
```

복원은 설치기가 교체한 파일과 자신의 Git 상태를 업데이트 전으로 되돌립니다. main 서버 모드의 백업·복구는 제품 Git을 포함하지 않습니다. 일반 설치의 옛 `~/controlroom`, `~/kmh-agent-kit`, `~/projects/_control-docs`는 전환 후 정리하지만 main 서버 모드는 옛 조정실 폴더를 이동·삭제하지 않습니다. 복원 후 새 터미널에서 명령을 실행합니다. GBrain 역할명과 서버 런타임은 기존 운영 계약을 유지합니다.

## 운영 설명

- [장비 준비](.controlroom/docs/onboarding-new-server.md)
- [스킬 관리](.controlroom/docs/skill-management.md)
- [GBrain 운영](.controlroom/docs/gbrain-operating-guide.md)
- [서버 통합과 실제 운영 상태](.controlroom/docs/production-server-consolidation-20260916.md)
- [승인된 구조·업데이트 계획](.controlroom/docs/controlroom-unification.md)

과거 문서의 옛 경로는 기록 당시 상태이며, 현행 조정실 구조는 이 README를 따릅니다.
