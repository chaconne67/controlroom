# Funding Outbox Controls Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Restore the funding list filters and primary action with existing WDS/Tailwind styles without changing their behavior.

**Architecture:** Keep the current `admin_list.html` form, field names, HTMX contract, and JavaScript entry point. Replace only undefined presentational component classes with existing Tailwind utilities backed by WDS tokens, and lock the rendered contract in the existing Django view test module.

**Tech Stack:** Django templates, pytest-django, HTMX, Tailwind CSS, WDS tokens

---

### Task 1: Restore the filter and primary-action presentation

**Files:**
- Modify: `funding/test_adminview.py`
- Modify: `funding/templates/funding/admin_list.html:95-168`
- Rebuild: `static/css/output.css`

- [ ] **Step 1: Write the failing rendered-template test**

Add this test beside the existing outbox view tests in `funding/test_adminview.py`:

```python
def test_outbox_filter_controls_use_design_system(client):
    _user(client, Role.ADMIN)

    body = client.get(reverse("funding:outbox")).content.decode()

    assert 'aria-label="회사 검색"' in body
    assert 'aria-label="담당 TM 필터"' in body
    assert 'aria-label="발송 상태 필터"' in body
    assert 'aria-label="자격 필터"' in body
    assert 'aria-label="최소 매출 필터"' in body
    assert 'aria-label="최소 신용등급 필터"' in body
    assert 'aria-label="최대 부채비율 필터"' in body
    assert body.count("h-11 rounded-lg border border-wds-line-solid") >= 6
    assert "bg-wds-primary-normal" in body
    assert "hover:bg-wds-primary-strong" in body
    assert 'hx-target="#admin-rows"' in body
    assert 'hx-swap="outerHTML"' in body
```

- [ ] **Step 2: Run the focused test and verify it fails**

Run:

```bash
uv run pytest funding/test_adminview.py::test_outbox_filter_controls_use_design_system -q
```

Expected: FAIL because the rendered controls do not yet contain the accessible names or WDS utility classes.

- [ ] **Step 3: Apply the minimal WDS utility classes**

In `funding/templates/funding/admin_list.html`, keep every input name, option, HTMX attribute, ID, and JavaScript listener unchanged. Apply these exact presentation contracts:

```html
<input type="search" name="search" value="{{ search }}"
       placeholder="회사·대표·사업자번호·전화" aria-label="회사 검색"
       class="h-11 w-64 rounded-lg border border-wds-line-solid bg-wds-bg-normal px-3 text-sm text-wds-label-normal placeholder:text-wds-label-alternative focus:border-wds-primary-normal focus:outline-none">
```

Use this class list for every filter `select`, with the matching accessible name from Step 1:

```html
class="h-11 rounded-lg border border-wds-line-solid bg-wds-bg-normal px-3 text-sm text-wds-label-normal focus:border-wds-primary-normal focus:outline-none"
```

Use this class list for both `#pick-open` branches:

```html
class="ml-2 inline-flex h-11 items-center justify-center rounded-lg bg-wds-primary-normal px-4 text-sm font-semibold text-white transition-colors hover:bg-wds-primary-strong focus:outline-none disabled:cursor-not-allowed disabled:bg-wds-interaction-disable disabled:text-wds-label-disable"
```

- [ ] **Step 4: Run the focused test and verify it passes**

Run:

```bash
uv run pytest funding/test_adminview.py::test_outbox_filter_controls_use_design_system -q
```

Expected: `1 passed`.

- [ ] **Step 5: Rebuild Tailwind and verify generated selectors**

Run:

```bash
npx tailwindcss -i static/css/input.css -o static/css/output.css --minify
rg -n "bg-wds-primary-normal|border-wds-line-solid|h-11" static/css/output.css
```

Expected: the build succeeds and all three selector families are present in `static/css/output.css`.

- [ ] **Step 6: Run the funding and Django checks**

Run:

```bash
uv run pytest funding/test_adminview.py -q
uv run python manage.py check
git diff --check
```

Expected: all tests pass, Django reports no issues, and the diff check prints no errors.

- [ ] **Step 7: Verify the real UI contract**

Use the project's existing Django development entry point and an authenticated ADMIN and TM test state. In the browser, open the actual outbox and progress routes.

Verify:

- The search, every visible filter, and the primary action are 44px high and use WDS colors.
- At a narrow viewport the controls wrap without horizontal clipping.
- Keyboard focus is visible on search, selects, and the primary action.
- Changing each filter sends the existing GET request and replaces only `#admin-rows`.
- Clicking `문자 예약하기` opens the existing content in `#modal-slot`.
- The TM progress button remains disabled with zero selected rows and uses the disabled WDS state.
- No new console error, failed network request, page-level swap, URL change, or extra vertical scroll appears.

- [ ] **Step 8: Run the required review loop and commit**

Run `code-review-loop` on the local diff. Fix only verified defects inside the approved template/test/CSS scope, rerun Steps 4–7 for any affected path, then commit:

```bash
git add funding/templates/funding/admin_list.html funding/test_adminview.py static/css/output.css docs/superpowers/plans/2026-08-08-funding-outbox-controls.md
git commit -m "fix(funding): restore filter control styling"
```

Expected: the review loop has no remaining findings and the commit succeeds.
