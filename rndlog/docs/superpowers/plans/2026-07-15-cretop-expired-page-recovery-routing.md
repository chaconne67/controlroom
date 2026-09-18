# CRETOP Expired Page Recovery Routing Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Detect grammatical variants of the CRETOP expired-page message, hard-refresh once, wait 30 seconds, then choose direct home reset or preflight before restarting the interrupted company search.

**Architecture:** Keep the change inside the existing `CommandRunner` SSP in `scripts/cretop_agent.py`. Replace the narrow expiry phrase check and the fixed `wait → refresh → preflight → home → wait` recovery sequence; reuse the existing preflight, home reset, batch restart, and one-recovery-per-batch boundaries.

**Tech Stack:** Python 3.13, pytest, pyautogui abstraction, existing CRETOP remote SSP

---

## File map

- Modify: `scripts/cretop_agent.py`
  - Owns expired-page detection, refresh recovery routing, preflight, and home reset.
- Modify: `scripts/test_cretop_agent.py`
  - Holds stable state-contract tests for expiry detection and recovery ordering.
- Modify: `docs/cretop/final_collection_procedure.md`
  - Documents the official operator-visible recovery sequence.
- Modify after local verification: `/home/chaconne/.codex/skills/cretop-automation/SKILL.md`
  - Updates the CRETOP final-path declaration without adding another execution path.
- Update after local verification: `agents/rndlog/private/cretop-expired-page-recovery-routing-20260715`
  - Records the implemented contract and the pending remote verification boundary.

### Task 1: Recognize expired-page wording variants

**Files:**
- Modify: `scripts/test_cretop_agent.py:488-518`
- Modify: `scripts/cretop_agent.py:957-963`

- [ ] **Step 1: Extend the existing expiry contract test with the observed wording**

Change the parameter list to:

```python
@pytest.mark.parametrize(
    "error_marker",
    ["[8004]", "페이지 만료", "페이지가 만료되었습니다"],
)
def test_preflight_stops_on_expired_page(monkeypatch, error_marker):
    runner = object.__new__(agent.CommandRunner)

    class FakeDesktop:
        def _normalize_marker_text(self, text):
            return "".join(ch for ch in text if not ch.isspace())

        def copy_text(self, _x, _y):
            return {"text": error_marker}

        def display(self):
            return {"width": 1920, "height": 1080}

        def select_cretop_tab(self):
            return {"ok": True}

    runner.desktop = FakeDesktop()
    monkeypatch.setattr(
        runner,
        "_dismiss_kodata_service_popup",
        lambda **_kwargs: {"ok": True, "dismissed": False},
    )
    monkeypatch.setattr(
        runner,
        "_copied_page_has_marker",
        lambda marker, **_kwargs: marker == error_marker,
    )

    with pytest.raises(agent.ExpiredPageError, match="CRETOP expired page detected"):
        runner._ensure_ready_fast(interval_seconds=0, timeout_seconds=1)
```

- [ ] **Step 2: Run the observed wording case and verify RED**

Run:

```bash
uv run pytest scripts/test_cretop_agent.py::test_preflight_stops_on_expired_page -q
```

Expected: two existing cases pass and `페이지가 만료되었습니다` fails because `_raise_if_expired_page()` does not raise `ExpiredPageError`.

- [ ] **Step 3: Replace the narrow phrase check with the shared semantic marker contract**

Change `_raise_if_expired_page()` to:

```python
def _raise_if_expired_page(self, text: str) -> None:
    has_expired_code = "[8004]" in text
    has_expired_message = self._copied_text_has_markers(
        text,
        ["페이지", "만료"],
    )
    if has_expired_code or has_expired_message:
        raise ExpiredPageError(
            f"CRETOP expired page detected: {text[:300]}"
        )
```

- [ ] **Step 4: Run the expiry contract and verify GREEN**

Run:

```bash
uv run pytest scripts/test_cretop_agent.py::test_preflight_stops_on_expired_page -q
```

Expected: `3 passed`.

### Task 2: Route refresh recovery from the observed screen

**Files:**
- Modify: `scripts/test_cretop_agent.py`
- Modify: `scripts/cretop_agent.py:1387-1490`

