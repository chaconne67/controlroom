# RNDlog CEO Loan Clone Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Preserve the RNDlog landing page, KOITA checkup, and every CRETOP path while replacing the authenticated product with the deployed CEO Loan system at commit `0e6c3a50443488a68c006dc9e045bd97a67430d8`.

**Architecture:** Django uses the local `ceo_loan` database as its single `default` database. The public RNDlog routes remain at `/` and `/koita-checkup/`; Google-only authentication starts at `/accounts/login/`; the authenticated `accounts`, `funding`, `common`, SMS, and handoff code comes from the pinned CEO Loan commit and is branded as RNDlog. CRETOP schemas and collection code are not migrated or rewritten; derived funding data is rebuilt from `cretop` and `public.leads` after a rehearsed cutover.

**Tech Stack:** Django 5.2, django-allauth, PostgreSQL 16, HTMX, Tailwind CSS, Playwright, Pillow, SOLAPI HTTP API, Docker Swarm, Nginx, pytest, Ruff.

---

## File map

### Pinned upstream imports

- Replace from CEO Loan: `accounts/`, `common/`, `funding/`
- Replace from CEO Loan: `templates/account/`, `templates/admin/`, `templates/common/`, `templates/socialaccount/`
- Merge from CEO Loan: `static/css/input.css`, `static/css/output.css`
- Import and track: `funding/templates/funding/mms_card_template.html`
- Do not copy: `static/img/logo-rogeon.svg`, `assets/logo_rogeon*.png`

### RNDlog-owned files

- Preserve: `templates/landing.html`, `templates/landing-light.html`
- Preserve: `checkup/questions.py`, `checkup/templates/`, public result behavior
- Preserve: `cretop/`, `scripts/cretop*`, `docs/cretop/`
- Modify: `main/settings/base.py`, `main/settings/local.py`, `main/settings/deploy.py`
- Modify: `main/urls.py`, `accounts/urls.py`, `accounts/views.py`
- Modify: `accounts/models.py`, `accounts/forms.py`, `accounts/notifications.py`
- Create: `accounts/services/consultations.py`
- Create: `accounts/test_consultations.py`
- Replace: `accounts/migrations/0001_initial.py`
- Delete: current `accounts/migrations/0002_consultationrequest.py` through `0005_backfill_role.py`
- Create: `accounts/migrations/0002_consultationrequest.py`
- Modify: `checkup/views.py`, `checkup/test_views.py`
- Modify: `pyproject.toml`, `uv.lock`, `Dockerfile`, `.env.example`
- Modify: `deploy.sh`, host crontab
- Delete: `main/db_routers.py`, `marketing/`, `companies/`

### Operations only

- Preserve DB: `ceo_loan.cretop` and `ceo_loan.public.leads`
- Reset DB: derived `funding_*` tables and non-superuser accounts
- Temporary rehearsal DB: `ceo_loan_cutover_check`
- Preserve emergency accounts: two rows where `rndnote.public.users.is_superuser = true`

---

### Task 1: Establish baselines and pin the source snapshot

**Files:**
- Reference: `docs/superpowers/specs/2026-08-04-rndlog-ceoloan-clone-design.md`
- Reference: remote `~/ceoloan/repo` at `0e6c3a50443488a68c006dc9e045bd97a67430d8`

- [ ] **Step 1: Verify the RNDlog worktree and pinned source commit**

Run:

```bash
git status --short --branch
ssh chaconne@49.247.205.170 \
  'cd ~/ceoloan/repo && git cat-file -e 0e6c3a50443488a68c006dc9e045bd97a67430d8^{commit} && git status --short --branch'
```

Expected: RNDlog contains only approved plan/spec commits; the remote commit exists; the remote worktree is clean.

- [ ] **Step 2: Run both baseline test suites**

Run:

```bash
uv run --extra dev pytest -q --create-db
ssh chaconne@49.247.205.170 \
  'cd ~/ceoloan/repo && /home/chaconne/.local/bin/uv run pytest -q'
```

Expected: RNDlog reports 383 passing tests or the current higher count; CEO Loan reports 265 passing tests or the current higher count.

- [ ] **Step 3: Capture the pinned source in an isolated temporary directory**

Run:

```bash
source_dir=$(mktemp -d /tmp/rndlog-ceoloan-0e6c3a5.XXXXXX)
printf '%s' "$source_dir" > /tmp/rndlog-ceoloan-source-path
ssh chaconne@49.247.205.170 \
  'cd ~/ceoloan/repo && git archive 0e6c3a50443488a68c006dc9e045bd97a67430d8' \
  | tar -x -C "$source_dir"
test -f "$source_dir/funding/services/sms.py"
test -f "$source_dir/accounts/adapters.py"
```

Expected: both tests return exit code 0. The temporary directory is not inside the repository.

- [ ] **Step 4: Record source hashes needed for non-Git runtime assets**

Run:

```bash
ssh chaconne@49.247.205.170 \
  'cd ~/ceoloan/repo && sha256sum assets/mms_card_template.html assets/경영진단.xlsx'
sha256sum assets/경영진단.xlsx
```

Expected: the workbook hashes match `16b54294182ad78232c286ef538b082683315086fc9527f8350d9a3f154c160e`; record the MMS template hash `ed2e6f943a5655b1f833fa8e15cf9e4d2a184145ee8996035942e634766147e2` in the task log.

---

### Task 2: Import Google authentication and membership contracts

