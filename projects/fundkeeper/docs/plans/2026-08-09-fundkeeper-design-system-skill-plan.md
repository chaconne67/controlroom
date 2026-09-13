# FundKeeper 디자인 시스템 스킬 통합 계획

> 상태: 구현 완료
> 작성일: 2026-08-09

## 1. 목표

- FundKeeper 템플릿과 공통 프런트엔드 코드를 근거로 디자인 시스템 정본을 보강한다.
- 프로젝트 전용 `fundkeeper-design-system` 스킬을 만든다.
- FundKeeper의 UI·UX·디자인 작업이 스킬 description과 일치해 자동 발동하게 한다.
- 실제 화면과 런타임 동작은 이번 작업에서 변경하지 않는다.

## 2. 분석 결과

### 기존 자산

- 상세 문서: `docs/design-system.md`
- CSS 정본: `static/input.css`
- Tailwind 설정: `tailwind.config.js`
- 앱 셸: `templates/base.html`, `templates/head.html`, `templates/navbar.html`, `templates/footer.html`
- 공통 상호작용: `templates/base-js.html`, `static/custom.js`
- 대표 화면군: 포트폴리오·계좌·ETF 표·은퇴 설계·가격 설정·월간 리포트

### 확인한 공통 패턴

- 전체 표면: `bg-slate-50` 위의 흰 카드와 조밀한 데이터 화면
- 주요 위계: NanumSquareNeo, `text-xs`·`text-sm`, `font-neoBold`·`font-neoExBold`
- 주요 컴포넌트: `btn-*`, `form`, `backtest-container`, `darkhead-table`, `modal-*`
- 반응형: `sm=480px`, `lg=1024px`, 모바일 전용 `mb:max-width 480px`
- 상호작용: Django 템플릿 + HTMX 중심, Alpine.js는 작은 로컬 상태, jQuery는 레거시 입력 흐름
- 데이터 계약: `.pct`, `.currency`, `.num`, `.krw-man`과 `data-*` 값이 공통 포맷터에 연결됨
- HTMX 계약: 교체 후 `static/custom.js`가 숫자·정렬·툴팁·로딩 상태를 다시 초기화함

### 현재 문제

- `docs/design-system.md`는 디자인 토큰과 컴포넌트를 잘 정리했지만 실행 순서와 완료 검증이 약하다.
- 기존 템플릿에는 클릭 가능한 `div`, 사라진 전역 focus 표시 등 복제하면 안 되는 레거시 패턴이 섞여 있다.
- UI 요청마다 디자인 문서와 코드의 참조 여부가 담당자 판단에 맡겨져 있다.

## 3. 도메인 분리 결정

- 공용 `kmh-agent-kit`은 수정하지 않는다.
- 프로젝트 전용 스킬의 실파일은 `.claude/skills/fundkeeper-design-system/`에 둔다.
- Codex는 `.codex/skills/fundkeeper-design-system` 심볼릭 링크로 같은 실파일을 사용한다.
- `.claude/skills/`와 `.codex/skills/`는 프로젝트의 로컬 도메인 자산으로 Git에서 제외한다.
- 공유 가능한 상세 디자인 지식은 기존 `docs/design-system.md`에 유지한다.

## 4. 최소 구현 게이트

`최소 구현 게이트: 7단계에서 멈춤 — 프로젝트 로컬 스킬을 검색했지만 .claude/skills·.codex/skills가 없고, 기존 fundkeeper 스킬에는 UI 작업 경로가 없다. 표준 라이브러리·프레임워크·설치 의존성으로 지침을 대신할 수 없으며, 한 줄 참조는 스킬의 발동 조건·작업 순서·검증 계약을 충족하지 못한다.`

- 2단계 검색 근거:
  - 프로젝트 루트의 `.claude/skills`, `.codex/skills`, `.agents/skills` 검색 결과 없음
  - `/home/chaconne/kmh-agent-kit/skills/fundkeeper/SKILL.md`에 UI·UX 디자인 워크플로 없음
  - 기존 `docs/design-system.md`는 지식 정본으로 재사용
- 3~5단계 판단 근거:
  - 산출물은 실행 코드가 아니라 에이전트가 읽는 프로젝트 지침이다.
  - 라이브러리나 프런트엔드 의존성으로 스킬의 발동·작업·검증 계약을 대체할 수 없다.
- 6단계 판단 근거:
  - `skill-creator`가 요구하는 frontmatter, 본문 지침, UI 메타데이터를 한 줄로 충족할 수 없다.

## 5. 최종 경로 잠금

### 현재 최종 경로

1. 사용자가 FundKeeper UI 작업을 요청한다.
2. 에이전트가 프로젝트 일반 지침을 읽는다.
3. 에이전트가 필요한 템플릿과 CSS를 임의로 찾는다.
4. 에이전트가 화면을 수정하고 개별 방식으로 검증한다.

### 변경 후 최종 경로

1. 사용자가 FundKeeper의 UI·UX·디자인·템플릿·스타일 작업을 요청한다.
2. 프로젝트 로컬 스킬의 frontmatter description이 요청 의도와 일치해 `fundkeeper-design-system`을 자동 로드한다.
3. 스킬이 `docs/design-system.md`와 영향 범위의 실제 템플릿·CSS·JS를 읽는다.
4. 스킬이 기존 컴포넌트 재사용, UX·접근성, 반응형, HTMX 계약을 함께 잠근다.
5. 에이전트가 승인 범위 안에서 화면을 수정한다.
6. 에이전트가 Tailwind 빌드와 실제 데스크톱·모바일 화면으로 같은 경로를 검증한다.
7. 시스템 규칙이 달라졌으면 `docs/design-system.md`를 함께 갱신한다.

