# CRETOP Click Marker Retry Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make every CRETOP logical click that produces a marker poll at one-second intervals for ten seconds, repeat the same click up to three times, and stop the batch after the fourth failed click.

**Architecture:** Add one retry boundary inside `CommandRunner` that owns `click action → marker confirmation`. Timeout observers raise a dedicated exception so only missing-marker failures repeat the click; expired pages and mechanical errors continue through their existing failure paths. Existing coordinates, markers, collection order, and wrapper behavior remain unchanged.

**Tech Stack:** Python 3.13, pytest, pyautogui abstraction in `scripts/cretop_agent.py`

---

## File map

- Modify: `scripts/cretop_agent.py`
  - Owns the official CRETOP browser SSP, marker timeout type, click retry contract, and all integrations.
- Create: `scripts/test_cretop_click_marker_retry.py`
  - Focused regression tests for retry count, retryable timeout, non-retryable errors, search terminal states, and official interval defaults.
  - A new focused file avoids staging the user's existing untracked `scripts/test_cretop_agent.py`.
- Modify: `/home/chaconne/.codex/skills/cretop-automation/SKILL.md`
  - Replaces the current single-click marker rule with the verified retry contract after local verification.
- Update: `agents/rndlog/private/cretop-click-marker-retry-20260714` through `gbrain-rndlog note`
  - Records the durable final-path rule after implementation verification.

### Task 1: Core retry contract

**Files:**
- Modify: `scripts/cretop_agent.py:65-123,981-1123`
- Create: `scripts/test_cretop_click_marker_retry.py`

- [ ] **Step 1: Write failing tests for successful retry and retry exhaustion**

```python
from __future__ import annotations

import pytest

from scripts import cretop_agent as agent


def make_runner():
    return object.__new__(agent.CommandRunner)


def test_click_confirmation_retries_three_times_then_succeeds():
    runner = make_runner()
    clicks = []
    confirmations = iter([
        agent.MarkerTimeoutError("first"),
        agent.MarkerTimeoutError("second"),
        agent.MarkerTimeoutError("third"),
        {"marker_check": {"matched": True}},
    ])

    def click_action():
        clicks.append(len(clicks) + 1)
        return {"click": len(clicks)}

    def confirm_action():
        result = next(confirmations)
        if isinstance(result, Exception):
            raise result
        return result

    result = runner._click_and_confirm(click_action, confirm_action)

    assert len(clicks) == 4
    assert result["click_attempt_count"] == 4
    assert result["retry_count"] == 3
    assert result["confirmation"]["marker_check"]["matched"] is True


def test_click_confirmation_stops_after_four_failed_clicks():
    runner = make_runner()
    clicks = []

    def click_action():
        clicks.append(len(clicks) + 1)
        return {"click": len(clicks)}

    def confirm_action():
        raise agent.MarkerTimeoutError("missing marker")

    with pytest.raises(agent.MarkerTimeoutError, match="click_attempts=4"):
        runner._click_and_confirm(click_action, confirm_action)

    assert len(clicks) == 4
```

- [ ] **Step 2: Run the focused tests and verify RED**

Run:

```bash
uv run pytest scripts/test_cretop_click_marker_retry.py -q
```

Expected: FAIL because `MarkerTimeoutError` and `_click_and_confirm` do not exist.

- [ ] **Step 3: Implement the timeout type, constants, and minimal retry helper**

Add near the existing timeout constants and `ExpiredPageError`:

```python
DEFAULT_MARKER_INTERVAL_SECONDS = 1.0
MAX_CLICK_RETRIES = 3


class MarkerTimeoutError(RuntimeError):
    pass
```

Add inside `CommandRunner` before `_copy_until_markers`:

```python
def _click_and_confirm(self, click_action, confirm_action) -> dict[str, Any]:
    click_attempts: list[dict[str, Any]] = []
    for attempt in range(1, MAX_CLICK_RETRIES + 2):
        click_attempts.append(click_action())
        try:
            confirmation = confirm_action()
        except MarkerTimeoutError as exc:
            if attempt == MAX_CLICK_RETRIES + 1:
                raise MarkerTimeoutError(
                    f"{exc}; click_attempts={attempt}; "
                    f"max_click_retries={MAX_CLICK_RETRIES}"
                ) from exc
            continue
        return {
            "ok": True,
            "click_attempts": click_attempts,
            "click_attempt_count": attempt,
            "retry_count": attempt - 1,
            "confirmation": confirmation,
        }
    raise AssertionError("unreachable click retry state")
```

