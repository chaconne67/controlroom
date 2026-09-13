# 기업자금 관리자 페이지 · 역할 3종 · 영업 전달 구현 계획

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** TM 진행 내역을 관리자가 회사 단위로 확인하고, 고른 건을 경영진단 엑셀과 함께 영업담당자에게 메일로 전달하며, 영업담당자가 결과를 남기는 흐름을 만든다.

**Architecture:** 역할의 정본을 `accounts.User.role` 한 곳에 모으고, `funding`의 시야 규칙을 그 역할로 갈아끼운다. 관리자 목록은 `CeoCompany`를 기준 테이블로 삼아 DB에서 집계·필터·정렬을 끝낸다. 전달은 `Handoff` 레코드를 만든 뒤 메일 1통을 보내며, 본문 조립은 DB를 모르는 순수 함수로 분리해 테스트한다.

**Tech Stack:** Django 5.2, PostgreSQL(2개 DB: `default`, `ceo_loan`), HTMX, Tailwind, pytest-django, openpyxl

**설계 문서:** [2026-07-26-funding-admin-handoff-design.md](../specs/2026-07-26-funding-admin-handoff-design.md)

**범위:** 설계 문서의 구현 순서 1~4단계. **5단계(구글 로그인·가입 승인 화면)는 이 계획에 없다** — OAuth 클라이언트 정보가 있어야 시작할 수 있어 별도 계획으로 뺀다.

## Global Constraints

- 브랜치는 `ceo-loan`이다. `marketing` 메뉴와 `*/marketing` URL에 닿는 작업은 모두 이 브랜치에서 한다.
- **테스트에서 `funding` 모델을 만지는 테스트는 `@pytest.mark.django_db(databases=["default", "ceo_loan"])`를 붙인다.** alias만 있고 마크에 명시하지 않으면 `DatabaseOperationForbidden`으로 막힌다 (실측 확인, 2026-07-26). `default`만 쓰는 테스트는 기존대로 `@pytest.mark.django_db`면 된다.
- **`cretop` 스키마(`cretop.company_profiles`, `cretop.report_template_fields` 등)는 테스트 DB에 없다.** 마이그레이션이 만드는 테이블이 아니다. `funding.services.cretop_data`와 `report.build`를 호출하는 경로는 테스트에서 monkeypatch로 막는다 — 기존 `funding/test_report.py`가 쓰는 방식이다.
- 본문 조립처럼 DB가 필요 없는 로직은 **순수 함수로 분리**해 DB 없이 검증한다. 테스트가 빨라지고 무엇이 깨졌는지 좁혀진다.
- `funding`과 `accounts`는 서로 다른 DB에 있어 **교차 FK를 걸 수 없다**. 기존 `funding.Agent.username`처럼 문자열로 느슨하게 잇는다.
- 목록 화면의 필터·정렬·집계는 **전부 DB에서** 끝낸다. 파이썬에서 거르면 상한(`PAGE_SIZE`) 앞에서 전 건을 읽게 된다.
- 한글 이름·상호 정렬은 `Collate("<컬럼>", "C")`를 쓴다. DB 콜레이션이 `en_US.utf8`이라 그냥 정렬하면 가나다순이 아니다.
- 값이 없으면 비운다. **추정값이나 대체값을 만들어 넣지 않는다.**
- 검증 명령: `uv run pytest`, `uv run ruff check`, `uv run python manage.py check`, `uv run python manage.py check --settings=main.settings.deploy`
- 커밋 메시지는 한국어 한 줄 요약 + 필요 시 본문. 기존 이력 형식(`feat(funding): …`)을 따른다.

---

## File Structure

**생성**

| 파일 | 책임 |
|---|---|
| `accounts/services/__init__.py` | 빈 패키지 |
| `accounts/services/membership.py` | 역할 부여·변경의 단일 진입점. `Agent` 동기화 포함 |
| `accounts/test_membership.py` | 역할 부여 규칙 테스트 |
| `accounts/test_landing.py` | 로그인 착지 분기 테스트 |
| `accounts/templates/accounts/pending.html` | 승인대기 안내 화면 |
| `funding/views/__init__.py` | 기존 `views.py`의 공용 헬퍼 + 하위 모듈 re-export |
| `funding/views/tm.py` | 기존 TM 워크스페이스·상세·통화·녹음 뷰 (이동) |
| `funding/views/adminboard.py` | 관리자 목록·진행 내역 모달 |
| `funding/views/handoff.py` | 전달 폼·전달 생성·영업자 전달함 |
| `funding/services/adminboard.py` | 관리자 목록 쿼리셋 조립 |
| `funding/services/handoff.py` | 전달 본문 조립(순수) + 메일 발송 |
| `funding/test_handoff.py` | 본문 조립·메일 조립 테스트 |
| `funding/templates/funding/admin_list.html` | 관리자 목록 화면 |
| `funding/templates/funding/_admin_rows.html` | 목록 머리글+항목 파샬 |
| `funding/templates/funding/_admin_items.html` | 「더 보기」용 항목 파샬 |
| `funding/templates/funding/_progress_modal.html` | 진행 내역 모달 |
| `funding/templates/funding/_handoff_form.html` | 전달 모달 |
| `funding/templates/funding/handoff_inbox.html` | 영업자 전달함 |
| `funding/templates/funding/_handoff_items.html` | 전달함 항목 파샬 |

**수정**

| 파일 | 변경 |
|---|---|
| `accounts/models.py` | `Role` choices + `role` 필드 |
| `accounts/views.py:22,40` | 로그인 성공 리다이렉트를 착지 뷰로 |
| `accounts/urls.py` | `after-login/`, `pending/` 추가 |
| `common/auth.py` | `require_roles` 추가 (`require_staff`는 그대로 둔다) |
| `funding/models.py` | `Handoff` 모델 |
| `funding/urls.py` | 관리자·전달·전달함 경로 |
| `templates/common/nav_sidebar.html:25,33` | 메뉴 표시를 역할 기준으로 |
| `main/settings/base.py:129` | `LOGIN_REDIRECT_URL`을 착지 뷰로 |

**건드리지 않음:** `marketing/` 전체, `checkup/`, `companies/`, `cretop/`, `funding/services/{report,loan,assignment,audio,cretop_data}.py`

---

### Task 0: 테스트에서 ceo_loan DB 쓰기 — **완료됨 (커밋 `52da627`)**

**Files:**
- Modify: `main/settings/base.py:109-118`

계획을 세우면서 먼저 확인한 항목이다. 결과만 남긴다.

- [x] `postgres_database()`에서 `if not RUNNING_TESTS` 조건을 없애 `ceo_loan` alias가 테스트에도 생긴다
- [x] `uv run pytest` 292개 전부 통과 — 기존 테스트가 깨지지 않는다
- [x] `test_ceo_loan` DB가 실제로 만들어지고 `funding` 모델 CRUD가 된다
- [x] 마크에 `databases=["default", "ceo_loan"]`를 명시하지 않으면 `DatabaseOperationForbidden`으로 막힌다 — 아래 모든 funding DB 테스트가 이 마크를 쓴다

---

### Task 1: 사용자 역할 필드

**Files:**
- Modify: `accounts/models.py`
- Create: `accounts/migrations/0003_user_role.py` (번호는 기존 최신 +1)
- Test: `accounts/test_membership.py`

**Interfaces:**
- Produces: `accounts.models.User.Role` (`PENDING`/`ADMIN`/`TM`/`SALES`), `User.role` 필드

- [ ] **Step 1: 기존 마이그레이션 번호 확인**

Run: `ls accounts/migrations/`
새 마이그레이션 파일 이름은 마지막 번호 +1로 짓는다.

- [ ] **Step 2: 실패하는 테스트 작성**

Create `accounts/test_membership.py`:

```python
"""역할 부여 규칙 테스트.

예방 장애: 역할과 is_staff가 어긋나 영업담당자가 마케팅 화면을 보거나,
승인된 TM이 배분 대상에서 빠지는 것.
"""

import pytest
from django.contrib.auth import get_user_model


@pytest.mark.django_db
def test_new_user_starts_pending():
    user = get_user_model().objects.create_user(username="u1", password="pw")
    assert user.role == get_user_model().Role.PENDING
    assert user.is_staff is False
```

- [ ] **Step 3: 실패 확인**

Run: `uv run pytest accounts/test_membership.py -v`
Expected: FAIL — `AttributeError: type object 'User' has no attribute 'Role'`

- [ ] **Step 4: 모델에 역할 추가**

`accounts/models.py`:

```python
class User(AbstractUser):
    class Role(models.TextChoices):
        PENDING = "pending", "승인대기"
        ADMIN = "admin", "관리자"
        TM = "tm", "TM담당자"
        SALES = "sales", "영업담당자"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    phone = models.CharField(max_length=20, blank=True)
    # 역할의 정본. 화면 가드는 이 값만 본다.
    # is_staff는 Django admin과 marketing 화면 전용으로 남는다 — 둘을 같이
    # 세팅하는 곳은 accounts.services.membership.approve 하나뿐이다.
    role = models.CharField(
        max_length=10,
        choices=Role.choices,
        default=Role.PENDING,
        db_index=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "users"
```

- [ ] **Step 5: 마이그레이션 생성**

Run: `uv run python manage.py makemigrations accounts`
Expected: `accounts/migrations/0003_user_role.py` 생성

- [ ] **Step 6: 테스트 통과 확인**

Run: `uv run pytest accounts/test_membership.py -v`
Expected: PASS

- [ ] **Step 7: 커밋**

```bash
git add accounts/models.py accounts/migrations/ accounts/test_membership.py
git commit -m "feat(accounts): 사용자 역할 필드를 추가한다"
```

---

### Task 2: 역할 부여 서비스

**Files:**
- Create: `accounts/services/__init__.py`, `accounts/services/membership.py`
- Test: `accounts/test_membership.py` (추가)

**Interfaces:**
- Consumes: `User.Role` (Task 1)
- Produces:
  - `accounts.services.membership.approve(user, role) -> None`
  - `accounts.services.membership.reject(user) -> None`
  - `accounts.services.membership.sync_agent(user, role) -> None` (테스트에서 monkeypatch 대상)
  - `accounts.services.membership.STAFF_ROLES` (`frozenset`)

- [ ] **Step 1: 실패하는 테스트 추가**

`accounts/test_membership.py`에 이어 붙인다:

```python
from accounts.services import membership
from funding.models import Agent

Role = get_user_model().Role

# 승인은 accounts(default)와 funding(ceo_loan) 두 DB를 함께 만진다.
both_dbs = pytest.mark.django_db(databases=["default", "ceo_loan"])


@both_dbs
def test_admin_gets_staff_flag():
    user = get_user_model().objects.create_user(username="a", password="pw")
    membership.approve(user, Role.ADMIN)
    user.refresh_from_db()
    assert user.role == Role.ADMIN
    assert user.is_staff is True


@both_dbs
def test_sales_does_not_get_staff_flag():
    """영업담당자에게 is_staff를 주면 이메일 캠페인 화면까지 열린다."""
    user = get_user_model().objects.create_user(username="s", password="pw")
    membership.approve(user, Role.SALES)
    user.refresh_from_db()
    assert user.role == Role.SALES
    assert user.is_staff is False


@both_dbs
def test_tm_approval_creates_active_agent():
    """TM으로 승인하면 배분 대상이 되어야 한다."""
    user = get_user_model().objects.create_user(
        username="t", password="pw", first_name="김", last_name="티엠"
    )
    membership.approve(user, Role.TM)
    agent = Agent.objects.get(username="t")
    assert agent.is_active is True
    assert agent.display_name


@both_dbs
def test_role_change_away_from_tm_deactivates_agent_without_deleting():
    """Assignment.agent가 PROTECT라 레코드를 지우면 안 된다 — 비활성만 한다."""
    user = get_user_model().objects.create_user(username="t2", password="pw")
    membership.approve(user, Role.TM)
    membership.approve(user, Role.SALES)
    agent = Agent.objects.get(username="t2")
    assert agent.is_active is False


@both_dbs
def test_reject_clears_role_and_deactivates():
    user = get_user_model().objects.create_user(username="r", password="pw")
    membership.approve(user, Role.TM)
    membership.reject(user)
    user.refresh_from_db()
    assert user.role == Role.PENDING
    assert user.is_active is False
    assert user.is_staff is False
    assert Agent.objects.get(username="r").is_active is False
```