**Files:**
- Replace: `accounts/adapters.py`
- Replace: `accounts/admin.py`
- Replace: `accounts/services/membership.py`
- Replace: `accounts/test_impersonate.py`
- Replace: `accounts/test_membership.py`
- Replace: `accounts/test_signup.py`
- Replace: `common/auth.py`
- Create: `common/text.py`
- Modify: `accounts/models.py`
- Modify: `accounts/views.py`
- Modify: `accounts/urls.py`
- Modify: `accounts/templates/accounts/login.html`
- Modify: `accounts/templates/accounts/pending.html`
- Create: `accounts/templates/accounts/approvals.html`
- Modify: `main/settings/base.py`
- Modify: `pyproject.toml`
- Modify: `uv.lock`
- Replace: `accounts/migrations/0001_initial.py`
- Delete: `accounts/migrations/0002_consultationrequest.py`
- Delete: `accounts/migrations/0003_delete_consultationrequest.py`
- Delete: `accounts/migrations/0004_user_role.py`
- Delete: `accounts/migrations/0005_backfill_role.py`

- [ ] **Step 1: Copy the pinned authentication tests before implementation**

Run a bulk copy from the recorded temporary source:

```bash
source_dir=$(cat /tmp/rndlog-ceoloan-source-path)
cp "$source_dir/accounts/test_signup.py" accounts/test_signup.py
cp "$source_dir/accounts/test_impersonate.py" accounts/test_impersonate.py
cp "$source_dir/accounts/test_membership.py" accounts/test_membership.py
```

- [ ] **Step 2: Add RNDlog route assertions to the failing login tests**

Add to `accounts/test_signup.py`:

```python
def test_public_root_stays_rndlog_landing(client):
    response = client.get("/")
    assert response.status_code == 200
    assert b"RNDlog" in response.content


def test_login_page_is_separate_from_public_root(client):
    response = client.get("/accounts/login/")
    assert response.status_code == 200
    assert "Google" in response.content.decode()
```

- [ ] **Step 3: Run authentication tests and verify the expected failure**

Run:

```bash
uv run --extra dev pytest -q accounts/test_signup.py accounts/test_impersonate.py accounts/test_membership.py
```

Expected: failures for missing allauth apps, adapters, impersonation views, and `/accounts/login/` behavior.

- [ ] **Step 4: Import the pinned authentication implementation**

Copy these exact files from the pinned source:

```bash
source_dir=$(cat /tmp/rndlog-ceoloan-source-path)
cp "$source_dir/accounts/adapters.py" accounts/adapters.py
cp "$source_dir/accounts/admin.py" accounts/admin.py
cp "$source_dir/accounts/services/membership.py" accounts/services/membership.py
cp "$source_dir/common/auth.py" common/auth.py
cp "$source_dir/common/text.py" common/text.py
cp "$source_dir/accounts/templates/accounts/approvals.html" accounts/templates/accounts/approvals.html
cp "$source_dir/accounts/templates/accounts/login.html" accounts/templates/accounts/login.html
cp "$source_dir/accounts/templates/accounts/pending.html" accounts/templates/accounts/pending.html
cp "$source_dir/accounts/migrations/0001_initial.py" accounts/migrations/0001_initial.py
rm accounts/migrations/0002_consultationrequest.py \
  accounts/migrations/0003_delete_consultationrequest.py \
  accounts/migrations/0004_user_role.py \
  accounts/migrations/0005_backfill_role.py
```

Merge `accounts.models.User.display_name` from the pinned source into the existing RNDlog `User` model. Keep the existing UUID primary key, `phone`, `role`, and timestamps.

Expected: the imported initial migration creates `users` with `role`; no superseded RNDlog migration remains. Task 3 will create the only new `0002` migration.

- [ ] **Step 5: Configure allauth without taking ownership of the public root**

In `main/settings/base.py`, add these apps and middleware entries:

```python
"django.contrib.sites",
"allauth",
"allauth.account",
"allauth.socialaccount",
"allauth.socialaccount.providers.google",
```

```python
"allauth.account.middleware.AccountMiddleware",
```

Set the authentication contract:

```python
SITE_ID = 1
LOGIN_URL = "/accounts/login/"
LOGIN_REDIRECT_URL = "/accounts/after-login/"
LOGOUT_REDIRECT_URL = "/"
AUTHENTICATION_BACKENDS = [
    "django.contrib.auth.backends.ModelBackend",
    "allauth.account.auth_backends.AuthenticationBackend",
]
SOCIALACCOUNT_ONLY = True
ACCOUNT_EMAIL_VERIFICATION = "none"
ACCOUNT_ADAPTER = "accounts.adapters.CeoLoanAccountAdapter"
SOCIALACCOUNT_ADAPTER = "accounts.adapters.CeoLoanSocialAdapter"
SOCIALACCOUNT_LOGIN_ON_GET = True
SOCIALACCOUNT_PROVIDERS = {
    "google": {
        "APP": {
            "client_id": os.environ.get("GOOGLE_CLIENT_ID", ""),
            "secret": os.environ.get("GOOGLE_CLIENT_SECRET", ""),
            "key": "",
        },
        "SCOPE": ["profile", "email"],
        "AUTH_PARAMS": {"access_type": "online"},
    }
}
GOOGLE_ALLOWED_DOMAINS = tuple(
    value.strip().lower()
    for value in os.environ.get("GOOGLE_ALLOWED_DOMAINS", "").split(",")
    if value.strip()
)
BOOTSTRAP_ADMIN_EMAILS = tuple(
    value.strip().lower()
    for value in os.environ.get("BOOTSTRAP_ADMIN_EMAILS", "").split(",")
    if value.strip()
)
```

- [ ] **Step 6: Add runtime dependencies and regenerate the lock**

