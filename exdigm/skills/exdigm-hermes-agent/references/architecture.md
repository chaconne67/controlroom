# Architecture

## Components

| 정확한 이름 | 역할 | 실행 위치 |
|---|---|---|
| 텔레그램 관리자봇 | 직원이 처음 대화하는 실제 Telegram bot 계정 | Telegram |
| Telegram 연결 API | 관리자봇 update 처리, 계정 연결, 관리형 봇 승인·token 취득 | 독립 서비스 |
| 프로비저닝 | 직원별 profile·secret·공식 Hermes container 생성 | 독립 서비스 |
| 직원별 Telegram 봇 | 직원이 자기 Hermes와 대화하는 실제 bot 계정 | Telegram |
| 직원별 Hermes | 기억·세션·스킬·추론을 가진 에이전트 | 직원별 container |
| Exdigm MCP | `code_query`, 읽기 전용 `orm_read`, 계약 검증형 `exdigm_request` 제공 | 직원별 container |
| Exdigm 웹 | 직원 인증·기존 화면의 HTML/DRF 표현과 업무 기능 제공 | Django 웹 서버 |

텔레그램 bot 계정 자체는 코드를 실행하지 않는다. Telegram이 보낸 update를
Telegram 연결 API가 관리자봇 token으로 수신하고 처리한다.

## Single Success Paths

### Onboarding

```text
Exdigm 설정 화면
→ Telegram 관리자봇 deep link
→ 직원의 Telegram 숫자 ID 연결
→ Telegram 관리형 봇 생성 승인
→ Telegram 연결 API가 직원 봇 token 취득
→ 독립 프로비저닝 접수
→ profile secret 생성
→ 공식 Hermes container 시작
→ webhook health 확인
→ Django 연결 상태 active
→ Django 구형 bot token 정리
```

### Work Path

```text
직원 Telegram 요청
→ 직원별 Hermes
→ 필요한 새 업무용어를 code_query로 해석
→ 저장 데이터 읽기면 orm_read에서 현재 schema 확인
→ 직원 권한 queryset에서 필요한 필드·조건·정렬·개수만 조회
→ 업무 동작이면 선택형 OpenAPI에서 필요한 operation 하나 확인
→ exdigm_request가 계약과 Agent key를 검증해 기존 Django 업무 기능 실행
→ JSON 결과·건수·오류 또는 계약에 선언된 안전한 첨부·workspace 파일 확인
```

현재 에이전트에 노출하는 Exdigm 전용 MCP 도구는 `code_query`, `orm_read`,
`exdigm_request` 세 개다. 저장 데이터 읽기는 공통 `orm_read` 하나에 합치고,
생성·수정·발송·파일 처리는 기존 업무 기능을 실행한다.

### Notification

```text
Exdigm_net 안의 Django NotificationDispatch 작업자
→ 직원 Hermes의 HMAC V2 webhook
→ deliver_only route
→ 직원별 Telegram 봇
→ 직원 Telegram
```

## Deployment Boundary

- Django 웹 배포와 Hermes 인프라 배포는 별개다.
- 알림 배달 작업자는 Django 앱 image의 별도 stack service이며 `Exdigm_net` 안에서
  실행한다. 호스트 systemd 작업자로 실행하지 않는다.
- Django stack 배포는 새 알림 작업자를 시작하기 전에 구형 host
  `exdigm-notification-dispatcher.service`를 정지·비활성화·삭제한다.
- Django web container는 Docker socket이나 직원 profile directory를 소유하지 않는다.
- Telegram 연결 API와 프로비저닝은 같은 저장소여도 서로 다른 프로세스·container다.
- 프로비저닝은 Nous Research 공식 image, 직원 profile directory, 로컬 Exdigm MCP를 소유한다.
- 최초 온보딩 뒤 fleet 재생성은 profile의 지속 에이전트 키를 보존한다. 짧게 유지되는
  Telegram 연결 기록을 재사용하지 않는다.
- Django 직원 lifecycle signal은 외부 HTTP를 호출하지 않고 수명주기 요청을
  같은 DB transaction에 기록한다.
- 기존 알림 배달 작업자가 확정된 수명주기 요청을 독립 프로비저닝의 인증된
  pause·resume·offboard endpoint로 전달하고 일시 실패를 재시도한다.
- 같은 profile의 수명주기 요청은 생성 순서를 앞지르지 않는다.
- offboard는 이전 pending 요청을 대체하는 최종 상태다.
- 프로비저닝은 container 준비 뒤 Django의 현재 직원 상태를 다시 확인하고,
  비활성 직원의 새 container를 성공 처리 전에 정지한다.
- GBrain은 개발 프로비저닝에서만 선택적으로 연결한다.
