# research 앱 Phase 1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `research` Django 앱을 만들어 과제(Project) + 월간 연구노트(MonthlyNote) 핵심 CRUD와 서명/승인 워크플로우를 구현한다.

**Architecture:** `research` 앱을 신규 생성하고 `companies` 앱의 `ResearchInstitute` / `Researcher`에 FK로 연결한다. HTMX 네비게이션은 `request.htmx` 분기로 전체 페이지/파셜 템플릿을 구분하는 기존 패턴을 그대로 사용한다. 상태 전환(서명 → 승인)은 POST 전용 뷰로 처리하고 타임스탬프를 기록한다.

**Tech Stack:** Django 5.2, PostgreSQL, HTMX, Tailwind CSS, pytest + pytest-django

**Out of scope (이번 Phase 아님):** AI 문서 생성, PDF 출력, 음성 입력, 컴플라이언스 캘린더, 전자서명 이미지, MonthlyMilestone CRUD UI (모델만 생성)

---

## File Structure

```
research/
├── __init__.py
├── admin.py
├── apps.py
├── forms.py
├── migrations/
│   ├── __init__.py
│   └── 0001_initial.py       (makemigrations로 자동 생성)
├── models.py
├── urls.py
├── views.py
└── tests.py

templates/research/
├── project_list.html            (base.html 상속 전체 페이지)
├── project_form.html            (create + edit 공용)
├── project_detail.html
├── note_list.html
├── note_form.html
├── note_detail.html
└── partials/
    ├── project_list_content.html    (HTMX 파셜)
    ├── project_form_content.html
    ├── project_detail_content.html
    ├── note_list_content.html
    ├── note_form_content.html
    └── note_detail_content.html

main/urls.py                         (수정: research URLs 추가)
main/settings.py                     (수정: INSTALLED_APPS에 research 추가)
templates/common/nav_sidebar.html    (수정: 과제 목록 링크 추가)
```

---

## Task 1: research 앱 생성 + 모델 + 마이그레이션

**Files:**
- Create: `research/__init__.py`, `research/apps.py`, `research/models.py`, `research/admin.py`, `research/forms.py`, `research/urls.py`, `research/views.py`, `research/tests.py`
- Modify: `main/settings.py` (INSTALLED_APPS)
- Modify: `main/urls.py` (include research.urls)

- [ ] **Step 1: 앱 디렉토리 생성**

```bash
cd /home/chaconne/rndlog
python manage.py startapp research
```

Expected output: `research/` 디렉토리 생성됨.

- [ ] **Step 2: `research/models.py` 작성**

```python
from django.db import models

from common.mixins import BaseModel
from companies.models import ResearchInstitute, Researcher


class Project(BaseModel):
    class Status(models.TextChoices):
        DRAFT = "draft", "초안"
        ACTIVE = "active", "진행중"
        COMPLETED = "completed", "완료"
        SUSPENDED = "suspended", "중단"

    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    period_start = models.DateField()
    period_end = models.DateField()
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.DRAFT
    )
    budget_personnel = models.DecimalField(max_digits=14, decimal_places=0, default=0)
    budget_material = models.DecimalField(max_digits=14, decimal_places=0, default=0)
    budget_outsource = models.DecimalField(max_digits=14, decimal_places=0, default=0)
    institute = models.ForeignKey(
        ResearchInstitute, on_delete=models.CASCADE, related_name="projects"
    )

    class Meta:
        ordering = ["-period_start"]

    def __str__(self) -> str:
        return self.title

    @property
    def budget_total(self) -> int:
        return int(self.budget_personnel + self.budget_material + self.budget_outsource)


class MonthlyMilestone(BaseModel):
    class MilestoneStatus(models.TextChoices):
        UPCOMING = "upcoming", "예정"
        IN_PROGRESS = "in_progress", "진행중"
        COMPLETED = "completed", "완료"
        DELAYED = "delayed", "지연"

    project = models.ForeignKey(
        Project, on_delete=models.CASCADE, related_name="milestones"
    )
    month_number = models.PositiveSmallIntegerField()  # 1~12
    target_month = models.DateField()
    objective = models.TextField()
    tasks = models.JSONField(default=list)  # list[str]
    expected_outputs = models.TextField(blank=True)
    note_guide = models.TextField(blank=True)
    status = models.CharField(
        max_length=20,
        choices=MilestoneStatus.choices,
        default=MilestoneStatus.UPCOMING,
    )
    actual_result = models.TextField(blank=True)

    class Meta:
        ordering = ["month_number"]
        unique_together = ("project", "month_number")

    def __str__(self) -> str:
        return f"{self.project.title} M{self.month_number}"


class MonthlyNote(BaseModel):
    class NoteStatus(models.TextChoices):
        DRAFT = "draft", "작성중"
        RESEARCHER_SIGNED = "researcher_signed", "연구원 서명"
        MANAGER_APPROVED = "manager_approved", "연구소장 승인"

    researcher = models.ForeignKey(
        Researcher, on_delete=models.CASCADE, related_name="notes"
    )
    project = models.ForeignKey(
        Project, on_delete=models.CASCADE, related_name="notes"
    )
    milestone = models.ForeignKey(
        MonthlyMilestone,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="notes",
    )
    month = models.DateField()  # 해당 월의 1일 (e.g. 2026-01-01)

    # 입력 데이터
    activities = models.TextField(blank=True)
    challenges = models.TextField(blank=True)
    results = models.TextField(blank=True)

    # 상태 + 타임스탬프 증빙 체인
    status = models.CharField(
        max_length=30, choices=NoteStatus.choices, default=NoteStatus.DRAFT
    )
    notified_at = models.DateTimeField(null=True, blank=True)
    researcher_signed_at = models.DateTimeField(null=True, blank=True)
    manager_approved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-month"]
        unique_together = ("researcher", "project", "month")

    def __str__(self) -> str:
        return f"{self.project.title} {self.month.strftime('%Y-%m')} - {self.researcher.name}"
```

- [ ] **Step 3: `main/settings.py` INSTALLED_APPS에 `"research"` 추가**

`"companies",` 다음 줄에 추가:
```python
    "companies",
    "research",
```

- [ ] **Step 4: `main/urls.py`에 research URLs 추가**

`research/urls.py`는 아직 없으므로 빈 파일 먼저 생성:

```python
# research/urls.py
from django.urls import path
from . import views

urlpatterns = []
```

그런 다음 `main/urls.py` 수정:

```python
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

from companies.views import dashboard

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", dashboard, name="dashboard"),
    path("", include("accounts.urls")),
    path("companies/", include("companies.urls")),
    path("projects/", include("research.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
```