- [ ] **Step 1: Add failing tests for direct reset, preflight routing, and repeat expiry**

Add below `test_preflight_stops_on_expired_page`:

```python
def make_expired_recovery_runner(monkeypatch, refreshed_text):
    runner = object.__new__(agent.CommandRunner)
    events = []

    class FakeDesktop:
        def _normalize_marker_text(self, text):
            return "".join(ch for ch in text if not ch.isspace())

        def hard_refresh(self):
            events.append("hard_refresh")
            return {"ok": True, "action": "ctrl_shift_r"}

        def copy_text(self, _x, _y):
            events.append("observe")
            return {"text": refreshed_text, "characters": len(refreshed_text)}

    runner.desktop = FakeDesktop()
    monkeypatch.setattr(
        runner,
        "_wait_without_action",
        lambda seconds, **_kwargs: events.append(("wait", seconds))
        or {"elapsed_seconds": seconds},
    )
    monkeypatch.setattr(
        runner,
        "_ensure_ready_fast",
        lambda **_kwargs: events.append("preflight")
        or {"ok": True, "state": "ready"},
    )
    monkeypatch.setattr(
        runner,
        "_go_home_fast",
        lambda **_kwargs: events.append("home_reset")
        or {"ok": True, "source_layout": "global", "marker_check": {"matched": True}},
    )
    return runner, events


def test_expired_recovery_resets_home_directly_from_authenticated_layout(monkeypatch):
    text = "CRETOP 기업 조기경보 KOGPS KOgrid SOHO TECH ESG WA260642"
    runner, events = make_expired_recovery_runner(monkeypatch, text)

    result = runner._recover_expired_page_to_home(
        interval_seconds=0,
        timeout_seconds=1,
        trigger_error="expired",
    )

    assert events == ["hard_refresh", ("wait", 30.0), "observe", "home_reset"]
    assert result["recovery_route"] == "home_reset"
    assert result["refresh_state"]["login_marker"] is True
    assert "before_refresh" not in result
    assert "before_resume" not in result


def test_expired_recovery_runs_preflight_when_authenticated_layout_is_missing(monkeypatch):
    runner, events = make_expired_recovery_runner(
        monkeypatch,
        "재로그인 하시겠습니까? 예 아니오",
    )

    result = runner._recover_expired_page_to_home(
        interval_seconds=0,
        timeout_seconds=1,
        trigger_error="expired",
    )

    assert events == [
        "hard_refresh",
        ("wait", 30.0),
        "observe",
        "preflight",
        "home_reset",
    ]
    assert result["recovery_route"] == "preflight_then_home_reset"


def test_expired_recovery_stops_when_refresh_still_shows_expiry(monkeypatch):
    runner, events = make_expired_recovery_runner(
        monkeypatch,
        "페이지가 만료되었습니다",
    )

    with pytest.raises(agent.ExpiredPageError, match="CRETOP expired page detected"):
        runner._recover_expired_page_to_home(
            interval_seconds=0,
            timeout_seconds=1,
            trigger_error="expired",
        )

    assert events == ["hard_refresh", ("wait", 30.0), "observe"]
```

- [ ] **Step 2: Run the recovery tests and verify RED**

Run:

```bash
uv run pytest \
  scripts/test_cretop_agent.py::test_expired_recovery_resets_home_directly_from_authenticated_layout \
  scripts/test_cretop_agent.py::test_expired_recovery_runs_preflight_when_authenticated_layout_is_missing \
  scripts/test_cretop_agent.py::test_expired_recovery_stops_when_refresh_still_shows_expiry \
  -q
```

Expected: FAIL because the current implementation waits before refresh, always runs preflight, waits again after home reset, and does not return route evidence.

- [ ] **Step 3: Extract the existing home-layout classifier without changing its contract**

Add before `_go_home_fast()`:

