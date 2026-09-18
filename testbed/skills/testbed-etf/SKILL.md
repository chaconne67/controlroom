---
name: testbed-etf
description: "투자유니버스 ETF 정보 조회 & 채우기. 투자유니버스, ETF 정보, ISIN 조회, 종목 채우기 언급 시 사용."
---

# 투자유니버스 ETF 정보 조회 & 채우기

**관련**: `testbed-base` (테스트베드), `fundkeeper` (프로젝트)

투자유니버스 시트의 신규 종목 정보를 조회·채우는 스킬. 국내 ETF는 funetf.co.kr(Playwright), 글로벌 종목은 웹검색으로 조회.

## 스크립트 위치
`<SKILL_DIR>`은 이 `SKILL.md`가 있는 실제 절대경로다. 활성 스킬 경로에서 확인한다.
- `lookup_isin.py` — 글로벌 ISIN 조회 (stockanalysis.com + Google + OpenFIGI 검증)
  - `validate_isin(isin)` — Luhn 체크디짓 검증
  - `make_isin(ticker)` — 국내 티커 → ISIN 조립
  - `verify_isin_openfigi(isins_dict)` — OpenFIGI 역검증

실행 시 `<SKILL_DIR>`를 실제 경로로 바꾸거나 그 디렉토리에서 실행한다.

## 1. 파일 찾기

1. 사용자가 전략명을 안 알려주면 질문
2. 경로: `C:\Users\chaconne\Google Drive 스트리밍\내 드라이브\MOA\테스트베드2차\준비서류\`
3. 전략 폴더: 국내ETF → `모아국내ETF레시피/`, 글로벌 → `모아글로벌투자레시피/`, 퇴직연금 → `모아퇴직연금레시피/`
4. `21.`로 시작하는 `리밸런싱 발생내역` xlsx (최신 날짜) → `투자유니버스` 시트
5. **비고(I열) 빈 행은 무시** (CASH 등)
6. **ISIN 검증**:
   - **국내**: I열 티커 → `make_isin()` 재계산 → A열 비교. 불일치 시 funetf 상세페이지로 확인
   - **글로벌**: Playwright 브라우저로 조회 → A열 비교 (§4)
   - **ISIN 수정 시 다른 시트**:
     - **국내**: 다른 시트에도 잘못된 ISIN이 키값으로 존재 → 함께 수정
     - **글로벌**: **투자유니버스만 수정**. 다른 시트(전체매매내역, 잔고변경현황, MP내역 등)는 증권사 거래 데이터 기반으로 이미 올바른 ISIN

## 2. 투자유니버스 시트 구조 (A~I열)

| 열 | 헤더 | 국내 ETF/퇴직연금 | 글로벌 |
|---|---|---|---|
| A | ISIN코드 | `make_isin(티커)` → funetf 확인 | 주식: stockanalysis.com, ETF: Google+OpenFIGI |
| B | 종목명 | funetf 타이틀 | OpenFIGI `figi_name` 또는 웹검색 |
| C | 시장구분 | **사용자에게 질문** | **사용자에게 질문** |
| D | 자산군 | ETF (고정) | 주식 또는 ETF |
| E | 자산종류 | funetf 기초지수로 판별 (§6) | 웹검색으로 판별 (§6) |
| F | 위험등급 | funetf "N등급(위험등급명)" | 글로벌 위험도 규칙 (§4) |
| G | 위험도 점수 | `7 - 등급번호` | 글로벌 위험도 규칙 (§4) |
| H | 위험자산여부 | `등급 ≤ 3 ? Y : N` | 글로벌 위험도 규칙 (§4) |
| I | 비고 | 티커 | 티커 |

## 3. 국내 ETF 조회 — lookup_funetf.py

**스크립트**: `<SKILL_DIR>/lookup_funetf.py`

### 단건 조회
```
python "<SKILL_DIR>/lookup_funetf.py" --isin KR7069500007
python "<SKILL_DIR>/lookup_funetf.py" --ticker 069500
```

### 대량 조회
```
python "<SKILL_DIR>/lookup_funetf.py" \
  --batch KR7069500007 KR7379800004 ...
```

결과 JSON의 `results` 배열을 보고한다. 독립 작업자가 허용된 환경에서는 국내·글로벌 조회를
나눠 실행할 수 있다.

### 출력 JSON
```json
{"results": [{"isin": "KR7069500007", "name": "KODEX 200", "base_index": "KOSPI 200",
  "risk_grade": 2, "risk_grade_name": "높은위험", "risk_score": 5,
  "is_risk_asset": "Y", "asset_type_hint": "국내주식"}], "errors": []}
```

### ISIN코드 조립 (티커만 있는 경우)
`KR7` + 티커(6자리, 좌측0패딩) + `00` + Luhn체크디짓 = **12자리**
→ `--ticker` 옵션 사용 시 자동 조립. 예: `069500` → `KR7069500007`

### 참고
- URL: `https://www.funetf.co.kr/product/etf/view/{ISIN코드}` — 타사 ETF(SOL, ACE, RISE 등)도 지원
- `headless=False`로 실행 — 화면에 브라우저 창이 열림

## 4. 글로벌 종목 조회 — lookup_isin.py

**스크립트**: `<SKILL_DIR>/lookup_isin.py`

