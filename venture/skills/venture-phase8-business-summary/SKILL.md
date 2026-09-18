---
name: venture-phase8-business-summary
description: README.md, values.md와 앞선 본문 산출물을 바탕으로 사업계획서 요약 양식의 빈칸 값만 작성하고, 치환 스크립트로 조립할 때 사용한다.
---

# 실행

## 사전 준비

- 아래 `companies/<회사>`의 `<회사>`는 `V<YYMMDD>-<한글회사명>` 형식의 회사 폴더명이다. 사용자가 한글회사명만 말하면 `companies/`에서 `V*-<한글회사명>` 폴더를 찾아 쓰고, 날짜가 다른 폴더가 둘 이상이면 임의로 고르지 말고 어느 것을 쓸지 사용자에게 확인한다.
- 회사 작업공간: `companies/<회사>`
- 입력 파일 존재 여부를 확인한다.
  - `companies/<회사>/README.md`
  - `companies/<회사>/distillation.md`
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
- 조립 자산 존재를 확인한다.
  - 양식 템플릿: `skills/venture/references/business_plan_summary_template.md`
  - 치환 스크립트: `scripts/fill_business_plan_summary.py`
- 출력 폴더가 없으면 생성한다.
  - `companies/<회사>/texts/`
- Markdown 파일 읽기와 쓰기는 항상 UTF-8을 명시한다.
- PowerShell에서 한글 파일을 확인할 때는 먼저 `[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)`를 실행한 뒤 `Get-Content -LiteralPath <path> -Encoding UTF8`로 읽는다.

## 입력 내용

- `README.md`
  - 회사명
  - 작성 방향
  - 현재 진행 상태
- `values.md`
  - `tech_name`
  - 주요 제품·서비스
  - 기술·인증·사업화 값
  - 재무·협업·자금 후보
- `distillation.md`
  - 회사 개요
  - 주요 제품·서비스
  - 핵심 기술
  - 특허·인증
  - 시장환경
  - 경쟁·대체재 환경
  - 차별성 작성 포인트
- 문제해결 본문:
  - `texts/problem_background.md`
  - `texts/solution.md`
  - `texts/tech_progress.md`
  - `texts/tech_plan.md`
- 시장 본문:
  - `texts/target_market.md`
  - `texts/competition.md`
  - `texts/market_progress.md`
  - `texts/market_plan.md`
- 스타트업 본문:
  - `texts/funding_plan.md`
  - `texts/entrepreneurship.md`

## 작업 내용

- 사업계획서 요약은 정해진 양식의 밑줄 빈칸만 채우는 작업이며, 고정 문구는 작성 대상이 아니다.
- 작성 sub-agent는 고정 문구를 생성하지 않고, 양식 템플릿의 각 플레이스홀더(`{{key}}`)에 들어갈 값만 키별로 반환한다.
- 메인 에이전트는 반환된 값을 JSON으로 저장하고, 치환 스크립트로 템플릿의 빈칸만 채워 산출물을 조립한다.
- 고정 문구는 템플릿에만 존재하고 스크립트가 그대로 보존하므로, LLM이 양식을 재생성하다 고정 문구를 변형하는 오류가 원천 차단된다.
- 작성·검사 sub-agent를 호출하고, 메인 에이전트는 스크립트로 조립한 뒤 결과를 저장한다.

## 작문 규칙 로드

작문 규칙 정본은 아래 한 파일이다. 규칙을 이 파일에 복제하지 않는다.

```
skills/venture/references/writing-rules.md
```

- 작성·검사 sub-agent를 호출하기 전에 프로젝트 루트 기준 위 경로를 Read로 읽는다. 이미 읽었다고 판단해 건너뛰지 않는다.
- 파일 첫 절인 `## 역할과 입장`을 먼저 적용한다. 다른 모든 규칙보다 우선하며, sub-agent 프롬프트에 반드시 함께 포함한다.
- 읽지 않은 상태로 sub-agent를 호출하지 않는다.
- sub-agent 프롬프트에는 해당 절 전문을 그대로 포함한다. 요약하거나 경로만 알려주지 않는다.
- 규칙 파일의 `phase별 적용 범위` 표에서 이 phase에 해당하는 행을 확인하고 그대로 적용한다.

