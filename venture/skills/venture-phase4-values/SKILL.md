---
name: venture-phase4-values
description: 정제 자료를 바탕으로 포털 입력과 후속 본문 작성에 필요한 짧은 값, 선택값, 표 데이터, 신청기술명을 values.md에 정리할 때 사용한다.
---

# 실행

## 사전 준비

- 아래 `companies/<회사>`의 `<회사>`는 `V<YYMMDD>-<한글회사명>` 형식의 회사 폴더명이다. 사용자가 한글회사명만 말하면 `companies/`에서 `V*-<한글회사명>` 폴더를 찾아 쓰고, 날짜가 다른 폴더가 둘 이상이면 임의로 고르지 말고 어느 것을 쓸지 사용자에게 확인한다.
- `companies/<회사>/README.md`에서 회사명, 홈페이지 URL, 추출 문서 목록, `distillation.md` 위치를 확인한다.
- Markdown 파일 읽기와 쓰기는 항상 UTF-8을 명시한다.
- PowerShell에서 한글 파일을 확인할 때는 먼저 `[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)`를 실행한 뒤 `Get-Content -LiteralPath <path> -Encoding UTF8`로 읽는다.

## 작문 규칙 로드

이 phase는 시장 규모·성장률·목표 수치를 만들어 후속 phase가 그대로 쓰는 단계다.
작업을 시작하기 전에 프로젝트 루트 기준 아래 경로를 Read로 읽고 `## 역할과 입장`을 적용한다.

```
skills/venture/references/writing-rules.md
```

- 읽지 않은 상태로 정제·수치 산출을 시작하지 않는다. 이미 읽었다고 판단해 건너뛰지 않는다.
- sub-agent를 호출할 때는 `## 역할과 입장` 전문을 프롬프트에 그대로 포함한다.
- 수치는 선택 가능한 범위에서 가장 큰 값을 취하고, 근거가 부족해도 비우지 말고 산출 로직과 함께 적극적 추정치를 제시한다.

## 입력 내용

- 입력 파일:
  - `companies/<회사>/README.md`
  - `companies/<회사>/distillation.md`
  - 기존 `companies/<회사>/values.md`가 있으면 현재 값을 보존·갱신할 기준으로 읽는다.
  - `README.md`의 `추출 문서` 표에 기록된 `src/*.md`
- 포털 이력 확인:
  - 신규기업/재확인기업 여부는 포털의 `My 벤처 > My 벤처현황 > 벤처기업확인이력`에서 확인한다.
  - 포털에서 확인한 이력 값은 `values.md`의 `venture_confirmation_history`, `company_application_status`에 기록한다.

## 작업 내용

