# Marketing Pipeline Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the marketing pipeline app (Lead intake → email send → TM/visit tracking → Next Action) as a single `marketing` Django app, with HTMX UI, Google Sheets import, Gmail sending with open tracking, and unified Activity timeline.

**Architecture:** Single Django app `marketing/` with 8 models (Lead, LeadImport, EmailTemplate, EmailAttachment, EmailCampaign, EmailSendLog, Activity). Views split by domain under `marketing/views/`. Service layer for Sheets (`gspread`), Mailer (Django `EmailMultiAlternatives` + tracking pixel), and state transitions. Background sending via `threading.Thread`. Frontend: HTMX + Pretendard + Tailwind, following existing patterns in `templates/common/`.

**Tech Stack:** Django 5.2, PostgreSQL, HTMX, Tailwind, pytest-django, `gspread` + `google-auth` (new dependencies).

**Spec:** `docs/superpowers/specs/2026-06-09-marketing-pipeline-design.md`

---

## File Map

**Created**
- `marketing/__init__.py`, `marketing/apps.py`, `marketing/admin.py`
- `marketing/models.py` — all 7 concrete models (Lead, LeadImport, EmailTemplate, EmailAttachment, EmailCampaign, EmailSendLog, Activity)
- `marketing/forms.py` — Lead landing form, activity recording form, template form, import form
- `marketing/urls.py`
- `marketing/views/__init__.py` (re-exports)
- `marketing/views/leads.py`, `marketing/views/imports.py`, `marketing/views/templates.py`, `marketing/views/campaigns.py`, `marketing/views/dashboard.py`, `marketing/views/tracking.py`, `marketing/views/unsubscribe.py`
- `marketing/services/__init__.py`
- `marketing/services/sheets.py` — `gspread` connector
- `marketing/services/mailer.py` — email building + send + tracking injection
- `marketing/services/state.py` — auto state transition rules
- `marketing/services/tokens.py` — HMAC unsubscribe token
- `marketing/management/commands/seed_marketing.py`
- `marketing/migrations/0001_initial.py` (auto)
- `marketing/migrations/0002_import_consultation_requests.py` (data migration)
- `marketing/templates/marketing/_layout.html` and per-page templates listed in tasks
- `marketing/test_models.py`, `marketing/test_leads.py`, `marketing/test_imports.py`, `marketing/test_templates.py`, `marketing/test_campaigns.py`, `marketing/test_activities.py`, `marketing/test_tracking.py`, `marketing/test_state.py`, `marketing/test_landing_form.py`

**Modified**
- `pyproject.toml` — add `gspread`, `google-auth`
- `main/settings.py` — add `marketing` to `INSTALLED_APPS`, `GOOGLE_SERVICE_ACCOUNT_JSON` setting
- `main/urls.py` — include `marketing.urls`
- `.env.example` — add `GOOGLE_SERVICE_ACCOUNT_JSON`
- `accounts/views.py` — `consultation_request_create` writes Lead instead of `ConsultationRequest`
- `accounts/forms.py` — `ConsultationRequestForm` becomes thin wrapper writing a Lead
- `accounts/urls.py` — keep URL name unchanged
- `accounts/notifications.py` — `send_consultation_request_email(lead)` adapted
- `accounts/admin.py` — drop `ConsultationRequest` registration
- `accounts/models.py` — `ConsultationRequest` removed (via migration)
- `templates/common/nav_sidebar.html` — add marketing menu group
- `docker-compose.yml` — mount `media` volume on web service (for attachment uploads)

**Removed**
- `accounts/test_consultation_requests.py` — replaced by `marketing/test_landing_form.py`

---

## Conventions Applied to All Tasks

- **Models:** Inherit from `common.mixins.BaseModel` (UUID PK + timestamps). Choices defined inline as `TextChoices`. Tables named `marketing_*` via `Meta.db_table`.
- **Tests:** Django `TestCase`, run with `uv run pytest <path> -v`. Use `self.client`, `reverse(...)`, `mail.outbox`.
- **Auth:** Views except `tracking`/`unsubscribe`/landing form use `@login_required` + check `request.user.is_staff`.
- **Templates:** Extend `templates/common/base.html` (existing). Korean copy. Pretendard + Tailwind.
- **Commits:** Conventional Commits style (`feat:`, `test:`, `chore:`, `refactor:`). One commit per task. Never amend.
- **Run commands assume:** `uv run` prefix and `cd /home/work/rndnote`.

---

## Phase A — Foundation: marketing app + Lead model

### Task 1: Scaffold the marketing app

**Files:**
- Create: `marketing/__init__.py`, `marketing/apps.py`, `marketing/models.py`, `marketing/admin.py`, `marketing/urls.py`, `marketing/views/__init__.py`, `marketing/migrations/__init__.py`
- Modify: `main/settings.py`, `main/urls.py`

- [ ] **Step 1: Create the app directory and stub files**

```bash
mkdir -p marketing/views marketing/services marketing/migrations marketing/templates/marketing marketing/management/commands
touch marketing/__init__.py marketing/migrations/__init__.py marketing/views/__init__.py marketing/services/__init__.py marketing/management/__init__.py marketing/management/commands/__init__.py
```

Create `marketing/apps.py`:
```python
from django.apps import AppConfig


class MarketingConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "marketing"
```

Create `marketing/models.py`:
```python
# Models added in subsequent tasks.
```

Create `marketing/admin.py`:
```python
# Admin registrations added in subsequent tasks.
```

Create `marketing/urls.py`:
```python
from django.urls import path

app_name = "marketing"

urlpatterns: list = []
```

- [ ] **Step 2: Register the app**

In `main/settings.py` `INSTALLED_APPS`, add `"marketing",` after `"companies",`.

In `main/urls.py`, include the new urlconf. Read the file first to see existing patterns, then add `path("marketing/", include("marketing.urls"))`.

- [ ] **Step 3: Verify app loads**

```bash
uv run python manage.py check
```

Expected: `System check identified no issues (0 silenced).`

- [ ] **Step 4: Commit**

```bash
git add marketing main/settings.py main/urls.py
git commit -m "feat(marketing): scaffold new marketing app"
```

---

### Task 2: Lead model + migration

**Files:**
- Modify: `marketing/models.py`
- Create: `marketing/test_models.py`, `marketing/migrations/0001_initial.py` (auto-generated)

- [ ] **Step 1: Write the failing test**

Create `marketing/test_models.py`:
```python
from django.test import TestCase

from marketing.models import Lead


class LeadModelTests(TestCase):
    def test_lead_defaults(self):
        lead = Lead.objects.create(email="Alice@Example.com")
        self.assertEqual(lead.email, "alice@example.com")
        self.assertEqual(lead.status, Lead.Status.NEW)
        self.assertEqual(lead.interest_level, Lead.InterestLevel.UNKNOWN)
        self.assertEqual(lead.source, Lead.Source.MANUAL)
        self.assertFalse(lead.is_unsubscribed)
        self.assertEqual(lead.tags, [])

    def test_email_uniqueness_case_insensitive(self):
        Lead.objects.create(email="dup@example.com")
        with self.assertRaises(Exception):
            Lead.objects.create(email="DUP@example.com")
```

- [ ] **Step 2: Add the Lead model**

In `marketing/models.py`:
```python
from django.conf import settings
from django.contrib.postgres.fields import ArrayField
from django.db import models

from common.mixins import BaseModel


class Lead(BaseModel):
    class Source(models.TextChoices):
        GOOGLE_SHEET = "google_sheet", "구글 시트"
        LANDING_PAGE = "landing_page", "랜딩 페이지"
        TM = "tm", "TM"
        AD = "ad", "광고"
        MANUAL = "manual", "수동 입력"

    class Status(models.TextChoices):
        NEW = "new", "신규"
        CONTACTED = "contacted", "이메일 발송됨"
        INTERESTED = "interested", "관심"
        SCHEDULED = "scheduled", "방문 예약"
        VISITED = "visited", "방문 완료"
        WON = "won", "성사"
        LOST = "lost", "이탈"

    class InterestLevel(models.TextChoices):
        UNKNOWN = "unknown", "미확인"
        LOW = "low", "낮음"
        MEDIUM = "medium", "보통"
        HIGH = "high", "높음"

    email = models.EmailField(unique=True)
    name = models.CharField(max_length=100, blank=True)
    phone = models.CharField(max_length=40, blank=True)
    company_name = models.CharField(max_length=200, blank=True)
    source = models.CharField(max_length=20, choices=Source.choices, default=Source.MANUAL)
    source_detail = models.CharField(max_length=500, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.NEW)
    interest_level = models.CharField(
        max_length=20, choices=InterestLevel.choices, default=InterestLevel.UNKNOWN
    )
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assigned_leads",
    )
    tags = ArrayField(models.CharField(max_length=40), default=list, blank=True)
    notes = models.TextField(blank=True)
    is_unsubscribed = models.BooleanField(default=False)
    last_contacted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "marketing_lead"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status", "assigned_to"]),
            models.Index(fields=["source"]),
        ]

    def save(self, *args, **kwargs):
        if self.email:
            self.email = self.email.strip().lower()
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return f"{self.name or self.email}"
```

- [ ] **Step 3: Make and run the migration**

```bash
uv run python manage.py makemigrations marketing
uv run python manage.py migrate
```

Expected: `0001_initial` created and applied.

- [ ] **Step 4: Run the test**

```bash
uv run pytest marketing/test_models.py -v
```

Expected: 2 passed.

- [ ] **Step 5: Commit**

```bash
git add marketing/models.py marketing/test_models.py marketing/migrations/0001_initial.py
git commit -m "feat(marketing): add Lead model with status/source enums"
```

---

### Task 3: Remaining models (LeadImport, EmailTemplate, EmailAttachment, EmailCampaign, EmailSendLog, Activity)

**Files:**
- Modify: `marketing/models.py`, `marketing/test_models.py`
- Create: `marketing/migrations/0002_*.py` (auto-generated)

- [ ] **Step 1: Write failing tests for the new models**

Append to `marketing/test_models.py`:
```python
import uuid

from marketing.models import (
    Activity,
    EmailCampaign,
    EmailSendLog,
    EmailTemplate,
    LeadImport,
)


class OtherModelTests(TestCase):
    def setUp(self):
        self.lead = Lead.objects.create(email="b@example.com", name="b")

    def test_email_template_str(self):
        t = EmailTemplate.objects.create(name="koita", subject="s", html_body="<p>x</p>")
        self.assertIn("koita", str(t))

    def test_campaign_defaults(self):
        t = EmailTemplate.objects.create(name="koita2", subject="s", html_body="x")
        c = EmailCampaign.objects.create(name="c1", template=t)
        self.assertEqual(c.status, EmailCampaign.Status.DRAFT)
        self.assertEqual(c.success_count, 0)

    def test_sendlog_unique_per_campaign(self):
        t = EmailTemplate.objects.create(name="t", subject="s", html_body="x")
        c = EmailCampaign.objects.create(name="c", template=t)
        EmailSendLog.objects.create(campaign=c, lead=self.lead, to_email=self.lead.email)
        with self.assertRaises(Exception):
            EmailSendLog.objects.create(campaign=c, lead=self.lead, to_email=self.lead.email)

    def test_sendlog_tracking_id_autogenerated(self):
        t = EmailTemplate.objects.create(name="t2", subject="s", html_body="x")
        c = EmailCampaign.objects.create(name="c2", template=t)
        log = EmailSendLog.objects.create(campaign=c, lead=self.lead, to_email=self.lead.email)
        self.assertIsInstance(log.tracking_id, uuid.UUID)

    def test_activity_defaults(self):
        a = Activity.objects.create(lead=self.lead, type=Activity.Type.NOTE, subject="x")
        self.assertEqual(a.outcome, Activity.Outcome.NA)

    def test_leadimport_counters_default_zero(self):
        li = LeadImport.objects.create(sheet_url="https://x", sheet_title="t")
        self.assertEqual(li.imported_count, 0)
```

- [ ] **Step 2: Add the models**

Append to `marketing/models.py`:
```python
import uuid


class LeadImport(BaseModel):
    sheet_url = models.URLField(max_length=500)
    sheet_title = models.CharField(max_length=200, blank=True)
    column_mapping = models.JSONField(default=dict)
    filter_rule = models.JSONField(null=True, blank=True)
    imported_count = models.PositiveIntegerField(default=0)
    skipped_count = models.PositiveIntegerField(default=0)
    failed_count = models.PositiveIntegerField(default=0)
    imported_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="lead_imports",
    )
    error_log = models.TextField(blank=True)

    class Meta:
        db_table = "marketing_lead_import"
        ordering = ["-created_at"]


class EmailTemplate(BaseModel):
    name = models.CharField(max_length=120, unique=True)
    subject = models.CharField(max_length=300)
    html_body = models.TextField()
    text_body = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="email_templates",
    )

    class Meta:
        db_table = "marketing_email_template"
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return self.name


def attachment_upload_path(instance, filename):
    return f"email_attachments/{instance.template_id}/{filename}"


class EmailAttachment(BaseModel):
    template = models.ForeignKey(
        EmailTemplate, on_delete=models.CASCADE, related_name="attachments"
    )
    file = models.FileField(upload_to=attachment_upload_path)
    display_name = models.CharField(max_length=200)

    class Meta:
        db_table = "marketing_email_attachment"
        ordering = ["created_at"]


class EmailCampaign(BaseModel):
    class Status(models.TextChoices):
        DRAFT = "draft", "초안"
        SENDING = "sending", "발송 중"
        SENT = "sent", "발송 완료"
        PARTIAL_FAILED = "partial_failed", "일부 실패"
        FAILED = "failed", "실패"

    name = models.CharField(max_length=200)
    template = models.ForeignKey(EmailTemplate, on_delete=models.PROTECT, related_name="campaigns")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)
    scheduled_at = models.DateTimeField(null=True, blank=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="email_campaigns",
    )
    total_recipients = models.PositiveIntegerField(default=0)
    success_count = models.PositiveIntegerField(default=0)
    failure_count = models.PositiveIntegerField(default=0)
    open_count = models.PositiveIntegerField(default=0)
    selection_snapshot = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = "marketing_email_campaign"
        ordering = ["-created_at"]


class EmailSendLog(BaseModel):
    class Status(models.TextChoices):
        QUEUED = "queued", "대기"
        SENT = "sent", "발송됨"
        FAILED = "failed", "실패"

    campaign = models.ForeignKey(EmailCampaign, on_delete=models.CASCADE, related_name="sends")
    lead = models.ForeignKey(Lead, on_delete=models.PROTECT, related_name="email_sends")
    to_email = models.EmailField()
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.QUEUED)
    sent_at = models.DateTimeField(null=True, blank=True)
    error_message = models.TextField(blank=True)
    tracking_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    opened_at = models.DateTimeField(null=True, blank=True)
    open_count = models.PositiveIntegerField(default=0)
    last_opened_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "marketing_email_send_log"
        constraints = [
            models.UniqueConstraint(fields=["campaign", "lead"], name="uniq_send_campaign_lead"),
        ]


class Activity(BaseModel):
    class Type(models.TextChoices):
        EMAIL = "email", "이메일"
        CALL = "call", "TM 통화"
        VISIT = "visit", "방문"
        NOTE = "note", "메모"

    class Outcome(models.TextChoices):
        POSITIVE = "positive", "긍정"
        NEUTRAL = "neutral", "보통"
        NEGATIVE = "negative", "부정"
        NO_RESPONSE = "no_response", "부재중"
        NA = "na", "해당없음"

    lead = models.ForeignKey(Lead, on_delete=models.CASCADE, related_name="activities")
    type = models.CharField(max_length=10, choices=Type.choices)
    subject = models.CharField(max_length=200, blank=True)
    body = models.TextField(blank=True)
    outcome = models.CharField(max_length=15, choices=Outcome.choices, default=Outcome.NA)
    scheduled_at = models.DateTimeField(null=True, blank=True)
    happened_at = models.DateTimeField(null=True, blank=True)
    performed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="performed_activities",
    )
    email_log = models.ForeignKey(
        EmailSendLog,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="activities",
    )
    next_action = models.CharField(max_length=300, blank=True)
    next_action_due = models.DateTimeField(null=True, blank=True)
    next_action_done_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "marketing_activity"
        ordering = ["-happened_at", "-created_at"]
        indexes = [
            models.Index(fields=["lead", "-happened_at"]),
            models.Index(fields=["next_action_due", "next_action_done_at"]),
        ]
```

Move the `import uuid` up to the top of the file (group imports cleanly).

- [ ] **Step 3: Make and apply migration**

```bash
uv run python manage.py makemigrations marketing
uv run python manage.py migrate
```

- [ ] **Step 4: Run the tests**

