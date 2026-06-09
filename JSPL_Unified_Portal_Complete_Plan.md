# JSPL Unified Plant Portal — Complete Implementation Plan
## Auth + Department Hub + Module Routing (TPM, CMC, PRODUCTION, etc.)
### Stack: Django 5 + PostgreSQL + HTMX + Alpine.js

---

> **What this document covers:**
> This is the COMPLETE implementation plan for the unified JSPL portal.
> It covers the single login page (jindalsteel.in email), the plant-wide dashboard,
> the department hub with module cards (TPM, CMC, PRODUCTION, etc.),
> role-based access per module, and seamless redirect into the TPM portal
> (already built) without a second login. All other modules follow the same pattern.

---

## ARCHITECTURE OVERVIEW

```
SINGLE LOGIN (jindalsteel.in email)
         │
         ▼
PLANT-WIDE DASHBOARD (/dashboard/)
  • Summary ribbons for all active modules
  • 28 department status cards
  • Admin sees everything; user sees own dept highlighted
         │
         ├── Click Department Card
         ▼
DEPARTMENT HUB (/department/<dept_id>/)
  • Module grid: TPM | CMC | PRODUCTION | Safety | HR | ...
  • User sees only their permitted modules (others are LOCKED with padlock)
  • Admin sees all modules
         │
         ├── Click TPM (permitted)     → /department/<dept_id>/tpm/         (existing TPM portal, no re-login)
         ├── Click CMC (permitted)     → /department/<dept_id>/cmc/          (CMC dashboard)
         ├── Click PRODUCTION          → /department/<dept_id>/PRODUCTION/   (PRODUCTION dashboard)
         ├── Click 🔒 Locked module   → shows "Access Denied" tooltip, no redirect
         └── ...more modules
```

---

## PART 1 — DATABASE MODELS

### `portal/models.py` — Full Schema

```python
from django.db import models
from django.contrib.auth.models import AbstractUser


# ─────────────────────────────────────────────
# MODULE REGISTRY
# Every major portal section is a "Module"
# ─────────────────────────────────────────────

class Module(models.Model):
    """
    Represents a portal module: TPM, CMC, PRODUCTION, Safety, HR, etc.
    Created once in seed data — admin never needs to recreate.
    """
    key         = models.CharField(max_length=30, unique=True)
    # e.g. 'TPM', 'CMC', 'PRODUCTION', 'SAFETY', 'HR', 'MAINTENANCE'
    label       = models.CharField(max_length=100)
    # e.g. 'Total Productive Maintenance', 'Contract Management Cell'
    description = models.CharField(max_length=200, blank=True)
    icon        = models.CharField(max_length=50, blank=True)
    # e.g. 'gear', 'chart-bar', 'hard-hat' — maps to a CSS icon class
    color_class = models.CharField(max_length=30, blank=True)
    # e.g. 'module-tpm', 'module-cmc' — CSS class for card color theming
    url_namespace = models.CharField(max_length=100, blank=True)
    # e.g. 'tpm:dept_overview' — the named URL to redirect to when clicking
    is_active   = models.BooleanField(default=True)
    sort_order  = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ['sort_order', 'label']

    def __str__(self):
        return self.label


# ─────────────────────────────────────────────
# DEPARTMENT
# ─────────────────────────────────────────────

class Department(models.Model):
    name = models.CharField(max_length=100, unique=True)
    code = models.CharField(max_length=10,  unique=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name

    class Meta:
        ordering = ['name']


# ─────────────────────────────────────────────
# USER
# ─────────────────────────────────────────────

class User(AbstractUser):
    """
    LOGIN: email = lalit.goyal@jindalsteel.in
    username field is kept for Django admin compatibility
    but EMAIL is the login credential.
    """
    ROLE_ADMIN  = 'ADMIN'
    ROLE_USER   = 'USER'
    ROLE_CHOICES = [
        (ROLE_ADMIN, 'Plant Admin'),
        (ROLE_USER,  'Department User'),
    ]

    email        = models.EmailField(unique=True)
    # overridden to make email the unique identifier
    role         = models.CharField(max_length=10, choices=ROLE_CHOICES, default=ROLE_USER)
    department   = models.ForeignKey(
        Department, null=True, blank=True,
        on_delete=models.SET_NULL, related_name='users'
    )
    is_plant_admin = models.BooleanField(default=False)
    # Plant admin sees ALL depts + ALL modules (bypass all permission checks)
    phone        = models.CharField(max_length=20, blank=True)
    employee_id  = models.CharField(max_length=30, blank=True)
    designation  = models.CharField(max_length=100, blank=True)
    profile_photo = models.ImageField(upload_to='profiles/', null=True, blank=True)
    last_active  = models.DateTimeField(null=True, blank=True)

    USERNAME_FIELD  = 'email'
    REQUIRED_FIELDS = ['username']  # kept for createsuperuser compatibility

    def is_admin(self):
        return self.role == self.ROLE_ADMIN or self.is_plant_admin

    def get_display_name(self):
        full = self.get_full_name()
        return full if full.strip() else self.email.split('@')[0]

    def __str__(self):
        return f"{self.get_display_name()} ({self.email})"


# ─────────────────────────────────────────────
# USER ↔ DEPARTMENT ↔ MODULE PERMISSIONS
# ─────────────────────────────────────────────

class UserModuleAccess(models.Model):
    """
    Controls which modules a user can access within a department.

    A user may belong to one primary department (User.department)
    but can be granted cross-department access via this model.

    Examples:
      - Lalit Goyal (SMS-2) has TPM access → UserModuleAccess(user=lalit, dept=SMS2, module=TPM, can_edit=True)
      - Saurabh Agrawal (Plant Admin) → User.is_plant_admin=True, no individual records needed
      - A user with CMC access only in Blast Furnace-1
    """
    class AccessLevel(models.TextChoices):
        VIEW = 'VIEW', 'View Only'
        EDIT = 'EDIT', 'View + Edit'

    user         = models.ForeignKey(User, on_delete=models.CASCADE, related_name='module_access')
    department   = models.ForeignKey(Department, on_delete=models.CASCADE, related_name='module_access')
    module       = models.ForeignKey(Module, on_delete=models.CASCADE, related_name='user_access')
    access_level = models.CharField(max_length=10, choices=AccessLevel.choices, default=AccessLevel.EDIT)
    granted_by   = models.ForeignKey(
        User, null=True, blank=True,
        on_delete=models.SET_NULL, related_name='access_grants'
    )
    granted_at   = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'department', 'module')
        verbose_name = 'User Module Access'

    def __str__(self):
        return f"{self.user.email} → {self.department.code}/{self.module.key} ({self.access_level})"


# ─────────────────────────────────────────────
# AUDIT LOG (portal-level, not module-level)
# ─────────────────────────────────────────────

class AuditLog(models.Model):
    user       = models.ForeignKey(User, null=True, on_delete=models.SET_NULL)
    action     = models.CharField(max_length=100)
    # e.g. 'LOGIN', 'VIEW_DEPT', 'ACCESS_MODULE', 'LOGOUT'
    department = models.ForeignKey(Department, null=True, blank=True, on_delete=models.SET_NULL)
    module     = models.ForeignKey(Module, null=True, blank=True, on_delete=models.SET_NULL)
    detail     = models.TextField(blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    timestamp  = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-timestamp']
```

---

## PART 2 — MODULES SEED DATA

These modules are seeded once. More can be added by admin without code changes.

```python
# portal/management/commands/seed_portal.py

MODULES = [
    {
        'key': 'TPM',
        'label': 'Total Productive Maintenance',
        'description': 'KPI tracking across 8 pillars + Workstation KPIs',
        'icon': 'gear',
        'color_class': 'module-tpm',
        'url_namespace': 'tpm:dept_overview',
        'sort_order': 1,
    },
    {
        'key': 'CMC',
        'label': 'Contract Management Cell',
        'description': 'Contractor management, compliance and billing',
        'icon': 'file-contract',
        'color_class': 'module-cmc',
        'url_namespace': 'cmc:dept_overview',
        'sort_order': 2,
    },
    {
        'key': 'PRODUCTION',
        'label': 'PRODUCTION',
        'description': 'Daily PRODUCTION targets, shift reports and efficiency',
        'icon': 'industry',
        'color_class': 'module-PRODUCTION',
        'url_namespace': 'PRODUCTION:dept_overview',
        'sort_order': 3,
    },
    {
        'key': 'SAFETY',
        'label': 'Safety & Environment',
        'description': 'Incident reporting, safety observations and audits',
        'icon': 'hard-hat',
        'color_class': 'module-safety',
        'url_namespace': 'safety:dept_overview',
        'sort_order': 4,
    },
    {
        'key': 'HR',
        'label': 'Human Resources',
        'description': 'Attendance, training compliance and manpower data',
        'icon': 'users',
        'color_class': 'module-hr',
        'url_namespace': 'hr:dept_overview',
        'sort_order': 5,
    },
    {
        'key': 'MAINTENANCE',
        'label': 'Maintenance',
        'description': 'Breakdown reports, PM schedules and spare parts',
        'icon': 'wrench',
        'color_class': 'module-maintenance',
        'url_namespace': 'maintenance:dept_overview',
        'sort_order': 6,
    },
    # Add more as needed — admin can toggle is_active per module
]

DEPARTMENTS = [
    {'name': 'Blast Furnace-1',        'code': 'BF1'},
    {'name': 'Blast Furnace-2',        'code': 'BF2'},
    {'name': 'Brick Plant',            'code': 'BP'},
    {'name': 'Cement Plant',           'code': 'CP'},
    {'name': 'Coke Oven',              'code': 'CO'},
    {'name': 'DRI-1',                  'code': 'DRI1'},
    {'name': 'DRI-2',                  'code': 'DRI2'},
    {'name': 'Extrusion Plant',        'code': 'EP'},
    {'name': 'Lime and Dolo Plant',    'code': 'LDP'},
    {'name': 'Oxygen Plant',           'code': 'OP'},
    {'name': 'PGP-1',                  'code': 'PGP1'},
    {'name': 'PGP-2',                  'code': 'PGP2'},
    {'name': 'PGP-3',                  'code': 'PGP3'},
    {'name': 'Plate Mill',             'code': 'PM'},
    {'name': 'Power Plant 1',          'code': 'PP1'},
    {'name': 'Power Plant 2',          'code': 'PP2'},
    {'name': 'Power Plant 3',          'code': 'PP3'},
    {'name': 'Power Plant Phase #3',   'code': 'PPP3'},
    {'name': 'RMHS-1',                 'code': 'RMHS1'},
    {'name': 'RMHS-2',                 'code': 'RMHS2'},
    {'name': 'RMHS-3',                 'code': 'RMHS3'},
    {'name': 'Rail Mill',              'code': 'RM'},
    {'name': 'SAF-1',                  'code': 'SAF1'},
    {'name': 'SAF-2',                  'code': 'SAF2'},
    {'name': 'SMS-2',                  'code': 'SMS2'},
    {'name': 'SMS-3',                  'code': 'SMS3'},
    {'name': 'Sinter',                 'code': 'SINT'},
    {'name': 'Special Profile Mill (SPM)', 'code': 'SPM'},
]
```

