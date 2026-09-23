# Exdigm 중앙 조정실

## 조정실

- 작업 위치는 현재 조정실 루트의 실제 `exdigm` 폴더입니다. 모든 OS의 PC·노트북·main 서버 조정실은 `~/controlroom/exdigm`입니다. `~`는 Windows의 `USERPROFILE`, macOS·Linux의 `HOME`입니다.
- 개발 에이전트는 사용자 조정실에서 실행합니다. 아래 Exdigm 서버의 코드·Git·검증·배포 경로는 SSH로 사용하며 제품 기능의 기존 AI·LLM 실행은 보존합니다.
- 새 세션은 전역 `~/.gbrain-agent.md`를 먼저 읽고, 이 `AGENTS.md`와 같은 폴더의 `.gbrain-agent.md`를 추가로 읽습니다. 두 카드가 지정한 GBrain 문서를 확인한 뒤 작업합니다.
- 아래 Linux 경로와 명령은 명시된 원격 호스트의 셸에서 실행합니다. 조정실 OS에 맞춰 서버 경로를 바꾸거나 운영 코드를 조정실에 복제하지 않습니다.
- 기획·리서치·작업 계획은 `docs/README.md`에서 찾습니다. 정본은 현재 프로젝트의 실제 `docs` 폴더이며 GitHub controlroom 저장소의 `exdigm/docs`와 같은 위치입니다.
- 작업을 이어받을 때는 `docs/README.md`의 진행 중 작업 링크와 해당 계획의 재개 정보를 읽고 실제 서버 Git 상태와 대조합니다. 작업을 마치거나 옮기기 전에 그 계획에 재개 정보를 갱신하며 병렬 작업은 각 계획에서 관리합니다.

## 역할

- 이 폴더는 Exdigm의 에이전트 지침·스킬·기획 문서와 GBrain 연결 정보의 진입점입니다.
- 애플리케이션 소스는 기존 원격 저장소에 둡니다. 비밀값은 실제 사용·복구에 필요한 양쪽에서 관리할 수 있으며, 교체 기준을 하나로 정하고 필요한 값만 공급합니다. 문서·Git·로그에는 값을 남기지 않습니다.
- 중앙 Hermes의 샘이 10분마다 운영 오류 DB를 조회하고 새 오류를 직접 조사·보고합니다. 정기 실행은 수정·배포하지 않으며, 주인님의 명시적 지시가 있으면 샘이 SSH로 원격 디버깅 worktree를 수정·검증·Git 관리하고 별도 배포 지시에 따라 배포합니다.
- Exdigm 앱 서버에는 Codex·Claude 개발 에이전트와 조정실 지침·스킬·GBrain 설정을 설치하지 않습니다.

## 정본

| 항목 | 값 |
|---|---|
| SSH | `chaconne@49.247.202.197` |
| 호스트명 | `exdigm` |
| 운영 체크아웃 | `/home/chaconne/exdigm` |
| 디버깅 worktree | `/home/chaconne/exdigm-debug` |
| GitHub | `git@github.com:chaconne67/exdigm.git` |
| 배포 브랜치 | `main` |
| 디버깅 Python | `/home/chaconne/exdigm-debug/.venv/bin/python` |
| 디버깅 진입점 | `scripts/debug_workspace.sh` |
| 디버깅 실행 | 원격 셸의 `goexdigm` |
| 디버깅 도메인 | `https://dev.exdigm.com` |
| 운영 배포 | `scripts/deploy/deploy.sh prod` |
| 운영 DB 인프라 배포 | `scripts/deploy/deploy.sh db-prod` |
| 운영 도메인 | `https://office.exdigm.com` |

현재 코드·서버와 이 문서가 다르면 현재 상태를 확인해 코드와 서버에 맞춰 이 문서와 GBrain을 갱신합니다.

## 공식 작업 경로

1. GBrain과 원격 코드 상태를 확인합니다.
2. 운영 체크아웃이 `main`의 clean 상태인지 확인합니다.
3. 디버깅 worktree의 기존 변경을 확인하고 보존합니다.
4. 디버깅 worktree가 clean일 때만 `origin/main`의 detached HEAD로 갱신합니다.
5. SSH를 통해 디버깅 worktree의 코드만 수정합니다.
6. `scripts/debug_workspace.sh`로 격리된 검증을 실행하고, 필요할 때 `goexdigm`으로 같은 코드를 브라우저에서 확인합니다.
7. 변경을 커밋한 뒤 `scripts/deploy/deploy.sh prod`로 `origin/main`과 운영 체크아웃에 같은 커밋을 반영합니다.
8. HTTPS·Swarm 서비스·운영 작업자 상태를 확인합니다.

운영 체크아웃은 배포와 운영 작업자의 실행 원본입니다. 그 폴더에서 직접 수정하거나 테스트하지 않습니다.

## 디버깅 DB 경계