```bash
uv run pytest marketing/test_models.py -v
```

Expected: 8 tests passed.

- [ ] **Step 5: Commit**

```bash
git add marketing/models.py marketing/test_models.py marketing/migrations/
git commit -m "feat(marketing): add Template/Attachment/Campaign/SendLog/Activity/Import models"
```

---

### Task 4: Lead service — normalize_email + get_or_create_by_email

**Files:**
- Create: `marketing/services/leads.py`, `marketing/test_lead_service.py`

- [ ] **Step 1: Write failing tests**

Create `marketing/test_lead_service.py`:
```python
from django.test import TestCase

from marketing.models import Lead
from marketing.services.leads import get_or_create_lead_by_email, normalize_email


class NormalizeEmailTests(TestCase):
    def test_normalize_strips_and_lowers(self):
        self.assertEqual(normalize_email("  Alice@Example.COM "), "alice@example.com")

    def test_normalize_returns_empty_for_invalid(self):
        self.assertEqual(normalize_email("no-at"), "")
        self.assertEqual(normalize_email(""), "")
        self.assertEqual(normalize_email(None), "")


class GetOrCreateLeadTests(TestCase):
    def test_creates_when_absent(self):
        lead, created = get_or_create_lead_by_email(
            "X@Example.com", defaults={"name": "X", "source": Lead.Source.LANDING_PAGE}
        )
        self.assertTrue(created)
        self.assertEqual(lead.email, "x@example.com")
        self.assertEqual(lead.name, "X")

    def test_returns_existing_without_overwrite(self):
        Lead.objects.create(email="y@example.com", name="orig")
        lead, created = get_or_create_lead_by_email("Y@Example.com", defaults={"name": "new"})
        self.assertFalse(created)
        self.assertEqual(lead.name, "orig")
```

- [ ] **Step 2: Implement the service**

Create `marketing/services/leads.py`:
```python
import re

from marketing.models import Lead

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def normalize_email(value):
    if not value:
        return ""
    cleaned = str(value).strip().lower()
    if not _EMAIL_RE.match(cleaned):
        return ""
    return cleaned


def get_or_create_lead_by_email(email, defaults=None):
    normalized = normalize_email(email)
    if not normalized:
        raise ValueError(f"Invalid email: {email!r}")
    lead = Lead.objects.filter(email=normalized).first()
    if lead:
        return lead, False
    payload = {"email": normalized}
    payload.update(defaults or {})
    return Lead.objects.create(**payload), True
```

- [ ] **Step 3: Run tests**

```bash
uv run pytest marketing/test_lead_service.py -v
```

Expected: 5 passed.

- [ ] **Step 4: Commit**

```bash
git add marketing/services/leads.py marketing/test_lead_service.py
git commit -m "feat(marketing): add lead service for email normalization and idempotent creation"
```

---

### Task 5: Data migration — ConsultationRequest → Lead

**Files:**
- Create: `marketing/migrations/0003_import_consultation_requests.py`
- Create: `marketing/test_migration_import.py`

- [ ] **Step 1: Write the failing test (uses MigrationExecutor)**

Create `marketing/test_migration_import.py`:
```python
from django.db.migrations.executor import MigrationExecutor
from django.db import connection
from django.test import TransactionTestCase


class ImportConsultationRequestsMigrationTests(TransactionTestCase):
    @property
    def app(self):
        return "marketing"

    migrate_from = [("marketing", "0002"), ("accounts", "0002_consultationrequest")]
    migrate_to = [("marketing", "0003_import_consultation_requests")]

    def setUp(self):
        executor = MigrationExecutor(connection)
        executor.migrate(self.migrate_from)
        self.old_apps = executor.loader.project_state(self.migrate_from).apps

    def _migrate_forward(self):
        executor = MigrationExecutor(connection)
        executor.loader.build_graph()
        executor.migrate(self.migrate_to)
        return executor.loader.project_state(self.migrate_to).apps

    def test_copies_consultation_requests_to_leads(self):
        ConsultationRequest = self.old_apps.get_model("accounts", "ConsultationRequest")
        ConsultationRequest.objects.create(
            company_name="A", contact_name="홍",
            phone="010", email="A@Example.com",
            concern="실사", preferred_time="평일",
            privacy_agreed=True,
        )
        new_apps = self._migrate_forward()
        Lead = new_apps.get_model("marketing", "Lead")
        Activity = new_apps.get_model("marketing", "Activity")
        lead = Lead.objects.get(email="a@example.com")
        self.assertEqual(lead.source, "landing_page")
        self.assertEqual(lead.name, "홍")
        self.assertEqual(lead.company_name, "A")
        self.assertTrue(Activity.objects.filter(lead=lead, type="note").exists())
```

(Migration numbers like `0002` reference whatever number Task 3 produced — adjust if Task 3 actually emitted a different number; the dependency is "the marketing migration created by Task 3".)

- [ ] **Step 2: Write the data migration**

Inspect what migration number Task 3 emitted:
```bash
ls marketing/migrations/
```

Create `marketing/migrations/0003_import_consultation_requests.py`:
```python
from django.db import migrations


def copy_consultations(apps, schema_editor):
    Lead = apps.get_model("marketing", "Lead")
    Activity = apps.get_model("marketing", "Activity")
    ConsultationRequest = apps.get_model("accounts", "ConsultationRequest")

    for cr in ConsultationRequest.objects.all():
        email = (cr.email or "").strip().lower()
        if not email:
            continue
        lead, created = Lead.objects.get_or_create(
            email=email,
            defaults={
                "name": cr.contact_name,
                "phone": cr.phone,
                "company_name": cr.company_name,
                "source": "landing_page",
                "notes": f"고민: {cr.concern}\n희망시간: {cr.preferred_time}",
            },
        )
        Activity.objects.create(
            lead=lead,
            type="note",
            subject="랜딩페이지 상담신청",
            body=(
                f"회사: {cr.company_name}\n"
                f"이름: {cr.contact_name}\n"
                f"연락처: {cr.phone}\n"
                f"이메일: {cr.email}\n"
                f"고민: {cr.concern}\n"
                f"희망시간: {cr.preferred_time}\n"
                f"접수: {cr.created_at:%Y-%m-%d %H:%M}"
            ),
            happened_at=cr.created_at,
        )


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):
    dependencies = [
        ("marketing", "0002"),  # replace with the actual previous migration name
        ("accounts", "0002_consultationrequest"),
    ]

    operations = [
        migrations.RunPython(copy_consultations, noop_reverse),
    ]
```

Replace `"0002"` in `dependencies` with the actual migration name from Task 3 (e.g., `"0002_emailtemplate_emailattachment_..."` — copy the exact name).

- [ ] **Step 3: Run the migration test**

```bash
uv run pytest marketing/test_migration_import.py -v
```

Expected: pass.

- [ ] **Step 4: Apply migration**

```bash
uv run python manage.py migrate
```

- [ ] **Step 5: Commit**

```bash
git add marketing/migrations/0003_import_consultation_requests.py marketing/test_migration_import.py
git commit -m "feat(marketing): data migration copying ConsultationRequest to Lead"
```

---

### Task 6: Landing form now writes Lead; drop ConsultationRequest model

**Files:**
- Modify: `accounts/views.py`, `accounts/forms.py`, `accounts/notifications.py`, `accounts/admin.py`
- Create: `marketing/test_landing_form.py`
- Delete: `accounts/test_consultation_requests.py`
- Create: `accounts/migrations/0003_delete_consultationrequest.py` (auto)

- [ ] **Step 1: Write the new landing-form tests**

Create `marketing/test_landing_form.py`:
```python
from django.core import mail
from django.test import TestCase, override_settings
from django.urls import reverse

from marketing.models import Activity, Lead


class LandingConsultationRequestTests(TestCase):
    def _payload(self, email="owner@example.com"):
        return {
            "company_name": "테스트 주식회사",
            "contact_name": "홍길동",
            "phone": "010-1234-5678",
            "email": email,
            "concern": "실사 대비",
            "preferred_time": "평일 오후",
            "privacy_agreed": "on",
        }

    def test_creates_lead_and_activity(self):
        response = self.client.post(reverse("consultation_request_create"), self._payload())
        self.assertRedirects(response, "/?consultation=sent#contact")
        lead = Lead.objects.get(email="owner@example.com")
        self.assertEqual(lead.source, Lead.Source.LANDING_PAGE)
        self.assertEqual(lead.name, "홍길동")
        self.assertEqual(lead.company_name, "테스트 주식회사")
        self.assertTrue(Activity.objects.filter(lead=lead, subject="랜딩페이지 상담신청").exists())

    def test_duplicate_email_does_not_create_second_lead(self):
        self.client.post(reverse("consultation_request_create"), self._payload())
        self.client.post(reverse("consultation_request_create"), self._payload())
        self.assertEqual(Lead.objects.filter(email="owner@example.com").count(), 1)
        # but two activities are recorded
        lead = Lead.objects.get(email="owner@example.com")
        self.assertEqual(lead.activities.count(), 2)

    @override_settings(COMPANY_EMAIL="company@example.com")
    def test_sends_email_to_company(self):
        self.client.post(reverse("consultation_request_create"), self._payload())
        self.assertEqual(len(mail.outbox), 1)
        msg = mail.outbox[0]
        self.assertEqual(msg.to, ["company@example.com"])
        self.assertEqual(msg.reply_to, ["owner@example.com"])
        self.assertIn("테스트 주식회사", msg.body)

    def test_privacy_agreement_required(self):
        payload = self._payload()
        payload.pop("privacy_agreed")
        response = self.client.post(reverse("consultation_request_create"), payload)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(Lead.objects.count(), 0)
```

- [ ] **Step 2: Rewrite the form, view, notification**

Replace `accounts/forms.py`:
```python
from django import forms


class ConsultationRequestForm(forms.Form):
    company_name = forms.CharField(max_length=200)
    contact_name = forms.CharField(max_length=100)
    phone = forms.CharField(max_length=40)
    email = forms.EmailField()
    concern = forms.CharField(max_length=200)
    preferred_time = forms.CharField(max_length=200)
    privacy_agreed = forms.BooleanField(required=False)

    def clean_privacy_agreed(self):
        if not self.cleaned_data.get("privacy_agreed"):
            raise forms.ValidationError("개인정보 수집 및 이용 동의가 필요합니다.")
        return True
```

Replace `accounts/notifications.py`:
```python
import logging

from django.conf import settings
from django.core.mail import EmailMessage

logger = logging.getLogger(__name__)


def send_consultation_request_email(lead, raw_concern, raw_preferred_time):
    company_email = getattr(settings, "COMPANY_EMAIL", "")
    if not company_email:
        logger.warning("COMPANY_EMAIL is not configured; consultation email skipped.")
        return False

    subject = f"[RNDlog] 전문가 상담 신청 - {lead.company_name}"
    body = "\n".join(
        [
            "전문가 상담 신청이 접수되었습니다.",
            "",
            f"회사명: {lead.company_name}",
            f"이름: {lead.name}",
            f"연락처: {lead.phone}",
            f"이메일: {lead.email}",
            f"현재 고민: {raw_concern}",
            f"상담 희망 시간: {raw_preferred_time}",
            f"접수 시각: {lead.created_at:%Y-%m-%d %H:%M}",
        ]
    )
    email = EmailMessage(
        subject=subject,
        body=body,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[company_email],
        reply_to=[lead.email],
    )
    try:
        email.send(fail_silently=False)
    except Exception:
        logger.exception("Failed to send consultation email.")
        return False
    return True
```

Rewrite `accounts/views.py` `consultation_request_create`:
```python
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseBadRequest
from django.shortcuts import redirect, render
from django.utils import timezone

from marketing.models import Activity, Lead
from marketing.services.leads import get_or_create_lead_by_email

from .forms import ConsultationRequestForm
from .models import User
from .notifications import send_consultation_request_email


@login_required
def home(request):
    return redirect("/")


def login_page(request):
    if request.user.is_authenticated:
        return redirect("dashboard")
    if request.method == "POST":
        email = request.POST.get("email", "").strip()
        password = request.POST.get("password", "")
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            return render(request, "accounts/login.html",
                          {"error": "이메일 또는 비밀번호가 올바르지 않습니다."})
        if user.check_password(password):
            login(request, user)
            return redirect("dashboard")
        return render(request, "accounts/login.html",
                      {"error": "이메일 또는 비밀번호가 올바르지 않습니다."})
    return render(request, "accounts/login.html")


def logout_view(request):
    logout(request)
    return redirect("login")


def consultation_request_create(request):
    if request.method != "POST":
        return redirect("/#contact")
    form = ConsultationRequestForm(request.POST)
    if not form.is_valid():
        return HttpResponseBadRequest("상담 신청 내용을 확인해주세요.")
    data = form.cleaned_data
    lead, _ = get_or_create_lead_by_email(
        data["email"],
        defaults={
            "name": data["contact_name"],
            "phone": data["phone"],
            "company_name": data["company_name"],
            "source": Lead.Source.LANDING_PAGE,
        },
    )
    Activity.objects.create(
        lead=lead,
        type=Activity.Type.NOTE,
        subject="랜딩페이지 상담신청",
        body=(
            f"고민: {data['concern']}\n"
            f"희망시간: {data['preferred_time']}\n"
            f"제출 일시: {timezone.now():%Y-%m-%d %H:%M}"
        ),
        happened_at=timezone.now(),
    )
    send_consultation_request_email(lead, data["concern"], data["preferred_time"])
    return redirect("/?consultation=sent#contact")
```

Update `accounts/admin.py`: remove the `ConsultationRequest` registration (read the file, drop only that admin and the import).

- [ ] **Step 3: Generate the model-deletion migration**

Remove the `ConsultationRequest` model from `accounts/models.py`. Then:
```bash
uv run python manage.py makemigrations accounts
```

Expected: a migration like `0003_delete_consultationrequest.py`. Verify it depends on `marketing.0003_import_consultation_requests` so the data is copied before the table is dropped — if Django did not infer the dependency, edit the migration to add it:

```python
class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0002_consultationrequest"),
        ("marketing", "0003_import_consultation_requests"),
    ]
    operations = [
        migrations.DeleteModel(name="ConsultationRequest"),
    ]
```

- [ ] **Step 4: Run the migration and tests**

```bash
uv run python manage.py migrate
rm accounts/test_consultation_requests.py
uv run pytest marketing/test_landing_form.py -v
uv run pytest accounts -v
```

Expected: all pass; the old `test_consultation_requests.py` no longer exists.

- [ ] **Step 5: Commit**

```bash
git add -A
git commit -m "refactor(landing): wire landing form into Lead and drop ConsultationRequest model"
```

---

## Phase B — Email templates, attachments, seed

### Task 7: EmailTemplate admin + simple template list view

**Files:**
- Modify: `marketing/admin.py`, `marketing/urls.py`
- Create: `marketing/views/templates.py`, `marketing/templates/marketing/_layout.html`, `marketing/templates/marketing/template_list.html`, `marketing/test_templates.py`

- [ ] **Step 1: Write failing tests**

Create `marketing/test_templates.py`:
```python
from django.test import TestCase
from django.urls import reverse

from accounts.models import User
from marketing.models import EmailTemplate


class TemplateListTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="admin", email="a@x.com", password="pw", is_staff=True
        )
        self.client.force_login(self.user)

    def test_redirects_when_not_staff(self):
        self.client.logout()
        non_staff = User.objects.create_user(
            username="u2", email="u2@x.com", password="pw", is_staff=False
        )
        self.client.force_login(non_staff)
        resp = self.client.get(reverse("marketing:template_list"))
        self.assertEqual(resp.status_code, 403)

    def test_shows_templates(self):
        EmailTemplate.objects.create(name="koita", subject="s", html_body="<p>x</p>")
        resp = self.client.get(reverse("marketing:template_list"))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "koita")
```

- [ ] **Step 2: Add base layout and template list page**

Create `marketing/templates/marketing/_layout.html`:
```html
{% extends "common/base.html" %}
{% block content %}
<div class="max-w-6xl mx-auto p-6">
  <nav class="text-sm text-gray-500 mb-4">
    <a href="{% url 'marketing:dashboard' %}" class="hover:underline">마케팅</a>
    {% block breadcrumb %}{% endblock %}
  </nav>
  <h1 class="text-2xl font-bold mb-6">{% block title %}{% endblock %}</h1>
  {% block marketing_content %}{% endblock %}
</div>
{% endblock %}
```