---

## PART 3 — URL STRUCTURE (Complete)

```python
# jspl_portal/urls.py  (root URL conf)

from django.urls import path, include

urlpatterns = [
    # ── Portal Core ──────────────────────────────────────────
    path('',            include('portal.urls')),

    # ── Module Sub-apps ──────────────────────────────────────
    # Each module lives under its own namespace
    # The TPM app is your existing TPM portal — just namespaced
    path('tpm/',        include('tpm.urls',        namespace='tpm')),
    path('cmc/',        include('cmc.urls',         namespace='cmc')),
    path('PRODUCTION/', include('PRODUCTION.urls',  namespace='PRODUCTION')),
    path('safety/',     include('safety.urls',      namespace='safety')),
    path('hr/',         include('hr.urls',           namespace='hr')),
    # ... add more as modules are built

    # ── Django Admin ─────────────────────────────────────────
    path('django-admin/', admin.site.urls),
]
```

```python
# portal/urls.py

from django.urls import path
from portal.views import auth_views, dashboard_views, department_views, admin_views

app_name = 'portal'

urlpatterns = [
    # ── Auth ─────────────────────────────────────────────────
    path('',            auth_views.root_redirect,       name='root'),
    path('login/',      auth_views.login_view,           name='login'),
    path('logout/',     auth_views.logout_view,          name='logout'),

    # ── Plant-Wide Dashboard ──────────────────────────────────
    path('dashboard/',  dashboard_views.plant_dashboard,  name='plant_dashboard'),

    # ── Department Hub ────────────────────────────────────────
    path('department/<int:dept_id>/',
         department_views.dept_hub,                       name='dept_hub'),

    # HTMX partial: module access check before redirect
    path('department/<int:dept_id>/module/<str:module_key>/enter/',
         department_views.enter_module,                   name='enter_module'),

    # ── Portal Admin Panel ────────────────────────────────────
    path('admin/users/',            admin_views.users_list,      name='admin_users'),
    path('admin/users/add/',        admin_views.add_user,         name='admin_add_user'),
    path('admin/users/<int:uid>/edit/', admin_views.edit_user,   name='admin_edit_user'),
    path('admin/users/<int:uid>/access/', admin_views.manage_access, name='admin_access'),
    path('admin/departments/',      admin_views.departments,      name='admin_depts'),
    path('admin/audit/',            admin_views.audit_log,        name='admin_audit'),
]
```

```python
# tpm/urls.py  (your existing TPM app — add dept_id prefix)
# app_name = 'tpm'

urlpatterns = [
    # Department-scoped TPM entry point
    path('department/<int:dept_id>/',
         tpm_views.dept_overview,    name='dept_overview'),

    path('department/<int:dept_id>/pillar/<str:pillar_id>/',
         tpm_views.pillar_page,      name='pillar_page'),

    path('department/<int:dept_id>/pillar/ws-kpi/',
         tpm_views.ws_kpi_page,      name='ws_kpi_page'),

    path('department/<int:dept_id>/report/',
         tpm_views.report_page,      name='report_page'),

    # HTMX partials (unchanged from existing plan)
    path('department/<int:dept_id>/pillar/<str:pillar_id>/table/',
         tpm_views.kpi_table_partial, name='kpi_table_partial'),
    # ... rest of existing TPM URLs unchanged
]
```

---

## PART 4 — VIEWS

### `portal/views/auth_views.py`

```python
from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.views.decorators.http import require_http_methods
from django.contrib import messages
from portal.models import AuditLog


def root_redirect(request):
    """
    / → always redirects based on auth state.
    Never shows content on root URL.
    """
    if not request.user.is_authenticated:
        return redirect('portal:login')
    if request.user.is_admin():
        return redirect('portal:plant_dashboard')
    # Department user → go straight to their department hub
    if request.user.department_id:
        return redirect('portal:dept_hub', dept_id=request.user.department_id)
    return redirect('portal:plant_dashboard')


@require_http_methods(['GET', 'POST'])
def login_view(request):
    """
    THE ONE AND ONLY LOGIN PAGE for the entire portal.
    Accepts jindalsteel.in email + password.
    After login, no more authentication prompts anywhere in the portal.
    """
    if request.user.is_authenticated:
        return redirect('portal:root')

    error = None

    if request.method == 'POST':
        email    = request.POST.get('email', '').strip().lower()
        password = request.POST.get('password', '')

        # Validate email domain
        if not email.endswith('@jindalsteel.in'):
            error = 'Please use your @jindalsteel.in email address.'
        else:
            user = authenticate(request, username=email, password=password)
            # Note: USERNAME_FIELD = 'email', so Django auth uses email directly

            if user is not None and user.is_active:
                login(request, user)
                # Record audit log
                AuditLog.objects.create(
                    user=user,
                    action='LOGIN',
                    ip_address=get_client_ip(request),
                )
                # Redirect based on role
                next_url = request.GET.get('next')
                if next_url:
                    return redirect(next_url)
                return redirect('portal:root')
            else:
                error = 'Invalid email or password. Please try again.'

    return render(request, 'portal/auth/login.html', {'error': error})


def logout_view(request):
    if request.user.is_authenticated:
        AuditLog.objects.create(user=request.user, action='LOGOUT',
                                ip_address=get_client_ip(request))
    logout(request)
    return redirect('portal:login')


def get_client_ip(request):
    x_forwarded = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded:
        return x_forwarded.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR')
```

### `portal/views/dashboard_views.py`

```python
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from portal.models import Department, Module, UserModuleAccess
from portal.utils.aggregations import (
    get_plant_summary_stats,
    get_dept_status_cards,
    get_module_summary_stats,
)


@login_required
def plant_dashboard(request):
    """
    Plant-wide dashboard. Visible to all logged-in users.
    Admin sees all 28 depts. User sees all depts but their own is highlighted.
    """
    departments  = Department.objects.filter(is_active=True)
    active_modules = Module.objects.filter(is_active=True).order_by('sort_order')

    # Per-department status cards (colour-coded by overall performance)
    dept_cards = get_dept_status_cards(request.user, departments)

    # Plant-level KPI summaries per module (if module has analytics)
    module_stats = get_module_summary_stats(active_modules)

    # User's own department (for highlighting)
    user_dept = request.user.department

    context = {
        'departments':   departments,
        'active_modules': active_modules,
        'dept_cards':    dept_cards,
        'module_stats':  module_stats,
        'user_dept':     user_dept,
        'page_title':    'Plant Overview Dashboard',
    }
    return render(request, 'portal/dashboard/plant_dashboard.html', context)
```

### `portal/views/department_views.py`

