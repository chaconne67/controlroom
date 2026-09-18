# 벤처 스킬 자료 보강 설계 (phase2 + phase3)

작성일: 2026-06-13

## 배경과 문제

- 회사가 제공하는 원본 자료의 양·질은 편차가 크고, 자료가 부실한 회사가 있을 수 있다.
- 벤처인증 합격의 핵심 점수는 ISO·특허·기술개발 같은 객관 요소가 좌우하지만, 신청서 문구의 품질도 중요하다.
- 문구 품질은 작성 시 동원할 수 있는 자료의 풍부함에서 나온다.
- 현재 `distillation.md`의 "확인 필요"에는 시장규모·매출 부족이 남아, 후속 작성(특히 `target_market`)이 정량 근거 없이 막연한 추정에 머문다.

## 목표

- 입력단(phase2 추출, phase3 정제)을 강화해 후속 작성 phase가 더 풍부하고 출처 있는 자료로 문구를 작성하게 한다.
- 시장규모·성장률 같은 정량 수치가 출처·근거와 함께 distillation에 들어가게 한다.

## 결정 사항

1. **적용 위치**: phase2는 로컬 원본파일 텍스트 추출만 유지(강화 롤백). 홈페이지 깊은 조사는 phase3(distillation) 웹조사로 보강.
2. **정량 수치 산출**: 출처 통계 우선 → 없으면 인접·상위 시장 통계에서 산출 근거(로직)를 명기해 추론까지 허용. 매출·계약·납품 같은 실적성 수치는 창작 금지.
3. **홈페이지 조사 방식**: JS로 주입되는 네비게이션 때문에 정적 fetch/WebFetch는 하위 페이지 URL을 발견하지 못한다(onearch.co.kr에서 `#none`만 노출). Playwright 렌더링 스크래퍼(`scripts/scrape_site.js`)로 메인+하위 페이지를 추출하고, phase3가 이를 호출한다.
4. **산출 관점**: 시장규모·성장률·고객 반응 등은 사업계획서 관점에서 긍정적·우호적으로 산출한다(낙관적 시나리오 허용, 단 실적성 수치 창작 금지).

## 설계

### 1. phase2 — 변경 없음 (로컬 원본 추출만)

phase2는 `src/raw/`의 로컬 원본파일 텍스트 추출과 홈페이지 메인 페이지 정적 추출(`src/homepage.md`)만 유지한다. 초기 검토에서 phase2에 홈페이지 하위 페이지 정적 수집을 넣었으나, (1) phase2 역할은 원본 추출로 한정하고, (2) 정적 수집은 JS 네비게이션 사이트(onearch.co.kr)에서 하위 링크를 발견하지 못해 효과가 없어 롤백했다. 홈페이지 깊은 조사는 phase3로 이관한다.

### 1-b. phase3 — 홈페이지 렌더링 스크래퍼 (`scripts/scrape_site.js`)

진단 결과: onearch.co.kr은 네비게이션이 JS로 주입되어 정적 fetch/WebFetch가 `#none`만 본다. Playwright로 렌더링하면 `/heritage.html`, `/press.html`이 DOM에 드러나고 본문도 추출된다(정적 1,392자 → 렌더링 4,984자).

신규 `scripts/scrape_site.js`:
- `web.js`와 동일한 Playwright 스택(playwright-core + 시스템 Chrome) 사용.
- `--url`로 받은 페이지를 렌더링 후 메인 본문(innerText) + 같은 도메인 내부 링크 수집.
- 키워드 우선순위(`사업`, `제품`, `기술`, `heritage`, `about`, `회사`, `소개`, `연혁`, `press` 등) 상위 N개(기본 12) 하위 페이지를 렌더링·추출.
- `--out`으로 Markdown 저장(메타에 `subpage_count`, `## 하위 페이지` 섹션). 실패한 하위 페이지는 건너뛰고 메인은 보존.
- 비범위(YAGNI): 무한 크롤링, 외부 도메인, 페이지네이션. 1-depth + 키워드 우선순위.

