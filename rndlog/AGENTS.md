# RNDLOG 중앙 조정실

## 조정실

- 작업 위치는 현재 조정실 루트의 실제 `rndlog` 폴더입니다. PC·노트북은 `~/projects/rndlog`, main 서버 조정실은 `~/controlroom-workspaces/rndlog`입니다. `~`는 Windows의 `USERPROFILE`, macOS·Linux의 `HOME`입니다.
- 개발 에이전트는 선택한 조정실 장비에서만 실행합니다. 아래 서버의 코드·Git·검증·배포 경로는 SSH로 사용하며 제품 기능의 기존 AI·LLM 실행은 보존합니다.
- 새 세션은 `~/.gbrain-agent.md`를 읽고, 공용 최신 `project/windows-control-tower-operating-context`와 `project/rndlog-operating-context`를 확인합니다.
- 아래 Linux 경로와 명령은 명시된 원격 호스트의 셸에서 실행합니다. 조정실 OS에 맞춰 서버 경로를 바꾸거나 운영 코드를 조정실에 복제하지 않습니다.
- 기획·리서치·작업 계획은 `docs/README.md`에서 찾습니다. 정본은 현재 프로젝트의 실제 `docs` 폴더이며 GitHub controlroom 저장소의 `rndlog/docs`와 같은 위치입니다.
- 작업을 이어받을 때는 `docs/README.md`의 진행 중 작업 링크와 해당 계획의 재개 정보를 읽고 실제 서버 Git 상태와 대조합니다. 작업을 마치거나 옮기기 전에 그 계획에 재개 정보를 갱신하며 병렬 작업은 각 계획에서 관리합니다.

## 역할

- 이 폴더는 RNDLOG의 중앙 컨트롤타워입니다.
- 로컬 `companies/`·`resources/`는 DB 자료를 복사한 준비본입니다. 운영 업로드의 저장 정본과 게이트웨이는 main에 있으므로 로컬 사본으로 정본을 대체하거나 자동 동기화하지 않습니다.
- 로컬 스킬 원본은 현재 프로젝트의 실제 `skills` 폴더에 둡니다.
- 통합 main에서 웹서비스 코드·런타임과 별도 자료 정본을 관리합니다. 고객사 자료는 앱 코드/미디어와 분리된 아래 workspace 경로에 저장합니다.

## 정본

2026-09-17 22:33 KST 실제 인계 이후의 운영 주소는 `chaconne@49.247.192.127`입니다. 2026-09-18 00:35 KST 공개 DNS 원본 14개 이름 모두 새 main이고 가비아 권한 서버 3곳 및 Google/Cloudflare에서 이를 확인했습니다. DNS 캐시의 옛 공개 입구와 SQL/CLI/자료 호환 주소는 새 main으로 전달합니다. 옛 서버의 호환 전달·별도 복구 백업·제외 서비스 의존성은 남아 있으므로 DNS 변경만으로 해지/삭제하지 않습니다. 최신 운영 상태·복구 경로는 현재 조정실 루트의 `.controlroom/docs/production-server-consolidation-20260916.md` 최신 절과 main `/srv/consolidation/infra/README.md`를 먼저 확인합니다. 과거 GBrain 프로젝트 맥락이나 고유 스킬에 남은 옛 서버·Swarm 배포 명령보다 이 현행 주소를 우선합니다. 옛 운영 writer는 정지·읽기 전용이므로 그 서버에서 배포하거나 DB/자료를 쓰지 않습니다.

| 항목 | 값 |
|---|---|
| 컨트롤타워 | 현재 조정실 루트의 `rndlog` |
| 운영 업로드·회사별 제출·연구자료 정본(main) | `/srv/consolidation/data/files-standby/workspace/companies/<정식 회사명>/` |
| 공통 제작 자원(main) | `/srv/consolidation/data/files-standby/workspace/resources/` |
| 자료 접속 프로그램(main 코드) | `/home/chaconne/projects/rndlog/deploy/workspace_storage_gateway.py` |
| 로컬 스킬 | 현재 조정실 루트의 `rndlog/skills` |
| 운영서버 SSH | `chaconne@49.247.192.127` |
| 운영 코드 | `/home/chaconne/projects/rndlog` |
| GitHub / 원격 / 기준 브랜치 | `git@github.com:chaconne67/rndnote.git` / `origin` / `main` |
| 앱 Python | Docker 이미지 Python 3.13 |
| 배포 정의 | `/srv/consolidation/infra/compose.production.rndlog.json` + `compose.activate.rndlog.json`, Compose 프로젝트 `production-rndlog` |
| 운영 서비스 | `production-rndlog-web-1`, `production-rndlog-nginx-1` |
| 운영 도메인 | `https://rndlog.kr` |
| 운영 DB | main `migration-replicas-postgres-1` / `company_main` / 앱망 `172.30.40.10:5432` |
| 옛 공개 입구 | `49.247.207.147` → main 전달; 옛 `Rndnote` Swarm writer는 정지 |

