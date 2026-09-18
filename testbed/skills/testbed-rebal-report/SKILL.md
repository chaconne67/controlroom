---
name: testbed-rebal-report
description: "테스트베드 리밸런싱 발생내역 엑셀(21번 서류) 작성·갱신·업로드. 리밸런싱 발생내역, 21번 서류, update_rebalancing_report, 엑셀 갱신 언급 시 사용."
---

# 테스트베드 리밸런싱 발생내역 (엑셀) 작성

**관련**: `testbed-base` (테스트베드 공통), `testbed-etf` (투자유니버스)
**접속정보**: `C:\Users\chaconne\.env` → `TESTBED_ID`, `TESTBED_PW` (포털: https://www.ratestbed.kr:7443)
**서류 디렉토리**: `C:\Users\chaconne\Google Drive 스트리밍\내 드라이브\MOA\테스트베드2차\준비서류\`

## 스크립트 위치
`<SKILL_DIR>`은 이 `SKILL.md`가 있는 실제 절대경로다. 활성 스킬 경로에서 확인한다.
- `fetch_rebalancing_data.py` — 서버 데이터 수집 → JSON
- `update_rebalancing_report.py` — JSON → 엑셀 업데이트
- `rebalancing_report_config.json` — 레시피명 설정 (`name`만 기입, `dir`/`file_prefix`는 코드에서 자동 생성)

실행 시 `<SKILL_DIR>`를 실제 경로로 바꾸거나 그 디렉토리에서 실행한다.
```
python "<SKILL_DIR>/fetch_rebalancing_data.py" ...
```

## 작업 흐름 (⚠ 순서 엄수)

### 1단계: 사용자 확인 — 스케줄 목록 조회 (메인 에이전트)
사용자 요청이 모호하면 **반드시 확인 후 진행**:
```
python fetch_rebalancing_data.py list-schedules --recipe {kr|svr|us}
```
확인 항목:
- **레시피**: kr(국내ETF) / svr(퇴직연금) / us(글로벌투자)
- **스케줄(회차)**: 어떤 schedule_id를 업데이트할지
- 리밸런싱 사유는 항상 **정기리밸런싱** (별도 확인 불필요)

### 2-3단계: 데이터 생성 + 엑셀 업데이트

레시피마다 다음 두 명령을 순서대로 실행한다.
```
python "<SKILL_DIR>/fetch_rebalancing_data.py" \
  fetch --recipe {recipe} --schedule-id {ID}
python "<SKILL_DIR>/update_rebalancing_report.py" \
  --recipe {recipe} --schedule-id {ID}
```

성공 시 엑셀 파일 경로를 보고하고 실패 시 에러 출력 전체를 보고한다.

독립 작업자가 허용된 환경에서는 복수 레시피를 레시피별로 나눠 동시에 처리할 수 있다.

#### 2단계 세부: 데이터 생성 (서버 → JSON)
```
python fetch_rebalancing_data.py fetch --recipe {kr|svr|us} --schedule-id {ID}
```
서버에서 수행하는 작업 순서:
1. **잔고내역저장** — TestBed API로 실제 잔고 조회 → TestBedBalance DB 저장
2. **거래내역 조회** — TradeHistory에서 해당 기간 매매내역
3. **모델포트폴리오 조회** — OrderAccounts.order_json에서 목표 비중
4. **잔고내역불러오기** — TestBedBalance + rday 종가 적용 (rday_value)

결과: `{서류디렉토리}/{레시피명}/rebalancing_data_{ID}.json`

#### 3단계 세부: 엑셀 업데이트 (JSON → xlsx)
```
python update_rebalancing_report.py --recipe {kr|svr|us} --schedule-id {ID}
```
- 기존 최신 `_YYYYMMDD.xlsx` 로드 → 시트 편집 → 오늘 날짜로 저장
- `--dry-run`: 검증만, 파일 저장 안 함
- **멱등성**: 같은 rday 데이터가 이미 있으면 삭제 후 재작성

편집 대상 시트 (순서):
1. **투자유니버스** — 누락 종목만 추가 (전체 값 입력)
2. **전체매매내역** — 해당 기간 거래 삭제 → append (전체 값 입력)
3. 그룹별 (안정/중립/적극) ×:
   - **MP내역** — rday 블록 삭제 → 재작성 (값+수식 혼합)
   - **포트변경내역** — rday 행 삭제 → 재작성 (대부분 수식)
   - **잔고변경현황 ×3** — rday 블록+합계행 삭제 → 재작성 (값+수식 혼합)

### 4단계: 포털 업로드

`<TESTBED_BASE_SKILL_DIR>`은 `testbed-base`의 `SKILL.md`가 있는 실제 절대경로다.
```
python "<TESTBED_BASE_SKILL_DIR>/portal_upload.py" \
  --url "{forUpdate_URL}" \
  --file "{xlsx_path}" \
  --title "{title_YYYYMMDD}" \
  --content-append "{history_line}"
```

JSON 결과를 보고한다.

독립 작업자가 허용된 환경에서는 복수 레시피 업로드를 동시에 실행할 수 있다.

## 엑셀 편집 핵심 원칙 (하드코딩 금지)

### 컬럼 동적 매핑
- 컬럼 번호 하드코딩 절대 금지 → 헤더 행에서 `build_header_map()` → `find_col()`로 동적 탐지
- 시트별 헤더 위치: 투자유니버스/전체매매내역/MP내역 = R1, 잔고변경현황/포트변경내역 = R4

### 수식/값 자동 분류
- 템플릿 행(기존 마지막 데이터 행)에서 수식 셀과 값 셀을 자동 감지
- `clone_row()`: 수식 셀 → 행번호 치환 복제, 값 셀 → `value_overrides`로 기입
- `$`절대참조는 유지, 상대참조만 행번호 치환

### 합계행 복제
- `clone_sum_row()`: SUM 범위를 새 블록에 맞게 조정
- 범위 end가 old_block_end와 일치하면 start/end 모두 새 블록으로 치환 (컬럼별 start 불일치 대응)
- old_block_start/end는 SUM 수식에서 직접 파싱 (`extract_sum_range()`) — 날짜 추정이 아님

### 합계행 탐지 함정
- 안정 시트: ISIN 컬럼에 '합계' 텍스트 있음 → 직접 탐지
- 중립/적극 시트: '합계' 텍스트 없음 → `=SUM(` 패턴으로 폴백 탐지
- 새 합계행 생성 시 `value_overrides`로 '합계' 텍스트를 항상 기입

### 잔고 데이터 함정 (서버 측, `test_bed.py` → `export_rebalancing_report()`)
- CASH의 DataFrame index가 `None` → `isincode='CASH'`로 보정 (ticker 컬럼 참조)
- CASH의 `rday_value=0` (qty=0 × price) → 실제 현금 잔액은 `value` 컬럼 사용
- `잔고내역불러오기` 반환값: `{pk: DataFrame}` — index=isincode, 컬럼=ticker/qty/avg_price/value/ratio/rday_price/rday_value
- `order_json`과 `TestBedBalance.balance`는 pandas DataFrame을 JSON 직렬화한 형태 (컬럼 지향 dict)

### 새 블록 삽입 위치 (합계행 있는 시트: MP내역, 잔고변경현황)
- 반드시 **템플릿 합계행 바로 다음** (`tpl_sum + 1`)에 삽입
- `find_last_data_row()` 사용 금지: 합계행의 identifier 컬럼이 비어있으면 합계행을 데이터로 오인 → 합계행 덮어쓰기 발생
- 포트변경내역은 합계행이 없으므로 `find_last_data_row()` 사용 가능

## 포털 업로드 — 수동 폴백 (portal_upload.py 실패 시 — Playwright MCP 사용)

⚠ `portal_upload.py` 스크립트 실패 시에만 아래 절차를 사용.
⚠ 핵심 함정: 파일 삭제 시 페이지 리로드 → 폼 필드 초기화. 폼 입력은 삭제 완료 후에.

```
1. browser_navigate → 포털 로그인 → forUpdate.do URL 이동
2. [삭제 전] browser_run_code:
   await page.evaluate(() => { window.confirm = () => true; });
   page.once('dialog', async dialog => { await dialog.accept(); });
3. browser_click 삭제 → 페이지 리로드
4. [리로드 후] browser_file_upload → browser_fill_form (제목, 내용)
5. [제출 전] browser_run_code로 dialog 리스너 재등록
6. 확인 클릭 → browser_close
```

### 빠뜨리기 쉬운 것
- **파일명 날짜**: xlsx 파일명 `_YYYYMMDD`를 당일 날짜로 변경 후 업로드
- **제목 날짜**: 포털 제목 필드의 `_YYYYMMDD`도 당일 날짜로 변경