- [ ] **Step 2: 실패 확인**

Run: `uv run pytest accounts/test_membership.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'accounts.services'`

- [ ] **Step 3: 서비스 구현**

Create `accounts/services/__init__.py` (빈 파일).

Create `accounts/services/membership.py`:

```python
"""역할 부여의 단일 진입점.

역할(User.role)과 is_staff, 그리고 배분 대상 여부(funding.Agent)는 항상
같이 움직여야 한다. 세 곳을 각자 세팅하면 어긋난 계정이 생긴다 —
승인·역할 변경·거절은 전부 이 모듈을 지난다.
"""

from django.contrib.auth import get_user_model

User = get_user_model()

# 마케팅 화면과 Django admin 접근권을 함께 받는 역할.
# 영업담당자는 제외한다 — 이메일 캠페인은 영업 업무가 아니다.
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

    Agent는 ceo_loan DB에 있어 User와 FK로 묶을 수 없다 — username으로 잇는다.
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

- [ ] **Step 4: 테스트 통과 확인**

Run: `uv run pytest accounts/test_membership.py -v`
Expected: PASS (6 passed — Task 1의 1개 + 이번 5개)

- [ ] **Step 5: 커밋**

```bash
git add accounts/services/ accounts/test_membership.py
git commit -m "feat(accounts): 역할 부여를 한 서비스로 모은다"
```

---

### Task 3: 기존 계정 역할 백필

**Files:**
- Create: `accounts/migrations/0004_backfill_role.py`

**Interfaces:**
- Consumes: `User.role` (Task 1)

기존 사용자가 전부 `pending`으로 남으면 배포 순간 업무가 멈춘다. 아래 순서로 채운다.

- [ ] **Step 1: 마이그레이션 파일 작성**

Create `accounts/migrations/0004_backfill_role.py`:

```python
"""기존 계정에 역할을 채운다.

판정 순서가 곧 우선순위다.
  1. is_superuser        → admin
  2. 활성 funding.Agent  → tm
  3. 나머지 is_staff     → admin (지금 화면을 쓰던 내부 인원. 잠기면 업무가 멈춘다)
  4. 그 외               → pending

funding.Agent는 ceo_loan DB에 있어 apps.get_model로 못 읽는다 — 커넥션을
직접 연다. 마이그레이션 순서상 funding 테이블이 아직 없을 수 있으므로
(앱 간 순서는 교차 DB에서 보장되지 않는다) 있는지 먼저 확인하고 없으면
2번을 건너뛴다. 마이그레이션이 여기서 깨지면 테스트 전체가 멈춘다.
"""

from django.db import connections, migrations


def _tm_usernames() -> set:
    if "ceo_loan" not in connections:
        return set()
    with connections["ceo_loan"].cursor() as cur:
        cur.execute("SELECT to_regclass('public.funding_agent')")
        if cur.fetchone()[0] is None:
            return set()
        cur.execute("SELECT username FROM funding_agent WHERE is_active")
        return {row[0] for row in cur.fetchall()}


def backfill(apps, schema_editor):
    if schema_editor.connection.alias != "default":
        return
    User = apps.get_model("accounts", "User")
    User.objects.filter(is_superuser=True).update(role="admin")

    tm_names = _tm_usernames()
    if tm_names:
        User.objects.filter(username__in=tm_names, is_superuser=False).update(role="tm")

    User.objects.filter(is_staff=True, role="pending").update(role="admin")


def unbackfill(apps, schema_editor):
    if schema_editor.connection.alias != "default":
        return
    apps.get_model("accounts", "User").objects.update(role="pending")


class Migration(migrations.Migration):
    dependencies = [("accounts", "0003_user_role")]
    operations = [migrations.RunPython(backfill, unbackfill)]
```

- [ ] **Step 2: 테이블 이름 확인**

Run: `uv run python manage.py sqlmigrate funding 0001 | head -40`
`funding.Agent`의 실제 테이블 이름을 확인한다. Django 기본이면 `funding_agent`가 맞다. 다르면 위 SQL을 실제 이름으로 고친다.

- [ ] **Step 3: 마이그레이션이 테스트에서 깨지지 않는지 확인**

Run: `uv run pytest -q`
Expected: 292개 + 새 테스트 전부 PASS. 테스트 DB를 새로 만들 때 이 마이그레이션이 실행되므로, 여기서 깨지면 **전체 테스트가 멈춘다** — 반드시 전체를 돌린다.

- [ ] **Step 4: 로컬 DB에 적용해 결과 확인**

Run: `uv run python manage.py migrate accounts`
Run: `uv run python manage.py shell -c "from accounts.models import User; print(list(User.objects.values('username','role','is_staff')))"`
Expected: 기존 스태프가 `admin` 또는 `tm`으로 채워져 있다. `pending`으로 남은 내부 인원이 있으면 백필 규칙을 다시 본다.

- [ ] **Step 5: 커밋**

```bash
git add accounts/migrations/
git commit -m "feat(accounts): 기존 계정에 역할을 채운다"
```

---

### Task 4: 역할 가드와 시야 규칙 교체

**Files:**
- Modify: `common/auth.py`
- Modify: `funding/views.py` (8곳의 `is_superuser`, 2곳의 `is_staff`)
- Test: `funding/test_guards.py` (신규)

**Interfaces:**
- Consumes: `User.Role` (Task 1)
- Produces:
  - `common.auth.require_roles(request, *roles) -> None`
  - `common.auth.is_admin(user) -> bool`

`is_superuser`가 관리자 판정으로 쓰이는 곳이 8군데다. 하나라도 놓치면 TM이 남의 대표 데이터를 본다.

- [ ] **Step 1: 실패하는 테스트 작성**

Create `funding/test_guards.py`:

```python
"""역할 가드 계약 테스트.

예방 장애: 승인 안 된 계정이나 영업담당자가 TM 워크스페이스에 들어가
전체 대표 명단을 보는 것.
"""

import pytest
from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied

from common.auth import is_admin, require_roles

Role = get_user_model().Role


class _Req:
    def __init__(self, user):
        self.user = user


def _user(role, **kw):
    return get_user_model()(username="x", role=role, is_active=True, **kw)


@pytest.mark.django_db
def test_matching_role_passes():
    require_roles(_Req(_user(Role.ADMIN)), Role.ADMIN, Role.TM)


@pytest.mark.django_db
def test_other_role_is_denied():
    with pytest.raises(PermissionDenied):
        require_roles(_Req(_user(Role.SALES)), Role.ADMIN, Role.TM)


@pytest.mark.django_db
def test_pending_is_denied():
    with pytest.raises(PermissionDenied):
        require_roles(_Req(_user(Role.PENDING)), Role.ADMIN, Role.TM)


def test_anonymous_is_denied():
    from django.contrib.auth.models import AnonymousUser

    with pytest.raises(PermissionDenied):
        require_roles(_Req(AnonymousUser()), Role.ADMIN)


@pytest.mark.django_db
def test_is_admin_reads_role_not_superuser_flag():
    """superuser 플래그가 아니라 역할이 기준이다."""
    assert is_admin(_user(Role.ADMIN)) is True
    assert is_admin(_user(Role.TM, is_superuser=True)) is False
```

- [ ] **Step 2: 실패 확인**

Run: `uv run pytest funding/test_guards.py -v`
Expected: FAIL — `ImportError: cannot import name 'require_roles'`

- [ ] **Step 3: 가드 구현**

`common/auth.py`에 추가한다 (`require_staff`는 그대로 둔다 — marketing이 쓴다):

```python
from django.core.exceptions import PermissionDenied


def require_staff(request):
    """스태프 전용 화면 가드. marketing 전용."""
    if not (request.user.is_authenticated and request.user.is_staff):
        raise PermissionDenied


def require_roles(request, *roles):
    """역할 전용 화면 가드. funding·accounts 신규 화면이 쓴다.

    is_staff가 아니라 role을 본다 — 영업담당자는 is_staff가 없다.
    """
    user = request.user
    if not user.is_authenticated or not user.is_active:
        raise PermissionDenied
    if user.role not in roles:
        raise PermissionDenied


def is_admin(user) -> bool:
    """관리자 판정. superuser 플래그가 아니라 역할이 기준이다."""
    from django.contrib.auth import get_user_model

    return (
        getattr(user, "is_authenticated", False)
        and user.role == get_user_model().Role.ADMIN
    )
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `uv run pytest funding/test_guards.py -v`
Expected: PASS (5 passed)

- [ ] **Step 5: funding 뷰의 관리자 판정 교체**

`funding/views.py`에서 아래를 전부 바꾼다. 위치는 현재 파일 기준이며, 바꾸기 전에 `grep -n "is_superuser\|is_staff\|require_staff" funding/views.py`로 다시 확인한다.

| 현재 | 바꿀 것 |
|---|---|
| `funding/views.py:107` `_my_agent` — `if request.user.is_superuser:` | `if is_admin(request.user):` |
| `funding/views.py:117,122` `_visible_ceo_queryset` | `is_admin(request.user)` |
| `funding/views.py:293` `_get_visible_ceo` | `is_admin(request.user)` |
| `funding/views.py:485,618` QR 발급 가드 | `is_admin(request.user) or _my_agent(request)` |
| `funding/views.py:506` 미매칭 정리 | `is_admin(request.user)` |
| `funding/views.py:512` `_require_admin` | `if not is_admin(request.user): raise Http404` |
| `funding/views.py:598` 이름 노출 판정 | `is_admin(viewer)` |
| `funding/views.py:703,730` 담당자 후보 목록 `is_staff=True` | `role=User.Role.TM` |
| 모든 `require_staff(request)` | `require_roles(request, Role.ADMIN, Role.TM)` |

import를 파일 상단에 추가한다:

```python
from django.contrib.auth import get_user_model

from common.auth import is_admin, require_roles
```

`funding/templates/funding/audio_batch.html:69`의 `{% if request.user.is_superuser %}`는 뷰에서 넘긴 값으로 바꾼다 — 템플릿이 역할 규칙을 따로 알면 안 된다. `audio_batch` 뷰 컨텍스트에 `"is_admin": is_admin(request.user)`를 넣고 템플릿은 `{% if is_admin %}`로 고친다.

- [ ] **Step 6: 남은 곳이 없는지 확인**

Run: `grep -n "is_superuser\|require_staff\|is_staff=True" funding/`
Expected: 결과 없음 (마이그레이션 제외)

- [ ] **Step 7: 기존 테스트가 그대로 통과하는지 확인**