## 작성 sub-agent 제공 내용

- 작성 규칙:
  - 자유 서술 문체·글자수 규칙은 적용하지 않는다. 수치 빈칸은 작문 규칙 파일의 `## 작문 공통 규칙` 중 `### 수치·근거`를 따른다.
  - 이 phase는 양식 빈칸에 들어갈 값만 작성하는 작업이다. 고정 문구, 양식 전체, 다른 빈칸을 생성하거나 수정하지 않는다.
- 입력 자료:
  - `신청기술(제품/서비스)명`: `values.md`의 `### tech_name`
  - 문제정의 및 해결방안 작성 요지: `texts/problem_background.md`, `texts/solution.md`, `texts/tech_progress.md`, `texts/tech_plan.md`
  - 성장 전략 작성 요지: `texts/target_market.md`, `texts/competition.md`, `texts/market_progress.md`, `texts/market_plan.md`, `texts/funding_plan.md`, `texts/entrepreneurship.md`
  - 참고 자료: `distillation.md`, `values.md`
- 빈칸 값 작성 원칙:
  - 각 빈칸 키에 들어갈 짧은 명사구나 절만 작성하고, 양식 고정 문구와 이어졌을 때 문장이 자연스럽게 읽히도록 한다.
  - 값은 앞 본문 산출물과 `values.md`의 확인값을 압축해 채운다. 새 문단·추가 설명·근거 설명을 만들지 않는다.
  - 수치 빈칸(`market_size`·`cagr`·`ip_count`·`rnd_count`·`dev_count`·`current_market`·`years`)은 앞 본문의 수치를 가져와 채우고 비우지 않는다(작문 규칙 파일의 `## 작문 공통 규칙` 중 `### 수치·근거`). 매출·실적이 없는 초기 기업은 `market_size`를 추정 시장규모로, `current_market`을 진입 단계 표현으로 채운다.
  - 결과는 키별 값만 반환한다. 고정 문구나 양식 문장을 포함하지 않는다.
- 빈칸 키 목록(반환할 값):

  | 키 | 들어갈 내용 | 주 근거 |
  |---|---|---|
  | `tech_name` | 신청기술(제품/서비스)명 | `values.md` tech_name |
  | `summary` | 기술 요약 한 줄 | tech_name·solution |
  | `problem` | 기존 시장의 니즈(문제) | problem_background |
  | `problem_cause` | 문제가 지속되는 이유 | problem_background |
  | `solution` | 당사의 해결 방식 | solution |
  | `difference` | 기존 시장 기술과의 차이 | solution |
  | `tech_name_full` | 보유·개발 중인 기술명 | `values.md` tech_name |
  | `market_size` | 전체 시장 규모 | target_market |
  | `cagr` | 연평균 성장률(% 앞 숫자) | target_market |
  | `tech_base` | 기술이 기반한 것 | solution·tech_progress |
  | `tech_feature` | 기술 특징 | solution |
  | `tech_advantage` | 우위·차별 이유 | solution |
  | `ip_list` | 지식재산권 종류 나열 | tech_progress·values |
  | `ip_count` | 지식재산권 건수(숫자) | values |
  | `rnd_org` | 연구개발조직(기업부설연구소/전담부서 등) | values |
  | `rnd_count` | 연구개발조직 인원(숫자) | values |
  | `dev_count` | 완료한 기술개발 건수(숫자) | tech_progress·values |
  | `market_entry` | 시장진입 마케팅 활동 | market_progress |
  | `current_market` | 현재 확보 시장 규모 | market_progress |
  | `market_expand` | 향후 3년 마케팅 계획 | market_plan |
  | `capability` | 성과를 가능케 한 역량 | entrepreneurship·전반 |
  | `years` | 향후 몇 년(숫자, 보통 3) | market_plan |
  | `growth_adj` | 성장 수식어 | market_plan |
  | `growth` | 성장 유형·목표 | market_plan·target_market |

## 검사 sub-agent 제공 내용

