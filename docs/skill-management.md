# Skill Management

이 저장소의 `skills/`가 직접 만든 독립 스킬과 외부에서 가져온 독립 스킬의 단일 원본이다.
live 위치(`~/.claude/skills`, `~/.agents/skills`, `~/.hermes/skills`, `<프로젝트>/.claude/skills`,
`<프로젝트>/.agents/skills`)에는 프로필 심링크만 있다. 도구가 관리하는 네이티브·플러그인
스킬은 이 저장소로 복제하지 않는다.

| 범위 | Codex | Claude Code | Hermes |
|---|---|---|---|
| 사용자 전역 | `~/.agents/skills` | `~/.claude/skills` | Linux·macOS `~/.hermes/skills`, Windows `%LOCALAPPDATA%\hermes\skills` |
| 프로젝트 | `<프로젝트>/.agents/skills` | `<프로젝트>/.claude/skills` | 사용자 전역 스킬 사용 |

Codex의 `~/.codex/skills/.system`과 플러그인 캐시, Claude Code의 내장 기능은 각 도구가
관리한다. 설치기는 이 영역을 수정하지 않는다.

처음 연결할 때 Codex·Claude Code의 전역 스킬 폴더에 같은 이름의 옛 사용자 스킬이 있으면
설치기가 백업한 뒤 키트 원본을 연결한다. 시스템 스킬, 플러그인, 이름이 겹치지 않는 도구 관리
스킬은 그대로 둔다.

## 공용 / 도메인 구분

**분류는 원본 위치가, 발동 범위는 프로필이 정한다.** 두 축을 분리해 두면 "무엇인지"와 "어디서 뜨는지"를 따로 바꿀 수 있다.

| | 원본 | 전역 프로필 | 프로젝트 프로필 |
|---|---|---|---|
| 공용 스킬 | `skills/common/<이름>` | O — **Claude·Codex·Hermes 모두** | 보통 불필요 |
| 도메인 스킬 | `skills/domains/<도메인>/<이름>` | **금지** | O (그 프로젝트에서만 발동) |

판정 기준은 "이 스킬이 특정 제품·업무 맥락을 알아야만 쓸모가 있는가"다. 그렇다면 도메인
스킬이다. 현재 도메인은 `ceoloan`, `exdigm`, `fundkeeper`, `rndlog`, `testbed`다.

공용 스킬은 **한쪽 전역 프로필에만 걸지 않는다.** 한쪽에만 걸면 같은 작업이 Claude냐 Codex냐에 따라 다른 규칙으로 처리되고, 그 차이가 프로필을 열어보기 전에는 드러나지 않는다. 도구 기본 기능과 이름이 겹치는 스킬(`code-review` 등)도 마찬가지로 양쪽에 연결한다 — 겹친다는 이유로 빼면 도구마다 다른 리뷰 기준을 쓰게 된다. 이름이 같으면 키트 원본이 그 이름의 정본이다.

`scripts/check-skill-deps.py`가 도메인 스킬의 전역 배치를 오류로 막고, `scripts/link-skill.py`도 같은 규칙을 적용해 잘못된 배치를 애초에 만들지 않는다.

도메인 스킬은 프로필을 연결한 폴더에서만 뜬다. 그 도메인 작업을 하는 폴더에 반드시 연결해야 한다 — 연결을 잊으면 스킬이 조용히 안 뜨는 것이 이 구조의 유일한 함정이다.

## 배치 규칙

- **배치의 정본은 프로필 심링크다.** 어떤 스킬이 어느 도구·프로젝트에서 발동하는지는 `claude/skills/`, `codex/skills/`, `projects/<프로젝트>/skills/`의 링크 존재 여부가 결정한다.
- `manifests/skills.json`은 심링크로 표현할 수 없는 스킬 간 의존관계와 외부 독립 스킬의
  출처만 담는다. 배치 정보를 여기 중복 기록하지 않는다.
- **사용자 스킬 원본은 키트 한 곳에만 둔다.** 공용은 `skills/common/`, 프로젝트 전용은
  `skills/domains/<도메인>/`에 둔다. `projects/<프로젝트>/skills/`와 live 경로에는 링크만 둔다.
- **제작 주체는 폴더를 늘리지 않고 manifest로 구분한다.** 외부에서 직접 가져온 독립 스킬만
  `manifests/skills.json`의 `external_sources`에 원본 URL과 revision을 기록한다. 직접 만든 스킬은
  기록하지 않는다.
- **플러그인은 도구가 관리한다.** 플러그인 스킬을 독립 스킬로 다시 복사하거나 링크하지 않는다.

## 일상 수정

조정실에서 스킬·지침을 수정하면 심링크 덕에 레포 작업트리가 이미 바뀌어 있다:

```bash
kitpush "변경 설명"
```

다른 조정실 장비:

```bash
kitpull
```

두 명령은 `main ↔ origin/main`만 사용한다. `kitpull`은 fast-forward 뒤 설치기를 실행하고, `kitpush`도 commit·재배치·push 전후에 설치기를 실행한다. 따라서 새 스킬 추가·삭제, Windows 파일 하드링크 교체, 등록 프로젝트 프로필 갱신까지 자동 반영된다.

비중앙 등록은 공용 파일과 자기 카드·도메인만 push할 수 있다. 중앙 `main` 등록은 모든 도메인을 조정할 수 있다.

## 새 스킬 추가

1. 공용이면 `skills/common/<이름>/SKILL.md`, 도메인 전용이면 `skills/domains/<도메인>/<이름>/SKILL.md` 작성 (frontmatter: `name`, `description` — description이 발동 조건의 정본).
2. 발동시킬 프로필에 링크 추가. `scripts/link-skill.py`가 원본 위치를 찾아 상대경로를 계산하고, 작업트리 표현과 무관하게 git 인덱스에 항상 심링크(mode 120000)로 등록한다:
   ```bash
   python scripts/link-skill.py add <이름> --claude --codex     # 공용
   python scripts/link-skill.py add <이름> --project <도메인>    # 도메인
   ```
   손으로 걸 때는(Linux 한정) 상대 심링크여야 한다:
   ```bash
   ln -s ../../skills/common/<이름> claude/skills/<이름>
   ln -s ../../../skills/domains/<도메인>/<이름> projects/<도메인>/skills/<이름>
   ```
3. 다른 스킬을 전제로 하면 `manifests/skills.json`의 `depends_on`에 추가.
4. `python3 scripts/check-skill-deps.py` 통과 확인 → `kitpush`.
5. 다른 설치 장비: `kitpull`.

작성 원칙은 `skills/common/skill-writing-guide/`와 `skills/common/prompt-guide/`를 따른다.

## 프로젝트 온보딩 (의존성 기반 선별 설치)

새 프로젝트에 키트를 적용할 때 에이전트가 수행하는 절차:

1. **필요 스킬 파악**: 프로젝트의 성격(도메인, 사용하는 도구, 반복 작업)을 분석해 필요한 스킬을 고른다. 그 프로젝트의 도메인 스킬(`skills/domains/<도메인>/`)은 전부, 공용 스킬은 전역에 없는 것만 고르면 된다. 각 SKILL.md의 description이 판단 기준이다.
2. **의존성 폐포 계산**: 고른 스킬마다 `manifests/skills.json`의 `depends_on`을 재귀로 따라가 필요한 스킬을 전부 포함시킨다. 의존 스킬이 이미 전역 프로필(`claude/skills`, `codex/skills`)에 있으면 프로젝트 프로필에 중복으로 넣지 않아도 된다.
3. **프로필 생성·커밋**:
   ```bash
   python scripts/link-skill.py add <이름> --project <프로젝트>   # 선별된 스킬마다
   # 프로젝트 전용 지침이 있으면 projects/<프로젝트>/CLAUDE.md, AGENTS.md 작성
   python3 scripts/check-skill-deps.py
   git add -A && git commit -m "Add <프로젝트> project profile" && git push
   ```
4. **프로젝트에 연결**:
   ```bash
   ./install.sh --project <프로젝트 경로> <프로젝트명>
   ```

프로젝트 지침 파일 소유권 판정:

1. 프로젝트 내용이 그 프로젝트에서만 쓰이면 → 프로젝트 폴더의 로컬 파일이 정본, 키트에 넣지 않는다.
2. 여러 기기·프로젝트가 공유할 내용이면 → 키트 `projects/<프로젝트>/`에 두고 live는 심링크로 연결한다.

## Windows 기기

PowerShell·CMD·Git Bash 중 편한 터미널에서 README의 최초 설치 명령을 실행한다. 개발자 모드나 관리자 권한은 필요 없다.

```powershell
git clone https://github.com/chaconne67/controlroom.git "$env:USERPROFILE\controlroom"
& "$env:USERPROFILE\controlroom\install.ps1" -Agent '<등록-이름>'
```

동작이 Linux와 다른 지점은 세 곳뿐이다:

- **live 연결** — 심링크 대신 junction(디렉토리)·하드링크(파일). Codex는 `.agents/skills`, Claude Code는 `.claude/skills`, Hermes는 `%LOCALAPPDATA%\hermes\skills`를 사용한다. Hermes의 기존 개인 스킬과 설정은 덮어쓰지 않는다.
- **프로필 항목** — 개발자 모드가 꺼진 Windows는 git이 `core.symlinks=false`로 clone하므로 `claude/skills/<이름>`이 링크가 아니라 대상 경로만 담긴 일반 파일이 된다. `install.ps1`과 `check-skill-deps.py`가 이 표현도 링크로 인정한다.
- **GBrain 런타임** — Linux용 원격 프록시·systemd 유닛은 건너뛴다. 등록 이름의 규칙 카드는 연결된다.

