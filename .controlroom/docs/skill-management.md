# 스킬 관리

원본과 배치 목록을 하나씩 유지합니다. PC·노트북·메인서버의 공통 원본은 `~/controlroom/.controlroom/skills/<이름>`, 도메인 원본은 `~/controlroom/<프로젝트>/skills/<이름>`의 실제 폴더입니다. 프로젝트 스킬은 같은 조정실 프로젝트의 `.agents/skills`, `.claude/skills`에 배치합니다. `SKILL.md`와 직접 참조하는 scripts/references/agents 파일을 함께 관리합니다. 공유 manifest 안에서는 이름이 유일해야 합니다.

`.controlroom/manifests/skills.json`의 `sources`는 원본 위치, `profiles`는 전역·프로젝트 배치 목록, `depends_on`은 의존 관계입니다. 전역에는 공통 스킬만 배치하며 프로젝트 스킬의 의존 스킬은 전역 또는 같은 프로젝트에 있어야 합니다. FundKeeper는 TestBed의 원본을 배치 목록으로 사용합니다.

## 원본 변경과 동기화

앱 폴더 대신 위 원본을 편집합니다. 공통 지침 원본은 `.controlroom/codex/AGENTS.md`, `.controlroom/claude/CLAUDE.md`이며, 전역 역할 카드 원본은 `.controlroom/gbrain-cards/<역할>.md`입니다. 프로젝트별 GBrain 카드는 `<프로젝트>/.gbrain-agent.md`에 두고 해당 프로젝트 `AGENTS.md`에서 경로를 지정합니다. 새 규칙의 필요성과 승인 범위·기존 성공 동작을 확인하고 변경 전 상태를 잠근 뒤 수정·검증·리뷰합니다. 상위 지침 변경은 사용자 승인 범위를 기준으로 기존 게이트와 실제 소비자 검증을 유지합니다. GBrain 카드가 있으면 공용 문서 변경 계약에 맞춰 결과를 기록합니다.

```bash
python ~/controlroom/.controlroom/scripts/check-skill-deps.py
kitpush "변경 이유"
```

push는 원본을 저장·전송하고 앱이 읽는 사본을 갱신합니다. 다른 장비에서는 `kitpull`이 백업 후 최신 원본·사본을 함께 갱신합니다. `.agents/skills`, `.claude/skills`, Hermes의 설치기 관리 항목은 실제 복사본이며 연결 폴더가 아닙니다. 시스템 스킬·플러그인·개인 스킬은 별도 소유로 유지합니다. 다른 Hermes가 이미 가진 동명 스킬은 가져오지 않습니다.

모든 장비의 push 대상은 Venture 코드가 포함된 `~/controlroom`의 단일 Git입니다. 별도 제품 저장소의 코드·스킬·지침은 해당 제품의 Git 절차로 관리합니다. 이전 설치가 제품 저장소에 배치한 지침·스킬도 그 위치에 보존하며, Controlroom의 설치·동기화가 갱신하거나 제거하지 않습니다.

## 배치 추가·제거

원본 폴더를 만든 뒤 배치 목록을 관리합니다. 링크 생성이나 Git mode 120000 조작은 하지 않습니다.

```bash
python ~/controlroom/.controlroom/scripts/manage-skill.py add <이름> --global
python ~/controlroom/.controlroom/scripts/manage-skill.py add <이름> --project <프로젝트>
python ~/controlroom/.controlroom/scripts/manage-skill.py rm <이름> --project <프로젝트>
python ~/controlroom/.controlroom/scripts/check-skill-deps.py
kitpush "배치 변경 이유"
```

의존성·원본 범위를 만족하지 못하는 배치는 저장하지 않고 기존 목록을 복구합니다. 정상 업데이트는 목록에서 빠진 설치기 관리 항목도 백업 후 정리합니다. 코드·권한·실행 경로가 바뀌면 code-review-loop, 스킬 본문이 바뀌면 skill-review를 적용합니다.

## GBrain 역할 설치

```bash
bash ~/controlroom/.controlroom/install.sh rndlog
bash ~/controlroom/.controlroom/install.sh --new analytics --dry-run
```

기존 역할명과 중앙 정책·GBrain 저장공간 규칙은 유지합니다. 새 역할의 실제 생성은 기존 중앙 등록 절차를 사용하며 중앙 등록 권한이 별도로 필요합니다. 이 구조 정리는 서버의 GBrain 소스·정책·서비스를 재배치하지 않습니다. 모든 세션은 전역 `~/.gbrain-agent.md`를 먼저 읽고, 프로젝트 `AGENTS.md`가 별도 카드를 지정하면 프로젝트 카드를 추가로 읽습니다. 일반 작업 폴더에는 전역 카드만 적용됩니다. 자세한 권한·조회·쓰기 계약은 전역 카드와 공용 운영 프로토콜을 따릅니다.
