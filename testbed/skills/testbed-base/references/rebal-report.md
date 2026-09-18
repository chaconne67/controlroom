# 21번 리밸런싱 발생내역 XLSX

Drive의 기존 20번·21번 Office 파일을 로컬 임시본으로 내려받고, TestBed2 데이터로 새 21번 XLSX를 만든다.

## 입력과 출력

- 증분 갱신 입력: 최신 확정 21번 XLSX와 선택한 `schedule_id`.
- 전체 재구성 입력: 20번 운용개시 현황 XLSX, 21번 템플릿 XLSX, 선택한 `schedule_id`.
- 출력: 기존 21번 파일명 패턴과 당일 날짜를 따른 새 XLSX.
- 최종 위치: 입력 21번 파일이 있던 Drive 전략 폴더.

20번과 21번은 `fetch(download_raw_file=true, include_base64=false)`로 내려받고 openpyxl로 실제 열리는지 먼저 확인한다. Drive 스트리밍 캐시나 Downloads 파일을 사용하지 않는다.

## 승인 경계

`list-schedules`는 조회다. `fetch` 경로는 실제 잔고를 조회해 `TestBedBalance`를 저장할 수 있으므로, 작업 시작 계획에 운영 DB 저장을 명시해 승인받은 경우에만 실행한다.

## 공통 데이터 수집

```bash
REBAL_DIR=/absolute/path/to/testbed-base/scripts/rebal-report
WORK_DIR=/tmp/testbed-work.<actual>

FUNDKEEPER_HOST=chaconne@49.247.38.186 \
  uv run python "$REBAL_DIR/fetch_rebalancing_data.py" \
  list-schedules --recipe kr
```

레시피와 스케줄을 확정한 뒤 승인 범위에 DB 저장이 있으면 다음을 실행한다.

```bash
FUNDKEEPER_HOST=chaconne@49.247.38.186 \
  uv run python "$REBAL_DIR/fetch_rebalancing_data.py" \
  fetch --recipe kr --schedule-id "$SCHEDULE_ID" --work-dir "$WORK_DIR"
```

JSON에 `schedule`, `model_portfolio`, `balance`, `trade_history`, `pk_groups` 키가 모두 있는지 확인한다. 모델포트폴리오·잔고가 비어 있거나 비중 합계가 계약 범위를 벗어나면 XLSX를 만들지 않는다. 거래가 없을 수 있으므로 빈 `trade_history`만으로 실패 처리하지 않는다.

## 증분 갱신

기존 21번에 새 회차를 추가할 때 사용한다.

```bash
uv run --with openpyxl \
  python "$REBAL_DIR/update_rebalancing_report.py" \
  --recipe kr \
  --schedule-id "$SCHEDULE_ID" \
  --work-dir "$WORK_DIR" \
  --source-xlsx "$WORK_DIR/source-21.xlsx" \
  --output-xlsx "$WORK_DIR/$OUTPUT_NAME" \
  --dry-run
```

dry-run의 오류와 경고를 확인한 뒤 `--dry-run`만 빼 새 파일을 만든다. 같은 기준일 블록은 삭제 후 다시 쓰되, 원본 파일 자체는 바꾸지 않는다.

## 전체 재구성

운용개시 블록과 회차 블록을 다시 구성해야 할 때 사용한다.

```bash
uv run --with openpyxl \
  python "$REBAL_DIR/prepare_local_data.py" \
  "$WORK_DIR/source-20.xlsx" "$WORK_DIR"
```

이 명령은 `existing_uni.json`, `opening_block.json`, `sheet_meta.json`을 만든다. 이어서 `fetch_universe.py`를 FundKeeper 서버의 `.venv/bin/python manage.py shell`에서 읽기 조회로 실행해 `uni_full.json`, `extra_db.json`, 계좌 메타데이터를 준비한다. 시스템 `python`을 사용하지 않는다. 서버 계좌번호와 운용금액이 `sheet_meta.json`과 다르면 중단한다.

DB 자산종류와 문서 자산종류가 다르면 `$WORK_DIR/asset_type_fix.json`에 검토한 매핑만 기록한다. 추측한 보정값을 넣지 않는다.

```bash
uv run --with openpyxl \
  python "$REBAL_DIR/build_rebal_report.py" \
  "$WORK_DIR" \
  "$WORK_DIR/source-21-template.xlsx" \
  "$WORK_DIR/$OUTPUT_NAME" \
  "rebalancing_data_${SCHEDULE_ID}.json" \
  "$RDAY" \
  "$REASON"
```

## 비자명한 서식 계약

- MP 데이터는 2행부터, 포트변경 데이터는 6행부터, 잔고 데이터는 5행부터 다룬다.
- 헤더 행 전체를 삭제하지 않는다. 데이터 행만 교체한다.
- 잔고 블록에는 목표 종목을 모두 포함하고 미보유 목표 종목은 수량 0으로 남긴다.
- 자산 열을 삽입·삭제한 뒤 합계, 위험자산비중, 위험도, 사유, 확인 영역의 병합 범위를 다시 확인한다.
- 거래 실행일은 `rday` 주변 실제 `TradeHistory`의 마지막 거래일로 확인한다.

## 검증과 저장

- 모든 그룹의 MP 합계가 100%인지 확인한다.
- 실제 잔고비중 합계, 위험자산비중, 위험도 수식과 범위를 확인한다.
- 운용개시 첫 종목과 각 회차 첫 종목이 누락되지 않았는지 확인한다.
- `verify_pass_criteria.py`로 11번 PPTX와 새 21번 XLSX를 함께 검사한다.
- LibreOffice로 시트, 병합, 수식, 날짜, 한글을 실제 확인한다.
- 같은 이름이 Drive 전략 폴더에 없을 때만 raw XLSX로 업로드하고 메타데이터를 재확인한다.
