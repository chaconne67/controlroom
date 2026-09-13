# 조정실 장비 준비와 기존 역할 설치

## 개요

설치 명령에 넣는 값은 장비의 호스트명이 아니라 GBrain 공간·정책·카드를 고르는 **등록 이름**입니다.

| 상황 | 설치 방식 |
|---|---|
| 새로운 프로젝트 역할을 처음 등록 | `--new` 사용 |
| 기존 역할을 새 장비에 설치 | 기존 등록 이름 사용 |

GBrain 등록 이름은 영문 소문자·숫자·중간 하이픈으로 된 1~32자입니다. 밑줄은 허용되지 않으므로 `abc_project`는 `abc-project`로 등록합니다.

최초 설치 뒤에는 키트를 설치한 장비에서 `kitpull`, `kitpush`만 사용합니다. 최초 설치가 저장한 등록 이름으로 공용 자산과 매칭 도메인을 자동 선택합니다.

운영 서버 설치는 이 절차의 기본값이 아닙니다. Coconut·RNDLOG·CEO Loan·Exdigm 운영 서버는 키트와 분리해 현재 상태를 유지합니다. 다른 서버도 명시적으로 선택한 경우에만 아래 절차를 적용합니다.

## 한 줄 설치

데스크톱·노트북에서 같은 조정실을 이어받을 때는 Windows·macOS·Linux 모두 호환 등록명 `windows-control`을 사용합니다. 아래 `~`는 Windows의 `USERPROFILE`, macOS·Linux의 `HOME`이며 기존에 등록한 프로젝트 경로를 우선합니다.

| 운영체제 | 기본 터미널 | 최초 설치 명령 |
|---|---|---|
| Windows | Git Bash | `curl -fsSL https://raw.githubusercontent.com/chaconne67/kmh-agent-kit/main/install.sh \| bash -s -- windows-control` |
| macOS | Terminal | `curl -fsSL https://raw.githubusercontent.com/chaconne67/kmh-agent-kit/main/install.sh \| bash -s -- windows-control` |
| Linux | Bash | `curl -fsSL https://raw.githubusercontent.com/chaconne67/kmh-agent-kit/main/install.sh \| bash -s -- windows-control` |

Windows는 Git for Windows에 포함된 Git Bash가 필요합니다. 위 표의 공식 설치 명령은 세 OS에서 같습니다.

```bash
curl -fsSL https://raw.githubusercontent.com/chaconne67/kmh-agent-kit/main/install.sh | bash -s -- windows-control
```

`install.sh`가 Windows를 감지해 저장소의 `install.ps1`을 내부 호출하므로 사용자가 별도 PowerShell 순서를 수행하지 않습니다. 설치 후 새 터미널을 열면 PowerShell·CMD·Git Bash·Linux·macOS 어디서든 `kitpull`, `kitpush`를 사용할 수 있습니다.

이 한 줄은 `~/kmh-agent-kit`의 공용 지침·스킬·카드와 다섯 프로젝트 프로필을 연결합니다. 비공개 `control-room-docs`를 `~/projects/_control-docs`에 복원하고 각 프로젝트의 `docs`를 해당 문서 원본에 연결합니다. `venture`가 없으면 별도 GitHub 저장소에서 clone합니다. 기존 프로젝트 등록 경로와 사용자 작업은 보존하고 다른 실제 docs 폴더는 자동으로 옮기지 않습니다.

### 처음 등록하는 `abc_project` 역할

중앙 Linux 환경에서 먼저 생성 내용을 확인합니다.

```bash
curl -fsSL https://raw.githubusercontent.com/chaconne67/kmh-agent-kit/main/install.sh | bash -s -- --new abc-project --dry-run
```

확인 후 실제 설치:

```bash
~/kmh-agent-kit/install.sh --new abc-project
```

처음부터 바로 설치하려면 다음 한 줄만 실행합니다.

