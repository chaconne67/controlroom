# CRETOP Concurrent Session Direct-Ready Recovery Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 동시접속 종료 확인 뒤 로그인 확인 팝업 또는 로그인 완료 화면으로 복귀하는 두 정상 결과를 처리하고 같은 회사 추출을 재시도한다.

**Architecture:** 기존 `session_recovery` 예외 경로만 수정한다. 동시접속 팝업이 사라진 뒤의 화면을 한 공용 판정으로 확인하고, 로그인 확인 팝업이면 기존 확인 경로를 사용하며 `WA260642` 화면이면 기존 홈 초기화와 회사 재시도 경로로 바로 연결한다.

**Tech Stack:** Python, pytest, 원격 Windows Chrome SSP

---

## SSP 잠금

- 현재 경로: `collect_batch_fast → _handle_company_exception → session_recovery → _ensure_ready_fast → _go_home_fast → _enter_smart_search_from_landing → retry_company`
- 병합 위치: `_ensure_ready_fast`의 재로그인 후 `접속` 분기와 직접 동시접속 분기
- 대체 대상: `접속` 클릭 뒤 `손진석` 문구만 기다리는 단일 사후조건
- 검증 경로: 로컬 테스트 → 리뷰 → 커밋 → 실패 회사 1건 원격 SSP → 남은 52건 원격 SSP
- 금지 범위: 정상 검색, 상세 진입, 8개 화면 수집, 정보 비공개·유료 서비스·페이지 만료 처리

### Task 1: 동시접속 사후조건 계약 고정

**Files:**
- Modify: `scripts/test_cretop_agent.py`

- [x] **Step 1: 직접 준비화면 복귀 테스트 작성**

```python
def test_preflight_accepts_ready_page_after_concurrent_access(monkeypatch):
    runner = object.__new__(agent.CommandRunner)
    clicks = []

    class FakeDesktop:
        def display(self):
            return {"width": 1920, "height": 1080}

        def select_cretop_tab(self):
            return {"ok": True}

        def click(self, x, y):
            clicks.append((x, y))
            return {"x": x, "y": y}

    runner.desktop = FakeDesktop()
    monkeypatch.setattr(
        runner,
        "_dismiss_kodata_service_popup",
        lambda **_kwargs: {"ok": True, "dismissed": False},
    )
    monkeypatch.setattr(
        runner,
        "_copied_page_has_marker",
        lambda marker, **_kwargs: marker == "동시접속자 수",
    )
    monkeypatch.setattr(
        runner,
        "_wait_copied_page_any_marker",
        lambda markers, **_kwargs: {
            "text": "CRETOP WA260642 기업 검색 결과 1건",
            "marker_check": {
                "markers": markers,
                "matched_marker": agent.LOGIN_READY_MARKER,
                "matched": True,
            },
        },
    )
    monkeypatch.setattr(
        runner,
        "_confirm_login_popup",
        lambda **_kwargs: pytest.fail("ready page must not click login confirmation"),
    )

    result = runner._ensure_ready_fast(interval_seconds=0, timeout_seconds=1)

    assert result["recovered_from"] == "concurrent_session"
    assert result["ready"]["marker_check"]["matched_marker"] == agent.LOGIN_READY_MARKER
    assert clicks == [(1035, 681)]
```

- [x] **Step 2: 실패 확인**

Run: `uv run pytest -q scripts/test_cretop_agent.py -k 'concurrent_access or concurrent_popup'`

Expected: 현재 코드는 `손진석` 전용 대기를 사용하므로 새 계약이 FAIL.

### Task 2: 두 정상 결과를 기존 세션 복구 단계에 병합

**Files:**
- Modify: `scripts/cretop_agent.py`

- [x] **Step 1: 공용 marker 대기에 제외 marker 조건 추가**