Add to the main dependency list in `pyproject.toml`:

```toml
"django-allauth[socialaccount]>=65.18.0",
"playwright>=1.60.0",
"pillow>=10.0",
```

Remove Playwright from the dev-only dependency group, then run:

```bash
uv lock
uv sync --extra dev
```

Expected: lock and environment update without dependency resolution errors.

- [ ] **Step 7: Merge the pinned views while keeping `/accounts/login/`**

Use the pinned `accounts/views.py` approval and impersonation functions. Add this RNDlog-owned view:

```python
def login_page(request):
    if request.user.is_authenticated:
        return redirect("after_login")
    return render(request, "accounts/login.html")
```

In `accounts/urls.py`, put this route before allauth routes:

```python
path("accounts/login/", views.login_page, name="login"),
```

Keep `after_login`, `pending`, approvals, approve/reject, and impersonation routes from the pinned source.

- [ ] **Step 8: Run focused tests and commit**

Run:

```bash
uv run --extra dev pytest -q accounts/test_signup.py accounts/test_impersonate.py accounts/test_membership.py accounts/test_landing.py
uv run ruff check accounts common main/settings/base.py
```

Expected: all focused tests and Ruff checks pass.

Commit:

```bash
git add accounts common main/settings/base.py pyproject.toml uv.lock
git commit -m "feat(accounts): adopt Google-only ceoloan authentication"
```

---

### Task 3: Replace marketing-backed public inquiries with one minimal model

**Files:**
- Modify: `accounts/models.py`
- Modify: `accounts/forms.py`
- Modify: `accounts/views.py`
- Modify: `accounts/notifications.py`
- Create: `accounts/services/consultations.py`
- Create: `accounts/test_consultations.py`
- Create: `accounts/migrations/0002_consultationrequest.py`
- Modify: `checkup/views.py`
- Modify: `checkup/test_views.py`

- [ ] **Step 1: Write failing tests for both public inquiry paths**

Create `accounts/test_consultations.py`:

```python
import pytest

from accounts.models import ConsultationRequest


@pytest.mark.django_db
def test_landing_consultation_is_stored(client):
    response = client.post(
        "/consultation-requests/",
        {
            "company_name": "테스트회사",
            "contact_name": "홍길동",
            "phone": "010-1111-2222",
            "email": "landing@example.com",
            "concern": "연구소 관리",
            "preferred_time": "오후",
        },
    )
    assert response.status_code == 302
    inquiry = ConsultationRequest.objects.get(email="landing@example.com")
    assert inquiry.source == ConsultationRequest.Source.LANDING
    assert inquiry.details["concern"] == "연구소 관리"


@pytest.mark.django_db
def test_checkup_consultation_is_stored(client):
    response = client.post(
        "/koita-checkup/consultation/",
        {
            "company_name": "진단회사",
            "contact_name": "김담당",
            "phone": "010-3333-4444",
            "email": "checkup@example.com",
            "score": "75",
            "grade_label": "B",
            "grade_title": "보완 필요",
            "industry": "제조업",
            "director": "0613",
        },
    )
    assert response.status_code == 200
    inquiry = ConsultationRequest.objects.get(email="checkup@example.com")
    assert inquiry.source == ConsultationRequest.Source.CHECKUP
    assert inquiry.details["score"] == "75"
```

- [ ] **Step 2: Run the tests and verify the model is missing**

Run:

```bash
uv run --extra dev pytest -q accounts/test_consultations.py
```

Expected: collection fails because `ConsultationRequest` does not exist.

- [ ] **Step 3: Add the minimal inquiry model**

Add to `accounts/models.py`:

```python
class ConsultationRequest(models.Model):
    class Source(models.TextChoices):
        LANDING = "landing", "랜딩페이지"
        CHECKUP = "checkup", "KOITA 자가진단"

    company_name = models.CharField(max_length=200)
    contact_name = models.CharField(max_length=100)
    phone = models.CharField(max_length=40)
    email = models.EmailField()
    source = models.CharField(max_length=10, choices=Source.choices, db_index=True)
    details = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        db_table = "consultation_requests"
        ordering = ["-created_at"]
```

- [ ] **Step 4: Put public inquiry creation behind one service**

Create `accounts/services/consultations.py`:

```python
from accounts.models import ConsultationRequest


def create_consultation(*, company_name, contact_name, phone, email, source, details):
    return ConsultationRequest.objects.create(
        company_name=company_name.strip(),
        contact_name=contact_name.strip(),
        phone=phone.strip(),
        email=email.strip().lower(),
        source=source,
        details=details,
    )
```

Modify landing and checkup views to call this service. Remove imports from `marketing.models` and `marketing.services`.

- [ ] **Step 5: Generate and inspect the migration**

Run:

```bash
uv run python manage.py makemigrations accounts --name consultationrequest
uv run python manage.py makemigrations --check --dry-run
```

Expected: `accounts/migrations/0002_consultationrequest.py` creates only `consultation_requests`; the dry run reports no further changes.

- [ ] **Step 6: Run public tests and commit**

Run:

```bash
uv run --extra dev pytest -q accounts/test_consultations.py accounts/test_landing.py checkup/test_views.py
uv run ruff check accounts checkup
```

Expected: all tests and Ruff checks pass.

Commit:

```bash
git add accounts checkup
git commit -m "refactor(public): store inquiries without marketing"
```

---

### Task 4: Convert Django to the single local `ceo_loan` database

**Files:**
- Modify: `main/settings/base.py`
- Modify: `main/settings/local.py`
- Modify: `main/settings/deploy.py`
- Delete: `main/db_routers.py`
- Create: `main/test_database_contract.py`