```bash
curl -fsSL https://raw.githubusercontent.com/chaconne67/kmh-agent-kit/main/install.sh | bash -s -- --new abc-project
```

그 밖의 서버는 자동 배포 대상이 아닙니다. 설치하기로 별도 결정한 장비에서만 위 한 줄 명령을 실행합니다.

## 그 외

### 설치 전 조건

- 키트는 설치 명령을 실행한 사용자 계정에 전역 설치됩니다.
- Windows에서는 Git for Windows와 Git Bash가 설치되어 있어야 합니다.
- 키트 첫 clone은 공개 HTTPS를 사용합니다. 전체 조정실 복원에는 비공개 `chaconne67/control-room-docs`를 읽는 Git 인증이 필요하고, 변경을 올리려면 각 저장소의 쓰기 권한도 필요합니다.
- GBrain 확인에는 `chaconne@49.247.45.243` SSH 접근이 필요합니다. 각 프로젝트 서버의 SSH 등록은 별개이며 프로젝트 프로필의 목적지로 확인합니다.
- 에이전트 앱과 필요한 로컬 도구의 설치·로그인은 장비별로 준비합니다. 인증값·프로그램 설정·대화 세션을 키트로 복제하지 않습니다. Windows 전용 기능은 실제 사용하는 환경에서 따로 검증합니다.
- 기존 `~/.claude`, `~/.codex`, `~/.gbrain` 일반 파일은 설치기가 백업합니다.

현재 상태 확인:

```bash
ls -ld ~/.claude ~/.codex ~/.gbrain ~/kmh-agent-kit 2>/dev/null || true
ssh -o BatchMode=yes -o ConnectTimeout=10 chaconne@49.247.45.243 true
```

### 신규 생성 범위

`--new abc-project`는 다음 항목만 새로 만듭니다.

- 중앙 GBrain 소스 `abc-project`
- 중앙 정책의 `[sources.abc-project]`, `[agents.abc-project]`
- 전용 쓰기 경로 `agents/abc-project/private`
- 저장소 카드 `gbrain-cards/abc-project.md`
- 현재 서버의 `~/.gbrain-agent.md`, `~/.local/bin/gbrain-abc-project`

기존 공간·정책·카드는 덮어쓰지 않습니다. 정책 충돌이 있으면 중단합니다. 정책 변경 전 백업은 `agent-policy.toml.backup-날짜-시각`으로 남깁니다.

### 중앙 GBrain 보호 검증

새 공간을 추가한 뒤 설치기가 자동으로 확인합니다.

- 중앙 기본 소스: `default`
- 해석 단계: `brain_default`
- 공용 운영 프로토콜 조회
- 새 에이전트 정책 조회

이 검증 중 하나라도 실패하면 설치 성공으로 보고하지 않습니다.

### 설치된 장비 업데이트

Linux·macOS·Windows PowerShell·CMD·Git Bash에서 같은 명령을 실행합니다.

```bash
kitpull
```

공용 또는 현재 서버의 매칭 도메인 변경을 올릴 때:

```bash
kitpush
```

최초 설치가 등록 이름을 Git 로컬 설정에 저장하므로 이름을 다시 입력하지 않습니다.

- `kitpull`은 키트와 조정실 계약의 문서·Venture 커밋을 받은 뒤 프로필·docs 연결을 확인합니다. 변경·미전송 커밋·다른 브랜치·분기 상태는 보존하고 안전하게 받을 수 없는 저장소를 알립니다.
- `kitpush`는 키트의 기존 허용 범위와 검토한 문서 변경을 저장·전송합니다. Venture는 이미 만든 커밋만 push하며 미커밋 코드·미추적 파일은 자동으로 stage하지 않습니다.
- 키트는 `main ↔ origin/main`을 사용하고 조정실 Git 저장소는 manifest의 원격·브랜치를 확인합니다. 원격 제품 서버의 코드·배포는 각 프로젝트의 기존 경로를 따릅니다.
- 충돌이나 인증 실패가 있으면 사용자 작업을 보존하며 완료한 저장소와 남은 저장소를 구분합니다.
- 프로젝트 전용 등록은 기존 도메인 제한을 유지하고, `main`과 `windows-control` 등록은 모든 키트 도메인을 다룹니다.

