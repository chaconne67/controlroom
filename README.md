# Controlroom

조정실의 공통 지침·스킬·프로젝트 계획을 관리합니다. 모든 조정실 장비의 실제 작업 폴더는 **`~/projects`**입니다. Windows의 `~`는 사용자 폴더, macOS·Linux는 HOME입니다.

## 처음 설치하거나 최신본 적용

Git과 Python 3.12 이상, 이 비공개 GitHub 저장소의 읽기 권한을 준비합니다. 아래 설치 파일을 다운로드한 폴더에서 실행합니다. 설치기는 인증된 Git으로 최신본을 먼저 받아 확인하고, 기존 대상을 압축 백업한 뒤 적용합니다.

### Windows — PowerShell

[install.ps1](.controlroom/install.ps1)을 다운로드한 뒤:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\install.ps1 -Agent windows-control
```

### macOS·Linux — Bash

[install.sh](.controlroom/install.sh)을 다운로드한 뒤:

```bash
bash ./install.sh windows-control
```

설치 후 터미널을 새로 엽니다. 설치 파일은 임시로 다운로드한 어디에서든 실행할 수 있습니다. 최종 저장 위치는 항상 `~/projects`이며 별도의 `~/controlroom` 체크아웃은 필요하지 않습니다. 이미 설치한 장비에서 다시 실행해도 최신본을 적용합니다.

## 일상 동기화

```bash
controlroom pull
controlroom push "변경 설명"
controlroom verify
```

- `pull`: 지침·도구·계획과 등록된 Venture 코드를 최신본으로 교체합니다. 수정 중인 파일·로컬 커밋·다른 브랜치도 먼저 백업하므로 기존 파일이 있다는 이유로 중단하지 않습니다.
- `push`: 승인·검토한 조정실 지침·도구·계획을 저장하고 GitHub로 보낸 뒤 실행 앱의 사본도 갱신합니다. Venture는 이미 만든 커밋만 전송합니다. 작업 중인 코드를 자동으로 커밋하지 않습니다. 충돌하면 rebase를 취소해 로컬 커밋을 보존합니다.
- `verify`: 실제 폴더 구조와 앱에서 읽는 지침·스킬의 내용이 원본과 같은지 확인합니다.
- `kitpull`, `kitpush`는 같은 실행 경로를 사용하는 기존 명령입니다.

기기를 옮기기 전 현재 계획에 목표·승인 범위, 실제 서버/저장소·브랜치·커밋, 남은 변경, 마지막 검증 결과와 다음 행동을 기록하고 push합니다. 다음 장비에서는 pull 후 계획과 실제 서버 상태를 대조합니다.

## 실제 구조

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

사용자 조정실은 로컬 데스크탑이며 main 서버에는 자동 수정용 조정실을 함께 둘 수 있습니다. 같은 저장소와 설치·동기화 명령을 사용하되, main의 기존 운영 코드 폴더와 조정실 프로젝트 폴더는 별도로 등록합니다. Exdigm은 main의 Codex에서도 SSH로 전용 서버의 debug worktree에 접근합니다. 실제 설치 위치·인증·검증 상태는 [자동 수정 방침](exdigm/docs/operational-error-triage-repair-policy-20260918.md)을 확인합니다.

현재 main의 조정실은 옛 등록 구조로 설치되어 있습니다. 서버 조정실의 전환 계획이 승인·검증되기 전에는 새 설치기를 main의 운영 코드 루트 `~/projects`에 적용하지 않습니다.

개발 에이전트는 조정실에서 실행합니다. 서버의 제품 코드·Git·데이터·미디어·빌드·테스트·배포는 각 프로젝트의 기존 SSH 절차와 실제 서버 경로를 따릅니다. Venture의 업무 스킬은 Venture 저장소의 `skills`가 원본입니다. 조정실 Git은 Venture와 고객 자료·환경 파일·인증 정보를 자동 수집하지 않습니다.

## 백업과 복구

백업은 **`~/backups/controlroom/<날짜>-<번호>.zip`**에 보관합니다. 교체할 폴더 전체와 숨김 파일·Git 상태·로컬 변경을 포함하고 압축 파일의 내용까지 검사합니다. 외부 자료를 가리키는 링크는 연결 정보만 보관하며 외부 자료를 따라가거나 지우지 않습니다. 다운로드·사전 검사에 실패하면 기존 설치는 건드리지 않습니다. 적용 중 실패하면 같은 백업에서 자동으로 이전 상태를 복구합니다.

일반 업데이트는 다운로드한 최신본을 적용하는 것이 목적입니다. 같은 이름의 옛 파일과 최신본에서 없어진 관리 파일은 교체·정리합니다. Venture의 환경 파일·고객 자료·독립 실행 자료, 플러그인·시스템·사용자 개인 스킬과 다른 Hermes의 기존 스킬은 유지합니다. 추가로 과거 상태를 직접 복원할 때:

```bash
controlroom restore "백업 ZIP의 전체 경로"
```

복원은 업데이트 직전의 Git 상태와 파일로 돌아가는 작업입니다. 복원 후 새 터미널에서 명령을 실행합니다. 옛 `~/controlroom`, `~/kmh-agent-kit`, `~/projects/_control-docs`는 성공한 전환에서 백업 후 제거하며 호환 링크로 남기지 않습니다. GBrain 역할명과 서버 런타임은 별도의 기존 운영 계약을 유지합니다.

## 운영 설명

- [장비 준비](.controlroom/docs/onboarding-new-server.md)
- [스킬 관리](.controlroom/docs/skill-management.md)
- [GBrain 운영](.controlroom/docs/gbrain-operating-guide.md)
- [서버 통합과 실제 운영 상태](.controlroom/docs/production-server-consolidation-20260916.md)
- [승인된 구조·업데이트 계획](.controlroom/docs/controlroom-unification.md)

과거 문서의 옛 경로는 기록 당시 상태이며, 현행 조정실 구조는 이 README를 따릅니다.
