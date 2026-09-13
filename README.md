# Controlroom

지침·스킬·프로젝트 문서와 작업 재개 정보를 한 저장소에서 관리하는 조정실입니다.

## 처음 설치

Git 인증과 프로젝트 서버 SSH 접근을 준비한 뒤 다음 명령을 실행합니다. GitHub의 현재 공개 설정에 맞는 읽기 권한이 필요합니다.

### Windows — Git Bash

```bash
git clone https://github.com/chaconne67/controlroom.git ~/controlroom
bash ~/controlroom/install.sh windows-control
```

### macOS — Terminal / Linux — Bash

위와 같은 두 명령을 사용합니다. 설치 후 터미널을 새로 엽니다. 이미 controlroom을 설치한 장비에서는 clone을 반복하지 않고 설치기만 실행해 다시 연결할 수 있습니다.

## 매일 사용하는 명령

```bash
controlroom pull
controlroom push "변경 설명"
```

- `controlroom pull`: 통합 저장소의 지침·도구·프로젝트 문서를 함께 받고 설치 연결을 검증합니다. Venture는 기존 별도 Git 저장소에서 안전하게 받을 수 있는 커밋을 받습니다.
- `controlroom push`: 검토한 지침·도구·문서 변경을 한 커밋으로 저장하고 전송합니다. Venture는 이미 만든 커밋만 전송하며 미완료 코드·새 파일을 자동 stage하지 않습니다.
- 기존 `kitpull`, `kitpush`도 같은 기능의 호환 명령으로 사용할 수 있습니다.
- 작업을 마치거나 기기를 옮기기 전에 현재 계획의 재개 정보에 목표·승인 범위, 실제 서버/저장소와 branch/commit, 남은 변경, 마지막 검증 결과와 다음 행동을 기록합니다. 다른 장비에서는 받은 계획과 실제 서버 상태를 대조해 이어갑니다.

## 한 저장소의 구성

| 위치 | 역할 |
|---|---|
| `codex`, `claude`, `gbrain-cards` | 공통 지침과 조정실 역할 |
| `skills` | 공용 도구·프로젝트 스킬 |
| `projects/<프로젝트>/AGENTS.md`, `projects/<프로젝트>/skills` | 프로젝트 진입 지침과 스킬 연결 |
| `projects/<프로젝트>/docs` | 프로젝트 기획·리서치·현재 작업 계획 |
| `docs` | 설치·운영·유지보수 설명 |
| `install.sh`, `install.ps1`, `shell` | 설치와 일상 명령 |

각 조정실의 프로젝트 폴더는 등록된 기존 위치를 우선합니다. 프로젝트 `docs`는 이 저장소 안의 같은 프로젝트 문서로 연결됩니다. 별도 control-room-docs 저장소를 clone하거나 동기화하지 않습니다. 이전 문서 저장소의 README와 provenance는 `projects/README.md`, `projects/provenance.json`에 보존했습니다. 과거 계획에 있는 옛 경로는 기록 당시 기준이며 현재 경로는 이 README를 따릅니다.

개발 에이전트는 조정실에서 실행합니다. 원격 프로젝트의 코드·Git·데이터·미디어·빌드·테스트·배포는 기존 서버와 각 프로젝트의 공식 절차를 사용합니다. Venture는 조정실의 별도 로컬 코드 프로젝트입니다. Git/SSH 인증, 앱 로그인, 대화 세션과 기기 고유 기능은 해당 장비에서 관리합니다.

## 보존과 실패 처리

미커밋 변경·미전송 커밋·다른 브랜치·진행 중인 Git 작업이 있으면 pull을 중단해 작업을 보존합니다. push에서 충돌하면 이번 rebase를 취소하고 로컬 커밋을 보존합니다. 강제 push나 자동 stash로 덮어쓰지 않습니다. 일부 저장소가 실패하면 전체 성공으로 표시하지 않습니다.

통합 저장소의 origin과 별도 push 주소가 controlroom인지 확인하여 기획 문서를 이전 공개 키트로 보내지 않습니다. 기존 Git 로컬 등록 키 `kmh-agent-kit.*`, GBrain 역할명 `windows-control`, `kitpull`/`kitpush`는 설치 호환을 위해 유지합니다. 공개 범위는 저장소 소유자가 관리합니다.

## 추가 안내

- [장비 준비](docs/onboarding-new-server.md)
- [스킬 관리](docs/skill-management.md)
- [GBrain 운영](docs/gbrain-operating-guide.md)
- [문제 해결](docs/troubleshooting.md)
- [프로젝트 문서 목록과 보관 이력](projects/README.md)
- [통합 계획](docs/controlroom-unification.md)

기존 역할 설치(`bash install.sh <역할>`)와 프로젝트 등록(`bash install.sh --project <경로> <프로필>`)은 유지합니다. 새 조정실에는 `windows-control` 역할을 사용합니다.

기존 `~/kmh-agent-kit`와 `~/projects/_control-docs` 이름은 호환 링크로 유지합니다. 파일은 `~/controlroom`에 한 벌만 있습니다. 다른 장비에 옛 저장소가 남아 있다면 새 설치기는 이를 자동 삭제하지 않습니다. 그 장비의 미전송 변경을 먼저 확인해 통합한 뒤 옛 폴더를 보관하고 호환 링크로 바꿉니다.