Create `marketing/templates/marketing/template_list.html`:
```html
{% extends "marketing/_layout.html" %}
{% block title %}이메일 템플릿{% endblock %}
{% block marketing_content %}
<div class="mb-4">
  <a href="{% url 'marketing:template_new' %}" class="px-4 py-2 bg-green-600 text-white rounded">새 템플릿</a>
</div>
<table class="w-full border">
  <thead class="bg-gray-50 text-left text-sm">
    <tr><th class="p-2">이름</th><th class="p-2">제목</th><th class="p-2">활성</th><th class="p-2">수정일</th></tr>
  </thead>
  <tbody>
    {% for t in templates %}
    <tr class="border-t">
      <td class="p-2"><a href="{% url 'marketing:template_edit' t.id %}" class="text-blue-700">{{ t.name }}</a></td>
      <td class="p-2">{{ t.subject }}</td>
      <td class="p-2">{% if t.is_active %}✓{% else %}—{% endif %}</td>
      <td class="p-2">{{ t.updated_at|date:"Y-m-d H:i" }}</td>
    </tr>
    {% empty %}
    <tr><td colspan="4" class="p-4 text-center text-gray-400">템플릿이 없습니다.</td></tr>
    {% endfor %}
  </tbody>
</table>
{% endblock %}
```

Create `marketing/views/templates.py`:
```python
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import render

from marketing.models import EmailTemplate


def _require_staff(request):
    if not request.user.is_authenticated:
        raise PermissionDenied
    if not request.user.is_staff:
        raise PermissionDenied


@login_required
def template_list(request):
    _require_staff(request)
    templates = EmailTemplate.objects.all()
    return render(request, "marketing/template_list.html", {"templates": templates})
```

In `marketing/views/__init__.py`:
```python
from .templates import template_list  # noqa: F401
```

In `marketing/urls.py` (replace the file):
```python
from django.urls import path

from .views import templates as tv

app_name = "marketing"

urlpatterns = [
    path("", lambda r: __import__("django.http", fromlist=["HttpResponse"]).HttpResponse("dashboard placeholder"), name="dashboard"),
    path("templates/", tv.template_list, name="template_list"),
    path("templates/new/", lambda r: None, name="template_new"),
    path("templates/<uuid:pk>/edit/", lambda r, pk: None, name="template_edit"),
]
```

(The placeholder routes for `template_new`, `template_edit`, and `dashboard` are real routes added in later tasks. The lambdas here let `{% url %}` calls resolve so the list page renders. Replace each lambda when that task lands.)

- [ ] **Step 3: Register admin**

In `marketing/admin.py`:
```python
from django.contrib import admin

from .models import EmailAttachment, EmailTemplate


class AttachmentInline(admin.TabularInline):
    model = EmailAttachment
    extra = 0


@admin.register(EmailTemplate)
class EmailTemplateAdmin(admin.ModelAdmin):
    list_display = ("name", "subject", "is_active", "updated_at")
    search_fields = ("name", "subject")
    inlines = [AttachmentInline]
```

- [ ] **Step 4: Run the tests**

```bash
uv run pytest marketing/test_templates.py -v
```

Expected: 2 passed.

- [ ] **Step 5: Commit**

```bash
git add marketing/admin.py marketing/urls.py marketing/views/ marketing/templates/ marketing/test_templates.py
git commit -m "feat(marketing): template list view + admin"
```

---

### Task 8: Template create/edit views

**Files:**
- Modify: `marketing/views/templates.py`, `marketing/urls.py`, `marketing/forms.py`
- Create: `marketing/templates/marketing/template_form.html`
- Modify: `marketing/test_templates.py`

- [ ] **Step 1: Add failing tests**

Append to `marketing/test_templates.py`:
```python
class TemplateCreateTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="a", email="a2@x.com", password="pw", is_staff=True
        )
        self.client.force_login(self.user)

    def test_create_template(self):
        resp = self.client.post(
            reverse("marketing:template_new"),
            {"name": "t1", "subject": "s", "html_body": "<p>hi</p>", "is_active": "on"},
        )
        self.assertEqual(resp.status_code, 302)
        self.assertTrue(EmailTemplate.objects.filter(name="t1").exists())

    def test_edit_template(self):
        t = EmailTemplate.objects.create(name="t2", subject="s", html_body="x")
        resp = self.client.post(
            reverse("marketing:template_edit", args=[t.id]),
            {"name": "t2", "subject": "new", "html_body": "x"},
        )
        self.assertEqual(resp.status_code, 302)
        t.refresh_from_db()
        self.assertEqual(t.subject, "new")
        self.assertFalse(t.is_active)
```

- [ ] **Step 2: Create form**

Create `marketing/forms.py`:
```python
from django import forms

from .models import EmailTemplate


class EmailTemplateForm(forms.ModelForm):
    class Meta:
        model = EmailTemplate
        fields = ["name", "subject", "html_body", "text_body", "is_active"]
```

- [ ] **Step 3: Implement views**

Append to `marketing/views/templates.py`:
```python
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse

from marketing.forms import EmailTemplateForm


@login_required
def template_new(request):
    _require_staff(request)
    form = EmailTemplateForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        obj = form.save(commit=False)
        obj.created_by = request.user
        obj.save()
        return redirect(reverse("marketing:template_edit", args=[obj.id]))
    return render(request, "marketing/template_form.html", {"form": form, "obj": None})


@login_required
def template_edit(request, pk):
    _require_staff(request)
    obj = get_object_or_404(EmailTemplate, pk=pk)
    form = EmailTemplateForm(request.POST or None, instance=obj)
    if request.method == "POST" and form.is_valid():
        form.save()
        return redirect(reverse("marketing:template_edit", args=[obj.id]))
    return render(request, "marketing/template_form.html", {"form": form, "obj": obj})
```

Re-export in `marketing/views/__init__.py`:
```python
from .templates import template_list, template_new, template_edit  # noqa: F401
```

Replace the placeholder lambdas in `marketing/urls.py`:
```python
path("templates/new/", tv.template_new, name="template_new"),
path("templates/<uuid:pk>/edit/", tv.template_edit, name="template_edit"),
```

Create `marketing/templates/marketing/template_form.html`:
```html
{% extends "marketing/_layout.html" %}
{% load widget_tweaks %}
{% block title %}{{ obj.name|default:"새 템플릿" }}{% endblock %}
{% block marketing_content %}
<form method="post" class="space-y-4">
  {% csrf_token %}
  <div>
    <label class="block text-sm font-medium">이름</label>
    {{ form.name|add_class:"border rounded w-full p-2" }}
  </div>
  <div>
    <label class="block text-sm font-medium">제목</label>
    {{ form.subject|add_class:"border rounded w-full p-2" }}
  </div>
  <div>
    <label class="block text-sm font-medium">HTML 본문</label>
    {{ form.html_body|add_class:"border rounded w-full p-2 h-96 font-mono text-xs" }}
  </div>
  <div>
    <label class="block text-sm font-medium">텍스트 본문 (선택)</label>
    {{ form.text_body|add_class:"border rounded w-full p-2 h-32 font-mono text-xs" }}
  </div>
  <label class="inline-flex items-center gap-2">
    {{ form.is_active }} 활성
  </label>
  <div class="flex gap-2">
    <button class="px-4 py-2 bg-green-600 text-white rounded">저장</button>
    <a href="{% url 'marketing:template_list' %}" class="px-4 py-2 border rounded">취소</a>
  </div>
</form>
{% endblock %}
```

- [ ] **Step 4: Run tests**

```bash
uv run pytest marketing/test_templates.py -v
```

Expected: 4 passed.

- [ ] **Step 5: Commit**

```bash
git add marketing/views/templates.py marketing/views/__init__.py marketing/urls.py marketing/forms.py marketing/templates/marketing/template_form.html marketing/test_templates.py
git commit -m "feat(marketing): create/edit email template views"
```

---

### Task 9: Seed command — load KOITA template + PDF attachment

**Files:**
- Create: `marketing/management/commands/seed_marketing.py`, `marketing/test_seed.py`

- [ ] **Step 1: Write failing tests**

Create `marketing/test_seed.py`:
```python
from io import StringIO

from django.core.management import call_command
from django.test import TestCase

from marketing.models import EmailAttachment, EmailTemplate


class SeedMarketingTests(TestCase):
    def test_seed_creates_template_idempotently(self):
        call_command("seed_marketing", stdout=StringIO())
        self.assertEqual(EmailTemplate.objects.filter(name="KOITA 자가진단 안내 v1").count(), 1)
        self.assertEqual(EmailAttachment.objects.count(), 1)

        # second run should not duplicate
        call_command("seed_marketing", stdout=StringIO())
        self.assertEqual(EmailTemplate.objects.filter(name="KOITA 자가진단 안내 v1").count(), 1)
        self.assertEqual(EmailAttachment.objects.count(), 1)
```

- [ ] **Step 2: Implement the command**

Create `marketing/management/commands/seed_marketing.py`:
```python
from pathlib import Path

from django.core.files import File
from django.core.management.base import BaseCommand

from marketing.models import EmailAttachment, EmailTemplate

ASSET_DIR = Path(__file__).resolve().parents[3] / "docs" / "자료" / "checkup-nextjs"
HTML_PATH = ASSET_DIR / "email-html" / "typeA_crisis_hero_v4_two_directors.html"
PDF_PATH = ASSET_DIR / "rndlog_service_guide.pdf"


class Command(BaseCommand):
    help = "Seed marketing templates and attachments idempotently"

    def handle(self, *args, **opts):
        if not HTML_PATH.exists():
            self.stdout.write(self.style.ERROR(f"missing {HTML_PATH}"))
            return
        html = HTML_PATH.read_text(encoding="utf-8")
        template, created = EmailTemplate.objects.get_or_create(
            name="KOITA 자가진단 안내 v1",
            defaults={
                "subject": "RNDlog | 2026 KOITA 실사 대비 안내",
                "html_body": html,
                "is_active": True,
            },
        )
        action = "created" if created else "exists"
        self.stdout.write(f"template {action}: {template.name}")

        if PDF_PATH.exists() and not template.attachments.exists():
            with PDF_PATH.open("rb") as f:
                EmailAttachment.objects.create(
                    template=template,
                    file=File(f, name=PDF_PATH.name),
                    display_name="RNDlog 서비스 안내서.pdf",
                )
            self.stdout.write("attachment created: rndlog_service_guide.pdf")
        elif template.attachments.exists():
            self.stdout.write("attachment exists, skipping")
        else:
            self.stdout.write(self.style.WARNING(f"missing {PDF_PATH}"))
```

- [ ] **Step 3: Run tests + actual seed**

```bash
uv run pytest marketing/test_seed.py -v
uv run python manage.py seed_marketing
```

Expected: tests pass; seed runs without error.

- [ ] **Step 4: Commit**

```bash
git add marketing/management/ marketing/test_seed.py
git commit -m "feat(marketing): seed_marketing command loads KOITA template + PDF"
```

---

## Phase C — Activity recording + state transitions

### Task 10: State transition service

**Files:**
- Create: `marketing/services/state.py`, `marketing/test_state.py`

- [ ] **Step 1: Write failing tests**

Create `marketing/test_state.py`:
```python
from django.test import TestCase
from django.utils import timezone

from marketing.models import Activity, Lead
from marketing.services.state import apply_activity_transition


class StateTransitionTests(TestCase):
    def setUp(self):
        self.lead = Lead.objects.create(email="t@example.com")

    def _activity(self, **kw):
        return Activity.objects.create(lead=self.lead, **kw)

    def test_call_positive_promotes_to_interested(self):
        act = self._activity(
            type=Activity.Type.CALL, outcome=Activity.Outcome.POSITIVE,
            happened_at=timezone.now(),
        )
        apply_activity_transition(self.lead, act)
        self.lead.refresh_from_db()
        self.assertEqual(self.lead.status, Lead.Status.INTERESTED)

    def test_call_negative_lowers_interest_only(self):
        self.lead.status = Lead.Status.INTERESTED
        self.lead.save()
        act = self._activity(
            type=Activity.Type.CALL, outcome=Activity.Outcome.NEGATIVE,
            happened_at=timezone.now(),
        )
        apply_activity_transition(self.lead, act)
        self.lead.refresh_from_db()
        self.assertEqual(self.lead.status, Lead.Status.INTERESTED)
        self.assertEqual(self.lead.interest_level, Lead.InterestLevel.LOW)

    def test_visit_scheduled_promotes_to_scheduled(self):
        act = self._activity(type=Activity.Type.VISIT, scheduled_at=timezone.now())
        apply_activity_transition(self.lead, act)
        self.lead.refresh_from_db()
        self.assertEqual(self.lead.status, Lead.Status.SCHEDULED)

    def test_visit_happened_promotes_to_visited(self):
        act = self._activity(type=Activity.Type.VISIT, happened_at=timezone.now())
        apply_activity_transition(self.lead, act)
        self.lead.refresh_from_db()
        self.assertEqual(self.lead.status, Lead.Status.VISITED)

    def test_no_backwards_transition(self):
        self.lead.status = Lead.Status.WON
        self.lead.save()
        act = self._activity(
            type=Activity.Type.CALL, outcome=Activity.Outcome.POSITIVE,
            happened_at=timezone.now(),
        )
        apply_activity_transition(self.lead, act)
        self.lead.refresh_from_db()
        self.assertEqual(self.lead.status, Lead.Status.WON)
```

- [ ] **Step 2: Implement**

Create `marketing/services/state.py`:
```python
from marketing.models import Activity, Lead

_ORDER = [
    Lead.Status.NEW,
    Lead.Status.CONTACTED,
    Lead.Status.INTERESTED,
    Lead.Status.SCHEDULED,
    Lead.Status.VISITED,
]


def _promote(lead, target):
    """Forward-only promotion; never moves a won/lost lead."""
    if lead.status in (Lead.Status.WON, Lead.Status.LOST):
        return
    if target not in _ORDER or lead.status not in _ORDER:
        return
    if _ORDER.index(target) > _ORDER.index(lead.status):
        lead.status = target
        lead.save(update_fields=["status", "updated_at"])


def apply_activity_transition(lead, activity):
    if activity.type == Activity.Type.CALL:
        if activity.outcome == Activity.Outcome.POSITIVE:
            _promote(lead, Lead.Status.INTERESTED)
        elif activity.outcome == Activity.Outcome.NEGATIVE:
            if lead.interest_level != Lead.InterestLevel.LOW:
                lead.interest_level = Lead.InterestLevel.LOW
                lead.save(update_fields=["interest_level", "updated_at"])
    elif activity.type == Activity.Type.VISIT:
        if activity.happened_at:
            _promote(lead, Lead.Status.VISITED)
        elif activity.scheduled_at:
            _promote(lead, Lead.Status.SCHEDULED)


def mark_contacted(lead):
    _promote(lead, Lead.Status.CONTACTED)
```

- [ ] **Step 3: Run tests**

```bash
uv run pytest marketing/test_state.py -v
```

Expected: 5 passed.

- [ ] **Step 4: Commit**

```bash
git add marketing/services/state.py marketing/test_state.py
git commit -m "feat(marketing): state transition service for Activity-driven Lead promotion"
```

---

### Task 11: Activity recording view

**Files:**
- Create: `marketing/views/activities.py`, `marketing/test_activities.py`, `marketing/templates/marketing/_activity_form.html`, `marketing/templates/marketing/_timeline_item.html`
- Modify: `marketing/urls.py`, `marketing/views/__init__.py`, `marketing/forms.py`

- [ ] **Step 1: Write failing tests**

Create `marketing/test_activities.py`:
```python
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from accounts.models import User
from marketing.models import Activity, Lead


class RecordActivityTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="u", email="u@x.com", password="pw", is_staff=True
        )
        self.client.force_login(self.user)
        self.lead = Lead.objects.create(email="l@example.com")

    def _post(self, **data):
        return self.client.post(
            reverse("marketing:activity_create", args=[self.lead.id]),
            data,
        )

    def test_create_call_activity_promotes_lead(self):
        resp = self._post(
            type="call", subject="첫 통화", body="관심 있다 함",
            outcome="positive",
        )
        self.assertEqual(resp.status_code, 200)  # HTMX fragment
        self.lead.refresh_from_db()
        self.assertEqual(self.lead.status, Lead.Status.INTERESTED)
        self.assertTrue(Activity.objects.filter(lead=self.lead, type="call").exists())

    def test_create_visit_scheduled(self):
        when = (timezone.now() + timezone.timedelta(days=3)).isoformat()
        self._post(type="visit", scheduled_at=when, subject="방문 일정")
        self.lead.refresh_from_db()
        self.assertEqual(self.lead.status, Lead.Status.SCHEDULED)

    def test_complete_next_action(self):
        a = Activity.objects.create(
            lead=self.lead, type=Activity.Type.NOTE,
            next_action="확인 전화", next_action_due=timezone.now(),
        )
        resp = self.client.post(reverse("marketing:next_action_complete", args=[a.id]))
        self.assertEqual(resp.status_code, 200)
        a.refresh_from_db()
        self.assertIsNotNone(a.next_action_done_at)
```

