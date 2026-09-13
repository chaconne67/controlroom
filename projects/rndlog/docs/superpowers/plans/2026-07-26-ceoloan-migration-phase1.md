# ceoloan 분리 이전 계획 — 1차 (서버 세팅 · 새 프로젝트 · 데이터 이전)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 새 서버에 `ceoloan` Django 프로젝트를 세우고, 수집 데이터를 옮겨 기업자금 화면이 실제 데이터로 뜨는 상태까지 만든다.

**Architecture:** rndlog에서 `funding`·`common` 앱만 가져온 새 프로젝트를 만든다. DB는 `ceo_loan` 하나만 쓰고 라우터를 없앤다. 수집 데이터(cretop 스키마 + leads)만 옮기고 대표이사·배분은 새 서버에서 동기화 명령으로 다시 만든다.

**Tech Stack:** Django 5.2, Python 3.13, PostgreSQL 16, Docker Compose, uv, Tailwind CSS, HTMX

**설계 문서:** [2026-07-26-ceoloan-server-split-design.md](../specs/2026-07-26-ceoloan-server-split-design.md)

**범위:** 설계 문서의 1·2·4단계. **3단계(구글 로그인)와 5·6단계(배포·전환)는 이 계획에 없다** — 구글 로그인은 OAuth 정보를 받아야 시작할 수 있고, 배포는 그 뒤에 온다.

이 계획이 끝나면: 새 서버에서 `runserver`로 기업자금 화면이 뜨고, 회사 7,899건이 보이며, 경영진단 결과서가 생성된다. 로그인은 `/admin/`으로 한다(정식 로그인 화면은 3단계).

## Global Constraints

- 새 프로젝트 위치: 로컬 `/home/work/ceoloan`, 서버 `/home/chaconne/ceoloan`
- 서버: `chaconne@49.247.205.170` (Ubuntu 24.04, 8코어, 7.8GB RAM, 42GB 여유, 무암호 sudo)
- 기존 서버: `chaconne@49.247.46.171` — DB 컨테이너 `rndnote-db-prod`, 접속 `10.7.0.18:5433`, DB `ceo_loan`, 사용자 `rndnote`
- **DB는 하나만 쓴다.** `DATABASES`에 `default` 하나뿐이고 이름은 `ceo_loan`. `FundingRouter`는 가져오지 않는다
- **`cretop` 스키마와 `public.leads`는 Django가 모델로 관리하지 않는다.** 수집 도구가 소유한다 — 마이그레이션으로 만들거나 지우지 않는다
- 앱 이름 `funding`을 바꾸지 않는다. 테이블 이름이 앱 이름에서 나오므로 바꾸면 옮겨온 DB를 전부 고쳐야 한다
- 한글 이름·상호 정렬은 `Collate("<컬럼>", "C")`를 쓴다 (DB 콜레이션이 `en_US.utf8`)
- 값이 없으면 비운다. 추정값이나 대체값을 만들어 넣지 않는다
- 비밀은 `.env`에만 둔다. git에 올리지 않는다
- 검증 명령: `uv run pytest`, `uv run ruff check`, `uv run python manage.py check`

---

## File Structure

새로 만드는 프로젝트의 구성이다.

| 경로 | 책임 |
|---|---|
| `main/settings/base.py` | 공통 설정. DB 1개, funding이 쓰는 설정만 |
| `main/settings/local.py` | 개발용 — DEBUG, 로컬 DB |
| `main/settings/deploy.py` | 배포용 — synco.kr, 보안 헤더 |
| `main/urls.py` | admin · accounts · funding |
| `accounts/models.py` | `User`(UUID PK, `role` 필드) — 로그인 화면은 3단계 |
| `accounts/services/membership.py` | 역할 부여 단일 진입점 |
| `common/mixins.py`, `common/auth.py` | UUID·timestamp mixin, 역할 가드 |
| `funding/**` | rndlog에서 그대로 가져온다 (모델·서비스·뷰·템플릿·테스트) |
| `templates/common/base.html` | 기본 레이아웃 — 로고 `ceoloan` |
| `templates/common/nav_sidebar.html` | 사이드바 — 기업자금 메뉴만 |
| `assets/경영진단.xlsx` | 결과서 양식 (git 비추적) |
| `docker-compose.yml` | db + web |
| `pyproject.toml` | 의존성 (rndlog의 절반) |

가져오지 않는 것: `marketing`, `checkup`, `companies`, 랜딩 페이지 2개, 상담신청, `FundingRouter`

---

## Phase A — 서버 기본 세팅

### Task 1: 서버 기본 패키지와 스왑

**Files:** 서버 설정만. 저장소 변경 없음

**Interfaces:**
- Produces: docker·docker compose가 동작하는 서버, 2GB 스왑

- [ ] **Step 1: 현재 상태 확인**

Run:
```bash
ssh chaconne@49.247.205.170 'free -h; df -h /; command -v docker || echo "docker 없음"'
```
Expected: 스왑 0B, docker 없음

- [ ] **Step 2: 스왑 2GB 생성**

Run:
```bash
ssh chaconne@49.247.205.170 'sudo fallocate -l 2G /swapfile && sudo chmod 600 /swapfile && sudo mkswap /swapfile && sudo swapon /swapfile && echo "/swapfile none swap sw 0 0" | sudo tee -a /etc/fstab && free -h'
```
Expected: `Swap: 2.0Gi` 표시

- [ ] **Step 3: docker 설치**

Run:
```bash
ssh chaconne@49.247.205.170 'curl -fsSL https://get.docker.com | sudo sh && sudo usermod -aG docker chaconne'
```
Expected: 설치 완료

- [ ] **Step 4: docker 권한 적용 확인**

Run:
```bash
ssh chaconne@49.247.205.170 'docker ps'
```
Expected: 빈 목록이 출력된다(권한 오류가 아니라). 권한 오류가 나면 SSH를 다시 붙어야 그룹이 적용된다 — 새 세션으로 재시도한다.

- [ ] **Step 5: uv 설치**

Run:
```bash
ssh chaconne@49.247.205.170 'curl -LsSf https://astral.sh/uv/install.sh | sh && ~/.local/bin/uv --version'
```
Expected: 버전 출력

- [ ] **Step 6: 확인 기록**

Run:
```bash
ssh chaconne@49.247.205.170 'free -h | head -3; docker --version; docker compose version; ~/.local/bin/uv --version'
```
Expected: 스왑 2GB, docker·compose·uv 버전이 모두 출력된다

---

### Task 2: 방화벽

**Files:** 서버 설정만

**Interfaces:**
- Consumes: Task 1의 docker
- Produces: 22·80·443만 열린 서버. 5433은 기존 서버 IP에만 열린다

DB 포트를 전체 공개하면 1.9GB 회사 데이터가 인터넷에 노출된다. 출발지를 기존 서버로 못박는다.

- [ ] **Step 1: ufw 규칙 추가 (아직 켜지 않는다)**