`./install.sh --project <경로> <프로필>`로 연결한 프로젝트는 로컬 Git 설정에 저장됩니다. 재설치와 두 동기화 명령은 등록 경로를 우선하고 해당 프로필·docs를 다시 연결합니다.

`windows-control`은 프로젝트 계약을 매번 읽습니다. 다섯 프로젝트의 지침·스킬은 kit, 기획 문서는 비공개 `control-room-docs`, Venture 지침·스킬·소스는 Venture Git이 정본입니다. 설치된 파일과 새 에이전트 세션이 실제로 읽은 상태를 구분해 확인합니다.

사용자가 만든 전역 스킬은 kit 정본에서 Codex와 Claude Code에 함께 연결됩니다. 같은 이름의 옛
사용자 스킬은 백업한 뒤 교체합니다. 도구 기본 스킬과 플러그인 캐시, 키트에 없는 도구 스킬은
각 도구가 계속 관리합니다. FundKeeper 폴더에는 Testbed 작업 스킬도 함께 연결됩니다.

### 현재 작업 이어받기

작업을 마치거나 장비를 옮기기 전에 기존 작업 계획에 목표·승인 범위, 실행 서버/저장소와 branch/commit, 남은 변경, 마지막 검증 결과와 다음 행동을 기록합니다. 프로젝트 `docs/README.md`에서 진행 중 계획을 연결하고 병렬 작업은 각 계획에서 관리합니다.

이전 장비에서 `kitpush`의 저장 결과를 확인한 뒤 새 장비에서 `kitpull`을 실행합니다. 현재 GBrain 카드·공용 최신 운영 맥락·프로젝트 문맥과 계획의 재개 정보를 읽고, 실제 서버 Git 상태를 대조합니다. GBrain에는 장기 결정과 재사용 지식만 남기며 대화 원문이나 단순 진행 로그를 동기화하지 않습니다.

### 설치 결과 확인

```bash
python3 ~/kmh-agent-kit/scripts/check-skill-deps.py
readlink ~/.gbrain-agent.md
```

신규 `abc-project`:

```bash
gbrain-abc-project policy
```

Ceoloan:

```bash
gbrain-ceoloan policy
```

FundKeeper:

```bash
gbrain-fundkeeper policy
```

### 중앙 GBrain 서버만 확인할 항목

일반 애플리케이션 서버에서는 로컬 GBrain DB나 `gbrain-http.service`를 만들지 않습니다. 아래 명령은 `49.247.45.243`에서만 실행합니다.

```bash
~/.gbrain/bin/gbrain_with_google_env.sh doctor --fast
~/.gbrain/bin/gbrain_with_google_env.sh sources current
systemctl --user status gbrain-http.service --no-pager
```

### Windows

상단 표의 Git Bash 한 줄을 실행합니다. 설치기는 사용자 PATH에 `kitpull.cmd`·`kitpush.cmd`를 추가하고 Git Bash의 셸 설정도 연결합니다. Windows는 junction과 하드링크를 사용하며 Linux 전용 systemd 서비스는 설치하지 않습니다.

### 주의

- 기존 역할을 새 장비에 설치할 때는 `--new`를 쓰지 않고 위 표의 등록 이름을 사용합니다.
- 신규 카드 파일은 자동 commit·push하지 않습니다. 내용을 검토한 뒤 저장소에 반영합니다.
- Coconut·RNDLOG·CEO Loan·Exdigm 운영 서버는 자동 설치 대상이 아닙니다.
- 다른 서버 설치도 장비별로 명시적으로 선택한 경우에만 수행합니다.
- API 키, DB 비밀번호, OAuth 토큰은 저장소와 GBrain 카드에 넣지 않습니다.