- [ ] **Step 5: 마이그레이션 생성 및 적용**

```bash
python manage.py makemigrations research
python manage.py migrate
```

Expected: `research/migrations/0001_initial.py` 생성, migrate 성공.

- [ ] **Step 6: `research/tests.py`에 모델 테스트 작성**

```python
import datetime

import pytest
from django.test import Client
from django.urls import reverse

from accounts.models import User
from companies.models import Company, Membership, ResearchInstitute, Researcher
from research.models import MonthlyNote, Project


# ──────────────── Fixtures ────────────────

@pytest.fixture
def user(db):
    return User.objects.create_user(
        username="testuser", email="test@example.com", password="password123"
    )


@pytest.fixture
def company(db):
    return Company.objects.create(name="테스트 기업")


@pytest.fixture
def institute(db, company):
    return ResearchInstitute.objects.create(name="테스트 연구소", company=company)


@pytest.fixture
def membership(db, user, company):
    return Membership.objects.create(
        user=user, company=company, role=Membership.Role.MANAGER
    )


@pytest.fixture
def researcher(db, user, institute):
    return Researcher.objects.create(name="테스트 연구원", institute=institute, user=user)


@pytest.fixture
def project(db, institute):
    return Project.objects.create(
        title="테스트 과제",
        period_start=datetime.date(2026, 1, 1),
        period_end=datetime.date(2026, 12, 31),
        institute=institute,
    )


@pytest.fixture
def logged_in_client(db, user, membership):
    client = Client()
    client.force_login(user)
    return client


# ──────────────── Model tests ────────────────

class TestProjectModel:
    def test_str(self, project):
        assert str(project) == "테스트 과제"

    def test_budget_total(self, project):
        project.budget_personnel = 48_000_000
        project.budget_material = 12_000_000
        project.save()
        assert project.budget_total == 60_000_000

    def test_default_status_is_draft(self, project):
        assert project.status == Project.Status.DRAFT


class TestMonthlyNoteModel:
    def test_str(self, db, project, researcher):
        note = MonthlyNote.objects.create(
            researcher=researcher,
            project=project,
            month=datetime.date(2026, 1, 1),
        )
        assert "테스트 과제" in str(note)
        assert "2026-01" in str(note)
```

- [ ] **Step 7: 테스트 실행 — 통과 확인**

```bash
python -m pytest research/tests.py -v
```

Expected: 4 tests PASSED.

- [ ] **Step 8: Commit**

```bash
git add research/ main/settings.py main/urls.py
git commit -m "feat: add research app with Project, MonthlyMilestone, MonthlyNote models"
```

---

## Task 2: Project CRUD (목록 + 등록 + 상세 + 수정)

**Files:**
- Modify: `research/forms.py`
- Modify: `research/views.py`
- Modify: `research/urls.py`
- Create: `templates/research/project_list.html`
- Create: `templates/research/project_form.html`
- Create: `templates/research/project_detail.html`
- Create: `templates/research/partials/project_list_content.html`
- Create: `templates/research/partials/project_form_content.html`
- Create: `templates/research/partials/project_detail_content.html`

- [ ] **Step 1: Project 뷰 테스트 작성 — 실패 확인**

`research/tests.py`에 다음 클래스 추가:

```python
class TestProjectList:
    def test_unauthenticated_redirects(self, db):
        response = Client().get(reverse("project_list"))
        assert response.status_code == 302

    def test_empty_list(self, logged_in_client):
        response = logged_in_client.get(reverse("project_list"))
        assert response.status_code == 200

    def test_shows_project(self, logged_in_client, project):
        response = logged_in_client.get(reverse("project_list"))
        assert "테스트 과제" in response.content.decode()

    def test_project_from_other_company_not_shown(self, logged_in_client, db):
        other_company = Company.objects.create(name="다른 기업")
        other_institute = ResearchInstitute.objects.create(
            name="다른 연구소", company=other_company
        )
        Project.objects.create(
            title="다른 과제",
            period_start=datetime.date(2026, 1, 1),
            period_end=datetime.date(2026, 12, 31),
            institute=other_institute,
        )
        response = logged_in_client.get(reverse("project_list"))
        assert "다른 과제" not in response.content.decode()


class TestProjectCreate:
    def test_get(self, logged_in_client):
        response = logged_in_client.get(reverse("project_create"))
        assert response.status_code == 200

    def test_post_creates_project(self, logged_in_client, institute):
        response = logged_in_client.post(
            reverse("project_create"),
            {
                "title": "새 과제",
                "description": "",
                "period_start": "2026-01-01",
                "period_end": "2026-12-31",
                "status": "draft",
                "budget_personnel": 0,
                "budget_material": 0,
                "budget_outsource": 0,
                "institute": str(institute.pk),
            },
        )
        assert response.status_code == 302
        assert Project.objects.filter(title="새 과제").exists()

    def test_cannot_create_for_other_institute(self, logged_in_client, db):
        other_company = Company.objects.create(name="다른 기업")
        other_institute = ResearchInstitute.objects.create(
            name="다른 연구소", company=other_company
        )
        response = logged_in_client.post(
            reverse("project_create"),
            {
                "title": "침입 과제",
                "period_start": "2026-01-01",
                "period_end": "2026-12-31",
                "status": "draft",
                "budget_personnel": 0,
                "budget_material": 0,
                "budget_outsource": 0,
                "institute": str(other_institute.pk),
            },
        )
        # form error, not redirect
        assert response.status_code == 200
        assert not Project.objects.filter(title="침입 과제").exists()


class TestProjectDetail:
    def test_get(self, logged_in_client, project):
        response = logged_in_client.get(
            reverse("project_detail", kwargs={"pk": project.pk})
        )
        assert response.status_code == 200
        assert "테스트 과제" in response.content.decode()

    def test_404_for_other_company(self, logged_in_client, db):
        other_company = Company.objects.create(name="다른 기업")
        other_institute = ResearchInstitute.objects.create(
            name="다른 연구소", company=other_company
        )
        other_project = Project.objects.create(
            title="다른 과제",
            period_start=datetime.date(2026, 1, 1),
            period_end=datetime.date(2026, 12, 31),
            institute=other_institute,
        )
        response = logged_in_client.get(
            reverse("project_detail", kwargs={"pk": other_project.pk})
        )
        assert response.status_code == 404
```

- [ ] **Step 2: 테스트 실행 — 실패 확인**

```bash
python -m pytest research/tests.py::TestProjectList research/tests.py::TestProjectCreate research/tests.py::TestProjectDetail -v
```

