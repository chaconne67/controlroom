# Managed Onboarding And Provisioning

## Employee Flow

1. 직원이 Exdigm Telegram 설정의 연결 버튼을 누른다.
2. Telegram 앱이 관리자봇 개인 대화창을 연다.
3. 직원이 Telegram의 시작 버튼을 누른다.
4. Telegram 연결 API가 관리자봇 update의 숫자 사용자 ID와 일회용 연결값을 결합한다.
5. 직원이 Telegram 안에서 개인 비서 생성을 승인한다.
6. Telegram 연결 API가 Telegram 관리형 봇 정보를 취득한다.
7. Telegram 연결 API가 token을 Django에 저장하지 않고 독립 프로비저닝에 전달한다.
8. 프로비저닝이 직원 profile secret 파일과 공식 Hermes container를 만든다.
9. 프로비저닝이 container 내부 webhook `/health`를 확인한다.
10. Telegram 연결 API가 Django 상태를 `active`로 바꾼다.

직원은 BotFather, token 복사, username 생성 규칙을 직접 다루지 않는다.

## Secrets

| secret | 저장 위치 | 읽는 주체 |
|---|---|---|
| 관리자봇 token | Telegram 연결 API secret 환경 | Telegram 연결 API |
| 직원 bot token | 직원 profile의 mode `0600` `.env` | 직원 Hermes Gateway |
| 에이전트 키 | Django 암호화 DB + 직원 profile의 mode `0600` `.env` | 프로비저닝, Django 인증 |
| webhook secret | Django 암호화 DB + 직원 profile `.env` | Django, 직원 Hermes webhook |

- 프로비저닝 job DB, 응답, 로그에 plaintext secret을 넣지 않는다.
- `.env`는 임시 파일을 fsync한 뒤 원자적으로 교체한다.
- 직원 bot token은 활성화 뒤 Django의 구형 필드에서 제거한다.
- 새 Gateway webhook 준비 뒤 구형 `/var/lib/exdigm/hermes-config/<profile>`의
  `.env`, config, SOUL, 관리 marker를 제거한다.
- 알 수 없는 구형 파일은 임의로 삭제하지 않는다.

## Official Runtime

- Nous Research 공식 Hermes image를 digest로 고정한다.
- custom Dockerfile·entrypoint monkey patch를 만들지 않는다.
- profile directory와 Exdigm MCP directory를 read-write/read-only로 정확히 mount한다.
- container 이름은 `exdigm-agent-<canonical-profile-name>`이다.
- container 실행 확인만으로 성공 처리하지 않는다.
- webhook health가 `{"status":"ok","platform":"webhook"}`일 때만 성공 처리한다.

## Profile Migration

보존:

- `memories/`
- `workspace/`
- 직원 생성 `skills/<name>/`
- Hermes state DB

정리:

- `.no-bundled-skills`
- `.skills_prompt_snapshot.json`
- `.exdigm_recipe_refresh_epoch`
- `.exdigm-profile-fingerprint`
- `sessions/sessions.json`
- `skills/exdigm-work`
- 폐기 제품명으로 생성된 이전 예약 skill
- 예약된 공식 skill은 새 `skills/exdigm-work`로 다시 생성

## GBrain

- 중앙 조정실에서만 조회한다.
- 운영 profile에는 연결하지 않는다.
- GBrain 장애는 Exdigm MCP·Telegram 작동을 막지 않는다.

## Deployment

- Django 일반 배포와 Hermes 배포는 별도 명령이다.
- 운영: `scripts/deploy/deploy_hermes.sh prod <git-commit>`.
- 순서: preflight → 공통 Exdigm MCP 교체 → 독립 인프라 재시작 →
  전 직원 공식 Hermes recreate → fleet health.
- recreate는 profile의 지속 에이전트 키를 보존한다. 최초 온보딩의 Telegram 연결
  기록이나 bootstrap을 다시 호출하지 않는다.
- 직원 profile `.env`, memory, workspace, 직원 생성 skill은 보존한다.
- Telegram live health는 관리자봇 token·username 일치와 Telegram 연결 API의
  Django 인증 읽기를 모두 확인한다.
- 장기 컨테이너에는 서비스별 allowlist secret만 전달한다.
- 실패 시 자동 rollback을 만들지 않는다. 출력된 직전 Git commit을 같은 명령으로
  다시 배포한다.
- 실제 운영 배포는 별도 명시적 승인 없이는 실행하지 않는다.

## Employee Lifecycle

- 비활성화: Django 사용자 변경 + 수명주기 요청 확정 → 배달 작업자 →
  프로비저닝 `pause` → `docker stop`.
- 복귀: Django 사용자 변경 + 수명주기 요청 확정 → 배달 작업자 →
  프로비저닝 `resume` → `docker start` → webhook readiness → profile `active`.
- 삭제: Django 사용자 삭제 + FK 없는 offboard 요청 확정 → 배달 작업자 →
  프로비저닝 `offboard` → container 제거 → profile의 runtime secret 제거.
- 프로비저닝 호출 실패는 요청을 `pending`으로 유지하고 지수형 대기 뒤 재시도한다.
- 같은 profile의 뒤 요청은 앞 요청이 성공·대체되기 전 실행하지 않는다.
- offboard를 기록할 때 그 profile의 이전 pending 요청은 `superseded`로 끝낸다.
- user·profile 삭제 뒤에도 offboard 요청은 남아 있어야 한다.
- resume webhook readiness 실패 시 시작한 container를 다시 정지한다.
- 신규 프로비저닝은 container 준비 뒤 현재 직원 상태를 다시 조회한다.
- 현재 직원이 비활성이면 job 성공 전에 container를 정지하고 profile을 `paused`로 둔다.
- Django는 Docker socket·container filesystem을 직접 사용하지 않는다.
