# ZiiN 프로젝트

## 조정실

- 작업 위치는 이 프로필을 연결한 현재 프로젝트 폴더이며 기본값은 `~/projects/ziin`입니다. `~`는 Windows의 `USERPROFILE`, macOS·Linux의 `HOME`입니다. 이미 등록된 사용자 지정 경로를 우선합니다.
- 개발 에이전트는 선택한 조정실 장비에서만 실행합니다. 아래 서버의 코드·Git·검증·배포 경로는 SSH로 사용하며 제품 기능의 기존 AI·LLM 실행은 보존합니다.
- 새 세션은 `~/.gbrain-agent.md`를 읽고, 공용 최신 `project/windows-control-tower-operating-context`와 `project/ziin-operating-context`를 확인합니다.
- 아래 Linux 경로와 명령은 명시된 원격 호스트의 셸에서 실행합니다. 조정실 OS에 맞춰 서버 경로를 바꾸거나 운영 코드를 조정실에 복제하지 않습니다.
- 기획·리서치·작업 계획은 `docs/README.md`에서 찾습니다. `docs`는 통합 controlroom 저장소의 `projects/ziin/docs`에 연결되며 기본 정본은 `~/controlroom/projects/ziin/docs`입니다.
- 작업을 이어받을 때는 `docs/README.md`의 진행 중 작업 링크와 해당 계획의 재개 정보를 읽고 실제 서버 Git 상태와 대조합니다. 작업을 마치거나 옮기기 전에 그 계획에 재개 정보를 갱신하며 병렬 작업은 각 계획에서 관리합니다.

## 역할

- 이 폴더는 ZiiN의 조정실입니다. 실제 코드·실행 및 검증 자료·코드 Git·배포 대상은 main `chaconne@49.247.192.127:/home/chaconne/projects/ziin`입니다.
- ZiiN은 Exdigm에서 운영 중인 헤드헌팅 업무 시스템을 다른 헤드헌팅 회사에도 제공할 수 있도록 범용화한 제품입니다.
- 제품 사실의 최종 기준은 검증된 Exdigm 운영 코드입니다. ZiiN 문서와 코드가 다르면 실제 코드를 확인한 뒤 문서와 GBrain을 갱신합니다.
- 조정실 에이전트가 SSH로 main의 `/home/chaconne/projects/ziin`에서 개발·검증합니다. `docs/implementation/`과 `docs/product/`의 기획 원본은 조정실 문서 경로이며, 나머지 코드·디자인·운영 문서 경로는 원격 저장소 기준입니다. 배포는 별도 명시적 요청이 있을 때 해당 제품 Compose 정의와 검증·복구 경로를 대조해 실행하며 옛 `scripts/deploy.sh`를 그대로 실행하지 않습니다.

## 정본

2026-09-17 22:33 KST 실제 인계 이후의 운영 주소는 `chaconne@49.247.192.127`입니다. 2026-09-18 00:35 KST 공개 DNS 원본 14개 이름 모두 새 main이고 가비아 권한 서버 3곳 및 Google/Cloudflare에서 이를 확인했습니다. DNS 캐시의 옛 공개 입구와 SQL/CLI/자료 호환 주소는 새 main으로 전달합니다. 옛 서버의 호환 전달·별도 복구 백업·제외 서비스 의존성은 남아 있으므로 DNS 변경만으로 해지/삭제하지 않습니다. 최신 운영 상태·복구 경로는 `~/controlroom/docs/production-server-consolidation-20260916.md` 최신 절과 main `/srv/consolidation/infra/README.md`를 먼저 확인합니다. 과거 GBrain 프로젝트 맥락이나 고유 스킬에 남은 옛 서버·Swarm 배포 명령보다 이 현행 주소를 우선합니다. 옛 운영 writer는 정지·읽기 전용이므로 그 서버에서 배포하거나 DB/자료를 쓰지 않습니다.