Expected: NoReverseMatch 오류 — 뷰가 없으므로 FAIL. 정상.

- [ ] **Step 3: `research/forms.py` 작성**

```python
from django import forms

from .models import MonthlyNote, Project


class ProjectForm(forms.ModelForm):
    class Meta:
        model = Project
        fields = [
            "title",
            "description",
            "period_start",
            "period_end",
            "status",
            "budget_personnel",
            "budget_material",
            "budget_outsource",
            "institute",
        ]
        widgets = {
            "description": forms.Textarea(attrs={"rows": 4}),
            "period_start": forms.DateInput(attrs={"type": "date"}),
            "period_end": forms.DateInput(attrs={"type": "date"}),
        }


class MonthlyNoteForm(forms.ModelForm):
    class Meta:
        model = MonthlyNote
        fields = ["researcher", "month", "milestone", "activities", "challenges", "results"]
        widgets = {
            "month": forms.DateInput(attrs={"type": "date"}),
            "activities": forms.Textarea(attrs={"rows": 6}),
            "challenges": forms.Textarea(attrs={"rows": 4}),
            "results": forms.Textarea(attrs={"rows": 4}),
        }

    def __init__(self, *args, project=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["milestone"].required = False
        if project:
            self.fields["researcher"].queryset = project.institute.researchers.all()
            self.fields["milestone"].queryset = project.milestones.all()
```

- [ ] **Step 4: `research/views.py` 작성 (Project 뷰)**

```python
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from companies.models import ResearchInstitute
from .forms import MonthlyNoteForm, ProjectForm
from .models import MonthlyNote, Project


def _accessible_institutes(user):
    company_ids = user.memberships.values_list("company_id", flat=True)
    return ResearchInstitute.objects.filter(company_id__in=company_ids)


@login_required
def project_list(request):
    institutes = _accessible_institutes(request.user)
    projects = Project.objects.filter(
        institute__in=institutes
    ).select_related("institute__company")
    template = (
        "research/partials/project_list_content.html"
        if request.htmx
        else "research/project_list.html"
    )
    return render(request, template, {"projects": projects})


@login_required
def project_create(request):
    institutes = _accessible_institutes(request.user)
    if request.method == "POST":
        form = ProjectForm(request.POST)
        form.fields["institute"].queryset = institutes
        if form.is_valid():
            project = form.save(commit=False)
            if project.institute not in institutes:
                form.add_error("institute", "권한이 없는 연구소입니다.")
            else:
                project.save()
                return redirect("project_detail", pk=project.pk)
    else:
        form = ProjectForm()
        form.fields["institute"].queryset = institutes

    template = (
        "research/partials/project_form_content.html"
        if request.htmx
        else "research/project_form.html"
    )
    return render(request, template, {"form": form, "action": "등록"})


@login_required
def project_detail(request, pk):
    institutes = _accessible_institutes(request.user)
    project = get_object_or_404(Project, pk=pk, institute__in=institutes)
    milestones = project.milestones.all()
    notes = project.notes.select_related("researcher").order_by("-month")
    template = (
        "research/partials/project_detail_content.html"
        if request.htmx
        else "research/project_detail.html"
    )
    return render(
        request,
        template,
        {"project": project, "milestones": milestones, "notes": notes},
    )


@login_required
def project_edit(request, pk):
    institutes = _accessible_institutes(request.user)
    project = get_object_or_404(Project, pk=pk, institute__in=institutes)
    if request.method == "POST":
        form = ProjectForm(request.POST, instance=project)
        form.fields["institute"].queryset = institutes
        if form.is_valid():
            form.save()
            return redirect("project_detail", pk=project.pk)
    else:
        form = ProjectForm(instance=project)
        form.fields["institute"].queryset = institutes

    template = (
        "research/partials/project_form_content.html"
        if request.htmx
        else "research/project_form.html"
    )
    return render(
        request, template, {"form": form, "project": project, "action": "수정"}
    )
```

- [ ] **Step 5: `research/urls.py` Project URL 추가**

```python
from django.urls import path

from . import views

urlpatterns = [
    path("", views.project_list, name="project_list"),
    path("new/", views.project_create, name="project_create"),
    path("<uuid:pk>/", views.project_detail, name="project_detail"),
    path("<uuid:pk>/edit/", views.project_edit, name="project_edit"),
]
```

- [ ] **Step 6: 템플릿 디렉토리 생성**

```bash
mkdir -p templates/research/partials
```

- [ ] **Step 7: `templates/research/project_list.html` 작성**

```html
{% extends "common/base.html" %}
{% block title %}연구과제 목록{% endblock %}
{% block content %}{% include "research/partials/project_list_content.html" %}{% endblock %}
```

- [ ] **Step 8: `templates/research/partials/project_list_content.html` 작성**

```html
<div class="p-4 lg:p-8">
  <div class="flex items-center justify-between mb-6">
    <h1 class="text-xl font-bold text-gray-900">연구과제 목록</h1>
    <a href="{% url 'project_create' %}"
       hx-get="{% url 'project_create' %}"
       hx-target="#main-content"
       hx-push-url="true"
       class="bg-blue-600 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-blue-700">
      + 과제 등록
    </a>
  </div>

  {% if projects %}
  <div class="space-y-3">
    {% for project in projects %}
    <a href="{% url 'project_detail' project.pk %}"
       hx-get="{% url 'project_detail' project.pk %}"
       hx-target="#main-content"
       hx-push-url="true"
       class="block bg-white rounded-xl border border-gray-200 p-4 hover:border-blue-300 hover:shadow-sm transition">
      <div class="flex items-center justify-between">
        <div class="min-w-0">
          <div class="font-semibold text-gray-900 truncate">{{ project.title }}</div>
          <div class="text-sm text-gray-500 mt-0.5">
            {{ project.institute.company.name }} · {{ project.period_start }} ~ {{ project.period_end }}
          </div>
        </div>
        <span class="ml-3 flex-shrink-0 text-xs px-2.5 py-1 rounded-full font-medium
          {% if project.status == 'active' %}bg-green-100 text-green-700
          {% elif project.status == 'draft' %}bg-gray-100 text-gray-600
          {% elif project.status == 'completed' %}bg-blue-100 text-blue-700
          {% else %}bg-yellow-100 text-yellow-700{% endif %}">
          {{ project.get_status_display }}
        </span>
      </div>
    </a>
    {% endfor %}
  </div>
  {% else %}
  <div class="text-center py-20 text-gray-400">등록된 과제가 없습니다.</div>
  {% endif %}
</div>
```

