---
name: fundkeeper-design-system
description: Use when designing, implementing, reviewing, or validating FundKeeper/Coconut UI, templates, Tailwind CSS, HTMX interactions, responsive behavior, charts, forms, or accessibility.
---

# FundKeeper 디자인 시스템

FundKeeper의 기존 시각 언어와 화면 계약을 보존하면서 UI를 변경한다. 상세 토큰과 컴포넌트 규칙은 원격 저장소의 `docs/design-system.md`가 정본이다.

## 정본 확인

1. SSH로 `/home/chaconne/fundkeeper`에서 작업한다.
2. `docs/design-system.md`를 끝까지 읽는다.
3. 변경 대상 템플릿과 가장 가까운 기존 화면을 읽는다.
4. 영향 범위에 따라 다음 공통 소스를 확인한다.
   - 시각 컴포넌트: `static/input.css`, `tailwind.config.js`
   - 앱 셸: `templates/base.html`, `templates/head.html`, `templates/navbar.html`, `templates/footer.html`
   - 상호작용: `templates/base-js.html`, `static/custom.js`
   - 차트: `templates/chart/`, `simulation/charts.py`
5. 문서와 실행 코드가 다르면 실행 코드를 따른다. 시스템 규칙이 달라지면 같은 작업에서 디자인 문서를 갱신한다.

## 작업 경로

1. 화면에서 사용자가 완료할 행동을 하나로 정한다.
2. 데스크톱·모바일·로딩·오류·빈 상태에서 그 행동이 어떻게 보이는지 정한다.
3. 아래 재사용 순서로 구현 위치를 고른다.
4. 컴포넌트·데이터 포맷·HTMX·접근성 계약을 확인한다.
5. 승인 범위 안에서 최소 변경만 구현한다.
6. Tailwind 빌드와 실제 화면으로 검증한다.

## 재사용 순서

1. 같은 역할의 기존 공통 파셜
2. `static/input.css`의 기존 컴포넌트 클래스
3. Tailwind 기본 유틸리티
4. 이미 설치된 HTMX·Alpine.js·Flowbite 기능
5. 앞 단계로 해결되지 않을 때 필요한 최소 신규 규칙

`static/output.css`를 직접 수정하지 않는다. 한 화면의 장식만을 위해 공통 클래스나 새 의존성을 만들지 않는다.

## 프로젝트 계약

### 시각과 반응형

- 앱 화면은 `bg-slate-50` 위의 흰 카드와 조밀한 데이터 레이아웃을 기본으로 삼는다.
- NanumSquareNeo 계열과 기존 `font-neo*` 클래스를 유지한다.
- 주 액션은 기존 `btn-*` 계열을 사용한다.
- `pension`, `us`, Coconut yellow, Kakao 색은 해당 도메인 의미가 있을 때만 사용한다.
- `sm`은 min-width 480px이고 `mb`는 max-width 480px인 프로젝트 고유 breakpoint다.
- 모바일에서는 정보를 삭제하지 말고 카드 중첩·가로 배치·여백을 단순화한다.
- 조밀한 표는 가로 스크롤이나 기존 모바일 대체 레이아웃을 사용한다.

### 데이터 표현

- 퍼센트는 `.pct`와 `data-value` 계약을 유지한다.
- 통화는 `.currency`, `data-value`, `data-currency` 계약을 유지한다.
- `.num`, `.krw-man`을 단순 스타일 클래스로 사용하지 않는다.
- 일반 손익은 상승 녹색·하락 빨강을 유지한다.
- 국내 캔들 차트는 상승 빨강·하락 파랑 계약을 유지한다.
- 차트 계열 색은 `simulation/charts.py`나 해당 서비스가 만든 데이터를 우선한다.

### HTMX와 접근성

- `hx-target`과 `hx-swap`의 실제 교체 범위를 먼저 확인한다.
- 숫자 포맷·정렬·툴팁·로딩 상태의 `htmx:afterSwap` 재초기화 경로를 보존한다.
- 클릭 동작에는 `button` 또는 `a`를 사용하고 클릭 가능한 `div`를 새 UI에 복제하지 않는다.
- 새로 만들거나 수정한 컨트롤에 보이는 `:focus-visible` 상태를 제공한다.
- 입력에는 연결된 label을, 아이콘 버튼에는 접근 가능한 이름을 제공한다.
- 색만으로 손익·선택·오류를 구분하지 않는다.
- 오류와 빈 상태에는 사용자가 다음에 할 행동을 적는다.

## 검증

1. 템플릿이나 CSS를 수정했으면 `npx tailwindcss -i ./static/input.css -o ./static/output.css`를 실행한다.
2. 동작을 수정했으면 안전성을 확인한 관련 Django 검사나 집중 테스트를 실행한다.
3. 실제 화면에서 모바일 390px·480px와 데스크톱 1024px 이상을 확인한다.
4. 기본·hover·focus·disabled와 로딩·오류·빈 상태를 확인한다.
5. HTMX 교체 전후의 데이터 포맷과 상호작용을 확인한다.
6. 실제 화면을 열 수 없으면 디자인 검증을 통과했다고 보고하지 않는다.
7. 배포가 범위에 포함되면 운영 화면에서 같은 항목을 다시 확인한다.

## 완료 조건

- 기존 시각 위계와 도메인 색 의미가 유지된다.
- 모바일과 데스크톱에서 정보가 손실되지 않는다.
- 데이터 포맷과 HTMX 재초기화 계약이 유지된다.
- 건드린 범위의 키보드·focus·label 요구사항을 만족한다.
- 중복 컴포넌트·임시 스타일·직접 수정한 빌드 산출물이 없다.
- 실제 화면 검증 결과와 남은 미확인 범위를 구분해 보고한다.