Run: `uv run pytest -v`
Expected: 기존 funding·marketing 테스트 전부 PASS.
`funding/test_assignment.py`가 화면을 트리거할 때 만드는 사용자에 역할이 없으면 여기서 깨진다. 깨지면 그 테스트의 사용자 생성에 `role=User.Role.ADMIN`을 넣는다.

- [ ] **Step 8: 커밋**

```bash
git add common/auth.py funding/views.py funding/test_guards.py funding/templates/funding/audio_batch.html
git commit -m "feat(funding): 시야 규칙을 superuser 플래그에서 역할로 옮긴다"
```

---

### Task 5: 로그인 착지 분기와 사이드바

**Files:**
- Modify: `accounts/views.py:22,40`, `accounts/urls.py`, `main/settings/base.py:129`
- Create: `accounts/templates/accounts/pending.html`
- Modify: `templates/common/nav_sidebar.html:25,33`
- Test: `accounts/test_landing.py`

**Interfaces:**
- Consumes: `User.Role` (Task 1)
- Produces: URL name `after_login`, `pending`

**주의:** 현재 `accounts/views.py`의 `login_page`는 `LOGIN_REDIRECT_URL`을 쓰지 않고 `redirect("marketing:dashboard")`를 두 곳에 하드코딩하고 있다. 설정만 바꾸면 아무 일도 일어나지 않는다.

- [ ] **Step 1: 실패하는 테스트 작성**

Create `accounts/test_landing.py`:

```python
"""로그인 착지 분기 테스트.

예방 장애: 영업담당자가 로그인했는데 볼 권한이 없는 마케팅 대시보드로
떨어져 403을 보는 것.
"""

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse

Role = get_user_model().Role


def _login(client, role):
    user = get_user_model().objects.create_user(
        username=f"u-{role}", password="pw", role=role, is_active=True
    )
    client.force_login(user)
    return user


@pytest.mark.django_db
@pytest.mark.parametrize(
    "role,expected",
    [
        (Role.ADMIN, "/funding/admin/"),
        (Role.TM, "/funding/"),
        (Role.SALES, "/funding/handoffs/"),
        (Role.PENDING, "/accounts/pending/"),
    ],
)
def test_after_login_lands_by_role(client, role, expected):
    _login(client, role)
    response = client.get(reverse("after_login"))
    assert response.status_code == 302
    assert response.url == expected


@pytest.mark.django_db
def test_anonymous_goes_to_login(client):
    response = client.get(reverse("after_login"))
    assert response.status_code == 302
    assert "/accounts/login/" in response.url
```

- [ ] **Step 2: 실패 확인**

Run: `uv run pytest accounts/test_landing.py -v`
Expected: FAIL — `NoReverseMatch: 'after_login' is not a valid view function or pattern name`

- [ ] **Step 3: 착지 뷰 구현**

`accounts/views.py`에 추가한다:

```python
# 역할별 착지. 아이디·비번 로그인과 (나중에 붙일) 구글 로그인이 모두
# 이 뷰 하나를 지난다 — 착지 규칙이 두 벌로 갈라지지 않게.
_LANDING_BY_ROLE = {
    User.Role.ADMIN: "funding:admin_list",
    User.Role.TM: "funding:workspace",
    User.Role.SALES: "funding:handoff_inbox",
}


@login_required
def after_login(request):
    target = _LANDING_BY_ROLE.get(request.user.role)
    if target is None:
        return redirect("pending")
    return redirect(target)


@login_required
def pending(request):
    return render(request, "accounts/pending.html")
```

같은 파일의 `login_page`에서 하드코딩된 착지를 바꾼다:

```python
def login_page(request):
    if request.user.is_authenticated:
        return redirect("after_login")
    ...
        if user.check_password(password):
            login(request, user)
            return redirect("after_login")
    ...
```

- [ ] **Step 4: URL 등록**

`accounts/urls.py`:

```python
urlpatterns = [
    path("accounts/login/", views.login_page, name="login"),
    path("accounts/logout/", views.logout_view, name="logout"),
    path("accounts/after-login/", views.after_login, name="after_login"),
    path("accounts/pending/", views.pending, name="pending"),
    path(
        "consultation-requests/",
        views.consultation_request_create,
        name="consultation_request_create",
    ),
]
```

`main/settings/base.py:129`:

```python
LOGIN_REDIRECT_URL = "/accounts/after-login/"
```

- [ ] **Step 5: 승인대기 화면 작성**

Create `accounts/templates/accounts/pending.html`:

```html
{% extends "common/base.html" %}
{% block title %}승인 대기{% endblock %}
{% block content %}
<div class="mx-auto max-w-md px-6 py-24 text-center">
  <h1 class="mb-3 text-2xl font-extrabold tracking-tight text-ink">승인을 기다리는 중입니다</h1>
  <p class="text-sm text-ink-mid">
    관리자가 역할을 지정하면 바로 사용하실 수 있습니다.<br>
    승인 후 다시 로그인해 주세요.
  </p>
  <a href="{% url 'logout' %}"
     class="mt-8 inline-block rounded-lg border border-line-strong bg-white px-4 py-2 text-sm font-semibold text-ink-mid shadow-sm hover:bg-paper-soft">
    로그아웃
  </a>
</div>
{% endblock %}
```

- [ ] **Step 6: 사이드바 역할 분기**

`templates/common/nav_sidebar.html` — 기존 마케팅 메뉴 3개를 스태프 역할로 묶고, 역할별 항목을 나눈다. 25번 줄의 `{% if request.user.is_staff %}`와 33번 줄의 `{% if request.user.is_superuser %}`를 아래로 바꾼다:

```html
{% if request.user.role == 'admin' or request.user.role == 'tm' %}
  <!-- 대시보드 · 이메일 캠페인 · 이메일 템플릿 3개 링크를 이 안으로 옮긴다 -->
  <a href="{% url 'funding:workspace' %}" ...>기업 자금</a>
{% endif %}
{% if request.user.role == 'admin' %}
  <a href="{% url 'funding:admin_list' %}" ...>기업자금 관리</a>
{% endif %}
{% if request.user.role == 'sales' %}
  <a href="{% url 'funding:handoff_inbox' %}" ...>전달함</a>
{% endif %}
{% if request.user.is_superuser %}
  <a href="{% url 'admin:index' %}" ...>Settings</a>   <!-- Django admin은 플래그가 맞다 -->
{% endif %}
```

링크의 클래스와 `hx-*` 속성은 기존 링크에서 그대로 복사한다. 아이콘: 기업자금 관리 `fa-solid fa-clipboard-list`, 전달함 `fa-solid fa-inbox`.

- [ ] **Step 7: 테스트 통과 확인**

Run: `uv run pytest accounts/test_landing.py -v`
Expected: PASS.
`funding:admin_list`·`funding:handoff_inbox`는 아직 없어 `NoReverseMatch`가 난다 → **Task 7·14에서 URL이 생긴 뒤 이 테스트가 통과한다.** 그때까지는 이 두 파라미터를 `pytest.mark.xfail`로 표시하고, Task 14 마지막 단계에서 표시를 지운다.

- [ ] **Step 8: 커밋**

```bash
git add accounts/ main/settings/base.py templates/common/nav_sidebar.html
git commit -m "feat(accounts): 로그인 착지를 역할별로 가른다"
```

---

### Task 6: funding 뷰 패키지 분리

**Files:**
- Move: `funding/views.py` → `funding/views/tm.py`
- Create: `funding/views/__init__.py`

**Interfaces:**
- Produces: `funding.views` 이름으로 기존 뷰가 그대로 보인다 (`urls.py` 수정 불필요)

기존 `views.py`가 700줄이다. 관리자 페이지·전달·전달함을 더하면 1,200줄을 넘어 한눈에 안 들어온다. `marketing/views/`가 이미 같은 패턴이다.

- [ ] **Step 1: 파일 이동**

```bash
mkdir -p funding/views
git mv funding/views.py funding/views/tm.py
```

- [ ] **Step 2: 패키지 진입점 작성**

Create `funding/views/__init__.py`:

```python
"""funding 뷰 묶음.

urls.py가 `from . import views` 한 줄로 모든 뷰를 보게 유지한다.
tm은 담당자 워크스페이스, adminboard는 관리자 목록, handoff는 전달이다.
"""

from funding.views.tm import *  # noqa: F401,F403
```

- [ ] **Step 3: ruff가 와일드카드 import를 통과하는지 확인**

Run: `uv run ruff check funding/`
Expected: 통과. 실패하면 `pyproject.toml`의 `[tool.ruff.lint.per-file-ignores]`에 `"funding/views/__init__.py" = ["F401", "F403"]`을 추가한다.

- [ ] **Step 4: 기존 테스트 전부 통과 확인**

Run: `uv run pytest -v && uv run python manage.py check`
Expected: 전부 PASS. import 경로가 깨졌으면 여기서 잡힌다.

- [ ] **Step 5: 커밋**

```bash
git add funding/ pyproject.toml
git commit -m "refactor(funding): 뷰를 패키지로 나눈다"
```

---

### Task 7: 관리자 목록 쿼리

**Files:**
- Create: `funding/services/adminboard.py`
- Test: `funding/test_adminboard.py`

**Interfaces:**
- Produces:
  - `funding.services.adminboard.company_queryset() -> QuerySet[CeoCompany]`
  - `funding.services.adminboard.apply_filters(qs, *, search, agent_id, min_reaction, handoff_state) -> QuerySet`
  - `funding.services.adminboard.PAGE_SIZE` (= 100)
  - `funding.services.adminboard.label_rows(rows) -> rows`

이 모듈은 ORM만 쓰고 `cretop` 스키마를 읽지 않아 테스트 DB에서 그대로 검증된다.

- [ ] **Step 1: 실패하는 테스트 작성**

Create `funding/test_adminboard.py`:

```python
"""관리자 목록 쿼리 테스트.

예방 장애:
- 회사가 여럿인 대표의 행이 겹쳐 같은 회사가 두 번 나오는 것
- 반응도·전달 상태가 최신 것이 아니라 아무 값이나 붙는 것
- 필터가 파이썬에서 걸려 상한(PAGE_SIZE)이 무의미해지는 것
"""

import pytest
from django.utils import timezone

from funding.models import Agent, Assignment, CallRecord, Ceo, CeoCompany, Handoff
from funding.services import adminboard

pytestmark = pytest.mark.django_db(databases=["default", "ceo_loan"])


def _company(name, ceo_name, bizno):
    ceo = Ceo.objects.create(name=ceo_name, phone_digits=bizno + "0")
    return CeoCompany.objects.create(
        ceo=ceo,
        company_name=name,
        business_number_digits=bizno,
        cretop_company_id="00000000-0000-0000-0000-000000000001",
    )


def _call(ceo, *, days_ago, reaction):
    return CallRecord.objects.create(
        ceo=ceo,
        happened_at=timezone.now() - timezone.timedelta(days=days_ago),
        result=CallRecord.Result.CONNECTED,
        reaction=reaction,
        performed_by="tester",
    )


def test_one_row_per_company():
    link = _company("(주)가나다", "홍길동", "1111111111")
    CeoCompany.objects.create(
        ceo=link.ceo,
        company_name="(주)사아자",
        business_number_digits="2222222222",
        cretop_company_id="00000000-0000-0000-0000-000000000002",
    )
    assert adminboard.company_queryset().count() == 2


def test_latest_reaction_wins():
    link = _company("(주)가나다", "홍길동", "1111111111")
    _call(link.ceo, days_ago=5, reaction=2)
    _call(link.ceo, days_ago=1, reaction=5)
    row = adminboard.company_queryset().get(pk=link.pk)
    assert row.last_reaction == 5
    assert row.call_count == 2


def test_untouched_company_sorts_last():
    _company("(주)통화없음", "무통화", "3333333333")
    link = _company("(주)통화있음", "유통화", "4444444444")
    _call(link.ceo, days_ago=1, reaction=3)
    names = [r.company_name for r in adminboard.company_queryset()]
    assert names == ["(주)통화있음", "(주)통화없음"]


def test_search_matches_business_number():
    _company("(주)가나다", "홍길동", "1234567890")
    _company("(주)라마바", "이몰래", "9999999999")
    qs = adminboard.apply_filters(adminboard.company_queryset(), search="123456")
    assert [r.company_name for r in qs] == ["(주)가나다"]


def test_min_reaction_filter_is_inclusive():
    a = _company("(주)낮음", "낮", "1111111111")
    b = _company("(주)높음", "높", "2222222222")
    _call(a.ceo, days_ago=1, reaction=3)
    _call(b.ceo, days_ago=1, reaction=4)
    qs = adminboard.apply_filters(adminboard.company_queryset(), min_reaction="4")
    assert [r.company_name for r in qs] == ["(주)높음"]


def test_agent_filter_uses_assignment():
    agent = Agent.objects.create(username="kim", display_name="김티엠")
    other = Agent.objects.create(username="park", display_name="박티엠")
    a = _company("(주)김담당", "김", "1111111111")
    b = _company("(주)박담당", "박", "2222222222")
    Assignment.objects.create(ceo=a.ceo, agent=agent)
    Assignment.objects.create(ceo=b.ceo, agent=other)
    qs = adminboard.apply_filters(adminboard.company_queryset(), agent_id=str(agent.id))
    assert [r.company_name for r in qs] == ["(주)김담당"]


def test_handoff_status_is_the_latest_one():
    link = _company("(주)가나다", "홍길동", "1111111111")
    Handoff.objects.create(
        company=link, sales_username="s1", sent_by="admin", body_snapshot="x"
    )
    latest = Handoff.objects.create(
        company=link, sales_username="s2", sent_by="admin", body_snapshot="y"
    )
    latest.status = Handoff.Status.WON
    latest.save()
    row = adminboard.company_queryset().get(pk=link.pk)
    assert row.handoff_status == Handoff.Status.WON
    assert row.handoff_sales == "s2"


def test_unsent_filter_excludes_handed_off():
    a = _company("(주)전달함", "전", "1111111111")
    _company("(주)미전달", "미", "2222222222")
    Handoff.objects.create(
        company=a, sales_username="s", sent_by="admin", body_snapshot="x"
    )
    qs = adminboard.apply_filters(
        adminboard.company_queryset(), handoff_state="unsent"
    )
    assert [r.company_name for r in qs] == ["(주)미전달"]
```

- [ ] **Step 2: 실패 확인**

Run: `uv run pytest funding/test_adminboard.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'funding.services.adminboard'`

- [ ] **Step 3: 쿼리 모듈 작성**

Create `funding/services/adminboard.py`:

```python
"""관리자 목록 쿼리 — 회사 1개가 1행이다.

집계·필터·정렬을 전부 DB에서 끝낸다. 파이썬에서 거르면 상한(PAGE_SIZE)
앞에서 전 건을 읽게 되고, 그 순간 상한이 의미를 잃는다.
"""

from django.db.models import Count, F, Max, OuterRef, Q, Subquery
from django.db.models.functions import Collate

from funding.models import CallRecord, CeoCompany, Handoff

PAGE_SIZE = 100


def company_queryset():
    latest_call = CallRecord.objects.filter(ceo=OuterRef("ceo_id")).order_by(
        "-happened_at"
    )
    latest_handoff = Handoff.objects.filter(company=OuterRef("pk")).order_by(
        "-created_at"
    )
    return (
        CeoCompany.objects.select_related("ceo", "ceo__assignment__agent")
        .annotate(
            last_called_at=Max("ceo__calls__happened_at"),
            last_reaction=Subquery(latest_call.values("reaction")[:1]),
            call_count=Count("ceo__calls", distinct=True),
            handoff_status=Subquery(latest_handoff.values("status")[:1]),
            handoff_sales=Subquery(latest_handoff.values("sales_username")[:1]),
            sort_name=Collate("company_name", "C"),
        )
        .order_by(F("last_called_at").desc(nulls_last=True), "sort_name")
    )


def apply_filters(qs, *, search="", agent_id="", min_reaction="", handoff_state=""):
    if search:
        digits = "".join(ch for ch in search if ch.isdigit())
        cond = Q(company_name__icontains=search) | Q(ceo__name__icontains=search)
        if digits:
            cond |= Q(business_number_digits__contains=digits)
            cond |= Q(ceo__phone_digits__contains=digits)
        qs = qs.filter(cond)
    if agent_id:
        qs = qs.filter(ceo__assignment__agent_id=agent_id)
    if min_reaction:
        qs = qs.filter(last_reaction__gte=int(min_reaction))
    if handoff_state == "sent":
        qs = qs.filter(handoff_status__isnull=False)
    elif handoff_state == "unsent":
        qs = qs.filter(handoff_status__isnull=True)
    return qs


HANDOFF_LABELS = dict(Handoff.Status.choices)


def label_rows(rows):
    """annotate한 상태 코드를 화면 문구로 바꾼다. 템플릿이 코드값을 모르게."""
    for row in rows:
        row.handoff_label = HANDOFF_LABELS.get(row.handoff_status)
    return rows
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `uv run pytest funding/test_adminboard.py -v`
Expected: PASS (8 passed).
`Handoff`가 없어 import가 깨지면 **Task 10을 먼저 실행하고 돌아온다** — 두 태스크는 순서를 바꿔도 된다.

- [ ] **Step 5: 커밋**

```bash
git add funding/services/adminboard.py funding/test_adminboard.py
git commit -m "feat(funding): 관리자 목록 쿼리를 회사 단위로 만든다"
```

---

### Task 8: 관리자 목록 화면

**Files:**
- Create: `funding/views/adminboard.py`, `funding/templates/funding/admin_list.html`, `funding/templates/funding/_admin_rows.html`, `funding/templates/funding/_admin_items.html`
- Modify: `funding/urls.py`, `funding/views/__init__.py`

**Interfaces:**
- Consumes: `adminboard.company_queryset`, `adminboard.apply_filters`, `common.auth.require_roles`
- Produces: URL name `funding:admin_list`, `funding:admin_rows`

- [ ] **Step 1: 뷰 작성**

Create `funding/views/adminboard.py`:

```python
"""관리자 목록 — TM 진행 내역을 회사 단위로 본다. 관리자 전용."""

from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.http import Http404
from django.shortcuts import render
from urllib.parse import urlencode

from common.auth import require_roles
from funding.models import Agent, CallRecord
from funding.services import adminboard

Role = get_user_model().Role


def _offset(request) -> int:
    raw = request.GET.get("offset") or "0"
    if not raw.isdigit():
        raise Http404
    return int(raw)


def _context(request):
    search = (request.GET.get("search") or "").strip()
    agent_id = request.GET.get("agent") or ""
    min_reaction = request.GET.get("reaction") or ""
    handoff_state = request.GET.get("handoff") or ""

    qs = adminboard.apply_filters(
        adminboard.company_queryset(),
        search=search,
        agent_id=agent_id,
        min_reaction=min_reaction,
        handoff_state=handoff_state,
    )
    total = qs.count()
    offset = _offset(request)
    rows = list(qs[offset : offset + adminboard.PAGE_SIZE])

    next_offset = offset + adminboard.PAGE_SIZE
    query = {
        k: v
        for k, v in {
            "search": search,
            "agent": agent_id,
            "reaction": min_reaction,
            "handoff": handoff_state,
        }.items()
        if v
    }
    return {
        "rows": rows,
        "total": total,
        "loaded": offset + len(rows),
        "next_offset": next_offset if next_offset < total else None,
        "list_query": urlencode(query),
        "search": search,
        "agent_filter": agent_id,
        "reaction_filter": min_reaction,
        "handoff_filter": handoff_state,
        "agents": Agent.objects.filter(is_active=True),
        "reaction_choices": CallRecord.REACTION_CHOICES,
    }


@login_required
def admin_list(request):
    require_roles(request, Role.ADMIN)
    return render(request, "funding/admin_list.html", _context(request))


@login_required
def admin_rows(request):
    """목록 파샬. 「더 보기」(offset)는 항목만 이어 붙인다."""
    require_roles(request, Role.ADMIN)
    template = "_admin_items.html" if request.GET.get("offset") else "_admin_rows.html"
    return render(request, f"funding/{template}", _context(request))
```

`funding/views/__init__.py`에 추가:

```python
from funding.views.adminboard import *  # noqa: F401,F403
```

- [ ] **Step 2: URL 등록**

`funding/urls.py`의 `urlpatterns`에 추가한다:

```python
    path("admin/", views.admin_list, name="admin_list"),
    path("admin/rows/", views.admin_rows, name="admin_rows"),
```

- [ ] **Step 3: 목록 화면 작성**

Create `funding/templates/funding/admin_list.html`:

```html
{% extends "funding/_layout.html" %}
{% block title %}기업자금 관리{% endblock %}
{% block page_title %}기업자금 관리{% endblock %}
{% block funding_content %}
<form id="admin-filters" hx-get="{% url 'funding:admin_rows' %}"
      hx-target="#admin-rows" hx-swap="outerHTML" hx-trigger="change, submit"
      class="mb-4 flex flex-wrap items-center gap-2">
  <input type="search" name="search" value="{{ search }}" placeholder="회사·대표·사업자번호·전화"
         class="w-64 rounded-lg border border-line-strong px-3 py-1.5 text-sm">
  <select name="agent" class="rounded-lg border border-line-strong px-3 py-1.5 text-sm">
    <option value="">담당 TM 전체</option>
    {% for a in agents %}
    <option value="{{ a.id }}" {% if agent_filter == a.id|stringformat:'s' %}selected{% endif %}>{{ a.display_name }}</option>
    {% endfor %}
  </select>
  <select name="reaction" class="rounded-lg border border-line-strong px-3 py-1.5 text-sm">
    <option value="">반응도 전체</option>
    {% for value, label in reaction_choices %}
    <option value="{{ value }}" {% if reaction_filter == value|stringformat:'s' %}selected{% endif %}>{{ label }} 이상</option>
    {% endfor %}
  </select>
  <select name="handoff" class="rounded-lg border border-line-strong px-3 py-1.5 text-sm">
    <option value="">전달 전체</option>
    <option value="unsent" {% if handoff_filter == 'unsent' %}selected{% endif %}>미전달</option>
    <option value="sent" {% if handoff_filter == 'sent' %}selected{% endif %}>전달함</option>
  </select>
  <button type="button" id="handoff-open"
          class="ml-auto rounded-lg bg-accent px-3 py-1.5 text-xs font-semibold text-white shadow-sm disabled:opacity-40"
          disabled>영업자에게 전달 <span id="handoff-count">0</span>건</button>
</form>

{% include "funding/_admin_rows.html" %}