```python
def _wait_copied_page_any_marker(
    self,
    markers: list[str],
    *,
    interval_seconds: float,
    timeout_seconds: float,
    absent_markers: list[str] | None = None,
) -> dict[str, Any]:
    started = time.monotonic()
    attempts = 0
    excluded = absent_markers or []
    last_copy: dict[str, Any] | None = None
    while time.monotonic() - started <= timeout_seconds:
        attempts += 1
        copied = self.desktop.copy_text(PAGE_COPY_POINT["x"], PAGE_COPY_POINT["y"])
        last_copy = copied
        text = copied.get("text") or ""
        self._raise_if_expired_page(text)
        excluded_present = any(
            self._copied_text_has_markers(text, [marker]) for marker in excluded
        )
        if not excluded_present:
            for marker in markers:
                if self._copied_text_has_markers(text, [marker]):
                    copied["marker_check"] = {
                        "markers": markers,
                        "absent_markers": excluded,
                        "matched_marker": marker,
                        "matched": True,
                        "attempts": attempts,
                        "elapsed_seconds": round(time.monotonic() - started, 2),
                        "mode": "copy_text",
                    }
                    return copied
        time.sleep(interval_seconds)
    raise MarkerTimeoutError(
        f"copied page markers not found after {timeout_seconds}s: {markers}; "
        f"absent_markers={excluded}; "
        f"last_text={(last_copy or {}).get('text', '')[:300]}",
        last_text=(last_copy or {}).get("text", ""),
    )
```

- [x] **Step 2: 중복된 `접속` 클릭 복구를 공용 함수로 병합**

```python
def _complete_concurrent_access(
    self,
    *,
    concurrent_markers: list[str],
    interval_seconds: float,
    timeout_seconds: float,
) -> dict[str, Any]:
    outcome = self._click_and_confirm(
        lambda: self.desktop.click(1035, 681),
        lambda: self._wait_copied_page_any_marker(
            [LOGIN_CONFIRM_MARKER, LOGIN_READY_MARKER],
            absent_markers=concurrent_markers,
            interval_seconds=interval_seconds,
            timeout_seconds=timeout_seconds,
        ),
    )
    ready_screen = outcome["confirmation"]
    matched_marker = ready_screen["marker_check"]["matched_marker"]
    if matched_marker == LOGIN_CONFIRM_MARKER:
        login_confirmation = self._confirm_login_popup(
            interval_seconds=interval_seconds,
            timeout_seconds=timeout_seconds,
        )
        ready = login_confirmation["ready"]
        service_popup = login_confirmation["service_popup"]
    else:
        login_confirmation = None
        ready = ready_screen
        service_popup = self._dismiss_kodata_service_popup(
            interval_seconds=interval_seconds,
            timeout_seconds=timeout_seconds,
        )
    return {
        "ready": ready,
        "login_confirmation": login_confirmation,
        "service_popup": service_popup,
        "click_retry": self._click_retry_evidence(outcome),
    }
```

- [x] **Step 3: 직접 동시접속 분기를 공용 함수에 연결**

```python
if any(
    self._copied_page_has_marker(marker, timeout_seconds=1.0)
    for marker in concurrent_markers
):
    access_recovery = self._complete_concurrent_access(
        concurrent_markers=concurrent_markers,
        interval_seconds=interval_seconds,
        timeout_seconds=timeout_seconds,
    )
    return {
        "ok": True,
        "state": "ready",
        "recovered_from": "concurrent_session",
        "display": display,
        "selected_tab": selected_tab,
        "service_popup": access_recovery["service_popup"],
        "login_confirmation": access_recovery["login_confirmation"],
        "ready": access_recovery["ready"],
        "concurrent_click_retry": access_recovery["click_retry"],
    }
```

- [x] **Step 4: 재로그인 뒤 `접속` 분기도 공용 함수에 연결**

