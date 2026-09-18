# Foundations

## 원천

- 토큰과 공통 CSS: `/home/chaconne/exdigm-debug/tailwind.config.js`, `/home/chaconne/exdigm-debug/static/css/input.css`
- 앱 셸·단일 스크롤: `/home/chaconne/exdigm-debug/templates/common/base.html`
- 불일치하면 코드가 기준이다.

## 폰트와 타이포그래피

- 전역 sans: `"Pretendard Variable", Pretendard, -apple-system, BlinkMacSystemFont, system-ui, sans-serif`
- 숫자 카운터·금액·통계: `.tnum`
- Page title: `text-3xl font-bold tracking-tight`
- 주요 section: `text-2xl font-bold`
- card title: `text-base font-bold`
- 본문·버튼: `text-sm`, 보조 정보: `text-xs`
- 영문 섹션 라벨: `.eyebrow`, 한글 라벨: `.eyebrow-ko`
- 임의 `text-[Npx]`, 다른 웹폰트, 읽기 전용 `<pre>`는 사용하지 않는다. 줄바꿈 보존 출력은 `font-sans whitespace-pre-wrap` 일반 요소를 쓴다.

## 토큰

| 역할 | Tailwind token | 값 | 사용 |
|---|---|---|---|
| canvas | `bg-canvas` | `#F8FAFC` | 페이지 배경·행 hover |
| surface | `bg-surface` | `#FFFFFF` | 카드·셀·header |
| ink | `bg-ink` / `text-ink` | `#0F172A` | sidebar·단 하나의 다크 KPI·강조 글자 |
| ink2 | `bg-ink2` | `#1E293B` | sidebar active·primary hover·avatar |
| ink3 | `bg-ink3` | `#334155` | primary button·active toggle·보조 강조 |
| muted | `text-muted` | `#475569` | 본문 보조·ghost button |
| faint | `text-faint` | `#64748B` | meta·placeholder·eyebrow·secondary icon |
| hair | `border-hair` | `#d8dee6` | 카드 외곽선 |
| line | `border-line` / `bg-line` | `#F1F5F9` | 내부 divider·옅은 tint |
| semantic | success/warning/info/danger | 코드 원천 | 상태 의미 전용 |

- primary button은 `ink3`, hover는 `ink2`다. `ink`를 버튼·토글에 쓰지 않는다.
- 의미 없는 brand gradient, 상태색 장식, 카드·컨테이너 왼쪽 색 stripe를 만들지 않는다.
- 카드 하나의 시선 앵커가 필요할 때만 `bg-ink` 다크 카드를 한 개 사용한다.

## 간격·반경·그림자

- 4px base, 8px grid. 카드 `p-6`, 메인 `px-8 py-8`, grid `gap-6`, sidebar nav `px-4 py-6`.
- 일반 card: `rounded-card`(16px). 작은 내부 독립 요소와 sidebar link만 `rounded-lg`(8px). `rounded-md`는 쓰지 않는다.
- 일반 card: `shadow-card`; 다크 강조: `shadow-lift`; FAB: `shadow-fab`; 떠 있는 검색: `shadow-searchbar`.
- hover lift는 클릭 가능한 `a` 또는 `button`의 `rounded-card`에만 적용한다. `transform` 대신 `position: relative`와 `top`을 쓴다.

## 폼 컨트롤

- 일반 `input`·`select`·`textarea`: `.form-control`. 최소 높이 44px, 반경 8px, `hair` 테두리, `ink3` 2px focus ring을 공통 적용한다.
- 목록 필터: `.form-control--compact`. 높이 40px만 허용하며 나머지 시각 상태는 `.form-control`과 같다.
- 검색 아이콘 여백: `.form-control--search`를 `.form-control`과 함께 쓴다.
- 입력과 버튼이 한 경계를 공유하는 복합 컨트롤: 바깥 `.form-control-shell`, 실제 입력 `.form-control__input`.
- checkbox·radio: `.form-choice`. file input: `.form-file`.
- 숨김 필드는 시각 토큰 대상에서 제외한다. 개별 템플릿에 border·radius·focus 유틸리티 묶음을 다시 만들지 않는다.

## 레이아웃과 스크롤

- 앱 셸 고정값: sidebar 260px, header 72px, main max-width 1280px.
- 표준 grid: `grid grid-cols-12 gap-6`; 3-up `col-span-4`, main/side `8 + 4`.
- 데스크톱 세로 스크롤은 `#main-content` 하나만 소유한다. 이 요소는 `overflow-y-auto`와 `contain: paint`를 함께 가진다.
- 모달·미리보기·로그처럼 명시적으로 높이를 제한한 영역만 독립 `overflow-y-auto`를 쓴다.
- 페이지·section의 두 번째 세로 스크롤, 공통 padding만으로 생기는 큰 하단 빈 화면을 만들지 않는다.

## 모션·focus·아이콘

- 색 변화 150ms, card lift 200ms, reduced-motion을 존중한다. 과시적 animation을 만들지 않는다.
- focus-visible은 `ink3` outline 규칙을 따른다. 입력 요소는 원천 CSS의 focus 규칙을 확인한다.
- Lucide inline SVG를 사용한다. inline control 14px, card deco 16px, nav/header 18px, FAB 22px.
- `/home/chaconne/exdigm-debug/templates/common/nav_sidebar.html`의 sidebar 아이콘 세트는 교체하지 않는다.