- [ ] **Step 9: `templates/research/project_form.html` 작성**

```html
{% extends "common/base.html" %}
{% block title %}과제 {{ action }}{% endblock %}
{% block content %}{% include "research/partials/project_form_content.html" %}{% endblock %}
```

- [ ] **Step 10: `templates/research/partials/project_form_content.html` 작성**

```html
{% load widget_tweaks %}
<div class="p-4 lg:p-8 max-w-2xl">
  <div class="flex items-center gap-3 mb-6">
    <a href="{% url 'project_list' %}"
       hx-get="{% url 'project_list' %}"
       hx-target="#main-content"
       hx-push-url="true"
       class="text-gray-400 hover:text-gray-600">
      ← 목록
    </a>
    <h1 class="text-xl font-bold text-gray-900">과제 {{ action }}</h1>
  </div>

  <form method="post"
        {% if project %}
        hx-post="{% url 'project_edit' project.pk %}"
        {% else %}
        hx-post="{% url 'project_create' %}"
        {% endif %}
        hx-target="#main-content"
        hx-push-url="true"
        class="bg-white rounded-xl border border-gray-200 p-6 space-y-4">
    {% csrf_token %}

    {% for field in form %}
    <div>
      <label class="block text-sm font-medium text-gray-700 mb-1">{{ field.label }}</label>
      {{ field|add_class:"w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500" }}
      {% if field.errors %}
      <p class="text-red-500 text-xs mt-1">{{ field.errors.0 }}</p>
      {% endif %}
    </div>
    {% endfor %}

    <div class="flex gap-3 pt-2">
      <button type="submit"
              class="bg-blue-600 text-white px-6 py-2 rounded-lg text-sm font-medium hover:bg-blue-700">
        {{ action }}
      </button>
      <a href="{% if project %}{% url 'project_detail' project.pk %}{% else %}{% url 'project_list' %}{% endif %}"
         hx-get="{% if project %}{% url 'project_detail' project.pk %}{% else %}{% url 'project_list' %}{% endif %}"
         hx-target="#main-content"
         hx-push-url="true"
         class="bg-gray-100 text-gray-700 px-6 py-2 rounded-lg text-sm font-medium hover:bg-gray-200">
        취소
      </a>
    </div>
  </form>
</div>
```

- [ ] **Step 11: `templates/research/project_detail.html` 작성**

```html
{% extends "common/base.html" %}
{% block title %}{{ project.title }}{% endblock %}
{% block content %}{% include "research/partials/project_detail_content.html" %}{% endblock %}
```

- [ ] **Step 12: `templates/research/partials/project_detail_content.html` 작성**

```html
<div class="p-4 lg:p-8 max-w-3xl">
  <div class="flex items-center gap-3 mb-4">
    <a href="{% url 'project_list' %}"
       hx-get="{% url 'project_list' %}"
       hx-target="#main-content"
       hx-push-url="true"
       class="text-gray-400 hover:text-gray-600">
      ← 목록
    </a>
  </div>

  <!-- 과제 헤더 -->
  <div class="bg-white rounded-xl border border-gray-200 p-6 mb-4">
    <div class="flex items-start justify-between gap-4">
      <div>
        <h1 class="text-xl font-bold text-gray-900">{{ project.title }}</h1>
        <p class="text-sm text-gray-500 mt-1">
          {{ project.institute.company.name }} · {{ project.institute.name }}
        </p>
        <p class="text-sm text-gray-500">
          기간: {{ project.period_start }} ~ {{ project.period_end }}
        </p>
        {% if project.description %}
        <p class="text-sm text-gray-700 mt-2">{{ project.description }}</p>
        {% endif %}
      </div>
      <div class="flex flex-col items-end gap-2">
        <span class="text-xs px-2.5 py-1 rounded-full font-medium
          {% if project.status == 'active' %}bg-green-100 text-green-700
          {% elif project.status == 'draft' %}bg-gray-100 text-gray-600
          {% elif project.status == 'completed' %}bg-blue-100 text-blue-700
          {% else %}bg-yellow-100 text-yellow-700{% endif %}">
          {{ project.get_status_display }}
        </span>
        <a href="{% url 'project_edit' project.pk %}"
           hx-get="{% url 'project_edit' project.pk %}"
           hx-target="#main-content"
           hx-push-url="true"
           class="text-xs text-gray-500 hover:text-blue-600">
          수정
        </a>
      </div>
    </div>
    <!-- 예산 -->
    <div class="mt-4 pt-4 border-t border-gray-100 grid grid-cols-3 gap-4 text-center">
      <div>
        <div class="text-xs text-gray-500">인건비</div>
        <div class="text-sm font-semibold">{{ project.budget_personnel|floatformat:0 }}원</div>
      </div>
      <div>
        <div class="text-xs text-gray-500">재료비</div>
        <div class="text-sm font-semibold">{{ project.budget_material|floatformat:0 }}원</div>
      </div>
      <div>
        <div class="text-xs text-gray-500">합계</div>
        <div class="text-sm font-bold text-blue-600">{{ project.budget_total }}원</div>
      </div>
    </div>
  </div>

  <!-- 연구노트 목록 -->
  <div class="flex items-center justify-between mb-3">
    <h2 class="font-semibold text-gray-800">월간 연구노트</h2>
    <a href="{% url 'note_create' project_pk=project.pk %}"
       hx-get="{% url 'note_create' project_pk=project.pk %}"
       hx-target="#main-content"
       hx-push-url="true"
       class="bg-blue-600 text-white px-3 py-1.5 rounded-lg text-xs font-medium hover:bg-blue-700">
      + 노트 작성
    </a>
  </div>

  {% if notes %}
  <div class="space-y-2">
    {% for note in notes %}
    <a href="{% url 'note_detail' project_pk=project.pk pk=note.pk %}"
       hx-get="{% url 'note_detail' project_pk=project.pk pk=note.pk %}"
       hx-target="#main-content"
       hx-push-url="true"
       class="block bg-white rounded-lg border border-gray-200 p-3 hover:border-blue-300 transition">
      <div class="flex items-center justify-between">
        <div>
          <span class="font-medium text-gray-900">{{ note.month|date:"Y년 m월" }}</span>
          <span class="text-sm text-gray-500 ml-2">{{ note.researcher.name }}</span>
        </div>
        <span class="text-xs px-2 py-0.5 rounded-full
          {% if note.status == 'manager_approved' %}bg-green-100 text-green-700
          {% elif note.status == 'researcher_signed' %}bg-blue-100 text-blue-700
          {% else %}bg-gray-100 text-gray-600{% endif %}">
          {{ note.get_status_display }}
        </span>
      </div>
    </a>
    {% endfor %}
  </div>
  {% else %}
  <p class="text-gray-400 text-sm py-4">작성된 연구노트가 없습니다.</p>
  {% endif %}
</div>
```