Run:
```bash
ssh chaconne@49.247.205.170 'sudo ufw allow 22/tcp && sudo ufw allow 80/tcp && sudo ufw allow 443/tcp && sudo ufw allow from 49.247.46.171 to any port 5433 proto tcp && sudo ufw status numbered'
```
Expected: 규칙 4개가 목록에 보인다. **22번이 반드시 있어야 한다** — 없이 켜면 SSH가 끊긴다

- [ ] **Step 2: 22번 규칙을 눈으로 확인한 뒤 방화벽 켜기**

Run:
```bash
ssh chaconne@49.247.205.170 'sudo ufw status numbered | grep -q "22/tcp" && sudo ufw --force enable && sudo ufw status verbose'
```
Expected: `Status: active`

- [ ] **Step 3: SSH가 여전히 되는지 새 연결로 확인**

Run:
```bash
ssh -o ConnectTimeout=10 chaconne@49.247.205.170 'echo SSH 정상'
```
Expected: `SSH 정상`

- [ ] **Step 4: docker가 ufw를 우회하는 문제 확인**

docker는 iptables를 직접 만져 ufw 규칙을 건너뛴다. 포트 매핑을 `127.0.0.1`에 묶어 외부 노출을 막는 방식으로 대응한다(Task 8에서 적용).

Run:
```bash
ssh chaconne@49.247.205.170 'sudo iptables -L DOCKER-USER -n 2>/dev/null | head -5 || echo "DOCKER-USER 체인 없음(컨테이너 미기동)"'
```
Expected: 체인이 없거나 비어 있다. 이 사실을 Task 8에서 쓴다

---

## Phase B — 새 프로젝트

### Task 3: 프로젝트 골격

**Files:**
- Create: `/home/work/ceoloan/` 전체 골격

**Interfaces:**
- Produces: `manage.py check`가 통과하는 빈 Django 프로젝트

- [ ] **Step 1: 디렉터리와 git 저장소 만들기**

Run:
```bash
mkdir -p /home/work/ceoloan && cd /home/work/ceoloan && git init && git branch -M main
```

- [ ] **Step 2: pyproject.toml 작성**

Create `/home/work/ceoloan/pyproject.toml`:

```toml
[project]
name = "ceoloan"
version = "0.1.0"
description = "기업자금 TM · 상담 관리"
readme = "README.md"
requires-python = ">=3.13"
dependencies = [
    "django>=5.2,<6",
    "django-htmx>=1.27.0",
    "django-widget-tweaks>=1.5.0",
    "psycopg[binary]>=3.3.3",
    "python-dotenv>=1.1.0",
    "gunicorn>=23.0.0",
    "whitenoise>=6.9.0",
    "openpyxl>=3.1.5",
    "qrcode>=8.2",
    "google-genai>=1.0.0",
]

[project.optional-dependencies]
dev = [
    "ruff>=0.11.0",
    "pytest>=8.0.0",
    "pytest-django>=4.9.0",
]

[tool.ruff]
exclude = [".venv/"]

[tool.ruff.lint]
ignore = ["E402"]

[tool.ruff.lint.per-file-ignores]
"main/settings/*.py" = ["F403", "F405"]

[tool.pytest.ini_options]
DJANGO_SETTINGS_MODULE = "main.settings.local"
pythonpath = ["."]
```

rndlog의 21개 의존성 중 10개만 남겼다. 뺀 것: `weasyprint`·`cairosvg`(PDF), `gspread`·`google-auth`(스프레드시트), `python-docx`·`xlrd`·`xlwt`·`xlutils`(문서), `python-telegram-bot`(알림), `openai`·`httpx`(마케팅 LLM) — `funding`은 쓰지 않는다.

- [ ] **Step 3: .gitignore 작성**

Create `/home/work/ceoloan/.gitignore`:

```
.venv/
__pycache__/
*.pyc
.env
/assets/
/media/
/staticfiles/
node_modules/
logs/
.vscode/
```

- [ ] **Step 4: 의존성 설치**

Run:
```bash
cd /home/work/ceoloan && uv sync --extra dev
```
Expected: `.venv` 생성, 설치 완료

- [ ] **Step 5: Django 프로젝트 골격 생성**

Run:
```bash
cd /home/work/ceoloan && uv run django-admin startproject main . && mkdir -p main/settings && git mv main/settings.py main/settings/base.py 2>/dev/null || mv main/settings.py main/settings/base.py && touch main/settings/__init__.py
```
Expected: `main/settings/base.py` 생성

- [ ] **Step 6: manage.py 기본 설정 바꾸기**

`manage.py`의 `DJANGO_SETTINGS_MODULE` 기본값을 바꾼다:

```python
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "main.settings.local")
```

- [ ] **Step 7: 커밋**

```bash
cd /home/work/ceoloan && git add -A && git commit -m "chore: 프로젝트 골격"
```

---

### Task 4: 설정 파일

**Files:**
- Modify: `main/settings/base.py`
- Create: `main/settings/local.py`, `main/settings/deploy.py`, `.env.example`

**Interfaces:**
- Produces: `postgres_database(host, port)` — DB 1개짜리 dict를 돌려준다
- Produces: 설정 키 `GEMINI_API_KEY`, `LLM_MODEL`, `FUNDING_NARRATIVE_MODEL`, `FUNDING_SUMMARY_MODEL`, `FUNDING_TRANSCRIBE_MODEL`, `FUNDING_AUDIO_MAX_TOTAL_BYTES`, `DEFAULT_FROM_EMAIL`

`funding`·`common`이 실제로 읽는 설정은 위 7개뿐이다(`settings.` 참조 전수 조사 결과).

- [ ] **Step 1: base.py 작성**

Create `/home/work/ceoloan/main/settings/base.py` (전체를 이 내용으로 바꾼다):