- [ ] **Step 1: Write failing database contract tests**

Create `main/test_database_contract.py`:

```python
from django.conf import settings


def test_default_database_is_ceo_loan():
    assert settings.DATABASES["default"]["NAME"].startswith("test_") or settings.DATABASES["default"]["NAME"] == "ceo_loan"


def test_database_router_is_removed():
    assert not getattr(settings, "DATABASE_ROUTERS", [])
    assert set(settings.DATABASES) == {"default"}
```

- [ ] **Step 2: Run the contract tests and verify failure**

Run:

```bash
uv run --extra dev pytest -q main/test_database_contract.py
```

Expected: failure because `ceo_loan` is a second alias and `FundingRouter` is configured.

- [ ] **Step 3: Replace the database builder**

In `main/settings/base.py`, use one builder:

```python
DATABASE_NAME = os.environ.get("POSTGRES_DB", "ceo_loan")
DATABASE_USER = os.environ.get("POSTGRES_USER", "rndnote")


def postgres_database(host: str, port: str) -> dict:
    if not DATABASE_PASSWORD and not (RUNNING_TESTS or RUNNING_COLLECTSTATIC):
        raise ImproperlyConfigured("POSTGRES_PASSWORD environment variable is required")
    return {
        "default": {
            "ENGINE": DATABASE_ENGINE,
            "NAME": DATABASE_NAME,
            "USER": DATABASE_USER,
            "PASSWORD": DATABASE_PASSWORD,
            "HOST": host,
            "PORT": port,
            "CONN_MAX_AGE": DATABASE_CONN_MAX_AGE,
        }
    }
```

Delete `DATABASE_ROUTERS` and delete `main/db_routers.py`.

- [ ] **Step 4: Point local and deploy settings to the same database**

Keep the existing host and port in each environment, but call the one-database builder:

```python
DATABASES = postgres_database(DATABASE_HOST, DATABASE_PORT)
```

In deployment, `POSTGRES_DB=ceo_loan` and `POSTGRES_USER=rndnote` are explicit environment values.

- [ ] **Step 5: Run tests and commit**

Run:

```bash
uv run --extra dev pytest -q main/test_database_contract.py funding/test_guards.py accounts/test_membership.py
uv run python manage.py check
```

Expected: one database alias, no router, and checks pass.

Commit:

```bash
git add main
git commit -m "refactor(db): make ceo_loan the single application database"
```

---

### Task 5: Import the authenticated CEO Loan funding system

**Files:**
- Replace: `funding/`
- Preserve and reconcile: `funding/services/cretop_data.py`
- Preserve and reconcile: `funding/services/report.py`
- Preserve and reconcile: `funding/services/narrative.py`
- Preserve and reconcile: `funding/services/loan.py`
- Preserve: `assets/경영진단.xlsx`
- Create: `funding/templates/funding/mms_card_template.html`

- [ ] **Step 1: Copy the pinned funding tests first**

Run:

```bash
source_dir=$(cat /tmp/rndlog-ceoloan-source-path)
cp "$source_dir"/funding/test_*.py funding/
cp "$source_dir/funding/conftest.py" funding/conftest.py
```

- [ ] **Step 2: Run the imported tests and verify missing SMS/campaign behavior**

Run:

```bash
uv run --extra dev pytest -q funding/test_sms.py funding/test_campaign.py funding/test_adminview.py
```

Expected: failures for missing `SmsSend`, `SmsCampaign`, SMS views, and the new `Ceo.agent`/`progress` contract.

- [ ] **Step 3: Replace funding with the pinned implementation**

Copy all tracked funding files from the pinned source over `funding/`. This is a mechanical import from one immutable commit:

```bash
source_dir=$(cat /tmp/rndlog-ceoloan-source-path)
cp -a "$source_dir/funding/." funding/
```

Do not copy or delete `cretop/`, `scripts/`, `docs/cretop/`, or `assets/경영진단.xlsx`.

- [ ] **Step 4: Verify CRETOP contract parity before accepting the import**

Compare the four CRETOP-facing services against the pre-import commit:

```bash
git diff HEAD -- funding/services/cretop_data.py funding/services/report.py funding/services/narrative.py funding/services/loan.py
```

Reconcile these exact RNDlog CRETOP contracts into the imported files:

- use `connections["default"]` through one `DB_ALIAS = "default"` constant;
- keep bulk fact loading for industry and sales data;
- keep the recent-three-year selection rule;
- keep the existing workbook cell mapping and required-field validation;
- keep the current Gemini narrative input/output contract and its no-fabricated-values rule.

Remove superseded `connections["ceo_loan"]` accesses and any duplicate query path after the merge.

- [ ] **Step 5: Add an explicit CRETOP preservation test**

Add to `funding/test_report.py`:

```python
def test_cretop_services_use_default_database(monkeypatch):
    from funding.services import cretop_data

    assert cretop_data.DB_ALIAS == "default"
```

Define exactly once:

```python
DB_ALIAS = "default"
```

and use `connections[DB_ALIAS]` in that module.

- [ ] **Step 6: Copy the MMS template into a tracked application path and replace its embedded brand**

Copy only the template from the remote server:

```bash
mkdir -p funding/templates/funding
scp chaconne@49.247.205.170:~/ceoloan/repo/assets/mms_card_template.html \
  funding/templates/funding/mms_card_template.html
sha256sum funding/templates/funding/mms_card_template.html
```

