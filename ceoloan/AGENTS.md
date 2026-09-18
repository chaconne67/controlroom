# CEO Loan 중앙 조정실

## 조정실

- 작업 위치는 현재 조정실 루트의 실제 `ceoloan` 폴더입니다. PC·노트북은 `~/projects/ceoloan`, main 서버 조정실은 `~/controlroom-workspaces/ceoloan`입니다. `~`는 Windows의 `USERPROFILE`, macOS·Linux의 `HOME`입니다.
- 개발 에이전트는 선택한 조정실 장비에서만 실행합니다. 아래 서버의 코드·Git·검증·배포 경로는 SSH로 사용하며 제품 기능의 기존 AI·LLM 실행은 보존합니다.
- 새 세션은 `~/.gbrain-agent.md`를 읽고, 공용 최신 `project/windows-control-tower-operating-context`와 `project/ceoloan-operating-context`를 확인합니다.
- 아래 Linux 경로와 명령은 명시된 원격 호스트의 셸에서 실행합니다. 조정실 OS에 맞춰 서버 경로를 바꾸거나 운영 코드를 조정실에 복제하지 않습니다.
- 기획·리서치·작업 계획은 `docs/README.md`에서 찾습니다. 정본은 현재 프로젝트의 실제 `docs` 폴더이며 GitHub controlroom 저장소의 `ceoloan/docs`와 같은 위치입니다.
- 작업을 이어받을 때는 `docs/README.md`의 진행 중 작업 링크와 해당 계획의 재개 정보를 읽고 실제 서버 Git 상태와 대조합니다. 작업을 마치거나 옮기기 전에 그 계획에 재개 정보를 갱신하며 병렬 작업은 각 계획에서 관리합니다.

## 역할

- 이 폴더는 CEO Loan의 에이전트 지침·고유 스킬·기획 문서와 장기 기억의 진입점입니다.
- 애플리케이션 코드와 운영 파일은 운영 서버의 저장소에서 관리합니다.
- 중앙 에이전트가 SSH로 원격 저장소를 수정·검증하고 Git을 관리합니다.
- 중앙의 기존 `/home/chaconne/ceoloan` 복제본은 공식 작업 경로로 사용하지 않습니다.

## 정본

2026-09-17 22:33 KST 실제 인계 이후의 운영 주소는 `chaconne@49.247.192.127`입니다. 2026-09-18 00:35 KST 공개 DNS 원본 14개 이름 모두 새 main이고 가비아 권한 서버 3곳 및 Google/Cloudflare에서 이를 확인했습니다. 2026-09-18 잔여 정리로 옛 공개 입구·SQL/CLI/자료 전달과 인증서 전달을 중지했습니다. 현행 운영 연결은 main을 직접 사용하며 Hermes 세 사용자도 main에서만 실행합니다. 별도 복구 암호문과 복호화 키는 조정실의 접근 제한 폴더로 보존·검증했습니다. 옛 서버는 정지 보관 상태이며 삭제/해지는 별도 지시로 처리합니다. 최신 운영 상태·복구 경로는 현재 조정실 원본의 `.controlroom/docs/production-server-consolidation-20260916.md` 최신 절과 main `/srv/consolidation/infra/README.md`를 먼저 확인합니다. 과거 GBrain 프로젝트 맥락이나 고유 스킬에 남은 옛 서버·Swarm 배포 명령보다 이 현행 주소를 우선합니다. 옛 운영 writer는 정지·읽기 전용이므로 그 서버에서 배포하거나 DB/자료를 쓰지 않습니다.

| 항목 | 값 |
|---|---|
| SSH | `chaconne@49.247.192.127` |
| 실제 저장소 | `/home/chaconne/projects/ceoloan` |
| 통합 런타임·설정 | `/srv/consolidation/infra` |
| GitHub / 원격 / 기준 브랜치 | `git@github.com:chaconne67/ceoloan.git` / `ceoloan` / `main` |
| 앱 Python | Docker 이미지 Python 3.13 |
| 배포 정의 | `compose.production.ceoloan.json` + `compose.activate.ceoloan.json`, Compose 프로젝트 `production-ceoloan` |
| 운영 서비스 | `production-ceoloan-web-1`, `production-ceoloan-nginx-1` |
| 운영 도메인 | `https://rogeon.kr` |
| 운영 DB | main `migration-replicas-postgres-1` / `company_main` / 앱망 `172.30.40.10:5432` |
| 미디어·등기 정본 | `/srv/consolidation/data/files-standby/ceoloan-media`, `/srv/consolidation/data/files-standby/ceoloan-registry` |
| 옛 공개 입구 | `49.247.205.170` 정지; 옛 `/home/chaconne/ceoloan/repo/deploy.sh` 실행 금지 |