<div id="modal-slot"></div>
{% endblock %}
```

- [ ] **Step 4: 목록 파샬 작성**

Create `funding/templates/funding/_admin_rows.html`:

```html
<div id="admin-rows">
  <p class="mb-2 text-xs text-ink-faint">전체 {{ total }}건 중 {{ loaded }}건</p>
  <table class="w-full text-sm">
    <thead class="border-b border-line text-xs text-ink-faint">
      <tr>
        <th class="w-8 px-2 py-2"></th>
        <th class="px-2 py-2 text-left">회사명</th>
        <th class="px-2 py-2 text-left">대표</th>
        <th class="px-2 py-2 text-left">담당 TM</th>
        <th class="px-2 py-2 text-left">최근 통화</th>
        <th class="px-2 py-2 text-left">반응도</th>
        <th class="px-2 py-2 text-right">통화</th>
        <th class="px-2 py-2 text-left">전달</th>
      </tr>
    </thead>
    <tbody id="admin-items">
      {% include "funding/_admin_items.html" %}
    </tbody>
  </table>
</div>
```

Create `funding/templates/funding/_admin_items.html`:

```html
{% for row in rows %}
<tr class="cursor-pointer border-b border-line-soft hover:bg-paper-soft"
    hx-get="{% url 'funding:progress_modal' row.pk %}" hx-target="#modal-slot" hx-swap="innerHTML">
  <td class="px-2 py-2" onclick="event.stopPropagation()">
    <input type="checkbox" class="handoff-pick" value="{{ row.pk }}"
           data-label="{{ row.company_name }}">
  </td>
  <td class="px-2 py-2 font-medium text-ink">{{ row.company_name }}</td>
  <td class="px-2 py-2">{{ row.ceo.name }}</td>
  <td class="px-2 py-2">{{ row.ceo.assignment.agent.display_name|default:"—" }}</td>
  <td class="px-2 py-2">{{ row.last_called_at|date:"m-d"|default:"—" }}</td>
  <td class="px-2 py-2">{{ row.last_reaction|default:"—" }}</td>
  <td class="px-2 py-2 text-right">{{ row.call_count }}</td>
  <td class="px-2 py-2">{{ row.handoff_label|default:"미전달" }}</td>
</tr>
{% endfor %}
{% if next_offset %}
<tr id="admin-more">
  <td colspan="8" class="py-3 text-center">
    <button hx-get="{% url 'funding:admin_rows' %}?{{ list_query }}&offset={{ next_offset }}"
            hx-target="#admin-more" hx-swap="outerHTML"
            class="rounded-lg border border-line-strong px-4 py-1.5 text-xs font-semibold text-ink-mid hover:bg-paper-soft">
      더 보기
    </button>
  </td>
</tr>
{% endif %}
```

`handoff_label`은 Task 7에서 만든 `adminboard.label_rows`가 붙인다. `_context`의 `rows = list(...)` 다음 줄에 `rows = adminboard.label_rows(rows)`를 넣는다 — 템플릿이 상태 코드값을 직접 비교하지 않게 한다.

- [ ] **Step 5: 화면 확인**

Run: `uv run python manage.py runserver`
관리자 계정으로 `/funding/admin/` 접속.
Expected: 회사가 한 줄씩 나오고, 필터를 바꾸면 목록만 갱신되며, 「더 보기」가 항목을 이어 붙인다. 100건 넘는 데이터에서 응답이 즉시 온다.

- [ ] **Step 6: 커밋**

```bash
git add funding/views/ funding/urls.py funding/templates/funding/admin_list.html funding/templates/funding/_admin_rows.html funding/templates/funding/_admin_items.html funding/services/adminboard.py
git commit -m "feat(funding): 관리자 목록 화면을 만든다"
```

---

### Task 9: 진행 내역 모달

**Files:**
- Modify: `funding/views/adminboard.py`, `funding/urls.py`
- Create: `funding/templates/funding/_progress_modal.html`

**Interfaces:**
- Produces: URL name `funding:progress_modal`

- [ ] **Step 1: 뷰 추가**

`funding/views/adminboard.py`에 추가:

```python
from django.shortcuts import get_object_or_404

from funding.models import CallAudio, CeoCompany
from funding.services import cretop_data
from funding.views.tm import _estimate_from_facts


@login_required
def progress_modal(request, pk):
    """회사 한 곳의 TM 진행 내역 — 목록 행을 눌렀을 때 뜬다."""
    require_roles(request, Role.ADMIN)
    link = get_object_or_404(CeoCompany.objects.select_related("ceo"), pk=pk)
    facts = cretop_data.bulk_company_facts([link.cretop_company_id]).get(
        str(link.cretop_company_id), {}
    )
    return render(
        request,
        "funding/_progress_modal.html",
        {
            "link": link,
            "ceo": link.ceo,
            "facts": facts,
            "profile": cretop_data.company_profile(link.cretop_company_id),
            "estimate": _estimate_from_facts(facts),
            "calls": link.ceo.calls.all()[:50],
            "audios": link.ceo.audios.exclude(summary="")[:20],
        },
    )
```

`funding/urls.py`:

```python
    path("admin/companies/<uuid:pk>/", views.progress_modal, name="progress_modal"),
```

- [ ] **Step 2: 모달 템플릿 작성**

Create `funding/templates/funding/_progress_modal.html`:

```html
<div class="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-6"
     onclick="if(event.target===this) this.remove()">
  <div class="max-h-[85vh] w-full max-w-3xl overflow-y-auto rounded-xl bg-white p-6 shadow-xl">
    <div class="mb-4 flex items-start justify-between">
      <div>
        <h2 class="text-lg font-extrabold text-ink">{{ link.company_name }}</h2>
        <p class="text-sm text-ink-mid">{{ ceo.name }} · {{ ceo.phone_display }}</p>
      </div>
      <button onclick="this.closest('.fixed').remove()" class="text-ink-faint hover:text-ink">✕</button>
    </div>

    <section class="mb-5">
      <h3 class="mb-2 text-xs font-bold uppercase tracking-wider text-ink-faint">회사 정보</h3>
      <dl class="grid grid-cols-2 gap-x-6 gap-y-1 text-sm">
        <div><dt class="inline text-ink-faint">사업자번호</dt> <dd class="inline">{{ link.business_number_digits }}</dd></div>
        <div><dt class="inline text-ink-faint">업종</dt> <dd class="inline">{{ profile.industry_name|default:"—" }}</dd></div>
        <div><dt class="inline text-ink-faint">매출</dt> <dd class="inline">{{ facts.sales_million|default:"—" }}</dd></div>
        <div><dt class="inline text-ink-faint">대출 예상</dt> <dd class="inline">{{ estimate.display_text|default:"—" }}</dd></div>
      </dl>
      <a href="{% url 'funding:company_report' link.pk %}"
         class="mt-3 inline-block rounded-lg border border-line-strong px-3 py-1.5 text-xs font-semibold text-ink-mid hover:bg-paper-soft">
        📊 경영진단 내려받기
      </a>
    </section>

    <section class="mb-5">
      <h3 class="mb-2 text-xs font-bold uppercase tracking-wider text-ink-faint">통화 녹음 요약</h3>
      {% for audio in audios %}
      <div class="mb-2 rounded-lg bg-paper-soft p-3 text-sm">
        <p class="mb-1 text-xs text-ink-faint">{{ audio.happened_at|date:"Y-m-d H:i" }}{% if audio.happened_at_estimated %} (추정){% endif %}</p>
        <p class="whitespace-pre-line">{{ audio.summary }}</p>
      </div>
      {% empty %}
      <p class="text-sm text-ink-faint">녹음 요약이 없습니다.</p>
      {% endfor %}
    </section>

    <section>
      <h3 class="mb-2 text-xs font-bold uppercase tracking-wider text-ink-faint">통화 이력</h3>
      <table class="w-full text-sm">
        <tbody>
          {% for call in calls %}
          <tr class="border-b border-line-soft">
            <td class="py-2 pr-3 text-ink-faint">{{ call.happened_at|date:"m-d H:i" }}</td>
            <td class="py-2 pr-3">{{ call.get_result_display }}</td>
            <td class="py-2 pr-3">{{ call.get_reaction_display|default:"—" }}</td>
            <td class="py-2 pr-3">{{ call.memo|default:"—" }}</td>
            <td class="py-2 text-ink-faint">{{ call.performed_by }}</td>
          </tr>
          {% empty %}
          <tr><td class="py-2 text-ink-faint">통화 기록이 없습니다.</td></tr>
          {% endfor %}
        </tbody>
      </table>
    </section>
  </div>
</div>
```

- [ ] **Step 3: 화면 확인**

목록에서 행을 누른다.
Expected: 모달이 뜨고 회사 정보·녹음 요약·통화 이력이 보인다. 배경을 누르면 닫힌다. 체크박스를 눌러도 모달이 뜨지 않는다.

- [ ] **Step 4: 커밋**

```bash
git add funding/views/adminboard.py funding/urls.py funding/templates/funding/_progress_modal.html
git commit -m "feat(funding): 진행 내역 모달을 만든다"
```

---

### Task 10: Handoff 모델

**Files:**
- Modify: `funding/models.py`
- Create: `funding/migrations/00XX_handoff.py`

**Interfaces:**
- Produces: `funding.models.Handoff`, `Handoff.Status`

- [ ] **Step 1: 모델 추가**

`funding/models.py` 끝에 추가:

```python
class Handoff(BaseModel):
    """관리자 → 영업담당자 전달 1건. 회사 1개가 1건이다.

    영업담당자는 ceo_loan DB 밖(accounts.User)에 있어 FK를 걸 수 없다 —
    Agent와 같은 방식으로 username 문자열로 잇는다.
    """

    class Status(models.TextChoices):
        RECEIVED = "received", "수신"
        IN_PROGRESS = "in_progress", "진행중"
        WON = "won", "성사"
        LOST = "lost", "무산"

    company = models.ForeignKey(
        CeoCompany, on_delete=models.PROTECT, related_name="handoffs"
    )
    sales_username = models.CharField(max_length=150, db_index=True)
    sent_by = models.CharField(max_length=150)
    admin_comment = models.TextField(blank=True)
    # 보낸 본문 그대로. 영업자 화면에서 다시 보고, 나중에 무엇을 보냈는지 확인한다.
    body_snapshot = models.TextField()
    status = models.CharField(
        max_length=12, choices=Status.choices, default=Status.RECEIVED, db_index=True
    )
    sales_memo = models.TextField(blank=True)
    next_due = models.DateField(null=True, blank=True)
    email_sent_at = models.DateTimeField(null=True, blank=True)
    email_error = models.TextField(blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["sales_username", "status"]),
            models.Index(fields=["company", "-created_at"]),
        ]