```python
access_recovery = None
if matched_marker == "접속":
    access_recovery = self._complete_concurrent_access(
        concurrent_markers=concurrent_markers,
        interval_seconds=interval_seconds,
        timeout_seconds=timeout_seconds,
    )
    login_confirmation = access_recovery["login_confirmation"]
    ready = access_recovery["ready"]
    service_popup = access_recovery["service_popup"]
else:
    login_confirmation = self._confirm_login_popup(
        interval_seconds=interval_seconds,
        timeout_seconds=timeout_seconds,
    )
    ready = login_confirmation["ready"]
    service_popup = login_confirmation["service_popup"]
```

- [x] **Step 5: 집중 테스트 통과 확인**

Run: `uv run pytest -q scripts/test_cretop_agent.py -k 'preflight and (login or concurrent)'`

Expected: 기존 로그인 확인 경로와 직접 준비화면 경로가 모두 PASS.

### Task 3: 전체 검증·리뷰·문서화·커밋

**Files:**
- Modify: `docs/cretop/final_collection_procedure.md`
- Modify: `docs/superpowers/plans/2026-07-16-cretop-concurrent-session-direct-ready-recovery.md`

- [x] **Step 1: 전체 검증**

Run: `uv run pytest -q scripts/test_cretop_agent.py && uv run pytest -q && uv run ruff check scripts/cretop_agent.py scripts/test_cretop_agent.py`

Expected: 모든 명령 종료 코드 0.

- [x] **Step 2: 코드리뷰 루프**

Run: 변경된 CRETOP diff를 `$code-review-loop`로 리뷰하고 finding이 없을 때까지 승인된 범위만 수정한다.

Expected: 승인된 finding 없음.

- [x] **Step 3: 운영 문서와 GBrain 갱신**

- 동시접속 후 로그인 확인 팝업 또는 로그인 완료 화면을 허용한다.
- 동시접속 팝업이 남은 상태는 성공으로 인정하지 않는다.
- 검증된 원인과 복구 계약을 기능 단위 GBrain 페이지에 반영한다.

- [x] **Step 4: 커밋**

```bash
git add scripts/cretop_agent.py scripts/test_cretop_agent.py docs/cretop/final_collection_procedure.md docs/superpowers/plans/2026-07-16-cretop-concurrent-session-direct-ready-recovery.md
git commit -m "fix(cretop): accept direct ready state after concurrent access"
```

### Task 4: 원격 SSP 검증과 추출 재개

**Files:**
- Create: `docs/cretop/detail_collection/cretop_concurrent_retry_20260716_01/cretop_concurrent_retry_20260716_01_payload.json`
- Create: `docs/cretop/detail_collection/cretop_pending52_after_concurrent_20260716_01/cretop_pending52_after_concurrent_20260716_01_payload.json`

- [x] **Step 1: 실패 회사 1건 case-first 실행**

Run: `uv run python scripts/cretop_detail_collection.py remote-agent-start --agent-command collect-batch --run-id cretop_concurrent_retry_20260716_01 --payload-file docs/cretop/detail_collection/cretop_concurrent_retry_20260716_01/cretop_concurrent_retry_20260716_01_payload.json`

Expected: `(주)일신에스티`가 `present`로 끝나고 배치가 중단되지 않음.

- [x] **Step 2: case-first 결과 확인**

Run: `uv run python scripts/cretop_detail_collection.py remote-result-fetch --run-id cretop_concurrent_retry_20260716_01`

Expected: `final_smart_search_ready.ok=true`, 회사 결과 `presence_status=present`.

- [x] **Step 3: 남은 52건 실행**

Run: `uv run python scripts/cretop_detail_collection.py remote-agent-start --agent-command collect-batch --run-id cretop_pending52_after_concurrent_20260716_01 --payload-file docs/cretop/detail_collection/cretop_pending52_after_concurrent_20260716_01/cretop_pending52_after_concurrent_20260716_01_payload.json`

Expected: 원격 백그라운드 작업이 `Running`으로 시작됨. 결과 회수와 DB 저장은 주인님의 후속 지시까지 하지 않음.
