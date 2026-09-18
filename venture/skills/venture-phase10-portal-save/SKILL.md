---
name: venture-phase10-portal-save
description: README.md, values.md, texts/*.md를 기준으로 벤처인증 포털에 입력하고 임시저장할 때 사용한다.
---

# 실행

## 사전 준비

- 아래 `companies/<회사>`의 `<회사>`는 `V<YYMMDD>-<한글회사명>` 형식의 회사 폴더명이다. 사용자가 한글회사명만 말하면 `companies/`에서 `V*-<한글회사명>` 폴더를 찾아 쓰고, 날짜가 다른 폴더가 둘 이상이면 임의로 고르지 말고 어느 것을 쓸지 사용자에게 확인한다.
- 회사 작업공간: `companies/<회사>`
- 입력 파일 존재 여부를 확인한다.
  - `companies/<회사>/README.md`
  - `companies/<회사>/values.md`
  - `companies/<회사>/texts/business_plan_summary.md`
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
- 포털 계정은 `companies/<회사>/.env`의 `SMES_ID`, `SMES_PW`를 사용한다.
- Markdown 파일 읽기는 항상 UTF-8을 명시한다.
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
- `texts/*.md`
  - 사업계획서 요약
  - 문제정의 및 해결방안 본문
  - 성장전략 본문

## 작업 내용

- 표준 명령으로 `scripts/web.js`를 실행한다.
- 스크립트는 `README.md`, `values.md`, `texts/*.md`를 읽어 포털 입력용 내부 데이터로 변환한다.
- 스크립트는 준비된 값과 본문만 입력하고, 값이 없거나 `needs_confirmation`, `candidate`, `not_applicable` 상태인 항목은 건너뛴 뒤 로그에 남긴다.
- 대표자, 피보험자 수, 법인등기부등본처럼 제출서류와 맞아야 하는 항목은 `values.md`의 정해진 키 구조로만 읽는다.
- 첨부 업로드는 `values.md`의 `attachment_source_paths`에서 `status: ready`이고 파일 경로와 포털 코드가 있는 항목만 대상으로 한다.
- 담당자 본인인증처럼 자동입력이 불가능한 항목은 수동 필요 상태로 남긴다.
- 화면 이동, 입력, 임시저장은 `scripts/web.js`에 구현된 검증된 순서대로 수행한다.
- 파일 구조, 키 매핑, 문법, 화면 selector처럼 구조가 맞지 않는 오류가 발생하면 즉시 중단하고 오류 메시지와 멈춘 위치를 보고한다.

## 표준 명령

```powershell
node scripts/web.js --company "<회사>" --debug-port <포트> --step attachments-upload
```

## 출력 내용

- 포털에 입력 가능한 값과 본문을 입력하고 각 단계에서 임시저장한다.
- 실행 로그는 `.venture-sessions/portal-runs/<회사>/`에 기록한다.
- 회사 작업공간에는 새 입력 데이터 파일을 만들지 않는다.

## 사후 처리

- 스크립트 종료 상태를 확인한다.
- 실패 시 오류 메시지와 멈춘 단계를 주인님에게 보고한다.
- 값이 부족해 건너뛴 항목은 실패가 아니라 실행 로그의 skipped 항목으로 보고한다.
- 성공 시 마지막으로 실행된 단계와 임시저장 결과를 보고한다.

## 완료 조건

- `scripts/web.js`가 문법 오류 없이 실행 가능함
- `README.md`에서 포털 계정을 읽을 수 있음
- `values.md`와 `texts/*.md`를 포털 입력용 내부 데이터로 변환할 수 있음
- 표준 명령이 준비된 입력값과 본문을 읽어 실행을 시작할 수 있음
- 값 누락은 skipped로 기록되고 구조 오류가 아니면 실행을 계속함
- 첨부파일 누락은 skipped로 기록되고 구조 오류가 아니면 실행을 계속함
- 파일 경로, 키 매핑, 파싱, 문법 오류는 즉시 실패함
- 실행 결과가 성공 또는 명확한 포털 화면·입력값 부족 사유로 보고됨