```python
import os
import sys
from pathlib import Path

from django.core.exceptions import ImproperlyConfigured
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent.parent
load_dotenv(BASE_DIR / ".env")

RUNNING_TESTS = any("pytest" in arg or arg == "test" for arg in sys.argv)
RUNNING_COLLECTSTATIC = "collectstatic" in sys.argv

DEV_SECRET_KEY="<generate-for-development>"
SECRET_KEY = os.environ.get("SECRET_KEY", DEV_SECRET_KEY)
DEBUG = False

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.humanize",
    # Third-party
    "django_htmx",
    "widget_tweaks",
    # Local
    "accounts",
    "funding",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "django_htmx.middleware.HtmxMiddleware",
]

ROOT_URLCONF = "main.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "main.wsgi.application"


# Database — ceo_loan 하나만 쓴다.
# rndlog는 계정(rndnote)과 기업자금(ceo_loan)이 갈려 있어 교차 FK를 못 걸었다.
# 여기서는 하나라 라우터가 필요 없다.

DATABASE_ENGINE = "django.db.backends.postgresql"
DATABASE_NAME = os.environ.get("POSTGRES_DB", "ceo_loan")
DATABASE_USER = os.environ.get("POSTGRES_USER", "ceoloan")
DATABASE_PASSWORD = os.environ.get("POSTGRES_PASSWORD", "")
DATABASE_CONN_MAX_AGE = 600


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


# Auth

AUTH_USER_MODEL = "accounts.User"
LOGIN_URL = "/admin/login/"  # 3단계에서 구글 로그인 화면으로 바꾼다
LOGIN_REDIRECT_URL = "/funding/"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

CSRF_COOKIE_HTTPONLY = True
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")


# i18n

LANGUAGE_CODE = "ko-kr"
TIME_ZONE = "Asia/Seoul"
USE_TZ = True


# Static / media

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "static"]
MEDIA_URL = "media/"
MEDIA_ROOT = BASE_DIR / "media"

STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"
    },
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"


# Email — 영업자 전달 메일 발신

EMAIL_BACKEND = os.environ.get(
    "EMAIL_BACKEND", "django.core.mail.backends.smtp.EmailBackend"
)
EMAIL_HOST = os.environ.get("EMAIL_HOST", "localhost")
EMAIL_PORT = int(os.environ.get("EMAIL_PORT", "25"))
EMAIL_TIMEOUT = int(os.environ.get("EMAIL_TIMEOUT", "10"))
EMAIL_HOST_USER = os.environ.get("EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = os.environ.get("EMAIL_HOST_PASSWORD", "")
EMAIL_USE_TLS = os.environ.get("EMAIL_USE_TLS", "false").lower() in ("1", "true", "yes")
EMAIL_USE_SSL = os.environ.get("EMAIL_USE_SSL", "false").lower() in ("1", "true", "yes")
DEFAULT_FROM_EMAIL = os.environ.get(
    "DEFAULT_FROM_EMAIL", EMAIL_HOST_USER or "webmaster@localhost"
)
SERVER_EMAIL = DEFAULT_FROM_EMAIL


# LLM — 통화 녹음 전사·요약, 경영진단 문구 생성

# 값은 rndlog의 현재 기본값과 같다(2026-07-26 확인). 모델 이름이 틀리면
# 녹음 요약과 경영진단 문구 생성이 실패한다.
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
LLM_PROVIDER = os.environ.get("LLM_PROVIDER", "gemini")
LLM_MODEL = os.environ.get("LLM_MODEL", "gemini-3.5-flash")
FUNDING_TRANSCRIBE_MODEL = os.environ.get(
    "FUNDING_TRANSCRIBE_MODEL", "gemini-3.1-flash-lite"
)
FUNDING_SUMMARY_MODEL = os.environ.get("FUNDING_SUMMARY_MODEL", "gemini-3.5-flash")
FUNDING_NARRATIVE_MODEL = os.environ.get("FUNDING_NARRATIVE_MODEL", "gemini-3.5-flash")
# 녹음 원본 총량 상한(10GB). 넘으면 오래된 것부터 지운다 — 전사·요약은 남는다
FUNDING_AUDIO_MAX_TOTAL_BYTES = int(
    os.environ.get("FUNDING_AUDIO_MAX_TOTAL_BYTES", 10 * 1024**3)
)
```

- [ ] **Step 2: local.py 작성**

Create `/home/work/ceoloan/main/settings/local.py`:

```python
from .base import *

DEBUG = True
ALLOWED_HOSTS = ["*"]
CSRF_TRUSTED_ORIGINS = ["http://localhost:8000", "http://127.0.0.1:8000"]
SITE_URL = "http://localhost:8000"

DATABASES = postgres_database(
    os.environ.get("DATABASE_HOST", "127.0.0.1"),
    os.environ.get("DATABASE_PORT", "5433"),
)

SECURE_SSL_REDIRECT = False
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False
```

- [ ] **Step 3: deploy.py 작성**

Create `/home/work/ceoloan/main/settings/deploy.py`:

```python
from django.core.exceptions import ImproperlyConfigured

from .base import *

DEBUG = False

ALLOWED_HOSTS = ["synco.kr", "www.synco.kr"]
CSRF_TRUSTED_ORIGINS = ["https://synco.kr", "https://www.synco.kr"]
SITE_URL = "https://synco.kr"

DATABASES = postgres_database(
    os.environ.get("DATABASE_HOST", "db"),
    os.environ.get("DATABASE_PORT", "5432"),
)

if SECRET_KEY == DEV_SECRET_KEY and not (RUNNING_TESTS or RUNNING_COLLECTSTATIC):
    raise ImproperlyConfigured("SECRET_KEY environment variable is required")

SECURE_SSL_REDIRECT = False if RUNNING_TESTS else True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
```

- [ ] **Step 4: .env.example 작성**

Create `/home/work/ceoloan/.env.example`:

```
SECRET_KEY=
POSTGRES_DB=ceo_loan
POSTGRES_USER=ceoloan
POSTGRES_PASSWORD=
DATABASE_HOST=127.0.0.1
DATABASE_PORT=5433

GEMINI_API_KEY=

EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=true
EMAIL_HOST_USER=
EMAIL_HOST_PASSWORD=
DEFAULT_FROM_EMAIL=
```

- [ ] **Step 5: 커밋**

```bash
cd /home/work/ceoloan && git add -A && git commit -m "chore: 설정 파일 (DB 1개, funding이 쓰는 설정만)"
```

---

### Task 5: accounts 앱 — 사용자와 역할

**Files:**
- Create: `accounts/models.py`, `accounts/admin.py`, `accounts/apps.py`, `accounts/services/membership.py`, `accounts/test_membership.py`

**Interfaces:**
- Produces: `accounts.models.User` (UUID PK, `role` 필드, `db_table="users"`)
- Produces: `User.Role` — `PENDING`/`ADMIN`/`TM`/`SALES`
- Produces: `accounts.services.membership.approve(user, role)`, `reject(user)`, `sync_agent(user, role)`, `STAFF_ROLES`

로그인 화면은 3단계에서 만든다. 지금은 `/admin/`으로 로그인해 화면을 확인한다.

- [ ] **Step 1: 앱 생성**

Run:
```bash
cd /home/work/ceoloan && uv run python manage.py startapp accounts && mkdir -p accounts/services && touch accounts/services/__init__.py
```

- [ ] **Step 2: 실패하는 테스트 작성**

Create `/home/work/ceoloan/accounts/test_membership.py`:

```python
"""역할 부여 규칙 테스트.

예방 장애: 역할과 is_staff가 어긋나 승인된 TM이 배분 대상에서 빠지는 것.
"""

import pytest
from django.contrib.auth import get_user_model

from accounts.services import membership
from funding.models import Agent

Role = get_user_model().Role


@pytest.mark.django_db
def test_new_user_starts_pending():
    user = get_user_model().objects.create_user(username="u1", password="pw")
    assert user.role == Role.PENDING
    assert user.is_staff is False


@pytest.mark.django_db
def test_admin_gets_staff_flag():
    user = get_user_model().objects.create_user(username="a", password="pw")
    membership.approve(user, Role.ADMIN)
    user.refresh_from_db()
    assert user.role == Role.ADMIN
    assert user.is_staff is True


@pytest.mark.django_db
def test_sales_does_not_get_staff_flag():
    """영업담당자에게 admin 접근권을 주지 않는다."""
    user = get_user_model().objects.create_user(username="s", password="pw")
    membership.approve(user, Role.SALES)
    user.refresh_from_db()
    assert user.is_staff is False


@pytest.mark.django_db
def test_tm_approval_creates_active_agent():
    """TM으로 승인하면 배분 대상이 되어야 한다."""
    user = get_user_model().objects.create_user(
        username="t", password="pw", first_name="김", last_name="티엠"
    )
    membership.approve(user, Role.TM)
    agent = Agent.objects.get(username="t")
    assert agent.is_active is True
    assert agent.display_name


@pytest.mark.django_db
def test_role_change_away_from_tm_deactivates_agent_without_deleting():
    """Assignment.agent가 PROTECT라 레코드를 지우면 안 된다 — 비활성만 한다."""
    user = get_user_model().objects.create_user(username="t2", password="pw")
    membership.approve(user, Role.TM)
    membership.approve(user, Role.SALES)
    assert Agent.objects.get(username="t2").is_active is False


@pytest.mark.django_db
def test_reject_clears_role_and_deactivates():
    user = get_user_model().objects.create_user(username="r", password="pw")
    membership.approve(user, Role.TM)
    membership.reject(user)
    user.refresh_from_db()
    assert user.role == Role.PENDING
    assert user.is_active is False
    assert Agent.objects.get(username="r").is_active is False
```

- [ ] **Step 3: User 모델 작성**

Create `/home/work/ceoloan/accounts/models.py`:

```python
import uuid

from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    class Role(models.TextChoices):
        PENDING = "pending", "승인대기"
        ADMIN = "admin", "관리자"
        TM = "tm", "TM담당자"
        SALES = "sales", "영업담당자"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    phone = models.CharField(max_length=20, blank=True)
    # 역할의 정본. 화면 가드는 이 값만 본다.
    # is_staff는 Django admin 접근 플래그로만 남는다 — 둘을 같이 세팅하는 곳은
    # accounts.services.membership.approve 하나뿐이다.
    role = models.CharField(
        max_length=10, choices=Role.choices, default=Role.PENDING, db_index=True
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "users"
```

- [ ] **Step 4: 역할 부여 서비스 작성**

Create `/home/work/ceoloan/accounts/services/membership.py`:

```python
"""역할 부여의 단일 진입점.

역할(User.role)과 is_staff, 배분 대상 여부(funding.Agent)는 항상 같이
움직여야 한다. 세 곳을 각자 세팅하면 어긋난 계정이 생긴다.
"""

from django.contrib.auth import get_user_model

User = get_user_model()

# Django admin 접근권을 함께 받는 역할. 영업담당자는 제외한다.
STAFF_ROLES = frozenset({User.Role.ADMIN, User.Role.TM})


def approve(user, role) -> None:
    """역할을 준다. 승인과 역할 변경이 같은 경로다."""
    user.role = role
    user.is_staff = role in STAFF_ROLES
    user.is_active = True
    user.save(update_fields=["role", "is_staff", "is_active", "updated_at"])
    sync_agent(user, role)


def reject(user) -> None:
    """가입을 거절한다. 계정은 지우지 않고 잠근다 — 기록이 남아야 한다."""
    user.role = User.Role.PENDING
    user.is_staff = False
    user.is_active = False
    user.save(update_fields=["role", "is_staff", "is_active", "updated_at"])
    sync_agent(user, User.Role.PENDING)


def sync_agent(user, role) -> None:
    """TM 배분 대상 여부를 역할에 맞춘다.

    역할이 TM이 아니게 되어도 레코드는 지우지 않는다. Assignment.agent가
    PROTECT라 과거 배분 이력이 물려 있다.
    """
    from funding.models import Agent

    if role == User.Role.TM:
        Agent.objects.update_or_create(
            username=user.username,
            defaults={
                "display_name": user.get_full_name() or user.username,
                "is_active": True,
            },
        )
        return
    Agent.objects.filter(username=user.username).update(is_active=False)
```

- [ ] **Step 5: admin 등록**

Create `/home/work/ceoloan/accounts/admin.py`:

```python
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from accounts.models import User


@admin.register(User)
class CeoLoanUserAdmin(UserAdmin):
    list_display = ("username", "email", "role", "is_staff", "is_active")
    list_filter = ("role", "is_staff", "is_active")
    fieldsets = UserAdmin.fieldsets + (("기업자금", {"fields": ("role", "phone")}),)
```

- [ ] **Step 6: 테스트는 Task 6 이후에 통과한다**

이 테스트는 `funding.models.Agent`를 쓴다. Task 6에서 funding을 가져온 뒤 실행한다.

Run:
```bash
cd /home/work/ceoloan && uv run python manage.py check
```
Expected: `funding` 앱이 없어 실패한다 — 정상이다. Task 6에서 해결된다

- [ ] **Step 7: 커밋**

```bash
cd /home/work/ceoloan && git add -A && git commit -m "feat(accounts): 사용자·역할과 역할 부여 서비스"
```

---

### Task 6: funding·common 이식

**Files:**
- Copy: `funding/**`, `common/**` from `/home/work/rndnote`
- Modify: 가져온 파일에서 rndlog 전용 부분 제거

**Interfaces:**
- Consumes: `accounts.models.User.Role` (Task 5)
- Produces: `funding` 앱 전체 — 모델·서비스·뷰·템플릿·마이그레이션·테스트

- [ ] **Step 1: 앱 복사**

Run:
```bash
cd /home/work/ceoloan && cp -r /home/work/rndnote/funding . && cp -r /home/work/rndnote/common . && rm -rf funding/__pycache__ funding/*/__pycache__ common/__pycache__ && ls funding/ common/
```
Expected: `funding/`(models·views·services·templates·migrations·test), `common/`(auth.py·mixins.py)

- [ ] **Step 2: 라우터 참조가 없는지 확인**

Run:
```bash
cd /home/work/ceoloan && grep -rn "ceo_loan\|FundingRouter\|databases=" funding/ common/ --include=*.py | grep -v migrations
```
Expected: `services/handoff.py`의 `transaction.atomic(using="ceo_loan")`과 테스트의 `databases=["default","ceo_loan"]`가 나온다. 다음 단계에서 고친다

- [ ] **Step 3: DB alias 참조 제거**

DB가 하나뿐이라 alias를 명시할 이유가 없다.