Change only the terminal timeout raises in `_copy_until_markers`, `_wait_copied_page_marker`, `_wait_login_ready`, `_wait_copied_page_marker_absent`, and `_wait_search_result_fast` from `RuntimeError` to `MarkerTimeoutError`.

- [ ] **Step 4: Verify GREEN and non-retryable errors**

Add and run:

```python
def test_click_confirmation_does_not_retry_non_marker_errors():
    runner = make_runner()
    clicks = []

    def click_action():
        clicks.append(1)
        return {"click": 1}

    def confirm_action():
        raise agent.ExpiredPageError("expired")

    with pytest.raises(agent.ExpiredPageError, match="expired"):
        runner._click_and_confirm(click_action, confirm_action)

    assert len(clicks) == 1
```

Run:

```bash
uv run pytest scripts/test_cretop_click_marker_retry.py -q
```

Expected: 3 passed.

- [ ] **Step 5: Commit the core contract**

```bash
git add scripts/cretop_agent.py scripts/test_cretop_click_marker_retry.py
git commit -m "fix(cretop): add marker-aware click retries"
```

### Task 2: Collection, search, home, and popup integration

**Files:**
- Modify: `scripts/cretop_agent.py:1125-1182,1266-1320,1431-1568`
- Modify: `scripts/test_cretop_click_marker_retry.py`

- [ ] **Step 1: Write failing integration tests**

Use a fake desktop whose logical navigation click is recorded and marker confirmation fails once before succeeding. Cover these existing boundaries:

```python
@pytest.mark.parametrize(
    "method_name",
    [
        "_go_home_fast",
        "_search_business_number_from_home_fast",
        "_enter_detail_from_company_item",
        "_collect_detail_map_fast",
        "_dismiss_kodata_service_popup",
    ],
)
def test_click_marker_boundaries_use_common_retry(method_name):
    assert method_name in {
        "_go_home_fast",
        "_search_business_number_from_home_fast",
        "_enter_detail_from_company_item",
        "_collect_detail_map_fast",
        "_dismiss_kodata_service_popup",
    }
```

Replace the structural parameter check with one focused behavior test per method using the existing fake patterns from `scripts/test_cretop_agent.py`. Each test must make the first confirmation raise `MarkerTimeoutError`, return success on the second confirmation, and assert that the navigation click or popup click bundle ran exactly twice.

Add a search terminal-state test:

```python
@pytest.mark.parametrize("presence_status", ["absent", "ambiguous"])
def test_search_terminal_states_do_not_repeat_click(presence_status):
    runner = make_runner()
    clicks = []
    runner.desktop = type(
        "Desktop",
        (),
        {
            "click": lambda _self, x, y: clicks.append((x, y)) or {"x": x, "y": y},
            "paste_text": lambda _self, text: {"text": text},
        },
    )()
    runner._wait_search_result_fast = lambda *_args, **_kwargs: {
        "presence_status": presence_status,
        "result_count": 0 if presence_status == "absent" else 1,
    }

    result = runner._search_business_number_from_home_fast(
        "1234567890",
        home_reset={"ok": True},
        interval_seconds=1.0,
        timeout_seconds=10.0,
    )

    assert result["presence_status"] == presence_status
    assert clicks.count((agent.HOME_SEARCH_BUTTON_POINT["x"], agent.HOME_SEARCH_BUTTON_POINT["y"])) == 1
```

- [ ] **Step 2: Run the new integration tests and verify RED**

Run each new node with `uv run pytest <file>::<node> -q`.

Expected: FAIL because each caller still executes the click outside `_click_and_confirm`.

- [ ] **Step 3: Replace each existing click-confirm pair**

Use the same shape at every boundary:

```python
outcome = self._click_and_confirm(
    lambda: self.desktop.click(point["x"], point["y"]),
    lambda: self._copy_until_markers(
        markers,
        PAGE_COPY_POINT,
        interval_seconds=interval_seconds,
        timeout_seconds=timeout_seconds,
        previous_text=previous_text,
    ),
)
copied = outcome["confirmation"]
retry_evidence = {
    key: value for key, value in outcome.items() if key != "confirmation"
}
```

Preserve existing return keys with the final click result for compatibility. Add `click_retry` or `navigation_retry` metadata without duplicating the copied page text. For KODATA, click `skip_week` once, then retry only the `close` click while the popup marker remains. Repeating the checkbox click would toggle the selection off.

- [ ] **Step 4: Verify the focused integration tests**

Run:

```bash
uv run pytest scripts/test_cretop_click_marker_retry.py -q
```

Expected: all focused tests pass.

- [ ] **Step 5: Commit the integrated collection path**

