# 12번 투자유니버스 ETF 확인과 XLSX 반영

Drive의 투자유니버스를 조회·검증하고 새 XLSX를 만든다. 원본이나 Drive의 21번 파일을 직접 덮어쓰지 않는다.

## 입력과 출력

- 입력: 전략 폴더의 12번 투자유니버스 XLSX.
- 선택 입력: 투자유니버스 시트를 함께 갱신할 21번 리밸런싱 XLSX.
- 출력: 갱신된 12번 XLSX와, 요청된 경우 투자유니버스 시트가 갱신된 새 21번 XLSX.
- 최종 위치: 입력 파일이 있던 Drive 전략 폴더.

## universe.json 계약

Drive에서 받은 로컬 임시 경로만 metadata에 넣는다.

```json
{
  "metadata": {
    "strategy": "전략명",
    "source_file": "/tmp/testbed-work.<actual>/source-universe.xlsx",
    "target_file": "/tmp/testbed-work.<actual>/source-rebalancing.xlsx",
    "target_sheet": "투자유니버스",
    "col_mapping": {
      "isin": 1,
      "name": 2,
      "market": 3,
      "asset_class": 4,
      "asset_type": 5,
      "risk_grade": 6,
      "risk_score": 7,
      "is_risk_asset": 8
    }
  },
  "items": []
}
```

각 item은 `row`, `ticker`, `current`, `lookup`, `final`을 가진다. `current`, `lookup`, `final`의 필드는 `isin`, `name`, `market`, `asset_class`, `asset_type`, `risk_grade`, `risk_score`, `is_risk_asset`이다. `lookup`에는 필요하면 `base_index`와 `risk_grade_name`을 추가한다.

- 열은 헤더 내용으로 확인하고 `col_mapping`에 기록한다. 위 번호는 기존 계약을 보여주는 기본 구조이며 실제 파일이 다르면 헤더가 우선한다.
- 티커는 비고/티커 헤더의 값으로 만들고 문자열로 보존한다. 국내 6자리 티커의 앞자리 0을 잃지 않는다.
- 빈 티커 행은 제외한다. item이 0개면 중단한다.
- 중복 티커와 중복 ISIN은 사용자가 확정하기 전까지 병합하거나 삭제하지 않는다.
- `final`만 XLSX에 쓴다. `lookup` 결과를 자동 확정하지 않는다.

## 조회와 판정

```bash
ETF_DIR=/absolute/path/to/testbed-base/scripts/etf
```

- 국내 6자리 티커 또는 `KR` ISIN은 `lookup_funetf.py`로 조회한다.
- 글로벌 티커는 `lookup_isin.py`로 조회하고 ISIN 체크디짓과 OpenFIGI 역조회 결과를 함께 확인한다.
- 조회 결과가 없거나 출처가 서로 다르면 `final`을 비워 두고 불일치 목록에 남긴다.
- 자산종류와 위험자산 여부는 기존 전략의 분류 체계, 기초지수, 시장, 위험등급을 함께 보고 확정한다. 새 자산종류가 필요하면 승인 계획 밖의 DB 변경으로 이어질 수 있으므로 사용자에게 보고한다.
- 웹사이트 구조 변경이나 조회 실패를 임의 값으로 메우지 않는다.

## 새 XLSX 생성

먼저 dry-run으로 변경 목록을 확인한다.

```bash
uv run --with openpyxl \
  python "$ETF_DIR/write_universe.py" \
  "$WORK_DIR/universe.json" \
  --output-xlsx "$WORK_DIR/$UNIVERSE_OUTPUT" \
  --dry-run
```

검증 후 같은 명령에서 `--dry-run`만 빼 새 12번 XLSX를 만든다. 기존 파일이 있으면 스크립트가 중단해야 한다.

21번의 투자유니버스 시트도 갱신할 때는 새 12번 결과를 `metadata.source_file`로, Drive에서 받은 21번 원본을 `metadata.target_file`로 지정한다.

```bash
uv run --with openpyxl \
  python "$ETF_DIR/copy_universe_sheet.py" \
  "$WORK_DIR/universe.json" \
  --output-xlsx "$WORK_DIR/$REBAL_OUTPUT" \
  --dry-run
```

검증 후 `--dry-run`을 빼 새 21번 XLSX를 만든다. 두 스크립트 모두 Drive 원본을 수정하면 안 된다.

## DB와 Drive 경계

- 투자유니버스 파일 생성의 성공 조건은 Drive 업로드와 메타데이터 재확인이다.
- `ticker_list` DB 동기화는 이 파일 생성 경로에 포함하지 않는다.
- DB 동기화가 필요하면 FundKeeper 작업으로 별도 범위를 정하고 dry-run 차이, 공유 전략 영향, 신규 종목 기본값을 제시한 뒤 승인받는다.
- 새 12번과 새 21번은 각각 같은 이름 충돌을 확인한 뒤 raw XLSX로 전략 폴더에 업로드한다.