Run:
```bash
cd /home/work/ceoloan && python3 - <<'PY'
import pathlib, re
for p in pathlib.Path("funding").rglob("*.py"):
    s = p.read_text(encoding="utf-8")
    o = s
    s = s.replace('transaction.atomic(using="ceo_loan")', "transaction.atomic()")
    s = s.replace('pytest.mark.django_db(databases=["default", "ceo_loan"])', "pytest.mark.django_db")
    s = s.replace('@pytest.mark.django_db(databases=["default", "ceo_loan"])', "@pytest.mark.django_db")
    if s != o:
        p.write_text(s, encoding="utf-8")
        print("고침:", p)
PY
```
Expected: `services/handoff.py`, `test_*.py` 몇 개가 고쳐진다

- [ ] **Step 4: 남은 참조 확인**

Run:
```bash
cd /home/work/ceoloan && grep -rn "ceo_loan" funding/ common/ --include=*.py | grep -v migrations
```
Expected: 결과 없음. 남아 있으면 손으로 고친다

- [ ] **Step 5: 마이그레이션의 allow_migrate 제약 확인**

Run:
```bash
cd /home/work/ceoloan && ls funding/migrations/ && grep -rn "database\|using" funding/migrations/*.py | head
```
Expected: 마이그레이션 파일에 DB alias가 없다(라우터가 처리했으므로). 있으면 지운다

- [ ] **Step 6: 커밋**

```bash
cd /home/work/ceoloan && git add -A && git commit -m "feat(funding): rndlog에서 기업자금·공용 앱을 가져온다"
```

---

### Task 7: URL·템플릿·정적 파일

**Files:**
- Modify: `main/urls.py`
- Create: `templates/common/base.html`, `templates/common/nav_sidebar.html`
- Copy: `static/`, `tailwind.config.js`, `wds-tokens.json`, `package.json`

**Interfaces:**
- Consumes: `funding.urls` (Task 6)
- Produces: `/funding/` 이하 화면이 뜨는 상태

- [ ] **Step 1: main/urls.py 작성**

Create `/home/work/ceoloan/main/urls.py` (전체 교체):

```python
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from django.views.generic import RedirectView

urlpatterns = [
    path("admin/", admin.site.urls),
    # 첫 화면은 3단계에서 로그인 화면이 된다. 지금은 기업자금으로 보낸다.
    path("", RedirectView.as_view(url="/funding/", permanent=False), name="home"),
    path("funding/", include("funding.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
```

- [ ] **Step 2: 정적 자산 복사**

Run:
```bash
cd /home/work/ceoloan && cp -r /home/work/rndnote/static . && cp /home/work/rndnote/tailwind.config.js /home/work/rndnote/wds-tokens.json /home/work/rndnote/package.json . && rm -rf static/email_assets && ls static/
```
Expected: `css/`, `img/`. 마케팅 이메일 자산은 뺀다

- [ ] **Step 3: tailwind.config.js의 대상 경로 정리**

`tailwind.config.js`의 `content` 배열에서 없는 앱을 지운다:

```javascript
  content: [
    './templates/**/*.html',
    './accounts/templates/**/*.html',
    './funding/templates/**/*.html',
  ],
```

- [ ] **Step 4: base.html 가져와 로고 바꾸기**

Run:
```bash
cd /home/work/ceoloan && mkdir -p templates/common && cp /home/work/rndnote/templates/common/base.html templates/common/
```

`templates/common/base.html`에서 두 곳을 바꾼다:
- `<title>{% block title %}rndlog{% endblock %}</title>` → `<title>{% block title %}ceoloan{% endblock %}</title>`

- [ ] **Step 5: 사이드바 새로 작성**

Create `/home/work/ceoloan/templates/common/nav_sidebar.html`:

```html
<div class="mb-8">
  <a href="/" class="text-xl font-extrabold tracking-tight text-ink">ceo<span class="text-accent">loan</span></a>
  <p class="text-xs text-ink-faint mt-1">기업자금 상담 관리</p>
</div>

<div class="flex flex-col gap-1 flex-1">
  {% if request.user.role == 'admin' or request.user.role == 'tm' %}
  <a href="{% url 'funding:workspace' %}"
     hx-get="{% url 'funding:workspace' %}" hx-target="#main-content" hx-swap="outerHTML" hx-select="#main-content" hx-push-url="true"
     class="flex items-center gap-3 px-3 py-2.5 rounded-lg text-[15px] text-ink-mid hover:bg-accent-soft hover:text-ink transition-colors">
    <i class="fa-solid fa-coins w-5 text-center"></i>
    기업 자금
  </a>
  {% endif %}
  {% if request.user.role == 'admin' %}
  <a href="{% url 'funding:admin_list' %}"
     hx-get="{% url 'funding:admin_list' %}" hx-target="#main-content" hx-swap="outerHTML" hx-select="#main-content" hx-push-url="true"
     class="flex items-center gap-3 px-3 py-2.5 rounded-lg text-[15px] text-ink-mid hover:bg-accent-soft hover:text-ink transition-colors">
    <i class="fa-solid fa-clipboard-list w-5 text-center"></i>
    기업자금 관리
  </a>
  {% endif %}
  {% if request.user.role == 'sales' or request.user.role == 'admin' %}
  <a href="{% url 'funding:handoff_inbox' %}"
     hx-get="{% url 'funding:handoff_inbox' %}" hx-target="#main-content" hx-swap="outerHTML" hx-select="#main-content" hx-push-url="true"
     class="flex items-center gap-3 px-3 py-2.5 rounded-lg text-[15px] text-ink-mid hover:bg-accent-soft hover:text-ink transition-colors">
    <i class="fa-solid fa-inbox w-5 text-center"></i>
    {% if request.user.role == 'admin' %}전달 내역{% else %}전달함{% endif %}
  </a>
  {% endif %}
  {% if request.user.is_superuser %}
  <a href="{% url 'admin:index' %}" target="_blank" rel="noopener"
     class="mt-auto flex items-center gap-3 px-3 py-2.5 rounded-lg text-[15px] text-ink-mid hover:bg-accent-soft hover:text-ink transition-colors">
    <i class="fa-solid fa-gear w-5 text-center"></i>
    Settings
  </a>
  {% endif %}
</div>

<div class="mt-auto pt-6 border-t border-line">
  <div class="flex items-center gap-3 px-3 py-2">
    <div class="w-8 h-8 rounded-full bg-accent-soft flex items-center justify-center">
      <i class="fa-solid fa-user text-accent text-sm"></i>
    </div>
    <div class="flex-1 min-w-0">
      <p class="text-sm font-medium text-ink truncate">{{ request.user.get_full_name|default:request.user.username }}</p>
    </div>
  </div>
  <a href="/admin/logout/"
     class="flex items-center gap-3 px-3 py-2 rounded-lg text-sm text-ink-soft hover:bg-accent-soft hover:text-ink transition-colors mt-1">
    <i class="fa-solid fa-right-from-bracket w-5 text-center"></i>
    로그아웃
  </a>
</div>
```