```python
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.urls import reverse
from portal.models import Department, Module, UserModuleAccess
from portal.utils.access import get_user_module_access_map
from portal.utils.decorators import dept_visibility_required


@login_required
@dept_visibility_required
def dept_hub(request, dept_id):
    """
    DEPARTMENT HUB PAGE.
    Shows all active modules as cards.
    Each card is either:
      - ACCESSIBLE: clickable, shows module summary stats
      - LOCKED: grayed out with padlock icon, shows "Access Restricted" tooltip
    """
    department = get_object_or_404(Department, id=dept_id, is_active=True)
    active_modules = Module.objects.filter(is_active=True).order_by('sort_order')

    # Build access map: {module_key: access_level | None}
    access_map = get_user_module_access_map(request.user, department)

    module_cards = []
    for module in active_modules:
        access = access_map.get(module.key)  # 'VIEW', 'EDIT', or None
        module_cards.append({
            'module':     module,
            'accessible': access is not None,
            'access_level': access,
        })

    # Recent activity for this department across all modules
    from portal.models import AuditLog
    recent_activity = AuditLog.objects.filter(
        department=department
    ).select_related('user', 'module').order_by('-timestamp')[:10]

    context = {
        'department':     department,
        'module_cards':   module_cards,
        'recent_activity': recent_activity,
        'page_title':     department.name,
    }
    return render(request, 'portal/department/dept_hub.html', context)


@login_required
def enter_module(request, dept_id, module_key):
    """
    Called when a user clicks a module card.
    Checks access, logs entry, then REDIRECTS to the module's entry URL.
    This is the ONLY gate — no separate login inside any module.

    For TPM: redirects to /tpm/department/<dept_id>/
    For CMC: redirects to /cmc/department/<dept_id>/
    etc.
    """
    department = get_object_or_404(Department, id=dept_id, is_active=True)
    module     = get_object_or_404(Module, key=module_key, is_active=True)

    # Check access
    access_map = get_user_module_access_map(request.user, department)
    if module.key not in access_map and not request.user.is_admin():
        # Denied — return HTMX-friendly error or redirect to dept hub
        if request.htmx:
            return HttpResponse(
                '<div class="access-denied-toast">You do not have access to this module.</div>',
                status=403
            )
        return redirect('portal:dept_hub', dept_id=dept_id)

    # Log the module entry
    from portal.models import AuditLog
    AuditLog.objects.create(
        user=request.user,
        action='ACCESS_MODULE',
        department=department,
        module=module,
        ip_address=request.META.get('REMOTE_ADDR'),
    )

    # Resolve module URL and redirect
    # url_namespace e.g. 'tpm:dept_overview' → reverse('tpm:dept_overview', kwargs={'dept_id': dept_id})
    namespace, view_name = module.url_namespace.split(':')
    target_url = reverse(f'{namespace}:{view_name}', kwargs={'dept_id': dept_id})
    return redirect(target_url)
```

### `portal/utils/access.py`

```python
from portal.models import UserModuleAccess


def get_user_module_access_map(user, department) -> dict:
    """
    Returns dict: {module_key: access_level}
    For plant admins, returns all modules with 'EDIT' access.
    """
    if user.is_admin():
        from portal.models import Module
        return {m.key: 'EDIT' for m in Module.objects.filter(is_active=True)}

    records = UserModuleAccess.objects.filter(
        user=user,
        department=department,
    ).select_related('module')

    return {r.module.key: r.access_level for r in records}


def user_can_access_module(user, department, module_key) -> bool:
    access_map = get_user_module_access_map(user, department)
    return module_key in access_map


def user_can_edit_module(user, department, module_key) -> bool:
    access_map = get_user_module_access_map(user, department)
    return access_map.get(module_key) == 'EDIT'
```

### `portal/utils/decorators.py`

```python
from functools import wraps
from django.shortcuts import redirect, get_object_or_404
from portal.models import Department


def dept_visibility_required(view_func):
    """
    Ensures the user can VIEW a department page.
    Admin → always yes.
    User → must be their own dept OR have any module access in that dept.
    """
    @wraps(view_func)
    def wrapper(request, dept_id, *args, **kwargs):
        if request.user.is_admin():
            return view_func(request, dept_id, *args, **kwargs)

        # User's own primary dept
        if request.user.department_id == int(dept_id):
            return view_func(request, dept_id, *args, **kwargs)

        # Cross-dept access? (has any module access there)
        from portal.models import UserModuleAccess
        has_any = UserModuleAccess.objects.filter(
            user=request.user,
            department_id=dept_id
        ).exists()
        if has_any:
            return view_func(request, dept_id, *args, **kwargs)

        return redirect('portal:plant_dashboard')
    return wrapper


def module_access_required(module_key, require_edit=False):
    """
    Decorator for views inside module sub-apps (TPM, CMC, etc.)
    Checks UserModuleAccess — no separate login.
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, dept_id, *args, **kwargs):
            from portal.utils.access import (
                user_can_access_module, user_can_edit_module
            )
            from portal.models import Department
            department = get_object_or_404(Department, id=dept_id)

            if require_edit:
                allowed = user_can_edit_module(request.user, department, module_key)
            else:
                allowed = user_can_access_module(request.user, department, module_key)

            if not allowed:
                return redirect('portal:dept_hub', dept_id=dept_id)
            return view_func(request, dept_id, *args, **kwargs)
        return wrapper
    return decorator
```

---

## PART 5 — TEMPLATES

### `portal/templates/portal/auth/login.html`

```html
{% load static %}
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>JSPL Plant Portal — Login</title>
  <link href="https://fonts.googleapis.com/css2?family=Sora:wght@300;400;600;700&family=JetBrains+Mono:wght@400;600&display=swap" rel="stylesheet">
  <link rel="stylesheet" href="{% static 'portal/css/portal.css' %}">
</head>
<body class="login-page">

  <div class="login-split">

    <!-- LEFT PANEL: Branding -->
    <div class="login-brand-panel">
      <div class="login-brand-content">
        <img src="{% static 'portal/img/jspl_logo.png' %}" alt="JSPL" class="login-logo">
        <h1 class="login-brand-title">Jindal Steel &amp; Power</h1>
        <p class="login-brand-sub">RGH Plant — Integrated Operations Portal</p>
        <div class="login-modules-preview">
          <!-- Shows small icons of available modules as a teaser -->
          <span class="module-chip">TPM</span>
          <span class="module-chip">CMC</span>
          <span class="module-chip">PRODUCTION</span>
          <span class="module-chip">Safety</span>
          <span class="module-chip">HR</span>
          <span class="module-chip">+more</span>
        </div>
      </div>
    </div>

    <!-- RIGHT PANEL: Login Form -->
    <div class="login-form-panel">
      <div class="login-form-card">
        <h2 class="login-form-title">Sign In</h2>
        <p class="login-form-subtitle">Use your @jindalsteel.in email</p>

        {% if error %}
          <div class="login-error">
            <span class="icon">⚠</span> {{ error }}
          </div>
        {% endif %}

        <form method="post" action="{% url 'portal:login' %}{% if request.GET.next %}?next={{ request.GET.next }}{% endif %}">
          {% csrf_token %}

          <div class="form-group">
            <label for="email">Email Address</label>
            <input type="email" id="email" name="email"
                   placeholder="name.surname@jindalsteel.in"
                   autocomplete="email" required autofocus
                   value="{{ request.POST.email|default:'' }}">
          </div>

          <div class="form-group">
            <label for="password">Password</label>
            <div class="password-wrapper" x-data="{ show: false }">
              <input :type="show ? 'text' : 'password'"
                     id="password" name="password"
                     placeholder="Enter your password"
                     autocomplete="current-password" required>
              <button type="button" class="toggle-password"
                      @click="show = !show"
                      :aria-label="show ? 'Hide password' : 'Show password'">
                <span x-text="show ? '🙈' : '👁'"></span>
              </button>
            </div>
          </div>

          <button type="submit" class="btn-login">
            Sign In to Portal
          </button>
        </form>

        <p class="login-help">
          Trouble signing in? Contact IT: <a href="mailto:it-helpdesk@jindalsteel.in">it-helpdesk@jindalsteel.in</a>
        </p>
      </div>
    </div>

  </div>

  <!-- Alpine.js for password show/hide only — no other JS needed on login page -->
  <script src="https://unpkg.com/alpinejs@3.14.1/dist/cdn.min.js" defer></script>
</body>
</html>
```

### `portal/templates/portal/base.html` (Shell for all portal pages)