```bash
git add scripts/cretop_agent.py scripts/test_cretop_click_marker_retry.py
git commit -m "fix(cretop): retry click-driven collection steps"
```

### Task 3: Login stages and one-second official interval

**Files:**
- Modify: `scripts/cretop_agent.py:1157-1264,1637-1644,1811-1815,1822-1830`
- Modify: `scripts/test_cretop_click_marker_retry.py`

- [ ] **Step 1: Write failing tests for login boundaries and defaults**

Add tests that make the first marker confirmation fail and the second succeed for:

- login confirmation click → `WA260642`
- time extension click → `WA260642` with `시간연장` absent
- relogin click → existing next-stage marker
- concurrent-session click → `손진석`

Add constant/default assertions:

```python
def test_official_marker_interval_is_one_second():
    assert agent.DEFAULT_MARKER_INTERVAL_SECONDS == 1.0
```

Patch `_ensure_ready_fast` in command-level tests and assert that `preflight`, `collect_batch_fast`, and `search_detail` pass `interval_seconds=1.0` when payloads omit the optional value.

- [ ] **Step 2: Run the login/default tests and verify RED**

Run:

```bash
uv run pytest scripts/test_cretop_click_marker_retry.py -q
```

Expected: login click counts remain one and command defaults remain `0.5`.

- [ ] **Step 3: Integrate login clicks without replaying whole flows**

Wrap each existing click and its direct next marker in `_click_and_confirm`. For relogin, keep the current conditional next-stage behavior: the first click confirms either the access step or login confirmation; the access click, when present, separately confirms `LOGIN_CONFIRM_MARKER`; the final confirmation click separately confirms login readiness.

Do not retry the full login sequence, resolution change, tab selection, or service-popup probe.

Replace command defaults:

```python
interval_seconds = float(
    payload.get("interval_seconds", DEFAULT_MARKER_INTERVAL_SECONDS)
)
```

Use `DEFAULT_MARKER_INTERVAL_SECONDS` in `preflight()` as well.

- [ ] **Step 4: Verify all focused tests**

Run:

```bash
uv run pytest scripts/test_cretop_click_marker_retry.py -q
```

Expected: all tests pass.

- [ ] **Step 5: Commit login and interval integration**

```bash
git add scripts/cretop_agent.py scripts/test_cretop_click_marker_retry.py
git commit -m "fix(cretop): retry login clicks on marker timeout"
```

### Task 4: Local verification, review, and final-path documentation

**Files:**
- Verify: `scripts/cretop_agent.py`
- Verify: `scripts/test_cretop_click_marker_retry.py`
- Verify without modifying: `scripts/test_cretop_agent.py`
- Modify: `/home/chaconne/.codex/skills/cretop-automation/SKILL.md`

- [ ] **Step 1: Run focused and existing CRETOP tests**

```bash
uv run pytest scripts/test_cretop_click_marker_retry.py scripts/test_cretop_agent.py scripts/test_cretop_detail_collection.py -q
```

Expected: zero failures.

- [ ] **Step 2: Run syntax and lint checks**

```bash
uv run python -m py_compile scripts/cretop_agent.py scripts/test_cretop_click_marker_retry.py
uv run ruff check scripts/cretop_agent.py scripts/test_cretop_click_marker_retry.py
```

Expected: both commands exit 0.

- [ ] **Step 3: Review the local implementation diff**

Lock the review to the approved retry contract and inspect:

- only `MarkerTimeoutError` triggers a repeated click
- every logical click-marker boundary uses the helper
- body-copy and input-focus clicks remain excluded
- `present`, `absent`, and `ambiguous` do not repeat search
- fourth marker timeout propagates to existing batch stop behavior
- no coordinates, markers, tab order, browser lifecycle, wrapper, or DB code changed

- [ ] **Step 4: Update the final-path skill and GBrain**

Replace the marker wait sentence in `cretop-automation/SKILL.md` with the verified contract: one-second polling, ten seconds per click, three reclicks, four total clicks, then immediate failure and batch stop. Record the durable rule with:

```bash
gbrain-rndlog note cretop-click-marker-retry-20260714 '<verified summary>'
```

- [ ] **Step 5: Commit documentation and confirm clean task scope**

```bash
git add /home/chaconne/.codex/skills/cretop-automation/SKILL.md
git commit -m "docs(cretop): record click marker retry contract"
git status --short
git log -5 --oneline
```

Expected: task files are committed; unrelated pre-existing user changes remain untouched. The skill path may be outside the repository, so if Git does not track it, report the direct skill update and commit only repository files.

Remote deployment and live-browser verification are deliberately excluded. They require a separate explicit user instruction after local review.
