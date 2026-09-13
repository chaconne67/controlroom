# CRETOP 8004 Recovery Implementation Plan

> **For agentic workers:** Implement inline in the existing SSP. Do not create a browser runner, test script, or alternate execution path.

**Goal:** Recover the first `[8004]` once, restart the affected company from search, pause after every five successful collections, and fail on a second `[8004]`.

**Architecture:** Keep browser behavior in `scripts/cretop_agent.py`. Convert every observed expired-page text into one typed exception, handle that exception only at the batch boundary, and reuse the existing preflight/home-reset/company-collection path after recovery.

**Tech Stack:** Python, pyautogui, existing remote SSP wrapper

---

### Task 1: Expired-page signal and recovery action

**Files:**
- Modify: `scripts/cretop_agent.py`

- [x] Add one `ExpiredPageError` type and shared expired-page marker check.
- [x] Make marker/search/login waits raise it immediately when `[8004]` or `페이지 만료` is copied.
- [x] Add a foreground `Ctrl+Shift+R` action and 30-second no-action wait using sleep slices no longer than three seconds.

### Task 2: Batch recovery and cooldown

**Files:**
- Modify: `scripts/cretop_agent.py`

- [x] On the first `ExpiredPageError`, wait 30 seconds, hard-refresh once, identify the restored page by copied markers, execute the existing home reset, wait another 30 seconds, and restart the current lead from search.
- [x] Keep one recovery allowance for the whole batch; a second `ExpiredPageError` follows the normal failure path.
- [x] Count only successful `present` collections. After five, reuse the completed home reset, wait 30 seconds, and reset the success count.
- [x] Change coordinate-click post-action wait to one second without slowing marker-only copy key combinations.

### Task 3: Final-path verification

**Files:**
- Modify: `/home/chaconne/.codex/skills/cretop-automation/SKILL.md`

- [x] Replace the old `[8004]` hard-failure wording with the approved one-recovery contract.
- [x] Run local syntax and diff checks; do not add CRETOP test code.
- [x] Execute `batch-script-only-collect --limit 10` through the remote SSP.
- [x] Confirm ten successful eight-section collections, two 30-second cooldowns, one-second click pauses, and a final landing marker.
- [ ] Runtime verification of the first `[8004]` recovery remains pending because no expired page appeared during the successful ten-company run.
- [x] Commit the verified SSP and supporting final-path files.
