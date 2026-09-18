# 14번 백테스팅결과분석자료 XLSX

Drive에서 받은 레퍼런스의 구조와 서식을 JSON으로 추출하고, FundKeeper가 만든 CSV를 합쳐 새 XLSX를 만든다.

## 입력과 출력

- 입력: 타깃과 다른 맛의 14번 XLSX, 같은 전략의 11번 PPTX와 12번 XLSX.
- 사용자 결정: 차수, 전략, 타깃 맛, 기간, 레퍼런스 파일.
- 출력: 기존 14번 파일명 패턴과 맛·날짜를 유지한 새 XLSX.
- 최종 위치: 같은 Drive 전략 폴더.

번호와 맛의 대응을 하드코딩하지 않는다. Drive 폴더의 실제 파일명에서 대응을 찾는다.

## 작업 파일 계약

`bt_params.json`에는 최소한 다음 값을 넣는다.

```json
{
  "round": null,
  "folder_name": "선택한 전략 폴더명",
  "recipe_name": "레시피 검색명",
  "flavor": null,
  "start_date": "YYYY-MM-DD",
  "end_date": "YYYY-MM-DD",
  "doc_dir": "/tmp/testbed-work.<actual>",
  "reference_xlsx": "/tmp/testbed-work.<actual>/reference.xlsx",
  "universe_xlsx": "/tmp/testbed-work.<actual>/universe.xlsx",
  "algo_pptx": "/tmp/testbed-work.<actual>/algo.pptx",
  "work_dir": "/tmp/testbed-work.<actual>",
  "pk": null,
  "portfolio_type": null,
  "risk_limit": null,
  "min_risk": null,
  "max_risk": null,
  "universe_tickers": []
}
```

이 JSON은 필드 계약을 보여주는 템플릿이다. 서버와 원본 문서에서 확인한 실제 값으로 모든 `null`과 빈 티커 목록을 채우기 전에는 스크립트를 실행하지 않는다.

- PK는 서버에서 레시피명과 맛으로 조회한다. 0개면 중단하고 여러 개면 이름 목록에서 사용자가 고른다.
- 티커는 투자유니버스의 헤더를 찾아 추출한다. 첫 번째 열이라고 가정하지 않는다.
- 위험자산 한도와 위험도 범위는 11번 PPTX의 `RA테스트베드 참여 현황`에 해당하는 표를 내용으로 찾아 추출한다. 슬라이드 번호와 shape 이름을 고정하지 않는다.
- `doc_dir`은 로컬 임시 디렉토리다. Drive 경로나 Windows 경로를 넣지 않는다.

## 레퍼런스 추출과 서버 데이터

```bash
BT_DIR=/absolute/path/to/testbed-base/scripts/backtest-report
WORK_DIR=/tmp/testbed-work.<actual>

uv run --with openpyxl \
  python "$BT_DIR/bt_extract_spec.py" \
  --ref "$WORK_DIR/reference.xlsx" \
  --output "$WORK_DIR/bt_spec.json"
```

원격 `/home/chaconne/fundkeeper/.venv/bin/python xmodules/test_bed/test_bed.py 백테스트 --help`에서 `--tickers` 지원을 확인한 뒤 승인된 기간과 PK로 실행한다. 시스템 `python`을 사용하지 않는다. 결과는 원격 임시 디렉토리에 만들고 다음 파일을 로컬 작업 디렉토리로 받는다.

- `{pk}_일별수익률.csv`
- `{pk}_월별수익률.csv`
- `{pk}_종목별비중.csv`
- `{pk}_자산종류별비중.csv`
- `{pk}_리밸런싱내역.csv`
- `{pk}_asset_map.json`

파일이 하나라도 없거나 CSV가 비어 있으면 조립하지 않는다.

## 조립과 렌더링

```bash
uv run --with openpyxl --with pandas \
  python "$BT_DIR/bt_assemble.py" \
  --spec "$WORK_DIR/bt_spec.json" \
  --params "$WORK_DIR/bt_params.json" \
  --asset-map "$WORK_DIR/${PK}_asset_map.json" \
  --work-dir "$WORK_DIR" \
  --output "$WORK_DIR/bt_render_input.json"

uv run --with openpyxl \
  python "$BT_DIR/bt_render.py" \
  --input "$WORK_DIR/bt_render_input.json" \
  --output "$WORK_DIR/$OUTPUT_NAME" \
  --ref "$WORK_DIR/reference.xlsx" \
  --spec "$WORK_DIR/bt_spec.json"
```

`PK`와 `OUTPUT_NAME`은 앞에서 확정한 실제 값이다. 빈 값으로 실행하지 않는다.

## 검증과 저장

```bash
uv run --with openpyxl --with pandas \
  python "$BT_DIR/verify_data.py" \
  --params "$WORK_DIR/bt_params.json" \
  --asset-map "$WORK_DIR/${PK}_asset_map.json" \
  --work-dir "$WORK_DIR" \
  --render-input "$WORK_DIR/bt_render_input.json" \
  --target "$WORK_DIR/$OUTPUT_NAME" \
  --output "$WORK_DIR/verify_data.json"

uv run --with openpyxl \
  python "$BT_DIR/verify_structure.py" \
  --ref "$WORK_DIR/reference.xlsx" \
  --target "$WORK_DIR/$OUTPUT_NAME" \
  --output "$WORK_DIR/verify_structure.json"

uv run --with openpyxl \
  python "$BT_DIR/verify_style.py" \
  --ref "$WORK_DIR/reference.xlsx" \
  --target "$WORK_DIR/$OUTPUT_NAME" \
  --spec "$WORK_DIR/bt_spec.json" \
  --output "$WORK_DIR/verify_style.json"
```

- 세 검증 결과에 오류가 없어야 한다.
- LibreOffice로 실제 XLSX를 열어 수식, 차트, 날짜축, 한글, 열 너비를 확인한다.
- 같은 이름이 Drive 전략 폴더에 없을 때만 raw XLSX로 업로드하고 메타데이터를 재확인한다.