현재 코드·서버와 이 문서가 다르면 실제 상태를 확인해 코드와 서버에 맞춰 이 문서와 GBrain을
갱신합니다. `Rndnote`와 `rndnote.git`은 남아 있는 운영 식별자이며 제품 이름은 RNDLOG입니다.

## 서버 코드 작업

- 조정실 진입 폴더는 `C:\Users\chaconne\projects\rndlog`, main 코드 저장소는 `/home/chaconne/projects/rndlog`입니다. main의 서버 조정실 진입 폴더는 `/home/chaconne/controlroom-workspaces/rndlog`입니다. 조정실은 지침·스킬·기획의 진입점이고 서버 폴더는 실제 `.git`과 코드를 가진 독립 저장소입니다.
- main의 이 폴더에서 해당 프로젝트의 코드를 수정·검증하고, 이번 변경 파일만 커밋한 뒤 기존 `origin`의 `main` 브랜치로 푸시합니다. 경로 이동을 이유로 Git 저장소·브랜치·원격을 다시 만들지 않습니다.

```text
ssh chaconne@49.247.192.127
cd /home/chaconne/projects/rndlog
git status --short
```

위 `cd`와 Git 명령은 SSH 접속 후 서버 셸에서 실행합니다. 코드 검증·커밋 후 푸시는 `git push origin main`입니다. 기존 수정·신규 파일을 보존하고 이번에 검증한 변경만 포함합니다.

## 제품 경계

- 공개 영역은 RNDLOG 랜딩, 상담 신청, KOITA 자가진단입니다.
- 로그인 영역은 기업자금 TM·영업 업무를 제공합니다.
- 제품 맥락의 정본은 원격 저장소의 `CONTEXT.md`입니다.
- R&D 증빙 고객사 작업 공간은 메인서버 `companies/<정식 회사명>/`입니다.
- `sources/original/`은 고객 원본, `sources/intake/`는 수신기록, `research/`는 회사별 조사자료,
  `deliverables/drafts/`는 기존 HTML과 신규 DOCX 작업본, `deliverables/final/`은 기존 PDF와 검토 완료 DOCX 산출물입니다.
- 공통 참고자료·샘플·양식·도구는 `resources/`에 두고 고객사 파일과 섞지 않습니다.
- 앱의 공식 DB는 `company_main` 하나이며 RNDLOG 업무 테이블은 `rndlog` 스키마에 둡니다.

## 작업 전 GBrain

GBrain 본체는 main에 있습니다. 로컬 카드의 기존 DB 주소 호환 CLI로 다음 공용 문서를 읽습니다. 회사별 제출·연구자료 저장 위치는 `project/rndlog-file-upload-storage`를 함께 확인합니다.

- `project/rndlog-operating-context`
- 작업 기능명·화면명·모델명으로 찾은 관련 페이지

## 공식 작업 경로

1. 카카오톡 원천파일을 받을 수 있는 승인된 장비에서 파일을 받고 사업자등록증의 정식 법인명을 확인합니다.
2. 메인서버 `companies/<정식 회사명>/sources/original/`에 원본 그대로 올리고, 수신메모·링크·대화 캡처는 `sources/intake/`에 둡니다.
3. `rndlog` 스킬을 읽고 회사 자료 취합, 리서치와 DOCX 보고서 작성을 순서대로 수행합니다.
4. 조사 결과는 `research/`, DOCX 작업본은 `deliverables/drafts/`, 검토 완료 DOCX는 `deliverables/final/`에 저장합니다.
5. 회사 README에 자료 입수·리서치·산출 이력을 기록합니다.
6. 웹서비스 코드 변경이 필요한 경우에만 별도로 운영서버 Git·테스트·배포 절차를 사용합니다.

옛 `deploy.sh`의 Swarm 배포·전체 정리 명령은 통합 main의 배포 경로가 아닙니다. 배포를 요청받으면 실제 변경 범위·frozen image·해당 Compose 두 정의와 검증·복구 경로를 먼저 대조하고 해당 제품만 갱신합니다. 다른 제품과 기존 변경은 보존합니다.

## 고유 스킬

- 고객사 R&D 증빙 조사·DOCX 보고서 작성: `rndlog`
- RNDLOG 제품 UI·템플릿·Tailwind·HTMX·반응형·접근성: `rndlog-design-system`

두 스킬은 RNDLOG 조정실에서만 노출합니다. 고객사 DOCX 보고서 스타일과 제품 UI 디자인 시스템을 서로
섞지 않으며, 일반 코딩이나 배포라는 이유만으로 발동하지 않습니다.