**주의**: 이 기기에서 프로필 링크를 손으로 만들면(탐색기 복사, `New-Item -ItemType File` 등) git에 일반 파일로 커밋되어 **Linux 서버의 설치가 조용히 깨진다**. 반드시 `scripts/link-skill.py`를 써서 인덱스에 심링크로 등록한다.

하드링크는 파일 교체 방식의 저장이나 Git checkout으로 연결이 끊길 수 있다. `kitpull`과 `kitpush`는 설치기를 다시 실행해 현재 저장소 원본에 하드링크를 재연결한다. 전역 지침을 직접 고칠 때는 `~/controlroom` 안의 원본을 편집하는 것이 정본 경로다.

## GBrain 에이전트 카드

GBrain 사용 규칙은 서버가 아니라 **에이전트 단위**로 다르다(같은 서버에 Codex·Hermes 프로필 등 여러 에이전트가 있을 수 있다). 그래서 공유 지침(CLAUDE.md·AGENTS.md)의 GBrain 섹션은 내용 대신 카드 참조만 갖는다:

- 카드 원본: `gbrain-cards/<에이전트>.md` (git 관리)
- 공식 설치: `./install.sh rndlog`처럼 에이전트 이름 하나를 사용한다. 전역 자산·카드·원격 프록시·프로젝트 프로필·연결 검증이 한 번에 실행된다.
- 이전 `./install.sh --gbrain rndlog` 명령은 호환을 위해 유지하지만 공식 경로와 같은 전체 설치를 실행한다.
- 카드가 없는 서버: 에이전트가 GBrain 규칙 전체를 건너뛴다 (임포트 실패해도 세션은 정상 — 2026-07-21 실측)

공간(사적 메모리) 구조 — GBrain 본체 서버(coconut-db) 기준:

- 등록부는 `~/.gbrain/memory/agent-policy.toml` 하나다. `[agents.<이름>]`의 `private_source`(필수)·`private_prefix`(선택)가 공간을 정의한다.
- 래퍼는 단일 스크립트 `gbrain-agent`(kit `gbrain/bin/`)뿐이다. `gbrain-<이름>` 심링크는 install.sh가 정책 파일에서 자동 생성하며, 호출된 이름으로 에이전트를 감지한다. 에이전트별 사본 스크립트를 만들지 않는다.
- 각 에이전트는 자기 공간과 공용(default)을 조회·기록한다. 기본 get·list·쓰기는 자기 공간, `--source default get|list|put|note`는 공용을 사용한다. `query`·`query-all`은 공용과 자기 공간만 검색하며, 일부 검색이 실패해도 실패 상태를 반환한다.
- 공용 쓰기는 정책의 `defaults.common_direct_write`, 에이전트의 `common_write`와 `write_sources`가 허용해야 한다. 경로는 `guardrails.common_write_prefixes`(agent·feedback·project·reference·incident·shared/common)로 제한한다. 다른 에이전트의 개인 공간은 접근하지 않는다.
- Windows 설치기는 Git Bash 프록시와 PowerShell·CMD용 `.cmd` 명령을 함께 연결한다. 설치 완료 검증에는 같은 명령으로 공용 운영 프로토콜 본문을 읽는 과정이 포함된다.

새 공간 에이전트 추가는 설치기의 단일 경로를 사용한다:

```bash
./install.sh --new analytics
```

설치기는 카드 생성, 중앙 GBrain 소스 생성, 기본 소스 `default` 즉시 복구·검증, 정책 등록, 중앙 래퍼 생성, 현재 서버 설치와 정책 조회 검증을 순서대로 수행한다. 원격 서버에서는 SSH로 중앙 설치기의 내부 등록 옵션을 호출한다.

```bash
./install.sh --new analytics --dry-run
```

dry-run은 생성할 소스·프리픽스·카드와 카드 본문을 출력하고 아무것도 변경하지 않는다. 실제 생성은 기존 카드·공간·정책을 덮어쓰지 않으며, 정책이 예상 구조와 다르면 중단한다. 생성된 카드는 자동 commit하지 않으므로 검토 후 저장소에 반영한다.

## 검증

```bash
python3 ~/controlroom/scripts/check-skill-deps.py
```

프로필 링크 해상, 고아 스킬, 의존성 누락, Codex system skill 부재를 검사한다.