Expected before branding: `ed2e6f943a5655b1f833fa8e15cf9e4d2a184145ee8996035942e634766147e2`.

Replace the embedded base64 RoGeon logo with text markup:

```html
<span class="rndlog-logo">RND<span>log</span></span>
```

Add CSS:

```css
.rndlog-logo { color:#0b1526; font-size:42px; font-weight:900; letter-spacing:-.06em; }
.rndlog-logo span { color:#9fe000; }
```

Keep the existing `.agent .phone` node. Change `services/mms_card.py` to load the tracked template from `funding/templates/funding/mms_card_template.html` and populate the phone from `settings.SOLAPI_SENDER`.

- [ ] **Step 7: Run the full funding and CRETOP regression suites**

Run:

```bash
uv run --extra dev pytest -q funding scripts/test_cretop_agent.py scripts/test_cretop_detail_collection.py scripts/test_cretop_report_pipeline.py
uv run ruff check funding
```

Expected: all imported CEO Loan tests and existing CRETOP tests pass.

- [ ] **Step 8: Commit the funding import**

```bash
git add funding
git commit -m "feat(funding): import the deployed ceoloan workflow"
```

---

### Task 6: Integrate RNDlog routes, navigation, and branding

**Files:**
- Modify: `main/urls.py`
- Modify: `templates/common/base.html`
- Modify: `templates/common/nav_sidebar.html`
- Create: `templates/common/_impersonation_banner.html`
- Create: `templates/common/manage_tabs.html`
- Create: `templates/account/logout.html`
- Create: `templates/admin/base_site.html`
- Create: `templates/socialaccount/authentication_error.html`
- Modify: `static/css/input.css`
- Modify: `tailwind.config.js`
- Delete: `static/img/logo-rogeon.svg` if imported accidentally

- [ ] **Step 1: Write route and branding tests**

Add to `accounts/test_landing.py`:

```python
def test_marketing_route_is_removed(client):
    assert client.get("/marketing/").status_code == 404


def test_public_routes_stay_available(client):
    assert client.get("/").status_code == 200
    assert client.get("/koita-checkup/").status_code == 200
```

Add to `funding/test_guards.py`:

```python
def test_sidebar_uses_rndlog_brand(admin_client):
    response = admin_client.get("/funding/admin/")
    html = response.content.decode()
    assert "RND" in html and "log" in html
    assert "RoGeon" not in html
```

- [ ] **Step 2: Run the tests and verify expected failures**

Run:

```bash
uv run --extra dev pytest -q accounts/test_landing.py funding/test_guards.py
```

Expected: marketing still resolves or CEO Loan templates still contain its original brand.

- [ ] **Step 3: Merge pinned shared templates and CSS**

Copy shared templates from the pinned source, then replace visible RoGeon branding with the existing RNDlog text-logo pattern from `templates/common/nav_sidebar.html`:

```html
<a href="/" class="text-xl font-extrabold tracking-tight text-ink">
  RND<span class="text-accent">log</span>
</a>
```

Keep role-based CEO Loan navigation and impersonation banner behavior.

- [ ] **Step 4: Define the final URL order**

Set `main/urls.py` to this ownership order:

```python
urlpatterns = [
    path("admin/", admin.site.urls),
    path("", TemplateView.as_view(template_name="landing.html"), name="landing"),
    path("light/", TemplateView.as_view(template_name="landing-light.html"), name="landing_light"),
    path("", include("accounts.urls")),
    path("accounts/", include("allauth.urls")),
    path("funding/", include("funding.urls")),
    path("koita-checkup/", include("checkup.urls")),
]
```

Do not include `marketing.urls` or `companies.urls`.

- [ ] **Step 5: Run route, template, and CSS checks**

Run:

```bash
npx tailwindcss -i static/css/input.css -o static/css/output.css --minify
uv run --extra dev pytest -q accounts/test_landing.py accounts/test_signup.py funding/test_guards.py checkup/test_views.py
uv run python manage.py check
```

Expected: public routes are 200, marketing is 404, Google login is available, role screens use RNDlog branding.

- [ ] **Step 6: Commit**

```bash
git add main/urls.py templates static/css tailwind.config.js accounts/test_landing.py funding/test_guards.py
git commit -m "feat(ui): combine rndlog public pages with ceoloan workspace"
```

---

### Task 7: Remove superseded marketing and companies code

**Files:**
- Delete: `marketing/`
- Delete: `companies/`
- Modify: `main/settings/base.py`
- Modify: `Dockerfile`
- Modify: `pyproject.toml` only where imports prove a dependency is unused

- [ ] **Step 1: Search for remaining runtime imports**

Run:

```bash
rg -n "from marketing|import marketing|marketing:|include\(\"marketing|from companies|import companies|companies:" \
  --glob '*.py' --glob '*.html' --glob '!docs/**' --glob '!marketing/**' --glob '!companies/**'
```

Expected: no runtime references after Task 3 and Task 6. A remaining reference is a failed precondition; resolve it within the Task 3 inquiry service or Task 6 URL/template ownership before deletion.

- [ ] **Step 2: Remove apps and Docker template copies**

Delete the two directories. Remove `marketing` and `companies` from `INSTALLED_APPS`. Remove `COPY marketing/templates` from the Docker assets stage; keep `COPY checkup/templates`.

- [ ] **Step 3: Verify import closure**

Run:

```bash
uv run python manage.py check
uv run --extra dev pytest -q accounts checkup funding
rg -n "marketing|companies" main accounts checkup funding templates --glob '*.py' --glob '*.html'
```

Expected: Django check and tests pass; remaining text matches only historical migration labels or explanatory tests that intentionally assert removal.

