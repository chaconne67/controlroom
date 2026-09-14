---
name: exdigm-hermes-agent
description: Use when changing, operating, debugging, or documenting Exdigm Hermes Telegram employee agents and their onboarding, provisioning, runtime, access, notification, migration, or offboarding boundaries.
---

# Exdigm Hermes Agent

Exdigm 직원별 Telegram Hermes의 구현·운영 규칙이다. 코드 위치는 코드 목차로
찾고, 이 스킬은 서비스 경계와 보존해야 할 계약에 집중한다.

## Start With Code Knowledge

```bash
uv run --locked python -m tools.code_knowledge code_query --query "헤르메스 에이전트"
uv run --locked python -m tools.code_knowledge code_query --query "Telegram 온보딩"
```

종료 코드 `3`이면 질의를 구체화한다. 종료 코드 `4`이면 `rg`로 현재 코드를
탐색한다. 공식 경로가 바뀌면 코드 목차와 canonical GBrain page를 함께 갱신한다.

## Official Boundaries

- 직원 1명당 `AgentProfile` 1개, 공식 Hermes container 1개, Telegram bot 1개다.
- 공식 온보딩: Exdigm 웹 → 텔레그램 관리자봇 → 관리형 봇 승인 → 독립 프로비저닝.
- 현재 공식 데이터 읽기: `code_query`로 업무 의미 해석 → `orm_read`로 현재 모델
  schema 확인 → 필요한 필드·조건·정렬·개수만 직원 권한 queryset에서 조회.
- 현재 공식 업무 실행: `code_query`로 업무 의미 해석 → 선택형 OpenAPI에서
  operation 계약 확인 → `exdigm_request` → 기존 Django 화면 뷰의 DRF 표현.
- 직원 Hermes의 Exdigm 전용 MCP 도구는 `code_query`, `orm_read`,
  `exdigm_request` 세 개다.
- 일회용 Telegram 연결 기록은 최초 온보딩에만 사용한다. 이후 fleet 재생성은 profile의
  지속 에이전트 키를 현재 직원의 DRF 인증에 사용한다.
- 공식 알림: Django → 직원 Hermes HMAC webhook → `deliver_only` → Telegram.
- Django는 직원 Telegram bot token을 읽거나 Telegram API로 직접 발송하지 않는다.
- 독립 프로비저닝 서비스만 직원 Hermes container와 profile secret 파일을 관리한다.
- 직원 비활성화·복귀·삭제는 Django의 수명주기 요청 DB에 먼저 확정한다.
- 기존 알림 배달 작업자가 독립 프로비저닝의 pause·resume·offboard HTTP 경계로
  전달하고 실패한 요청을 재시도한다.
- 기존 BotFather 입력, owner-bind, Django Docker 실행, `/agent/django`, custom image는 폐기 경로다.

## Hermes Defaults

- Nous Research 공식 Hermes image를 digest로 고정한다.
- 기본 추론 공급자는 `gemini`, 기본 모델은 `gemini-3.8-flash`다.
- 직원 profile에는 최소 `GEMINI_API_KEY`가 있어야 하며 모델 선택 화면에
  Gemini 공급자가 나타나야 한다.
- Hermes의 기본 추론, 메모리, 도구, 개인화, 스킬 학습 기능을 유지한다.
- Exdigm 업무를 주 역할로 안내하되 기본 Hermes 기능을 막지 않는다.
- `code_execution` 비활성, bundled skill 차단, 강제 SOUL 같은 구형 제한을 되살리지 않는다.
- GBrain은 중앙 조정실의 선택 지식원이다. 운영 Hermes profile에는 연결하지 않으며, GBrain 장애가 운영 업무 경로를 막지 않는다.

## Exdigm Access Policy

- 안내 지도는 업무 의미와 OpenAPI 분류 선택의 근거이며 실행 허용 목록이 아니다.
- `orm_read`는 Django의 현재 모델 필드·관계를 schema로 보여주고, Agent key에 연결된
  직원의 행 권한을 먼저 적용한 뒤 선택한 필드만 조회·정렬·집계한다.
- `orm_read`는 `status_code=200`일 때만 `data.result`와 `data.page`를 성공 결과로
  사용한다.
- `orm_read`는 쓰기, raw SQL, Python 실행, 비밀·내부 모델과 필드, 역관계 조회,
  무제한 결과를 허용하지 않는다.
- 회사 이메일은 외부 Mailplug IMAP/SMTP 상태를 다루므로 저장 데이터 범용 조회의
  예외다. 목록·상세·발송·휴지통 이동은 `email` 분류의 전용 OpenAPI operation을
  `exdigm_request`로 실행한다. 현재 Agent key 직원의 DB에 연결된 활성
  `@exdigm.com` 계정만 사용하며 계정 ID·발신 주소·앱 비밀번호를 입력받지 않는다.
  발송과 휴지통 이동은 사용자가 이번 동작을 명시적으로 요청한 경우에만 실행하고,
  삭제는 복구 가능한 서버 휴지통 이동까지만 허용한다.
- OpenAPI는 분류 → operation 목록 → operation 하나의 계약 순서로 필요한 부분만 읽는다.
- `exdigm_request`는 상세 계약의 `contract_token`과 입력을 검증한 뒤 Agent key로
  기존 Django 화면 뷰의 JSON 표현을 요청한다.
- 상세 계약이 파일 입력이나 바이너리 응답을 선언한 경우에만 작업공간 상대경로나
  Telegram이 알려준 `/opt/data/cache/...` 첨부 경로로 업로드하고, 다운로드는
  `workspace/`에 저장한다. 파일 본문은 대화나 JSON에 넣지 않는다.
- 업무별 읽기 API나 별도 inspect 도구를 추가하지 않고 모든 저장 데이터 읽기를
  공통 `orm_read`에 합친다.
- `DELETE`, 내부 프로비저닝·관리자 경로, 계약에 없는 입력은 사용하지 않는다.

## Profile Preservation

- 보존: profile name, `memories/`, `workspace/`, 직원 생성 `skills/`, Hermes state.
- 교체: `config.yaml`, `SOUL.md`, 예약 `skills/exdigm-work`, `.env`.
- 제거: `.no-bundled-skills`, 구형 snapshot·fingerprint·refresh marker,
  폐기된 관리형 runtime 산출물, stale session.
- 직원 생성 skill 전체를 지우지 않는다.
- 관리형 Gateway와 webhook 준비 완료 뒤에만 Django의 구형 bot token 필드를 비운다.
- 같은 준비 완료 뒤 구형 `hermes-config/<profile>`의 관리 secret·config 파일도 제거한다.

## References

- `references/architecture.md`: 역할과 공식 실행 경로
- `references/onboarding-provisioning-ops.md`: 관리형 연결·secret·프로비저닝
- `references/troubleshooting.md`: 장애 분리와 검증

## Verification

```bash
HERMES_INTEGRATION_ENABLED=true scripts/debug_workspace.sh test \
  tests/test_new_hermes_runtime.py \
  tests/test_hermes_deploy.py \
  tests/test_provisioning_service.py \
  tests/test_gemini_gateway.py \
  tests/accounts/test_provisioning_bootstrap.py \
  tests/accounts/test_agent_lifecycle.py \
  tests/accounts/test_telegram_connection_boundary.py \
  tests/test_telegram_connection_service.py \
  tests/test_notification_dispatch_worker.py

uv run --locked python -m tools.code_knowledge catalog_update
HERMES_INTEGRATION_ENABLED=true scripts/debug_workspace.sh check
```

운영 container·Telegram 검증은 사용자가 운영 작업을 요청한 경우에만 수행한다.