```html
{% load static portal_tags %}
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{% block title %}JSPL Portal{% endblock %}</title>
  <link href="https://fonts.googleapis.com/css2?family=Sora:wght@300;400;600;700&family=JetBrains+Mono:wght@400;600&display=swap" rel="stylesheet">
  <link rel="stylesheet" href="{% static 'portal/css/portal.css' %}">
  {% block extra_css %}{% endblock %}
</head>
<body x-data="portalShell()">

  <!-- ── TOPBAR ─────────────────────────────────────────────── -->
  <header id="portal-topbar">
    <div class="topbar-left">
      <!-- Hamburger (mobile) -->
      <button class="sidebar-toggle" @click="sidebarOpen = !sidebarOpen" aria-label="Toggle menu">☰</button>
      <img src="{% static 'portal/img/jspl_logo.png' %}" alt="JSPL" class="topbar-logo">
      <span class="topbar-title">Plant Portal</span>
    </div>

    <!-- Breadcrumb -->
    <nav class="topbar-breadcrumb" aria-label="Breadcrumb">
      <a href="{% url 'portal:plant_dashboard' %}">🏭 Plant</a>
      {% block breadcrumb_items %}{% endblock %}
    </nav>

    <div class="topbar-right">
      <!-- Active module indicator (shown when inside a module) -->
      {% block module_badge %}{% endblock %}

      <!-- User menu -->
      <div class="user-menu" x-data="{ open: false }" @click.outside="open = false">
        <button class="user-menu-trigger" @click="open = !open">
          <span class="user-avatar">{{ request.user.get_display_name|first|upper }}</span>
          <span class="user-name">{{ request.user.get_display_name }}</span>
          <span>▾</span>
        </button>
        <div class="user-dropdown" x-show="open" x-transition>
          <div class="user-dropdown-header">
            <strong>{{ request.user.get_full_name }}</strong>
            <small>{{ request.user.email }}</small>
            {% if request.user.department %}
              <small>{{ request.user.department.name }}</small>
            {% endif %}
          </div>
          {% if request.user.is_admin %}
            <a href="{% url 'portal:admin_users' %}">⚙ Admin Panel</a>
          {% endif %}
          <a href="{% url 'portal:logout' %}">↩ Sign Out</a>
        </div>
      </div>
    </div>
  </header>

  <!-- ── MAIN SHELL ──────────────────────────────────────────── -->
  <div id="portal-shell" :class="{ 'sidebar-collapsed': !sidebarOpen }">

    <!-- ── SIDEBAR ──────────────────────────────────────────── -->
    <aside id="portal-sidebar"
           x-show="sidebarOpen || !isMobile"
           x-transition:enter="sidebar-slide-in"
           data-active-dept="{{ active_dept_id|default:'' }}">

      <!-- Plant overview link -->
      <a href="{% url 'portal:plant_dashboard' %}"
         class="sidebar-link {% if active_section == 'dashboard' %}active{% endif %}">
        <span class="sidebar-icon">🏭</span> Plant Overview
      </a>

      <div class="sidebar-divider">Departments</div>

      <!-- Department accordion list -->
      {% for dept in sidebar_departments %}
        <div class="sidebar-dept-group"
             x-data="{ open: {{ dept.id }} == {{ active_dept_id|default:0 }} }">

          <button class="sidebar-dept-btn" @click="open = !open">
            <span class="dept-code">{{ dept.code }}</span>
            <span class="dept-name">{{ dept.name }}</span>
            <span class="sidebar-chevron" :class="{ 'rotated': open }">›</span>
          </button>

          <div class="sidebar-dept-modules" x-show="open" x-transition>
            <!-- Module links for this dept -->
            {% get_user_modules request.user dept as dept_modules %}
            {% for item in dept_modules %}
              {% if item.accessible %}
                <a href="{% url 'portal:enter_module' dept.id item.module.key %}"
                   class="sidebar-module-link {% if active_dept_id == dept.id and active_module == item.module.key %}active{% endif %}">
                  <span class="module-icon-sm">{{ item.module.icon }}</span>
                  {{ item.module.key }}
                </a>
              {% else %}
                <span class="sidebar-module-link locked" title="Access Restricted">
                  🔒 {{ item.module.key }}
                </span>
              {% endif %}
            {% endfor %}
          </div>
        </div>
      {% endfor %}

      {% if request.user.is_admin %}
        <div class="sidebar-divider">Admin</div>
        <a href="{% url 'portal:admin_users' %}" class="sidebar-link">👥 Users</a>
        <a href="{% url 'portal:admin_depts' %}" class="sidebar-link">🏗 Departments</a>
        <a href="{% url 'portal:admin_audit' %}" class="sidebar-link">📋 Audit Log</a>
      {% endif %}
    </aside>

    <!-- ── CONTENT ─────────────────────────────────────────── -->
    <main id="portal-content">
      <!-- Toast notifications (HTMX OOB target) -->
      <div id="toast-container" aria-live="polite"></div>
      {% block content %}{% endblock %}
    </main>
  </div>

  <!-- Scripts -->
  <script src="https://unpkg.com/htmx.org@1.9.12"></script>
  <script src="https://unpkg.com/alpinejs@3.14.1/dist/cdn.min.js" defer></script>
  <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.3/dist/chart.umd.min.js"></script>
  <script src="{% static 'portal/js/portal.js' %}"></script>
  {% block extra_js %}{% endblock %}
</body>
</html>
```

### `portal/templates/portal/dashboard/plant_dashboard.html`

```html
{% extends 'portal/base.html' %}
{% block title %}Plant Overview — JSPL Portal{% endblock %}

{% block content %}
<div class="page-header">
  <h1 class="page-title">Plant Overview Dashboard</h1>
  <p class="page-subtitle">RGH Plant — All Departments & Modules</p>
  <!-- Month/Year selector (HTMX refreshes summary cards) -->
  <div class="period-selector">
    <select name="month" hx-get="{% url 'portal:plant_dashboard' %}"
            hx-target="#plant-summary-section" hx-push-url="false">
      {% for m in months %}<option value="{{ m.num }}" {% if m.num == current_month %}selected{% endif %}>{{ m.label }}</option>{% endfor %}
    </select>
    <select name="year" hx-get="{% url 'portal:plant_dashboard' %}"
            hx-target="#plant-summary-section" hx-push-url="false">
      {% for y in years %}<option {% if y == current_year %}selected{% endif %}>{{ y }}</option>{% endfor %}
    </select>
  </div>
</div>

<!-- ── Section 1: Module Summary Ribbon ─────────────────────── -->
<section id="plant-summary-section">
  <div class="summary-ribbon">
    {% for stat in module_stats %}
    <div class="summary-card module-card-{{ stat.module.key|lower }}">
      <div class="summary-card-icon">{{ stat.module.icon }}</div>
      <div class="summary-card-body">
        <div class="summary-label">{{ stat.module.label }}</div>
        <div class="summary-value mono">{{ stat.headline_value }}</div>
        <div class="summary-sub">{{ stat.headline_label }}</div>
      </div>
      <div class="summary-card-status badge-{{ stat.status }}">{{ stat.status|upper }}</div>
    </div>
    {% endfor %}
  </div>
</section>

<!-- ── Section 2: Department Status Grid ────────────────────── -->
<section class="section">
  <h2 class="section-title">Department Status</h2>
  <div class="dept-grid">
    {% for card in dept_cards %}
    <a href="{% url 'portal:dept_hub' card.dept.id %}"
       class="dept-card {% if user_dept and card.dept.id == user_dept.id %}dept-card--mine{% endif %} status-border-{{ card.status }}">
      <div class="dept-card-header">
        <span class="dept-code-badge">{{ card.dept.code }}</span>
        <span class="dept-status-badge badge-{{ card.status }}">{{ card.status_label }}</span>
      </div>
      <div class="dept-name">{{ card.dept.name }}</div>
      <div class="dept-modules-row">
        {% for mod in card.accessible_modules %}
          <span class="dept-module-chip chip-{{ mod.key|lower }}">{{ mod.key }}</span>
        {% endfor %}
      </div>
      <!-- Mini sparkline chart (last 6 months overall score) -->
      <canvas class="dept-sparkline" data-values="{{ card.sparkline_json }}"></canvas>
    </a>
    {% endfor %}
  </div>
</section>

<!-- ── Section 3: Quick Access — My Department ──────────────── -->
{% if user_dept %}
<section class="section">
  <h2 class="section-title">My Department — {{ user_dept.name }}</h2>
  <div class="my-dept-modules">
    {% for item in my_module_cards %}
      {% if item.accessible %}
        <a href="{% url 'portal:enter_module' user_dept.id item.module.key %}"
           class="my-module-card color-{{ item.module.color_class }}">
          <span class="my-module-icon">{{ item.module.icon }}</span>
          <span class="my-module-label">{{ item.module.label }}</span>
          <span class="my-module-key">{{ item.module.key }}</span>
          <span class="my-module-arrow">→</span>
        </a>
      {% else %}
        <div class="my-module-card locked">
          <span class="my-module-icon">🔒</span>
          <span class="my-module-label">{{ item.module.label }}</span>
          <span class="my-module-key">{{ item.module.key }}</span>
          <span class="my-module-locked-msg">Access Restricted</span>
        </div>
      {% endif %}
    {% endfor %}
  </div>
</section>
{% endif %}
{% endblock %}
```

### `portal/templates/portal/department/dept_hub.html`

```html
{% extends 'portal/base.html' %}
{% block title %}{{ department.name }} — JSPL Portal{% endblock %}

{% block breadcrumb_items %}
  <span class="breadcrumb-sep">›</span>
  <span class="breadcrumb-current">{{ department.name }}</span>
{% endblock %}

{% block content %}
<div class="page-header">
  <div class="dept-hub-header">
    <div>
      <span class="dept-hub-code">{{ department.code }}</span>
      <h1 class="page-title">{{ department.name }}</h1>
      <p class="page-subtitle">Select a module to access its dashboard</p>
    </div>
    {% if request.user.is_admin %}
      <div class="dept-hub-admin-actions">
        <a href="{% url 'portal:admin_access' %}" class="btn-secondary">Manage Access</a>
      </div>
    {% endif %}
  </div>
</div>

<!-- ── Module Cards Grid ──────────────────────────────────────── -->
<div class="module-grid">
  {% for item in module_cards %}
    {% if item.accessible %}
      <!-- ACCESSIBLE MODULE CARD — full click through -->
      <a href="{% url 'portal:enter_module' department.id item.module.key %}"
         class="module-card module-card--accessible {{ item.module.color_class }}">
        <div class="module-card-icon">
          {% include "portal/partials/_module_icon.html" with key=item.module.key %}
        </div>
        <div class="module-card-body">
          <h3 class="module-card-title">{{ item.module.key }}</h3>
          <p class="module-card-label">{{ item.module.label }}</p>
          <p class="module-card-desc">{{ item.module.description }}</p>
        </div>
        <div class="module-card-footer">
          <span class="access-badge badge-{{ item.access_level|lower }}">
            {{ item.access_level|title }}
          </span>
          <span class="module-card-cta">Open →</span>
        </div>
      </a>

    {% else %}
      <!-- LOCKED MODULE CARD — visually distinct, no click -->
      <div class="module-card module-card--locked"
           x-data="{ tooltip: false }"
           @mouseenter="tooltip = true"
           @mouseleave="tooltip = false">
        <div class="module-card-icon locked-icon">🔒</div>
        <div class="module-card-body">
          <h3 class="module-card-title muted">{{ item.module.key }}</h3>
          <p class="module-card-label muted">{{ item.module.label }}</p>
          <p class="module-card-desc muted">{{ item.module.description }}</p>
        </div>
        <div class="module-card-footer">
          <span class="locked-label">Access Restricted</span>
        </div>
        <!-- Tooltip -->
        <div class="locked-tooltip" x-show="tooltip" x-transition>
          You don't have access to {{ item.module.label }}.<br>
          Contact your administrator.
        </div>
      </div>
    {% endif %}
  {% endfor %}
</div>

<!-- ── Recent Activity ───────────────────────────────────────── -->
{% if recent_activity %}
<section class="section">
  <h2 class="section-title">Recent Activity — {{ department.name }}</h2>
  <table class="activity-table">
    <thead>
      <tr><th>User</th><th>Action</th><th>Module</th><th>Time</th></tr>
    </thead>
    <tbody>
      {% for log in recent_activity %}
      <tr>
        <td>{{ log.user.get_display_name }}</td>
        <td>{{ log.action }}</td>
        <td>{{ log.module.key|default:"—" }}</td>
        <td>{{ log.timestamp|timesince }} ago</td>
      </tr>
      {% endfor %}
    </tbody>
  </table>
</section>
{% endif %}
{% endblock %}
```

