---
name: ceoloan-design-system
description: Use when creating, modifying, reviewing, or validating CEO Loan product UI, Django templates, shared components, Tailwind CSS, HTMX or Alpine interactions, responsive layouts, forms, tables, modals, loading states, or accessibility.
---

# CEO Loan 디자인 시스템

CEO Loan의 실제 코드에 이미 있는 시각 언어와 영업 업무 흐름을 보존하면서 제품 UI를 변경한다.
토큰·컴포넌트·화면 계약은 원격 운영 저장소가 정본이며 이 스킬에 값을 복제하지 않는다.

## 적용 경계

- 웹 제품 화면·템플릿·상호작용에는 이 스킬을 사용한다.
- MMS 카드 이미지는 `assets/mms-design-concept.md`와 해당 생성 경로를 사용한다.
- MMS의 밝은 인포그래픽 규칙을 웹 제품 화면에 옮기거나 웹 WDS를 MMS에 강제하지 않는다.
- 백엔드·배포 작업은 사용자 화면이나 상호작용이 바뀔 때만 이 스킬을 사용한다.

## 실행 위치

- 조정실: `~/projects/ceoloan`; 이 스킬 원본은 프로젝트의 `skills/ceoloan-design-system`, 공통 지침 원본은 `~/projects/.controlroom`이다.
- 앱·빌드·개발 서버의 SSH 접속과 실제 저장소는 프로젝트 `AGENTS.md`의 현행 경로를 따른다.
- 운영 URL: `https://rogeon.kr`. 호스트 코드를 직접 읽는 정기 작업은 웹 배포 전에도 소스 변경의 영향을 받는다.
- 원격 화면 검증은 공용 `web-automation`의 「Remote development UI verification」을 따른다.
  아래 「프로젝트 검증 설정」을 그 절차의 입력으로 사용한다.

## 정본 순서

다음 순서로 실제 파일을 읽고 결정한다.

1. 변경 대상 템플릿과 가장 가까운 화면·partial
2. `wds-tokens.json` — WDS 토큰 원본
3. `tailwind.config.js` — WDS와 `paper`·`ink`·`accent`·`line` 매핑
4. `static/css/input.css` — `.select`·`.input`·`.btn` 컴포넌트와 focus·reduced-motion
5. `templates/common/base.html`, `templates/common/nav_sidebar.html`, `funding/templates/funding/_layout.html`
6. 관련 view·form·service·테스트 — 데이터와 상태 전이 계약

GBrain은 결정 이유와 과거 맥락에 사용하고 현재 코드와 다르면 코드를 따른다. 공통 계약을 바꿀
때는 위 원천 한 곳에 병합하고 페이지별 CSS 체계를 추가하지 않는다.

## 변경 절차

### 사용자 결과 고정

- 사용자가 화면에서 끝낼 업무를 한 문장으로 정한다.
- 정적 표현 변경과 클릭·제출·HTMX 교체로 상태가 변하는 변경을 구분한다.
- 바뀔 DOM 범위와 보존할 입력·URL·스크롤·열린 상태를 정한다.
- 같은 정보·제목·행동을 앱 셸, 본문, 모달에 반복하지 않는다.

### 기존 원천 재사용

다음 순서에서 해결되는 첫 항목을 사용한다.

1. 같은 업무 역할의 기존 템플릿·partial
2. `static/css/input.css`의 공용 컴포넌트
3. `tailwind.config.js`에 매핑된 의미 토큰
4. Tailwind 기본 유틸리티
5. 이미 설치된 HTMX·Alpine.js 기능
6. 앞 단계로 해결되지 않을 때 기존 디자인 원천에 추가하는 최소 규칙

페이지 전용 `<style>`, 임의 색상값, 같은 역할의 새 클래스, 고정 버튼 너비, 새 UI 의존성을 먼저
만들지 않는다. `static/css/output.css`는 빌드 산출물이므로 직접 수정하지 않는다.

### 정보 구조와 시각 언어

- 메뉴와 화면은 문자 발송 → TM 상담 → TM 진행 내역 → 영업 현황의 업무 순서를 유지한다.
- 관리 기능은 영업 흐름 안에 섞지 않고 기존 관리 진입점을 사용한다.
- 입력, 결과, 현재 상태, 다음 행동을 구분하고 시스템 상태명을 사용자의 업무 말로 바꾼다.
- 표는 비교·정렬·선택이 필요한 목록에 사용하고 내용과 무관한 빈 폭을 강제하지 않는다.
- 바탕·글자·강조·선은 `paper`·`ink`·`accent`·`line`을 우선한다.
- WDS 의미 토큰이 있는 상태에 임의의 `green-*`·`emerald-*`·hex 색을 섞지 않는다.
- 성공·주의·오류처럼 의미가 있을 때만 상태색을 사용한다.
- 장식용 gradient, 중첩 카드, 의미 없는 배지, 고정 크기로 억지 정렬하는 방식을 추가하지 않는다.

