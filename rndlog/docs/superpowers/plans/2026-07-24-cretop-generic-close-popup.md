# CRETOP 비정형 닫기 팝업 구현 계획

**목표:** 알려진 오류 복구가 실패한 마지막 경계에서만 하단 우측 단일 닫기형 팝업을 영상으로 판정하고, 팝업 소멸과 기존 CRETOP 준비 경로 복귀가 확인된 경우에만 처리를 재개한다.

**구조:** `CommandRunner._handle_company_exception()`이 분기 순서와 최종 결과를 계속 소유한다. 새 순수 함수 `detect_generic_footer_close_popup()`은 좌표만 계산한다. 기존 `_recover_generic_popup_to_smart_search()`는 회사 처리에서 중앙 확인형을 먼저, 닫기형을 다음으로 선택한다. 사전 준비용 복구는 닫기형만 허용하고 기존 `_ensure_ready_fast()`, `_go_home_fast()`, `_enter_smart_search_from_landing()`으로 복귀한다.

**기술:** Python, Pillow, pytest, 기존 `mss`·`pyautogui`

## 작업 1: 영상 검출 계약

**파일**

- 수정: `scripts/cretop_agent.py`
- 테스트: `scripts/test_cretop_agent.py`

### RED

- 실제 장애 캡처에서 `action_type="footer_close"`와 하단 우측 클릭 좌표가 반환되는 테스트를 추가한다.
- 일반 흰 모달과 본문 선택 상태 모달을 모두 검출하는 합성 테스트를 추가한다.
- 다음 이미지는 `None`이어야 한다.
  - 정상 화면
  - `1920x1080`이 아닌 화면
  - 암막이 없는 화면
  - 우측 후보가 두 개인 화면
  - 푸터나 중앙 모달 조건이 없는 화면

실행:

```bash
uv run pytest -q scripts/test_cretop_agent.py -k generic_footer_close
```

기대: 함수 부재로 새 테스트 실패.

### GREEN

- `detect_generic_footer_close_popup(path)`을 추가한다.
- 밝은 푸터 연결 영역, 주변 암막 비율, 우측 파란 픽셀 군집을 제한한다.
- 파란 글자의 가까운 조각만 하나의 후보로 묶는다.
- 단일 후보일 때만 다음 증거를 반환한다.
  - `action_type`
  - `image_size`
  - `panel_box`
  - `footer_box`
  - `action_box`
  - `click_point`

실행:

```bash
uv run pytest -q scripts/test_cretop_agent.py -k 'generic_footer_close or generic_confirm_popup'
```

기대: 새 검출 테스트와 기존 중앙 확인형 테스트 통과.

## 작업 2: 같은 회사 복구 경계 병합

**파일**

- 수정: `scripts/cretop_agent.py`
- 테스트: `scripts/test_cretop_agent.py`

### RED

- 회사 처리에서 중앙 확인형 미검출 뒤 닫기형을 선택하는 테스트를 추가한다.
- 클릭 후 같은 닫기형 구조가 사라지지 않으면 재클릭 후 실패하는 기존 클릭 계약을 고정한다.
- 닫기 성공 뒤 기존 화면 분류와 스마트 검색 복귀를 사용하는지 확인한다.
- 기존 중앙 확인형이 검출되면 닫기형 검출을 호출하지 않는지 확인한다.
- 두 유형이 `generic_popup_recovery_used` 예산을 공유하는지 확인한다.

실행:

```bash
uv run pytest -q scripts/test_cretop_agent.py -k 'generic_popup or footer_close'
```

기대: 닫기형 선택과 복구가 없어 새 테스트 실패.

### GREEN

- 범용 팝업 검출 선택을 기존 `_recover_generic_popup_to_smart_search()` 안에 병합한다.
- 검출 유형에 맞는 동일 검출기를 클릭 후 소멸 확인에도 사용한다.
- 기존 화면 분류와 스마트 검색 복귀 코드는 공통으로 유지한다.
- `_handle_company_exception()`의 기존 회사별 재시도 정책은 변경하지 않는다.

실행:

```bash
uv run pytest -q scripts/test_cretop_agent.py -k 'generic_popup or footer_close or company_exception'
```

기대: 새 분기와 기존 회사 처리 회귀 테스트 통과.

## 작업 3: 사전 준비 마지막 복구 병합

**파일**