로그아웃 주소는 3단계에서 정식 로그아웃으로 바꾼다.

- [ ] **Step 6: funding 레이아웃의 브레드크럼 고치기**

`funding/templates/funding/_layout.html`의 브레드크럼이 「마케팅 · 기업 자금」으로 되어 있다. 「기업 자금」만 남긴다:

```html
  <nav class="mb-4 flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-ink-faint">
    <span class="text-ink-mid">기업 자금</span>
    {% block breadcrumb %}{% endblock %}
  </nav>
```

- [ ] **Step 7: Tailwind 빌드**

Run:
```bash
cd /home/work/ceoloan && npm install && npx tailwindcss -i static/css/input.css -o static/css/output.css --minify && ls -la static/css/
```
Expected: `output.css` 생성 (rndlog도 `input.css` → `output.css`를 쓴다, 2026-07-26 확인)

- [ ] **Step 8: 커밋**

```bash
cd /home/work/ceoloan && git add -A && git commit -m "feat: URL·템플릿·정적 자산 (로고 ceoloan)"
```

---

## Phase C — DB와 검증

### Task 8: 로컬 PostgreSQL 기동

**Files:**
- Create: `docker-compose.yml`, `.env`

**Interfaces:**
- Produces: `127.0.0.1:5433`에 뜬 PostgreSQL 16, DB `ceo_loan`, 사용자 `ceoloan`

- [ ] **Step 1: docker-compose.yml 작성**

Create `/home/work/ceoloan/docker-compose.yml`:

```yaml
services:
  db:
    image: postgres:16
    container_name: ceoloan-db
    restart: always
    environment:
      POSTGRES_DB: ${POSTGRES_DB:-ceo_loan}
      POSTGRES_USER: ${POSTGRES_USER:-ceoloan}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:?POSTGRES_PASSWORD is required}
      # 한글 정렬은 코드에서 Collate("C")로 처리한다. 초기화 로케일은 기본값.
    volumes:
      - pgdata:/var/lib/postgresql/data
    ports:
      # 외부 노출은 방화벽이 아니라 바인드 주소로 막는다 — docker가 ufw를 우회한다.
      - "127.0.0.1:5433:5432"
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER:-ceoloan}"]
      interval: 5s
      timeout: 3s
      retries: 5

volumes:
  pgdata:
```

`web`·`nginx` 서비스는 5단계(배포)에서 더한다.

- [ ] **Step 2: .env 만들기**

Run:
```bash
cd /home/work/ceoloan && cp .env.example .env && python3 -c "
import secrets, pathlib
p = pathlib.Path('.env'); s = p.read_text()
s = s.replace('SECRET_KEY=', 'SECRET_KEY=' + secrets.token_urlsafe(50))
s = s.replace('POSTGRES_PASSWORD=', 'POSTGRES_PASSWORD=' + secrets.token_urlsafe(24))
p.write_text(s); print('SECRET_KEY·POSTGRES_PASSWORD 생성됨')
"
```

`GEMINI_API_KEY`와 메일 설정은 rndlog의 `.env`에서 가져와 채운다:
```bash
grep -E "^(GEMINI_API_KEY|EMAIL_|DEFAULT_FROM_EMAIL)" /home/work/rndnote/.env
```

- [ ] **Step 3: DB 기동**

Run:
```bash
cd /home/work/ceoloan && docker compose up -d db && sleep 8 && docker compose ps
```
Expected: `ceoloan-db`가 healthy

- [ ] **Step 4: 접속 확인**

Run:
```bash
cd /home/work/ceoloan && docker compose exec db psql -U ceoloan -d ceo_loan -c "select version();"
```
Expected: PostgreSQL 16 버전 문자열

- [ ] **Step 5: 커밋**

```bash
cd /home/work/ceoloan && git add docker-compose.yml && git commit -m "chore: 로컬 PostgreSQL"
```

---

### Task 9: 마이그레이션과 테스트 통과

**Files:**
- Create: `accounts/migrations/0001_initial.py` (자동 생성)

**Interfaces:**
- Consumes: Task 5~8 전부
- Produces: 테이블이 만들어지고 테스트가 통과하는 상태

- [ ] **Step 1: 설정 점검**

Run:
```bash
cd /home/work/ceoloan && uv run python manage.py check
```
Expected: `System check identified no issues`. 실패하면 메시지대로 고친다 — 대개 import 경로나 빠진 설정이다

- [ ] **Step 2: 마이그레이션 생성**

Run:
```bash
cd /home/work/ceoloan && uv run python manage.py makemigrations accounts
```
Expected: `accounts/migrations/0001_initial.py` 생성

- [ ] **Step 3: 마이그레이션 적용**

Run:
```bash
cd /home/work/ceoloan && uv run python manage.py migrate
```
Expected: accounts·funding·Django 기본 앱이 모두 적용된다

- [ ] **Step 4: 테스트 실행**

Run:
```bash
cd /home/work/ceoloan && uv run pytest -q
```
Expected: 통과. 실패하면 원인별로 대응한다
- `cretop` 스키마를 읽는 테스트: 그 테스트는 이미 monkeypatch로 막혀 있어야 한다. 안 막혀 있으면 막는다
- `marketing` import: 가져오지 않은 앱을 참조하는 테스트가 있으면 그 테스트를 지운다

- [ ] **Step 5: 린트**

Run:
```bash
cd /home/work/ceoloan && uv run ruff check
```
Expected: 통과

- [ ] **Step 6: 슈퍼유저 만들고 화면 확인**

Run:
```bash
cd /home/work/ceoloan && uv run python manage.py createsuperuser --username admin --email admin@example.com
```

그 다음 역할을 관리자로 올린다:
```bash
cd /home/work/ceoloan && uv run python manage.py shell -c "
from accounts.models import User
from accounts.services import membership
u = User.objects.get(username='admin')
membership.approve(u, User.Role.ADMIN)
print(u.username, u.role, u.is_staff, u.is_superuser)
"
```
Expected: `admin admin True True`

- [ ] **Step 7: 화면 확인**

Run:
```bash
cd /home/work/ceoloan && uv run python manage.py runserver
```
`/admin/`으로 로그인한 뒤 `/funding/admin/` 접속.
Expected: 목록 화면이 뜬다(데이터는 아직 0건). 사이드바에 「기업 자금」·「기업자금 관리」·「전달 내역」이 보이고 로고가 `ceoloan`이다

- [ ] **Step 8: 커밋**

```bash
cd /home/work/ceoloan && git add -A && git commit -m "feat: 마이그레이션과 로컬 구동"
```

---

## Phase D — 데이터 이전

### Task 10: 수집 데이터 덤프

**Files:** 없음 (서버 작업)

**Interfaces:**
- Produces: `cretop` 스키마 + `public.leads` 덤프 파일

`funding_*` 테이블과 `django_migrations`는 **가져오지 않는다** — 새 서버에서 이미 새로 만들었고, 테스트 계정·테스트 배분이 따라오면 안 된다.