- [ ] **Step 13: 테스트 실행 — 통과 확인**

```bash
python -m pytest research/tests.py -v
```

Expected: 기존 4 + 신규 8 = 12 tests PASSED.

- [ ] **Step 14: Commit**

```bash
git add research/ templates/research/ main/urls.py
git commit -m "feat: add Project CRUD views and templates"
```

---

## Task 3: MonthlyNote CRUD (목록 + 등록 + 상세 + 수정)

**Files:**
- Modify: `research/views.py` (note views 추가)
- Modify: `research/urls.py` (note URL 추가)
- Create: `templates/research/note_list.html`
- Create: `templates/research/note_form.html`
- Create: `templates/research/note_detail.html`
- Create: `templates/research/partials/note_list_content.html`
- Create: `templates/research/partials/note_form_content.html`
- Create: `templates/research/partials/note_detail_content.html`

- [ ] **Step 1: MonthlyNote 뷰 테스트 작성 — 실패 확인**

`research/tests.py`에 추가:

```python
@pytest.fixture
def note(db, project, researcher):
    return MonthlyNote.objects.create(
        researcher=researcher,
        project=project,
        month=datetime.date(2026, 1, 1),
        activities="1월 실험 수행",
        results="결과 확인",
    )


class TestNoteList:
    def test_get(self, logged_in_client, project, note):
        response = logged_in_client.get(
            reverse("note_list", kwargs={"project_pk": project.pk})
        )
        assert response.status_code == 200
        assert "1월" in response.content.decode()

    def test_404_for_other_project(self, logged_in_client, db):
        other_company = Company.objects.create(name="다른 기업")
        other_institute = ResearchInstitute.objects.create(
            name="다른 연구소", company=other_company
        )
        other_project = Project.objects.create(
            title="다른 과제",
            period_start=datetime.date(2026, 1, 1),
            period_end=datetime.date(2026, 12, 31),
            institute=other_institute,
        )
        response = logged_in_client.get(
            reverse("note_list", kwargs={"project_pk": other_project.pk})
        )
        assert response.status_code == 404


class TestNoteCreate:
    def test_get(self, logged_in_client, project):
        response = logged_in_client.get(
            reverse("note_create", kwargs={"project_pk": project.pk})
        )
        assert response.status_code == 200

    def test_post_creates_note(self, logged_in_client, project, researcher):
        response = logged_in_client.post(
            reverse("note_create", kwargs={"project_pk": project.pk}),
            {
                "researcher": str(researcher.pk),
                "month": "2026-03-01",
                "activities": "3월 활동",
                "challenges": "",
                "results": "",
            },
        )
        assert response.status_code == 302
        assert MonthlyNote.objects.filter(
            project=project, month=datetime.date(2026, 3, 1)
        ).exists()

    def test_notified_at_set_on_create(self, logged_in_client, project, researcher):
        logged_in_client.post(
            reverse("note_create", kwargs={"project_pk": project.pk}),
            {
                "researcher": str(researcher.pk),
                "month": "2026-04-01",
                "activities": "4월 활동",
                "challenges": "",
                "results": "",
            },
        )
        note = MonthlyNote.objects.get(project=project, month=datetime.date(2026, 4, 1))
        assert note.notified_at is not None


class TestNoteDetail:
    def test_get(self, logged_in_client, project, note):
        response = logged_in_client.get(
            reverse("note_detail", kwargs={"project_pk": project.pk, "pk": note.pk})
        )
        assert response.status_code == 200
        assert "1월 실험 수행" in response.content.decode()

    def test_edit_blocked_after_sign(self, logged_in_client, project, note):
        note.status = MonthlyNote.NoteStatus.RESEARCHER_SIGNED
        note.save()
        response = logged_in_client.get(
            reverse("note_edit", kwargs={"project_pk": project.pk, "pk": note.pk})
        )
        # redirect back to detail (edit blocked)
        assert response.status_code == 302
```

- [ ] **Step 2: 테스트 실행 — 실패 확인**

```bash
python -m pytest research/tests.py::TestNoteList research/tests.py::TestNoteCreate research/tests.py::TestNoteDetail -v
```

Expected: NoReverseMatch — FAIL. 정상.

- [ ] **Step 3: `research/views.py`에 Note 뷰 추가**

기존 `project_edit` 함수 아래에 추가:

```python
@login_required
def note_list(request, project_pk):
    institutes = _accessible_institutes(request.user)
    project = get_object_or_404(Project, pk=project_pk, institute__in=institutes)
    notes = project.notes.select_related("researcher", "milestone").order_by("-month")
    template = (
        "research/partials/note_list_content.html"
        if request.htmx
        else "research/note_list.html"
    )
    return render(request, template, {"project": project, "notes": notes})


@login_required
def note_create(request, project_pk):
    institutes = _accessible_institutes(request.user)
    project = get_object_or_404(Project, pk=project_pk, institute__in=institutes)
    if request.method == "POST":
        form = MonthlyNoteForm(request.POST, project=project)
        if form.is_valid():
            note = form.save(commit=False)
            note.project = project
            note.notified_at = timezone.now()
            note.save()
            return redirect("note_detail", project_pk=project.pk, pk=note.pk)
    else:
        form = MonthlyNoteForm(project=project)
    template = (
        "research/partials/note_form_content.html"
        if request.htmx
        else "research/note_form.html"
    )
    return render(request, template, {"form": form, "project": project, "action": "등록"})


@login_required
def note_detail(request, project_pk, pk):
    institutes = _accessible_institutes(request.user)
    project = get_object_or_404(Project, pk=project_pk, institute__in=institutes)
    note = get_object_or_404(MonthlyNote, pk=pk, project=project)
    template = (
        "research/partials/note_detail_content.html"
        if request.htmx
        else "research/note_detail.html"
    )
    return render(request, template, {"project": project, "note": note})


@login_required
def note_edit(request, project_pk, pk):
    institutes = _accessible_institutes(request.user)
    project = get_object_or_404(Project, pk=project_pk, institute__in=institutes)
    note = get_object_or_404(MonthlyNote, pk=pk, project=project)
    if note.status != MonthlyNote.NoteStatus.DRAFT:
        return redirect("note_detail", project_pk=project.pk, pk=note.pk)
    if request.method == "POST":
        form = MonthlyNoteForm(request.POST, instance=note, project=project)
        if form.is_valid():
            form.save()
            return redirect("note_detail", project_pk=project.pk, pk=note.pk)
    else:
        form = MonthlyNoteForm(instance=note, project=project)
    template = (
        "research/partials/note_form_content.html"
        if request.htmx
        else "research/note_form.html"
    )
    return render(
        request, template, {"form": form, "project": project, "note": note, "action": "수정"}
    )
```