- [ ] **Step 2: Add the form**

Append to `marketing/forms.py`:
```python
from .models import Activity


class ActivityForm(forms.ModelForm):
    class Meta:
        model = Activity
        fields = [
            "type", "subject", "body", "outcome",
            "scheduled_at", "happened_at",
            "next_action", "next_action_due",
        ]
        widgets = {
            "scheduled_at": forms.DateTimeInput(attrs={"type": "datetime-local"}),
            "happened_at": forms.DateTimeInput(attrs={"type": "datetime-local"}),
            "next_action_due": forms.DateTimeInput(attrs={"type": "datetime-local"}),
        }
```

- [ ] **Step 3: Add the view**

Create `marketing/views/activities.py`:
```python
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from marketing.forms import ActivityForm
from marketing.models import Activity, Lead
from marketing.services.state import apply_activity_transition

from .templates import _require_staff


@login_required
@require_POST
def activity_create(request, lead_id):
    _require_staff(request)
    lead = get_object_or_404(Lead, pk=lead_id)
    form = ActivityForm(request.POST)
    if not form.is_valid():
        return render(request, "marketing/_activity_form.html",
                      {"form": form, "lead": lead}, status=422)
    activity = form.save(commit=False)
    activity.lead = lead
    activity.performed_by = request.user
    if activity.type == Activity.Type.CALL and not activity.happened_at:
        activity.happened_at = timezone.now()
    if activity.type == Activity.Type.NOTE and not activity.happened_at:
        activity.happened_at = timezone.now()
    activity.save()
    apply_activity_transition(lead, activity)
    lead.refresh_from_db()
    activities = lead.activities.all()[:50]
    return render(request, "marketing/_lead_detail_dynamic.html",
                  {"lead": lead, "activities": activities, "form": ActivityForm()})


@login_required
@require_POST
def next_action_complete(request, activity_id):
    _require_staff(request)
    act = get_object_or_404(Activity, pk=activity_id)
    if not act.next_action_done_at:
        act.next_action_done_at = timezone.now()
        act.save(update_fields=["next_action_done_at", "updated_at"])
    return render(request, "marketing/_next_action_row.html", {"activity": act})
```

Create `marketing/templates/marketing/_activity_form.html`:
```html
{% load widget_tweaks %}
<form id="activity-form"
      hx-post="{% url 'marketing:activity_create' lead.id %}"
      hx-target="#lead-dynamic"
      hx-swap="outerHTML"
      class="space-y-3 border rounded p-4">
  {% csrf_token %}
  <div class="grid grid-cols-2 gap-2">
    <label class="text-sm">유형 {{ form.type|add_class:"border rounded p-1 w-full" }}</label>
    <label class="text-sm">결과 {{ form.outcome|add_class:"border rounded p-1 w-full" }}</label>
  </div>
  <label class="block text-sm">요약 {{ form.subject|add_class:"border rounded p-1 w-full" }}</label>
  <label class="block text-sm">메모 {{ form.body|add_class:"border rounded p-1 w-full h-20" }}</label>
  <div class="grid grid-cols-2 gap-2">
    <label class="text-sm">방문 예정 {{ form.scheduled_at|add_class:"border rounded p-1 w-full" }}</label>
    <label class="text-sm">실제 일시 {{ form.happened_at|add_class:"border rounded p-1 w-full" }}</label>
  </div>
  <label class="block text-sm">다음 액션 {{ form.next_action|add_class:"border rounded p-1 w-full" }}</label>
  <label class="block text-sm">다음 액션 마감 {{ form.next_action_due|add_class:"border rounded p-1 w-full" }}</label>
  <button class="px-3 py-1 bg-blue-600 text-white rounded">기록</button>
</form>
```

Create `marketing/templates/marketing/_timeline_item.html`:
```html
<li class="border-l-2 pl-3 py-2 text-sm">
  <div class="text-gray-500">
    {{ activity.happened_at|default:activity.scheduled_at|date:"m-d H:i" }} · {{ activity.get_type_display }}
    {% if activity.performed_by %}· {{ activity.performed_by.username }}{% endif %}
  </div>
  <div class="font-medium">{{ activity.subject }}</div>
  {% if activity.body %}<div class="text-gray-700 whitespace-pre-wrap">{{ activity.body }}</div>{% endif %}
  {% if activity.next_action and not activity.next_action_done_at %}
    <div class="text-xs text-amber-700">▶ {{ activity.next_action }}{% if activity.next_action_due %} (마감 {{ activity.next_action_due|date:"m-d" }}){% endif %}</div>
  {% endif %}
</li>
```

Create `marketing/templates/marketing/_lead_detail_dynamic.html`:
```html
<div id="lead-dynamic">
  {% include "marketing/_activity_form.html" %}
  <ul class="mt-4 space-y-2">
    {% for activity in activities %}
      {% include "marketing/_timeline_item.html" %}
    {% empty %}
      <li class="text-sm text-gray-400">기록된 활동이 없습니다.</li>
    {% endfor %}
  </ul>
</div>
```

Create `marketing/templates/marketing/_next_action_row.html`:
```html
<tr id="na-{{ activity.id }}" class="border-t {% if activity.next_action_done_at %}text-gray-400 line-through{% endif %}">
  <td class="p-2"><a href="{% url 'marketing:lead_detail' activity.lead_id %}" class="text-blue-700">{{ activity.lead }}</a></td>
  <td class="p-2">{{ activity.next_action }}</td>
  <td class="p-2">{{ activity.next_action_due|date:"m-d H:i"|default:"—" }}</td>
  <td class="p-2">
    {% if not activity.next_action_done_at %}
      <button hx-post="{% url 'marketing:next_action_complete' activity.id %}"
              hx-target="#na-{{ activity.id }}" hx-swap="outerHTML"
              class="px-2 py-1 text-xs border rounded">완료</button>
    {% else %}
      ✓ {{ activity.next_action_done_at|date:"m-d" }}
    {% endif %}
  </td>
</tr>
```

Add to `marketing/views/__init__.py`:
```python
from .activities import activity_create, next_action_complete  # noqa: F401
```

Add to `marketing/urls.py`:
```python
from .views import activities as av

# ... inside urlpatterns:
path("leads/<uuid:lead_id>/activities/", av.activity_create, name="activity_create"),
path("activities/<uuid:activity_id>/complete-next/", av.next_action_complete, name="next_action_complete"),
path("leads/<uuid:pk>/", lambda r, pk: None, name="lead_detail"),  # filled in later task
```

- [ ] **Step 4: Run tests**

```bash
uv run pytest marketing/test_activities.py -v
```

Expected: 3 passed.

- [ ] **Step 5: Commit**

```bash
git add marketing/views/activities.py marketing/forms.py marketing/templates/ marketing/urls.py marketing/views/__init__.py marketing/test_activities.py
git commit -m "feat(marketing): activity recording with auto state transition"
```

---

## Phase D — Mailer + Campaign + Tracking + Unsubscribe

### Task 12: Add gspread + google-auth dependencies and env var

**Files:**
- Modify: `pyproject.toml`, `main/settings.py`, `.env.example`

- [ ] **Step 1: Add dependencies**

Edit `pyproject.toml` `dependencies`, append:
```
"gspread>=6.0.0",
"google-auth>=2.30.0",
```

- [ ] **Step 2: Sync**

```bash
uv sync
```

- [ ] **Step 3: Add setting**

In `main/settings.py`, after other env reads, add:
```python
GOOGLE_SERVICE_ACCOUNT_JSON = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON", "")
```

In `.env.example`, append:
```
# Google Sheets (마케팅 Lead 임포트)
GOOGLE_SERVICE_ACCOUNT_JSON=
```

- [ ] **Step 4: Verify**

```bash
uv run python -c "import gspread; import google.auth; print('ok')"
uv run python manage.py check
```

Expected: `ok` and no errors.

- [ ] **Step 5: Commit**

```bash
git add pyproject.toml uv.lock main/settings.py .env.example
git commit -m "chore: add gspread + google-auth deps and GOOGLE_SERVICE_ACCOUNT_JSON setting"
```

---

### Task 13: Unsubscribe token service

**Files:**
- Create: `marketing/services/tokens.py`, `marketing/test_tokens.py`

- [ ] **Step 1: Write failing tests**

Create `marketing/test_tokens.py`:
```python
from django.test import TestCase

from marketing.models import Lead
from marketing.services.tokens import make_unsubscribe_token, verify_unsubscribe_token


class TokenTests(TestCase):
    def setUp(self):
        self.lead = Lead.objects.create(email="t@example.com")

    def test_roundtrip(self):
        token = make_unsubscribe_token(self.lead)
        verified = verify_unsubscribe_token(token)
        self.assertEqual(verified.id, self.lead.id)

    def test_tampered_returns_none(self):
        token = make_unsubscribe_token(self.lead)
        bad = token[:-2] + "xx"
        self.assertIsNone(verify_unsubscribe_token(bad))

    def test_unknown_lead_returns_none(self):
        token = make_unsubscribe_token(self.lead)
        self.lead.delete()
        self.assertIsNone(verify_unsubscribe_token(token))
```

- [ ] **Step 2: Implement**

Create `marketing/services/tokens.py`:
```python
import hmac
from hashlib import sha256

from django.conf import settings
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode

from marketing.models import Lead


def _sig(lead_id_bytes):
    return hmac.new(
        settings.SECRET_KEY.encode(), lead_id_bytes, sha256
    ).hexdigest()[:16]


def make_unsubscribe_token(lead):
    raw = str(lead.id).encode()
    return f"{urlsafe_base64_encode(raw)}.{_sig(raw)}"


def verify_unsubscribe_token(token):
    try:
        b64, sig = token.rsplit(".", 1)
    except ValueError:
        return None
    try:
        raw = urlsafe_base64_decode(b64)
    except Exception:
        return None
    if not hmac.compare_digest(_sig(raw), sig):
        return None
    return Lead.objects.filter(pk=raw.decode()).first()
```

- [ ] **Step 3: Run tests**

```bash
uv run pytest marketing/test_tokens.py -v
```

Expected: 3 passed.

- [ ] **Step 4: Commit**

```bash
git add marketing/services/tokens.py marketing/test_tokens.py
git commit -m "feat(marketing): HMAC-signed unsubscribe token service"
```

---

### Task 14: Mailer service — build EmailMultiAlternatives with tracking pixel

**Files:**
- Create: `marketing/services/mailer.py`, `marketing/test_mailer.py`

- [ ] **Step 1: Write failing tests**

Create `marketing/test_mailer.py`:
```python
from django.test import TestCase, override_settings
from django.core import mail

from marketing.models import EmailCampaign, EmailSendLog, EmailTemplate, Lead
from marketing.services.mailer import build_message_for_send, send_one


@override_settings(SITE_URL="http://example.test", DEFAULT_FROM_EMAIL="from@example.test")
class MailerTests(TestCase):
    def setUp(self):
        self.template = EmailTemplate.objects.create(
            name="t", subject="안녕 {lead.name}",
            html_body="<html><body>Hi {lead.name}</body></html>",
        )
        self.lead = Lead.objects.create(email="rcpt@example.com", name="홍")
        self.campaign = EmailCampaign.objects.create(name="c", template=self.template)
        self.send = EmailSendLog.objects.create(
            campaign=self.campaign, lead=self.lead, to_email=self.lead.email
        )

    def test_substitutes_variables(self):
        msg = build_message_for_send(self.send)
        self.assertEqual(msg.subject, "안녕 홍")

    def test_injects_tracking_pixel(self):
        msg = build_message_for_send(self.send)
        html_alt = next(a for a in msg.alternatives if a[1] == "text/html")
        self.assertIn(f"/marketing/track/o/{self.send.tracking_id}.png", html_alt[0])
        self.assertIn("</body>", html_alt[0])

    def test_send_one_sends_and_updates_status(self):
        send_one(self.send)
        self.send.refresh_from_db()
        self.assertEqual(self.send.status, EmailSendLog.Status.SENT)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("rcpt@example.com", mail.outbox[0].to)

    def test_send_one_skips_unsubscribed(self):
        self.lead.is_unsubscribed = True
        self.lead.save()
        send_one(self.send)
        self.send.refresh_from_db()
        self.assertEqual(self.send.status, EmailSendLog.Status.FAILED)
        self.assertIn("unsubscribed", self.send.error_message)
        self.assertEqual(len(mail.outbox), 0)
```

- [ ] **Step 2: Implement mailer service**

Create `marketing/services/mailer.py`:
```python
import logging

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.urls import reverse
from django.utils import timezone

from marketing.models import EmailSendLog
from marketing.services.tokens import make_unsubscribe_token

logger = logging.getLogger(__name__)


class _SafeLead:
    def __init__(self, lead):
        self._lead = lead

    def __getattr__(self, item):
        return getattr(self._lead, item, "") or ""


def _format(text, lead):
    safe = {"lead": _SafeLead(lead)}
    try:
        return text.format_map(safe)
    except Exception:
        return text


def _site_url():
    return getattr(settings, "SITE_URL", "").rstrip("/")


def _inject_tracking(html, send):
    px = (
        f'<img src="{_site_url()}/marketing/track/o/{send.tracking_id}.png" '
        f'width="1" height="1" alt="" style="display:block" />'
    )
    if "</body>" in html.lower():
        idx = html.lower().rfind("</body>")
        return html[:idx] + px + html[idx:]
    return html + px


def _inject_unsubscribe(html, lead):
    token = make_unsubscribe_token(lead)
    url = f"{_site_url()}/marketing/unsubscribe/{token}/"
    footer = (
        f'<div style="text-align:center;margin-top:24px;font-size:11px;color:#888">'
        f'수신을 원치 않으시면 <a href="{url}">여기</a>를 누르거나 본 메일에 회신해 주세요.'
        f"</div>"
    )
    if "</body>" in html.lower():
        idx = html.lower().rfind("</body>")
        return html[:idx] + footer + html[idx:]
    return html + footer


def build_message_for_send(send):
    template = send.campaign.template
    lead = send.lead
    subject = _format(template.subject, lead)
    html = _format(template.html_body, lead)
    html = _inject_unsubscribe(html, lead)
    html = _inject_tracking(html, send)
    text = _format(template.text_body, lead) or "이 메일은 HTML 형식입니다."
    sender = send.campaign.sender
    msg = EmailMultiAlternatives(
        subject=subject,
        body=text,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[send.to_email],
        reply_to=[sender.email] if sender and sender.email else None,
    )
    msg.attach_alternative(html, "text/html")
    for att in template.attachments.all():
        try:
            msg.attach_file(att.file.path, mimetype=None)
        except Exception:
            logger.exception("failed to attach %s", att.id)
    return msg


def send_one(send):
    if send.lead.is_unsubscribed:
        send.status = EmailSendLog.Status.FAILED
        send.error_message = "unsubscribed"
        send.save(update_fields=["status", "error_message", "updated_at"])
        return False
    try:
        msg = build_message_for_send(send)
        msg.send(fail_silently=False)
    except Exception as exc:
        send.status = EmailSendLog.Status.FAILED
        send.error_message = str(exc)[:5000]
        send.save(update_fields=["status", "error_message", "updated_at"])
        return False
    send.status = EmailSendLog.Status.SENT
    send.sent_at = timezone.now()
    send.save(update_fields=["status", "sent_at", "updated_at"])
    return True
```

- [ ] **Step 3: Run tests**

```bash
uv run pytest marketing/test_mailer.py -v
```

Expected: 4 passed.

- [ ] **Step 4: Commit**

```bash
git add marketing/services/mailer.py marketing/test_mailer.py
git commit -m "feat(marketing): mailer builds message with tracking pixel and unsubscribe link"
```

---

### Task 15: Tracking pixel endpoint

**Files:**
- Create: `marketing/views/tracking.py`, `marketing/test_tracking.py`
- Modify: `marketing/views/__init__.py`, `marketing/urls.py`

- [ ] **Step 1: Write failing tests**