```python
def _classify_home_reset_layout(self, text: str) -> str | None:
    normalized_text = self.desktop._normalize_marker_text(text)
    has_detail_layout = all(
        self.desktop._normalize_marker_text(marker) in normalized_text
        for marker in DETAIL_LAYOUT_MARKERS
    )
    has_global_layout = all(
        self.desktop._normalize_marker_text(marker) in normalized_text
        for marker in GLOBAL_LAYOUT_MARKERS
    )
    has_login_marker = (
        self.desktop._normalize_marker_text(LOGIN_READY_MARKER) in normalized_text
    )
    if has_detail_layout:
        return "detail"
    if has_global_layout and has_login_marker:
        return "global"
    return None
```

Replace the duplicated layout calculation at the start of `_go_home_fast()` with:

```python
copied = self.desktop.copy_text(PAGE_COPY_POINT["x"], PAGE_COPY_POINT["y"])
text = copied.get("text") or ""
self._raise_if_expired_page(text)
source_layout = self._classify_home_reset_layout(text)
briefing_reset: dict[str, Any] | None = None
if source_layout == "detail":
    briefing_point = self.cretop.top_tab_point("briefing")
    briefing_outcome = self._click_and_confirm(
        lambda: self.desktop.click(briefing_point["x"], briefing_point["y"]),
        lambda: self._copy_until_markers(
            ["기업프로필", "My 재무 Data"],
            PAGE_COPY_POINT,
            interval_seconds=interval_seconds,
            timeout_seconds=timeout_seconds,
        ),
    )
    briefing_click = briefing_outcome["click_attempts"][-1]
    briefing_ready = briefing_outcome["confirmation"]
    briefing_reset = {
        "point": briefing_point,
        "click": briefing_click,
        "marker_check": briefing_ready.get("marker_check"),
        "click_retry": self._click_retry_evidence(briefing_outcome),
    }
    logo_point = DETAIL_HOME_LOGO_POINT.copy()
elif source_layout == "global":
    logo_point = GLOBAL_HOME_LOGO_POINT.copy()
else:
    raise RuntimeError(
        "CRETOP home reset layout not recognized: "
        f"text={text[:300]}"
    )
```

- [ ] **Step 4: Replace the fixed recovery sequence with refresh-state routing**

Replace `_recover_expired_page_to_home()` with:

```python
def _recover_expired_page_to_home(
    self,
    *,
    interval_seconds: float,
    timeout_seconds: float,
    trigger_error: str,
) -> dict[str, Any]:
    hard_refresh = self.desktop.hard_refresh()
    after_refresh_wait = self._wait_without_action(
        EXPIRED_PAGE_RECOVERY_WAIT_SECONDS,
        reason="expired_page_after_hard_refresh",
    )
    observed = self.desktop.copy_text(PAGE_COPY_POINT["x"], PAGE_COPY_POINT["y"])
    observed_text = observed.get("text") or ""
    self._raise_if_expired_page(observed_text)
    source_layout = self._classify_home_reset_layout(observed_text)
    has_login_marker = self._copied_text_has_markers(
        observed_text,
        [LOGIN_READY_MARKER],
    )
    refresh_state = {
        "characters": observed.get("characters", len(observed_text)),
        "source_layout": source_layout,
        "login_marker": has_login_marker,
    }
    if source_layout is not None and has_login_marker:
        recovery_route = "home_reset"
        ready = {
            "ok": True,
            "state": "ready",
            "recovered_from": "expired_refresh",
            "refresh_state": refresh_state,
        }
    else:
        recovery_route = "preflight_then_home_reset"
        ready = self._ensure_ready_fast(
            interval_seconds=interval_seconds,
            timeout_seconds=timeout_seconds,
        )
    home_reset = self._go_home_fast(
        interval_seconds=interval_seconds,
        timeout_seconds=timeout_seconds,
    )
    return {
        "ok": True,
        "trigger_error": trigger_error,
        "hard_refresh": hard_refresh,
        "after_refresh_wait": after_refresh_wait,
        "refresh_state": refresh_state,
        "recovery_route": recovery_route,
        "position": {
            "ready_state": ready.get("state"),
            "source_layout": home_reset.get("source_layout"),
            "home_marker": home_reset.get("marker_check"),
        },
        "ready": ready,
        "home_reset": home_reset,
    }
```

- [ ] **Step 5: Run the focused recovery tests and verify GREEN**

Run:

