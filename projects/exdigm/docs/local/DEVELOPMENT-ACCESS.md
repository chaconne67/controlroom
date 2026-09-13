# Exdigm 개발·디버깅 접근 안내

확인일: 2026-09-08. 이 문서는 접속·설정 위치 안내이며 비밀값은 포함하지 않습니다. 실제 코드와 프로젝트 AGENTS.md가 우선합니다.

## 환경

| 용도 | 정본 |
|---|---|
| Windows 조정실 | `C:\Users\chaconne\projects\exdigm` |
| SSH | `chaconne@49.247.202.197` |
| 운영 코드 | `/home/chaconne/exdigm` — 운영 main, 직접 수정·테스트 금지 |
| 개발 코드 | `/home/chaconne/exdigm-debug` — detached worktree |
| 개발 진입점 | `scripts/debug_workspace.sh` |
| 개발 화면 | `https://dev.exdigm.com` |
| 운영 화면 | `https://office.exdigm.com` |
| 원격 uv | `/home/chaconne/.local/bin/uv` — 비대화형 SSH에서 PATH에 없을 수 있음 |

## 설정·인증 위치

| 항목 | 위치 및 확인 상태 |
|---|---|
| 운영 Gemini 키 | `/home/chaconne/exdigm/.env`의 `GEMINI_API_KEY` 존재 확인. 값은 출력하지 않음. 파일 권한 0600 |
| 개발 외부 연동 | `/home/chaconne/exdigm-debug/.debug/integrations.env`. 사용자 승인에 따라 Gemini 키만 공급 완료. 파일 권한 0600. 운영 DB·Telegram·사이트 인증은 함께 복사하지 않음 |
| 개발 DB | `.debug/sandbox.env` |
| 운영 조회 전용 DB | `.debug/readonly.env` |
| 개발 화면 로그인 정보 | `.debug/public-login.txt`, `.debug/sandbox-login.txt`. 원격 개발 브라우저 검증에 사용. 값은 로컬 문서·대화에 기록하지 않음 |
| 운영 설정 주입 | `scripts/render_secret_env.py` → 기존 운영 실행 스크립트. 전체 `.env`를 개발 환경으로 주입하지 않음 |
| 링크드인 대표 계정 | 운영 `LINKEDIN_ID`·`LINKEDIN_PW`; 기존 영속 브라우저 CDP 19326 |
| 링크드인 개인 계정 | 현재 검색자의 활성 `ExternalSiteCredential`; 개인 브라우저 포트는 동적 |
| 외부 후보검색 브라우저 | CDP 9223; 자동 게시 9222와 별도 |

개발 키가 없다는 사실과 운영 키가 없다는 사실은 다릅니다. 먼저 위 정본의 존재 여부와 공식 주입 경로를 확인합니다. 사용자에게 이미 있는 정보를 다시 묻기 전에 운영 설정에서 필요한 항목만 확인합니다. 키 재사용 시에는 필요한 키만 승인된 개발 실행 범위에 공급하고 DB·Telegram·사이트 인증·Drive 등 다른 운영 연동을 함께 가져오지 않습니다. 비밀값은 실제 사용·복구에 필요한 양쪽에서 관리할 수 있습니다. 교체 기준을 하나로 정하고 필요한 값만 공급하며 문서·Git·로그에는 값을 남기지 않습니다.

## 원격 공식 명령

아래 명령은 SSH 접속 후 `/home/chaconne/exdigm-debug`에서 실행합니다.

```bash
git status --short --branch
git -C /home/chaconne/exdigm status --short --branch
/home/chaconne/.local/bin/uv run --locked python -m tools.code_knowledge code_query --query candidate_search --format markdown
scripts/debug_workspace.sh status
scripts/debug_workspace.sh shell-readonly
scripts/debug_workspace.sh check
scripts/debug_workspace.sh test tests/test_candidate_sourcing.py
```

- `shell-readonly`는 운영 SELECT 전용입니다. 화면 조작·데이터 변경 검증은 개발 사본에서 합니다.
- `goexdigm`은 원격 셸의 기존 개발 실행 진입점입니다.
- `refresh`는 개발 DB와 미디어를 재생성하므로 단순 진단 시 실행하지 않습니다.
- 조회 결과는 작업 상태·오류·최소 통계로 제한합니다. 자격값·후보 원문을 대량 출력하지 않습니다.
- 배포는 검증·리뷰·커밋 후 `scripts/deploy/deploy.sh prod` 경로만 사용합니다.

## 검색 장애 근거

- 작업 상태: `SearchSession.workflow_state`의 plan, progress, result.sites, started_at, completed_at.
- 서비스: `exdigm-candidate-sourcing-worker`, `exdigm-linkedin-browser`.
- 로그: `journalctl -q -u exdigm-candidate-sourcing-worker -n 50 --no-pager`.
- 사이트 증거: `/home/chaconne/exdigm/runtime/auto_posting/evidence/<site>/`.
- GBrain: 로컬 `~/.gbrain-agent.md`의 현행 공용 경로. 프로젝트 시작점은 `default:project/exdigm-operating-context`.

2026-09-07 수정 전 검사에서 관련 3개 테스트 파일은 97 통과, 후보 선택 시 `ActionType` 기준 데이터 누락으로 1 실패였습니다. 이는 전체 통과가 아니며 검사를 삭제·완화할 근거가 아닙니다.