phase3 SKILL.md 변경:
- 사전 준비에 `node scripts/scrape_site.js --url <homepage_url> --out companies/<회사>/src/homepage_rendered.md` 실행 단계 추가(실패 시 정적 `src/homepage.md`로 진행).
- 원본자료 정제 sub-agent 입력에 `src/homepage_rendered.md` 추가(있으면 우선 활용).

### 2. phase3 — 웹조사 정량화 + 수치 산출 규칙

phase3 SKILL.md 변경:
- 웹조사 sub-agent **조사 관점에 정량 항목을 명시**: 시장규모, 성장률(CAGR), 정책 예산·통계, 인접·상위 시장 규모, 고객 반응·수요 지표.
- 웹조사 sub-agent **반환 형식을 `수치 + 출처 URL + 출처명 + 연도` 필수**로 강화.
- 메인 에이전트가 `distillation.md`의 **"시장환경"에 정량 수치(출처 병기)를 적극 수록**하도록 지시.
- **수치 산출 규칙(신규)**을 phase3 작업 내용에 추가:
  1. 출처 통계 우선.
  2. 직접 통계가 없으면 인접·상위 시장 통계에서 산출 근거(로직)를 명기해 추론.
  3. 시장규모·성장률·고객 반응은 사업계획서 관점에서 긍정적·우호적으로 산출.
  4. 매출·계약·납품 등 회사 실적성 수치는 창작 금지.
- **"확인 필요" 운영 변경**: 시장규모를 공란으로 남기지 말고, 추론치 + 산출 근거와 함께 distillation에 제시한다. 정말 산출 불가한 것만 확인 필요로 분류한다.

`writing-common-rules.md`: 이미 "인접시장 추론 허용", "시장 추정 수치 명시", "긍정적 사업계획서 관점"이 반영되어 있어 추가 변경은 최소. 필요 시 "긍정적·우호적 산출" 표현만 한 줄 정합.

### 3. 후속 정합 (자동 연계, 별도 변경 없음)

- phase4 `values.md`의 시장 관련 값과 phase6 `target_market` 본문이 distillation의 출처 기반 수치를 인용하게 된다.
- 앞서 개정한 `writing-common-rules.md`의 수치 규칙과 맞물려, target_market의 시장규모·매출 추정이 출처·근거 있는 수치로 격상된다.

## 변경 대상 파일

- `scripts/scrape_site.js` — (신규) Playwright 렌더링 홈페이지 스크래퍼.
- `skills/venture-phase3-distillation/SKILL.md` — 홈페이지 렌더링 스크래핑 단계, 정제 sub-agent 입력에 `homepage_rendered.md` 추가, 웹조사 정량 항목·반환 형식·수치 산출 규칙·확인 필요 운영.
- `skills/venture/references/writing-common-rules.md` — 긍정적 산출 표현 정합.
- `scripts/extract_sources_to_src.py`, `skills/venture-phase2-raw-data/SKILL.md` — 변경 없음(초기 강화 후 롤백).

## 검증 방법

- 전통한옥금송재 자료로 phase2 재실행 → `src/homepage.md`에 하위 페이지 섹션이 추가되는지 확인.
- phase3 재실행 → `distillation.md` "시장환경"에 출처 있는 정량 수치가 들어가고, "확인 필요"에서 시장규모 공란이 사라지는지 확인.
- target_market 재작성 테스트 → 시장규모·성장률이 출처/산출 근거와 함께 들어가는지 확인.

## 비범위 (YAGNI)

- 홈페이지 무한 크롤링, 외부 도메인 수집, JS 강제 렌더링.
- 신규 phase 신설(기존 phase2/phase3 강화로 해결).
- 자동 통계 API 연동(웹조사 sub-agent의 검색으로 충분).