- [ ] **Step 4: Commit**

```bash
git add -A marketing companies main/settings/base.py Dockerfile accounts checkup funding templates
git commit -m "refactor(apps): remove superseded marketing and companies paths"
```

---

### Task 8: Add SMS settings, browser runtime, deploy, and scheduler contracts

**Files:**
- Modify: `.env.example`
- Modify: `main/settings/base.py`
- Modify: `Dockerfile`
- Modify: `deploy.sh`
- Modify: `docker-compose.yml`
- Test: `funding/test_sms.py`

- [ ] **Step 1: Add settings contract tests**

Add to `funding/test_sms.py`:

```python
def test_company_contact_uses_solapi_sender(settings):
    from funding.services import sms

    settings.SOLAPI_SENDER = "01011112222"
    assert sms.company_contact() == "01011112222"
```

Add exactly this helper and use it from SMS text and MMS card context:

```python
def company_contact():
    return digits_only(settings.SOLAPI_SENDER)
```

- [ ] **Step 2: Verify the new contract fails before adaptation**

Run:

```bash
uv run --extra dev pytest -q funding/test_sms.py::test_company_contact_uses_solapi_sender
```

Expected: failure because the helper or shared use is missing.

- [ ] **Step 3: Add environment-owned SMS settings**

In `main/settings/base.py`:

```python
SOLAPI_API_KEY = os.environ.get("SOLAPI_API_KEY", "")
SOLAPI_API_SECRET = os.environ.get("SOLAPI_API_SECRET", "")
SOLAPI_SENDER = os.environ.get("SOLAPI_SENDER", "")
SMS_OPT_OUT_NUMBER = os.environ.get("SMS_OPT_OUT_NUMBER", "")
```

Add the same keys without values to `.env.example`, with `SMS_OPT_OUT_NUMBER=080-500-4233` as the documented default. Never commit `.env`.

- [ ] **Step 4: Install browser and Korean font runtime in Docker**

Merge the pinned CEO Loan Docker packages:

```dockerfile
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        curl fontconfig fonts-noto-cjk \
        libasound2 libatk-bridge2.0-0 libatk1.0-0 libatspi2.0-0 libcairo2 \
        libcups2 libdbus-1-3 libdrm2 libgbm1 libnspr4 libnss3 \
        libpango-1.0-0 libpangocairo-1.0-0 libx11-6 libxcomposite1 \
        libxdamage1 libxext6 libxfixes3 libxkbcommon0 libxrandr2 && \
    rm -rf /var/lib/apt/lists/*
ENV PLAYWRIGHT_BROWSERS_PATH=/opt/playwright
RUN python -m playwright install chromium
```

- [ ] **Step 5: Make deploy migrate and back up one database**

In `deploy.sh`:

- change the backup database from `rndnote` to `${POSTGRES_DB:-ceo_loan}`;
- run one `python manage.py migrate --settings=main.settings.deploy --noinput`;
- remove `--database=ceo_loan` migration;
- keep migration plan, release check, Swarm render, service health wait, and cleanup.

- [ ] **Step 6: Verify configuration and image build**

Run:

```bash
uv run --extra dev pytest -q funding/test_sms.py funding/test_campaign.py
uv run python manage.py check --settings=main.settings.deploy --deploy --fail-level WARNING
docker build -t rndlog_app:ceoloan-plan-check .
docker run --rm --env-file .env \
  -e DATABASE_HOST=10.7.0.18 -e DATABASE_PORT=5433 -e POSTGRES_DB=ceo_loan \
  rndlog_app:ceoloan-plan-check \
  python manage.py check --settings=main.settings.deploy
```

Expected: tests and checks pass; image includes Chromium and renders Django checks without browser installation at runtime.

- [ ] **Step 7: Commit**

```bash
git add .env.example main/settings/base.py Dockerfile deploy.sh docker-compose.yml funding/test_sms.py funding/services
git commit -m "build: add rndlog SMS and MMS runtime"
```

---

### Task 9: Run full pre-cutover verification and code review

**Files:**
- Review: complete diff from `077ec98`

- [ ] **Step 1: Run migration drift and static checks**

Run:

```bash
uv run python manage.py makemigrations --check --dry-run
uv run ruff check
npx tailwindcss -i static/css/input.css -o static/css/output.css --minify
git diff --check 077ec98..HEAD
```

Expected: no model drift, no lint failures, CSS builds, no whitespace errors.

- [ ] **Step 2: Run the complete test suite**

Run:

```bash
uv run --extra dev pytest -q --create-db
```

Expected: all RNDlog public, CEO Loan, funding, and CRETOP tests pass.

- [ ] **Step 3: Run `code-review-loop`**

Review the complete local diff from `077ec98` through `HEAD`. Fix only verified findings within the approved scope, rerun the focused tests for each fix, and repeat until no findings remain.

- [ ] **Step 4: Re-run complete verification after review fixes**

Run:

```bash
uv run python manage.py makemigrations --check --dry-run
uv run ruff check
uv run --extra dev pytest -q --create-db
git status --short --branch
```

Expected: all commands pass; only intentional committed changes exist.

---

### Task 10: Rehearse the destructive database cutover

**Files:**
- No repository files
- Temporary DB: `ceo_loan_cutover_check`

- [ ] **Step 1: Measure database and free disk before cloning**

Run:

```bash
docker exec rndnote-db-prod psql -U rndnote -d postgres -At -c \
  "select pg_database_size('ceo_loan');"
df -B1 --output=avail / | tail -1
```