---

## PART 6 — TPM INTEGRATION (No Second Login)

The existing TPM portal needs these changes to plug into the unified portal:

### 6.1 — Extend TPM base template

```html
{# tpm/templates/tpm/base_tpm.html — extends portal shell #}
{% extends 'portal/base.html' %}
{% load static %}

{% block title %}TPM — {{ department.name }} — JSPL Portal{% endblock %}

{% block breadcrumb_items %}
  <span class="breadcrumb-sep">›</span>
  <a href="{% url 'portal:dept_hub' department.id %}">{{ department.name }}</a>
  <span class="breadcrumb-sep">›</span>
  <span class="breadcrumb-current">TPM</span>
  {% block tpm_breadcrumb %}{% endblock %}
{% endblock %}

{% block module_badge %}
  <span class="active-module-badge module-tpm">⚙ TPM</span>
{% endblock %}

{# TPM-specific sidebar addition (pillar list) is inserted into the portal sidebar
   by overriding the sidebar_extra block #}
{% block extra_css %}
  <link rel="stylesheet" href="{% static 'tpm/css/tpm.css' %}">
{% endblock %}
```

### 6.2 — Remove TPM login entirely

**DELETE** any TPM-specific login view, login URL, and login template.

The `@login_required` decorator on TPM views now points to the **portal login** (`LOGIN_URL = '/login/'`), which is the unified login. Once a user is logged in from the portal login page, they are authenticated for all modules including TPM.

### 6.3 — Add TPM module access check

All TPM views get the `@module_access_required('TPM')` decorator instead of any TPM-specific auth:

```python
# tpm/views/pillar_views.py

from portal.utils.decorators import module_access_required
from django.contrib.auth.decorators import login_required

@login_required
@module_access_required('TPM')   # ← replaces any old TPM-specific auth
def dept_overview(request, dept_id):
    ...

@login_required
@module_access_required('TPM')
def pillar_page(request, dept_id, pillar_id):
    ...
```

### 6.4 — TPM "Back to Department" button

Every TPM page gets a back button in the topbar/breadcrumb:

```html
{# Already handled by the breadcrumb in base_tpm.html #}
{# The dept name in breadcrumb links back to the dept hub #}
<a href="{% url 'portal:dept_hub' department.id %}">{{ department.name }}</a>
```

---

## PART 7 — SETTINGS (Key Changes)

```python
# jspl_portal/settings.py

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django_htmx',
    'crispy_forms',
    'crispy_bootstrap5',
    # Portal apps
    'portal',    # ← core portal: auth, dept hub, access control
    'tpm',       # ← existing TPM app
    'cmc',       # ← CMC app (stub initially)
    'PRODUCTION',
    'safety',
    'hr',
]

# Custom user model lives in portal app
AUTH_USER_MODEL = 'portal.User'

# LOGIN_URL must point to portal login — all @login_required decorators
# across ALL apps redirect here
LOGIN_URL = '/login/'
LOGIN_REDIRECT_URL = '/'  # root_redirect handles the rest

SESSION_COOKIE_AGE = 28800         # 8 hours
SESSION_EXPIRE_AT_BROWSER_CLOSE = False
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SECURE = True        # PRODUCTION — set False in development
SESSION_COOKIE_SAMESITE = 'Lax'

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'django_htmx.middleware.HtmxMiddleware',
    'portal.middleware.UpdateLastActiveMiddleware',  # tracks last_active on User
]

# Template context processors — makes sidebar_departments available everywhere
TEMPLATES = [{
    ...
    'OPTIONS': {
        'context_processors': [
            ...
            'portal.context_processors.sidebar_context',
            # Injects: sidebar_departments, active_dept_id, active_module
        ],
    },
}]
```

### Context Processor

```python
# portal/context_processors.py

from portal.models import Department
from portal.utils.access import get_user_module_access_map


def sidebar_context(request):
    """
    Injected into every template automatically.
    Provides sidebar_departments and current active state.
    """
    if not request.user.is_authenticated:
        return {}

    departments = Department.objects.filter(is_active=True).order_by('name')

    # Determine active dept from URL kwargs (set by middleware or view)
    active_dept_id = getattr(request, 'active_dept_id', None)
    active_module  = getattr(request, 'active_module', None)

    return {
        'sidebar_departments': departments,
        'active_dept_id':      active_dept_id,
        'active_module':       active_module,
        'portal_user':         request.user,
    }
```

---

## PART 8 — CSS (JSPL Brand + Portal Layout)