- [ ] **Step 4: `research/urls.py`에 Note URL 추가**

```python
from django.urls import path

from . import views

urlpatterns = [
    path("", views.project_list, name="project_list"),
    path("new/", views.project_create, name="project_create"),
    path("<uuid:pk>/", views.project_detail, name="project_detail"),
    path("<uuid:pk>/edit/", views.project_edit, name="project_edit"),
    # Note URLs
    path("<uuid:project_pk>/notes/", views.note_list, name="note_list"),
    path("<uuid:project_pk>/notes/new/", views.note_create, name="note_create"),
    path("<uuid:project_pk>/notes/<uuid:pk>/", views.note_detail, name="note_detail"),
    path("<uuid:project_pk>/notes/<uuid:pk>/edit/", views.note_edit, name="note_edit"),
]
```

- [ ] **Step 5: `templates/research/note_list.html` 작성**

```html
{% extends "common/base.html" %}
{% block title %}연구노트 목록 — {{ project.title }}{% endblock %}
{% block content %}{% include "research/partials/note_list_content.html" %}{% endblock %}
```

- [ ] **Step 6: `templates/research/partials/note_list_content.html` 작성**

```html
<div class="p-4 lg:p-8 max-w-2xl">
  <div class="flex items-center gap-3 mb-4">
    <a href="{% url 'project_detail' project.pk %}"
       hx-get="{% url 'project_detail' project.pk %}"
       hx-target="#main-content"
       hx-push-url="true"
       class="text-gray-400 hover:text-gray-600">
      ← {{ project.title }}
    </a>
  </div>
  <div class="flex items-center justify-between mb-4">
    <h1 class="text-xl font-bold text-gray-900">월간 연구노트</h1>
    <a href="{% url 'note_create' project_pk=project.pk %}"
       hx-get="{% url 'note_create' project_pk=project.pk %}"
       hx-target="#main-content"
       hx-push-url="true"
       class="bg-blue-600 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-blue-700">
      + 노트 작성
    </a>
  </div>
  {% if notes %}
  <div class="space-y-2">
    {% for note in notes %}
    <a href="{% url 'note_detail' project_pk=project.pk pk=note.pk %}"
       hx-get="{% url 'note_detail' project_pk=project.pk pk=note.pk %}"
       hx-target="#main-content"
       hx-push-url="true"
       class="block bg-white rounded-lg border border-gray-200 p-4 hover:border-blue-300 transition">
      <div class="flex justify-between items-center">
        <div>
          <div class="font-semibold text-gray-900">{{ note.month|date:"Y년 m월" }}</div>
          <div class="text-sm text-gray-500">{{ note.researcher.name }}</div>
        </div>
        <span class="text-xs px-2 py-0.5 rounded-full
          {% if note.status == 'manager_approved' %}bg-green-100 text-green-700
          {% elif note.status == 'researcher_signed' %}bg-blue-100 text-blue-700
          {% else %}bg-gray-100 text-gray-600{% endif %}">
          {{ note.get_status_display }}
        </span>
      </div>
    </a>
    {% endfor %}
  </div>
  {% else %}
  <p class="text-gray-400 text-sm py-8 text-center">작성된 연구노트가 없습니다.</p>
  {% endif %}
</div>
```

- [ ] **Step 7: `templates/research/note_form.html` 작성**

```html
{% extends "common/base.html" %}
{% block title %}연구노트 {{ action }}{% endblock %}
{% block content %}{% include "research/partials/note_form_content.html" %}{% endblock %}
```

- [ ] **Step 8: `templates/research/partials/note_form_content.html` 작성**

```html
{% load widget_tweaks %}
<div class="p-4 lg:p-8 max-w-2xl">
  <div class="flex items-center gap-3 mb-6">
    <a href="{% url 'project_detail' project.pk %}"
       hx-get="{% url 'project_detail' project.pk %}"
       hx-target="#main-content"
       hx-push-url="true"
       class="text-gray-400 hover:text-gray-600">
      ← {{ project.title }}
    </a>
    <h1 class="text-xl font-bold text-gray-900">연구노트 {{ action }}</h1>
  </div>

  <form method="post"
        {% if note %}
        hx-post="{% url 'note_edit' project_pk=project.pk pk=note.pk %}"
        {% else %}
        hx-post="{% url 'note_create' project_pk=project.pk %}"
        {% endif %}
        hx-target="#main-content"
        hx-push-url="true"
        class="bg-white rounded-xl border border-gray-200 p-6 space-y-4">
    {% csrf_token %}

    {% for field in form %}
    <div>
      <label class="block text-sm font-medium text-gray-700 mb-1">{{ field.label }}</label>
      {{ field|add_class:"w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500" }}
      {% if field.errors %}
      <p class="text-red-500 text-xs mt-1">{{ field.errors.0 }}</p>
      {% endif %}
    </div>
    {% endfor %}

    <div class="flex gap-3 pt-2">
      <button type="submit"
              class="bg-blue-600 text-white px-6 py-2 rounded-lg text-sm font-medium hover:bg-blue-700">
        {{ action }}
      </button>
      <a href="{% url 'project_detail' project.pk %}"
         hx-get="{% url 'project_detail' project.pk %}"
         hx-target="#main-content"
         hx-push-url="true"
         class="bg-gray-100 text-gray-700 px-6 py-2 rounded-lg text-sm font-medium hover:bg-gray-200">
        취소
      </a>
    </div>
  </form>
</div>
```

- [ ] **Step 9: `templates/research/note_detail.html` 작성**

```html
{% extends "common/base.html" %}
{% block title %}{{ note.month|date:"Y년 m월" }} 연구노트{% endblock %}
{% block content %}{% include "research/partials/note_detail_content.html" %}{% endblock %}
```

- [ ] **Step 10: `templates/research/partials/note_detail_content.html` 작성**