```

- [ ] **Step 2: 마이그레이션 생성**

Run: `uv run python manage.py makemigrations funding`
Expected: 새 마이그레이션 파일 생성

- [ ] **Step 3: ceo_loan에 적용**

Run: `uv run python manage.py migrate funding --database=ceo_loan`
Expected: 적용 성공. (배포는 `deploy.sh`가 이미 `--database=ceo_loan`을 돈다)

- [ ] **Step 4: 점검 통과 확인**

Run: `uv run python manage.py check && uv run pytest -v`
Expected: PASS

- [ ] **Step 5: 커밋**

```bash
git add funding/models.py funding/migrations/
git commit -m "feat(funding): 영업 전달 기록 모델을 추가한다"
```

---

### Task 11: 전달 본문 조립 (순수 함수)

**Files:**
- Create: `funding/services/handoff.py`, `funding/test_handoff.py`

**Interfaces:**
- Produces:
  - `funding.services.handoff.CompanyItem` (dataclass: `company_name`, `ceo_name`, `business_number`, `industry`, `sales_text`, `loan_text`, `call_lines: list[str]`, `audio_summaries: list[str]`)
  - `funding.services.handoff.build_draft(items: list[CompanyItem]) -> str`
  - `funding.services.handoff.collect_items(company_links) -> list[CompanyItem]`

본문 조립은 DB를 모르는 순수 함수로 둔다 — 테스트 환경에 `ceo_loan`이 없어 이 방법으로만 검증할 수 있다.

- [ ] **Step 1: 실패하는 테스트 작성**

Create `funding/test_handoff.py`:

```python
"""전달 본문 조립 테스트.

예방 장애:
- 통화 녹음 요약이 빠진 채 회사 정보만 나가는 것 (영업자가 왜 이 건인지 모른다)
- 값이 없을 때 '없음' 같은 대체값이 사실처럼 나가는 것
"""

from funding.services import handoff


def _item(**kw):
    base = dict(
        company_name="(주)가나다",
        ceo_name="홍길동",
        business_number="1234567890",
        industry="소프트웨어 개발",
        sales_text="12억",
        loan_text="3억~5억",
        call_lines=["07-24 연결 · 5 유망 · 방문 희망"],
        audio_summaries=["대표가 시설자금 5억을 찾고 있음. 8월 초 방문 요청."],
    )
    base.update(kw)
    return handoff.CompanyItem(**base)


def test_draft_contains_company_and_tm_summary():
    body = handoff.build_draft([_item()])
    assert "(주)가나다" in body
    assert "홍길동" in body
    assert "시설자금 5억" in body
    assert "07-24 연결" in body


def test_draft_repeats_block_per_company():
    body = handoff.build_draft([_item(), _item(company_name="(주)라마바")])
    assert "(주)가나다" in body
    assert "(주)라마바" in body
    assert body.count("회사 정보") == 2


def test_missing_value_is_left_blank_not_filled():
    """값이 없으면 비운다 — 대체값을 만들어 넣지 않는다."""
    body = handoff.build_draft([_item(sales_text="", loan_text="")])
    assert "없음" not in body
    assert "미상" not in body
    assert "None" not in body


def test_audio_summary_missing_is_stated_plainly():
    body = handoff.build_draft([_item(audio_summaries=[])])
    assert "녹음 요약 없음" in body


def test_numbering_starts_at_one():
    body = handoff.build_draft([_item(), _item(company_name="(주)라마바")])
    assert "1. (주)가나다" in body
    assert "2. (주)라마바" in body
```

- [ ] **Step 2: 실패 확인**

Run: `uv run pytest funding/test_handoff.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'funding.services.handoff'`

- [ ] **Step 3: 구현**

Create `funding/services/handoff.py`:

```python
"""영업 전달 — 본문 조립과 메일 발송.

본문 조립(build_draft)은 DB를 모른다. 값을 모으는 일(collect_items)과
문장을 만드는 일을 나눠야 테스트 환경(ceo_loan DB 없음)에서 검증할 수 있다.

값이 없으면 비운다. 대체값을 만들어 넣지 않는다 — 영업자가 사실로 읽는다.
"""

from dataclasses import dataclass, field


@dataclass
class CompanyItem:
    company_name: str
    ceo_name: str
    business_number: str = ""
    industry: str = ""
    sales_text: str = ""
    loan_text: str = ""
    call_lines: list = field(default_factory=list)
    audio_summaries: list = field(default_factory=list)


def _line(label, value):
    return f"  - {label}: {value}" if value else None


def build_draft(items) -> str:
    blocks = []
    for index, item in enumerate(items, start=1):
        lines = [f"── {index}. {item.company_name} ──", "", "[회사 정보]"]
        lines += [
            line
            for line in (
                _line("대표", item.ceo_name),
                _line("사업자번호", item.business_number),
                _line("업종", item.industry),
                _line("매출", item.sales_text),
                _line("대출 예상", item.loan_text),
            )
            if line
        ]
        lines += ["", "[TM 내용]"]
        if item.audio_summaries:
            lines += [f"  - {summary}" for summary in item.audio_summaries]
        else:
            lines.append("  - 녹음 요약 없음")
        lines += [f"  - {call}" for call in item.call_lines]
        blocks.append("\n".join(lines))
    return "\n\n".join(blocks)
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `uv run pytest funding/test_handoff.py -v`
Expected: PASS (5 passed)

- [ ] **Step 5: 값 수집 함수 추가**

같은 파일에 이어 붙인다 (DB를 읽으므로 테스트하지 않는다):

```python
def collect_items(links) -> list:
    """CeoCompany 목록에서 본문에 쓸 값을 모은다.

    대출 금액은 화면·경영진단 결과서와 같은 함수를 쓴다 — 세 곳이 다른
    금액을 말하면 안 된다.
    """
    from funding.services import cretop_data
    from funding.views.tm import _estimate_from_facts

    facts_map = cretop_data.bulk_company_facts([link.cretop_company_id for link in links])
    items = []
    for link in links:
        facts = facts_map.get(str(link.cretop_company_id), {})
        estimate = _estimate_from_facts(facts)
        profile = cretop_data.company_profile(link.cretop_company_id)
        calls = link.ceo.calls.all()[:5]
        audios = link.ceo.audios.exclude(summary="")[:3]
        items.append(
            CompanyItem(
                company_name=link.company_name,
                ceo_name=link.ceo.name,
                business_number=link.business_number_digits,
                industry=(profile or {}).get("industry_name") or "",
                sales_text=str(facts.get("sales_million") or ""),
                loan_text=(estimate or {}).get("display_text") or "",
                call_lines=[
                    f"{call.happened_at:%m-%d} {call.get_result_display()}"
                    + (f" · {call.get_reaction_display()}" if call.reaction else "")
                    + (f" · {call.memo}" if call.memo else "")
                    for call in calls
                ],
                audio_summaries=[audio.summary for audio in audios],
            )
        )
    return items
```

- [ ] **Step 6: 커밋**

```bash
git add funding/services/handoff.py funding/test_handoff.py
git commit -m "feat(funding): 전달 본문 초안을 조립한다"
```

---

### Task 12: 전달 모달 화면

**Files:**
- Create: `funding/views/handoff.py`, `funding/templates/funding/_handoff_form.html`
- Modify: `funding/urls.py`, `funding/views/__init__.py`, `funding/templates/funding/admin_list.html`

**Interfaces:**
- Consumes: `handoff.collect_items`, `handoff.build_draft`
- Produces: URL name `funding:handoff_form`

- [ ] **Step 1: 폼 뷰 작성**

Create `funding/views/handoff.py`:

```python
"""영업 전달 — 전달 폼, 전달 생성, 영업자 전달함."""

from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.http import Http404
from django.shortcuts import render

from common.auth import require_roles
from funding.models import CeoCompany
from funding.services import handoff as handoff_service

Role = get_user_model().Role

# 한 번에 보낼 수 있는 건수 상한. 건마다 경영진단 엑셀을 만들어 붙이므로
# 상한이 없으면 요청이 타임아웃되거나 메일이 수신 한도에 걸린다.
MAX_PER_HANDOFF = 20


def _picked_links(request):
    ids = request.POST.getlist("company_ids") or request.GET.getlist("company_ids")
    if not ids:
        raise Http404
    if len(ids) > MAX_PER_HANDOFF:
        raise Http404
    links = list(
        CeoCompany.objects.select_related("ceo").filter(pk__in=ids)
    )
    if not links:
        raise Http404
    return links


@login_required
def handoff_form(request):
    """전달 모달 — 목록에서 고른 건으로 초안을 만들어 보여준다."""
    require_roles(request, Role.ADMIN)
    links = _picked_links(request)
    items = handoff_service.collect_items(links)
    return render(
        request,
        "funding/_handoff_form.html",
        {
            "links": links,
            "draft": handoff_service.build_draft(items),
            "sales_users": get_user_model().objects.filter(
                role=Role.SALES, is_active=True
            ).order_by("first_name", "username"),
            "max_per_handoff": MAX_PER_HANDOFF,
        },
    )
```

`funding/views/__init__.py`에 추가:

```python
from funding.views.handoff import *  # noqa: F401,F403
```

`funding/urls.py`:

```python
    path("admin/handoff/", views.handoff_form, name="handoff_form"),
```

- [ ] **Step 2: 전달 모달 템플릿 작성**

Create `funding/templates/funding/_handoff_form.html`:

```html
<div class="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-6"
     onclick="if(event.target===this) this.remove()">
  <form method="post" action="{% url 'funding:handoff_create' %}"
        class="max-h-[85vh] w-full max-w-2xl overflow-y-auto rounded-xl bg-white p-6 shadow-xl"
        onsubmit="var b=this.querySelector('[type=submit]'); b.disabled=true; b.textContent='보내는 중…';">
    {% csrf_token %}
    <h2 class="mb-1 text-lg font-extrabold text-ink">영업자에게 전달</h2>
    <p class="mb-4 text-sm text-ink-mid">{{ links|length }}건 · 경영진단 엑셀이 건별로 첨부됩니다.</p>

    <ul class="mb-4 max-h-24 overflow-y-auto rounded-lg bg-paper-soft p-3 text-sm">
      {% for link in links %}
      <li>{{ link.company_name }} · {{ link.ceo.name }}
        <input type="hidden" name="company_ids" value="{{ link.pk }}"></li>
      {% endfor %}
    </ul>

    <label class="mb-1 block text-xs font-bold text-ink-mid">받는 영업담당자</label>
    <select name="sales_username" required
            class="mb-4 w-full rounded-lg border border-line-strong px-3 py-2 text-sm">
      <option value="">선택하세요</option>
      {% for u in sales_users %}
      <option value="{{ u.username }}">{{ u.get_full_name|default:u.username }} · {{ u.email }}</option>
      {% endfor %}
    </select>

    <label class="mb-1 block text-xs font-bold text-ink-mid">관리자 커멘트</label>
    <textarea name="admin_comment" rows="3" placeholder="영업자에게 전할 말"
              class="mb-4 w-full rounded-lg border border-line-strong px-3 py-2 text-sm"></textarea>

    <label class="mb-1 block text-xs font-bold text-ink-mid">본문 (초안 — 고쳐서 보낼 수 있습니다)</label>
    <textarea name="body" rows="14" required
              class="mb-4 w-full rounded-lg border border-line-strong px-3 py-2 font-mono text-xs">{{ draft }}</textarea>

    <div class="flex justify-end gap-2">
      <button type="button" onclick="this.closest('.fixed').remove()"
              class="rounded-lg border border-line-strong px-4 py-2 text-sm font-semibold text-ink-mid hover:bg-paper-soft">취소</button>
      <button type="submit"
              class="rounded-lg bg-accent px-4 py-2 text-sm font-semibold text-white shadow-sm">전달하기</button>
    </div>
  </form>
</div>
```

- [ ] **Step 3: 목록에서 모달을 여는 스크립트 추가**

`funding/templates/funding/admin_list.html`의 `{% block funding_content %}` 끝(`</div>` 뒤)에 추가:

```html
<script>
  // 체크박스 선택 → 버튼 활성화 → 고른 id로 전달 모달을 연다.
  document.addEventListener('change', function (e) {
    if (!e.target.classList.contains('handoff-pick')) return;
    var picked = document.querySelectorAll('.handoff-pick:checked');
    document.getElementById('handoff-count').textContent = picked.length;
    document.getElementById('handoff-open').disabled = picked.length === 0;
  });
  document.getElementById('handoff-open').addEventListener('click', function () {
    var params = new URLSearchParams();
    document.querySelectorAll('.handoff-pick:checked').forEach(function (el) {
      params.append('company_ids', el.value);
    });
    htmx.ajax('GET', '{% url "funding:handoff_form" %}?' + params.toString(),
              { target: '#modal-slot', swap: 'innerHTML' });
  });
</script>
```

- [ ] **Step 4: 화면 확인**

목록에서 2건을 체크하고 「영업자에게 전달」을 누른다.
Expected: 모달이 뜨고 본문 초안에 회사 2곳의 정보와 통화 녹음 요약이 들어 있다. 영업담당자 드롭다운에 `role=sales` 사용자만 나온다.

- [ ] **Step 5: 커밋**

```bash
git add funding/views/ funding/urls.py funding/templates/funding/
git commit -m "feat(funding): 전달 모달을 만든다"
```

---

### Task 13: 전달 생성과 메일 발송

**Files:**
- Modify: `funding/services/handoff.py`, `funding/views/handoff.py`, `funding/urls.py`
- Modify: `funding/test_handoff.py`

**Interfaces:**
- Produces:
  - `handoff.build_message(*, to_email, subject, body, attachments) -> EmailMultiAlternatives`
  - `handoff.send_handoff(links, *, to_user, body, comment, sent_by) -> list[Handoff]`
  - URL name `funding:handoff_create`

- [ ] **Step 1: 실패하는 테스트 추가**

`funding/test_handoff.py`에 이어 붙인다:

```python
from django.core import mail
from django.test import override_settings


@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
def test_message_carries_comment_above_body():
    """관리자 커멘트가 본문 맨 위에 온다 — 영업자가 먼저 읽어야 한다."""
    msg = handoff.build_message(
        to_email="sales@x.com",
        subject="기업자금 상담 전달 2건",
        body="── 1. (주)가나다 ──",
        comment="8월 초 방문 잡아주세요",
        attachments=[],
    )
    assert msg.body.index("8월 초 방문") < msg.body.index("(주)가나다")


@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
def test_message_attaches_each_file():
    msg = handoff.build_message(
        to_email="sales@x.com",
        subject="s",
        body="b",
        comment="",
        attachments=[("가나다_경영진단.xlsx", b"x"), ("라마바_경영진단.xlsx", b"y")],
    )
    assert len(msg.attachments) == 2
    assert msg.attachments[0][0] == "가나다_경영진단.xlsx"


@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
def test_message_sends_one_mail():
    mail.outbox.clear()
    handoff.build_message(
        to_email="sales@x.com", subject="s", body="b", comment="", attachments=[]
    ).send()
    assert len(mail.outbox) == 1
    assert mail.outbox[0].to == ["sales@x.com"]
```

- [ ] **Step 2: 실패 확인**

Run: `uv run pytest funding/test_handoff.py -v`
Expected: FAIL — `AttributeError: module 'funding.services.handoff' has no attribute 'build_message'`

- [ ] **Step 3: 메일 조립 구현**

`funding/services/handoff.py`에 추가:

```python
from django.conf import settings
from django.core.mail import EmailMultiAlternatives

_XLSX_CONTENT_TYPE = (
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
)


def build_message(*, to_email, subject, body, comment, attachments):
    """전달 메일 1통. 커멘트를 맨 위에 두고 회사 블록을 잇는다."""
    parts = []
    if comment:
        parts.append(f"[관리자 커멘트]\n{comment}")
    parts.append(body)
    msg = EmailMultiAlternatives(
        subject=subject,
        body="\n\n".join(parts),
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[to_email],
        reply_to=[settings.DEFAULT_FROM_EMAIL],
    )
    for filename, content in attachments:
        msg.attach(filename, content, _XLSX_CONTENT_TYPE)
    return msg
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `uv run pytest funding/test_handoff.py -v`
Expected: PASS (8 passed)

- [ ] **Step 5: 전달 생성 함수 추가**

`funding/services/handoff.py`에 이어 붙인다:

```python
def send_handoff(links, *, to_user, body, comment, sent_by):
    """전달 기록을 먼저 남기고 메일을 보낸다.

    순서가 중요하다 — 메일이 나갔는데 기록이 없으면 무엇을 보냈는지 알 수
    없다. 발송이 실패하면 기록에 사유를 남기고 목록에서 다시 보낸다.
    """
    from django.db import transaction
    from django.utils import timezone

    from funding.models import Handoff
    from funding.services import report
    from funding.views.tm import _estimate_from_facts
    from funding.services import cretop_data

    with transaction.atomic(using="ceo_loan"):
        records = Handoff.objects.bulk_create(
            [
                Handoff(
                    company=link,
                    sales_username=to_user.username,
                    sent_by=sent_by,
                    admin_comment=comment,
                    body_snapshot=body,
                )
                for link in links
            ]
        )

    attachments = []
    for link in links:
        facts = cretop_data.bulk_company_facts([link.cretop_company_id]).get(
            str(link.cretop_company_id), {}
        )
        estimate = _estimate_from_facts(facts)
        overrides = (
            {"possible_loan_amount": estimate["display_text"]} if estimate else {}
        )
        attachments.append(
            (
                f"{link.company_name}_경영진단.xlsx",
                report.build(link.cretop_company_id, overrides),
            )
        )

    message = build_message(
        to_email=to_user.email,
        subject=f"기업자금 상담 전달 {len(links)}건",
        body=body,
        comment=comment,
        attachments=attachments,
    )
    try:
        message.send(fail_silently=False)
    except Exception as exc:  # 발송 실패는 기록에 남기고 화면에 알린다
        Handoff.objects.filter(pk__in=[r.pk for r in records]).update(
            email_error=str(exc)[:5000]
        )
        return records, str(exc)

    Handoff.objects.filter(pk__in=[r.pk for r in records]).update(
        email_sent_at=timezone.now()
    )
    return records, ""
```

- [ ] **Step 6: 생성 뷰 추가**

`funding/views/handoff.py`에 추가:

```python
from django.contrib import messages
from django.shortcuts import redirect
from django.views.decorators.http import require_POST


@login_required
@require_POST
def handoff_create(request):
    require_roles(request, Role.ADMIN)
    links = _picked_links(request)
    to_user = get_user_model().objects.filter(
        username=request.POST.get("sales_username"), role=Role.SALES, is_active=True
    ).first()
    if to_user is None or not to_user.email:
        raise Http404  # 이메일 없는 영업자에게는 보낼 수 없다

    _, error = handoff_service.send_handoff(
        links,
        to_user=to_user,
        body=request.POST.get("body", ""),
        comment=request.POST.get("admin_comment", ""),
        sent_by=request.user.username,
    )
    if error:
        messages.error(request, f"전달 기록은 남았지만 메일 발송이 실패했습니다: {error}")
    else:
        messages.success(request, f"{len(links)}건을 {to_user.get_full_name() or to_user.username}님께 전달했습니다.")
    return redirect("funding:admin_list")
```

`funding/urls.py`:

```python
    path("admin/handoff/send/", views.handoff_create, name="handoff_create"),
```

- [ ] **Step 7: 메시지 표시 확인**

`templates/common/base.html`에 `{% if messages %}` 블록이 있는지 확인한다.
Run: `grep -n "messages" templates/common/base.html`
없으면 레이아웃에 아래를 추가한다 (`funding/_layout.html`의 `<h1>` 아래):

```html
{% if messages %}
{% for message in messages %}
<div class="mb-4 rounded-lg border px-4 py-2 text-sm {% if message.tags == 'error' %}border-red-300 bg-red-50 text-red-800{% else %}border-green-300 bg-green-50 text-green-800{% endif %}">
  {{ message }}
</div>
{% endfor %}
{% endif %}
```

- [ ] **Step 8: 실제 전달 확인**

영업담당자 역할 계정을 하나 만들고(이메일 포함), 관리자로 2건을 전달한다.
Run: `uv run python manage.py runserver`
Expected: 성공 메시지가 뜬다. `EMAIL_BACKEND`가 콘솔이면 터미널에 메일이 찍히고 첨부가 2개다.

- [ ] **Step 9: 커밋**

```bash
git add funding/ 
git commit -m "feat(funding): 고른 건을 영업자에게 메일로 전달한다"
```

---

### Task 14: 영업자 전달함

**Files:**
- Modify: `funding/views/handoff.py`, `funding/urls.py`
- Create: `funding/templates/funding/handoff_inbox.html`, `funding/templates/funding/_handoff_items.html`
- Test: `funding/test_inbox.py`

**Interfaces:**
- Produces: URL name `funding:handoff_inbox`

- [ ] **Step 1: 실패하는 시야 테스트 작성**

Create `funding/test_inbox.py`:

```python
"""전달함 시야 규칙 테스트.

예방 장애: 영업담당자가 남에게 전달된 건까지 봐서 다른 영업자의 고객
명단과 통화 내용을 열람하는 것.
"""

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse

from funding.models import Ceo, CeoCompany, Handoff

pytestmark = pytest.mark.django_db(databases=["default", "ceo_loan"])

Role = get_user_model().Role


def _sales(username):
    return get_user_model().objects.create_user(
        username=username, password="pw", email=f"{username}@x.com", role=Role.SALES
    )


def _handoff(sales_username, company_name):
    ceo = Ceo.objects.create(name="홍길동", phone_digits=f"0101111{len(company_name):04d}")
    link = CeoCompany.objects.create(
        ceo=ceo,
        company_name=company_name,
        business_number_digits=f"{abs(hash(company_name)) % 10**10:010d}",
        cretop_company_id="00000000-0000-0000-0000-000000000001",
    )
    return Handoff.objects.create(
        company=link, sales_username=sales_username, sent_by="admin", body_snapshot="본문"
    )


def test_sales_sees_only_own_handoffs(client):
    _handoff("mine", "(주)내건")
    _handoff("other", "(주)남의건")
    client.force_login(_sales("mine"))
    body = client.get(reverse("funding:handoff_inbox")).content.decode()
    assert "(주)내건" in body
    assert "(주)남의건" not in body


def test_admin_sees_all_handoffs(client):
    _handoff("mine", "(주)내건")
    _handoff("other", "(주)남의건")
    admin = get_user_model().objects.create_user(
        username="admin", password="pw", role=Role.ADMIN, is_staff=True
    )
    client.force_login(admin)
    body = client.get(reverse("funding:handoff_inbox")).content.decode()
    assert "(주)내건" in body
    assert "(주)남의건" in body


def test_tm_cannot_open_inbox(client):
    tm = get_user_model().objects.create_user(
        username="tm", password="pw", role=Role.TM, is_staff=True
    )
    client.force_login(tm)
    assert client.get(reverse("funding:handoff_inbox")).status_code == 403
```

- [ ] **Step 2: 실패 확인**

Run: `uv run pytest funding/test_inbox.py -v`
Expected: FAIL — `NoReverseMatch: 'handoff_inbox' is not a valid view function or pattern name`

- [ ] **Step 3: 전달함 뷰 작성**

`funding/views/handoff.py`에 추가:

```python
from common.auth import is_admin
from funding.models import Handoff

INBOX_PAGE_SIZE = 100