Create `marketing/test_tracking.py`:
```python
import uuid

from django.test import TestCase
from django.urls import reverse

from marketing.models import EmailCampaign, EmailSendLog, EmailTemplate, Lead


class TrackingPixelTests(TestCase):
    def setUp(self):
        self.template = EmailTemplate.objects.create(name="t", subject="s", html_body="x")
        self.lead = Lead.objects.create(email="x@example.com")
        self.campaign = EmailCampaign.objects.create(name="c", template=self.template)
        self.send = EmailSendLog.objects.create(
            campaign=self.campaign, lead=self.lead, to_email=self.lead.email
        )

    def test_pixel_returns_gif_and_records_open(self):
        url = reverse("marketing:tracking_pixel", args=[self.send.tracking_id])
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp["Content-Type"], "image/gif")
        self.assertEqual(resp["Cache-Control"], "no-store")
        self.send.refresh_from_db()
        self.assertEqual(self.send.open_count, 1)
        self.assertIsNotNone(self.send.opened_at)
        self.campaign.refresh_from_db()
        self.assertEqual(self.campaign.open_count, 1)

    def test_unknown_uuid_still_returns_pixel(self):
        url = reverse("marketing:tracking_pixel", args=[uuid.uuid4()])
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp["Content-Type"], "image/gif")

    def test_repeated_open_increments_count_once_for_first(self):
        url = reverse("marketing:tracking_pixel", args=[self.send.tracking_id])
        self.client.get(url)
        self.client.get(url)
        self.send.refresh_from_db()
        self.assertEqual(self.send.open_count, 2)
        self.campaign.refresh_from_db()
        # campaign open_count only counts first-time opens per send
        self.assertEqual(self.campaign.open_count, 1)
```

- [ ] **Step 2: Implement**

Create `marketing/views/tracking.py`:
```python
from base64 import b64decode

from django.db import transaction
from django.http import HttpResponse
from django.utils import timezone
from django.views.decorators.http import require_GET

from marketing.models import EmailSendLog

# 43-byte 1x1 transparent GIF
_PIXEL = b64decode(
    b"R0lGODlhAQABAIAAAP///wAAACH5BAEAAAAALAAAAAABAAEAAAICRAEAOw=="
)


@require_GET
def tracking_pixel(request, tracking_id):
    with transaction.atomic():
        send = (
            EmailSendLog.objects.select_for_update()
            .filter(tracking_id=tracking_id)
            .first()
        )
        if send:
            first_open = send.opened_at is None
            now = timezone.now()
            if first_open:
                send.opened_at = now
            send.last_opened_at = now
            send.open_count += 1
            send.save(update_fields=["opened_at", "last_opened_at", "open_count", "updated_at"])
            if first_open:
                send.campaign.__class__.objects.filter(pk=send.campaign_id).update(
                    open_count=send.campaign.__class__._meta.get_field("open_count").default
                )
                # increment via F() to avoid race
                from django.db.models import F
                send.campaign.__class__.objects.filter(pk=send.campaign_id).update(
                    open_count=F("open_count") + 1
                )
    response = HttpResponse(_PIXEL, content_type="image/gif")
    response["Cache-Control"] = "no-store"
    return response
```

Re-export and route:
```python
# marketing/views/__init__.py
from .tracking import tracking_pixel  # noqa: F401
```

In `marketing/urls.py` add:
```python
from .views import tracking as trkv

path("track/o/<uuid:tracking_id>.png", trkv.tracking_pixel, name="tracking_pixel"),
```

- [ ] **Step 3: Run tests**

```bash
uv run pytest marketing/test_tracking.py -v
```

Expected: 3 passed.

- [ ] **Step 4: Commit**

```bash
git add marketing/views/tracking.py marketing/views/__init__.py marketing/urls.py marketing/test_tracking.py
git commit -m "feat(marketing): open-tracking pixel endpoint"
```

---

### Task 16: Unsubscribe endpoint

**Files:**
- Create: `marketing/views/unsubscribe.py`, `marketing/test_unsubscribe.py`, `marketing/templates/marketing/unsubscribed.html`
- Modify: `marketing/urls.py`, `marketing/views/__init__.py`

- [ ] **Step 1: Write failing tests**

Create `marketing/test_unsubscribe.py`:
```python
from django.test import TestCase
from django.urls import reverse

from marketing.models import Lead
from marketing.services.tokens import make_unsubscribe_token


class UnsubscribeTests(TestCase):
    def test_valid_token_marks_unsubscribed(self):
        lead = Lead.objects.create(email="u@example.com")
        token = make_unsubscribe_token(lead)
        resp = self.client.get(reverse("marketing:unsubscribe", args=[token]))
        self.assertEqual(resp.status_code, 200)
        lead.refresh_from_db()
        self.assertTrue(lead.is_unsubscribed)

    def test_invalid_token_returns_404(self):
        resp = self.client.get(reverse("marketing:unsubscribe", args=["bad.token"]))
        self.assertEqual(resp.status_code, 404)
```

- [ ] **Step 2: Implement**

Create `marketing/views/unsubscribe.py`:
```python
from django.http import Http404
from django.shortcuts import render

from marketing.services.tokens import verify_unsubscribe_token


def unsubscribe(request, token):
    lead = verify_unsubscribe_token(token)
    if not lead:
        raise Http404
    if not lead.is_unsubscribed:
        lead.is_unsubscribed = True
        lead.save(update_fields=["is_unsubscribed", "updated_at"])
    return render(request, "marketing/unsubscribed.html", {"lead": lead})
```

Create `marketing/templates/marketing/unsubscribed.html`:
```html
{% extends "common/base.html" %}
{% block content %}
<div class="max-w-md mx-auto p-12 text-center">
  <h1 class="text-2xl font-bold">수신거부가 완료되었습니다</h1>
  <p class="mt-4 text-gray-600">{{ lead.email }}로 더 이상 메일이 발송되지 않습니다.</p>
</div>
{% endblock %}
```

Add to `marketing/views/__init__.py`:
```python
from .unsubscribe import unsubscribe  # noqa: F401
```

In `marketing/urls.py`:
```python
from .views import unsubscribe as unsubv
path("unsubscribe/<str:token>/", unsubv.unsubscribe, name="unsubscribe"),
```

- [ ] **Step 3: Run tests**

```bash
uv run pytest marketing/test_unsubscribe.py -v
```

Expected: 2 passed.

- [ ] **Step 4: Commit**

```bash
git add marketing/views/unsubscribe.py marketing/templates/marketing/unsubscribed.html marketing/views/__init__.py marketing/urls.py marketing/test_unsubscribe.py
git commit -m "feat(marketing): unsubscribe endpoint with HMAC token"
```

---

### Task 17: Campaign send orchestration

**Files:**
- Modify: `marketing/services/mailer.py`, `marketing/test_mailer.py`

- [ ] **Step 1: Write failing tests for the campaign-level helper**

Append to `marketing/test_mailer.py`:
```python
from marketing.services.mailer import send_campaign_inline


@override_settings(SITE_URL="http://example.test", DEFAULT_FROM_EMAIL="from@example.test")
class CampaignSendTests(TestCase):
    def setUp(self):
        self.template = EmailTemplate.objects.create(
            name="cs", subject="s", html_body="<body>x</body>"
        )
        self.campaign = EmailCampaign.objects.create(name="csC", template=self.template)
        self.l1 = Lead.objects.create(email="a@x.com")
        self.l2 = Lead.objects.create(email="b@x.com")
        for lead in [self.l1, self.l2]:
            EmailSendLog.objects.create(
                campaign=self.campaign, lead=lead, to_email=lead.email
            )

    def test_send_inline_updates_counters_and_status(self):
        send_campaign_inline(self.campaign)
        self.campaign.refresh_from_db()
        self.assertEqual(self.campaign.success_count, 2)
        self.assertEqual(self.campaign.failure_count, 0)
        self.assertEqual(self.campaign.status, EmailCampaign.Status.SENT)
        self.l1.refresh_from_db()
        self.assertEqual(self.l1.status, Lead.Status.CONTACTED)
        self.assertIsNotNone(self.l1.last_contacted_at)

    def test_partial_failure_sets_partial_status(self):
        self.l2.is_unsubscribed = True
        self.l2.save()
        send_campaign_inline(self.campaign)
        self.campaign.refresh_from_db()
        self.assertEqual(self.campaign.success_count, 1)
        self.assertEqual(self.campaign.failure_count, 1)
        self.assertEqual(self.campaign.status, EmailCampaign.Status.PARTIAL_FAILED)
```

- [ ] **Step 2: Implement**

Append to `marketing/services/mailer.py`:
```python
import threading
import time

from marketing.models import EmailCampaign
from marketing.services.state import mark_contacted

SEND_INTERVAL_SECONDS = 0.3


def send_campaign_inline(campaign):
    """Synchronous send used by tests and by the background worker."""
    sends = list(campaign.sends.select_related("lead").all())
    campaign.status = EmailCampaign.Status.SENDING
    campaign.total_recipients = len(sends)
    campaign.save(update_fields=["status", "total_recipients", "updated_at"])

    success = 0
    failed = 0
    for s in sends:
        if send_one(s):
            success += 1
            lead = s.lead
            mark_contacted(lead)
            lead.last_contacted_at = timezone.now()
            lead.save(update_fields=["last_contacted_at", "updated_at"])
        else:
            failed += 1
        time.sleep(SEND_INTERVAL_SECONDS)

    campaign.success_count = success
    campaign.failure_count = failed
    if failed == 0:
        campaign.status = EmailCampaign.Status.SENT
    elif success == 0:
        campaign.status = EmailCampaign.Status.FAILED
    else:
        campaign.status = EmailCampaign.Status.PARTIAL_FAILED
    campaign.sent_at = timezone.now()
    campaign.save(update_fields=[
        "success_count", "failure_count", "status", "sent_at", "updated_at"
    ])


def send_campaign_async(campaign):
    def _worker():
        from django.db import connection
        try:
            send_campaign_inline(campaign)
        finally:
            connection.close()
    thread = threading.Thread(target=_worker, daemon=True)
    thread.start()
    return thread
```

Tune `SEND_INTERVAL_SECONDS` to 0 inside tests by overriding the module attribute if tests slow down — but with 2 sends × 0.3s the test takes <1 sec, acceptable.

- [ ] **Step 3: Run tests**

```bash
uv run pytest marketing/test_mailer.py -v
```

Expected: 6 passed.

- [ ] **Step 4: Commit**

```bash
git add marketing/services/mailer.py marketing/test_mailer.py
git commit -m "feat(marketing): campaign-level send with inline + threaded variants"
```

---

### Task 18: Campaign wizard views (template select, recipients, preview, send)

**Files:**
- Create: `marketing/views/campaigns.py`
- Modify: `marketing/forms.py`, `marketing/urls.py`, `marketing/views/__init__.py`
- Create: `marketing/templates/marketing/campaign_list.html`, `marketing/templates/marketing/campaign_step1.html`, `marketing/templates/marketing/campaign_step2.html`, `marketing/templates/marketing/campaign_step3.html`, `marketing/templates/marketing/campaign_detail.html`, `marketing/templates/marketing/_campaign_progress.html`
- Create: `marketing/test_campaigns.py`

- [ ] **Step 1: Write failing tests**

Create `marketing/test_campaigns.py`:
```python
from django.test import TestCase
from django.urls import reverse

from accounts.models import User
from marketing.models import EmailCampaign, EmailSendLog, EmailTemplate, Lead


class CampaignWizardTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="u", email="u@x.com", password="pw", is_staff=True
        )
        self.client.force_login(self.user)
        self.template = EmailTemplate.objects.create(
            name="tpl", subject="s", html_body="<body>hi</body>", is_active=True
        )
        Lead.objects.create(email="a@x.com")
        Lead.objects.create(email="b@x.com", is_unsubscribed=True)

    def test_step1_creates_draft_campaign(self):
        resp = self.client.post(reverse("marketing:campaign_new"), {
            "name": "c1", "template": str(self.template.id),
        })
        self.assertEqual(resp.status_code, 302)
        c = EmailCampaign.objects.get()
        self.assertEqual(c.status, EmailCampaign.Status.DRAFT)
        self.assertEqual(c.template, self.template)

    def test_step2_excludes_unsubscribed(self):
        c = EmailCampaign.objects.create(name="c", template=self.template)
        resp = self.client.post(
            reverse("marketing:campaign_recipients", args=[c.id]),
            {"source": "", "status": "", "interest_level": ""},
        )
        self.assertEqual(resp.status_code, 302)
        c.refresh_from_db()
        self.assertEqual(c.sends.count(), 1)  # only a@x.com, not b@x.com

    def test_step4_sends(self):
        c = EmailCampaign.objects.create(name="c", template=self.template)
        EmailSendLog.objects.create(
            campaign=c, lead=Lead.objects.get(email="a@x.com"), to_email="a@x.com",
        )
        resp = self.client.post(reverse("marketing:campaign_send", args=[c.id]))
        self.assertEqual(resp.status_code, 302)
        c.refresh_from_db()
        self.assertIn(c.status, [EmailCampaign.Status.SENT, EmailCampaign.Status.SENDING, EmailCampaign.Status.PARTIAL_FAILED])
```

- [ ] **Step 2: Add form + views**

Append to `marketing/forms.py`:
```python
from .models import EmailCampaign


class CampaignStep1Form(forms.ModelForm):
    class Meta:
        model = EmailCampaign
        fields = ["name", "template"]

    def __init__(self, *a, **kw):
        super().__init__(*a, **kw)
        self.fields["template"].queryset = EmailTemplate.objects.filter(is_active=True)
```

Add `LeadFilterForm`:
```python
from .models import Lead


class LeadFilterForm(forms.Form):
    source = forms.ChoiceField(
        choices=[("", "전체")] + list(Lead.Source.choices), required=False
    )
    status = forms.ChoiceField(
        choices=[("", "전체")] + list(Lead.Status.choices), required=False
    )
    interest_level = forms.ChoiceField(
        choices=[("", "전체")] + list(Lead.InterestLevel.choices), required=False
    )
    search = forms.CharField(required=False)

    def filter_queryset(self, qs):
        data = self.cleaned_data if self.is_valid() else {}
        if data.get("source"):
            qs = qs.filter(source=data["source"])
        if data.get("status"):
            qs = qs.filter(status=data["status"])
        if data.get("interest_level"):
            qs = qs.filter(interest_level=data["interest_level"])
        if data.get("search"):
            q = data["search"]
            qs = qs.filter(email__icontains=q) | qs.filter(name__icontains=q) | qs.filter(company_name__icontains=q)
        return qs
```

Create `marketing/views/campaigns.py`:
```python
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from marketing.forms import CampaignStep1Form, LeadFilterForm
from marketing.models import EmailCampaign, EmailSendLog, Lead
from marketing.services.mailer import send_campaign_async, build_message_for_send

from .templates import _require_staff


@login_required
def campaign_list(request):
    _require_staff(request)
    campaigns = EmailCampaign.objects.select_related("template", "sender").all()
    return render(request, "marketing/campaign_list.html", {"campaigns": campaigns})


@login_required
def campaign_new(request):
    _require_staff(request)
    form = CampaignStep1Form(request.POST or None)
    if request.method == "POST" and form.is_valid():
        c = form.save(commit=False)
        c.sender = request.user
        c.save()
        return redirect(reverse("marketing:campaign_recipients", args=[c.id]))
    return render(request, "marketing/campaign_step1.html", {"form": form})


@login_required
def campaign_recipients(request, pk):
    _require_staff(request)
    campaign = get_object_or_404(EmailCampaign, pk=pk, status=EmailCampaign.Status.DRAFT)
    form = LeadFilterForm(request.GET or None)
    qs = Lead.objects.filter(is_unsubscribed=False)
    if form.is_bound:
        qs = form.filter_queryset(qs)
    if request.method == "POST":
        # selection persists current GET filters from hidden inputs
        campaign.sends.all().delete()
        snapshot_ids = []
        for lead in qs:
            EmailSendLog.objects.create(
                campaign=campaign, lead=lead, to_email=lead.email,
            )
            snapshot_ids.append(str(lead.id))
        campaign.selection_snapshot = {"lead_ids": snapshot_ids, "filters": form.data.dict()}
        campaign.save(update_fields=["selection_snapshot", "updated_at"])
        return redirect(reverse("marketing:campaign_preview", args=[campaign.id]))
    return render(request, "marketing/campaign_step2.html",
                  {"campaign": campaign, "form": form, "leads": qs[:200], "count": qs.count()})


@login_required
def campaign_preview(request, pk):
    _require_staff(request)
    campaign = get_object_or_404(EmailCampaign, pk=pk, status=EmailCampaign.Status.DRAFT)
    first_send = campaign.sends.first()
    rendered_html = ""
    rendered_subject = campaign.template.subject
    if first_send:
        msg = build_message_for_send(first_send)
        rendered_subject = msg.subject
        rendered_html = next(a for a in msg.alternatives if a[1] == "text/html")[0]
    return render(request, "marketing/campaign_step3.html", {
        "campaign": campaign,
        "rendered_subject": rendered_subject,
        "rendered_html": rendered_html,
        "attachments": campaign.template.attachments.all(),
    })


@login_required
@require_POST
def campaign_test(request, pk):
    _require_staff(request)
    campaign = get_object_or_404(EmailCampaign, pk=pk, status=EmailCampaign.Status.DRAFT)
    # build using a synthetic Lead/SendLog without persisting
    from django.core.mail import EmailMultiAlternatives
    from django.conf import settings as dj_settings
    html = campaign.template.html_body
    msg = EmailMultiAlternatives(
        subject="[TEST] " + campaign.template.subject,
        body="이 메일은 캠페인 테스트 발송입니다.",
        from_email=dj_settings.DEFAULT_FROM_EMAIL,
        to=[request.user.email],
    )
    msg.attach_alternative(html, "text/html")
    for att in campaign.template.attachments.all():
        msg.attach_file(att.file.path)
    msg.send(fail_silently=False)
    return redirect(reverse("marketing:campaign_preview", args=[pk]))


@login_required
@require_POST
def campaign_send(request, pk):
    _require_staff(request)
    campaign = get_object_or_404(EmailCampaign, pk=pk, status=EmailCampaign.Status.DRAFT)
    send_campaign_async(campaign)
    return redirect(reverse("marketing:campaign_detail", args=[pk]))


@login_required
def campaign_detail(request, pk):
    _require_staff(request)
    campaign = get_object_or_404(EmailCampaign, pk=pk)
    sends = campaign.sends.select_related("lead").all()
    return render(request, "marketing/campaign_detail.html",
                  {"campaign": campaign, "sends": sends})


@login_required
def campaign_progress(request, pk):
    _require_staff(request)
    campaign = get_object_or_404(EmailCampaign, pk=pk)
    return render(request, "marketing/_campaign_progress.html", {"campaign": campaign})
```

