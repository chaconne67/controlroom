# UX Structure and Language

## 화면 구조

화면은 기능 나열이 아니라 사용자가 판단하고 행동하는 순서로 구성한다.

1. 화면 영역은 사용자 업무 단위로 나눈다.
2. 같은 위계의 선택지만 함께 둔다.
3. 선택 전에도 이름·설명·위치만으로 결과를 예측할 수 있게 한다.
4. 버튼 문구·위치·강조는 실제 결과와 일치시킨다.
5. 조회·선택·저장·확정·제출처럼 책임이 다른 행동은 다른 무게로 보이게 한다.
6. 입력은 원천, 생성된 결과는 출력으로 구분해 배치한다.
7. 앱 셸 header가 breadcrumb와 page title을 이미 소유하면 본문에서 같은 eyebrow·제목을 반복하지 않는다. 본문 제목은 더 좁은 업무 단위를 명명할 때만 사용하고, 반응형 화면의 의미상 제목이 필요하면 `sr-only` heading으로 보존한다.

## 보이는 행동

- 활성 버튼은 화면 상태 변화, 모달/패널 열기, 성공·실패가 보이는 저장, 별도 탭 파일 열기 중 하나로 끝난다.
- 기능이 준비되지 않았으면 활성 CTA처럼 보이지 않게 비활성 또는 `준비 중`으로 표시한다.
- 저장 실패는 사용자가 읽을 수 있는 오류와 다음 행동을 같은 흐름에 표시한다.
- 외부 파일/PDF는 모달에 억지로 넣지 않고 새 탭 또는 다운로드로 처리한다.

## 라벨과 상태 문구

- 사람의 업무 의미를 쓰고, 처음 보는 사용자도 문구만으로 행동을 이해하게 한다.
- 코드 상태명·개발 검증명·`timeout`, `orphan`, `stale`, `fraud`, `dropped` 같은 코드 어감은 운영 UI에 노출하지 않는다.
- `+`, `액션`, `드롭`, `에스컬레이션`, `내부 양식 변환`처럼 결과가 불명확한 라벨은 쓰지 않는다.
- 이력을 권위 있게 알 수 없으면 최초/재실행을 추정하는 이름을 만들지 않는다. 현재 사용자가 정하는 입력과 행동을 이름으로 쓴다.
- `연결 전`·`시작해 주세요`처럼 기본 상태와 CTA를 그대로 반복하는 상태 설명은 별도 영역으로 만들지 않는다. 진행·성공·실패처럼 사용자의 판단이나 다음 행동이 달라질 때만 상태 영역을 표시한다.
- icon-only 버튼에는 `aria-label`을 넣고, hover 설명이 추가로 필요할 때만 `title`을 쓴다.

## 폼과 반복 행

- 이미 card가 감싼 section 안에서 반복 항목을 다시 rounded·border·background box로 감싸지 않는다.
- 기본 반복 선택 행: `flex items-center gap-4 py-3`; checkbox 클릭 영역, 이름, 선택 form은 같은 행의 한 업무 단위다.
- 실제 checkbox를 다른 필드의 시작선에 맞춰야 하면 `w-5`와 작은 gap으로 input을 시작선에 둔다. label은 같은 checkbox를 가리킨다.
- Django choice를 자체 label과 함께 출력할 때는 `{{ option.tag }}`로 input만 렌더링한다. `{{ option }}`와 별도 label을 함께 써서 label을 중복하지 않는다.
- 저장·취소·확정·위험 action은 section 하단, modal footer, danger zone 같은 action 영역에 둔다. box 안에 둘 수 있는 것은 독립 form 또는 독립 실행 단위뿐이다.

## 모달과 인라인 편집

- 하위 modal은 상위 Workspace를 통째로 밀어내지 않는다. 닫으면 원래 작업 위치로 돌아온다.
- 정보 위계가 높은 header의 Edit는 작은 ghost icon으로 둔다. 큰 진한 사각 버튼·긴 input underline은 title 위계를 깨므로 쓰지 않는다.
- 편집 상태의 저장은 입력값 근처의 작고 예측 가능한 텍스트 버튼으로 둔다.

## 탐색과 HTMX

- 페이지 navigation: `hx-get`, `hx-target="#main-content"`, `hx-push-url="true"`.
- form submission은 specific target을 선언한다.
- 행 Edit·실행은 행 자신만 `outerHTML`로 바꾼다. 전체 페이지·card·form swap이나 redirect로 스크롤과 열린 입력을 잃지 않는다.
- 로딩 indicator는 초기 `display: none`; 요청 중에만 `inline-flex`다. 보이지 않아도 폭을 차지하는 opacity-only indicator는 쓰지 않는다.

## 보이스 우선

- 검색·조작의 첫 진입은 음성 또는 텍스트 자연어 입력이다.
- 전통 filter UI를 추가하기 전 voice-first 흐름과 충돌하지 않는지 확인한다.
- 관련 실제 원천: `/home/chaconne/exdigm-debug/projects/views_voice.py`, `/home/chaconne/exdigm-debug/projects/services/voice/`, `/home/chaconne/exdigm-debug/candidates/static/candidates/voice-input.js`.

## 운영 템플릿

- Tailwind token과 `input.css` 공통 class를 먼저 쓴다.
- 페이지 단위 `<style>`, 임의 custom CSS class, token을 우회한 hex를 만들지 않는다.
- 독립 실행 mockup만 `/home/chaconne/exdigm-debug/assets/ui-sample/`에서 inline style을 허용한다. 토큰은 코드 원천과 일치해야 한다.