## 검증 기준

- 코드 검증 위치는 main `/home/chaconne/projects/rndlog`입니다. 호스트 `.venv`는 없으며 기존 Python 3.13 앱 이미지와 운영 DB/대외 효과에서 분리한 테스트 환경으로 Django 검사·관련 테스트를 실행합니다.
- 템플릿 변경은 Tailwind 빌드와 `collectstatic` 후 실제 화면을 확인합니다.
- 제품 화면은 `rndlog-design-system` 스킬에 따라 모바일·데스크톱과 상호작용 상태를 확인합니다.
- 고객사 DOCX는 `rndlog` 스킬의 견적서 원본·파생 샘플 디자인을 적용하고 표 머리글 배경색만 짙은 네이비 또는 회색으로 바꿉니다.
- DOCX의 본문·표·머리말·꼬리말·패키지 무결성과 샘플 placeholder 잔존 여부를 확인합니다.
- 운영 확인은 `https://rndlog.kr` 응답과 main `production-rndlog-web-1`, `production-rndlog-nginx-1`의 running 상태를 사용합니다. 원본 이미지에는 web healthcheck가 없습니다.
- 검증하지 못한 항목을 통과했다고 보고하지 않습니다.

## 안전 경계

- `companies/*/sources/original/`의 고객사 원본은 수정하지 않습니다.
- 고객사 원본을 `resources/`에 넣거나 공통 샘플을 고객사 `deliverables/`에 넣지 않습니다.
- 확인되지 않은 회사 정보·연구원·수치·논문·기관명을 만들지 않습니다.
- 고객사 자료, `.env`, `.credential`, 운영 DB, 문자 발송, 예약 작업, Docker Swarm은 요청 없이
  변경하지 않습니다.
- 테스트와 관리 명령이 운영 DB·SOLAPI·Google·Telegram에 미치는 영향을 먼저 확인합니다.
- 원격 저장소의 기존 변경과 미추적 파일을 삭제하거나 덮어쓰지 않습니다.
- 고객사 자료, 리서치, 보고서 작업본과 산출물은 main의 workspace 정본에 저장하고 앱 코드·미디어 폴더에 섞지 않습니다.
- 기존 HTML/PDF 산출물을 임의로 다른 폴더로 옮기거나 숨기지 않습니다.
- 자료 누락은 고객 입력란과 보완 목록으로 남기고 조사·과제 설계·문서 초안을 계속 작성합니다. 제안 활동과 예상 결과는 고객 확인 전 실제 수행·측정 사실로 표시하지 않습니다.

## Git 경계

- 원격 저장소와 SSH 인증이 Git 작업의 정본입니다.
- 기준 브랜치는 `main`이고 GitHub 저장소 이름은 아직 `rndnote`입니다.
- 강제 push, 운영 파일 복사 배포, 일부 변경만 숨긴 부분 배포를 하지 않습니다.

## RNDLOG 작성 계약 — 2026-09-08

- 월간 연구노트·주간 연구일지·주간 업무일지는 별도 문서입니다.
- 검증한 고객 검토용 DOCX는 보완 목록과 함께 전달할 수 있습니다. 고객 사실 확인까지 끝난 문서만 final/에 확정합니다.

## 보관 디스크·DB 백업

- 현행 저장 배치와 실행·복원 증거는 현재 조정실 루트의 `.controlroom/docs/production-server-consolidation-20260916.md` 20절 및 main `/srv/consolidation/infra/README.md`를 확인합니다. 코드·Git은 위 프로젝트 폴더에서 관리합니다.
- Main DB 백업은 단일03:40 한국 시각 예약으로 `/mnt/data/backups/daily/YYYY-MM-DD`에 하루 한 묶음만 만들며 전체 PG 접속 가능 비템플릿 DB와 MySQL 저장 스키마를 포함합니다. 같은 날 재호출은 SHA 확인 후 중단하고 2026-09-18 후속 지시에 따라 최근3일분 완료 백업만 보관합니다. 추가 디스크 고정 UUID/mount 확인 실패 시 시스템 디스크에 대신 저장하지 않습니다.
- 실시간으로 쓰거나 즉시 꺼내 쓰지 않는 이미지·파일 원본·보관 자료는 `/mnt/data/files`에 둡니다. 복구 시험/보관 이미지 사본은 `/mnt/data/archive`, 초기 Git bundles는 `/mnt/data/imports`에 있습니다. 현재 앱 DB·실행 파일·캐시·업로드/다운로드는 위 정본 경로를 유지합니다. 기존 `/srv/consolidation` 복구용 bind mount는 같은 추가 디스크 파일을 보는 접속 경로이며 코드/자료 복사본을 새로 만드는 경로가 아닙니다.
