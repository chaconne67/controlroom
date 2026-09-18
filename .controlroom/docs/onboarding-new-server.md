# 새 조정실 설치

모든 조정실을 사용자 폴더 아래 **`controlroom/<프로젝트>`**에 설치합니다. Windows는 `%USERPROFILE%\controlroom`, macOS·Linux·Ubuntu main은 `~/controlroom`입니다. 각 프로젝트의 지침·스킬·문서는 실제 폴더에 있고 GitHub와 같은 상대경로를 사용합니다.

## 한 줄 설치

Git, Python 3.12 이상, GitHub SSH 키 접근을 준비합니다. 인증은 사용자가 관리합니다. Controlroom 저장소의 읽기 권한이 필요하며, `kitpush`에는 해당 저장소의 쓰기 권한이 필요합니다.

### Windows — PowerShell

PowerShell에서 다음 한 줄을 실행합니다. 설치 직후 같은 PowerShell과 새 명령 프롬프트(CMD)에서 `kitpull`, `kitpush`를 사용합니다.
현재 PowerShell 창의 실행 정책만 `RemoteSigned`로 설정합니다. 창을 닫으면 이 설정은 끝나며, 컴퓨터·사용자의 영구 설정이나 조직이 강제한 정책은 변경하지 않습니다.

```powershell
Set-ExecutionPolicy -Scope Process RemoteSigned -Force -ErrorAction Stop; $d=Join-Path $env:TEMP ([guid]::NewGuid()); git clone git@github.com:chaconne67/controlroom.git $d; if($LASTEXITCODE){throw 'Controlroom download failed'}; & (Join-Path $d '.controlroom/install.ps1')
```

### macOS·Linux — Bash/Zsh

```bash
d=$(mktemp -d) && git clone git@github.com:chaconne67/controlroom.git "$d" && bash "$d/.controlroom/install.sh" && . "$HOME/controlroom/.controlroom/shell/kit-aliases.sh"
```

### Ubuntu main — 기존 운영 코드 보존

조정실은 똑같이 `~/controlroom`에 설치합니다. `--main-server`는 기존 `~/projects/<프로젝트>` 코드 폴더에 에이전트 지침·스킬을 추가로 배치합니다.

```bash
d=$(mktemp -d) && git clone git@github.com:chaconne67/controlroom.git "$d" && bash "$d/.controlroom/install.sh" --main-server && . "$HOME/controlroom/.controlroom/shell/kit-aliases.sh"
```

다른 운영 코드 루트는 `--main-server` 뒤에 `--workspace "$HOME/operating-projects"`를 붙입니다. 기존 실제 폴더를 지정합니다. 제품 코드·`.git`·브랜치·원격·제품 문서·원본 스킬·환경·고객 자료는 그대로 보존하며, 지침의 기존 본문도 유지합니다. Exdigm처럼 코드가 다른 서버에 있어도 `~/controlroom/exdigm`의 지침·문서·스킬은 항상 설치합니다.

Venture 코드·지침·스킬·문서는 Controlroom Git의 `venture/`에 통합합니다. `controlroom/venture`에 별도 `.git`을 만들지 않으며 설치·동기화는 Controlroom 저장소 한 곳만 사용합니다. main의 기존 `~/projects/venture`와는 다른 작업 폴더입니다. 설치기는 에이전트 앱 로그인이나 프로젝트의 실행 환경·고객 자료를 대신 준비하지 않습니다.


설치 후 각 `~/controlroom/<프로젝트>/AGENTS.md`에서 실제 서버·DB·코드·저장소 위치를 확인합니다. 기본 역할명 `windows-control`은 모든 OS에서 공통으로 사용합니다.

```bash
kitpull
kitpull --verify
kitpush "변경 내용"
```

공유 원본·백업·복구와 기존 장비 전환 조건은 [저장소 README](../../README.md)를 따릅니다. 기존 코드 루트 `~/projects`는 조정실 원본과 구별합니다.