- 검사 규칙: 작문 규칙 파일의 `## 작문 검사 규칙` 전문
- 작성 sub-agent가 반환한 빈칸 값(키별)
- 값 확인에 필요한 `distillation.md`, `values.md`, 앞선 본문 산출물 내용

## 검사 sub-agent 작업

- 각 빈칸 값이 양식 고정 문구와 이어졌을 때 문장이 자연스러운지 점검한다.
- 모든 키에 값이 있는지, 수치 빈칸이 비어 있지 않은지 점검한다.
- 심각한 사실 오류, 명백한 창작, 벤처인증 제출문에 어울리지 않는 작성자 방어식 표현을 점검한다.
- 고정 문구 변형은 스크립트가 막으므로 점검 대상이 아니다.
- 최종 권장 값(키별)을 반환한다.

## 출력 내용

- 메인 에이전트는 확정된 빈칸 값을 JSON으로 저장한다.
  - 경로: `companies/<회사>/texts/business_plan_summary_values.json`
  - 키는 위 빈칸 키 목록과 동일하게 24개를 모두 채운다.
- 치환 스크립트로 산출물을 조립한다.
  - `uv run python scripts/fill_business_plan_summary.py --values companies/<회사>/texts/business_plan_summary_values.json --out companies/<회사>/texts/business_plan_summary.md`
  - 스크립트는 템플릿의 `{{key}}` 빈칸만 값으로 치환하고, 본문 실측 글자수를 `char_count`에 기록한다.
  - 미작성 빈칸이 있으면 스크립트가 미치환 키를 출력하며 실패하므로, 값을 채워 다시 실행한다.
- 산출물(`business_plan_summary.md`)의 고정 문구·양식·줄 순서는 템플릿을 그대로 따른다(스크립트가 생성).
- 메인 에이전트는 조립된 `business_plan_summary.md`를 읽어 고정 문구와 빈칸 값이 결합된 최종 문장이 자연스럽게 읽히는지(조사·어미·연결·문맥) 검토한다. 어색하면 고정 문구는 그대로 두고 ① 빈칸 값을 고쳐 `fill_business_plan_summary.py`로 재조립하거나 ② 결과물의 빈칸 값 표현을 직접 다듬는다(맥락 판단은 에이전트가 담당).
- 다듬은 뒤에는 반드시 verify 스크립트로 고정 문구 무결성을 기계 검증한다(메인 에이전트가 다듬다가 고정 문구를 훼손하지 않았는지 성공/실패로 판정).
  - `uv run python scripts/verify_business_plan_summary.py --file companies/<회사>/texts/business_plan_summary.md`
  - 고정 문구 훼손·순서 불일치·미치환 빈칸이 있으면 FAIL(exit 1)이므로 바로잡고, verify가 OK(exit 0)가 될 때까지 검토·재조립·검증을 반복한다.

## 사후 처리

- `README.md`의 자료 위치에 `business_plan_summary: texts/business_plan_summary.md`를 추가한다.
- `README.md`의 진행 상태를 `venture-phase9-portal-ready`로 바꾼다.
- 스크립트가 미치환 빈칸 없이 성공했는지 확인한다.
- 한글 깨짐이 없는지 확인한다.
- 고정 문구는 템플릿 기반으로 자동 보존되므로 별도의 변형 검증은 필요하지 않다.

## 완료 조건

- `companies/<회사>/texts/business_plan_summary_values.json`에 24개 빈칸 값이 모두 기록되어 있음
- `companies/<회사>/texts/business_plan_summary.md`가 스크립트로 생성되어 있고 미치환 빈칸이 없음
- 산출물의 고정 문구·양식·줄 순서가 템플릿과 동일함(스크립트 보장)
- 조립된 최종 문장이 고정 문구와 빈칸 값이 자연스럽게 이어져 읽힘(메인 에이전트 검토 완료)
- verify 스크립트(`verify_business_plan_summary.py`)가 OK(고정 문구 무결성 통과, exit 0)
- `README.md`의 자료 위치에 `business_plan_summary: texts/business_plan_summary.md`가 있음
- `README.md`의 `current_phase`가 `venture-phase9-portal-ready`임
- 한글 깨짐 흔적이 없음
