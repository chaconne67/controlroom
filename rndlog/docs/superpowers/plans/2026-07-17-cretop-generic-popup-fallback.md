# CRETOP Generic Popup Fallback Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 기존 정상 경로와 기존 오류 분기를 바꾸지 않고, 회사 처리 예외의 마지막 중단 직전에 영상 기반 단일 확인 팝업 복구를 한 번 실행한다.

**Architecture:** 기존 `CommandRunner._handle_company_exception()`이 오류 처리 순서와 결과 결정을 계속 소유한다. Pillow 기반 순수 영상 판정 함수가 중앙의 흰 팝업과 하단의 검은 단일 버튼을 찾아 좌표만 반환하고, 기존 에러처리기는 버튼 클릭·팝업 소멸·화면 재판정·스마트검색 복귀를 검증한 뒤 같은 회사를 검색부터 한 번 재시도한다. `preflight` 문맥과 기존에 성공한 오류 분기는 범용 단계에 진입하지 않는다.

**Tech Stack:** Python 3.13, Pillow, pytest, 기존 `mss`/`pyautogui` 원격 브라우저 경로

---

## 파일 구조

- Modify: `scripts/cretop_agent.py`
  - Pillow 선택적 import를 독립시킨다.
  - 영상 팝업 판정 함수를 추가한다.
  - 기존 `_handle_company_exception()`의 마지막 중단 단계에 범용 복구를 병합한다.
  - `preflight`와 `company` 호출 문맥, 회사별 사용 여부를 전달한다.
- Modify: `scripts/test_cretop_agent.py`
  - 영상 판정, 기존 분기 보존, 프리플라이트 제외, 회사당 1회 재시도를 검증한다.
- Modify: `/home/chaconne/.codex/skills/cretop-automation/SKILL.md`
  - 실브라우저 최종 경로가 검증된 뒤에만 최종 오류처리 선언을 교체한다.

### Task 1: Pillow 기반 단일 확인 팝업 판정

**Files:**
- Modify: `scripts/cretop_agent.py`
- Test: `scripts/test_cretop_agent.py`

- [ ] **Step 1: 실패하는 영상 판정 테스트 작성**

```python
def test_detect_generic_confirm_popup_returns_button_center(tmp_path):
    image = PILImage.new("RGB", (1920, 1080), (51, 51, 51))
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle((800, 498, 1120, 656), 8, fill="white")
    draw.rounded_rectangle((820, 588, 1100, 636), 8, fill=(36, 39, 48))
    path = tmp_path / "popup.png"
    image.save(path)

    detected = agent.detect_generic_confirm_popup(path)

    assert detected["panel_box"] == {"left": 800, "top": 498, "right": 1120, "bottom": 656}
    assert detected["button_box"] == {"left": 820, "top": 588, "right": 1100, "bottom": 636}
    assert detected["click_point"] == {"x": 960, "y": 612}
```

정상 화면, 후보 없음, 버튼 두 개, 해상도 불일치도 각각 `None`을 반환하는 테스트를 함께 작성한다.

- [ ] **Step 2: 실패 확인**

Run: `uv run pytest -q scripts/test_cretop_agent.py -k generic_confirm_popup`

Expected: `AttributeError: module 'scripts.cretop_agent' has no attribute 'detect_generic_confirm_popup'`

- [ ] **Step 3: 최소 영상 판정 구현**

```python
try:
    from PIL import Image
except Exception:
    Image = None


def detect_generic_confirm_popup(path: str | Path) -> dict[str, Any] | None:
    if Image is None:
        return None
    with Image.open(path) as source:
        image = source.convert("RGB")
    if image.size != (1920, 1080):
        return None
    # 중앙 영역의 근백색 연결 영역을 패널 후보로 제한한다.
    # 패널 하단 내부의 어두운색 또는 파란 선택색 연결 영역을 버튼 후보로 제한한다.
    # 패널과 버튼이 각각 하나일 때만 경계 상자와 버튼 중심을 반환한다.
```

연결 영역 계산은 같은 파일의 작은 순수 보조 함수로 구현한다. 새 이미지 처리 패키지는 추가하지 않는다.