```html
<div class="p-4 lg:p-8 max-w-2xl">
  <div class="flex items-center gap-3 mb-4">
    <a href="{% url 'project_detail' project.pk %}"
       hx-get="{% url 'project_detail' project.pk %}"
       hx-target="#main-content"
       hx-push-url="true"
       class="text-gray-400 hover:text-gray-600">
      ← {{ project.title }}
    </a>
  </div>

  <div class="bg-white rounded-xl border border-gray-200 p-6">
    <div class="flex items-center justify-between mb-4">
      <h1 class="text-xl font-bold text-gray-900">{{ note.month|date:"Y년 m월" }} 연구노트</h1>
      <span class="text-xs px-2.5 py-1 rounded-full font-medium
        {% if note.status == 'manager_approved' %}bg-green-100 text-green-700
        {% elif note.status == 'researcher_signed' %}bg-blue-100 text-blue-700
        {% else %}bg-gray-100 text-gray-600{% endif %}">
        {{ note.get_status_display }}
      </span>
    </div>

    <p class="text-sm text-gray-500 mb-4">연구원: {{ note.researcher.name }}</p>

    {% if note.activities %}
    <div class="mb-4">
      <h2 class="text-sm font-semibold text-gray-700 mb-1">수행 내용</h2>
      <p class="text-sm text-gray-900 whitespace-pre-wrap">{{ note.activities }}</p>
    </div>
    {% endif %}

    {% if note.challenges %}
    <div class="mb-4">
      <h2 class="text-sm font-semibold text-gray-700 mb-1">기술적 도전 및 해결</h2>
      <p class="text-sm text-gray-900 whitespace-pre-wrap">{{ note.challenges }}</p>
    </div>
    {% endif %}

    {% if note.results %}
    <div class="mb-4">
      <h2 class="text-sm font-semibold text-gray-700 mb-1">결과</h2>
      <p class="text-sm text-gray-900 whitespace-pre-wrap">{{ note.results }}</p>
    </div>
    {% endif %}

    <!-- 타임스탬프 체인 -->
    <div class="mt-4 pt-4 border-t border-gray-100 text-xs text-gray-400 space-y-1">
      {% if note.notified_at %}<p>① 생성: {{ note.notified_at|date:"Y-m-d H:i" }}</p>{% endif %}
      {% if note.researcher_signed_at %}<p>④ 연구원 서명: {{ note.researcher_signed_at|date:"Y-m-d H:i" }}</p>{% endif %}
      {% if note.manager_approved_at %}<p>⑤ 소장 승인: {{ note.manager_approved_at|date:"Y-m-d H:i" }}</p>{% endif %}
    </div>

    <!-- 액션 버튼 -->
    <div class="mt-6 flex gap-3">
      {% if note.status == 'draft' %}
      <a href="{% url 'note_edit' project_pk=project.pk pk=note.pk %}"
         hx-get="{% url 'note_edit' project_pk=project.pk pk=note.pk %}"
         hx-target="#main-content"
         hx-push-url="true"
         class="bg-gray-100 text-gray-700 px-4 py-2 rounded-lg text-sm font-medium hover:bg-gray-200">
        수정
      </a>
      <form method="post"
            hx-post="{% url 'note_sign' project_pk=project.pk pk=note.pk %}"
            hx-target="#main-content"
            hx-push-url="true">
        {% csrf_token %}
        <button type="submit"
                class="bg-blue-600 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-blue-700">
          연구원 서명
        </button>
      </form>
      {% elif note.status == 'researcher_signed' %}
      <form method="post"
            hx-post="{% url 'note_approve' project_pk=project.pk pk=note.pk %}"
            hx-target="#main-content"
            hx-push-url="true">
        {% csrf_token %}
        <button type="submit"
                class="bg-green-600 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-green-700">
          연구소장 승인
        </button>
      </form>
      {% endif %}
    </div>
  </div>
</div>
```

- [ ] **Step 11: 테스트 실행 — 통과 확인**

```bash
python -m pytest research/tests.py -v
```

Expected: 모든 테스트 PASSED.

- [ ] **Step 12: Commit**

```bash
git add research/ templates/research/
git commit -m "feat: add MonthlyNote CRUD views and templates"
```

---

## Task 4: Note 서명/승인 워크플로우

**Files:**
- Modify: `research/views.py` (note_sign, note_approve 추가)
- Modify: `research/urls.py` (sign, approve URL 추가)

- [ ] **Step 1: 워크플로우 테스트 작성**

`research/tests.py`에 추가:

```python
class TestNoteWorkflow:
    def test_sign_transitions_to_researcher_signed(self, logged_in_client, project, note):
        assert note.status == MonthlyNote.NoteStatus.DRAFT
        logged_in_client.post(
            reverse("note_sign", kwargs={"project_pk": project.pk, "pk": note.pk})
        )
        note.refresh_from_db()
        assert note.status == MonthlyNote.NoteStatus.RESEARCHER_SIGNED
        assert note.researcher_signed_at is not None

    def test_approve_requires_researcher_signed(self, logged_in_client, project, note):
        # draft 상태에서 approve → 상태 변경 없음
        logged_in_client.post(
            reverse("note_approve", kwargs={"project_pk": project.pk, "pk": note.pk})
        )
        note.refresh_from_db()
        assert note.status == MonthlyNote.NoteStatus.DRAFT

    def test_full_sign_then_approve(self, logged_in_client, project, note):
        logged_in_client.post(
            reverse("note_sign", kwargs={"project_pk": project.pk, "pk": note.pk})
        )
        logged_in_client.post(
            reverse("note_approve", kwargs={"project_pk": project.pk, "pk": note.pk})
        )
        note.refresh_from_db()
        assert note.status == MonthlyNote.NoteStatus.MANAGER_APPROVED
        assert note.manager_approved_at is not None

    def test_sign_only_accepts_post(self, logged_in_client, project, note):
        response = logged_in_client.get(
            reverse("note_sign", kwargs={"project_pk": project.pk, "pk": note.pk})
        )
        # GET은 note_detail로 redirect
        assert response.status_code == 302
        note.refresh_from_db()
        assert note.status == MonthlyNote.NoteStatus.DRAFT

    def test_approve_only_accepts_post(self, logged_in_client, project, note):
        note.status = MonthlyNote.NoteStatus.RESEARCHER_SIGNED
        note.save()
        response = logged_in_client.get(
            reverse("note_approve", kwargs={"project_pk": project.pk, "pk": note.pk})
        )
        assert response.status_code == 302
        note.refresh_from_db()
        assert note.status == MonthlyNote.NoteStatus.RESEARCHER_SIGNED
```

- [ ] **Step 2: 테스트 실행 — 실패 확인**

```bash
python -m pytest research/tests.py::TestNoteWorkflow -v
```

Expected: NoReverseMatch — FAIL. 정상.

