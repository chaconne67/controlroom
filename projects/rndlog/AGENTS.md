# RNDLOG 중앙 조정실

## Windows 조정실

- 작업 위치: `C:\Users\chaconne\projects\rndlog`. 애플리케이션 코드·Git·검증·배포는 아래 원격 서버의 기존 경로를 사용합니다.
- 새 세션은 대화 이식 없이 `~/.gbrain-agent.md`의 현재 래퍼로 공용 `project/rndlog-operating-context`를 먼저 읽습니다.
- GBrain은 전역 컨트롤타워 카드의 공용 조회 경로로 `project/rndlog-operating-context`를 읽습니다. GBrain 본체는 DB 서버에 유지합니다.
- 아래 Linux 경로와 명령은 명시된 원격 호스트의 셸에서 실행합니다. Windows에 운영 코드를 복제하지 않습니다.
- 기획·리서치·작업 계획은 조정실의 `docs/README.md`에서 찾습니다. 이 폴더는 `../_control-docs/rndlog/docs`의 같은 원본으로 연결되며, 문서 Git 이력은 `_control-docs`에서 관리합니다.


## 역할

- 이 폴더는 RNDLOG의 중앙 컨트롤타워입니다.
- 로컬 `companies/`·`resources/`는 DB 자료를 복사한 준비본입니다. 운영 업로드의 저장 정본과 게이트웨이는 아직 DB에 있으므로 로컬 사본으로 정본을 대체하거나 자동 동기화하지 않습니다.
- 로컬 스킬은 `C:\Users\chaconne\kmh-agent-kit\skills\domains\rndlog`에 연결합니다.
- 운영서버는 웹서비스 코드와 런타임만 운영하며 고객사 자료나 산출물의 정본으로 사용하지 않습니다.

## 정본

| 항목 | 값 |
|---|---|
| 컨트롤타워 | Windows `C:\Users\chaconne\projects\rndlog` |
| 운영 업로드·고객자료 정본(DB, 미전환) | `/home/chaconne/projects/rndlog/companies/<정식 회사명>/` |
| 공통 제작 자원(DB 원본) | `/home/chaconne/projects/rndlog/resources/` |
| 로컬 스킬 | `C:\Users\chaconne\kmh-agent-kit\skills\domains\rndlog` |
| 운영서버 SSH | `chaconne@49.247.207.147` (`rndlog`) |
| 운영 코드 | `/home/chaconne/rndlog` |
| 호환 경로 | `/home/work/rndnote` → 실제 저장소 |
| GitHub | `git@github.com:chaconne67/rndnote.git` |
| 기준 브랜치 | `main` |
| 앱 Python | Docker 이미지 Python 3.13 |
| 호스트 가상환경 | `/home/chaconne/rndlog/.venv` |
| 배포 진입점 | `/home/chaconne/rndlog/deploy.sh` |
| 운영 스택 | `Rndnote` (`Rndnote_app`, `Rndnote_nginx`) |
| 운영 도메인 | `https://rndlog.kr` |
| 운영 DB | 중앙 서버 `CentralDB_postgres`의 `ceo_loan`, SSH 터널 `127.0.0.1:15432` |

현재 코드·서버와 이 문서가 다르면 실제 상태를 확인해 코드와 서버에 맞춰 이 문서와 GBrain을
갱신합니다. `Rndnote`와 `rndnote.git`은 남아 있는 운영 식별자이며 제품 이름은 RNDLOG입니다.

## 제품 경계

- 공개 영역은 RNDLOG 랜딩, 상담 신청, KOITA 자가진단입니다.
- 로그인 영역은 기업자금 TM·영업 업무를 제공합니다.
- 제품 맥락의 정본은 원격 저장소의 `CONTEXT.md`입니다.
- R&D 증빙 고객사 작업 공간은 메인서버 `companies/<정식 회사명>/`입니다.
- `sources/original/`은 고객 원본, `sources/intake/`는 수신기록, `research/`는 회사별 조사자료,
  `deliverables/drafts/`는 기존 HTML과 신규 DOCX 작업본, `deliverables/final/`은 기존 PDF와 검토 완료 DOCX 산출물입니다.
- 공통 참고자료·샘플·양식·도구는 `resources/`에 두고 고객사 파일과 섞지 않습니다.
- 앱의 공식 DB는 `ceo_loan` 하나이며 RNDLOG 업무 테이블은 `rndlog` 스키마에 둡니다.

## 작업 전 GBrain

GBrain 본체는 DB에 유지합니다. 로컬 카드의 프록시로 다음 공용 문서를 읽습니다. 고객자료 저장 위치는 `project/rndlog-file-upload-storage`를 함께 확인합니다.