```css
/* portal/static/portal/css/portal.css */

/* ── JSPL Brand Tokens ──────────────────────────────────── */
:root {
  --jspl-navy:    #003478;
  --jspl-blue:    #0057A8;
  --jspl-orange:  #F47920;
  --jspl-light:   #E8F0FA;
  --jspl-white:   #FFFFFF;
  --jspl-gray:    #F4F6F9;
  --jspl-border:  #D1DCF0;
  --jspl-text:    #1A2640;
  --jspl-muted:   #6B7A99;

  /* Status */
  --green:  #16A34A;
  --amber:  #D97706;
  --red:    #DC2626;
  --blue:   #2563EB;

  /* Module accent colors */
  --tpm-color:        #0057A8;
  --cmc-color:        #7C3AED;
  --PRODUCTION-color: #D97706;
  --safety-color:     #DC2626;
  --hr-color:         #059669;
  --maintenance-color:#64748B;

  /* Layout */
  --topbar-h:   60px;
  --sidebar-w:  240px;
}

/* ── Login Page ─────────────────────────────────────────── */
.login-page { margin: 0; background: var(--jspl-gray); }

.login-split {
  display: grid;
  grid-template-columns: 1fr 1fr;
  min-height: 100vh;
}

.login-brand-panel {
  background: var(--jspl-navy);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 3rem;
}

.login-brand-content { color: white; text-align: center; }
.login-logo { width: 160px; margin-bottom: 1.5rem; }
.login-brand-title { font-family: 'Sora', sans-serif; font-size: 1.8rem; font-weight: 700; margin-bottom: 0.5rem; }
.login-brand-sub { font-family: 'Sora', sans-serif; opacity: 0.75; margin-bottom: 2rem; }

.login-modules-preview { display: flex; flex-wrap: wrap; gap: 0.5rem; justify-content: center; }
.module-chip {
  background: rgba(255,255,255,0.15);
  border: 1px solid rgba(255,255,255,0.3);
  color: white;
  padding: 0.25rem 0.75rem;
  border-radius: 999px;
  font-size: 0.8rem;
  font-family: 'Sora', sans-serif;
}

.login-form-panel {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 3rem;
}

.login-form-card {
  width: 100%;
  max-width: 420px;
}

.login-form-title { font-family: 'Sora', sans-serif; font-size: 1.8rem; color: var(--jspl-text); margin-bottom: 0.25rem; }
.login-form-subtitle { color: var(--jspl-muted); margin-bottom: 2rem; }

.login-error {
  background: #FEF2F2;
  border: 1px solid #FECACA;
  color: var(--red);
  padding: 0.75rem 1rem;
  border-radius: 8px;
  margin-bottom: 1.5rem;
}

.form-group { margin-bottom: 1.25rem; }
.form-group label { display: block; font-weight: 600; color: var(--jspl-text); margin-bottom: 0.4rem; font-size: 0.9rem; }
.form-group input {
  width: 100%; padding: 0.7rem 1rem;
  border: 1px solid var(--jspl-border);
  border-radius: 8px;
  font-size: 1rem;
  transition: border-color 0.2s;
  box-sizing: border-box;
}
.form-group input:focus { outline: none; border-color: var(--jspl-blue); box-shadow: 0 0 0 3px rgba(0,87,168,0.15); }

.password-wrapper { position: relative; }
.password-wrapper input { padding-right: 3rem; }
.toggle-password {
  position: absolute; right: 0.75rem; top: 50%; transform: translateY(-50%);
  background: none; border: none; cursor: pointer;
}

.btn-login {
  width: 100%;
  background: var(--jspl-navy);
  color: white;
  border: none;
  padding: 0.85rem;
  border-radius: 8px;
  font-size: 1rem;
  font-family: 'Sora', sans-serif;
  font-weight: 600;
  cursor: pointer;
  transition: background 0.2s;
}
.btn-login:hover { background: var(--jspl-blue); }

.login-help { margin-top: 1.5rem; font-size: 0.85rem; color: var(--jspl-muted); text-align: center; }
.login-help a { color: var(--jspl-blue); }

/* ── Shell Layout ───────────────────────────────────────── */
#portal-topbar {
  position: sticky; top: 0; z-index: 100;
  height: var(--topbar-h);
  background: var(--jspl-white);
  border-bottom: 1px solid var(--jspl-border);
  display: flex; align-items: center; justify-content: space-between;
  padding: 0 1.5rem;
  box-shadow: 0 1px 4px rgba(0,0,0,0.08);
}

.topbar-left { display: flex; align-items: center; gap: 1rem; }
.topbar-logo { height: 36px; }
.topbar-title { font-family: 'Sora', sans-serif; font-weight: 700; color: var(--jspl-navy); font-size: 1.1rem; }

.topbar-breadcrumb {
  display: flex; align-items: center; gap: 0.5rem;
  font-size: 0.9rem; color: var(--jspl-muted);
}
.topbar-breadcrumb a { color: var(--jspl-blue); text-decoration: none; }
.breadcrumb-sep { opacity: 0.4; }
.breadcrumb-current { color: var(--jspl-text); font-weight: 600; }

.topbar-right { display: flex; align-items: center; gap: 1rem; }

.active-module-badge {
  padding: 0.25rem 0.75rem;
  border-radius: 6px;
  font-size: 0.8rem;
  font-weight: 700;
  font-family: 'Sora', sans-serif;
}
.active-module-badge.module-tpm { background: var(--jspl-light); color: var(--jspl-blue); }

.user-menu { position: relative; }
.user-menu-trigger {
  display: flex; align-items: center; gap: 0.5rem;
  background: none; border: 1px solid var(--jspl-border);
  padding: 0.4rem 0.75rem;
  border-radius: 8px; cursor: pointer;
}
.user-avatar {
  width: 28px; height: 28px; border-radius: 50%;
  background: var(--jspl-navy); color: white;
  display: flex; align-items: center; justify-content: center;
  font-size: 0.75rem; font-weight: 700;
}
.user-name { font-size: 0.9rem; color: var(--jspl-text); font-weight: 600; }

.user-dropdown {
  position: absolute; right: 0; top: 110%;
  background: white; border: 1px solid var(--jspl-border);
  border-radius: 10px; min-width: 220px;
  box-shadow: 0 8px 24px rgba(0,0,0,0.12);
  z-index: 200; overflow: hidden;
}
.user-dropdown-header { padding: 1rem; border-bottom: 1px solid var(--jspl-border); }
.user-dropdown-header strong { display: block; font-size: 0.9rem; color: var(--jspl-text); }
.user-dropdown-header small { display: block; font-size: 0.78rem; color: var(--jspl-muted); }
.user-dropdown a { display: block; padding: 0.65rem 1rem; color: var(--jspl-text); text-decoration: none; font-size: 0.9rem; }
.user-dropdown a:hover { background: var(--jspl-gray); }

#portal-shell {
  display: grid;
  grid-template-columns: var(--sidebar-w) 1fr;
  height: calc(100vh - var(--topbar-h));
}

#portal-sidebar {
  background: var(--jspl-navy);
  overflow-y: auto;
  padding: 1rem 0;
}

.sidebar-link {
  display: flex; align-items: center; gap: 0.75rem;
  padding: 0.65rem 1.25rem;
  color: rgba(255,255,255,0.75);
  text-decoration: none;
  font-size: 0.88rem;
  transition: background 0.15s, color 0.15s;
}
.sidebar-link:hover, .sidebar-link.active {
  background: rgba(255,255,255,0.1);
  color: white;
  border-left: 3px solid var(--jspl-orange);
}

.sidebar-divider {
  padding: 0.75rem 1.25rem 0.25rem;
  font-size: 0.7rem;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: rgba(255,255,255,0.35);
}

.sidebar-dept-btn {
  width: 100%; background: none; border: none;
  display: flex; align-items: center; gap: 0.5rem;
  padding: 0.6rem 1.25rem;
  color: rgba(255,255,255,0.75);
  cursor: pointer; text-align: left; font-size: 0.85rem;
}
.sidebar-dept-btn:hover { background: rgba(255,255,255,0.07); color: white; }
.dept-code { font-family: 'JetBrains Mono', monospace; font-size: 0.75rem; background: rgba(255,255,255,0.15); padding: 0.1rem 0.4rem; border-radius: 4px; flex-shrink: 0; }
.dept-name { flex: 1; }
.sidebar-chevron { transition: transform 0.2s; }
.sidebar-chevron.rotated { transform: rotate(90deg); }

.sidebar-dept-modules { padding-left: 1rem; }
.sidebar-module-link {
  display: block;
  padding: 0.45rem 1rem;
  font-size: 0.82rem;
  color: rgba(255,255,255,0.6);
  text-decoration: none;
  border-left: 2px solid transparent;
}
.sidebar-module-link:hover { color: white; border-left-color: var(--jspl-orange); }
.sidebar-module-link.active { color: white; border-left-color: var(--jspl-orange); font-weight: 600; }
.sidebar-module-link.locked { color: rgba(255,255,255,0.3); cursor: not-allowed; }

#portal-content { overflow-y: auto; background: var(--jspl-gray); }

/* ── Module Grid (Dept Hub) ─────────────────────────────── */
.module-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 1.5rem;
  padding: 1.5rem;
}

.module-card {
  background: white;
  border: 1px solid var(--jspl-border);
  border-radius: 12px;
  padding: 1.5rem;
  text-decoration: none;
  display: flex;
  flex-direction: column;
  gap: 1rem;
  transition: box-shadow 0.2s, transform 0.15s;
  position: relative;
  overflow: hidden;
}

/* Colored top border per module */
.module-tpm    { border-top: 4px solid var(--tpm-color); }
.module-cmc    { border-top: 4px solid var(--cmc-color); }
.module-PRODUCTION { border-top: 4px solid var(--PRODUCTION-color); }
.module-safety { border-top: 4px solid var(--safety-color); }
.module-hr     { border-top: 4px solid var(--hr-color); }
.module-maintenance { border-top: 4px solid var(--maintenance-color); }

.module-card--accessible:hover {
  box-shadow: 0 8px 24px rgba(0,0,0,0.12);
  transform: translateY(-2px);
}

.module-card--locked {
  opacity: 0.6;
  cursor: not-allowed;
  background: var(--jspl-gray);
}

.module-card-icon { font-size: 2rem; }
.locked-icon { filter: grayscale(1); }

.module-card-title { font-family: 'Sora', sans-serif; font-size: 1.1rem; font-weight: 700; color: var(--jspl-text); margin: 0; }
.module-card-label { font-size: 0.85rem; color: var(--jspl-muted); margin: 0.2rem 0 0; }
.module-card-desc { font-size: 0.82rem; color: var(--jspl-muted); line-height: 1.4; margin: 0; }
.muted { color: var(--jspl-muted) !important; }

.module-card-footer { display: flex; justify-content: space-between; align-items: center; margin-top: auto; }
.module-card-cta { color: var(--jspl-blue); font-weight: 600; font-size: 0.9rem; }
.locked-label { font-size: 0.82rem; color: var(--jspl-muted); }

.locked-tooltip {
  position: absolute; bottom: 100%; left: 50%; transform: translateX(-50%);
  background: var(--jspl-text); color: white;
  padding: 0.5rem 0.75rem; border-radius: 6px;
  font-size: 0.8rem; white-space: nowrap; pointer-events: none;
  box-shadow: 0 4px 12px rgba(0,0,0,0.2);
  margin-bottom: 0.5rem;
}

/* ── Department Status Grid (Plant Dashboard) ─────────────── */
.dept-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: 1rem;
  padding: 1rem 1.5rem 1.5rem;
}

.dept-card {
  background: white;
  border: 1px solid var(--jspl-border);
  border-radius: 10px;
  padding: 1rem;
  text-decoration: none;
  display: flex; flex-direction: column; gap: 0.5rem;
  transition: box-shadow 0.2s;
  border-left: 4px solid transparent;
}
.dept-card:hover { box-shadow: 0 4px 16px rgba(0,0,0,0.1); }
.dept-card--mine { border-left-color: var(--jspl-orange); }
.status-border-on-track { border-left-color: var(--green); }
.status-border-at-risk  { border-left-color: var(--amber); }
.status-border-behind   { border-left-color: var(--red); }

.dept-code-badge {
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.72rem;
  background: var(--jspl-light);
  color: var(--jspl-blue);
  padding: 0.1rem 0.4rem;
  border-radius: 4px;
}
.dept-name { font-family: 'Sora', sans-serif; font-size: 0.9rem; font-weight: 600; color: var(--jspl-text); }
.dept-modules-row { display: flex; flex-wrap: wrap; gap: 0.25rem; }
.dept-module-chip { font-size: 0.68rem; padding: 0.15rem 0.4rem; border-radius: 4px; font-weight: 600; }
.chip-tpm  { background: #EFF6FF; color: var(--tpm-color); }
.chip-cmc  { background: #F5F3FF; color: var(--cmc-color); }
.chip-PRODUCTION { background: #FFF7ED; color: var(--PRODUCTION-color); }
.chip-safety { background: #FEF2F2; color: var(--safety-color); }

.dept-sparkline { height: 30px; margin-top: 0.25rem; }

/* ── Summary Ribbon ────────────────────────────────────── */
.summary-ribbon {
  display: flex; gap: 1rem; padding: 1.5rem;
  overflow-x: auto;
}
.summary-card {
  flex: 0 0 200px;
  background: white;
  border-radius: 10px;
  border: 1px solid var(--jspl-border);
  padding: 1rem;
  display: flex; align-items: flex-start; gap: 0.75rem;
}
.summary-card-icon { font-size: 1.5rem; }
.summary-label { font-size: 0.75rem; color: var(--jspl-muted); font-weight: 600; text-transform: uppercase; }
.summary-value { font-family: 'JetBrains Mono', monospace; font-size: 1.4rem; font-weight: 700; color: var(--jspl-text); }
.summary-sub { font-size: 0.78rem; color: var(--jspl-muted); }

/* ── Status Badges ──────────────────────────────────────── */
.badge-on-track, .badge-edit { background: #DCFCE7; color: var(--green); }
.badge-at-risk,  .badge-view { background: #FEF3C7; color: var(--amber); }
.badge-behind,   .badge-locked { background: #FEE2E2; color: var(--red); }
.badge-on-track, .badge-at-risk, .badge-behind,
.badge-edit, .badge-view, .badge-locked {
  padding: 0.2rem 0.55rem; border-radius: 999px;
  font-size: 0.75rem; font-weight: 700; font-family: 'Sora', sans-serif;
}

/* ── Page Header ────────────────────────────────────────── */
.page-header { padding: 1.5rem 1.5rem 0; }
.page-title { font-family: 'Sora', sans-serif; font-size: 1.5rem; font-weight: 700; color: var(--jspl-text); margin: 0; }
.page-subtitle { color: var(--jspl-muted); font-size: 0.9rem; margin: 0.25rem 0 0; }

/* ── Responsive ─────────────────────────────────────────── */
@media (max-width: 768px) {
  .login-split { grid-template-columns: 1fr; }
  .login-brand-panel { display: none; }
  #portal-shell { grid-template-columns: 1fr; }
  #portal-sidebar { position: fixed; top: var(--topbar-h); left: 0; height: 100%; z-index: 50; width: var(--sidebar-w); }
  .sidebar-toggle { display: block; }
}
```