- [ ] **Step 3: `research/views.py`에 note_sign, note_approve 추가**

```python
@login_required
def note_sign(request, project_pk, pk):
    if request.method != "POST":
        return redirect("note_detail", project_pk=project_pk, pk=pk)
    institutes = _accessible_institutes(request.user)
    project = get_object_or_404(Project, pk=project_pk, institute__in=institutes)
    note = get_object_or_404(MonthlyNote, pk=pk, project=project)
    if note.status == MonthlyNote.NoteStatus.DRAFT:
        note.status = MonthlyNote.NoteStatus.RESEARCHER_SIGNED
        note.researcher_signed_at = timezone.now()
        note.save(update_fields=["status", "researcher_signed_at"])
    return redirect("note_detail", project_pk=project.pk, pk=note.pk)


@login_required
def note_approve(request, project_pk, pk):
    if request.method != "POST":
        return redirect("note_detail", project_pk=project_pk, pk=pk)
    institutes = _accessible_institutes(request.user)
    project = get_object_or_404(Project, pk=project_pk, institute__in=institutes)
    note = get_object_or_404(MonthlyNote, pk=pk, project=project)
    if note.status == MonthlyNote.NoteStatus.RESEARCHER_SIGNED:
        note.status = MonthlyNote.NoteStatus.MANAGER_APPROVED
        note.manager_approved_at = timezone.now()
        note.save(update_fields=["status", "manager_approved_at"])
    return redirect("note_detail", project_pk=project.pk, pk=note.pk)
```

- [ ] **Step 4: `research/urls.py`에 sign, approve URL 추가**

```python
from django.urls import path

from . import views

urlpatterns = [
    path("", views.project_list, name="project_list"),
    path("new/", views.project_create, name="project_create"),
    path("<uuid:pk>/", views.project_detail, name="project_detail"),
    path("<uuid:pk>/edit/", views.project_edit, name="project_edit"),
    path("<uuid:project_pk>/notes/", views.note_list, name="note_list"),
    path("<uuid:project_pk>/notes/new/", views.note_create, name="note_create"),
    path("<uuid:project_pk>/notes/<uuid:pk>/", views.note_detail, name="note_detail"),
    path("<uuid:project_pk>/notes/<uuid:pk>/edit/", views.note_edit, name="note_edit"),
    path("<uuid:project_pk>/notes/<uuid:pk>/sign/", views.note_sign, name="note_sign"),
    path(
        "<uuid:project_pk>/notes/<uuid:pk>/approve/",
        views.note_approve,
        name="note_approve",
    ),
]
```

- [ ] **Step 5: 테스트 실행 — 전체 통과 확인**

```bash
python -m pytest research/tests.py -v
```

Expected: 모든 테스트 PASSED. (TestNoteWorkflow 5개 포함)

- [ ] **Step 6: Commit**

```bash
git add research/views.py research/urls.py
git commit -m "feat: add note sign/approve workflow with timestamp chain"
```

---

## Task 5: admin 등록 + 사이드바 연동

**Files:**
- Modify: `research/admin.py`
- Modify: `templates/common/nav_sidebar.html`

- [ ] **Step 1: `research/admin.py` 작성**

```python
from django.contrib import admin

from .models import MonthlyMilestone, MonthlyNote, Project


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ["title", "institute", "status", "period_start", "period_end"]
    list_filter = ["status", "institute__company"]
    search_fields = ["title"]


@admin.register(MonthlyMilestone)
class MonthlyMilestoneAdmin(admin.ModelAdmin):
    list_display = ["project", "month_number", "status"]
    list_filter = ["status"]


@admin.register(MonthlyNote)
class MonthlyNoteAdmin(admin.ModelAdmin):
    list_display = ["project", "month", "researcher", "status"]
    list_filter = ["status"]
    search_fields = ["project__title", "researcher__name"]
```

- [ ] **Step 2: `templates/common/nav_sidebar.html` 읽기 및 수정**

먼저 현재 내용 확인 후, 기존 링크 패턴을 참고하여 "과제" 링크 추가. 사이드바 기존 항목 목록 아래에 다음 블록 삽입:

```html
<a href="{% url 'project_list' %}"
   hx-get="{% url 'project_list' %}"
   hx-target="#main-content"
   hx-push-url="true"
   class="flex items-center gap-3 px-3 py-2 rounded-lg text-gray-700 hover:bg-gray-100 text-sm font-medium">
  <i class="fa-solid fa-flask-vial w-5 text-center text-gray-400"></i>
  연구과제
</a>
```

구체적인 삽입 위치는 `nav_sidebar.html`을 읽은 뒤 기존 항목(기업 목록 링크 등) 아래에 추가한다.

- [ ] **Step 3: Django admin 서버 접속 확인**

```bash
python manage.py runserver 0.0.0.0:8001
```

브라우저에서 `http://localhost:8001/admin/` → research 앱 모델이 보이는지 확인.

- [ ] **Step 4: 전체 테스트 최종 실행**

```bash
python -m pytest research/tests.py -v
```

Expected: 모든 테스트 PASSED.

- [ ] **Step 5: Commit**

```bash
git add research/admin.py templates/common/nav_sidebar.html
git commit -m "feat: register research models in admin and add nav link"
```

---

## Self-Review

**1. Spec coverage:**
- ✅ Project 모델 (CONTEXT.md 기준)
- ✅ MonthlyMilestone 모델 (CONTEXT.md 기준) — UI는 다음 Phase
- ✅ MonthlyNote 모델 (CONTEXT.md 기준)
- ✅ 타임스탬프 5단계 체인 (notified_at, researcher_signed_at, manager_approved_at)
- ✅ 상태 전환: draft → researcher_signed → manager_approved
- ✅ URL 구조 (CONTEXT.md 기준) — /projects/ 패턴 충족
- ✅ HTMX 패턴 (request.htmx 분기)
- ✅ 접근 제어 (사용자 소속 기업 연구소만 접근)
- ⬜ MonthlyMilestone CRUD UI — 다음 Phase
- ⬜ AI 문서 생성 — 다음 Phase
- ⬜ PDF 출력 — 다음 Phase

**2. Placeholder 없음:** 모든 코드 블록에 실제 구현 코드 포함 확인.

**3. 타입 일관성:**
- `_accessible_institutes()` — Task 2~4 모든 뷰에서 동일하게 사용
- `MonthlyNoteForm(project=project)` — Task 3 이후 모든 호출에 `project=` kwarg 사용
- `note_sign` / `note_approve` URL name — Task 4 urls.py와 note_detail 템플릿 일치
