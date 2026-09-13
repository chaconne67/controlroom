# FundKeeper TestBed 모듈 개선 사항

**대상**: `/home/work/fundkeeper/xmodules/test_bed/test_bed.py`
**작성일**: 2026-03-20
**배경**: 백테스팅결과분석자료 워크플로우 점검 중 발견된 서버 측 개선 필요 사항

---

## 0. [버그] parquet 캐시에서 tickers JSON 미파싱

**파일**: `/home/work/fundkeeper/simulation/fetch_price.py` 265행 `get_master_df_fromDB()`

**현재**: parquet 캐시에서 읽을 때 `tickers` 컬럼이 JSON 문자열 그대로 반환됨
```python
def get_master_df_fromDB(self, pk):
    path = f'/home/work/fundkeeper/data/masterdf_cache/portfolio_{pk}.parquet'
    if os.path.exists(path):
        return pd.read_parquet(path)  # ← tickers가 '["069500","102110"]' 문자열 그대로
    # ... DB 경로에서는 json.loads() 처리가 있음
```

**증상**: `get_alltickers()`에서 문자열을 문자 단위로 순회 → `'"', ',', '0', '1', ...`이 티커로 인식 → `get_main_df()`에서 `KeyError`
```
KeyError: 'None of [Index([\'"\'  \',\', \'0\', \'1\', ...], dtype=\'object\')] are in the [columns]'
```

**실제 데이터 확인**:
```python
df = pd.read_parquet('data/masterdf_cache/portfolio_1336.parquet')
type(df['tickers'].iloc[0])  # <class 'str'>
df['tickers'].iloc[0]        # '["442550","153130","214980","CASH",...]'
```

**수정**: parquet 경로에서도 tickers JSON 파싱 추가
```python
def get_master_df_fromDB(self, pk):
    path = f'/home/work/fundkeeper/data/masterdf_cache/portfolio_{pk}.parquet'
    if os.path.exists(path):
        df = pd.read_parquet(path)
        if 'tickers' in df.columns:
            df['tickers'] = df['tickers'].apply(
                lambda x: json.loads(x) if isinstance(x, str) else x
            )
        return df
    # ... 기존 DB 경로 코드
```

---

## 1. ~~TestBed.__init__ 기간 하드코딩~~ ✅ 적용 완료

**현재**: `start_date`, `end_date`가 `__init__`에 고정값으로 설정됨
```python
self.start_date = '2024-01-01'
self.end_date = '2025-09-30'
```

**문제**: 외부에서 기간을 변경하려면 인스턴스 생성 후 속성을 직접 덮어써야 함
```python
tb = TestBed()
tb.start_date = '2025-03-01'  # 이런 식으로 해야 함
tb.end_date = '2026-02-28'
```

**제안**: `__init__` 파라미터로 받을 수 있게 변경
```python
def __init__(self, start_date=None, end_date=None):
    self.start_date = start_date or '2024-01-01'
    self.end_date = end_date or '2025-09-30'
```

---

## 2. ~~pool(투자유니버스) 데이터 관리~~ ✅ 적용 완료

**현재 구조**:
- `files/xls/`에 `pool_kr.xlsx`, `pool_us.xlsx`, `pool_svr.xlsx` 존재
- `get_universe()`가 포트폴리오명 키워드('국내'→`pool_kr.csv`, '글로벌'→`pool_us.csv`, '퇴직'→`pool_svr.csv`)를 `files/csv/`에서 고정 선택
- `pool_kr.csv`만 존재하고 `pool_us.csv`, `pool_svr.csv`는 미생성 상태일 수 있음

**문제**:
- 테스트베드 서류 중 "투자유니버스자료" 엑셀이 정본인데, 서버의 `pool_*.xlsx/csv`와 동기화 메커니즘이 없음
- xlsx를 업데이트해도 csv가 자동 갱신되지 않아 구버전 pool로 시뮬레이션 위험
- 외부에서 pool 파일 경로를 지정할 수 없음

**제안** (우선순위 순):
1. `get_universe()` 진입 시 xlsx→csv 자동 변환 (xlsx가 csv보다 최신이면 재생성)
2. 또는 xlsx를 직접 `pd.read_excel()`로 읽기 (csv 중간 단계 제거)
3. pool 파일 경로를 파라미터로 받을 수 있게 변경:
```python
def __init__(self, start_date=None, end_date=None, pool_path=None):
    # pool_path가 주어지면 get_universe()에서 해당 파일 사용
```
4. 투자유니버스자료 엑셀이 변경될 때 서버 pool을 갱신하는 절차/스크립트 마련

---

## 3. ~~CSV 출력 경로 고정~~ ✅ 적용 완료

**현재**: `main(pk)` 실행 시 CSV가 `files/csv/{pk}_*.csv`에 고정 출력

**문제**: 출력 디렉토리를 지정할 수 없어, 결과를 `/tmp/` 등으로 내보내려면 파일을 별도로 복사해야 함

**제안**: 출력 디렉토리 파라미터 추가
```python
def main(self, pk, output_dir=None):
    output_dir = output_dir or os.path.join(self.base_dir, 'files', 'csv')
```

---

## 4. ~~CLI 인터페이스 부재 (TestBed 클래스)~~ ✅ 적용 완료

**현재**: TestBed2는 CLI 지원 (`python test_bed.py <command> --schedule <id>`)이 있지만, TestBed(백테스트 시뮬레이션)는 CLI가 없음. Python 코드로만 호출 가능.

**제안**: TestBed도 CLI 커맨드 추가
```bash
python test_bed.py 백테스트 --pk 1336 --start 2025-03-01 --end 2026-02-28 [--pool /tmp/pool.csv] [--output /tmp/]
```

---

---

## 우선순위

| 순위 | 항목 | 이유 |
|------|------|------|
| 1 | 기간 파라미터화 | 매 실행마다 필요, 가장 빈번 |
| 2 | pool 데이터 관리 | 투자유니버스 정합성 — 현재 pool_kr.xlsx 없이 운영 중이므로 시급 |
| 3 | CLI 인터페이스 | SSH 원격 실행 편의성, 1+2 반영 후 자연스럽게 추가 |
| 4 | 출력 디렉토리 지정 | 파일 관리 편의 |

## 목표 상태

서버 개선 완료 후 로컬 워크플로우는 아래처럼 단순해져야 함:
```bash
# SSH로 한 줄 실행
ssh root@49.247.38.186 "cd /home/work/fundkeeper/xmodules/test_bed && python test_bed.py 백테스트 --pk 1336 --start 2025-03-01 --end 2026-02-28 --output /tmp/"

# 결과 다운로드
scp root@49.247.38.186:/tmp/bt_*.csv ~/tmp/
scp root@49.247.38.186:/tmp/bt_asset_map.json ~/tmp/
```

pool 관리, 기간 설정, 출력 경로 등 모든 것이 서버 모듈 내부에서 해결되고, 로컬은 호출+다운로드만 담당.