### 대량 조회
```
python "<SKILL_DIR>/lookup_isin.py" {tickers} --etf {etf_tickers}
```

결과 JSON을 보고한다.

### 글로벌 + 국내 병렬 조회
독립 작업자가 허용된 환경에서는 국내(`lookup_funetf.py`)와 글로벌(`lookup_isin.py`) 조회를
동시에 실행할 수 있다.

⚠ headless=False로 실행 — 화면에 브라우저 창이 열림. 백그라운드 실행 불가.

### 주식 ISIN — stockanalysis.com
1. `https://stockanalysis.com/stocks/{ticker}/company/`
   - 티커 `-` → `.` 변환 (예: `BRK-B` → `brk.b`)
   - **GOOGL**(Class A) = `US02079K3059`, **GOOG**(Class C) = `US02079K1079` — 별도 종목
2. "ISIN Number" 행에서 추출
3. **ISIN 국가코드**: US 상장이라도 본사에 따라 접두사 다름
   - ASML → `USN070592100`, NXPI → `NL0009538784`, AZN → `GB0009895292`, AMCR → `JE00BV7DQ550`

#### 대량 조회 최적화
- **ISIN 추출** (`browser_evaluate`):
  ```javascript
  () => { const rows = document.querySelectorAll('tr'); for (const row of rows) { const cells = row.querySelectorAll('td'); if (cells.length >= 2 && cells[0].textContent.trim() === 'ISIN Number') { return cells[1].textContent.trim(); } } return 'NOT_FOUND'; }
  ```
- **페이지 이동** (`browser_evaluate` — 스냅샷 반환 없음):
  ```javascript
  () => { window.location.href = 'https://stockanalysis.com/stocks/{ticker}/company/'; return 'nav'; }
  ```
- `browser_navigate`는 스냅샷(300줄+)을 반환하므로 단순 이동에는 위 방법 사용
- **console overflow**: 광고 스크립트 에러가 ~10-15회 이동 후 누적 → `browser_navigate`로 리셋. 10-15회마다 1회 사용

### ETF ISIN — Google 검색 + OpenFIGI 역검증
1. `https://www.google.com/search?q={ticker}+{ETF풀네임}+ISIN`
2. ISIN 후보 추출 (`browser_evaluate`로 정규식 매칭) → `validate_isin()`으로 Luhn 필터
3. **OpenFIGI 역검증 (필수)**: `https://api.openfigi.com/v3/mapping` POST, `idType: "ID_ISIN"`, `idValue: "{ISIN}"` → 배치 가능, 응답 티커와 시트 티커 대조

### 글로벌 위험도 규칙
- **주식, 주식ETF, 원자재** → 1등급(매우높은위험), 점수 6, 위험자산 Y
- **채권 등** → 국내 기준에서 1등급 상향 (점수 +1, 최대 6)

위험등급 공식: `점수 = 7 - 등급번호`, `위험자산 = 등급 ≤ 3 ? Y : N`

## 5. 자산종류 판별

- 카테고리는 하드코딩 안 함. **시트 E열의 기존 고유값**을 유효 목록으로 사용
- **국내**: funetf 기초지수 키워드로 판별
- **글로벌**: 웹검색으로 종목 성격 파악 → 기존 카테고리 매칭. 채권은 듀레이션도 확인

### 글로벌 자산종류 특수 규칙
- **XLU (Utilities Select Sector SPDR)** → **해외원자재**. 원자재 가격과 동행
- 자산종류는 종목 형태가 아닌 **가격 동행 패턴(상관관계)** 기반 → 기존 시트 값 존중, 임의 변경 금지

## 6. 스크립트 실행 규칙

- **국내 ETF**: `lookup_funetf.py` 사용
- **글로벌 ISIN**: `lookup_isin.py` 사용
- **MCP Playwright 사용**: 위 스크립트로 해결 불가할 때만 (수동 탐색 등)
- **실행 실패** → `taskkill /F /IM chrome.exe /T` 후 재시도. WebFetch 우회 금지
- **headless=False 필수** — 두 스크립트 모두 visible 브라우저로 실행됨
- **금지**: 스크립트로 HTTP 리퀘스트 일괄 조회

## 7. 서버 DB 연동

엑셀 수정 후 서버 DB에도 반영.

### Asset 모델
- 파일: `/home/work/fundkeeper/simulation/models.py`
- 테이블: `ticker_list`

| 필드 | 설명 |
|------|------|
| `ticker` | CharField(10, unique) |
| `isin_code` | CharField(12) |
| `asset_type` | CharField(32) — 해외주식, 해외원자재, 해외중기채권 등 |
| `dscore` | IntegerField |
| `description` | CharField(255) — 종목명 |
| `asset_class` | CharField(24) |
| `market` | CharField(32) |
| `is_danger` | BooleanField |
| `pension` / `svr` | BooleanField |

### 주의
- 엑셀과 서버 DB 수정은 **항상 함께**
- 서버 DB가 엑셀보다 정확한 경우 있음 → 수정 전 서버 현재값 확인

## 참고
- funetf.co.kr: 검색은 일부 운용사만, ISIN 직접 접근은 모든 국내 ETF 지원
- 국내 ISIN: `KR7` + 종목코드(6자리) + `00` + 체크디짓 = 12자리
- 종목코드: 6자리 숫자 또는 영숫자 혼합 (예: 379800, 0051G0)