def _inbox_queryset(request):
    """시야 규칙: 영업담당자는 자기 건만, 관리자는 전체(읽기 전용)."""
    qs = Handoff.objects.select_related("company", "company__ceo")
    if is_admin(request.user):
        return qs, True
    return qs.filter(sales_username=request.user.username), False


@login_required
def handoff_inbox(request):
    require_roles(request, Role.SALES, Role.ADMIN)
    qs, viewer_is_admin = _inbox_queryset(request)
    status = request.GET.get("status") or ""
    if status:
        qs = qs.filter(status=status)
    return render(
        request,
        "funding/handoff_inbox.html",
        {
            "rows": list(qs[:INBOX_PAGE_SIZE]),
            "total": qs.count(),
            "viewer_is_admin": viewer_is_admin,
            "status_filter": status,
            "status_choices": Handoff.Status.choices,
        },
    )
```

`funding/urls.py`:

```python
    path("handoffs/", views.handoff_inbox, name="handoff_inbox"),
```

- [ ] **Step 4: 전달함 화면 작성**

Create `funding/templates/funding/handoff_inbox.html`:

```html
{% extends "funding/_layout.html" %}
{% block title %}전달함{% endblock %}
{% block page_title %}{% if viewer_is_admin %}전달 내역{% else %}내게 전달된 건{% endif %}{% endblock %}
{% block funding_content %}
<form class="mb-4 flex items-center gap-2">
  <select name="status" onchange="this.form.submit()"
          class="rounded-lg border border-line-strong px-3 py-1.5 text-sm">
    <option value="">상태 전체</option>
    {% for value, label in status_choices %}
    <option value="{{ value }}" {% if status_filter == value %}selected{% endif %}>{{ label }}</option>
    {% endfor %}
  </select>
  <span class="text-xs text-ink-faint">{{ total }}건</span>
</form>

<div id="handoff-items" class="flex flex-col gap-3">
  {% include "funding/_handoff_items.html" %}
</div>
{% endblock %}
```

Create `funding/templates/funding/_handoff_items.html`:

```html
{% for row in rows %}
<article class="rounded-xl border border-line bg-white p-4 shadow-sm">
  <div class="mb-2 flex items-start justify-between">
    <div>
      <h3 class="font-bold text-ink">{{ row.company.company_name }}</h3>
      <p class="text-sm text-ink-mid">{{ row.company.ceo.name }} · {{ row.company.ceo.phone_display }}</p>
    </div>
    <p class="text-xs text-ink-faint">
      {{ row.created_at|date:"Y-m-d" }} 전달{% if viewer_is_admin %} · 수신 {{ row.sales_username }}{% endif %}
      {% if row.email_error %}<span class="ml-2 text-red-600">메일 실패</span>{% endif %}
    </p>
  </div>

  {% if row.admin_comment %}
  <p class="mb-3 rounded-lg bg-accent-soft px-3 py-2 text-sm">{{ row.admin_comment }}</p>
  {% endif %}

  <details class="mb-3">
    <summary class="cursor-pointer text-xs font-semibold text-ink-mid">전달 내용 보기</summary>
    <pre class="mt-2 whitespace-pre-wrap rounded-lg bg-paper-soft p-3 text-xs">{{ row.body_snapshot }}</pre>
  </details>

  <div class="flex flex-wrap items-end gap-3">
    <a href="{% url 'funding:company_report' row.company.pk %}"
       class="rounded-lg border border-line-strong px-3 py-1.5 text-xs font-semibold text-ink-mid hover:bg-paper-soft">
      📊 경영진단 내려받기
    </a>
    {% if not viewer_is_admin %}
    <form method="post" action="{% url 'funding:handoff_update' row.pk %}"
          class="flex flex-wrap items-end gap-2">
      {% csrf_token %}
      <div>
        <label class="block text-xs text-ink-faint">상태</label>
        <select name="status" class="rounded-lg border border-line-strong px-2 py-1 text-sm">
          {% for value, label in status_choices %}
          <option value="{{ value }}" {% if row.status == value %}selected{% endif %}>{{ label }}</option>
          {% endfor %}
        </select>
      </div>
      <div>
        <label class="block text-xs text-ink-faint">다음 일정</label>
        <input type="date" name="next_due" value="{{ row.next_due|date:'Y-m-d' }}"
               class="rounded-lg border border-line-strong px-2 py-1 text-sm">
      </div>
      <div class="flex-1">
        <label class="block text-xs text-ink-faint">메모</label>
        <input type="text" name="sales_memo" value="{{ row.sales_memo }}"
               class="w-full rounded-lg border border-line-strong px-2 py-1 text-sm">
      </div>
      <button class="rounded-lg bg-accent px-3 py-1.5 text-xs font-semibold text-white">저장</button>
    </form>
    {% else %}
    <p class="text-xs text-ink-faint">
      상태 {{ row.get_status_display }}{% if row.next_due %} · 다음 {{ row.next_due|date:"m-d" }}{% endif %}
      {% if row.sales_memo %} · {{ row.sales_memo }}{% endif %}
    </p>
    {% endif %}
  </div>
</article>
{% empty %}
<p class="py-12 text-center text-sm text-ink-faint">전달된 건이 없습니다.</p>
{% endfor %}
```

- [ ] **Step 5: 시야 테스트 통과 확인**

Run: `uv run pytest funding/test_inbox.py -v`
Expected: PASS (3 passed)

- [ ] **Step 6: Task 5의 xfail 표시 제거**

`accounts/test_landing.py`에서 `funding:admin_list`·`funding:handoff_inbox` 파라미터에 붙였던 `xfail` 표시를 지운다.

Run: `uv run pytest accounts/test_landing.py -v`
Expected: 5개 파라미터 전부 PASS

- [ ] **Step 7: 커밋**

```bash
git add funding/ accounts/test_landing.py
git commit -m "feat(funding): 영업자 전달함을 만든다"
```

---

### Task 15: 영업 후속 입력

**Files:**
- Modify: `funding/views/handoff.py`, `funding/urls.py`
- Create: `funding/forms.py`에 `HandoffUpdateForm` 추가

**Interfaces:**
- Produces: URL name `funding:handoff_update`

- [ ] **Step 1: 폼 추가**

`funding/forms.py`에 추가:

```python
from funding.models import Handoff


class HandoffUpdateForm(forms.ModelForm):
    """영업담당자가 남기는 값만 받는다 — 본문·수신자·커멘트는 못 고친다."""

    class Meta:
        model = Handoff
        fields = ["status", "sales_memo", "next_due"]
```

- [ ] **Step 2: 갱신 뷰 작성**

`funding/views/handoff.py`에 추가:

```python
from funding.forms import HandoffUpdateForm


@login_required
@require_POST
def handoff_update(request, pk):
    """영업담당자의 후속 입력. 자기 건만 고칠 수 있다."""
    require_roles(request, Role.SALES)
    record = Handoff.objects.filter(
        pk=pk, sales_username=request.user.username
    ).first()
    if record is None:
        raise Http404
    form = HandoffUpdateForm(request.POST, instance=record)
    if form.is_valid():
        form.save()
        messages.success(request, "저장했습니다.")
    else:
        messages.error(request, "입력을 확인해 주세요.")
    return redirect("funding:handoff_inbox")
```

`funding/urls.py`:

```python
    path("handoffs/<uuid:pk>/", views.handoff_update, name="handoff_update"),
```

- [ ] **Step 3: 남의 건을 못 고치는지 테스트로 확인**

`funding/test_inbox.py`에 추가:

```python
def test_cannot_update_someone_elses_handoff(client):
    """pk만 바꿔 POST해도 남의 건은 못 고친다."""
    target = _handoff("other", "(주)남의건")
    client.force_login(_sales("mine"))
    response = client.post(
        reverse("funding:handoff_update", args=[target.pk]),
        {"status": Handoff.Status.WON, "sales_memo": "가로채기", "next_due": ""},
    )
    assert response.status_code == 404
    target.refresh_from_db()
    assert target.status == Handoff.Status.RECEIVED
    assert target.sales_memo == ""


def test_owner_can_update_own_handoff(client):
    record = _handoff("mine", "(주)내건")
    client.force_login(_sales("mine"))
    client.post(
        reverse("funding:handoff_update", args=[record.pk]),
        {
            "status": Handoff.Status.IN_PROGRESS,
            "sales_memo": "8/1 방문",
            "next_due": "2026-08-01",
        },
    )
    record.refresh_from_db()
    assert record.status == Handoff.Status.IN_PROGRESS
    assert record.sales_memo == "8/1 방문"
    assert str(record.next_due) == "2026-08-01"
```

Run: `uv run pytest funding/test_inbox.py -v`
Expected: PASS (5 passed)

- [ ] **Step 4: 한 바퀴 확인**

관리자 로그인 → 목록 → 모달 → 전달 → 영업자 로그인 → 전달함에서 상태 「진행중」·다음 일정·메모 저장 → 관리자 목록의 「전달」 열이 「진행중」으로 바뀐다.

- [ ] **Step 5: 전체 검증**

Run: `uv run pytest -v`
Run: `uv run ruff check`
Run: `uv run python manage.py check`
Run: `uv run python manage.py check --settings=main.settings.deploy`
Expected: 전부 통과

- [ ] **Step 6: 커밋**

```bash
git add funding/
git commit -m "feat(funding): 영업담당자가 전달 건의 결과를 남긴다"
```

---

## Self-Review 결과

**설계 문서 대비 빠진 것:** 없음. 설계 4~10절이 Task 0~15에 모두 대응한다. 5단계(구글 로그인)는 계획 범위에서 명시적으로 제외했다.

**계획 실행 중 확인이 필요한 지점:**

1. **Task 3** — `funding_agent` 테이블 이름을 `sqlmigrate`로 실제 확인한 뒤 SQL을 확정한다.
2. **Task 7** — `Handoff`가 있어야 `adminboard.py`가 import된다. Task 10을 먼저 실행해도 된다.
3. **Task 5** — `funding:admin_list`·`funding:handoff_inbox` URL이 Task 8·14에서 생기므로, 그전까지 착지 테스트 2개는 `xfail`로 둔다.
4. **Task 4 Step 7** — 기존 `funding/test_assignment.py`가 만드는 사용자에 역할이 없으면 여기서 깨진다. 깨지면 그 테스트에 `role`을 넣는다.
5. **Task 13** — 20건 전달의 실제 소요 시간을 재본다. 요청이 30초를 넘으면 `MAX_PER_HANDOFF`를 낮추거나 발송을 백그라운드 스레드로 돌린다(`marketing/services/mailer.py::send_campaign_async` 패턴).

## 다음 계획으로 넘길 것 — 구글 로그인(5단계)

정보를 받은 뒤 별도 계획으로 쓴다. 그때 반드시 다룰 것:

- **기존 계정 잇기**: 지금 TM들은 아이디로 `funding.Agent`와 묶여 있다. 구글로 가입할 때 아이디가 새로 만들어지면 같은 사람에게 담당자 기록이 두 개 생기고 배분이 쪼개진다. **이메일이 같은 기존 계정에 붙이는 처리**가 없으면 안 된다.
- **URL 순서**: `main/urls.py`에서 `accounts.urls`를 `allauth.urls`보다 먼저 등록한다. 기존 `/accounts/login/`이 이겨야 한다.
- **가입 승인 화면**: `/accounts/approvals/`. 이 계획의 `membership.approve`·`reject`를 그대로 쓴다.
- **필요한 값**: 워크스페이스 도메인, OAuth 클라이언트 ID·시크릿, 리디렉션 URI 등록.