- [ ] **Step 1: 기존 서버에서 덤프 대상 확인**

Run:
```bash
ssh chaconne@49.247.46.171 'docker exec rndnote-db-prod psql -U rndnote -d ceo_loan -c "select schemaname, count(*) from pg_tables where schemaname in (\"public\",\"cretop\") group by 1"' 2>/dev/null || \
ssh chaconne@49.247.46.171 "docker exec rndnote-db-prod psql -U rndnote -d ceo_loan -c \"select schemaname, count(*) from pg_tables where schemaname in ('public','cretop') group by 1\""
```
Expected: `cretop 34`, `public 9`

- [ ] **Step 2: 덤프 생성**

Run:
```bash
ssh chaconne@49.247.46.171 "docker exec rndnote-db-prod pg_dump -U rndnote -d ceo_loan --schema=cretop --table=public.leads -Fc -f /tmp/ceoloan_data.dump && docker cp rndnote-db-prod:/tmp/ceoloan_data.dump /tmp/ceoloan_data.dump && ls -lh /tmp/ceoloan_data.dump"
```
Expected: 파일 생성. 압축되어 1.9GB보다 작다

- [ ] **Step 3: 덤프 내용 확인**

Run:
```bash
ssh chaconne@49.247.46.171 "pg_restore -l /tmp/ceoloan_data.dump | grep -cE 'TABLE DATA'; pg_restore -l /tmp/ceoloan_data.dump | grep 'TABLE DATA' | grep -c funding_ || echo 'funding 테이블 없음(정상)'"
```
Expected: 테이블 데이터 항목 35개 내외, funding 테이블은 없다

---

### Task 11: 새 서버로 전송·복원

**Files:** 없음 (서버 작업)

**Interfaces:**
- Consumes: Task 10의 덤프
- Produces: 새 서버 DB에 cretop 34테이블 + leads 14,084행

- [ ] **Step 1: 새 서버에 DB 기동**

Run:
```bash
ssh chaconne@49.247.205.170 'mkdir -p ~/ceoloan'
scp /home/work/ceoloan/docker-compose.yml /home/work/ceoloan/.env chaconne@49.247.205.170:~/ceoloan/
ssh chaconne@49.247.205.170 'cd ~/ceoloan && docker compose up -d db && sleep 10 && docker compose ps'
```
Expected: `ceoloan-db` healthy

- [ ] **Step 2: 덤프 전송**

기존 서버에서 새 서버로 바로 보낸다(로컬을 거치지 않는다).

Run:
```bash
ssh chaconne@49.247.46.171 'scp -o StrictHostKeyChecking=accept-new /tmp/ceoloan_data.dump chaconne@49.247.205.170:/tmp/'
```
전송이 안 되면(키 없음) 로컬을 거친다:
```bash
scp chaconne@49.247.46.171:/tmp/ceoloan_data.dump /tmp/ && scp /tmp/ceoloan_data.dump chaconne@49.247.205.170:/tmp/
```
Expected: 새 서버 `/tmp/ceoloan_data.dump` 존재

- [ ] **Step 3: 복원**

Run:
```bash
ssh chaconne@49.247.205.170 'cd ~/ceoloan && docker cp /tmp/ceoloan_data.dump ceoloan-db:/tmp/ && docker compose exec -T db pg_restore -U ceoloan -d ceo_loan --no-owner --no-privileges /tmp/ceoloan_data.dump 2>&1 | tail -20'
```
Expected: 오류 없이 끝난다. 소유자 관련 경고는 무시해도 된다(`--no-owner`)

- [ ] **Step 4: 복원 확인**

Run:
```bash
ssh chaconne@49.247.205.170 "cd ~/ceoloan && docker compose exec -T db psql -U ceoloan -d ceo_loan -c \"select count(*) as cretop_tables from pg_tables where schemaname='cretop'\" -c 'select count(*) as leads from public.leads' -c \"select count(*) as companies from cretop.companies\""
```
Expected: cretop 34테이블, leads 14,084행, companies 약 7,900행

- [ ] **Step 5: 임시 파일 정리**

Run:
```bash
ssh chaconne@49.247.46.171 'rm -f /tmp/ceoloan_data.dump; docker exec rndnote-db-prod rm -f /tmp/ceoloan_data.dump'
ssh chaconne@49.247.205.170 'rm -f /tmp/ceoloan_data.dump; cd ~/ceoloan && docker compose exec -T db rm -f /tmp/ceoloan_data.dump'
```

---

### Task 12: 새 서버에서 앱 기동과 데이터 확인

**Files:** 없음 (서버 작업)

**Interfaces:**
- Consumes: Task 9(코드), Task 11(데이터)
- Produces: 새 서버에서 회사 7,899건이 보이는 상태

- [ ] **Step 1: 코드 전송**

Run:
```bash
cd /home/work/ceoloan && git bundle create /tmp/ceoloan.bundle --all && scp /tmp/ceoloan.bundle chaconne@49.247.205.170:/tmp/
ssh chaconne@49.247.205.170 'cd ~/ceoloan && git clone /tmp/ceoloan.bundle repo && ls repo/'
```
Expected: 저장소가 서버에 복제된다

- [ ] **Step 2: 양식 파일과 .env 전송**

`assets/경영진단.xlsx`는 git 비추적이라 따로 보낸다.

Run:
```bash
ssh chaconne@49.247.205.170 'mkdir -p ~/ceoloan/repo/assets'
scp "/home/work/rndnote/assets/경영진단.xlsx" chaconne@49.247.205.170:~/ceoloan/repo/assets/
scp /home/work/ceoloan/.env chaconne@49.247.205.170:~/ceoloan/repo/.env
ssh chaconne@49.247.205.170 'ls -la ~/ceoloan/repo/assets/'
```
Expected: 양식 파일 존재

- [ ] **Step 3: 의존성 설치와 마이그레이션**

Run:
```bash
ssh chaconne@49.247.205.170 'cd ~/ceoloan/repo && ~/.local/bin/uv sync --extra dev && ~/.local/bin/uv run python manage.py migrate 2>&1 | tail -10'
```
Expected: accounts·funding 마이그레이션 적용

- [ ] **Step 4: 대표이사 동기화**

Run:
```bash
ssh chaconne@49.247.205.170 'cd ~/ceoloan/repo && ~/.local/bin/uv run python manage.py funding_sync_ceos 2>&1 | tail -15'
```
Expected: 대표이사·회사 연결이 생성된다. 「자동 배분: … 활성 담당자 0명」이 나오면 정상이다 — 담당자가 아직 없다

- [ ] **Step 5: 데이터 확인**

Run:
```bash
ssh chaconne@49.247.205.170 'cd ~/ceoloan/repo && ~/.local/bin/uv run python manage.py shell -c "
from funding.models import Ceo, CeoCompany, Agent, Assignment
print(\"대표이사:\", Ceo.objects.count())
print(\"회사연결:\", CeoCompany.objects.count())
print(\"담당자:\", Agent.objects.count())
print(\"배분:\", Assignment.objects.count())
"'
```
Expected: 대표이사·회사연결 약 7,900건, 담당자 0, 배분 0