| 작업 | 공식 명령 | 데이터 경계 |
|---|---|---|
| 운영 데이터 조회 | `scripts/debug_workspace.sh shell-readonly` | `exdigm_debug_ro`의 SELECT만 허용 |
| 개발 사본 갱신 | `scripts/debug_workspace.sh refresh` | 운영 프로젝트 연결 후보자를 우선 포함한 정확히 1,000명과 연결 데이터·미디어만 복사 |
| Django 검사 | `scripts/debug_workspace.sh check` | 개발 사본 DB |
| 화면 확인 | 원격 셸에서 `goexdigm` | Docker 앱 없이 foreground `runserver`; `https://dev.exdigm.com`으로 접속 |
| 테스트 | `scripts/debug_workspace.sh test [대상]` | 개발 전용 테스트 DB; 외부 연동 인증은 읽지 않음 |
| Tailwind 빌드 | `scripts/debug_workspace.sh css` | 디버깅 worktree의 추적 CSS 갱신 |

- 운영 DB의 `exdigm` 슈퍼유저 계정으로 디버깅하지 않습니다.
- 운영 데이터가 필요한 진단은 조회 전용 경로에서 최소 결과만 확인합니다.
- 개발 사본에는 사용자·권한·고객사·프로젝트 기준 데이터를 복사합니다.
- 후보자·이력서·추출 산출물·미디어는 선택된 1,000명과 실제 DB 참조 범위만 복사합니다.
- 운영 배치 이력·뉴스 캐시·세션·큐·외부 사이트 인증은 복사하지 않습니다.
- DB와 미디어는 한 번의 `refresh`에서 함께 갱신하며, 완료 표식이 없으면 `goexdigm` 실행을 막습니다.
- 개발 Google Drive는 주인님의 개인 계정 내 개발 전용 폴더만 사용합니다.
- 운영 Drive 폴더·운영 Telegram 봇·운영 사이트 인증은 개발 환경에 넣지 않습니다.
- 외부 공개는 기존 Nginx의 HTTPS와 브라우저 암호가 맡고, `runserver`는 Docker bridge 주소에만 바인딩합니다.

## Git 경계

- 운영 체크아웃은 항상 `main`입니다.
- 디버깅 worktree는 Git의 동일 브랜치 중복 체크아웃을 피하기 위해 detached HEAD를 유지합니다.
- 디버깅 커밋의 `origin/main` push는 배포 스크립트가 fast-forward 방식으로 수행합니다.
- push 거절, 운영 dirty 상태, fast-forward 실패를 강제 push나 수동 파일 복사로 우회하지 않습니다.
- 저장소 전체 변경을 확인하고 사용자 변경을 포함한 하나의 검증된 커밋만 배포합니다.

## 코드 탐색과 완료 기준

- 코드 탐색은 원격 디버깅 worktree에서 `uv run --locked python -m tools.code_knowledge code_query`로 시작합니다.
- 테스트는 `scripts/debug_workspace.sh test`를 사용해 공용 잠금과 개발 전용 테스트 DB를 함께 적용합니다.
- 코드 변경 후 `uv run --locked python -m tools.code_knowledge catalog_update`를 원격 worktree에서 실행합니다.
- UI 변경은 `goexdigm`으로 띄운 같은 `runserver`를 `https://dev.exdigm.com`에서 직접 확인합니다.
- `resume-evolution-loop`로 수행하는 이력서 생성 개선의 프롬프트·생성 코드 반복 수정은 빠른 테스트·수정·재검증을 위해 해당 스킬의 `Direct Review Only`를 우선 적용하고 `code-review-loop`를 실행하지 않습니다.
- 이 예외는 이력서 진화의 반복 개선에만 적용합니다. 운영 배포·권한·운영 데이터·외부 효과를 바꾸는 작업은 예외가 아닙니다.
- 그 밖에 실행 동작·데이터·권한·배포 경로가 바뀌는 변경은 `code-review-loop`를 통과합니다.

## 회사 확장 경계

- 코드 저장소와 빌드 결과는 하나로 관리합니다.
- 회사별 DB·DB 역할·도메인·비밀값·미디어·작업자·외부 연동·백업은 분리합니다.
- 현재 Exdigm DB에 다른 HR 회사 데이터를 함께 넣지 않습니다.
- 공유 DB 멀티테넌시는 별도의 tenant 격리 설계와 검증 없이 도입하지 않습니다.

## 작업별 스킬

- 운영 오류 조회·조사·수정: `exdigm-error-control`
- 자동 게시: `auto-posting`
- 이력서·후보자 추출: `data-extraction`
- 화면·디자인 시스템: `exdigm-design`
- Hermes 제품 연동: `exdigm-hermes-agent`
- 추출 파이프라인 검증: `extraction-pipeline-verify`
- 이력서 생성 개선: `resume-evolution-loop`
- 운영 배포: `exdigm-deploy`