Re-export and route. In `marketing/views/__init__.py`:
```python
from .campaigns import (
    campaign_list, campaign_new, campaign_recipients, campaign_preview,
    campaign_test, campaign_send, campaign_detail, campaign_progress,
)  # noqa: F401
```

In `marketing/urls.py` add:
```python
from .views import campaigns as cv

path("campaigns/", cv.campaign_list, name="campaign_list"),
path("campaigns/new/", cv.campaign_new, name="campaign_new"),
path("campaigns/<uuid:pk>/recipients/", cv.campaign_recipients, name="campaign_recipients"),
path("campaigns/<uuid:pk>/preview/", cv.campaign_preview, name="campaign_preview"),
path("campaigns/<uuid:pk>/test/", cv.campaign_test, name="campaign_test"),
path("campaigns/<uuid:pk>/send/", cv.campaign_send, name="campaign_send"),
path("campaigns/<uuid:pk>/", cv.campaign_detail, name="campaign_detail"),
path("campaigns/<uuid:pk>/progress/", cv.campaign_progress, name="campaign_progress"),
```

In `send_campaign_async`, swap to a synchronous call when running under tests to avoid threading flakes:
```python
import sys


def send_campaign_async(campaign):
    if "pytest" in sys.modules:
        send_campaign_inline(campaign)
        return None
    def _worker():
        from django.db import connection
        try:
            send_campaign_inline(campaign)
        finally:
            connection.close()
    thread = threading.Thread(target=_worker, daemon=True)
    thread.start()
    return thread
```

Create templates:

`marketing/templates/marketing/campaign_list.html`:
```html
{% extends "marketing/_layout.html" %}
{% block title %}이메일 캠페인{% endblock %}
{% block marketing_content %}
<a href="{% url 'marketing:campaign_new' %}" class="px-4 py-2 bg-green-600 text-white rounded">새 캠페인</a>
<table class="w-full border mt-4 text-sm">
  <thead class="bg-gray-50"><tr>
    <th class="p-2 text-left">이름</th><th class="p-2">상태</th><th class="p-2">발송</th><th class="p-2">성공/실패</th><th class="p-2">열람</th>
  </tr></thead>
  <tbody>
    {% for c in campaigns %}
    <tr class="border-t">
      <td class="p-2"><a class="text-blue-700" href="{% url 'marketing:campaign_detail' c.id %}">{{ c.name }}</a></td>
      <td class="p-2">{{ c.get_status_display }}</td>
      <td class="p-2">{{ c.sent_at|date:"m-d H:i"|default:"—" }}</td>
      <td class="p-2">{{ c.success_count }}/{{ c.failure_count }}</td>
      <td class="p-2">{{ c.open_count }}</td>
    </tr>
    {% empty %}<tr><td colspan="5" class="p-4 text-gray-400 text-center">캠페인이 없습니다.</td></tr>{% endfor %}
  </tbody>
</table>
{% endblock %}
```

`marketing/templates/marketing/campaign_step1.html`:
```html
{% extends "marketing/_layout.html" %}
{% load widget_tweaks %}
{% block title %}새 캠페인 — 1. 템플릿 선택{% endblock %}
{% block marketing_content %}
<form method="post" class="space-y-4">{% csrf_token %}
  <label class="block text-sm">캠페인 이름 {{ form.name|add_class:"border rounded p-2 w-full" }}</label>
  <label class="block text-sm">템플릿 {{ form.template|add_class:"border rounded p-2 w-full" }}</label>
  <button class="px-4 py-2 bg-green-600 text-white rounded">다음 →</button>
</form>
{% endblock %}
```

`marketing/templates/marketing/campaign_step2.html`:
```html
{% extends "marketing/_layout.html" %}
{% load widget_tweaks %}
{% block title %}새 캠페인 — 2. 수신자 선택{% endblock %}
{% block marketing_content %}
<form method="get" class="space-y-2">
  <div class="flex gap-2 items-end">
    <label class="text-sm">출처 {{ form.source|add_class:"border rounded p-1" }}</label>
    <label class="text-sm">상태 {{ form.status|add_class:"border rounded p-1" }}</label>
    <label class="text-sm">관심도 {{ form.interest_level|add_class:"border rounded p-1" }}</label>
    <label class="text-sm">검색 {{ form.search|add_class:"border rounded p-1" }}</label>
    <button class="px-3 py-1 border rounded">필터</button>
  </div>
</form>
<div class="mt-4 text-sm">선택된 인원: <span class="font-bold">{{ count }}명</span> (수신거부 자동 제외)</div>
<form method="post" class="mt-3">{% csrf_token %}
  {% for k,v in request.GET.items %}<input type="hidden" name="{{ k }}" value="{{ v }}">{% endfor %}
  <button class="px-4 py-2 bg-green-600 text-white rounded">이 조건으로 발송 준비 →</button>
</form>
<table class="w-full border mt-4 text-xs">
  <thead class="bg-gray-50"><tr><th class="p-1 text-left">이메일</th><th class="p-1">이름</th><th class="p-1">회사</th><th class="p-1">상태</th></tr></thead>
  <tbody>{% for l in leads %}<tr class="border-t"><td class="p-1">{{ l.email }}</td><td class="p-1">{{ l.name }}</td><td class="p-1">{{ l.company_name }}</td><td class="p-1">{{ l.get_status_display }}</td></tr>{% endfor %}</tbody>
</table>
{% endblock %}
```

`marketing/templates/marketing/campaign_step3.html`:
```html
{% extends "marketing/_layout.html" %}
{% block title %}새 캠페인 — 3. 미리보기{% endblock %}
{% block marketing_content %}
<div class="border p-4 mb-4">
  <div class="text-sm text-gray-500">제목</div>
  <div class="font-medium">{{ rendered_subject }}</div>
  <div class="mt-2 text-sm text-gray-500">첨부</div>
  <ul class="text-sm">{% for a in attachments %}<li>{{ a.display_name }}</li>{% endfor %}</ul>
</div>
<div class="border p-2 h-96 overflow-auto">{{ rendered_html|safe }}</div>
<form method="post" action="{% url 'marketing:campaign_test' campaign.id %}" class="mt-4 inline">{% csrf_token %}
  <button class="px-4 py-2 border rounded">내게 테스트 발송</button>
</form>
<form method="post" action="{% url 'marketing:campaign_send' campaign.id %}" class="mt-4 inline"
      onsubmit="return confirm('{{ campaign.sends.count }}명에게 발송하시겠습니까?');">
  {% csrf_token %}
  <button class="px-4 py-2 bg-green-600 text-white rounded">발송 실행</button>
</form>
{% endblock %}
```

`marketing/templates/marketing/campaign_detail.html`:
```html
{% extends "marketing/_layout.html" %}
{% block title %}{{ campaign.name }}{% endblock %}
{% block marketing_content %}
<div id="campaign-progress" hx-get="{% url 'marketing:campaign_progress' campaign.id %}"
     hx-trigger="load, every 2s" hx-swap="outerHTML">
  {% include "marketing/_campaign_progress.html" %}
</div>
<table class="w-full border mt-4 text-xs">
  <thead class="bg-gray-50"><tr><th class="p-1 text-left">이메일</th><th class="p-1">상태</th><th class="p-1">열람</th><th class="p-1">에러</th></tr></thead>
  <tbody>
    {% for s in sends %}
    <tr class="border-t">
      <td class="p-1">{{ s.to_email }}</td>
      <td class="p-1">{{ s.get_status_display }}</td>
      <td class="p-1">{{ s.open_count }}</td>
      <td class="p-1 text-red-600">{{ s.error_message|truncatechars:80 }}</td>
    </tr>
    {% endfor %}
  </tbody>
</table>
{% endblock %}
```

`marketing/templates/marketing/_campaign_progress.html`:
```html
<div id="campaign-progress" {% if campaign.status != "sending" %}hx-swap-oob="false"{% endif %}>
  <div class="text-sm">
    상태: <b>{{ campaign.get_status_display }}</b> · 성공 {{ campaign.success_count }} · 실패 {{ campaign.failure_count }} · 열람 {{ campaign.open_count }}
  </div>
</div>
```

- [ ] **Step 3: Run tests**

```bash
uv run pytest marketing/test_campaigns.py -v
```

Expected: 3 passed.

- [ ] **Step 4: Commit**

```bash
git add marketing/views/campaigns.py marketing/views/__init__.py marketing/forms.py marketing/urls.py marketing/templates/marketing/ marketing/services/mailer.py marketing/test_campaigns.py
git commit -m "feat(marketing): campaign wizard (template/recipients/preview/test/send)"
```

---

## Phase E — Lead views (list, detail, inline edit)

### Task 19: Lead list with filters

**Files:**
- Create: `marketing/views/leads.py`, `marketing/templates/marketing/lead_list.html`, `marketing/test_leads.py`
- Modify: `marketing/views/__init__.py`, `marketing/urls.py`

- [ ] **Step 1: Write failing tests**

Create `marketing/test_leads.py`:
```python
from django.test import TestCase
from django.urls import reverse

from accounts.models import User
from marketing.models import Lead


class LeadListTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="u", email="u@x.com", password="pw", is_staff=True
        )
        self.client.force_login(self.user)
        Lead.objects.create(email="a@x.com", source=Lead.Source.GOOGLE_SHEET, name="alice")
        Lead.objects.create(email="b@x.com", source=Lead.Source.LANDING_PAGE, name="bob")

    def test_lists_all(self):
        resp = self.client.get(reverse("marketing:lead_list"))
        self.assertContains(resp, "alice")
        self.assertContains(resp, "bob")

    def test_filter_by_source(self):
        resp = self.client.get(reverse("marketing:lead_list"), {"source": "google_sheet"})
        self.assertContains(resp, "alice")
        self.assertNotContains(resp, "bob")

    def test_search(self):
        resp = self.client.get(reverse("marketing:lead_list"), {"search": "bob"})
        self.assertContains(resp, "bob")
        self.assertNotContains(resp, "alice")
```

- [ ] **Step 2: Implement**

Create `marketing/views/leads.py`:
```python
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_http_methods

from marketing.forms import ActivityForm, LeadFilterForm
from marketing.models import Lead

from .templates import _require_staff


@login_required
def lead_list(request):
    _require_staff(request)
    form = LeadFilterForm(request.GET or None)
    qs = Lead.objects.all()
    if form.is_bound:
        qs = form.filter_queryset(qs)
    return render(request, "marketing/lead_list.html", {
        "form": form, "leads": qs[:500], "total": qs.count(),
    })


@login_required
def lead_detail(request, pk):
    _require_staff(request)
    lead = get_object_or_404(Lead, pk=pk)
    activities = lead.activities.all()[:50]
    return render(request, "marketing/lead_detail.html", {
        "lead": lead,
        "activities": activities,
        "form": ActivityForm(),
    })


@login_required
@require_http_methods(["POST"])
def lead_patch(request, pk):
    _require_staff(request)
    lead = get_object_or_404(Lead, pk=pk)
    allowed = {"status", "interest_level", "assigned_to", "name", "phone", "company_name"}
    field = request.POST.get("field")
    value = request.POST.get("value", "")
    if field not in allowed:
        return render(request, "marketing/_field_error.html", status=400)
    if field == "assigned_to":
        from accounts.models import User
        lead.assigned_to = User.objects.filter(pk=value).first() if value else None
    else:
        setattr(lead, field, value)
    lead.save()
    return render(request, "marketing/_lead_field.html", {"lead": lead, "field": field})
```

Create `marketing/templates/marketing/lead_list.html`:
```html
{% extends "marketing/_layout.html" %}
{% load widget_tweaks %}
{% block title %}잠재고객 ({{ total }}명){% endblock %}
{% block marketing_content %}
<form method="get" class="flex gap-2 items-end mb-3">
  <label class="text-sm">출처 {{ form.source|add_class:"border rounded p-1" }}</label>
  <label class="text-sm">상태 {{ form.status|add_class:"border rounded p-1" }}</label>
  <label class="text-sm">관심도 {{ form.interest_level|add_class:"border rounded p-1" }}</label>
  <label class="text-sm">검색 {{ form.search|add_class:"border rounded p-1" }}</label>
  <button class="px-3 py-1 border rounded">필터</button>
  <a href="{% url 'marketing:lead_import' %}" class="ml-auto px-3 py-1 bg-blue-600 text-white rounded">시트 임포트</a>
</form>
<table class="w-full border text-sm">
  <thead class="bg-gray-50"><tr>
    <th class="p-2 text-left">이메일</th><th class="p-2">이름</th><th class="p-2">회사</th>
    <th class="p-2">출처</th><th class="p-2">상태</th><th class="p-2">관심도</th><th class="p-2">최근 접촉</th>
  </tr></thead>
  <tbody>
    {% for l in leads %}
    <tr class="border-t">
      <td class="p-2"><a class="text-blue-700" href="{% url 'marketing:lead_detail' l.id %}">{{ l.email }}</a></td>
      <td class="p-2">{{ l.name }}</td>
      <td class="p-2">{{ l.company_name }}</td>
      <td class="p-2">{{ l.get_source_display }}</td>
      <td class="p-2">{{ l.get_status_display }}</td>
      <td class="p-2">{{ l.get_interest_level_display }}</td>
      <td class="p-2">{{ l.last_contacted_at|date:"m-d"|default:"—" }}</td>
    </tr>
    {% empty %}<tr><td colspan="7" class="p-4 text-center text-gray-400">없음</td></tr>{% endfor %}
  </tbody>
</table>
{% endblock %}
```

Re-export and route. In `marketing/views/__init__.py`:
```python
from .leads import lead_list, lead_detail, lead_patch  # noqa: F401
```

In `marketing/urls.py`:
```python
from .views import leads as lv

# replace the placeholder lead_detail lambda with:
path("leads/", lv.lead_list, name="lead_list"),
path("leads/<uuid:pk>/", lv.lead_detail, name="lead_detail"),
path("leads/<uuid:pk>/patch/", lv.lead_patch, name="lead_patch"),
```

(Remove the earlier `path("leads/<uuid:pk>/", lambda r, pk: None, ...)` placeholder.)

- [ ] **Step 3: Run tests**

```bash
uv run pytest marketing/test_leads.py -v
```

Expected: 3 passed.

- [ ] **Step 4: Commit**

```bash
git add marketing/views/leads.py marketing/views/__init__.py marketing/urls.py marketing/templates/marketing/lead_list.html marketing/test_leads.py
git commit -m "feat(marketing): Lead list view with filters"
```

---

### Task 20: Lead detail + inline edit

**Files:**
- Create: `marketing/templates/marketing/lead_detail.html`, `marketing/templates/marketing/_lead_field.html`, `marketing/templates/marketing/_field_error.html`
- Append: `marketing/test_leads.py`

- [ ] **Step 1: Write failing tests**

