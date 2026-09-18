---
name: venture-phase9-portal-ready
description: values.md와 texts/*.md를 기준으로 포털 입력 전 준비 상태를 확인할 때 사용한다.
---

# 실행

## 사전 준비

- 아래 `companies/<회사>`의 `<회사>`는 `V<YYMMDD>-<한글회사명>` 형식의 회사 폴더명이다. 사용자가 한글회사명만 말하면 `companies/`에서 `V*-<한글회사명>` 폴더를 찾아 쓰고, 날짜가 다른 폴더가 둘 이상이면 임의로 고르지 말고 어느 것을 쓸지 사용자에게 확인한다.
- 회사 작업공간: `companies/<회사>`
- 입력 파일 존재 여부를 확인한다.
  - `companies/<회사>/README.md`
  - `companies/<회사>/values.md`
  - `companies/<회사>/texts/problem_background.md`
  - `companies/<회사>/texts/solution.md`
  - `companies/<회사>/texts/tech_progress.md`
  - `companies/<회사>/texts/tech_plan.md`
  - `companies/<회사>/texts/target_market.md`
  - `companies/<회사>/texts/competition.md`
  - `companies/<회사>/texts/market_progress.md`
  - `companies/<회사>/texts/market_plan.md`
  - `companies/<회사>/texts/funding_plan.md`
  - `companies/<회사>/texts/entrepreneurship.md`
  - `companies/<회사>/texts/business_plan_summary.md`
- Markdown 파일 읽기와 쓰기는 항상 UTF-8을 명시한다.
- PowerShell에서 한글 파일을 확인할 때는 먼저 `[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)`를 실행한 뒤 `Get-Content -LiteralPath <path> -Encoding UTF8`로 읽는다.

## 입력 내용

- `README.md`
  - 회사명
  - 포털 계정
  - 자료 위치
  - 현재 진행 상태
- `values.md`
  - 포털 입력에 필요한 짧은 값
  - 선택값
  - 표 데이터
  - 신청기술 제품/서비스명
- `texts/*.md`
  - 문제해결 본문 4개
  - 시장 본문 4개
  - 스타트업 본문 2개
  - 사업계획서 요약

## 작업 내용

- 포털 입력 스킬이 `values.md`와 `texts/*.md`를 읽어 입력을 진행할 수 있는지 확인한다.
- `README.md`의 포털 계정과 자료 위치가 실제 파일 경로와 연결되는지 확인한다.
- `values.md`의 포털 입력 후보 항목이 `value`, `status`, `source`, `notes` 형식으로 정리되어 있는지 확인한다.
- `texts/*.md`의 각 파일이 `field_id`, `status`, `char_count`, `source`, `notes` 프론트매터와 본문을 갖췄는지 확인한다.
- 자유 서술형 본문의 글자수는 `char_count` 자기보고가 아니라 `uv run python scripts/check_charcount.py <회사명>`으로 실측 검증한다. 스크립트가 전부 OK가 아니면(900자 미만·1000자 이상·선언값 불일치) 포털 입력 전에 해당 본문을 보강·압축하고 `char_count`를 실측값으로 맞춘다.
- `business_plan_summary.md`는 양식 빈칸 작성 산출물이므로 스크립트가 글자수 범위 검사에서 자동 제외한다.
- `needs_confirmation`, `candidate`, `portal_existing`, `not_applicable` 상태는 의미가 섞이지 않았는지 확인한다.
- 포털 입력에 필요한 값이나 본문이 비어 있으면 부족 항목으로 분류해 보고한다.
- 글자수 실측이 전부 OK가 된 뒤 장문 모음 PDF를 조립한다: `uv run python scripts/build_longtext_pdf.py <회사폴더명>`
  - 사업계획서 요약과 장문 본문 10개를 포털 제출 순서대로 한 파일에 모아, 포털 입력 전에 전체 흐름을 사람이 한 번에 검토하기 위한 산출물이다.
  - 출력 위치는 `companies/<회사>/<회사명>_사업계획서_장문통합.pdf`이며, 스크립트가 표지·항목 번호·서식을 생성한다.
  - 표지 날짜를 지정하려면 `--date 2026.07`처럼 전달한다. 미지정 시 이번 달로 표기된다.
  - 본문을 수정했으면 PDF를 다시 조립해 최신 본문과 일치시킨다.
- 확인 필요 값이 있더라도 `status`와 `notes`가 모두 채워져 있으면 구조 오류로 보지 않는다.
- `company_name`은 사업자등록증 회사명과 같은 기준으로 작성되어 있는지 확인한다.
- 대표자가 2인 이상이면 `representative_table`에 모든 대표자가 기록되어 있는지 확인한다.
- `three_year_employee_count`는 고용보험 사업장자격취득자명부의 각 연도 말일 기준 자료와 연결되어 있는지 확인한다.
- `corporate_registry_extract`는 법인등기부등본 적용 여부, 2주 이내 발급 여부, 말소사항 포함 여부가 구분되어 있는지 확인한다.
- `required_submission_documents`는 혁신성장유형 필수 제출자료의 제출 조건, 자료 상태, 확인 필요 사유가 구분되어 있는지 확인한다.
- `attachment_source_paths`는 실제 업로드할 파일만 문서 키, 포털 코드, 파일 경로, 상태로 정리되어 있는지 확인한다.

## 출력 내용

- 장문 모음 PDF 외에는 새 산출물 파일을 만들지 않는다.
- `companies/<회사>/<회사명>_사업계획서_장문통합.pdf`를 조립한다.
- `README.md`의 자료 위치에 누락된 기존 산출물 경로가 있으면 추가하고, `longtext_pdf: <회사명>_사업계획서_장문통합.pdf`를 기록한다.
- 포털 입력에 필요한 파일과 필드 구조가 연결되면 `README.md`의 진행 상태를 `venture-phase10-portal-save`로 바꾼다.

## 사후 처리

- `README.md`의 자료 위치에 아래 경로가 있는지 확인한다.
  - `values: values.md`
  - `problem_background: texts/problem_background.md`
  - `solution: texts/solution.md`
  - `tech_progress: texts/tech_progress.md`
  - `tech_plan: texts/tech_plan.md`
  - `target_market: texts/target_market.md`
  - `competition: texts/competition.md`
  - `market_progress: texts/market_progress.md`
  - `market_plan: texts/market_plan.md`
  - `funding_plan: texts/funding_plan.md`
  - `entrepreneurship: texts/entrepreneurship.md`
  - `business_plan_summary: texts/business_plan_summary.md`
- 장문 모음 PDF가 생성되었는지, 페이지 수와 섹션 11개(요약 1 + 본문 10)가 모두 들어갔는지 확인한다.
- 한글 깨짐이 없는지 확인한다. PDF 본문에 대체문자가 있으면 폰트 문제이므로 재조립한다.
- 포털 입력에 값이 부족한 항목은 파일을 임의로 보완하지 않고 주인님에게 보고한다.

## 완료 조건

- `companies/<회사>/README.md`가 있음
- `companies/<회사>/values.md`가 있음
- 필요한 `companies/<회사>/texts/*.md` 파일이 모두 있음
- `README.md`의 자료 위치가 실제 파일 경로와 연결됨
- `values.md`의 포털 입력 후보 항목에 `value`, `status`, `source`, `notes`가 있음
- 확인 필요 값은 `needs_confirmation`, `candidate`, `portal_existing`, `not_applicable` 중 적절한 상태와 사유가 기록되어 있음
- 회사명, 대표자 수, 피보험자 수, 법인등기부등본 조건, 필수 제출자료 상태가 구조적으로 확인 가능함
- 자유 서술형 본문 파일이 실측(`scripts/check_charcount.py`) 기준 900자 이상 1000자 미만이고 `char_count`가 실측값과 일치함
- `business_plan_summary.md`에 밑줄 빈칸이 남아 있지 않음
- `companies/<회사>/<회사명>_사업계획서_장문통합.pdf`가 있고 섹션 11개(요약 1 + 본문 10)를 포함함
- `README.md`의 자료 위치에 `longtext_pdf` 경로가 있음
- `README.md`의 `current_phase`가 `venture-phase10-portal-save`임
- 한글 깨짐 흔적이 없음