### 컴포넌트와 접근성

- 입력·셀렉트·버튼은 기존 `.input`·`.select`·`.btn` 계열을 재사용한다.
- 너비는 부모 레이아웃과 내용이 정하게 하고 컴포넌트에 고정 폭을 넣지 않는다.
- 클릭 동작은 `button` 또는 `a`에 두고 활성 CTA는 저장·화면 변화·이동 중 하나로 끝낸다.
- 입력에는 연결된 label을, 아이콘 버튼에는 접근 가능한 이름을 제공한다.
- 색만으로 선택·상태·오류를 구분하지 않는다.
- 기본·hover·focus-visible·disabled·loading·error·empty 상태를 확인한다.
- 모바일에서 정보를 삭제하지 말고 배치·중첩·여백을 단순화한다.

### HTMX·Alpine 계약

- 사이드바 이동이 `#main-content`를 `outerHTML`로 교체한다는 전제로 화면 수명을 설계한다.
- 화면 지역 요소를 참조하는 리스너는 `#main-content`에 붙여 화면과 함께 제거한다.
- 전역 리스너가 꼭 필요하면 대상 존재를 확인하고 중복 등록·정리 경로를 함께 검증한다.
- 반복 행 동작은 가능한 한 행 또는 가장 작은 업무 단위만 교체한다.
- `hx-target`, `hx-swap`, OOB 범위와 교체 후 보존할 입력·URL·스크롤·열린 상태를 먼저 정한다.
- `templates/common/base.html`의 `htmx:load` Alpine 초기화 경로를 중복 구현하지 않는다.
- 요청의 준비 → 처리 중 → 성공과 준비 → 처리 중 → 실패 경로를 모두 보이게 한다.

## 프로젝트 검증 설정

공통 연결·브라우저·CSS 적용·자원 종료 절차는 `web-automation`이 소유한다.
CEO Loan 고유 설정과 디자인 합격 기준은 다음과 같다.

- Python: 비대화형 SSH에서 `uv`가 PATH에 없으면 확인된 `/home/chaconne/.local/bin/uv` 또는
  저장소의 `.venv/bin/python`을 사용한다.
- 테스트: 기존 pytest 설정과 DB fixture를 사용한다. 설정은 `main.settings.local`, DB 선택은
  `POSTGRES_DB`다. 실제 연결 DB·스키마와 외부 API 테스트 대역을 확인한 후 `live_server`를 실행한다.
  실행할 테스트 진입점은 변경 대상의 현재 테스트에서 확인한다.
- CSS: 원격 저장소에서 `npm run css` 후 검증 설정으로 `collectstatic --noinput`을 실행한다.
  원천은 `static/css/input.css`, Git 추적 산출물은 `static/css/output.css`, 수집 경로는 `STATIC_ROOT`다.
- 정적 제공: `STORAGES['staticfiles']`는 `CompressedManifestStaticFilesStorage`다.
  pytest 제공기가 원본만 찾아 해시 URL이 404가 되면 테스트 fixture의 staticfiles 백엔드만
  `django.contrib.staticfiles.storage.StaticFilesStorage`로 맞추고 다른 저장소 설정은 유지한다.
  운영 manifest 제공 검증은 수집된 해시 파일을 실제 제공하는 구성에서 별도로 확인한다.
- 코드 검사: `uv run python manage.py check --settings=main.settings.local`과 영향 범위의
  `uv run pytest -q <대상>`을 원격 저장소에서 실행한다.
- 디자인 폭: 모바일 390px·480px, 데스크톱 1024px 이상. 위 토큰·컴포넌트·접근성 계약으로 판정한다.
- 화면 수명: HTMX 메뉴로 `#main-content`가 교체된 뒤 Alpine 입력·버튼·모달을 재검증한다.
  합성 데이터의 실제 제출 결과와 제외·보호 대상 보존을 함께 확인한다.

## 완료 조건

- 기존 업무 흐름과 view·HTMX 데이터 계약을 유지한다.
- 실제 토큰과 공용 컴포넌트를 재사용한다.
- 모바일과 데스크톱에서 정보와 주요 행동이 사라지지 않는다.
- 키보드 focus, label, 로딩·오류·빈 상태를 확인한다.
- 중복 partial·페이지 전용 임시 스타일·직접 수정한 빌드 산출물이 없다.
- 실제 화면 검증 결과와 남은 미확인 범위를 구분해 보고한다.