### 병합 위치

- 프로젝트 로컬 스킬 메타데이터의 요청 분류 단계
- UI 수정 직전 설계 잠금 단계
- UI 수정 직후 실제 화면 검증 단계

### 대체·정리 대상

- 담당자별 임의 탐색을 스킬의 고정된 소스 우선순위로 대체한다.
- 상세 토큰을 스킬에 복제하지 않고 `docs/design-system.md` 한 곳에서 유지한다.
- 새 런타임 코드·CSS 클래스·프런트엔드 의존성은 추가하지 않는다.
- `AGENTS.md`와 `CLAUDE.md`는 수정하지 않는다.

## 6. 구현 범위

| 파일 | 변경 |
|---|---|
| `.claude/skills/fundkeeper-design-system/SKILL.md` | 발동 조건, 정본 순서, 설계 잠금, 구현 규칙, 검증 절차 작성 |
| `.claude/skills/fundkeeper-design-system/agents/openai.yaml` | 스킬 표시 이름·설명·기본 호출문 작성 |
| `.codex/skills/fundkeeper-design-system` | Claude 실파일을 가리키는 프로젝트 로컬 심볼릭 링크 생성 |
| `.gitignore` | 프로젝트 로컬 스킬 경로 제외 |
| `docs/design-system.md` | 템플릿 분석 결과, 레거시 경계, 데이터·HTMX·차트·접근성·검증 규칙 보강 |

## 7. 스킬 내용

- 발동 범위:
  - 화면·컴포넌트·템플릿·Tailwind·CSS·반응형·차트 표현 수정
  - 폼·모달·탭·내비게이션·CTA·로딩·오류·빈 상태 작업
  - UI/UX·접근성·디자인 리뷰
- 발동 방식:
  - `SKILL.md` frontmatter의 description을 유일한 자동 발동 정본으로 사용
  - FundKeeper·Coconut과 UI 작업 종류·대상 파일·상태 패턴을 description에 함께 명시
  - `$fundkeeper-design-system` 명시 호출도 지원
- 정본 우선순위:
  1. 영향 범위의 실제 템플릿과 공통 파셜
  2. `static/input.css`, `tailwind.config.js`
  3. `templates/base-js.html`, `static/custom.js`
  4. `docs/design-system.md`
- 구현 우선순위:
  1. 기존 공통 파셜
  2. 기존 공통 클래스
  3. Tailwind 기본 유틸리티
  4. 설치된 프런트엔드 기능
  5. 필요한 최소 신규 규칙
- 필수 보호 규칙:
  - 레거시 템플릿의 접근성 결함을 새 화면에 복제하지 않는다.
  - `static/output.css`를 직접 수정하지 않는다.
  - 데이터 포맷 클래스의 JS 계약과 HTMX 교체 후 초기화를 보존한다.
  - 모바일은 정보 삭제보다 레이아웃 단순화를 우선한다.
  - 실제 화면을 보지 않고 디자인 완료로 판정하지 않는다.

## 8. 검증

1. `skill-creator/scripts/quick_validate.py`로 스킬 구조를 검사한다.
2. Claude 실파일과 Codex 심볼릭 링크가 같은 `SKILL.md`로 해석되는지 확인한다.
3. frontmatter description에 FundKeeper UI 작업의 전체 발동 범위가 들어갔는지 검사한다.
4. 대표 템플릿 한 개를 대상으로 스킬 체크리스트를 건식 실행한다.
5. Markdown 링크와 참조 경로가 실제로 존재하는지 검사한다.
6. Git diff에서 실제 UI·런타임 코드가 바뀌지 않았는지 확인한다.

## 9. 리뷰·문서화·커밋

- 실행 동작을 바꾸지 않으므로 `code-review-loop`는 실행하지 않는다.
- 스킬 지침은 `skill-writing-guide`와 `prompt-guide` 기준으로 자체 검토한다.
- 구현 완료 후 FundKeeper 저장소의 추적 파일만 한국어 커밋으로 남긴다.
- 프로젝트 로컬 스킬 실파일과 심볼릭 링크는 도메인 분리 방침에 따라 커밋하지 않는다.
- 재사용 가능한 새 지식이 확정되면 GBrain의 FundKeeper 사적 공간에 기록한다.

## 10. 제외 범위

- 실제 화면 스타일 변경
- 기존 템플릿의 접근성 결함 일괄 수정
- 디자인 토큰 CSS 변수화
- Storybook·컴포넌트 갤러리 추가
- 새 프런트엔드 의존성 추가
- 배포
- `AGENTS.md`, `CLAUDE.md` 수정

## 11. 완료 결과

- 프로젝트 로컬 `fundkeeper-design-system` 스킬 생성 완료
- Claude 실파일과 Codex 심볼릭 링크 연결 완료
- frontmatter description에 FundKeeper UI 작업 범위 반영 완료
- `docs/design-system.md`에 화면군, 레거시 경계, 데이터 포맷, HTMX 재초기화, 차트, 접근성, 실제 화면 검증 규칙 반영 완료
- `quick_validate.py`: `Skill is valid!`
- 참조 경로 존재 확인 완료
- ETF 대표 화면 건식 적용에서 공통 셸, 주 버튼, HTMX 모달, 반응형 표 계약 확인 완료
- `AGENTS.md`, `CLAUDE.md` 무변경 확인 완료
- 실제 UI·CSS·JS 런타임 파일 무변경 확인 완료