| 구분 | 정본 |
|---|---|
| SSH / 작업 루트 | `chaconne@49.247.192.127` / `/home/chaconne/projects/ziin` |
| GitHub | `git@github.com:chaconne67/ziin.git` |
| 목표 브랜치 | `main` |
| 운영 도메인 | `https://www.ziin.site` |
| 구축·배포 지시 | `docs/implementation/지니-챗봇-작업지시.md` |
| 디자인 시스템 | `docs/design/design.md` |
| 제품 사실 | `docs/product/지인-시스템-소개.md`와 검증된 Exdigm 코드 |
| 랜딩 문구 | `docs/product/랜딩-문구.md`, `docs/product/카피액기스.md` |
| 확정 랜딩 원본 | `docs/design/final/시안-D.html` |
| 확정 대화창 원본 | `docs/design/final/지니-대화창UI.html` |
| 배포 정의 | `/srv/consolidation/infra/compose.production.ziin.json` + `compose.activate.ziin.json`, Compose 프로젝트 `production-ziin` |
| 운영 서비스 | `production-ziin-web-1`, `production-ziin-nginx-1` |
| 운영 DB | main `migration-replicas-postgres-1` / `ziin` / 앱망 `172.30.40.10:5432` |
| 옛 공개 입구 | `49.247.45.243` → main 전달; 옛 writer는 정지 |

- 공개 제품명은 `ZiiN`, AI 이름은 `지니`입니다.
- 과거 문서의 `Ziin`, `G-in`, `지인`은 검색용 별칭으로만 취급합니다.

## 서버 코드 작업

- 조정실 진입 폴더는 `C:\Users\chaconne\projects\ziin`, main 코드 저장소는 `/home/chaconne/projects/ziin`입니다. 두 장비 모두 사용자 루트의 `projects/<프로젝트>` 구조를 사용합니다. 조정실은 지침·스킬·기획의 진입점이고 서버 폴더는 실제 `.git`과 코드를 가진 독립 저장소입니다.
- main의 이 폴더에서 해당 프로젝트의 코드를 수정·검증하고, 이번 변경 파일만 커밋한 뒤 기존 `origin`의 `main` 브랜치로 푸시합니다. 경로 이동을 이유로 Git 저장소·브랜치·원격을 다시 만들지 않습니다.

```text
ssh chaconne@49.247.192.127
cd /home/chaconne/projects/ziin
git status --short
```

위 `cd`와 Git 명령은 SSH 접속 후 서버 셸에서 실행합니다. 코드 검증·커밋 후 푸시는 `git push origin main`입니다. 기존 수정·신규 파일을 보존하고 이번에 검증한 변경만 포함합니다.

## 작업 전 GBrain

- 먼저 전역 GBrain 카드 `~/.gbrain-agent.md`를 읽고 그 규칙을 따릅니다.
- 아래 문서를 작업과 직접 관련된 범위에서 조회합니다.
  - `project/ziin-operating-context`
  - `project/ziin-landing-page`
  - `feedback/ziin-copy-and-design-rules`
  - `project/ziin-design-assets`
  - `project/ziin-chatbot-deploy`
- 제품 기능을 다룰 때는 관련 Exdigm 문서와 실제 운영 코드까지 확인합니다.
- 권위 순서는 검증된 실제 코드·운영 상태, 최신 사용자 결정과 작업 지시, 프로젝트 문서, GBrain입니다.

## 공식 작업 경로

1. SSH로 main의 실제 저장소 Git 상태와 기존 사용자 변경, 보호할 원본을 확인합니다.
2. GBrain과 해당 작업 지시를 읽습니다.
3. 변경 범위·보호 불변조건·검증 기준을 잠그고 일괄 승인을 받습니다.
4. 핵심 외부 연동은 구현 전에 실제 환경에서 짧게 검증합니다.
5. 승인된 단일 실행 경로를 구현하고 같은 경로로 테스트합니다.
6. 실행 동작·데이터·권한·외부 효과·배포 경로를 바꾸면 `code-review-loop`를 수행합니다.
7. 검증된 코드만 커밋합니다.
8. 배포한 커밋과 운영 결과를 직접 확인합니다.

- 직접 확인하지 못한 상태를 성공으로 보고하지 않습니다.
- 운영 배포는 RNDLOG·Exdigm·CEO Loan에서 검증된 공통 원칙인 단일 진입점, clean `main`, 이미지 커밋 대조, 마이그레이션 분리, 상태 검사를 따릅니다.

## 랜딩과 지식 경계