---

## PART 9 — Alpine.js Portal Shell (`portal/static/portal/js/portal.js`)

```javascript
// Portal shell — sidebar state, mobile handling
function portalShell() {
  return {
    sidebarOpen: window.innerWidth > 768,
    isMobile: window.innerWidth <= 768,

    init() {
      window.addEventListener('resize', () => {
        this.isMobile = window.innerWidth <= 768;
        if (!this.isMobile) this.sidebarOpen = true;
      });
    }
  };
}

// Initialize mini sparkline charts on department cards
document.addEventListener('DOMContentLoaded', () => {
  document.querySelectorAll('.dept-sparkline').forEach(canvas => {
    const values = JSON.parse(canvas.dataset.values || '[]');
    if (!values.length) return;
    new Chart(canvas, {
      type: 'line',
      data: {
        labels: values.map(() => ''),
        datasets: [{
          data: values,
          borderColor: '#0057A8',
          borderWidth: 1.5,
          pointRadius: 0,
          fill: false,
          tension: 0.4,
        }]
      },
      options: {
        plugins: { legend: { display: false } },
        scales: { x: { display: false }, y: { display: false } },
        animation: false,
        maintainAspectRatio: false,
      }
    });
  });
});
```

---

## PART 10 — ADMIN PANEL: User Access Management

### `portal/views/admin_views.py`

```python
@login_required
@admin_required
def manage_access(request, uid=None):
    """
    Admin page: assign/revoke module access per user per department.
    Shows a matrix: user → dept → [TPM ✓] [CMC ✓] [PRODUCTION ✗] ...
    """
    users       = User.objects.filter(is_active=True).select_related('department')
    departments = Department.objects.filter(is_active=True)
    modules     = Module.objects.filter(is_active=True)

    if request.method == 'POST':
        # Form: user_id, dept_id, module_key, access_level (or 'NONE')
        user_id      = request.POST.get('user_id')
        dept_id      = request.POST.get('dept_id')
        module_key   = request.POST.get('module_key')
        access_level = request.POST.get('access_level')  # 'VIEW', 'EDIT', 'NONE'

        module = Module.objects.get(key=module_key)
        user   = User.objects.get(id=user_id)
        dept   = Department.objects.get(id=dept_id)

        if access_level == 'NONE':
            UserModuleAccess.objects.filter(user=user, department=dept, module=module).delete()
        else:
            UserModuleAccess.objects.update_or_create(
                user=user, department=dept, module=module,
                defaults={'access_level': access_level, 'granted_by': request.user}
            )

        # HTMX: return just the updated cell
        if request.htmx:
            return render(request, 'portal/admin/partials/_access_cell.html', {
                'user': user, 'dept': dept, 'module': module, 'access_level': access_level
            })

    context = {'users': users, 'departments': departments, 'modules': modules}
    return render(request, 'portal/admin/manage_access.html', context)
```

---

## PART 11 — SEED COMMAND

```python
# portal/management/commands/seed_portal.py

from django.core.management.base import BaseCommand
from portal.models import User, Department, Module, UserModuleAccess


class Command(BaseCommand):
    help = 'Seed initial portal data: departments, modules, users, access'

    def handle(self, *args, **kwargs):
        self.seed_departments()
        self.seed_modules()
        self.seed_users()
        self.stdout.write(self.style.SUCCESS('Portal seed complete.'))

    def seed_departments(self):
        DEPARTMENTS = [
            ('Blast Furnace-1', 'BF1'),   ('Blast Furnace-2', 'BF2'),
            ('Brick Plant', 'BP'),          ('Cement Plant', 'CP'),
            ('Coke Oven', 'CO'),            ('DRI-1', 'DRI1'),
            ('DRI-2', 'DRI2'),              ('Extrusion Plant', 'EP'),
            ('Lime and Dolo Plant', 'LDP'), ('Oxygen Plant', 'OP'),
            ('PGP-1', 'PGP1'),             ('PGP-2', 'PGP2'),
            ('PGP-3', 'PGP3'),             ('Plate Mill', 'PM'),
            ('Power Plant 1', 'PP1'),       ('Power Plant 2', 'PP2'),
            ('Power Plant 3', 'PP3'),       ('Power Plant Phase #3', 'PPP3'),
            ('RMHS-1', 'RMHS1'),           ('RMHS-2', 'RMHS2'),
            ('RMHS-3', 'RMHS3'),           ('Rail Mill', 'RM'),
            ('SAF-1', 'SAF1'),             ('SAF-2', 'SAF2'),
            ('SMS-2', 'SMS2'),             ('SMS-3', 'SMS3'),
            ('Sinter', 'SINT'),            ('Special Profile Mill (SPM)', 'SPM'),
        ]
        for name, code in DEPARTMENTS:
            Department.objects.get_or_create(code=code, defaults={'name': name})
        self.stdout.write(f'  ✓ {len(DEPARTMENTS)} departments')

    def seed_modules(self):
        MODULES = [
            {'key': 'TPM',        'label': 'Total Productive Maintenance', 'url_namespace': 'tpm:dept_overview',        'sort_order': 1, 'color_class': 'module-tpm'},
            {'key': 'CMC',        'label': 'Contract Management Cell',     'url_namespace': 'cmc:dept_overview',        'sort_order': 2, 'color_class': 'module-cmc'},
            {'key': 'PRODUCTION', 'label': 'PRODUCTION',                   'url_namespace': 'PRODUCTION:dept_overview', 'sort_order': 3, 'color_class': 'module-PRODUCTION'},
            {'key': 'SAFETY',     'label': 'Safety & Environment',         'url_namespace': 'safety:dept_overview',     'sort_order': 4, 'color_class': 'module-safety'},
            {'key': 'HR',         'label': 'Human Resources',              'url_namespace': 'hr:dept_overview',         'sort_order': 5, 'color_class': 'module-hr'},
        ]
        for m in MODULES:
            Module.objects.get_or_create(key=m['key'], defaults=m)
        self.stdout.write(f'  ✓ {len(MODULES)} modules')

    def seed_users(self):
        # Plant admin
        admin, _ = User.objects.get_or_create(
            email='admin@jindalsteel.in',
            defaults={
                'username': 'admin',
                'first_name': 'Portal',
                'last_name': 'Admin',
                'role': User.ROLE_ADMIN,
                'is_plant_admin': True,
                'is_staff': True,
            }
        )
        admin.set_password('Admin@1234')
        admin.save()

        # Example named users (replace with real users — import from LDAP/AD)
        sms2 = Department.objects.get(code='SMS2')
        tpm_module = Module.objects.get(key='TPM')

        lalit, _ = User.objects.get_or_create(
            email='lalit.goyal@jindalsteel.in',
            defaults={
                'username': 'lalit.goyal',
                'first_name': 'Lalit',
                'last_name': 'Goyal',
                'role': User.ROLE_USER,
                'department': sms2,
            }
        )
        lalit.set_password('Dept@1234')
        lalit.save()

        # Grant Lalit TPM access on SMS-2
        UserModuleAccess.objects.get_or_create(
            user=lalit, department=sms2, module=tpm_module,
            defaults={'access_level': 'EDIT'}
        )

        saurabh, _ = User.objects.get_or_create(
            email='saurabh.agrawal@jindalsteel.in',
            defaults={
                'username': 'saurabh.agrawal',
                'first_name': 'Saurabh',
                'last_name': 'Agrawal',
                'role': User.ROLE_ADMIN,
                'is_plant_admin': True,
            }
        )
        saurabh.set_password('Admin@1234')
        saurabh.save()

        self.stdout.write('  ✓ Demo users created')
```