- 긴 사업계획서 본문을 작성하지 않고, 짧은 입력값, 선택값, 표 데이터만 정한다.
- 확인된 값은 `value`, `status`, `source`, `notes` 형식으로 정리한다.
- 사업자등록증에 기재된 회사명과 `company_name`이 일치하는지 확인하고, `㈜`, `주식회사`, 띄어쓰기 차이는 `notes`에 남긴다.
- 대표자가 2인 이상으로 확인되면 `representative_table`에 모든 대표자 후보를 정리한다.
- 고용보험 사업장자격취득자명부 자료가 있으면 최근 3개년의 각 연도 말일 기준 피보험자 수를 `three_year_employee_count`에 정리한다.
- 법인사업자인 경우 법인등기부등본 자료의 발급일과 말소사항 포함 여부를 `corporate_registry_extract`에 정리한다.
- 혁신성장유형 제출서류 안내 기준으로 필수 제출자료 상태를 `required_submission_documents`에 정리한다.
- 실제 포털 첨부 업로드에 사용할 파일 경로가 확인되면 `attachment_source_paths`에 문서 키, 포털 코드, 파일 경로, 상태를 정리한다.
- 회사 제공 특허·인증·자격·기술자료에서 확인되는 항목은 해당 표 데이터로 정리한다.
- 외부 웹조사 정보는 회사 실적값으로 쓰지 않고 시장·경쟁·기술 환경 판단에만 사용한다.
- 포털에 이미 저장되어 있고 원자료에서 확인되지 않는 연락처·주소·담당자 값은 `portal_existing` 또는 `needs_confirmation`으로 표시한다.
- 외부 협업 실적은 협약, MOU, 계약, 공동개발, 납품, 실증, 제휴처럼 회사 외부 주체와의 관계가 자료에서 확인될 때만 `ready`로 둔다.
- 외부 협업 실적 자료가 없으면 `value`를 비우고 `status: needs_confirmation`으로 둔다.
- ESG 자가진단은 회사 근거 유무와 무관하게 규격상 ESG 경영 여부와 전 세부 평가기준을 모두 `예 (Y)`로 선택하며, `esg_self_check_choices`는 `value: 전체 예(Y)`, `status: ready`로 둔다(`candidate`로 두지 않는다).
- 신청기술 제품/서비스명은 `distillation.md`와 `values.md`에서 반복 확인되는 핵심 기술·제품·서비스 축을 한 구절(명사구)로 압축해 작성한다.
- 신청기술 제품/서비스명은 별도 파일로 만들지 않고 `values.md`의 `### tech_name` 블록에만 기록한다.
- 신청기술 제품/서비스명의 핵심 기술축이 `distillation.md`와 `values.md`에서 반복 확인되면 `status: ready`로 둔다.
- 신청기술 제품/서비스명 후보가 여러 개이고 하나로 압축하기 어려우면 `status: candidate`로 둔다.
- 신청기술 제품/서비스명의 핵심 기술축이 `distillation.md`·`values.md`에서 확인되지 않으면 `value`를 비우고 `status: needs_confirmation`으로 둔다.

## 값 처리 기준

- `ready`: 자료에서 값이 확인되어 그대로 사용할 수 있는 상태.
- `needs_confirmation`: 자료에서 값을 찾지 못했거나, 같은 항목에 서로 다른 후보가 있어 확인이 필요한 상태.
- `not_applicable`: 회사 상황상 해당 항목이 적용되지 않는 상태.
- `portal_existing`: 포털에 기존 저장값이 있고 원자료에서 별도 변경 근거를 찾지 못한 상태.
- `candidate`: 정제 자료나 웹조사로 합리적 후보는 있으나 포털 선택값으로 확정하기 전인 상태.
- 숫자 `0`은 빈 값이 아니다. 자료에서 `0원`, `없음`, `해당 실적 없음`처럼 확인되면 `value: 0` 또는 `value: 없음`, `status: ready`로 기록한다.
- 자료가 없어 값을 정하지 못한 경우는 `value`를 비우고 `status: needs_confirmation`으로 기록한다.
- 항목 자체가 적용되지 않는 경우는 `value: 해당 없음`, `status: not_applicable`로 기록한다.
- 표 데이터에서 확인된 행이 없으면 빈 배열만 두지 말고, `status`를 `needs_confirmation` 또는 `not_applicable`로 구분한다.
- 선택값은 실제 포털 선택지와 정확히 일치해야 확정값으로 기록하고, 선택지 확인 전에는 `candidate`로 둔다.
- `notes`에는 값이 비어 있는 이유, `0`으로 둔 이유, 해당 없음 판단 이유, 포털 기존값 보존 이유를 짧게 남긴다.

## 출력 내용

- 출력 파일: `companies/<회사>/values.md`
- README 갱신 위치: `companies/<회사>/README.md`
- `values.md`에는 아래 값을 정리한다.
- 각 값은 다음 형식을 따른다.

```yaml
value:
status:
source:
notes:
```

### 기본 정보