Expected: available bytes exceed twice the database size plus 2 GiB. If not, stop and free space without deleting CRETOP data.

- [ ] **Step 2: Create the temporary rehearsal database**

Run only after confirming no database with that exact name exists:

```bash
docker exec rndnote-db-prod psql -U rndnote -d postgres -At -c \
  "select datname from pg_database where datname='ceo_loan_cutover_check';"
docker exec rndnote-db-prod createdb -U rndnote ceo_loan_cutover_check
set -o pipefail
docker exec rndnote-db-prod pg_dump -U rndnote -d ceo_loan --format=custom \
  | docker exec -i rndnote-db-prod pg_restore -U rndnote \
      -d ceo_loan_cutover_check --no-owner --no-privileges
```

Expected: the first command prints nothing; the dump/restore clone succeeds even while production has active connections.

- [ ] **Step 3: Export the two superusers into a protected temporary file**

Run in one shell:

```bash
superusers_csv=$(mktemp /tmp/rndlog-superusers.XXXXXX.csv)
chmod 600 "$superusers_csv"
docker exec rndnote-db-prod psql -U rndnote -d rndnote -c \
  "\copy (select id,password,last_login,is_superuser,username,first_name,last_name,email,is_staff,is_active,date_joined,phone,role,created_at,updated_at from users where is_superuser order by id) to stdout with csv" \
  > "$superusers_csv"
printf '%s' "$superusers_csv" > /tmp/rndlog-superusers-path
test "$(wc -l < "$superusers_csv")" -eq 2
```

Expected: exactly two rows, with no row contents printed.

- [ ] **Step 4: Reset only derived and inconsistent application state in the rehearsal DB**

Run:

```bash
docker exec -i rndnote-db-prod psql -v ON_ERROR_STOP=1 -U rndnote -d ceo_loan_cutover_check <<'SQL'
BEGIN;
TRUNCATE TABLE
  funding_handoff,
  funding_callaudio,
  funding_callrecord,
  funding_assignment,
  funding_agent,
  funding_ceocompany,
  funding_ceo
CASCADE;
DELETE FROM django_migrations
WHERE app IN ('accounts','admin','auth','contenttypes','sessions','sites','socialaccount');
COMMIT;
SQL
```

Do not name `cretop` tables or `public.leads` in this SQL.

- [ ] **Step 5: Apply the new schema to the rehearsal DB**

Run:

```bash
POSTGRES_DB=ceo_loan_cutover_check uv run python manage.py migrate --settings=main.settings.deploy --noinput
```

Expected: authentication/allauth tables are created and funding reaches `0017_ceo_agent_progress`.

- [ ] **Step 6: Import superusers and rebuild derived companies**

Run:

```bash
superusers_csv=$(cat /tmp/rndlog-superusers-path)
docker exec -i rndnote-db-prod psql -v ON_ERROR_STOP=1 -U rndnote -d ceo_loan_cutover_check -c \
  "\copy users (id,password,last_login,is_superuser,username,first_name,last_name,email,is_staff,is_active,date_joined,phone,role,created_at,updated_at) from stdin with csv" \
  < "$superusers_csv"
POSTGRES_DB=ceo_loan_cutover_check uv run python manage.py funding_sync_ceos --settings=main.settings.deploy
```

Expected: two superusers import; representative and company rows regenerate from preserved source data.

- [ ] **Step 7: Verify rehearsal invariants**

Run count-only SQL:

```bash
docker exec rndnote-db-prod psql -U rndnote -d ceo_loan_cutover_check -At -c "
select 'cretop_tables='||count(*) from information_schema.tables where table_schema='cretop';
select 'leads='||count(*) from public.leads;
select 'superusers='||count(*) from users where is_superuser;
select 'other_users='||count(*) from users where not is_superuser;
select 'funding_migration='||max(name) from django_migrations where app='funding';
select 'ceos='||count(*) from funding_ceo;
select 'companies='||count(*) from funding_ceocompany;
select 'calls='||count(*) from funding_callrecord;
select 'handoffs='||count(*) from funding_handoff;
select 'sms='||count(*) from funding_smssend;
select 'campaigns='||count(*) from funding_smscampaign;
"
```

Expected: 34 CRETOP tables; leads unchanged from production; 2 superusers; 0 other users; funding migration `0017_ceo_agent_progress`; CEOs and companies greater than zero; calls, handoffs, SMS, and campaigns equal zero.

- [ ] **Step 8: Remove rehearsal artifacts after success**

Resolve exact targets first, then remove only them:

```bash
docker exec rndnote-db-prod dropdb -U rndnote ceo_loan_cutover_check
superusers_csv=$(cat /tmp/rndlog-superusers-path)
shred -u "$superusers_csv"
rm /tmp/rndlog-superusers-path
```

Expected: rehearsal DB and protected CSV are gone; production DB is unchanged.

---

### Task 11: Configure Google OAuth callback

**External state:** Google Cloud OAuth client used by CEO Loan

- [ ] **Step 1: Open the Google Cloud OAuth client with user handoff**

Use a visible authenticated browser. If login or MFA is required, hand control to the user and resume only after authentication.

- [ ] **Step 2: Add the exact callback URI**

Add:

```text
https://rndnote.co.kr/accounts/google/login/callback/
```

Do not remove existing CEO Loan/RoGeon callback URIs.

- [ ] **Step 3: Verify configuration without creating an account**

Open `https://rndnote.co.kr/accounts/login/`, start Google login, and verify Google accepts the redirect URI. Stop before authorizing a new production user if no dedicated test account is available.

Expected: no `redirect_uri_mismatch` error.

---

