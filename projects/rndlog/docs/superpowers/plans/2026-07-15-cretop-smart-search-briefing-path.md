# CRETOP Smart Search Briefing Path Implementation Plan

> **For agentic workers:** Implement inline in the current workspace. Do not dispatch subagents or request another approval; the user approved the exact route before this plan was written.

**Goal:** Replace the per-company landing/home search loop with the verified Smart Search loop and force the Briefing top tab after every company detail entry.

**Architecture:** Keep browser behavior in `scripts/cretop_agent.py`. Use the landing `기업` menu only for initial entry or recovery, use the detail/search upper `스마트검색` tab between companies, and make detail entry produce a verified Briefing page before collection begins. Remove the old assumption that clicking a company always opens Briefing.

**Tech Stack:** Python 3.13, pytest, coordinate-based Windows Chrome automation

---

## Approved final path

1. Preflight and landing-page reset.
2. Click landing `기업` and verify the Smart Search markers.
3. Enter the 10-digit business number in `키워드`.
4. Select `정상` once.
5. Click `조회하기` and verify the one-result target business number.
6. Click the company name and verify the target detail page.
7. Click the upper `브리핑` tab and verify the Briefing markers.
8. Collect the approved eight sections in the existing order.
9. Click the upper `스마트검색` tab and verify the reset search screen.
10. Repeat from keyword entry for the next company.

The result list does not re-check `정상`, `청산`, or `해산`; the `정상` filter already determines the list.

## Files

- Modify: `scripts/cretop_agent.py`
- Modify: `scripts/test_cretop_agent.py`
- Modify: `scripts/test_cretop_click_marker_retry.py`
- Modify: `docs/cretop/final_collection_procedure.md`
- Modify: `/home/chaconne/.codex/skills/cretop-automation/SKILL.md`
- Update: GBrain `agents/rndlog/private/cretop-detail-state-reset-20260714`

### Task 1: Lock the new browser contract with failing tests

- [ ] Change the coordinate contract to landing `기업` `(303,171)`, Smart Search keyword `(733,631)`, `정상` `(581,686)`, `조회하기` `(953,1016)`, upper Smart Search `(390,276)`, result company `(448,490)`, and Briefing `(496,276)`.
- [ ] Add a contract test for landing-to-Smart-Search marker confirmation.
- [ ] Replace the home-search test with the Smart Search action sequence.
- [ ] Change detail-entry expectation to company click, detail identity confirmation, Briefing click, and Briefing confirmation.
- [ ] Change the batch boundary expectation to initial landing entry followed by upper Smart Search resets.
- [ ] Run the focused tests and confirm they fail because the new behavior is not implemented.

Run:

```bash
uv run pytest -q \
  scripts/test_cretop_agent.py::test_detail_navigation_coordinates_are_declared \
  scripts/test_cretop_agent.py::test_business_search_uses_verified_smart_search_controls \
  scripts/test_cretop_agent.py::test_detail_entry_clicks_briefing_after_company_detail_identity \
  scripts/test_cretop_agent.py::test_collect_batch_reuses_smart_search_between_companies
```

Expected: failures showing the old coordinates, home-search calls, missing Briefing click, and home-reset loop.

### Task 2: Replace the old final path

- [ ] Add the approved Smart Search coordinate and marker constants to `scripts/cretop_agent.py`.
- [ ] Add one landing-entry helper and one upper-tab reset helper; both use `_click_and_confirm` and the same Smart Search marker contract.
- [ ] Replace `_search_business_number_from_home_fast` with a Smart Search method that requires a verified ready token and performs keyword input, `정상`, and `조회하기` in that order.
- [ ] Change `_enter_detail_from_company_item` to verify detail identity, then click Briefing and return the verified Briefing copy as the first collected section.
- [ ] Replace the normal batch boundary state from `home_reset` to `smart_search_ready`.
- [ ] Keep landing/home reset only for initial positioning and exceptional recovery.
- [ ] Change company-error recovery to return to Smart Search instead of the landing page.
- [ ] Run the focused tests until green.

### Task 3: Remove contradictory instructions

- [ ] Replace the home-search/company-logo loop in `docs/cretop/final_collection_procedure.md` with the approved Smart Search loop.
- [ ] Replace the stale `cretop-automation` statements that company entry defaults to Briefing and that every company returns through the logo.
- [ ] Record the verified persistence rule and the new merge point in GBrain.
- [ ] Ensure no company-specific business number or company name becomes a production rule.

### Task 4: Verify and review

- [ ] Run all CRETOP local tests.

```bash
uv run pytest -q scripts/test_cretop_agent.py scripts/test_cretop_click_marker_retry.py
```

- [ ] Run the project test command.

```bash
uv run pytest -q
```

- [ ] Review only the CRETOP diff for path duplication, stale names, orphaned home-search behavior, and missing recovery transitions.
- [ ] Commit only the files changed for this SSP update.

Remote deployment and live-browser collection are outside this code-change request. Live SSP verification requires a later explicit remote execution instruction.
