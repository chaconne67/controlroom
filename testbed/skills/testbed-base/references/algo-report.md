# 11번 알고리즘설명서 PDF

Windows PowerPoint COM 경로를 사용하지 않고, Drive의 기존 PPTX 구조와 FundKeeper 데이터를 조합해 PDF를 만든다.

## 입력과 출력

- 입력: 같은 전략 폴더의 최신 확정 `11번 알고리즘설명서.pptx`와 `12번 투자유니버스.xlsx`.
- 서버 입력: 사용자가 확정한 레시피 검색어로 조회한 전략 데이터 JSON.
- 출력: 기존 파일명 규칙을 따른 날짜 포함 PDF.
- 최종 위치: 입력 PPTX가 있던 Drive 전략 폴더.

원본 PPTX와 XLSX는 raw Office 파일로 내려받고 변경하지 않는다.

## 준비

```bash
ALGO_DIR=/absolute/path/to/testbed-base/scripts/algo-report
WORK_DIR=/tmp/testbed-work.<actual>
```

- 서버 조회 스크립트는 FundKeeper 운영 저장소에서 읽기 조회로 실행한다.
- 검색어가 0개 또는 여러 기본 레시피와 일치하면 중단한다.
- 원격 스크립트와 JSON은 정확한 `/tmp` 경로를 사용하고 작업 뒤 정리한다.

```bash
scp "$ALGO_DIR/fetch_algo_data.py" chaconne@49.247.38.186:/tmp/testbed_fetch_algo_data.py
ssh chaconne@49.247.38.186 \
  "PYTHONPATH=/home/chaconne/fundkeeper DJANGO_SETTINGS_MODULE=fundkeeper.settings.deploy /home/chaconne/fundkeeper/.venv/bin/python /tmp/testbed_fetch_algo_data.py '확정 검색어' /tmp/testbed_algo_data.json"
scp chaconne@49.247.38.186:/tmp/testbed_algo_data.json "$WORK_DIR/algo_data.json"
```

## 구조 추출

```bash
uv run --with python-pptx --with lxml \
  python "$ALGO_DIR/extract_all_shapes.py" \
  "$WORK_DIR/source.pptx" "$WORK_DIR/shapes_manifest.json"

uv run --with python-pptx --with lxml \
  python "$ALGO_DIR/extract_tables.py" \
  "$WORK_DIR/source.pptx" "$WORK_DIR/tables_detail.json"
```

슬라이드 수와 manifest의 슬라이드 수가 같고, 각 shape ID가 고유한지 확인한다.

## semantic_map 계약

`shapes_manifest.json`과 `tables_detail.json`을 읽어 `$WORK_DIR/semantic_map.json`을 만든다. 원본에 없는 문구나 수치를 만들지 않는다.

- `shapes`: 참조 ID별 `shape_id`, `tag`, 테이블 `action`, `role`, `thead_rows`를 기록한다.
- `action=deepcopy`: 원본 표를 그대로 사용한다.
- `action=patch`: 원본 표의 계산 셀만 바꾼다.
- `action=render`: 서버·유니버스 데이터로 표 전체를 만든다.
- 필수 role: `grade_definition`, `investor_type`, `portfolio_type`, `investable_label`, `asset_risk_grade`, `asset_feature`, `portfolio_summary`, `asset_allocation`, `risk_calculation`, `testbed_participation`, `testbed_allocation`.
- `component_order`: `heading`, `text`, `table` 객체를 문서 의미 순서로 나열한다. 모든 `ref`는 `shapes`에 존재해야 한다.
- role은 중복하지 않는다. `thead_rows`는 추출한 원본 서식을 근거로 정한다.

필수 role 누락, 존재하지 않는 ref, 빈 component order가 있으면 다음 단계로 가지 않는다.

## 계산과 PDF 생성

`pipeline_input.json`을 만든다.

```json
{
  "manifest_path": "shapes_manifest.json",
  "semantic_map_path": "semantic_map.json",
  "universe_path": "universe.xlsx",
  "algo_data_path": "algo_data.json",
  "computed_path": "computed.json",
  "output_path": "components.json"
}
```

```bash
uv run --with openpyxl \
  python "$ALGO_DIR/build_and_prepare.py" "$WORK_DIR/pipeline_input.json"
```

`render_input.json`을 만든다.

```json
{
  "work_dir": "/tmp/testbed-work.<actual>",
  "manifest_path": "shapes_manifest.json",
  "components_path": "components.json",
  "output_path": "알고리즘설명서_YYYYMMDD.pdf"
}
```

```bash
uv run --with playwright \
  python "$ALGO_DIR/render_pdf.py" "$WORK_DIR/render_input.json"
```

## 검증과 저장

- PDF가 열리고 1페이지 이상인지 확인한다.
- 표 잘림, 빈 페이지, 깨진 한글, 제목과 본문의 순서를 실제 렌더링 화면에서 확인한다.
- 계산 결과를 `computed.json`, 서버 JSON, 유니버스 XLSX와 대조한다.
- 같은 이름이 Drive 전략 폴더에 없을 때만 PDF를 새 파일로 업로드하고 메타데이터를 재확인한다.
- `source.pptx`, 중간 JSON, HTML은 최종 산출물이 아니므로 성공 확인 뒤 정리한다.
