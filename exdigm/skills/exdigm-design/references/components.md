# Component Patterns

## 원천

- 공통 component CSS: `/home/chaconne/exdigm-debug/static/css/input.css`
- 구현 전에는 실제 class 정의와 현재 template 사용처를 확인한다.

## 공통 구조

| 구성요소 | 기본 규칙 |
|---|---|
| Sidebar | logo `px-6 py-6`, nav `px-4 py-6 space-y-1`, active는 `ink2` 배경과 3×18 흰 dot |
| Header | 72px, `bg-surface border-b border-hair px-8`; breadcrumb + H1, 우측 icon/button + user area |
| Standard card | `bg-surface rounded-card shadow-card p-6`; 정적 card에는 hover 없음 |
| Dark card | 한 화면 하나, `bg-ink text-white rounded-card shadow-lift p-6` |
| Stat | 숫자 `text-4xl font-bold tnum`, 설명 `text-sm text-muted` |
| Avatar | 일반 44px, header user 40px `bg-ink2`, stack은 28px white border / -6px overlap |

## 상태와 작은 요소

- 상태 dot은 6px 원이며 success/warning/info/danger의 의미를 직접 쓴다.
- `.progress`는 4px pill. default `ink3`; success/info/muted/dark variant만 사용한다.
- `.chip`은 filter toggle, `.badge`는 업무 상태, `.tag`는 skill/keyword, `.meta-pill`은 헤더 meta다. 같은 모양을 다른 업무 의미에 재사용하지 않는다.
- `.eyebrow-ko`를 한글 섹션 라벨에 우선한다.

## 반복 정보와 표

- 일반 반복 행은 box가 아니라 간격·divider·타이포로 구분한다.
- 표가 의미상 필요할 때만 12-column grid 또는 table을 쓴다.
- `.ref-table`은 UPPERCASE faint header, hair divider, canvas hover, primary column `text-sm font-bold text-ink`, 수치 `.tnum` right-align이다.
- 로고는 워드마크와 심볼의 비율이 다르므로 실제 업로드 로고를 정사각 타일에 강제하지 않는다. `.client-logo-strip`의 높이 정규화와 `object-fit: contain`을 사용하고, 로고가 없을 때만 `.client-logo-mono` fallback을 쓴다.

## Calendar·진행·칸반

- calendar card는 `overflow-hidden`; today는 셀 전체가 아니라 숫자만 ink 원형 chip으로 표시한다.
- Application stage progress는 `passed/current/pending`을 dot·line으로 구분한다. 화면 card에는 발굴을 제외한 6단계를 표시한다.
- 칸반 column은 `.col-container-{searching,screening,closed}`, count는 `.col-pill-*` variant를 쓴다. Django 동적 class는 safelist 존재를 확인한다.

## Workspace modal

- 원천: `/home/chaconne/exdigm-debug/assets/ui-sample/application-workspace-modal.html`과 `.workspace-modal` CSS namespace.
- 일반 card 16px와 달리 modal 내부 독립 form·alert·선택 카드만 8px을 쓴다. 반복 항목을 box로 감싸는 용도가 아니다.
- `.workspace-stage-tab`, `.field`, `.btn-primary`, `.btn-ghost`, `.btn-danger`, `.send-icon`의 정의를 재사용한다.
- 1024px 이상 사전 미팅은 우측 300px column + divider, 760px 이하는 단일 column과 wrap을 확인한다.

## 구현 전 확인

- 필요한 component가 있으면 새 CSS를 쓰기 전에 `input.css`에서 같은 책임의 class를 검색한다.
- 없으면 Tailwind token 조합으로 표현한다. 페이지 전용 CSS class와 style block을 추가하지 않는다.
