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

### macOS·Linux·Ubuntu 메인서버 — Bash/Zsh

```bash
d=$(mktemp -d) && git clone git@github.com:chaconne67/controlroom.git "$d" && bash "$d/.controlroom/install.sh" && . "$HOME/controlroom/.controlroom/shell/kit-aliases.sh"
```

PC·노트북·메인서버 모두 같은 명령으로 `~/controlroom`에 설치합니다. 지침·문서·스킬은 조정실의 프로젝트 폴더에서 관리하며, 실제 코드 위치·서버·DB·GitHub 저장소는 각 프로젝트 지침에서 확인합니다. Exdigm처럼 코드가 다른 서버에 있어도 조정실 폴더는 항상 설치합니다.

기존 `~/projects` 등 운영 코드 폴더는 설치·동기화 대상이 아닙니다. 코드·Git·문서·지침·스킬·환경·고객 자료를 그대로 보존합니다. 이전 메인서버 설치는 위 한 줄을 다시 실행해 통일된 방식으로 전환합니다. 운영 저장소에 이미 배치된 파일은 수정하거나 삭제하지 않습니다.

Venture 코드·지침·스킬·문서는 Controlroom Git의 `venture/`에 통합합니다. `controlroom/venture`에 별도 `.git`을 만들지 않으며 설치·동기화는 Controlroom 저장소 한 곳만 사용합니다. main의 기존 `~/projects/venture`와는 다른 작업 폴더입니다. 설치기는 에이전트 앱 로그인이나 프로젝트의 실행 환경·고객 자료를 대신 준비하지 않습니다.


설치 후 각 `~/controlroom/<프로젝트>/AGENTS.md`에서 실제 서버·DB·코드·저장소 위치를 확인합니다. 기본 역할명 `windows-control`은 모든 OS에서 공통으로 사용합니다.

```bash
kitpull
kitpull --verify
kitpush "변경 내용"
```

공유 원본·백업·복구와 기존 장비 전환 조건은 [저장소 README](../../README.md)를 따릅니다. 기존 코드 루트 `~/projects`는 조정실 원본과 구별합니다.
