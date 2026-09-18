# Interaction Acceptance Contract (IAC)

## 적용 조건

버튼·폼·토글·행 편집·모달·비동기 요청처럼 사용자 행동으로 데이터나 화면 상태가 바뀌는 모든 UI에 적용한다. IAC는 Design by Contract의 사전/사후/불변조건, BDD의 Given/When/Then, HTMX의 swap 계약, Definition of Done, E2E 시각 검증을 하나의 실행 계약으로 묶는다.

## Gate I — 구현 전 계약

코드 전에 작업 계획 또는 commentary에 아래를 구체적으로 선언한다. 대상·데이터·위치가 빠진 `성공하면 갱신한다`는 계약이 아니다.

| 항목 | 선언할 내용 |
|---|---|
| 사용자 의도 | 누르는 보이는 control과 기대 업무 결과 |
| Given | 권한, 유효한 입력, 현재 데이터 상태 |
| 입력 / SSOT | 전송 field·file·selection과 각각의 단일 진실 원천 |
| When | event → HTTP method/URL → view/service → 저장·생성 |
| Then | 생성·저장되는 값과 정확한 화면 위치 |
| 상태 전이 | `ready → in-flight → succeeded` 및 `ready → in-flight → failed` |
| 변경 경계 | DOM target·OOB target, 보존할 input·URL·스크롤 소유자·영역 |
| 렌더링 | response partial, `hx-target`, `hx-swap`, 허용 OOB, redirect 근거 |
| 시각 | 토큰·글꼴·위계·간격·loading·error 위치 |
| 불변조건 | 행동 전후 유지할 데이터·DOM·URL·scroll·열린 입력 |
| 실패 | 오류 문구·위치·재시도·입력 보존 규칙 |

필수 값이나 권위 있는 상태가 없으면 지어내지 않는다. 계약을 만들 수 없으면 구현을 멈추고 필요한 입력을 확인한다.

## Gate II — 구현 경계

1. 데이터 계약을 먼저 구현한다: 입력 → 처리 → 저장/생성 출력 → rendering.
2. 비동기 동작은 `hx-target`/`hx-swap` 또는 동등 target을 명시한다.
3. 반복 행의 action은 그 행만 교체한다. 선언하지 않은 page·card·form 전체를 교체하지 않는다.
4. 활성 action은 loading·success·failure 중 하나가 반드시 보인다.
5. service 직접 호출·Django client·fixture는 처리 보조 검증이다. 실제 UI 검증을 대신하지 못한다.

## Gate III — 상태별 수용 기준

| 상태 | 보여야 할 결과 | 바뀌는 범위 | 금지 변화 | 증거 |
|---|---|---|---|---|
| 클릭 전 | input·button·기존 output이 계약대로 보임 | 없음 | 숨은 loading의 공간 점유, 기존 input 손실 | screenshot + DOM |
| 처리 중 | 클릭한 control에서만 loading/disabled/progress | 그 control | page swap, duplicate request, input 손실 | 실제 클릭 직후 screenshot + request |
| 성공 | Then의 데이터가 선언 위치·형태로 rendering | 선언 target | 선언 밖 DOM/URL/scroll 변경, input 소실 | response + DOM + screenshot |
| 실패 | 사람이 이해할 오류와 다음 행동 | 오류 target | 조용한 실패, 성공처럼 보임, 임의 보정 | error response + DOM + screenshot |

## Gate IV — 완료 판정

다음을 모두 만족하기 전에는 완료·커밋·배포 완료라고 보고하지 않는다.

1. 보호 가치 있는 계약 테스트가 있으면 Given·Then·실패 경로를 검증한다. 새 테스트는 프로젝트의 테스트 작성 조건을 모두 충족할 때만 추가한다.
2. 실제 개발 URL의 보이는 control을 클릭한다. DOM 주입이나 service 직접 호출은 E2E가 아니다.
3. 클릭 전·처리 중·성공 또는 실패 후를 각각 캡처하고 직접 비교한다.
4. 성공 데이터, response 상태, 선언 target DOM을 확인한다.
5. 실패 오류 위치·문구·기존 input 보존을 확인한다.
6. 콘솔 새 오류와 네트워크 실패를 확인한다. 허용할 기존 오류는 계약에 원인·범위를 기록한다.
7. 불변조건과 변경 경계를 확인한다. 전체 page swap, URL 변경, 이중 scroll, 폰트·token 이탈도 검사한다.

외부 게시·결제·삭제처럼 되돌릴 수 없는 action은 공식 dry/test 최종 경로로 화면과 상태를 검증한다. 실제 실행은 주인님의 명시 승인이 있어야 한다. 실제 화면·상태를 만들 수 없으면 차단 상태이며 코드·단위 테스트만으로 완료할 수 없다.