현재 코드·서버와 이 문서가 다르면 실제 상태를 확인해 이 문서와 GBrain을 갱신합니다.

## 제품과 데이터 경계

- 제품 맥락의 정본은 원격 저장소의 `CONTEXT.md`입니다.
- CEO Loan은 대표이사·통화·문자·영업 전달 업무를 관리합니다.
- 회사 기본정보·리드·CRETOP 사실의 정본은 `company` 스키마입니다.
- CEO Loan 업무 데이터는 `ceoloan` 스키마가 소유합니다.
- CEO Loan 역할은 `company`를 읽고 `ceoloan`만 씁니다.
- 회사 정보를 CEO Loan 모델에 복사하지 않습니다.

## 서버 코드 작업

- 조정실 진입 폴더는 `C:\Users\chaconne\projects\ceoloan`, main 코드 저장소는 `/home/chaconne/projects/ceoloan`입니다. main의 서버 조정실 진입 폴더는 `/home/chaconne/controlroom-workspaces/ceoloan`입니다. 조정실은 지침·스킬·기획의 진입점이고 서버 폴더는 실제 `.git`과 코드를 가진 독립 저장소입니다.
- main의 이 폴더에서 해당 프로젝트의 코드를 수정·검증하고, 이번 변경 파일만 커밋한 뒤 기존 `ceoloan`의 `main` 브랜치로 푸시합니다. 경로 이동을 이유로 Git 저장소·브랜치·원격을 다시 만들지 않습니다.

```text
ssh chaconne@49.247.192.127
cd /home/chaconne/projects/ceoloan
git status --short
```

위 `cd`와 Git 명령은 SSH 접속 후 서버 셸에서 실행합니다. 코드 검증·커밋 후 푸시는 `git push ceoloan main`입니다. 기존 수정·신규 파일을 보존하고 이번에 검증한 변경만 포함합니다.

## 작업 전 GBrain

GBrain 본체는 main에 있으며 로컬 카드의 main 직접 CLI로 읽습니다. 다음 순서로 확인합니다.

1. 전역 카드의 공용 조회 명령으로 `project/ceoloan-operating-context`를 읽습니다.
2. 같은 카드의 공용 검색 명령으로 `ceoloan <작업 기능·화면·모델·오류>`를 검색합니다.
3. 검색 결과의 프로젝트 개요·구조·배포 런북과 작업 관련 페이지

GBrain은 과거 맥락이고 현재 코드와 서버가 최종 기준입니다.

## 공식 작업 경로

1. GBrain과 원격 저장소의 Git 상태를 확인합니다.
2. 기존 변경과 미추적 파일을 확인하고 그대로 보존합니다.
3. 요청과 관련된 원격 코드·설정·호출 경로를 읽습니다.
4. SSH를 통해 원격 저장소의 요청 범위만 수정합니다.
5. 새 main의 앱 이미지·독립 검증 환경에서 영향 범위에 맞는 검증을 실행합니다. 호스트 가상환경은 준비되지 않았으므로 옛 `.venv` 경로를 사용하지 않습니다.
6. 전체 diff와 검증 결과를 확인하고 요청 범위만 커밋합니다.
7. `ceoloan` 원격의 `main`에 push해 서버 밖에도 결과를 보존합니다.
8. 배포는 주인님이 명시적으로 요청한 경우에만 실행합니다.
9. 배포 후 HTTPS와 Compose 서비스 상태를 확인합니다.

원격 저장소에 요청과 무관한 변경이 있으면 함께 커밋하거나 숨기지 않습니다. 분리할 수 없는 변경은
주인님께 범위를 보고하고 멈춥니다.

## 고유 스킬

- CEO Loan 제품 UI·템플릿·Tailwind·HTMX·Alpine·반응형·접근성: `ceoloan-design-system`
- CRETOP 브라우저 상태 확인·기업 조회·배치 수집·결과 저장·오류 진단: `cretop-scraping`
- 인터넷등기소 부동산 조회·결제 경계·등기 PDF 수령과 검증: `iros-registry`

