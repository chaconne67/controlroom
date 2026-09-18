---
name: exdigm-design
description: Use when creating or modifying Exdigm UI, templates, styling, or user interactions.
---

# Exdigm Design

Exdigm UI 작업의 단일 진입점이다. 이 파일은 모든 UI 작업의 공통 실행·검수 게이트와 필요한 레퍼런스의 적용 순서를 정한다. 토큰·컴포넌트·업무 화면 규칙은 레퍼런스에 둔다.

## 1. 원천과 레퍼런스

### 원천 우선순위

1. `/home/chaconne/exdigm-debug/tailwind.config.js`와 `/home/chaconne/exdigm-debug/static/css/input.css` — 토큰·공통 컴포넌트의 실제 원천
2. 수정 대상 운영 템플릿 — 실제 조합과 현재 DOM
3. `/home/chaconne/exdigm-debug/assets/ui-sample/` — 화면 의도 reference
4. 이 스킬의 레퍼런스 — 원천을 작업 절차에 맞게 정리한 규칙

불일치하면 코드가 기준이다. 코드 원천을 바꿨다면 해당 레퍼런스도 같은 작업에서 갱신한다.

### 레퍼런스 선택표

| 작업 상황 | 반드시 읽을 레퍼런스 |
|---|---|
| 색·폰트·간격·레이아웃·스크롤·아이콘 | [foundations.md](references/foundations.md) |
| 카드·헤더·모달·표·칩·캘린더·진행 단계 | [components.md](references/components.md) |
| 라벨·정보 위계·폼·반복 행·보이스 검색·인라인 편집 | [ux-rules.md](references/ux-rules.md) |
| 버튼·폼·토글·행 편집·모달·HTMX 요청 | [interaction-acceptance.md](references/interaction-acceptance.md) |
| 프로젝트·후보자 작업공간·검색·칸반·References 화면 | [screen-patterns.md](references/screen-patterns.md) |
| 모든 UI 변경의 브라우저 검수 | [verification.md](references/verification.md) |

관련 없는 레퍼런스를 습관적으로 읽거나, 세부 규칙을 이 파일에 다시 추가하지 않는다.

### 작업별 게이트 경로

| 변경 종류 | 통과 경로 |
|---|---|
| 색·타이포·여백처럼 정적인 시각 변경 | Gate 0 → 1(Foundations) → 2 → 5 → 6 |
| layout·scroll·card·modal·table | Gate 0 → 1(Foundations + Components) → 2 → 5 → 6 |
| label·form·반복 행·inline edit | Gate 0 → 1(Foundations + UX Rules) → 2 → 5 → 6 |
| 버튼·폼 제출·HTMX·modal·비동기 상태 변경 | Gate 0 → 1(Foundations + UX Rules + IAC) → 2 → 3 → 5 → 6 |
| 프로젝트·Workspace·검색·알림·칸반·References | 위 해당 경로 + Gate 4(Screen Patterns) |

## 2. 실행 게이트

### Gate 0 — 범위와 변경 종류 고정

코드 전에 아래를 정한다.

- 변경하는 화면·보이는 컨트롤·사용자 업무 결과
- 정적 시각 변경인지, 사용자 행동으로 상태가 바뀌는 동적 변경인지
- 바뀌어야 하는 DOM 범위와 보존해야 하는 입력·URL·스크롤·열린 상태

동적 변경이면 Gate 3을 생략할 수 없다. 작업 화면이 정해진 업무 패턴이면 Gate 4도 적용한다.

### Gate 1 — 실제 원천과 필요한 규칙 읽기

1. 수정할 템플릿과 그 부모 partial을 읽는다.
2. 선택표에서 해당 레퍼런스만 읽는다.
3. Tailwind class 또는 공통 컴포넌트를 쓸 때는 실제 원천에서 존재를 확인한다.
4. mockup과 운영 코드가 다르면 운영 코드의 계약을 지키고, 차이는 원천 기준으로 정리한다.

토큰·클래스·DOM 소유자를 확인하지 못하면 추측으로 새 스타일이나 swap 범위를 만들지 않고 차단 상태로 보고한다.

### Gate 2 — 화면 구조와 시각 계약

