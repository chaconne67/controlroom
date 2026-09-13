# CRETOP 기업자금 참조자료 정리 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** PDF 회의 요청과 `경영진단.xlsx` 양식을 업무 해설·셀 매핑·계산식·LLM 프롬프트가 연결된 구현 기준 문서로 정리한다.

**Architecture:** PDF 원문과 실제 Excel 구조를 각각 사실 근거로 사용한다. 계산과 Excel 작성은 스크립트 책임으로, 검토의견과 최종결과의 의미 해석은 LLM 책임으로 분리하고 기존 `cretop_report_pipeline.py`를 단일 최종 경로로 유지한다.

**Tech Stack:** Poppler `pdftotext`, `openpyxl`, JSON, Markdown, Git

---

## 파일 구조

- 읽기: `cretop/cretop_기업자금_참조자료.pdf`
- 읽기: `cretop/경영진단.xlsx`
- 읽기: `docs/superpowers/specs/2026-07-15-cretop-funding-reference-summary-design.md`
- 수정: `cretop/cretop_기업자금_참조자료_정리.md`
- 수정: `docs/superpowers/specs/2026-07-15-cretop-funding-reference-summary-design.md`
- 수정: `docs/superpowers/plans/2026-07-15-cretop-funding-reference-summary.md`
- 코드와 설정 파일은 수정하지 않는다.

### Task 1: PDF 근거 추출 및 정리 문서 작성

**Files:**

- Create: `cretop/cretop_기업자금_참조자료_정리.md`
- Reference: `cretop/cretop_기업자금_참조자료.pdf`
- Reference: `docs/superpowers/specs/2026-07-15-cretop-funding-reference-summary-design.md`
- Test: 새 테스트를 작성하지 않는다. 문서 생성 작업이며 안정적인 실행 계약을 보호하는 테스트 대상이 아니다.

- [ ] **Step 1: PDF 텍스트를 다시 추출해 원문 근거를 고정한다**

Run:

```bash
pdftotext -layout 'cretop/cretop_기업자금_참조자료.pdf' -
```

Expected:

- `1. 대출가능금액 폼`
- `2. 필터링한 업체 14,000ea 업체 핸드폰 크레탑 조건값`
- `3. 업체 보고서 MMS 송부시`

- [ ] **Step 2: 통합형 Markdown 문서를 작성한다**

문서에 다음 제목을 이 순서대로 작성한다.

```markdown
# CRETOP 기업자금 참조자료 정리
## 1. 문서 개요
## 2. 한눈에 보는 핵심 요청
## 3. 대출가능금액 폼
## 4. CRETOP 대상 업체 필터
## 5. MMS 업체 보고서
## 6. 개발 요구사항 요약
## 7. 확인 필요 사항
## 8. 원문 보존본
```

다음 내용을 빠짐없이 반영한다.

- 이론 최대 한도는 제조업 `매출액의 1/2`, 도소매업 `1/6`, 그 외 비제조업 `1/4`
- 추정 상한은 이론 최대 한도에서 `1억원`을 차감하며 최솟값은 `1억원`
- 표시 하한은 추정 상한에서 다시 `1억원`을 차감하며 최솟값은 `1억원`
- 제조업 연매출 10억원은 이론 최대 5억원, 추정 상한 4억원, 표시 하한 3억원
- 최종 화면 예시는 `3억원 ~ 4억원`
- PDF 후반부의 제조업 `매출액의 1/4` 표기는 확정 규칙과 충돌함
- 매출 성장, 기존 대출 금액과 시기, 단기·장기차입금, 시설자금, 자본금이 실제 가능 금액을 바꿀 수 있음
- 안내 문구는 원문을 의미 변경 없이 보존함
- 휴업·폐업·회생 상태의 포함·제외 방향은 확인 필요
- 기업신용등급 `B+ 이상`
- 제조업과 비제조업 연매출 `5억원 이상`, 도소매업 `10억원 이상`
- 부채비율 `350% 이하`
- `B°`의 정확한 등급 표기는 확인 필요
- MMS 보고서에 `자본총계` 항목 추가
- PDF에 언급된 첨부이미지가 실제 파일에는 없어 위치와 표시 형식 확인 필요

- [ ] **Step 3: 사실과 해석을 구분해 자체 검토한다**

다음 기준으로 문장을 다시 읽는다.

- 원문 수치와 문구는 `원문 기준` 또는 인용문으로 표시함
- 문맥을 풀어 쓴 내용은 `해석`으로 표시함
- 사용자와 GBrain에서 확정한 제조업 `1/2` 계산 규칙을 적용하고 PDF 후반부 `1/4` 표기는 원문상 불일치로 남김
- 계산식이 없는 부채·자본금 보정 요인을 수치화하지 않음
- 필터 방향이 불명확한 휴업·폐업·회생 조건을 임의 확정하지 않음

- [ ] **Step 4: 문서 구조와 원문 범위를 검증한다**

Run:

```bash
test -s 'cretop/cretop_기업자금_참조자료_정리.md'
rg -n '^## ([1-9]|1[0-3])\.' 'cretop/cretop_기업자금_참조자료_정리.md'
rg -n '1/2|1/4|1/6|1억원|B\+|350%|자본총계|휴업|폐업|회생' 'cretop/cretop_기업자금_참조자료_정리.md'
git diff --check -- 'cretop/cretop_기업자금_참조자료_정리.md'
```

Expected:

- 파일이 비어 있지 않음
- `## 1.`부터 `## 13.`까지 13개 구역이 모두 검색됨
- 원문의 핵심 수치와 조건이 모두 검색됨
- `git diff --check` 오류가 없음

- [ ] **Step 5: 결과 문서만 커밋한다**

```bash
git add -- 'cretop/cretop_기업자금_참조자료_정리.md'
git commit --only -m 'docs: summarize CRETOP funding reference' -- 'cretop/cretop_기업자금_참조자료_정리.md'
```

Expected:

- 새 Markdown 문서 1개만 커밋됨
- 기존 사용자 변경사항은 커밋에 포함되지 않음

### Task 2: Excel 자동작성 기준 확장

**Files:**

- Modify: `cretop/cretop_기업자금_참조자료_정리.md`
- Modify: `docs/superpowers/specs/2026-07-15-cretop-funding-reference-summary-design.md`
- Modify: `docs/superpowers/plans/2026-07-15-cretop-funding-reference-summary.md`
- Reference: `cretop/경영진단.xlsx`
- Reference: `scripts/cretop_report_pipeline.py`
- Test: 문서 자체에는 새 테스트 파일을 만들지 않는다. 후속 스크립트의 계산·셀 오연결·파일 손상 계약은 문서에 테스트 대상으로 명시한다.

- [ ] **Step 1: 실제 Excel 구조를 읽는다**

Run:

```bash
uv run --with openpyxl python - <<'PY'
import openpyxl
wb = openpyxl.load_workbook('cretop/경영진단.xlsx', data_only=False)
print(wb.sheetnames)
ws = wb['Sheet1']
print(ws.max_row, ws.max_column)
print(ws['D32'].value, ws['D35'].value, ws['D36'].value)
PY
```

Expected:

- 시트 5개
- `Sheet1` 크기 37행 12열
- `D32`, `D35`, `D36`에 문구 입력 자리 표시값 존재

- [ ] **Step 2: 33개 셀 매핑과 출력 형식을 기록한다**

다음 계약을 문서에 포함한다.

- `Sheet1`만 자동작성
- 주거래은행은 `L11`
- `D7` 업태는 영업상태와 분리
- `D32`는 LLM 검토의견 2줄
- `D35`는 LLM 최종결과 2줄과 스크립트 고정 안내 1줄
- `D36`은 스크립트가 만든 대출가능금액 1줄
- 병합·스타일·행 높이·열 너비 보존

- [ ] **Step 3: 대출가능금액 계산 계약을 기록한다**

```text
sales_eok = latest_sales_million / 100
industry_rate = C이면 1/2, G이면 1/6, 그 외이면 1/4
theoretical_limit = floor(sales_eok × industry_rate)
estimated_upper = max(theoretical_limit - 1, 1)
display_lower = max(estimated_upper - 1, 1)
```

- [ ] **Step 4: LLM 프롬프트와 출력 계약을 기록한다**

- LLM은 `review_opinion_lines` 2개와 `final_result_lines` 2개를 JSON으로 출력
- LLM은 숫자 대출한도를 계산하거나 반복하지 않음
- 스크립트가 `D36`과 `D35` 고정 안내를 작성
- 계약 위반은 한 번 재요청하고 다시 실패하면 명시적 오류

- [ ] **Step 5: 문서와 양식의 셀 계약을 검증한다**

Run:

```bash
uv run --with openpyxl python - <<'PY'
import openpyxl
wb = openpyxl.load_workbook('cretop/경영진단.xlsx', data_only=False)
ws = wb['Sheet1']
required = ['L3','D4','J4','L4','D5','I5','L5','D6','K6','D7','K7','D10','D11','L11','D12','I12','L12','D15','D16','D17','D18','D19','D20','D21','D22','D23','D24','K24','D28','D29','D32','D35','D36']
assert len(required) == 33
assert all(ws[cell] is not None for cell in required)
assert ws['K11'].value == '주거래은행'
print('CELL_CONTRACT_OK', len(required))
PY
```

Expected: `CELL_CONTRACT_OK 33`

- [ ] **Step 6: 계산 예시와 프롬프트 책임을 검증한다**

Run:

```bash
rg -n 'theoretical_limit|estimated_upper|display_lower|review_opinion_lines|final_result_lines|NarrativeContractError' 'cretop/cretop_기업자금_참조자료_정리.md'
git diff --check -- 'cretop/cretop_기업자금_참조자료_정리.md' 'docs/superpowers/specs/2026-07-15-cretop-funding-reference-summary-design.md' 'docs/superpowers/plans/2026-07-15-cretop-funding-reference-summary.md'
```

Expected:

- 계산식과 프롬프트 출력 키가 모두 검색됨
- 공백 오류 없음

- [ ] **Step 7: 관련 문서만 커밋한다**

```bash
git add -- 'cretop/cretop_기업자금_참조자료_정리.md' 'docs/superpowers/specs/2026-07-15-cretop-funding-reference-summary-design.md' 'docs/superpowers/plans/2026-07-15-cretop-funding-reference-summary.md'
git commit --only -m 'docs: specify CRETOP xlsx report generation' -- 'cretop/cretop_기업자금_참조자료_정리.md' 'docs/superpowers/specs/2026-07-15-cretop-funding-reference-summary-design.md' 'docs/superpowers/plans/2026-07-15-cretop-funding-reference-summary.md'
```

Expected:

- 문서 3개만 커밋됨
- `cretop/경영진단.xlsx`는 사용자 원본으로 남고 커밋되지 않음