이 스킬들은 CEO Loan 조정실에서만 노출합니다. `ceoloan-design-system`은 웹 제품 화면과 MMS
카드 이미지의 디자인 규칙을 서로 섞지 않습니다. `cretop-scraping`은 CEO Loan 저장소의 독립
래퍼를 공식 수집 경로로 사용하며 RNDLOG 복사본과 함께 수정하지 않습니다. `cretop-scraping`과
`iros-registry`가 조정실 Windows의 실제 Chrome을 사용할 때는 공용 `hidden-desktop-browser`를
함께 적용하고, 사이트 절차와 결과 계약만 도메인 스킬에 둡니다. 일반 브라우저 자동화나 DB
변경이라는 이유만으로 발동하지 않습니다.

## 검증 기준

- 코드 검증 위치는 main `/home/chaconne/projects/ceoloan`입니다. 호스트 `.venv`는 없으며 현재 앱의 Python 3.13 이미지와 해당 변경의 독립 테스트 환경을 사용합니다. 운영 DB/대외 효과와 분리된 검증 경로를 확인한 뒤 Django 검사·관련 pytest만 실행합니다.
- 원격 화면 검증의 공통 절차는 공용 `web-automation` 스킬의 「Remote development UI verification」을 따릅니다.
- CEO Loan의 서버·테스트·CSS 설정과 디자인 기준은
  [.agents/skills/ceoloan-design-system/SKILL.md](.agents/skills/ceoloan-design-system/SKILL.md)의
  「실행 위치」와 「프로젝트 검증 설정」을 사용합니다.
- 운영 확인은 `https://rogeon.kr`의 HTTP 200과 main `production-ceoloan-web-1`의 healthy 상태를 사용합니다.
- 검증하지 못한 항목을 통과했다고 보고하지 않습니다.

## 안전 경계

- `.env`, 운영 DB, 문자 발송, 예약 작업, DB 터널, 인증서, Docker Compose는 요청 없이 변경하지 않습니다.
- 테스트와 관리 명령이 운영 DB·SOLAPI·Google·Gemini에 미치는 영향을 먼저 확인합니다.
- `company`와 `cretop` 스키마를 CEO Loan 마이그레이션으로 만들거나 변경하거나 삭제하지 않습니다.
- 값이 없으면 비우거나 오류로 멈추며 회사·대표이사·재무 수치를 추정하지 않습니다.
- 원격 저장소의 기존 변경과 미추적 파일을 삭제하거나 덮어쓰지 않습니다.
- 운영 서버에는 KMH Agent Kit, GBrain 카드, 사용자 `AGENTS.md`·`CLAUDE.md`, 프로젝트 스킬을 설치하지 않습니다.

## Git 경계

- 원격 운영 저장소와 GitHub SSH 원격 `ceoloan`이 코드 정본입니다.
- 기준 브랜치는 `main`입니다.
- `/tmp/ceoloan*.bundle`을 가리키는 `origin`·`bundle` 원격은 과거 잔재이므로 사용하지 않습니다.
- 강제 push, 운영 파일 복사 배포, 일부 변경만 숨긴 부분 배포를 하지 않습니다.

## 보관 디스크·DB 백업

- 현행 저장 배치와 실행·복원 증거는 현재 조정실 루트의 `.controlroom/docs/production-server-consolidation-20260916.md` 20절 및 main `/srv/consolidation/infra/README.md`를 확인합니다. 코드·Git은 위 프로젝트 폴더에서 관리합니다.
- Main DB 백업은 단일03:40 한국 시각 예약으로 `/mnt/data/backups/daily/YYYY-MM-DD`에 하루 한 묶음만 만들며 전체 PG 접속 가능 비템플릿 DB와 MySQL 저장 스키마를 포함합니다. 같은 날 재호출은 SHA 확인 후 중단하고 2026-09-18 후속 지시에 따라 최근3일분 완료 백업만 보관합니다. 추가 디스크 고정 UUID/mount 확인 실패 시 시스템 디스크에 대신 저장하지 않습니다.
- 실시간으로 쓰거나 즉시 꺼내 쓰지 않는 이미지·파일 원본·보관 자료는 `/mnt/data/files`에 둡니다. 복구 시험/보관 이미지 사본은 `/mnt/data/archive`, 초기 Git bundles는 `/mnt/data/imports`에 있습니다. 현재 앱 DB·실행 파일·캐시·업로드/다운로드는 위 정본 경로를 유지합니다. 기존 `/srv/consolidation` 복구용 bind mount는 같은 추가 디스크 파일을 보는 접속 경로이며 코드/자료 복사본을 새로 만드는 경로가 아닙니다.