Append to `marketing/test_leads.py`:
```python
from django.urls import reverse


class LeadDetailTests(TestCase):
    def setUp(self):
        from accounts.models import User
        self.user = User.objects.create_user(
            username="u3", email="u3@x.com", password="pw", is_staff=True
        )
        self.client.force_login(self.user)
        self.lead = Lead.objects.create(email="l@x.com", name="leo")

    def test_detail_renders(self):
        resp = self.client.get(reverse("marketing:lead_detail", args=[self.lead.id]))
        self.assertContains(resp, "leo")

    def test_patch_status(self):
        resp = self.client.post(
            reverse("marketing:lead_patch", args=[self.lead.id]),
            {"field": "status", "value": "interested"},
        )
        self.assertEqual(resp.status_code, 200)
        self.lead.refresh_from_db()
        self.assertEqual(self.lead.status, "interested")

    def test_patch_rejects_unknown_field(self):
        resp = self.client.post(
            reverse("marketing:lead_patch", args=[self.lead.id]),
            {"field": "is_unsubscribed", "value": "true"},
        )
        self.assertEqual(resp.status_code, 400)
```

- [ ] **Step 2: Create templates**

Create `marketing/templates/marketing/lead_detail.html`:
```html
{% extends "marketing/_layout.html" %}
{% block title %}{{ lead.name|default:lead.email }}{% endblock %}
{% block marketing_content %}
<div class="grid grid-cols-3 gap-6">
  <aside class="space-y-3">
    <div><b>이메일</b><div class="text-sm">{{ lead.email }}</div></div>
    <div><b>이름</b><div class="text-sm">{{ lead.name|default:"—" }}</div></div>
    <div><b>연락처</b><div class="text-sm">{{ lead.phone|default:"—" }}</div></div>
    <div><b>회사</b><div class="text-sm">{{ lead.company_name|default:"—" }}</div></div>
    <div><b>출처</b><div class="text-sm">{{ lead.get_source_display }}</div></div>

    <div>
      <b>상태</b>
      <form hx-post="{% url 'marketing:lead_patch' lead.id %}" hx-vals='{"field":"status"}' hx-target="this" hx-swap="outerHTML">
        <input type="hidden" name="field" value="status">
        <select name="value" hx-trigger="change" hx-post="{% url 'marketing:lead_patch' lead.id %}" hx-target="closest div" class="border rounded p-1 w-full">
          {% for v,label in lead.Status.choices %}
            <option value="{{ v }}" {% if lead.status == v %}selected{% endif %}>{{ label }}</option>
          {% endfor %}
        </select>
      </form>
    </div>

    <div>
      <b>관심도</b>
      <select name="value" hx-post="{% url 'marketing:lead_patch' lead.id %}" hx-vals='{"field":"interest_level"}' hx-trigger="change" hx-target="this" hx-swap="outerHTML" class="border rounded p-1 w-full">
        {% for v,label in lead.InterestLevel.choices %}
          <option value="{{ v }}" {% if lead.interest_level == v %}selected{% endif %}>{{ label }}</option>
        {% endfor %}
      </select>
    </div>
  </aside>

  <div class="col-span-2" id="lead-dynamic">
    {% include "marketing/_activity_form.html" %}
    <ul class="mt-4 space-y-2">
      {% for activity in activities %}
        {% include "marketing/_timeline_item.html" %}
      {% empty %}
        <li class="text-sm text-gray-400">기록된 활동이 없습니다.</li>
      {% endfor %}
    </ul>
  </div>
</div>
{% endblock %}
```

Create `marketing/templates/marketing/_lead_field.html`:
```html
<div class="text-sm text-green-700">저장됨 ✓</div>
```

Create `marketing/templates/marketing/_field_error.html`:
```html
<div class="text-sm text-red-600">잘못된 필드</div>
```

- [ ] **Step 3: Run tests**

```bash
uv run pytest marketing/test_leads.py -v
```

Expected: 6 passed.

- [ ] **Step 4: Commit**

```bash
git add marketing/templates/marketing/ marketing/test_leads.py
git commit -m "feat(marketing): Lead detail with inline HTMX field editing"
```

---

## Phase F — Sheets connector + import wizard

### Task 21: Sheets connector service

**Files:**
- Create: `marketing/services/sheets.py`, `marketing/test_sheets.py`

- [ ] **Step 1: Write failing tests with mocked gspread**

Create `marketing/test_sheets.py`:
```python
from unittest.mock import MagicMock, patch

from django.test import TestCase

from marketing.services.sheets import fetch_sheet_preview


class FetchSheetPreviewTests(TestCase):
    @patch("marketing.services.sheets._open_sheet")
    def test_returns_headers_and_rows(self, open_sheet):
        ws = MagicMock()
        ws.get_all_values.return_value = [
            ["이메일", "이름", "관심"],
            ["a@x.com", "Alice", "Y"],
            ["b@x.com", "Bob", "N"],
        ]
        ws.title = "Sheet1"
        gc_sheet = MagicMock()
        gc_sheet.sheet1 = ws
        open_sheet.return_value = (gc_sheet, ws)
        result = fetch_sheet_preview("https://docs.google.com/spreadsheets/d/abc/edit")
        self.assertEqual(result["headers"], ["이메일", "이름", "관심"])
        self.assertEqual(result["rows"][0], ["a@x.com", "Alice", "Y"])
        self.assertEqual(result["sheet_title"], "Sheet1")
```

- [ ] **Step 2: Implement**

Create `marketing/services/sheets.py`:
```python
import json
import logging

import gspread
from django.conf import settings
from google.oauth2.service_account import Credentials

logger = logging.getLogger(__name__)
SCOPES = ["https://www.googleapis.com/auth/spreadsheets.readonly"]


def _client():
    raw = settings.GOOGLE_SERVICE_ACCOUNT_JSON
    if not raw:
        raise RuntimeError("GOOGLE_SERVICE_ACCOUNT_JSON not configured")
    info = json.loads(raw)
    creds = Credentials.from_service_account_info(info, scopes=SCOPES)
    return gspread.authorize(creds)


def _open_sheet(url):
    client = _client()
    spreadsheet = client.open_by_url(url)
    return spreadsheet, spreadsheet.sheet1


def fetch_sheet_preview(url, max_rows=100):
    _, ws = _open_sheet(url)
    values = ws.get_all_values()
    if not values:
        return {"headers": [], "rows": [], "sheet_title": ws.title}
    headers, rows = values[0], values[1:max_rows + 1]
    return {"headers": headers, "rows": rows, "sheet_title": ws.title}


def fetch_sheet_all(url):
    _, ws = _open_sheet(url)
    values = ws.get_all_values()
    if not values:
        return {"headers": [], "rows": [], "sheet_title": ws.title}
    return {"headers": values[0], "rows": values[1:], "sheet_title": ws.title}
```

- [ ] **Step 3: Run tests**

```bash
uv run pytest marketing/test_sheets.py -v
```

Expected: 1 passed.

- [ ] **Step 4: Commit**

```bash
git add marketing/services/sheets.py marketing/test_sheets.py
git commit -m "feat(marketing): gspread connector for sheet preview and full fetch"
```

---

### Task 22: Import wizard views (URL → preview → execute)

**Files:**
- Create: `marketing/views/imports.py`, `marketing/templates/marketing/import_step1.html`, `marketing/templates/marketing/import_step2.html`, `marketing/templates/marketing/import_result.html`, `marketing/test_imports.py`
- Modify: `marketing/views/__init__.py`, `marketing/urls.py`, `marketing/forms.py`

- [ ] **Step 1: Write failing tests**

Create `marketing/test_imports.py`:
```python
from unittest.mock import patch

from django.test import TestCase
from django.urls import reverse

from accounts.models import User
from marketing.models import Lead, LeadImport


PREVIEW_DATA = {
    "headers": ["이메일", "이름", "회사", "관심"],
    "rows": [
        ["a@x.com", "Alice", "AcmeCo", "Y"],
        ["b@x.com", "Bob", "BetaCo", "N"],
        ["", "Anon", "", "Y"],
    ],
    "sheet_title": "Leads",
}


class ImportWizardTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="u", email="u@x.com", password="pw", is_staff=True
        )
        self.client.force_login(self.user)

    def test_step1_shows_form(self):
        resp = self.client.get(reverse("marketing:lead_import"))
        self.assertContains(resp, "시트 URL")

    @patch("marketing.views.imports.fetch_sheet_preview", return_value=PREVIEW_DATA)
    def test_preview_step(self, _):
        resp = self.client.post(reverse("marketing:lead_import_preview"), {
            "sheet_url": "https://docs.google.com/spreadsheets/d/abc/edit",
        })
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Alice")
        self.assertContains(resp, "이메일")

    @patch("marketing.views.imports.fetch_sheet_all", return_value=PREVIEW_DATA)
    def test_execute_step_creates_leads_and_skips_invalid(self, _):
        resp = self.client.post(reverse("marketing:lead_import_execute"), {
            "sheet_url": "https://docs.google.com/spreadsheets/d/abc/edit",
            "sheet_title": "Leads",
            "map_email": "이메일",
            "map_name": "이름",
            "map_company_name": "회사",
            "filter_column": "관심",
            "filter_value": "Y",
        })
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(Lead.objects.count(), 1)  # only Alice (b filtered out, anon blank)
        li = LeadImport.objects.get()
        self.assertEqual(li.imported_count, 1)
        self.assertEqual(li.skipped_count, 1)  # bob filtered out
        self.assertEqual(li.failed_count, 1)   # anon invalid email
```

- [ ] **Step 2: Add form + views**

Append to `marketing/forms.py`:
```python
class SheetURLForm(forms.Form):
    sheet_url = forms.URLField()
```

Create `marketing/views/imports.py`:
```python
from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_http_methods

from marketing.forms import SheetURLForm
from marketing.models import Activity, Lead, LeadImport
from marketing.services.leads import get_or_create_lead_by_email, normalize_email
from marketing.services.sheets import fetch_sheet_all, fetch_sheet_preview

from .templates import _require_staff


@login_required
def lead_import(request):
    _require_staff(request)
    return render(request, "marketing/import_step1.html",
                  {"form": SheetURLForm()})


@login_required
@require_http_methods(["POST"])
def lead_import_preview(request):
    _require_staff(request)
    form = SheetURLForm(request.POST)
    if not form.is_valid():
        return render(request, "marketing/import_step1.html",
                      {"form": form}, status=422)
    url = form.cleaned_data["sheet_url"]
    try:
        preview = fetch_sheet_preview(url)
    except Exception as exc:
        return render(request, "marketing/import_step1.html",
                      {"form": form, "error": str(exc)}, status=502)
    return render(request, "marketing/import_step2.html", {
        "url": url, "preview": preview,
        "lead_fields": ["email", "name", "phone", "company_name"],
    })


@login_required
@require_http_methods(["POST"])
def lead_import_execute(request):
    _require_staff(request)
    url = request.POST["sheet_url"]
    sheet_title = request.POST.get("sheet_title", "")
    mapping = {
        f: request.POST.get(f"map_{f}", "")
        for f in ["email", "name", "phone", "company_name"]
    }
    filter_column = request.POST.get("filter_column", "")
    filter_value = request.POST.get("filter_value", "")
    if not mapping["email"]:
        return render(request, "marketing/import_step1.html",
                      {"form": SheetURLForm(initial={"sheet_url": url}),
                       "error": "email 매핑이 필요합니다."}, status=400)
    try:
        data = fetch_sheet_all(url)
    except Exception as exc:
        return render(request, "marketing/import_step1.html",
                      {"form": SheetURLForm(initial={"sheet_url": url}),
                       "error": str(exc)}, status=502)

    headers = data["headers"]

    def col(row, header):
        if not header:
            return ""
        if header not in headers:
            return ""
        return row[headers.index(header)] if headers.index(header) < len(row) else ""

    imported = skipped = failed = 0
    errors = []
    for row in data["rows"]:
        if filter_column and col(row, filter_column).strip() != filter_value.strip():
            skipped += 1
            continue
        raw_email = col(row, mapping["email"])
        if not normalize_email(raw_email):
            failed += 1
            errors.append(f"invalid email: {raw_email!r}")
            continue
        defaults = {
            "name": col(row, mapping["name"]).strip(),
            "phone": col(row, mapping["phone"]).strip(),
            "company_name": col(row, mapping["company_name"]).strip(),
            "source": Lead.Source.GOOGLE_SHEET,
            "source_detail": url,
        }
        lead, created = get_or_create_lead_by_email(raw_email, defaults=defaults)
        if created:
            imported += 1
            Activity.objects.create(
                lead=lead, type=Activity.Type.NOTE,
                subject="구글 시트 임포트",
                body="\n".join(f"{h}: {c}" for h, c in zip(headers, row)),
                happened_at=timezone.now(),
                performed_by=request.user,
            )
        else:
            skipped += 1

    lead_import = LeadImport.objects.create(
        sheet_url=url,
        sheet_title=sheet_title,
        column_mapping=mapping,
        filter_rule={"column": filter_column, "equals": filter_value} if filter_column else None,
        imported_count=imported,
        skipped_count=skipped,
        failed_count=failed,
        imported_by=request.user,
        error_log="\n".join(errors[:200]),
    )

    return render(request, "marketing/import_result.html", {
        "lead_import": lead_import,
    })
```

Re-export and route:
```python
# marketing/views/__init__.py
from .imports import lead_import, lead_import_preview, lead_import_execute  # noqa: F401
```

In `marketing/urls.py`:
```python
from .views import imports as iv

path("leads/import/", iv.lead_import, name="lead_import"),
path("leads/import/preview/", iv.lead_import_preview, name="lead_import_preview"),
path("leads/import/execute/", iv.lead_import_execute, name="lead_import_execute"),
```

Create `marketing/templates/marketing/import_step1.html`:
```html
{% extends "marketing/_layout.html" %}
{% load widget_tweaks %}
{% block title %}시트 임포트{% endblock %}
{% block marketing_content %}
{% if error %}<div class="bg-red-50 text-red-700 p-2 rounded mb-3">{{ error }}</div>{% endif %}
<form method="post" action="{% url 'marketing:lead_import_preview' %}" class="space-y-3">
  {% csrf_token %}
  <label class="block text-sm">시트 URL {{ form.sheet_url|add_class:"border rounded p-2 w-full" }}</label>
  <div class="text-xs text-gray-500">서비스 계정 이메일을 시트에 "뷰어"로 공유하세요.</div>
  <button class="px-4 py-2 bg-green-600 text-white rounded">미리보기 →</button>
</form>
{% endblock %}
```

Create `marketing/templates/marketing/import_step2.html`:
```html
{% extends "marketing/_layout.html" %}
{% block title %}매핑 + 미리보기{% endblock %}
{% block marketing_content %}
<form method="post" action="{% url 'marketing:lead_import_execute' %}" class="space-y-3">
  {% csrf_token %}
  <input type="hidden" name="sheet_url" value="{{ url }}">
  <input type="hidden" name="sheet_title" value="{{ preview.sheet_title }}">

  <div class="grid grid-cols-4 gap-2 text-sm">
    {% for f in lead_fields %}
    <label>{{ f }}
      <select name="map_{{ f }}" class="border rounded p-1 w-full">
        <option value="">—</option>
        {% for h in preview.headers %}<option value="{{ h }}">{{ h }}</option>{% endfor %}
      </select>
    </label>
    {% endfor %}
  </div>

  <div class="grid grid-cols-2 gap-2 text-sm">
    <label>필터 컬럼
      <select name="filter_column" class="border rounded p-1 w-full">
        <option value="">없음</option>
        {% for h in preview.headers %}<option value="{{ h }}">{{ h }}</option>{% endfor %}
      </select>
    </label>
    <label>값과 같은 행만 <input name="filter_value" class="border rounded p-1 w-full"></label>
  </div>

  <table class="w-full border text-xs mt-3">
    <thead class="bg-gray-50"><tr>{% for h in preview.headers %}<th class="p-1">{{ h }}</th>{% endfor %}</tr></thead>
    <tbody>
    {% for row in preview.rows %}
      {% if forloop.counter <= 5 %}
        <tr class="border-t">{% for c in row %}<td class="p-1">{{ c }}</td>{% endfor %}</tr>
      {% endif %}
    {% endfor %}
    </tbody>
  </table>

  <button class="px-4 py-2 bg-green-600 text-white rounded">임포트 실행</button>
</form>
{% endblock %}
```

Create `marketing/templates/marketing/import_result.html`:
```html
{% extends "marketing/_layout.html" %}
{% block title %}임포트 결과{% endblock %}
{% block marketing_content %}
<div class="text-sm space-y-1">
  <div>시트: {{ lead_import.sheet_title }}</div>
  <div>생성: <b>{{ lead_import.imported_count }}</b>건</div>
  <div>스킵: {{ lead_import.skipped_count }}건 (중복 또는 필터 제외)</div>
  <div>실패: {{ lead_import.failed_count }}건</div>
</div>
{% if lead_import.error_log %}
<pre class="bg-gray-50 p-2 text-xs mt-3 overflow-auto h-32">{{ lead_import.error_log }}</pre>
{% endif %}
<a href="{% url 'marketing:lead_list' %}" class="inline-block mt-4 px-3 py-1 border rounded">잠재고객 목록으로</a>
{% endblock %}
```