- UI를 만들거나 고치기 전에 `docs/design/design.md`를 읽고, 변경 뒤 같은 기준으로 다시 검증합니다.
- `docs/design/final/시안-D.html`과 `docs/design/final/지니-대화창UI.html`은 확정 원본이므로 수정하지 않습니다.
- 서비스용 `index.html`은 확정 랜딩 원본의 정확한 복사본에 로컬 위젯 스크립트 한 줄만 추가합니다.
- 공개 지식에는 검증된 제품 기능·도입·가격 원칙·확정 카피만 넣습니다.
- 경쟁사명, 내부 코드·서버·인증 정보, 내부 범용화 메모는 공개 지식에서 제외합니다.
- 문서나 코드에 없는 제품 사실을 만들지 않습니다.

## 운영 안전 경계

- 같은 main의 Coconut/FundKeeper, RNDLOG, CEO Loan, GBrain, PostgreSQL/MySQL과 공유 네트워크는 보호 대상입니다. Exdigm 앱은 기존 별도 서버에 유지합니다.
- ZiiN 컨테이너와 `ziin` 데이터베이스·롤만 만들거나 변경합니다.
- Exdigm 데이터베이스의 데이터·설정·비밀번호는 읽지 않습니다.
- 새 호스트 포트는 80·443만 사용합니다.
- 기존 컨테이너 재시작, 전체 compose 종료, 이미지·볼륨·네트워크 정리를 하지 않습니다.
- `.env`의 비밀값은 출력·로그·Git·GBrain에 남기지 않습니다.
- 공개 방문자 입력은 도구가 없는 선택된 LLM 공급자 API로만 보냅니다. 개발용 에이전트 실행기와 그 지침·자격 증명을 공개 런타임에 연결하지 않습니다.
- LLM 공급자 장애 때 다른 공급자로 자동 우회하지 않습니다.
- 기본 공급자는 Gemini이며 기본 모델은 `gemini-3.7-flash`입니다. OpenAI는 환경변수로 명시했을 때만 선택합니다.

## Git

- 현재 조정실의 `AGENTS.md`는 로컬 KMH Agent Kit의 지침에 연결합니다. 원격 저장소의 기존 지침 링크·Git 제외 상태는 이번 이전에서 변경하지 않습니다.
- `.env`, 인증서, 런타임 상태 파일을 커밋하거나 이미지에 넣지 않습니다.
- 강제 푸시, 기존 이력 삭제, 사용자 변경 되돌리기를 하지 않습니다.

## GBrain 기록

- 검증된 사실, 반복할 결정, 사용자 피드백, 재현·원인이 확정된 디버깅 결과만 기록합니다.
- 원문 로그, 대화 전문, 비밀값, 개인정보, 검증되지 않은 추측은 기록하지 않습니다.
- 디버깅 문서는 재현 조건과 근본 원인이 확정된 뒤에만 만듭니다.

## 보관 디스크·DB 백업

- 현행 저장 배치와 실행·복원 증거는 `~/controlroom/docs/production-server-consolidation-20260916.md` 20절 및 main `/srv/consolidation/infra/README.md`를 확인합니다. 코드·Git은 위 프로젝트 폴더에서 관리합니다.
- Main DB 백업은 단일03:40 한국 시각 예약으로 `/mnt/data/backups/daily/YYYY-MM-DD`에 하루 한 묶음만 만들며 전체 PG 접속 가능 비템플릿 DB와 MySQL 저장 스키마를 포함합니다. 같은 날 재호출은 SHA 확인 후 중단하고 기존14일 보존 기본값을 유지합니다. 추가 디스크 고정 UUID/mount 확인 실패 시 시스템 디스크에 대신 저장하지 않습니다.
- 실시간으로 쓰거나 즉시 꺼내 쓰지 않는 이미지·파일 원본·보관 자료는 `/mnt/data/files`에 둡니다. 복구 시험/보관 이미지 사본은 `/mnt/data/archive`, 초기 Git bundles는 `/mnt/data/imports`에 있습니다. 현재 앱 DB·실행 파일·캐시·업로드/다운로드는 위 정본 경로를 유지합니다. 기존 `/srv/consolidation` 복구용 bind mount는 같은 추가 디스크 파일을 보는 접속 경로이며 코드/자료 복사본을 새로 만드는 경로가 아닙니다.