### Task 12: Perform the production cutover and deploy

**Files:**
- Operational: `.env`, host crontab, Docker Swarm services
- Database: local `ceo_loan`

- [ ] **Step 1: Verify required production settings without printing values**

Run:

```bash
for key in GOOGLE_CLIENT_ID GOOGLE_CLIENT_SECRET SOLAPI_API_KEY SOLAPI_API_SECRET SOLAPI_SENDER SMS_OPT_OUT_NUMBER; do
  value=$(awk -F= -v key="$key" '$1==key {sub(/^[^=]*=/, ""); print; exit}' .env)
  test -n "$value" || { printf '%s is unset\n' "$key"; exit 1; }
done
```

Expected: exit code 0 and no secret values printed.

- [ ] **Step 2: Push committed code before destructive work**

Run:

```bash
git status --short --branch
git push origin main
```

Expected: clean worktree; `origin/main` matches local `main`.

- [ ] **Step 3: Disable writers and stop the authenticated app**

Save the current crontab to a protected temporary file, remove only the three funding command lines from the active crontab, and scale the app to zero:

```bash
cron_backup=$(mktemp /tmp/rndlog-crontab.XXXXXX)
chmod 600 "$cron_backup"
crontab -l > "$cron_backup"
printf '%s' "$cron_backup" > /tmp/rndlog-crontab-path
crontab -l | rg -v 'funding_sync_ceos|funding_send_sms_campaigns|funding_sync_sms_delivery' | crontab -
docker service scale Rndnote_app=0
```

Expected: no funding writer cron remains; `Rndnote_app` is `0/0`.

- [ ] **Step 4: Export superusers and execute the rehearsed reset on production**

Repeat Task 10 Steps 3 and 4 with target database `ceo_loan`, not `ceo_loan_cutover_check`. Before executing, print the exact database name and table list; do not proceed if either differs from this plan.

- [ ] **Step 5: Apply schema, import superusers, and rebuild derived data**

Run the same commands as Task 10 Steps 5 and 6 with `POSTGRES_DB=ceo_loan` and target database `ceo_loan`.

Expected: migrations reach `0017`; two superusers import; CRETOP sync regenerates representatives and companies.

- [ ] **Step 6: Run count-only production invariants**

Run the exact SQL from Task 10 Step 7 against `ceo_loan`.

Expected: the same invariants as the successful rehearsal.

- [ ] **Step 7: Deploy the official RNDlog stack**

Run:

```bash
./deploy.sh --no-git --no-backup
```

Expected: full tests pass, release check passes, one migration path runs, `Rndnote_app` and `Rndnote_nginx` become `1/1` on the new tag.

- [ ] **Step 8: Install the final scheduler**

Merge these exact lines into the host crontab, preserving unrelated jobs:

```cron
5 * * * * cd /home/work/rndnote && .venv/bin/python manage.py funding_sync_ceos >> logs/funding_sync.log 2>&1
0,30 * * * * cd /home/work/rndnote && .venv/bin/python manage.py funding_send_sms_campaigns >> logs/sms_campaign.log 2>&1
25,55 * * * * cd /home/work/rndnote && .venv/bin/python manage.py funding_sync_sms_delivery >> logs/sms_delivery.log 2>&1
```

Verify with `crontab -l`. Remove the protected cron backup only after verification.

- [ ] **Step 9: Verify live public and authenticated entry points**

Run:

```bash
curl -fsS -o /dev/null -w 'landing=%{http_code}\n' https://rndnote.co.kr/
curl -fsS -o /dev/null -w 'checkup=%{http_code}\n' https://rndnote.co.kr/koita-checkup/
curl -fsS -o /dev/null -w 'login=%{http_code}\n' https://rndnote.co.kr/accounts/login/
docker service ls --format '{{.Name}}|{{.Image}}|{{.Replicas}}' | rg '^Rndnote_(app|nginx)\|'
```

Expected: all public responses are 200; app and nginx are `1/1`.

- [ ] **Step 10: Verify role and CRETOP flows in a browser**

Verify:

1. Google login reaches pending or the approved role.
2. `/admin/` accepts one preserved emergency superuser.
3. Superuser approval changes a pending user role.
4. Admin, TM, and sales land on their designated pages.
5. Admin company detail loads CRETOP facts.
6. One 경영진단 workbook generates successfully.
7. MMS preview shows RNDlog and the formatted `SOLAPI_SENDER`.
8. No real SMS is sent during this verification.

- [ ] **Step 11: Clean protected transfer files and report deletion**

After both superusers are verified:

```bash
superusers_csv=$(cat /tmp/rndlog-superusers-path)
shred -u "$superusers_csv"
rm /tmp/rndlog-superusers-path
cron_backup=$(cat /tmp/rndlog-crontab-path)
shred -u "$cron_backup"
rm /tmp/rndlog-crontab-path
```

Report that transfer files were irrecoverably removed; the accounts remain in the database.

- [ ] **Step 12: Update GBrain and final verification**

Update `project-overview` and `system-architecture` with the actual deployed structure, migration, schedules, and domain behavior. Then run:

```bash
git status --short --branch
git rev-parse HEAD
git rev-parse origin/main
```

Expected: clean worktree and matching SHAs.

---

## Rollback boundary

Before Task 12 Step 4, rollback is ordinary code rollback. After the production reset begins, old derived business data is intentionally gone and is not restored. If schema or deployment verification fails, keep `Rndnote_app=0`, preserve CRETOP and `public.leads`, fix the verified migration/deployment defect, rerun the same single cutover path, and do not re-enable cron until all invariants pass.