- `project/rndlog-operating-context`
- 작업 기능명·화면명·모델명으로 찾은 관련 페이지

## 공식 작업 경로

1. Windows PC에서 카카오톡 원천파일을 받고 사업자등록증의 정식 법인명을 확인합니다.
2. 메인서버 `companies/<정식 회사명>/sources/original/`에 원본 그대로 올리고, 수신메모·링크·대화 캡처는 `sources/intake/`에 둡니다.
3. `rndlog` 스킬을 읽고 회사 자료 취합, 리서치와 DOCX 보고서 작성을 순서대로 수행합니다.
4. 조사 결과는 `research/`, DOCX 작업본은 `deliverables/drafts/`, 검토 완료 DOCX는 `deliverables/final/`에 저장합니다.
5. 회사 README에 자료 입수·리서치·산출 이력을 기록합니다.
6. 웹서비스 코드 변경이 필요한 경우에만 별도로 운영서버 Git·테스트·배포 절차를 사용합니다.

`deploy.sh`는 저장소의 모든 변경과 미추적 파일을 한 배포 단위로 커밋할 수 있습니다. 함께
배포할 수 없는 기존 변경이 하나라도 있으면 배포하지 말고 주인님께 범위를 보고합니다.

## 고유 스킬

- 고객사 R&D 증빙 조사·DOCX 보고서 작성: `rndlog`
- RNDLOG 제품 UI·템플릿·Tailwind·HTMX·반응형·접근성: `rndlog-design-system`

두 스킬은 RNDLOG 조정실에서만 노출합니다. 고객사 DOCX 보고서 스타일과 제품 UI 디자인 시스템을 서로
섞지 않으며, 일반 코딩이나 배포라는 이유만으로 발동하지 않습니다.

## 검증 기준

- Django 검사: `cd /home/chaconne/rndlog && /home/chaconne/.local/bin/uv run python manage.py check --settings=main.settings.local`
- 관련 테스트: `/home/chaconne/rndlog/.venv/bin/pytest <대상>`
- 템플릿 변경은 Tailwind 빌드와 `collectstatic` 후 실제 화면을 확인합니다.
- 제품 화면은 `rndlog-design-system` 스킬에 따라 모바일·데스크톱과 상호작용 상태를 확인합니다.
- 고객사 DOCX는 `rndlog` 스킬의 견적서 원본·파생 샘플 디자인을 적용하고 표 머리글 배경색만 짙은 네이비 또는 회색으로 바꿉니다.
- DOCX의 본문·표·머리말·꼬리말·패키지 무결성과 샘플 placeholder 잔존 여부를 확인합니다.
- 운영 확인은 `https://rndlog.kr` 응답과 `Rndnote_app`, `Rndnote_nginx`의 `1/1` 상태를 사용합니다.
- 검증하지 못한 항목을 통과했다고 보고하지 않습니다.

## 안전 경계

- `companies/*/sources/original/`의 고객사 원본은 수정하지 않습니다.
- 고객사 원본을 `resources/`에 넣거나 공통 샘플을 고객사 `deliverables/`에 넣지 않습니다.
- 확인되지 않은 회사 정보·연구원·수치·논문·기관명을 만들지 않습니다.
- 고객사 자료, `.env`, `.credential`, 운영 DB, 문자 발송, 예약 작업, Docker Swarm은 요청 없이
  변경하지 않습니다.
- 테스트와 관리 명령이 운영 DB·SOLAPI·Google·Telegram에 미치는 영향을 먼저 확인합니다.
- 원격 저장소의 기존 변경과 미추적 파일을 삭제하거나 덮어쓰지 않습니다.
- 고객사 자료, 리서치, 보고서 작업본과 산출물을 운영서버에 새로 저장하지 않습니다.
- 기존 HTML/PDF 산출물을 임의로 다른 폴더로 옮기거나 숨기지 않습니다.
- 자료 누락은 고객 입력란과 보완 목록으로 남기고 조사·과제 설계·문서 초안을 계속 작성합니다. 제안 활동과 예상 결과는 고객 확인 전 실제 수행·측정 사실로 표시하지 않습니다.

## Git 경계

- 원격 저장소와 SSH 인증이 Git 작업의 정본입니다.
- 기준 브랜치는 `main`이고 GitHub 저장소 이름은 아직 `rndnote`입니다.
- 강제 push, 운영 파일 복사 배포, 일부 변경만 숨긴 부분 배포를 하지 않습니다.

## RNDLOG 작성 계약 — 2026-09-08

- 월간 연구노트·주간 연구일지·주간 업무일지는 별도 문서입니다.
- 검증한 고객 검토용 DOCX는 보완 목록과 함께 전달할 수 있습니다. 고객 사실 확인까지 끝난 문서만 final/에 확정합니다.
