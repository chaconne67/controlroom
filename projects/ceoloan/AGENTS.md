# CEO Loan 중앙 조정실

## 조정실

- 작업 위치는 이 프로필을 연결한 현재 프로젝트 폴더이며 기본값은 `~/projects/ceoloan`입니다. `~`는 Windows의 `USERPROFILE`, macOS·Linux의 `HOME`입니다. 이미 등록된 사용자 지정 경로를 우선합니다.
- 개발 에이전트는 선택한 조정실 장비에서만 실행합니다. 아래 서버의 코드·Git·검증·배포 경로는 SSH로 사용하며 제품 기능의 기존 AI·LLM 실행은 보존합니다.
- 새 세션은 `~/.gbrain-agent.md`를 읽고, 공용 최신 `project/windows-control-tower-operating-context`와 `project/ceoloan-operating-context`를 확인합니다.
- 아래 Linux 경로와 명령은 명시된 원격 호스트의 셸에서 실행합니다. 조정실 OS에 맞춰 서버 경로를 바꾸거나 운영 코드를 조정실에 복제하지 않습니다.
- 기획·리서치·작업 계획은 `docs/README.md`에서 찾습니다. `docs`는 비공개 문서 저장소의 `ceoloan/docs`에 연결되며 기본 정본은 `~/projects/_control-docs/ceoloan/docs`입니다.
- 작업을 이어받을 때는 `docs/README.md`의 진행 중 작업 링크와 해당 계획의 재개 정보를 읽고 실제 서버 Git 상태와 대조합니다. 작업을 마치거나 옮기기 전에 그 계획에 재개 정보를 갱신하며 병렬 작업은 각 계획에서 관리합니다.

## 역할

- 이 폴더는 CEO Loan의 에이전트 지침·고유 스킬·기획 문서와 장기 기억의 진입점입니다.
- 애플리케이션 코드와 운영 파일은 운영 서버의 저장소에서 관리합니다.
- 중앙 에이전트가 SSH로 원격 저장소를 수정·검증하고 Git을 관리합니다.
- 중앙의 기존 `/home/chaconne/ceoloan` 복제본은 공식 작업 경로로 사용하지 않습니다.

## 정본

| 항목 | 값 |
|---|---|
| SSH | `chaconne@49.247.205.170` |
| 호스트명 | `ceoloan` |
| 운영 루트 | `/home/chaconne/ceoloan` |
| 실제 저장소 | `/home/chaconne/ceoloan/repo` |
| GitHub | `git@github.com:chaconne67/ceoloan.git` |
| Git 원격 이름 | `ceoloan` |
| 기준 브랜치 | `main` |
| 앱 Python | Docker 이미지 Python 3.13 |
| 호스트 가상환경 | `/home/chaconne/ceoloan/repo/.venv` |
| 배포 진입점 | `/home/chaconne/ceoloan/repo/deploy.sh` |
| 운영 방식 | Docker Compose 프로젝트 `ceoloan` |
| 운영 서비스 | `ceoloan-web`, `ceoloan-nginx` |
| 운영 도메인 | `https://rogeon.kr` |
| 운영 DB | 중앙 서버 `CentralDB_postgres`의 `ceo_loan`, SSH 터널 `127.0.0.1:15432` |

현재 코드·서버와 이 문서가 다르면 실제 상태를 확인해 이 문서와 GBrain을 갱신합니다.

## 제품과 데이터 경계

- 제품 맥락의 정본은 원격 저장소의 `CONTEXT.md`입니다.
- CEO Loan은 대표이사·통화·문자·영업 전달 업무를 관리합니다.
- 회사 기본정보·리드·CRETOP 사실의 정본은 `company` 스키마입니다.
- CEO Loan 업무 데이터는 `ceoloan` 스키마가 소유합니다.
- CEO Loan 역할은 `company`를 읽고 `ceoloan`만 씁니다.
- 회사 정보를 CEO Loan 모델에 복사하지 않습니다.

## 작업 전 GBrain

GBrain 본체는 DB에 있으며 로컬 카드의 승인된 SSH 프록시를 사용합니다. 다음 순서로 확인합니다.

1. 전역 카드의 공용 조회 명령으로 `project/ceoloan-operating-context`를 읽습니다.
2. 같은 카드의 공용 검색 명령으로 `ceoloan <작업 기능·화면·모델·오류>`를 검색합니다.
3. 검색 결과의 프로젝트 개요·구조·배포 런북과 작업 관련 페이지

GBrain은 과거 맥락이고 현재 코드와 서버가 최종 기준입니다.

## 공식 작업 경로

1. GBrain과 원격 저장소의 Git 상태를 확인합니다.
2. 기존 변경과 미추적 파일을 확인하고 그대로 보존합니다.
3. 요청과 관련된 원격 코드·설정·호출 경로를 읽습니다.
4. SSH를 통해 원격 저장소의 요청 범위만 수정합니다.
5. 원격 가상환경에서 영향 범위에 맞는 검증을 실행합니다.
6. 전체 diff와 검증 결과를 확인하고 요청 범위만 커밋합니다.
7. `ceoloan` 원격의 `main`에 push해 서버 밖에도 결과를 보존합니다.
8. 배포는 주인님이 명시적으로 요청한 경우에만 실행합니다.
9. 배포 후 HTTPS와 Compose 서비스 상태를 확인합니다.

원격 저장소에 요청과 무관한 변경이 있으면 함께 커밋하거나 숨기지 않습니다. 분리할 수 없는 변경은
주인님께 범위를 보고하고 멈춥니다.

## 고유 스킬

- CEO Loan 제품 UI·템플릿·Tailwind·HTMX·Alpine·반응형·접근성: `ceoloan-design-system`
- CRETOP 브라우저 상태 확인·기업 조회·배치 수집·결과 저장·오류 진단: `cretop-scraping`

이 스킬들은 CEO Loan 조정실에서만 노출합니다. `ceoloan-design-system`은 웹 제품 화면과 MMS
카드 이미지의 디자인 규칙을 서로 섞지 않습니다. `cretop-scraping`은 CEO Loan 저장소의 독립
래퍼를 공식 수집 경로로 사용하며 RNDLOG 복사본과 함께 수정하지 않습니다. 일반 브라우저
자동화나 DB 변경이라는 이유만으로 발동하지 않습니다.

## 검증 기준

- Django 검사: `cd /home/chaconne/ceoloan/repo && uv run python manage.py check --settings=main.settings.local`
- 관련 테스트: `cd /home/chaconne/ceoloan/repo && uv run pytest -q <대상>`
- 원격 화면 검증의 공통 절차는 공용 `web-automation` 스킬의 「Remote development UI verification」을 따릅니다.
- CEO Loan의 서버·테스트·CSS 설정과 디자인 기준은
  [.agents/skills/ceoloan-design-system/SKILL.md](.agents/skills/ceoloan-design-system/SKILL.md)의
  「실행 위치」와 「프로젝트 검증 설정」을 사용합니다.
- 운영 확인은 `https://rogeon.kr`의 HTTP 200과 `ceoloan-web`의 healthy 상태를 사용합니다.
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