---

## PART 12 — PROJECT FOLDER STRUCTURE (Final)

```
jspl_portal/                        ← Django project root
├── manage.py
├── requirements.txt
├── .env
├── jspl_portal/
│   ├── settings.py
│   ├── urls.py                     ← root URL conf (includes all apps)
│   └── wsgi.py
│
├── portal/                         ← CORE PORTAL APP (auth, hub, access)
│   ├── models.py                   ← User, Department, Module, UserModuleAccess, AuditLog
│   ├── admin.py                    ← Django admin registrations
│   ├── views/
│   │   ├── auth_views.py           ← login / logout (THE ONLY LOGIN)
│   │   ├── dashboard_views.py      ← plant-wide dashboard
│   │   ├── department_views.py     ← dept hub + enter_module
│   │   └── admin_views.py          ← user + access management
│   ├── utils/
│   │   ├── access.py               ← get_user_module_access_map()
│   │   ├── decorators.py           ← @dept_visibility_required, @module_access_required
│   │   └── aggregations.py         ← plant summary stats
│   ├── context_processors.py       ← sidebar_context
│   ├── middleware.py               ← UpdateLastActiveMiddleware
│   ├── templatetags/
│   │   └── portal_tags.py          ← {% get_user_modules %} tag
│   ├── templates/
│   │   └── portal/
│   │       ├── base.html           ← MASTER SHELL (all pages extend this)
│   │       ├── auth/
│   │       │   └── login.html      ← THE ONE LOGIN PAGE
│   │       ├── dashboard/
│   │       │   └── plant_dashboard.html
│   │       ├── department/
│   │       │   └── dept_hub.html
│   │       ├── admin/
│   │       │   ├── users.html
│   │       │   ├── manage_access.html
│   │       │   └── audit_log.html
│   │       └── partials/
│   │           └── _module_icon.html
│   ├── static/
│   │   └── portal/
│   │       ├── css/portal.css
│   │       ├── js/portal.js
│   │       └── img/jspl_logo.png
│   ├── management/
│   │   └── commands/
│   │       └── seed_portal.py
│   └── migrations/
│
├── tpm/                            ← EXISTING TPM APP (plug in, no re-login)
│   ├── models.py                   ← PillarEntry, KPIValue, Workstation, etc.
│   ├── views/
│   │   ├── pillar_views.py         ← @module_access_required('TPM') on all views
│   │   ├── ws_kpi_views.py
│   │   └── report_views.py
│   ├── utils/
│   │   ├── kpi_definitions.py
│   │   ├── calculations.py
│   │   └── export.py
│   ├── templates/
│   │   └── tpm/
│   │       ├── base_tpm.html       ← extends portal/base.html (NOT a standalone base)
│   │       ├── dept_overview.html
│   │       ├── pillar_entry.html
│   │       ├── ws_kpi.html
│   │       ├── report.html
│   │       └── partials/
│   │           ├── _kpi_table.html
│   │           ├── _kpi_row.html
│   │           └── _analytics_charts.html
│   ├── static/tpm/css/tpm.css
│   ├── urls.py                     ← app_name = 'tpm'
│   └── migrations/
│
├── cmc/                            ← CMC APP STUB (extend later)
│   ├── views.py                    ← @module_access_required('CMC')
│   ├── urls.py                     ← app_name = 'cmc'
│   ├── templates/cmc/
│   │   └── coming_soon.html        ← placeholder until CMC is built
│   └── migrations/
│
├── PRODUCTION/                     ← PRODUCTION APP STUB
├── safety/                         ← SAFETY APP STUB
├── hr/                             ← HR APP STUB
│
└── fixtures/
    └── initial_portal.json         ← loaddata alternative to seed command
```

---

## PART 13 — COMPLETE USER JOURNEY (Step by Step)

```
1. User opens https://portal.jspl.in
   └─ root_redirect() → not logged in → /login/

2. Login page appears
   └─ JSPL branding left panel + email/password form right panel
   └─ User enters: lalit.goyal@jindalsteel.in + password
   └─ Domain validated: must be @jindalsteel.in
   └─ authenticate() checks DB credentials
   └─ Success → session created → AuditLog('LOGIN') written

3. root_redirect() fires
   └─ Lalit is ROLE_USER, department = SMS-2
   └─ Redirect to /department/25/ (SMS-2's dept_hub)

4. Department Hub (/department/25/)
   └─ Page shows module cards for SMS-2
   └─ TPM card: ACCESSIBLE (Lalit has EDIT access) → full color, "Open →"
   └─ CMC card: LOCKED (no access) → greyed out, 🔒, tooltip on hover
   └─ PRODUCTION, Safety, HR: all LOCKED for Lalit

5. Lalit clicks TPM card
   └─ GET /department/25/module/TPM/enter/
   └─ enter_module() checks UserModuleAccess → confirmed EDIT
   └─ AuditLog('ACCESS_MODULE', dept=SMS-2, module=TPM) written
   └─ reverse('tpm:dept_overview', kwargs={'dept_id': 25})
   └─ Redirect to /tpm/department/25/

6. TPM Department Overview loads
   └─ @login_required passes (already logged in from step 2, NO second login)
   └─ @module_access_required('TPM') passes
   └─ Breadcrumb: 🏭 Plant › SMS-2 › TPM
   └─ Sidebar shows: SMS-2 accordion open, TPM link highlighted
   └─ Full TPM pillar dashboard for SMS-2

7. Lalit navigates within TPM (pillar pages, analytics, reports)
   └─ All normal — no additional auth prompts
   └─ "Back" breadcrumb link goes to /department/25/ (dept hub)

8. If Lalit tries /department/1/ (Blast Furnace-1)
   └─ dept_visibility_required() → not Lalit's dept, no access → redirect /dashboard/
   └─ He can see plant dashboard (aggregate only, no dept details)

9. Saurabh Agrawal (admin) logs in
   └─ is_plant_admin = True
   └─ Redirect to /dashboard/ (plant overview)
   └─ Sees all 28 dept cards, all accessible
   └─ Sidebar shows all 28 depts, all modules accessible
   └─ Admin panel link visible in sidebar and user dropdown
```

---

## PART 14 — WHAT NOT TO DO

- Do NOT create a separate login for TPM — delete any existing TPM login views and URLs
- Do NOT create a separate session per module — one Django session covers the entire portal
- Do NOT check `request.user.is_authenticated` inside TPM views manually — use `@login_required` which points to the unified `/login/`
- Do NOT allow non-`@jindalsteel.in` emails — enforce in login view AND in User model `clean()`
- Do NOT give `ROLE_USER` users access to `/dashboard/` dept card details of other depts — aggregate view only
- Do NOT hardcode access rules in views — all access goes through `UserModuleAccess` table
- Do NOT build CMC, PRODUCTION, etc. dashboards from scratch immediately — stub them with a "Coming Soon" page and add `@module_access_required` so the access control is ready when the dashboards are built
- Do NOT use Django's default `User` model — use `portal.User` everywhere (`AUTH_USER_MODEL = 'portal.User'`)
- Do NOT forget `LOGIN_URL = '/login/'` in settings — this is what redirects unauthenticated users from any `@login_required` in any module app

---

## PART 15 — DELIVERABLES EXPECTED FROM ANTIGRAVITY

1. Complete Django 5 project with all apps: `portal`, `tpm`, `cmc` (stub), `PRODUCTION` (stub), `safety` (stub), `hr` (stub)
2. `portal/models.py` — User (email login, @jindalsteel.in), Department, Module, UserModuleAccess, AuditLog
3. `portal/views/auth_views.py` — single unified login/logout
4. `portal/views/dashboard_views.py` — plant-wide dashboard
5. `portal/views/department_views.py` — dept hub + enter_module gating
6. `portal/views/admin_views.py` — user + module access management matrix
7. `portal/utils/access.py` — access map helper
8. `portal/utils/decorators.py` — `@dept_visibility_required`, `@module_access_required`
9. `portal/context_processors.py` — sidebar context injected into all templates
10. All templates as specified in Part 5
11. `portal/static/portal/css/portal.css` — full JSPL brand CSS from Part 8
12. `portal/static/portal/js/portal.js` — Alpine.js shell + sparklines
13. `tpm/templates/tpm/base_tpm.html` — extends portal base (not standalone)
14. All existing TPM views updated with `@module_access_required('TPM')`; TPM login removed
15. `portal/management/commands/seed_portal.py` — seeds depts, modules, demo users
16. `jspl_portal/settings.py` — `AUTH_USER_MODEL`, `LOGIN_URL`, session config, context processors
17. `jspl_portal/urls.py` — root URL conf including all app namespaces
18. `README.md` with:
    - Setup: `pip install -r requirements.txt`, DB setup, `migrate`, `seed_portal`, `runserver`
    - How to add a new user and assign module access (via admin panel)
    - How to add a new module (add to Module table + create stub app + URL namespace)
    - How to add a new department (admin panel → Department)
    - Environment variables: `SECRET_KEY`, `DB_*`, `DEBUG`, `ALLOWED_HOSTS`

---

*This document is the COMPLETE unified portal specification.*
*Stack: Django 5 + PostgreSQL + HTMX + Alpine.js. Single login. No re-authentication between modules.*
*Hand this document directly to Antigravity along with the previous Django + HTMX TPM implementation plan.*