- [ ] **Step 4: 실제 실패 캡처 좌표 확인**

Run:

```bash
uv run python -c "from scripts.cretop_agent import detect_generic_confirm_popup; print(detect_generic_confirm_popup('docs/cretop/detail_collection/cretop_pending100_20260717_01/company_exception_cretop_pending100_20260717_01_021_7965500848_20260717_014012.png'))"
```

Expected: 패널 약 `(800, 498)-(1120, 656)`, 버튼 약 `(820, 588)-(1100, 636)`, 클릭 중심 `(960, 612)`.

- [ ] **Step 5: 집중 테스트 통과 확인**

Run: `uv run pytest -q scripts/test_cretop_agent.py -k generic_confirm_popup`

Expected: 관련 테스트 전체 PASS.

- [ ] **Step 6: 커밋**

```bash
git add scripts/cretop_agent.py scripts/test_cretop_agent.py
git commit -m "feat(cretop): detect generic confirmation popup"
```

### Task 2: 기존 에러처리기의 마지막 범용 복구 단계

**Files:**
- Modify: `scripts/cretop_agent.py`
- Test: `scripts/test_cretop_agent.py`

- [ ] **Step 1: 실패하는 에러처리 테스트 작성**

```python
def test_company_exception_uses_generic_popup_only_after_existing_recovery_fails(monkeypatch):
    result = runner._handle_company_exception(
        exc=agent.MarkerTimeoutError("marker missing", last_text="CRETOP 기업 총 1건"),
        item_run_id="generic-001",
        business_number="7965500848",
        interval_seconds=0,
        timeout_seconds=1,
        expired_page_recovery_used=False,
        phase="company",
        generic_popup_recovery_used=False,
    )
    assert result["action"] == "retry_company"
    assert result["generic_popup_recovery_used"] is True
    assert result["smart_search_ready"]["ok"] is True
```

다음 계약을 별도 테스트로 고정한다.

- 기존 오류 복구가 성공하면 영상 판정을 호출하지 않는다.
- `phase="preflight"`이면 영상 판정을 호출하지 않는다.
- 유료 서비스와 반복 만료는 영상 판정을 호출하지 않는다.
- 빈 본문과 본문 복사 실패는 영상 판정을 호출하지 않는다.
- `generic_popup_recovery_used=True`이면 두 번째 범용 복구를 실행하지 않는다.
- 팝업 후보가 없거나 클릭 후 남아 있으면 기존 중단 결과를 유지한다.

- [ ] **Step 2: 실패 확인**

Run: `uv run pytest -q scripts/test_cretop_agent.py -k 'generic_popup or preflight'`

Expected: 새 매개변수와 범용 복구 결과가 없어 FAIL.

- [ ] **Step 3: 범용 복구 동작 구현**

```python
def _recover_generic_popup_to_smart_search(
    self,
    *,
    screenshot: dict[str, Any],
    item_run_id: str,
    interval_seconds: float,
    timeout_seconds: float,
) -> dict[str, Any]:
    detected = detect_generic_confirm_popup(screenshot["screenshot"])
    if detected is None:
        raise CretopRuntimeError("generic confirmation popup not detected")
    point = detected["click_point"]
    click = self.desktop.click(point["x"], point["y"])
    after = self._capture_desktop(f"generic_popup_after_{item_run_id}")
    if detect_generic_confirm_popup(after["screenshot"]) is not None:
        raise CretopRuntimeError("generic confirmation popup remained after click")
    copied = self.desktop.copy_text(PAGE_COPY_POINT["x"], PAGE_COPY_POINT["y"])
    # 기존 화면 분류와 기존 스마트검색 복귀 함수만 사용한다.
```

`_handle_company_exception()`에는 `phase`와 `generic_popup_recovery_used`를 전달한다. 기존 분기 성공 시 즉시 반환하고, 회사 문맥의 `unclassified` 또는 기존 복구 예외에서만 위 복구를 실행한다.

- [ ] **Step 4: 집중 테스트 통과 확인**