- [ ] **Step 6: 슈퍼유저 만들고 화면 확인**

Run:
```bash
ssh chaconne@49.247.205.170 'cd ~/ceoloan/repo && ~/.local/bin/uv run python manage.py createsuperuser --noinput --username admin --email admin@example.com' || true
ssh chaconne@49.247.205.170 'cd ~/ceoloan/repo && ~/.local/bin/uv run python manage.py shell -c "
from accounts.models import User
from accounts.services import membership
u = User.objects.get(username=\"admin\")
u.set_password(\"임시비밀번호를_여기서_정한다\"); u.save()
membership.approve(u, User.Role.ADMIN)
print(u.username, u.role)
"'
```

그 다음 서버에서 임시로 띄워 확인한다:
```bash
ssh -L 8900:127.0.0.1:8900 chaconne@49.247.205.170 'cd ~/ceoloan/repo && ~/.local/bin/uv run python manage.py runserver 127.0.0.1:8900'
```
브라우저에서 `http://127.0.0.1:8900/admin/`으로 로그인한 뒤 `/funding/admin/` 접속.
Expected: 회사 목록이 7,899건 기준으로 뜨고 「더 보기」가 동작한다

- [ ] **Step 7: 경영진단 결과서 확인**

목록에서 회사 하나를 눌러 모달을 열고 「경영진단 내려받기」를 실행한다.
Expected: 엑셀이 받아지고 회사매출현황·재무제표가 채워져 있다. 실패하면 `GEMINI_API_KEY`가 `.env`에 있는지 확인한다

---

### Task 13: 수집 도구 접속 개통

**Files:** 없음 (서버 작업)

**Interfaces:**
- Produces: 기존 서버에서 새 서버 DB(5433)로 쓸 수 있는 상태

- [ ] **Step 1: DB 포트를 외부에 여는 설정으로 바꾸기**

`~/ceoloan/docker-compose.yml`의 db 포트 바인딩을 바꾼다. 지금은 `127.0.0.1:5433`이라 외부에서 못 붙는다.

```yaml
    ports:
      # ufw가 49.247.46.171만 허용한다(Task 2). docker가 ufw를 우회하므로
      # DOCKER-USER 체인에도 같은 제한을 건다.
      - "5433:5432"
```

Run:
```bash
ssh chaconne@49.247.205.170 'cd ~/ceoloan && docker compose up -d db && docker compose ps'
```

- [ ] **Step 2: docker의 ufw 우회를 막는 규칙 추가**

docker는 ufw를 건너뛰므로 `DOCKER-USER` 체인에 직접 건다.

Run:
```bash
ssh chaconne@49.247.205.170 'sudo iptables -I DOCKER-USER -p tcp --dport 5432 ! -s 49.247.46.171 -j DROP && sudo iptables -I DOCKER-USER -p tcp --dport 5432 -s 49.247.46.171 -j ACCEPT && sudo iptables -L DOCKER-USER -n --line-numbers'
```
Expected: 규칙 2개가 보인다

- [ ] **Step 3: 규칙을 재부팅 뒤에도 유지**

Run:
```bash
ssh chaconne@49.247.205.170 'sudo apt-get install -y iptables-persistent && sudo netfilter-persistent save'
```
설치 중 물어보면 IPv4·IPv6 모두 저장에 동의한다.

- [ ] **Step 4: 기존 서버에서 접속되는지 확인**

Run:
```bash
ssh chaconne@49.247.46.171 "PGPASSWORD='<새서버_POSTGRES_PASSWORD>' psql -h 49.247.205.170 -p 5433 -U ceoloan -d ceo_loan -c 'select count(*) from cretop.companies'"
```
Expected: 회사 수가 나온다

- [ ] **Step 5: 제3자는 못 붙는지 확인**

Run:
```bash
timeout 8 bash -c 'cat < /dev/null > /dev/tcp/49.247.205.170/5433' 2>&1 && echo "⚠ 로컬에서 붙힌다 — 규칙 재확인 필요" || echo "차단됨(정상)"
```
Expected: `차단됨(정상)`

- [ ] **Step 6: 수집 도구 접속 정보 변경**

수집 도구는 이 저장소 밖에 있다. 위치를 확인한 뒤 접속 정보를 새 서버로 바꾼다.

Run:
```bash
ssh chaconne@49.247.46.171 'grep -rl "ceo_loan" ~/ --include=*.py --include=*.env --include=*.yml 2>/dev/null | grep -v rndnote | head'
```
찾은 도구의 DB 접속 설정을 아래로 바꾼다:
- host `49.247.205.170`, port `5433`, dbname `ceo_loan`, user `ceoloan`, password는 새 서버 `.env`의 값

**도구를 못 찾으면 여기서 멈추고 사용자에게 위치를 묻는다.** 임의로 추정해 고치지 않는다

- [ ] **Step 7: 수집 1회 실행해 새 DB에 쓰이는지 확인**

수집 도구를 1회 실행한 뒤:
```bash
ssh chaconne@49.247.205.170 "cd ~/ceoloan && docker compose exec -T db psql -U ceoloan -d ceo_loan -c 'select max(collected_at) from cretop.company_detail_snapshots'"
```
Expected: 실행 시각이 갱신된다

---

## Self-Review 결과

**설계 문서 대비 빠진 것:** 없다. 설계의 1·2·4단계가 Task 1~13에 모두 대응한다. 3·5·6단계는 범위에서 명시적으로 제외했다.

**실행 중 확인이 필요한 지점:**

1. **Task 6 Step 3** — DB alias 제거 스크립트가 놓친 곳이 없는지 Step 4로 반드시 확인한다.
2. **Task 9 Step 4** — 가져온 테스트 중 `cretop` 스키마를 실제로 읽는 것이 있으면 monkeypatch로 막혀 있어야 한다.
3. **Task 13 Step 6** — 수집 도구를 찾지 못하면 멈추고 묻는다. 이 계획은 도구의 위치를 모른다.

## 다음 계획으로 넘길 것

- **3단계 구글 로그인**: OAuth 클라이언트 ID·시크릿, 리디렉션 URI(`https://synco.kr/accounts/google/login/callback/`), 가입 허용 도메인, 첫 슈퍼유저 구글 계정이 있어야 시작한다. `django-allauth` 도입, 로그인·승인 화면, `LOGIN_URL`·로그아웃 주소 교체, 첫 화면을 로그인으로 바꾸기가 포함된다.
- **5단계 배포**: `web`·`nginx` 컨테이너, `deploy.sh`, certbot 인증서, 크론 등록.
- **6단계 전환**: 실제 TM 계정 승인·배분, rndlog 기업자금 동결 공지.