- `company_name`: 기업명
- `business_registration_number`: 사업자등록번호
- `established_date`: 설립일 또는 개업일
- `industry_name`: 업종명
- `main_products_or_services`: 주요 제품·서비스
- `headquarters_address`: 본사주소
- `homepage`: 홈페이지
- `representative_name`: 대표자명
- `representative_table`: 대표자 목록
- `desired_evaluation_industry`: 평가희망업종
- `new_industry_field`: 신산업분야 여부

### 신청 유형

- `existing_application`: 기존 신청건 여부
- `venture_confirmation_history`: 벤처기업확인이력
- `company_application_status`: 신규기업 또는 재확인기업 판단
- `application_type`: 신청유형

### 포털 기본 입력 후보

- `phone_country`: 전화 국가번호
- `phone_number`: 전화번호
- `fax_number`: 팩스번호
- `headquarters_zip`: 우편번호
- `headquarters_base_address`: 기본주소
- `headquarters_detail_address`: 상세주소
- `representative_birth_date`: 대표자 생년월일
- `representative_gender`: 대표자 성별
- `representative_mobile_phone`: 대표자 휴대전화
- `representative_email`: 대표자 이메일
- `manager_name`: 담당자명
- `manager_position`: 담당자 직위
- `manager_mobile_phone`: 담당자 휴대전화
- `manager_email`: 담당자 이메일
- `paid_in_capital`: 납입자본금
- `innobiz_confirmation`: 6개월 이내 이노비즈기업 확인 여부
- `pre_venture_confirmation`: 예비벤처기업 확인 여부
- `three_year_employee_count`: 최근 3개년 각 연도 말일 기준 피보험자 수
- `corporate_registry_extract`: 법인등기부등본 적용 여부, 발급일, 말소사항 포함 여부
- `required_submission_documents`: 혁신성장유형 필수 제출자료 상태
- `attachment_source_paths`: 포털 첨부 업로드 대상 파일 경로

### 기술·인증·사업화 값

- `ip_ownership_table`: 지식재산권 보유 현황 표
- `iso_certifications`: ISO 인증 현황
- `technology_keywords`: 기술 키워드
- `product_service_differentiation_choices`: 제품·서비스 차별성 선택값 또는 후보
- `research_development_organization`: 연구개발 조직
- `technology_development_personnel_table`: 기술개발 인력 표
- `current_research_development_cost`: 현재 연구개발비
- `technology_development_achievements`: 기술개발 성과
- `tech_name`: 신청기술 제품/서비스명

### 재무·협업·자금·ESG 후보

- `finance_values`: 재무현황 입력 후보
- `external_collaboration_table`: 외부 협업 실적 표
- `funding_method_choices`: 자금조달 방법 선택값
- `growth_stage_radio`: 성장단계 선택값
- `esg_self_check_choices`: 모두 예(Y) 선택

## 사후 처리

- `README.md`의 자료 위치에 `values: values.md`를 추가한다.
- `README.md`의 진행 상태를 `venture-phase5-problemsolve`로 바꾼다.
- `values.md`의 값들이 장문 본문과 섞이지 않았는지 확인한다.

## 완료 조건

- `companies/<회사>/values.md`가 있음
- 기본 정보, 신청 유형, 포털 기본 입력 후보, 기술·인증·사업화 값이 구분되어 있음
- `ready`, `needs_confirmation`, `not_applicable`, `portal_existing`, `candidate` 상태가 기준에 맞게 구분되어 있음
- `0`, 빈 값, 해당 없음, 포털 기존값이 서로 다른 의미로 기록되어 있음
- 각 값에 `value`, `status`, `source`, `notes`가 있음
- `external_collaboration_table`, `esg_self_check_choices`, `tech_name`이 기준에 맞게 정리되어 있음
- 회사명, 대표자 수, 피보험자 수, 법인등기부등본 조건, 필수 제출자료 상태가 확인 가능한 범위에서 정리되어 있음
- `README.md`의 자료 위치에 `values: values.md`가 있음
- `README.md`의 `current_phase`가 `venture-phase5-problemsolve`임