- 수정: `scripts/cretop_agent.py`
- 테스트: `scripts/test_cretop_agent.py`

### RED

- 사전 준비의 미분류 화면에서 닫기형만 판정하는 테스트를 추가한다.
- 알려진 세션 복구가 실패한 뒤 닫기형 복구가 실행되는 테스트를 추가한다.
- 중앙 확인형만 있는 사전 준비 화면은 계속 중단하는 테스트를 유지한다.
- 유료 서비스, 반복 만료, OOM, 캡처 실패에서는 새 분기를 호출하지 않는지 확인한다.
- 닫기 성공 뒤 `_ensure_ready_fast()`, `_go_home_fast()`, `_enter_smart_search_from_landing()` 순서를 확인한다.

실행:

```bash
uv run pytest -q scripts/test_cretop_agent.py -k 'preflight and (generic or footer)'
```

기대: 기존 사전 준비 제외 규칙 때문에 새 테스트 실패.

### GREEN

- 사전 준비용 닫기형 복구를 `_handle_company_exception()`의 마지막 실패 경계에 병합한다.
- 사전 준비에서는 `detect_generic_confirm_popup()`을 호출하지 않는다.
- 복구 결과는 기존 `retry_company` 계약에 맞춰 `ready`, `home_reset`, `smart_search_ready`를 반환한다.
- 실패 시 원래 분류·오류와 새 영상 복구 오류를 모두 보존한다.

실행:

```bash
uv run pytest -q scripts/test_cretop_agent.py -k 'preflight or generic_popup or footer_close'
```

기대: 새 사전 준비 복구와 기존 정책 테스트 통과.

## 작업 4: 전체 검증과 리뷰

### 로컬 검증

```bash
uv run pytest -q scripts/test_cretop_agent.py scripts/test_cretop_click_marker_retry.py scripts/test_cretop_detail_collection.py scripts/test_cretop_report_pipeline.py
uv run ruff check scripts/cretop_agent.py scripts/test_cretop_agent.py
uv run python -m py_compile scripts/cretop_agent.py
```

기대: 모두 성공.

### 코드 리뷰 루프

- 승인 범위의 로컬 diff만 리뷰한다.
- 실행 계약을 깨는 검증된 finding만 수정한다.
- 수정 후 같은 집중 테스트와 전체 CRETOP 검증을 다시 실행한다.
- finding이 없을 때 종료한다.

## 작업 5: 원격 SSP 검증과 재실행

### 원격 사전 검증

- 승인된 배포 명령으로 로컬 코드와 원격 코드의 SHA-256 일치를 확인한다.
- `remote-preflight`를 실행한다.
- 다음 증거가 모두 있어야 통과한다.
  - `action_type="footer_close"`
  - 클릭 전·후 캡처
  - 팝업 소멸
  - 로그인 준비
  - 홈 초기화
  - 스마트 검색 marker 확인

### 추가 1000건 재실행

- 원격 사전 검증 성공 후에만 기존 `batch-script-only-collect` 경로로 추가 1000건을 실행한다.
- 실행 ID는 기존 실패 실행과 구분되는 새 ID를 사용한다.
- 이번 요청은 모니터링이 필요 없으므로 시작 결과와 실행 ID만 확인한다.

### 기록

- 실브라우저 성공 후 CRETOP 자동화 스킬의 비정형 팝업 계약을 갱신한다.
- 장애 원인, 탐지 조건, 원격 검증 결과를 GBrain에 기록한다.
- 코드·테스트·문서·스킬 변경을 검토한 뒤 커밋한다.

## 실행 결과

- 영상 검출, 분기, 최신 재캡처, 증거 보존 테스트를 추가했다.
- 첫 원격 검증에서 독립 `preflight()`의 공통 예외처리기 우회가 확인됐다.
- 독립 진입점을 공통 예외처리기에 병합하고 회귀 테스트를 추가했다.
- 최종 로컬 검증: CRETOP 테스트 `180 passed`, Ruff와 Python 컴파일 통과.
- 최종 원격 검증: 닫기 `(1213,878)`, 팝업 소멸, 재로그인, 홈, 스마트 검색 확인.
- 추가 1000건 실행 ID: `20260724_cretop_additional1000_footer_recovery`
- 사용자 요청에 따라 추가 1000건은 시작 후 진행 모니터링하지 않는다.