Run: `uv run pytest -q scripts/test_cretop_agent.py -k 'company_exception or generic_popup or preflight'`

Expected: 관련 테스트 전체 PASS.

- [ ] **Step 5: 커밋**

```bash
git add scripts/cretop_agent.py scripts/test_cretop_agent.py
git commit -m "fix(cretop): recover unknown confirmation popup"
```

### Task 3: 회사당 1회 재시도 연결과 회귀 검증

**Files:**
- Modify: `scripts/cretop_agent.py`
- Test: `scripts/test_cretop_agent.py`
- Modify after runtime verification: `/home/chaconne/.codex/skills/cretop-automation/SKILL.md`

- [ ] **Step 1: 실패하는 배치 재시도 테스트 작성**

```python
def test_collect_batch_retries_company_once_after_generic_popup(tmp_path):
    # 첫 호출은 범용 복구 성공, 두 번째 호출은 정상 수집으로 구성한다.
    result = runner.collect_batch_fast(str(payload_path))
    assert collected == ["7965500848", "7965500848"]
    assert handled_phases == ["company"]
    assert result["items"][0]["ok"] is True
```

프리플라이트 호출은 `phase="preflight"`, 회사 호출은 `phase="company"`를 전달하는지 검증한다. 같은 회사의 두 번째 실패에는 `generic_popup_recovery_used=True`가 전달되고 범용 복구가 반복되지 않는 테스트도 추가한다.

- [ ] **Step 2: 실패 확인**

Run: `uv run pytest -q scripts/test_cretop_agent.py -k 'retries_company_once_after_generic_popup or generic_popup_recovery_used'`

Expected: 배치가 범용 복구 사용 여부를 유지하지 않아 FAIL.

- [ ] **Step 3: 배치 상태 연결 구현**

```python
for index, lead in enumerate(leads, start=1):
    generic_popup_recovery_used = False
    while True:
        handling = self._handle_company_exception(
            exc=exc,
            item_run_id=item_run_id,
            business_number=lead.get("business_number") or "",
            interval_seconds=interval_seconds,
            timeout_seconds=timeout_seconds,
            expired_page_recovery_used=expired_page_recovery_used,
            phase="company",
            generic_popup_recovery_used=generic_popup_recovery_used,
        )
        if handling.get("generic_popup_recovery_used") is True:
            generic_popup_recovery_used = True
```

프리플라이트 호출에는 `phase="preflight"`, `generic_popup_recovery_used=False`를 전달한다.

- [ ] **Step 4: CRETOP 테스트와 정적 검사**

Run:

```bash
uv run pytest -q scripts/test_cretop_agent.py scripts/test_cretop_click_marker_retry.py scripts/test_cretop_detail_collection.py scripts/test_cretop_report_pipeline.py
uv run ruff check scripts/cretop_agent.py scripts/test_cretop_agent.py
uv run python -m py_compile scripts/cretop_agent.py
```

Expected: 모두 PASS.

- [ ] **Step 5: 전체 프로젝트 테스트**

Run: `uv run pytest -q`

Expected: 전체 PASS.

- [ ] **Step 6: 변경 diff 검토와 문서 동기화**

- 정상 경로와 기존 오류 분기의 diff가 없는지 확인한다.
- 범용 단계가 `_handle_company_exception()`의 마지막 실패 경계에만 있는지 확인한다.
- 프리플라이트가 범용 단계에 진입하지 않는지 확인한다.
- 실브라우저 검증 전에는 `cretop-automation`의 검증 완료 선언을 바꾸지 않는다.

- [ ] **Step 7: 최종 코드 커밋**

```bash
git add scripts/cretop_agent.py scripts/test_cretop_agent.py
git commit -m "test(cretop): verify generic popup recovery boundary"
```

## 원격 검증 보류

원격 배포와 실브라우저 case-first 실행은 현재 구현 지시에 포함하지 않는다. 주인님이 원격 실행을 명시하면 기존 SSP 명령으로 이번 실패 회사와 이전 정상 회사 한 곳을 검증하고, 성공한 뒤에만 `cretop-automation`과 GBrain의 최종 경로 선언을 갱신한다.