`foundations.md`와 필요한 `components.md`·`ux-rules.md`를 기준으로 다음을 결정한다.

- 사용자가 판단하는 순서에 따른 정보·입력·출력·행동의 배치
- 제목 위계, 여백, 카드 경계, 라벨, 상태 표현
- 적용할 토큰과 기존 컴포넌트 클래스
- 단일 세로 스크롤 소유자와 독립 스크롤의 필요성

이 단계에서 독립 의미가 없는 중첩 박스, 코드 어감 라벨, 스타일 기본값 누락을 제거한다.

### Gate 3 — 인터랙션 수용 계약

사용자 행동이 서버·데이터·화면 상태를 바꾸면 [interaction-acceptance.md](references/interaction-acceptance.md)의 IAC를 작업 계획 또는 commentary에 구체적으로 선언한다.

- 입력 SSOT → 처리 경로 → 저장/생성 출력 → 렌더링 순서를 고정한다.
- 상태 전이와 성공·실패의 보이는 결과를 정한다.
- `hx-target`·`hx-swap`·OOB를 포함한 변경 경계를 정한다.
- 선언 밖 페이지·카드·폼 전체 swap, 입력 소실, 이중 요청을 금지한다.

### Gate 4 — 업무 화면 패턴 적용

프로젝트, 후보자 Workspace, 검색, 알림, 칸반, References 화면이면 [screen-patterns.md](references/screen-patterns.md)를 읽고 그 화면의 데이터 위계와 행동 경계를 적용한다.

화면 고유 규칙과 공통 규칙이 충돌하면, 실제 코드 원천 다음으로 업무 화면 규칙을 우선한다.

### Gate 5 — 구현

- 운영 템플릿은 Tailwind 토큰과 기존 공통 클래스를 먼저 사용한다.
- 페이지 단위 style, 임의 CSS 클래스, 토큰 밖 hex를 새로 만들지 않는다.
- 활성 컨트롤은 선언한 진행·성공·실패 결과 중 하나를 보인다. 미구현 행동은 비활성 또는 준비 중으로 보인다.
- 반복 행과 부분 갱신은 가장 작은 업무 단위만 교체한다.

### Gate 6 — 검수와 종료

에이전트 브라우저 검수는 아래 설정을 항상 먼저 적용한다.

1. 원격 디버깅 worktree의 `scripts/debug_workspace.sh status`로 일회성 DB를 확인하고, 없으면 `create`로 준비한다.
2. 기존 `runserver`가 없을 때만 `scripts/debug_workspace.sh run`을 실행한다.
3. SSH 포트 포워딩을 통해 `http://127.0.0.1:8443`의 대상 경로를 연다. 운영 URL이나 공개 포트로 디버깅 서버를 노출하지 않는다.
4. `.debug/sandbox-login.txt`의 일회성 계정으로 로그인해 대상 화면을 캡처한다. `/accounts/login/`·`403`이면 완료하지 않는다.

[verification.md](references/verification.md)의 화면 수용 기준을 적용한다. 동적 변경은 IAC의 클릭 전·처리 중·결과 후 검증을 추가한다.

다음 중 하나면 완료가 아니다.

- 실제 디버깅 `runserver`에서 대상 화면과 캡처를 만들지 못함
- 성공·실패·보존 조건 중 하나를 증명하지 못함
- 콘솔·네트워크의 새 오류, 선언 밖 swap, 이중 스크롤, 토큰·폰트 이탈이 남음

## 3. 유지 규칙

- 반복되는 디자인·UX 규칙은 먼저 어떤 레퍼런스의 어느 게이트를 바꾸는지 정한 뒤 그 레퍼런스에만 추가한다. 모든 UI 작업에 필요한 공통 실행·검수 게이트만 이 파일에 둔다.
- 단일 화면 사례가 아니라 반복 가능한 원칙만 남긴다.
- 이 파일에는 토큰표·컴포넌트 세부값·화면별 체크리스트를 복제하지 않는다.
- 레퍼런스를 변경하면 이 선택표와 게이트의 경로가 여전히 맞는지 검토하고 `quick_validate.py`를 실행한다.
