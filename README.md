# Controlroom

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

## 설치되는 구조

```text
<사용자>/controlroom/
  .git/
  .controlroom/             # 공통 설치기·지침·스킬·운영 문서
  ceoloan/
  exdigm/
  fundkeeper/
  gbrain/
  im-not-ai/
  rndlog/
  testbed/
  venture/                 # 같은 Controlroom Git에 포함된 코드·지침·스킬·문서
  ziin/
```

각 프로젝트에서 `AGENTS.md`와 `CLAUDE.md`를 읽습니다. 서버·DB·코드 위치·GitHub 저장소와 작업 경계는 해당 지침에 있으며, `docs`에는 계획과 재개 정보, `skills`에는 스킬 원본을 둡니다. Codex·Claude용 `.agents/skills`, `.claude/skills`는 설치기가 배치합니다. 공통 지침과 스킬도 각 앱의 사용자 폴더에 설치합니다. Git·백업에 비밀값을 게시하지 않으며 `.env`, 로그인, 고객 자료는 별도로 관리합니다.

## 동기화

```bash
kitpull
kitpush "변경 내용"
```

- `kitpull`: 최신 Controlroom을 받은 뒤, 바뀔 파일을 압축 백업하고 지침·문서·스킬·Venture 코드를 적용합니다. 수정 중인 관리 파일도 백업 후 최신 버전으로 교체하므로 다른 장비로 넘길 변경은 먼저 `kitpush`로 올립니다. 실패하면 이전 상태로 복구합니다.
- `kitpush`: Controlroom 지침·스킬·문서와 Venture 코드의 변경을 한 번에 커밋·전송하고 앱 배치를 갱신합니다. 실행 전 변경 내용을 검토·검증합니다. `.env`·고객 자료·브라우저 로그인 상태는 전송 대상에서 제외합니다.
- main에서도 같은 명령을 사용합니다. 동기화 대상은 Venture를 포함한 단일 `controlroom` 저장소이며 기존 `~/projects` 운영 저장소의 Git을 동기화하지 않습니다.

## 백업과 확인

```bash
kitpull --verify
kitpull --restore <백업ZIP>
```

설치·갱신 백업은 `~/backups/controlroom`에 저장합니다. 기존 `controlroom`이 옛 키트로 연결된 폴더이면 연결과 기존 원본을 먼저 백업한 뒤 실제 폴더로 설치합니다. 기존 `kmh-agent-kit`, `projects`와 별도 서버의 운영 코드를 삭제하지 않습니다. 사용자가 기존 `projects`를 직접 지우기 전에는 환경·고객 자료·작업 결과·미전송 작업을 별도로 보관해야 합니다. 이 내용은 GitHub 설치만으로 복원되지 않습니다.

현재 데스크톱과 main의 실제 전환 시험은 사용자가 수행합니다. 자동 검사와 격리 설치 성공을 사용자의 장비 적용 완료로 표시하지 않습니다. 자세한 변경 계약은 [.controlroom/docs/controlroom-unification.md](.controlroom/docs/controlroom-unification.md), 프로젝트 작업은 각 `docs/README.md`를 따릅니다.