```bash
uv run pytest \
  scripts/test_cretop_agent.py::test_expired_recovery_resets_home_directly_from_authenticated_layout \
  scripts/test_cretop_agent.py::test_expired_recovery_runs_preflight_when_authenticated_layout_is_missing \
  scripts/test_cretop_agent.py::test_expired_recovery_stops_when_refresh_still_shows_expiry \
  -q
```

Expected: `3 passed`.

### Task 3: Align the final-path declaration and verify locally

**Files:**
- Modify: `docs/cretop/final_collection_procedure.md:35-101`
- Modify after tests pass: `/home/chaconne/.codex/skills/cretop-automation/SKILL.md:64-65`
- Review: `scripts/cretop_agent.py`, `scripts/test_cretop_agent.py`

- [ ] **Step 1: Replace the old documented recovery order**

Use this exact contract in both the repository procedure and the CRETOP automation skill:

```text
첫 `[8004]` 또는 화면 복사문에 `페이지`와 `만료`가 함께 보이면 `Ctrl+Shift+R 1회 → 30초 대기 → 화면 복사 상태 판정`을 수행한다. `WA260642`와 기존 CRETOP 레이아웃이 확인되면 홈 초기화하고, 아니면 기존 프리플라이트로 로그인 상태를 복구한 뒤 홈 초기화한다. 중단된 회사는 검색부터 다시 시작한다. 같은 배치의 두 번째 만료는 즉시 실패한다.
```

Update the Mermaid recovery nodes in `docs/cretop/final_collection_procedure.md` to the same order. Do not add a parallel recovery branch.

- [ ] **Step 2: Run focused and full local verification**

Run:

```bash
uv run pytest scripts/test_cretop_agent.py -q
uv run pytest \
  scripts/test_cretop_agent.py \
  scripts/test_cretop_click_marker_retry.py \
  scripts/test_cretop_detail_collection.py \
  -q
uv run ruff check scripts/cretop_agent.py scripts/test_cretop_agent.py
uv run python -m py_compile scripts/cretop_agent.py
git diff --check
```

Expected: all tests pass, Ruff reports no errors, compilation succeeds, and `git diff --check` prints nothing.

- [ ] **Step 3: Run the required code review**

Invoke the project `code-review` skill against the local diff. Fix only confirmed findings inside the approved expiry detection and recovery-routing scope, then rerun the focused and full local verification commands from Step 2.

- [ ] **Step 4: Record the verified local contract in GBrain**

Run:

```bash
gbrain-rndlog note cretop-expired-page-recovery-routing-20260715 '페이지 만료는 [8004] 또는 페이지와 만료 의미 토큰의 동시 존재로 분류한다. 복구 순서는 Ctrl+Shift+R 1회, 30초 대기, 화면 복사 상태 판정이다. WA260642와 기존 CRETOP 레이아웃이 확인되면 홈 초기화로 직행하고, 아니면 기존 프리플라이트 후 홈 초기화한다. 로컬 계약 검사와 CRETOP 단위 검사, Ruff, py_compile을 통과했다. 원격 배포와 실브라우저 12건 재검증은 아직 수행하지 않았다.'
```

Do not report the browser path as verified. The local result proves only classification, call ordering, and branch contracts.

- [ ] **Step 5: Commit only the intended repository files**

Run:

```bash
git add \
  scripts/cretop_agent.py \
  scripts/test_cretop_agent.py \
  docs/cretop/final_collection_procedure.md
git diff --cached --check
git commit -m "fix(cretop): route expired page recovery"
git status --short
```

Expected: the commit succeeds and the pre-existing user change in `AGENTS.md` remains unstaged.

## Deferred remote verification

Remote deployment and the 12-company rerun are a separate operational stage requiring a fresh user instruction after local review and commit.

The later final-path command is:

```bash
uv run python scripts/cretop_detail_collection.py \
  batch-script-only-collect \
  --run-id cretop_pending12_retry_20260715_01 \
  --limit 12
```

Success requires the official path to generate 12 remote result items, `remote-batch-fetch` to save them, and the 12 source leads to have terminal `present`, `absent`, or `ambiguous` lookup states in `ceo_loan`. A local unit-test result is not a substitute.