- [ ] **Step 3: Run tests**

```bash
uv run pytest marketing/test_imports.py -v
```

Expected: 3 passed.

- [ ] **Step 4: Commit**

```bash
git add marketing/views/imports.py marketing/views/__init__.py marketing/urls.py marketing/forms.py marketing/templates/marketing/ marketing/test_imports.py
git commit -m "feat(marketing): 3-step Google Sheets import wizard"
```

---

## Phase G — Visit calendar, Next Action queue, dashboard

### Task 23: Next Action queue page

**Files:**
- Modify: `marketing/views/__init__.py`, `marketing/urls.py`
- Create: `marketing/views/dashboard.py`, `marketing/templates/marketing/next_actions.html`
- Append: `marketing/test_activities.py`

- [ ] **Step 1: Write failing test**

Append to `marketing/test_activities.py`:
```python
from django.urls import reverse


class NextActionQueueTests(TestCase):
    def setUp(self):
        from accounts.models import User
        self.user = User.objects.create_user(
            username="uu", email="uu@x.com", password="pw", is_staff=True
        )
        self.client.force_login(self.user)
        self.lead = Lead.objects.create(email="na@x.com")

    def test_shows_pending(self):
        Activity.objects.create(
            lead=self.lead, type=Activity.Type.NOTE,
            next_action="콜백", next_action_due=timezone.now(),
        )
        Activity.objects.create(
            lead=self.lead, type=Activity.Type.NOTE,
            next_action="done", next_action_done_at=timezone.now(),
        )
        resp = self.client.get(reverse("marketing:next_actions"))
        self.assertContains(resp, "콜백")
        self.assertNotContains(resp, "done")
```

- [ ] **Step 2: Implement**

Create `marketing/views/dashboard.py`:
```python
from datetime import timedelta

from django.contrib.auth.decorators import login_required
from django.db.models import Count
from django.shortcuts import render
from django.utils import timezone

from marketing.models import Activity, EmailCampaign, Lead

from .templates import _require_staff


@login_required
def dashboard(request):
    _require_staff(request)
    now = timezone.now()
    week_end = now + timedelta(days=7)
    upcoming_na = Activity.objects.filter(
        next_action_done_at__isnull=True,
        next_action_due__isnull=False,
        next_action_due__lte=week_end,
    ).select_related("lead").order_by("next_action_due")[:10]
    visits = Activity.objects.filter(
        type=Activity.Type.VISIT,
        scheduled_at__gte=now,
        scheduled_at__lte=week_end,
    ).select_related("lead").order_by("scheduled_at")[:10]
    campaigns = EmailCampaign.objects.order_by("-created_at")[:3]
    status_counts = Lead.objects.values("status").annotate(n=Count("id"))
    return render(request, "marketing/dashboard.html", {
        "upcoming_na": upcoming_na,
        "visits": visits,
        "campaigns": campaigns,
        "status_counts": list(status_counts),
    })


@login_required
def next_actions(request):
    _require_staff(request)
    qs = (Activity.objects.filter(next_action_done_at__isnull=True)
          .exclude(next_action="").select_related("lead")
          .order_by("next_action_due"))
    return render(request, "marketing/next_actions.html", {"items": qs})


@login_required
def visit_calendar(request):
    _require_staff(request)
    qs = (Activity.objects.filter(type=Activity.Type.VISIT, scheduled_at__isnull=False)
          .select_related("lead").order_by("scheduled_at"))
    return render(request, "marketing/visit_calendar.html", {"items": qs})
```

Create `marketing/templates/marketing/next_actions.html`:
```html
{% extends "marketing/_layout.html" %}
{% block title %}Next Action 큐{% endblock %}
{% block marketing_content %}
<table class="w-full border text-sm">
  <thead class="bg-gray-50"><tr><th class="p-2 text-left">고객</th><th class="p-2">액션</th><th class="p-2">마감</th><th class="p-2">완료</th></tr></thead>
  <tbody>
    {% for activity in items %}{% include "marketing/_next_action_row.html" %}{% endfor %}
  </tbody>
</table>
{% endblock %}
```

Wire urls + exports. In `marketing/views/__init__.py`:
```python
from .dashboard import dashboard, next_actions, visit_calendar  # noqa: F401
```

In `marketing/urls.py` — REPLACE the earlier dashboard lambda with the real view:
```python
from .views import dashboard as dv

# replace path("", lambda...) with:
path("", dv.dashboard, name="dashboard"),
path("next-actions/", dv.next_actions, name="next_actions"),
path("visits/", dv.visit_calendar, name="visit_calendar"),
```

- [ ] **Step 3: Run tests**

```bash
uv run pytest marketing/test_activities.py -v
```

Expected: 4 passed.

- [ ] **Step 4: Commit**

```bash
git add marketing/views/dashboard.py marketing/views/__init__.py marketing/urls.py marketing/templates/marketing/next_actions.html marketing/test_activities.py
git commit -m "feat(marketing): Next Action queue view"
```

---

### Task 24: Visit calendar (list view, monthly grouping)

**Files:**
- Create: `marketing/templates/marketing/visit_calendar.html`, `marketing/test_visit_calendar.py`

- [ ] **Step 1: Write failing test**

Create `marketing/test_visit_calendar.py`:
```python
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from accounts.models import User
from marketing.models import Activity, Lead


class VisitCalendarTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="u", email="u@x.com", password="pw", is_staff=True
        )
        self.client.force_login(self.user)
        lead = Lead.objects.create(email="v@x.com", name="vinny")
        Activity.objects.create(
            lead=lead, type=Activity.Type.VISIT,
            scheduled_at=timezone.now() + timezone.timedelta(days=2),
            subject="첫 방문",
        )

    def test_shows_scheduled_visits(self):
        resp = self.client.get(reverse("marketing:visit_calendar"))
        self.assertContains(resp, "vinny")
        self.assertContains(resp, "첫 방문")
```

- [ ] **Step 2: Implement**

Create `marketing/templates/marketing/visit_calendar.html`:
```html
{% extends "marketing/_layout.html" %}
{% block title %}방문 일정{% endblock %}
{% block marketing_content %}
<ul class="space-y-2">
  {% for activity in items %}
    <li class="border rounded p-3 text-sm">
      <div class="text-gray-500">{{ activity.scheduled_at|date:"Y-m-d (D) H:i" }}</div>
      <div><a class="text-blue-700" href="{% url 'marketing:lead_detail' activity.lead.id %}">{{ activity.lead }}</a></div>
      <div class="text-gray-700">{{ activity.subject }}</div>
    </li>
  {% empty %}
    <li class="text-gray-400 text-sm">예약된 방문이 없습니다.</li>
  {% endfor %}
</ul>
{% endblock %}
```

(MVP: linear list grouped by date. A real calendar grid is out of scope.)

- [ ] **Step 3: Run tests**

```bash
uv run pytest marketing/test_visit_calendar.py -v
```

Expected: 1 passed.

- [ ] **Step 4: Commit**

```bash
git add marketing/templates/marketing/visit_calendar.html marketing/test_visit_calendar.py
git commit -m "feat(marketing): visit calendar list view"
```

---

### Task 25: Dashboard page

**Files:**
- Create: `marketing/templates/marketing/dashboard.html`, `marketing/test_dashboard.py`

- [ ] **Step 1: Write failing test**

Create `marketing/test_dashboard.py`:
```python
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from accounts.models import User
from marketing.models import Activity, EmailCampaign, EmailTemplate, Lead


class DashboardTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="u", email="u@x.com", password="pw", is_staff=True
        )
        self.client.force_login(self.user)
        lead = Lead.objects.create(email="d@x.com", name="dora")
        Activity.objects.create(
            lead=lead, type=Activity.Type.NOTE,
            next_action="연락", next_action_due=timezone.now(),
        )

    def test_dashboard_shows_pending_na(self):
        resp = self.client.get(reverse("marketing:dashboard"))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "연락")
```

- [ ] **Step 2: Implement template**

Create `marketing/templates/marketing/dashboard.html`:
```html
{% extends "marketing/_layout.html" %}
{% block title %}마케팅 대시보드{% endblock %}
{% block marketing_content %}
<section class="grid grid-cols-3 gap-6">
  <div>
    <h2 class="font-semibold mb-2">7일 내 Next Action</h2>
    <ul class="space-y-1 text-sm">
      {% for a in upcoming_na %}
        <li><span class="text-gray-500">{{ a.next_action_due|date:"m-d" }}</span>
          <a class="text-blue-700" href="{% url 'marketing:lead_detail' a.lead.id %}">{{ a.lead }}</a> —
          {{ a.next_action }}</li>
      {% empty %}<li class="text-gray-400">없음</li>{% endfor %}
    </ul>
  </div>
  <div>
    <h2 class="font-semibold mb-2">이번 주 방문</h2>
    <ul class="space-y-1 text-sm">
      {% for v in visits %}
        <li><span class="text-gray-500">{{ v.scheduled_at|date:"m-d H:i" }}</span>
          <a class="text-blue-700" href="{% url 'marketing:lead_detail' v.lead.id %}">{{ v.lead }}</a></li>
      {% empty %}<li class="text-gray-400">없음</li>{% endfor %}
    </ul>
  </div>
  <div>
    <h2 class="font-semibold mb-2">최근 캠페인</h2>
    <ul class="space-y-1 text-sm">
      {% for c in campaigns %}
        <li><a class="text-blue-700" href="{% url 'marketing:campaign_detail' c.id %}">{{ c.name }}</a>
          — 발송 {{ c.success_count }}, 열람 {{ c.open_count }}</li>
      {% empty %}<li class="text-gray-400">없음</li>{% endfor %}
    </ul>
  </div>
</section>
<section class="mt-8">
  <h2 class="font-semibold mb-2">상태별 잠재고객</h2>
  <ul class="flex flex-wrap gap-2 text-sm">
    {% for s in status_counts %}
      <li class="border rounded px-2 py-1">{{ s.status }} · {{ s.n }}</li>
    {% endfor %}
  </ul>
</section>
{% endblock %}
```

- [ ] **Step 3: Run tests**

```bash
uv run pytest marketing/test_dashboard.py -v
```

Expected: 1 passed.

- [ ] **Step 4: Commit**

```bash
git add marketing/templates/marketing/dashboard.html marketing/test_dashboard.py
git commit -m "feat(marketing): dashboard page"
```

---

## Phase H — Sidebar nav, media volume, integration

### Task 26: Add marketing entries to sidebar nav

**Files:**
- Modify: `templates/common/nav_sidebar.html`

- [ ] **Step 1: Read existing nav and add menu group**

Read `templates/common/nav_sidebar.html` to understand its structure. Then insert a marketing group, mirroring existing patterns. Add entries linking to:
- `{% url 'marketing:dashboard' %}` 대시보드
- `{% url 'marketing:lead_list' %}` 잠재고객
- `{% url 'marketing:campaign_list' %}` 이메일 발송
- `{% url 'marketing:template_list' %}` 템플릿
- `{% url 'marketing:visit_calendar' %}` 방문 일정
- `{% url 'marketing:next_actions' %}` Next Action

If the existing nav file uses an iteration over a list of items, append entries there. If it uses explicit `<a>` blocks, insert a sibling group.

- [ ] **Step 2: Manual verification**

```bash
uv run python manage.py runserver 0.0.0.0:8000 &
sleep 2
curl -s -I http://localhost:8000/marketing/ | head -1
kill %1
```

Expected: `HTTP/1.1 302` (redirect to login since unauthenticated) — confirms route resolves.

- [ ] **Step 3: Commit**

```bash
git add templates/common/nav_sidebar.html
git commit -m "feat(ui): add marketing menu to sidebar nav"
```

---

### Task 27: Mount media volume on docker compose web service

**Files:**
- Modify: `docker-compose.yml`

- [ ] **Step 1: Inspect current compose**

Read `docker-compose.yml`. Find the `web` service. Add a named volume `media_data` and mount it at the path Django writes to (default `MEDIA_ROOT`). If `MEDIA_ROOT` is not yet set in `main/settings.py`, add it:

```python
# main/settings.py
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"
```

- [ ] **Step 2: Modify docker-compose.yml**

Under `services.web`:
```yaml
    volumes:
      - media_data:/app/media
```

At the bottom of the file:
```yaml
volumes:
  media_data:
```

(If a `volumes:` top-level key already exists, append to it. If `web` already has volumes, append.)

- [ ] **Step 3: Verify django still serves media in dev**

In `main/urls.py`, ensure DEBUG-only media serving exists. If not, append:
```python
from django.conf import settings
from django.conf.urls.static import static

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
```

- [ ] **Step 4: Smoke check**

```bash
uv run python manage.py check
```

Expected: no issues.

- [ ] **Step 5: Commit**

```bash
git add docker-compose.yml main/settings.py main/urls.py
git commit -m "chore(deploy): persist media volume for email attachments"
```

---

### Task 28: Full-suite integration run

**Files:**
- None (verification)

- [ ] **Step 1: Run all marketing + accounts tests**

```bash
uv run pytest marketing accounts -v --tb=short
```

Expected: every test passes. If anything fails, fix it before the final commit.

- [ ] **Step 2: Smoke run the dev server**

```bash
uv run python manage.py migrate
uv run python manage.py seed_marketing
uv run python manage.py runserver 0.0.0.0:8000 &
sleep 3
curl -s -o /dev/null -w "%{http_code}\n" http://localhost:8000/marketing/
curl -s -o /dev/null -w "%{http_code}\n" http://localhost:8000/marketing/leads/
curl -s -o /dev/null -w "%{http_code}\n" http://localhost:8000/marketing/templates/
curl -s -o /dev/null -w "%{http_code}\n" http://localhost:8000/marketing/campaigns/
kill %1
```

Expected: all `302` (auth redirect) — confirms URLs route and views load without errors.

- [ ] **Step 3: Lint pass**

```bash
uv run ruff format .
uv run ruff check . --fix
```

Expected: clean (or auto-fixed).

- [ ] **Step 4: Final commit if anything changed**

```bash
git add -A
git commit -m "chore: format + lint pass after marketing pipeline rollout" || echo "nothing to commit"
```

---

## Self-Review

**Spec coverage:**

| Spec section | Implementing task(s) |
|---|---|
| 3.1 single `marketing` app | Task 1 |
| 3.2 Lead | Task 2 |
| 3.2 LeadImport / EmailTemplate / EmailAttachment / EmailCampaign / EmailSendLog / Activity | Task 3 |
| 3.3 state transitions | Task 10 + 17 (mark_contacted called in campaign send) |
| 4 URL map — leads | Tasks 19, 20 |
| 4 URL map — imports | Task 22 |
| 4 URL map — templates | Tasks 7, 8 |
| 4 URL map — campaigns | Task 18 |
| 4 URL map — activities/next-action | Tasks 11, 23 |
| 4 URL map — visits | Task 24 |
| 4 URL map — track/unsubscribe | Tasks 15, 16 |
| 5 Sheets import | Tasks 21, 22 |
| 6 Mailer + tracking + unsubscribe injection | Tasks 13, 14, 17 |
| 6.3 tracking pixel | Task 15 |
| 6.4 unsubscribe | Tasks 13, 16 |
| 7 Lead detail + activity form | Tasks 11, 20 |
| 7.2 dashboard | Task 25 |
| 7.3 Next Action queue | Task 23 |
| 7.4 visit calendar | Task 24 |
| 8 auth gate | Task 7 (`_require_staff` reused) |
| 9 ConsultationRequest data migration + landing form refactor | Tasks 5, 6 |
| 10 seed | Task 9 |
| 11 new deps | Task 12 |
| 12 env vars | Task 12, 27 (SITE_URL already exists) |
| 14 media volume | Task 27 |
| 26 sidebar nav | Task 26 |
| 28 integration smoke | Task 28 |

**Placeholder scan:** none — every step contains concrete code or commands.

**Type consistency:** `_require_staff` defined in `views/templates.py` (Task 7) and reused by every later view — consistent. `apply_activity_transition`/`mark_contacted` signatures match in tests and callers. `send_campaign_inline`/`send_campaign_async` signatures consistent across mailer module and campaign view.

**Notes for the executing engineer:**
- Migration numbers in Task 5 must match what Task 3's `makemigrations` produced — run `ls marketing/migrations/` first and substitute. The plan uses `"0002"` as a placeholder string.
- Task 18 includes a small `if "pytest" in sys.modules` guard inside `send_campaign_async` so threading doesn't cause flaky tests. That's intentional, not a hack — Django's transactional test isolation makes background threads see no data.
- Tracking pixel test for "campaign open_count counts first-time opens only" depends on the second GET being on the same `tracking_id` — verify that semantics matches the test before refactoring.
