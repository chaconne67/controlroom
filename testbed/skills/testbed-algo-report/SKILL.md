---
name: testbed-algo-report
description: "테스트베드 알고리즘설명서(11번 서류) pptx 점검·수정·PDF변환·업로드. 위험도 산출 테이블 검증, 레이아웃 비교, python-pptx 수정, PowerPoint COM PDF 변환, 포털 업로드. 알고리즘설명서, 11번 서류, pptx 점검, 위험도 산출 언급 시 사용."
---

# 테스트베드 알고리즘설명서 (pptx) 작성

**관련**: `testbed-base` (테스트베드 공통), `fundkeeper` (프로젝트)
**접속정보**: `C:\Users\chaconne\.env` → `TESTBED_ID`, `TESTBED_PW` (포털: https://www.ratestbed.kr:7443)
**서류 디렉토리**: `C:\Users\chaconne\Google Drive 스트리밍\내 드라이브\MOA\테스트베드2차\준비서류\`

## 작업 시작 전 확인사항
사용자 요청에 빠진 정보가 있으면 먼저 확인:
- **어떤 레시피?**: 모르면 `MyPortfolios.objects.filter(name__icontains=키워드)`로 검색
- **서류 폴더 경로?**: 서류 파일이 있는 로컬 폴더 (파일명에서 서류 종류 식별)
- **레퍼런스 파일?**: 레이아웃 비교가 필요한 서류는 기준본 파일 경로 확인

## 전략명 → 데이터 조회 흐름

모델 체인 (각 단계의 결과를 다음 단계 필터에 사용):
1. `MyPortfolios.objects.filter(name__icontains=키워드)` → name, purpose, id로 포트폴리오 특정
2. `MyPortfolioManager.objects.filter(myportfolio=portfolio)` → subportfolio, mixed_wt(비중%)
3. `MyAccount.objects.filter(myportfolio=portfolio)` → description에 적극투자/위험중립/안전추구 구분
4. `OrderAccounts.objects.filter(schedule=schedule, account__in=accounts)` → order_json(ticker, ratio, description)
5. `Asset.objects.get(ticker=ticker)` → isin_code, description, asset_type, dscore, market, pension, svr

모델 위치: MyPortfolios/MyPortfolioManager/Backtest → `myportfolio.models`, MyAccount → `myaccount.models`, OrderAccounts/RebalancingSchedule → `order.models`, Asset → `simulation.models`

## 필요 데이터 수집
1. 서브전략 & 비중 → `MyPortfolioManager` 조회
2. 각 서브전략의 공격/방어 종목:
   ```python
   bt = sub_portfolio.backtest.first()  # myportfolio.models.Backtest (역참조)
   tickers = bt.backtest_ticker.all()   # BacktestTicker → .ticker 필드
   # bt.attack_asset_num / bt.defense_asset_num → 공격/방어 종목 수
   # Asset.asset_type/dscore로 공격(주식/원자재)/방어 분류
   ```
3. 위험도 → 아래 "위험도 산출 방법"으로 계산

## 위험도 산출 방법 (보고서용)

**마스터 시트**: https://docs.google.com/spreadsheets/d/1VYfQAMLEBI3erAc8lv2YGzsORQx3j-ZahRAwUmDmz18/edit?usp=sharing
- `위험도` 시트에 레시피별(국내/글로벌/퇴직연금) × 유형별(순한맛/중간맛/매운맛) 전략 비중, 자산종류, 위험점수, 최소·최대 위험도 정리

### DB dscore와 보고서 위험점수의 불일치
Asset.dscore는 종목별로 세분화되어 있어 보고서용으로 직접 사용 불가. 추상화 규칙:
- asset_type 기준 그룹핑, 같은 asset_type 내에서 **낮은 dscore**를 대표값으로 사용
- TDF = 중기채권 50% + 안전자산 50%로 분할

### 위험점수 매핑 (보고서 고정값, DB에서 도출 불가)
| 자산종류 | 국내ETF/퇴직연금 | 글로벌투자 |
|---|---|---|
| 주식/원자재 | 6 | 6 |
| 장기채권 | - | 4 |
| 중기채권 | 3 | 3 |
| 단기채권 | 2 | - |
| 안전자산채권 | 1 | 2 |
| 현금 | 1 | 1 |

### 산출 공식
`위험도 = Σ(자산종류별 비중 × 위험점수) / 100`
- **최대위험도**: 위험자산(주식/원자재) 최대 편입 시 (공격 종목 전부 주식)
- **최소위험도**: 위험자산 0%, 방어자산으로 전환 시

서브전략 비중(MyPortfolioManager.mixed_wt)과 각 서브전략의 공격/방어 종목 구성으로 계산.

### 국내 방어종목 분류 주의
DB상 dscore가 다양하지만 보고서에서는 모두 **국내중기채권**(위험점수 3)으로 통일 처리.

## 점검 순서
1. **pptx 텍스트 추출** (`python-pptx`): 슬라이드별 테이블 데이터 확인
2. **위험도 교차검증**: 위험도 산출 테이블이 있는 슬라이드 ↔ RA테스트베드 참여 슬라이드 일치 확인
3. **레이아웃 비교**: 레퍼런스 파일과 구조 비교 (shape 위치/크기, 행높이, 셀여백, rowSpan)
4. **파일명 날짜 변경**: pptx 파일명의 `_YYYYMMDD.pptx` → 당일 날짜로 복사 & 이전 파일 삭제
5. **PDF 변환**: `{레시피명}/pdf/` 내 기존 PDF 삭제 → pptx를 PowerPoint COM으로 PDF 생성하여 pdf 폴더에 저장
6. **포털 업로드**: PDF 교체 + 제목 날짜 변경 + 내용 이력 추가 (아래 "포털 업로드 절차" 참조)

## 레이아웃 점검 (레퍼런스 파일과 비교)
- 위험도 산출 테이블: rowSpan이 자산종류 수+현금과 일치하는지 확인
- "동일 자산군 투자한도" 섹션 위치: 산출 테이블과 같은 슬라이드에 있으면 다음 슬라이드로 이동 필요
- 레퍼런스 파일의 shape 위치/크기를 참조값으로 사용

## pptx 수정 시 비표준 패턴 (python-pptx 공식 API에 없는 것)
- 셀여백: `tcPr.set('marL'/'marR'/'marT'/'marB', '36000')` (lxml 직접 조작)
- 셀병합: `tc.set('rowSpan', 'N')`, `tc.set('vMerge', '1')` (연속 행)
- shape 삭제: `shape._element.getparent().remove(shape._element)`
- shape 복사(슬라이드간): `deepcopy(shape._element)` → `slide._element.spTree.append()`

## 서류 파일 관리

### 파일명 날짜 변경 규칙
- 서류 파일명 끝 `_YYYYMMDD.pptx` → 당일 날짜로 복사 & 이전 파일 삭제

### pptx → PDF 변환
PowerPoint COM (`win32com.client`) 사용. 함정:
- `Presentations.Open()`에 **절대경로** 필수, `WithWindow=False`
- `SaveAs(path, 32)` — 32 = ppSaveAsPDF
- `ppt.Quit()`는 PowerPoint가 이미 열려있으면 AttributeError → try/except 필요
- PDF 저장 위치: `{레시피명}/pdf/` — 기존 PDF 삭제 후 새 PDF 저장 (옛 날짜 파일이 남지 않도록)

## 포털 업로드

### 사전 준비 (메인 에이전트)
- PDF 파일 경로 확정 (pptx → PDF 변환 완료 후)
- forUpdate.do URL 확정 (`nttId=`, `algrthSn=` 파라미터)
  - 심사진행현황 → 레시피 → 첨부파일관리 → 서류 행에서 URL 확인
- 새 제목 (파일명 `_YYYYMMDD` → 당일 날짜로)
- 이력 내용 (예: "2026-03-13 위험도 산출 테이블 업데이트")

### 실행

`<TESTBED_BASE_SKILL_DIR>`은 `testbed-base`의 `SKILL.md`가 있는 실제 절대경로다.

```
python "<TESTBED_BASE_SKILL_DIR>/portal_upload.py" \
  --url "{forUpdate_URL}" \
  --file "{pdf_path}" \
  --title "{title_YYYYMMDD}" \
  --content-append "{history_line}"
```

JSON 결과를 보고한다.

### 복수 레시피 병렬 업로드
독립 작업자가 허용된 환경에서는 국내·글로벌·퇴직연금 업로드를 동시에 실행할 수 있다.

### 빠뜨리기 쉬운 것
- **파일명 날짜**: pptx/pdf 파일명 `_YYYYMMDD`를 당일 날짜로 변경 후 변환/업로드
- **제목 날짜**: 포털 제목 필드의 `_YYYYMMDD`도 당일 날짜로 변경

### 수동 폴백 (스크립트 실패 시 — Playwright MCP 사용)

⚠ portal_upload.py 실패 시에만 아래 절차를 사용.
⚠ 핵심 함정: 파일 삭제 시 페이지 리로드 → 폼 필드 초기화. 폼 입력은 삭제 완료 후에.

```
1. browser_navigate → 포털 로그인 → forUpdate.do URL 이동
2. [삭제 전] browser_run_code:
   await page.evaluate(() => { window.confirm = () => true; });
   page.once('dialog', async dialog => { await dialog.accept(); });
3. browser_click 삭제 → 페이지 리로드
4. [리로드 후] browser_file_upload → browser_fill_form (제목, 내용)
5. [제출 전] browser_run_code로 dialog 리스너 재등록
6. 확인 클릭
```
