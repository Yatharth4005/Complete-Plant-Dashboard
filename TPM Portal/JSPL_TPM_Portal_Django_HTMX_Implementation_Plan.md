# JSPL TPM Portal — Complete Implementation Plan & Antigravity Prompt
# Stack: Django 5 + HTMX + Alpine.js (No Separate Frontend Framework)

---

## PART 1 — UNDERSTANDING THE DATA LOGIC (What the current portal stores)

Before building anything, here is exactly what data flows through every pillar form.

### The Core Data Model (Every Pillar Entry)

Every row in every pillar form stores exactly this:

```
{
  department_id,     // e.g. "SMS-II", "Blast Furnace-1"
  pillar_id,         // "KK" | "JH" | "PM" | "QM" | "ET" | "DM" | "SHE" | "OTPM" | "WS_KPI"
  month,             // 1–12
  year,              // e.g. 2026
  data_entry_type,   // "Monthly" | "Weekly"
  kpi_sl_no,         // e.g. "1", "1A", "1B", "8A", "8B", "8C" (sub-rows exist)
  kpi_name,          // full text of the KPI
  uom,               // unit of measurement
  benchmark,         // the all-time best / reference value (read-only, set once)
  target,            // this month's goal (usually pre-filled, may be editable)
  actual,            // what the user ENTERS each month (the only truly editable field)
  availability,      // PRODUCTION sub-component (only for KK pillar row 1 — PRODUCTION row)
  performance,       // PRODUCTION sub-component (only for KK pillar row 1)
  quality,           // PRODUCTION sub-component (only for KK pillar row 1)
  remarks            // free text, always editable
}
```

### Why Availability / Performance / Quality Columns exist

These are the three PRODUCTION components. PRODUCTION = Availability × Performance × Quality. Only the KK Pillar's first KPI (Overall Equipment Efficiency — PRODUCTION%) uses these three sub-fields. All other KPIs leave them blank. When entering PRODUCTION, users break it down into:
- **Availability** = (Planned run time − Downtime) / Planned run time
- **Performance** = (Ideal cycle time × Parts produced) / Run time
- **Quality** = (Good parts) / (Total parts produced)
- PRODUCTION (Actual) = A × P × Q

### Workstation KPI Pillar (from your Excel file)

This is a completely different structure from the 8 standard pillars. It tracks individual machines/workstations, not department-level KPIs.

```
{
  plant,              // e.g. "Plate Mill", "SPM", "SMS-2"
  workstation,        // e.g. "CTL", "Furnace Area", "Mill Area"
  leader,             // person responsible for this workstation
  ws_inception_date,  // when this WS KPI tracking started
  kpi_name,           // e.g. "CTL 1 Machine Availability >90%", "Break Down", "PRODUCTION"
  uom,                // %, Nos, Mt/Day, Min/Month, MCAL/MT, etc.
  goodness_indicator, // direction of improvement (higher better / lower better)
  baseline,           // starting reference value
  commitment,         // agreed target
  monthly_values: {   // time-series: Apr 2025 → forward
    "2025-04": value,
    "2025-05": value,
    ...
  }
}
```

---

## PART 2 — ALL PILLAR KPI LISTS (Complete, from your screenshots)

### KK Pillar (Kobetsu Kaizen)
| Sl | KPI | UOM |
|----|-----|-----|
| 1 | Overall equipment efficiency-OEE(%) | % |
| 2 | Productivity (Ton/Man or MWh/Man) (Company Employee only) | Ton/Man |
| 5 | Total losses [Updation of Loss Tree] | Hrs |
| 6 | Kobetsu Kaizen registered | Nos |
| 7 | Kobetsu Kaizen completed | Nos |
| 8 | Total Saving through Kaizen | Rs |
| 10 | Training on KK to improve performance [Loss identification, PRODUCTION, Kaizen, Cost Reduction] | Man Hours |

### JH Pillar (Jishu Hozen)
| Sl | KPI | UOM |
|----|-----|-----|
| 1 | Compliance of JH Steps as per JH Master Plan (% [Actual/Planned]) | % |
| 2 | White Fuguai Identified | Nos/month |
| 3 | White Fuguai Rectified | Nos/month |
| 4 | Red Fuguai Identified | Nos/month |
| 5 | Red Fuguai Rectified | Nos/month |
| 6 | JH Kaizen Completed | Nos |
| 7 | OPL Developed | Nos |
| 8A | Rank A machine with JH Step 1 Completed | Nos |
| 8B | Rank A machine with JH Step 2 Completed | Nos |
| 8C | Rank A machine with JH Step 3 Completed | Nos |
| 9A | Rank B machine with JH Step 1 Completed | Nos |
| 9B | Rank B machine with JH Step 2 Completed | Nos |
| 9C | Rank B machine with JH Step 3 Completed | Nos |
| 10A | Rank C machine with JH Step 1 Completed | Nos |
| 10B | Rank C machine with JH Step 2 Completed | Nos |
| 10C | Rank C machine with JH Step 3 Completed | Nos |
| 11 | Training on JH to improve performance (Fuguai identification, CLITA, etc.) | Man hours |

### PM Pillar (Planned Maintenance)
| Sl | KPI | UOM |
|----|-----|-----|
| 1 | Total breakdown nos. (Rank A + B + C machine) | Nos |
| 2 | Total breakdown hours (Rank A + B + C machine) | Hrs |
| 3 | No. of Machine with Repetitive breakdown | Nos/month |
| 4 | MTTR (Hours) | Hrs |
| 5 | MTBF (Hours) | Hrs |
| 8 | Equipment Availability (%) | % |
| 9 | CAPA Made | Nos |
| 10 | PM Kaizen done | Nos |
| 11 | One point Lesson | Nos |
| 13 | Shutdown Maintenance rate (%) | % |
| 14 | PM Schedule compliance [as per SAP] (%) | % |
| 15 | Training on PM to improve performance [Breakdown, PM, PM SOP as per ISO] | Man hours |
| 16 | Number of Breakdowns => 30 minutes | Nos |

### QM Pillar (Quality Maintenance)
| Sl | KPI | UOM |
|----|-----|-----|
| 1A | Customer complaint (Metric T/Dispatched Qty.) | % |
| 1B | Response time to customer against complaint | Days |
| 2 | Rejection | % |
| 3 | Rework | % |
| 4 | QM Kaizen/Project taken | Nos |
| 5 | QA Matrix developed | Nos |
| 6 | Training on QM to improve performance | Man hours |

### E&T Pillar (Education & Training)
| Sl | KPI | UOM |
|----|-----|-----|
| 1 | Compliance of Skill evaluation of employees | % |
| 2 | Trainings (Depts. Classroom) during the month | Nos (Actual/Planned) |
| 3 | Employees covered (Depts. Classroom) during the month | % |
| 4 | Training Man-hours | Man hrs/Emp |
| 5 | On-The-Job Training during the month | Nos |
| 6 | Employees covered (On the job) during the month | % |
| 7 | OPL's developed during the month (Including all Pillar) | Nos |
| 8A | Multi skilled Manpower_Uni-athlete | % |
| 8B | Multi skilled Manpower_Bi-athlete | % |
| 8C | Multi skilled Manpower_Tri-athlete | % |
| 9 | Skill Gap of Employee (0-5) | Score |
| 10 | In-house trainers developed (Annual) | Nos |
| 11 | Training on E&T to improve performance (quarterly) | Nos |

### DM Pillar (Initial Flow Control / Design & Management)
| Sl | KPI | UOM |
|----|-----|-----|
| 1 | Sales from upgraded & New products over total sales | Nos |
| 2 | New product developments | Percentage |
| 3 | Design related complaints/failures | Nos |
| 4 | New equipment/process developed | Nos |
| 5 | Modification done in existing equipment/processes | Nos |
| 6 | Number of MP Sheet Developed | Nos |
| 7 | Number of LCC Sheet Developed | Nos |
| 8 | Training on DM to improve performance | Nos |

### SHE Pillar (Safety, Health & Environment)
| Sl | KPI | UOM |
|----|-----|-----|
| 1A | Safety Observations made | Nos |
| 1B | Safety Observations rectified | Nos |
| 1C | Number of Near Misses Reported | Nos |
| 2A | Numbers of Fatal accidents | Nos |
| 2B | Numbers of reportable accidents (LTI) | Nos |
| 2C | Numbers of MTI & First Aid Cases | Nos |
| 3A | Employee (below executive) health check-up compliance adherence (%), monthly | % |
| 3B | Employee (executive & above) health check-up compliance adherence (%), Quarterly | % |
| 3C | Electrical Energy consumed (MWH) in PCDs-Pollution Control Devices | MWH |
| 4 | Compliance of Monitoring of environment parameters (as per limits) | |
| 5 | Water Consumption | kL/Ton |
| 6 | Dust level monitoring at workplace | ug/M3 |
| 7 | Noise level monitoring | db |
| 8 | Low Illuminated area identified | Nos |
| 9 | Low Illuminated area rectified | Nos |
| 10 | Dust level monitoring at stacks | mg/M3 |
| 11 | No. of Kaizen themes or improvement project (Kaizen) taken for improvement in Safety | Nos |
| 12 | Training on SHE | Man hours |

### OTPM Pillar (Office TPM)
| Sl | KPI | UOM |
|----|-----|-----|
| 1 | Losses Identified in Office TPM process | Hours |
| 2 | Losses rectified in Office TPM process | Hours |
| 3 | No. of Kaizen themes or improvement project (Kaizen) taken/registered for reduction in losses | |
| 4 | No. of Kaizen themes or improvement project (Kaizen) completed for reduction in losses | |
| 5 | OPL/SOPs prepared and displayed | Nos |
| 6 | Fuguai identified | Nos |
| 7 | Fuguai rectified | Nos |
| 8 | Area/Store/Offices identified for 1S | Nos |
| 9 | Area/Store/Offices completed for 1S | Nos |
| 10 | Area/Store/Offices identified for 2S | Nos |
| 11 | Area/Store/Offices completed for 2S | Nos |
| 12 | Area/Store/Offices identified for 3S | Nos |
| 13 | Area/Store/Offices completed for 3S | Nos |
| 14 | Area/Store/Offices identified for 4S | Nos |
| 15 | Area/Store/Offices completed for 4S | Nos |
| 16 | Area/Store/Offices identified for 5S | Nos |
| 17 | Area/Store/Offices completed for 5S | Nos |
| 18 | Area (Contractors) identify for 1S | Nos |
| 19 | Area (Contractors) completed for 1S | Nos |
| 20 | Area (Contractors) identify for 2S | Nos |
| 21 | Area (Contractors) completed for 2S | Nos |
| 22 | Area (Contractors) identify for 3S | Nos |
| 23 | Area (Contractors) completed for 3S | Nos |
| 24 | Training on OTPM to improve the performance | Man hours |

### Workstation KPI Pillar (9th Pillar — NEW)
Structure is different from above 8. Each workstation has:
- Plant → Workstation → Leader → WS Inception Date
- KPIs per workstation (2–6 KPIs each)
- Each KPI has: KPI name, UOM, Goodness Indicator (↑ or ↓), Baseline, Commitment (target)
- Monthly actuals tracked Apr 2025 → ongoing

---

## PART 3 — 25 DEPARTMENTS LIST

From your screenshots:

1. Blast Furnace-1
2. Blast Furnace-2
3. Brick Plant
4. Cement Plant
5. Coke Oven
6. DRI-1
7. DRI-2
8. Extrusion Plant
9. Lime and Dolo Plant
10. Oxygen Plant
11. PGP-1
12. PGP-2
13. PGP-3
14. Plate Mill
15. Power Plant 1
16. Power Plant 2
17. Power Plant 3
18. Power Plant Phase #3
19. RMHS-1
20. RMHS-2
21. RMHS-3
22. Rail Mill
23. SAF-1
24. SAF-2
25. SMS-2
26. SMS-3
27. Sinter
28. Special Profile Mill (SPM)

*(Note: screenshots show 28 entries — confirm with your team which 25 are active)*

---

## PART 4 — TECHNOLOGY STACK

### Stack (NON-NEGOTIABLE)

```
Backend:   Django 5 (Python)
Database:  PostgreSQL
ORM:       Django ORM (built-in)
Frontend:  Django Templates + HTMX + Alpine.js
Charts:    Chart.js (via CDN, same as your current demo)
Reports:   ReportLab (PDF) + openpyxl (Excel export)
Auth:      Django built-in (sessions, RBAC via groups)
Hosting:   Any Linux server, Docker, or a local server in the plant
```

### Why this stack wins for JSPL specifically:
- Django's built-in admin gives you user management, department config, and KPI config for free on day one
- No build step, no node_modules, no TypeScript compiler — easier to deploy on plant servers
- Python devs are far more common in Indian industrial IT teams
- The entire portal can be maintained by one mid-level Python developer
- Offline-capable if you host it on a local plant server (no internet dependency)
- HTMX makes tables interactive (inline editing, form submission, tab switching) without writing a single line of React
- Alpine.js handles all lightweight client-side reactivity (achievement badge, PRODUCTION auto-compute, accordion sidebar)

### Python Dependencies (`requirements.txt`)

```
Django==5.1
psycopg2-binary==2.9.9
django-htmx==1.21.0
whitenoise==6.7.0       # static file serving
reportlab==4.2.0         # PDF generation
openpyxl==3.1.2          # Excel export
django-crispy-forms==2.3  # form rendering
crispy-bootstrap5==2024.2
Pillow==10.3.0           # image handling (JSPL logo in reports)
django-ratelimit==4.1.0  # rate limiting
```

### Frontend CDN Imports (no npm, no build step)

```html
<!-- HTMX -->
<script src="https://unpkg.com/htmx.org@1.9.12"></script>
<!-- Alpine.js -->
<script src="https://unpkg.com/alpinejs@3.14.1/dist/cdn.min.js" defer></script>
<!-- Chart.js -->
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.3/dist/chart.umd.min.js"></script>
<!-- Google Fonts -->
<link href="https://fonts.googleapis.com/css2?family=Sora:wght@400;600;700&family=JetBrains+Mono:wght@400;600&display=swap" rel="stylesheet">
```

---

## PART 5 — DATABASE SCHEMA (Django ORM Models)

```python
# tpm/models.py

from django.db import models
from django.contrib.auth.models import AbstractUser


class User(AbstractUser):
    """Custom user: standard Django auth + department link"""
    ROLE_ADMIN = 'ADMIN'
    ROLE_USER  = 'USER'
    ROLE_CHOICES = [(ROLE_ADMIN, 'Admin'), (ROLE_USER, 'Department User')]

    role         = models.CharField(max_length=10, choices=ROLE_CHOICES, default=ROLE_USER)
    department   = models.ForeignKey(
        'Department', null=True, blank=True,
        on_delete=models.SET_NULL, related_name='users'
    )

    def is_admin(self):
        return self.role == self.ROLE_ADMIN


class Department(models.Model):
    name = models.CharField(max_length=100, unique=True)   # "Blast Furnace-1"
    code = models.CharField(max_length=10,  unique=True)   # "BF1"

    def __str__(self):
        return self.name


class PillarEntry(models.Model):
    """One submission per department × pillar × month × year"""

    class PillarType(models.TextChoices):
        KK    = 'KK',    'Kobetsu Kaizen'
        JH    = 'JH',    'Jishu Hozen'
        PM    = 'PM',    'Planned Maintenance'
        QM    = 'QM',    'Quality Maintenance'
        ET    = 'ET',    'Education & Training'
        DM    = 'DM',    'Design & Management'
        SHE   = 'SHE',   'Safety Health Environment'
        OTPM  = 'OTPM',  'Office TPM'

    class DataEntryType(models.TextChoices):
        MONTHLY = 'MONTHLY', 'Monthly'
        WEEKLY  = 'WEEKLY',  'Weekly'

    department    = models.ForeignKey(Department, on_delete=models.CASCADE, related_name='pillar_entries')
    pillar        = models.CharField(max_length=10, choices=PillarType.choices)
    month         = models.PositiveSmallIntegerField()   # 1–12
    year          = models.PositiveSmallIntegerField()
    data_entry_type = models.CharField(max_length=10, choices=DataEntryType.choices, default='MONTHLY')
    submitted_at  = models.DateTimeField(null=True, blank=True)
    submitted_by  = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL)
    updated_at    = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('department', 'pillar', 'month', 'year')

    def is_locked(self):
        return self.submitted_at is not None


class KPIValue(models.Model):
    """One row inside a PillarEntry — one KPI for one period"""
    pillar_entry  = models.ForeignKey(PillarEntry, on_delete=models.CASCADE, related_name='kpi_values')
    sl_no         = models.CharField(max_length=10)   # "1", "1A", "8B" etc.
    kpi_name      = models.CharField(max_length=300)
    uom           = models.CharField(max_length=50)
    benchmark     = models.FloatField(null=True, blank=True)
    target        = models.FloatField(null=True, blank=True)
    actual        = models.FloatField(null=True, blank=True)
    availability  = models.FloatField(null=True, blank=True)  # KK row 1 PRODUCTION only
    performance   = models.FloatField(null=True, blank=True)  # KK row 1 PRODUCTION only
    quality       = models.FloatField(null=True, blank=True)  # KK row 1 PRODUCTION only
    remarks       = models.TextField(blank=True)

    class Meta:
        unique_together = ('pillar_entry', 'sl_no')


# --- Workstation KPI (9th Pillar — different schema) ---

class Workstation(models.Model):
    department    = models.ForeignKey(Department, on_delete=models.CASCADE, related_name='workstations')
    name          = models.CharField(max_length=100)   # "Furnace Area", "Mill Area"
    leader        = models.CharField(max_length=100)
    inception_date = models.DateField(null=True, blank=True)

    def __str__(self):
        return f"{self.department.code} — {self.name}"


class WorkstationKPI(models.Model):
    class GoodnessIndicator(models.TextChoices):
        HIGHER = 'HIGHER', 'Higher is Better ↑'
        LOWER  = 'LOWER',  'Lower is Better ↓'

    workstation       = models.ForeignKey(Workstation, on_delete=models.CASCADE, related_name='kpis')
    kpi_name          = models.CharField(max_length=200)
    uom               = models.CharField(max_length=50)
    goodness_indicator = models.CharField(max_length=10, choices=GoodnessIndicator.choices)
    baseline          = models.FloatField(null=True, blank=True)
    commitment        = models.FloatField(null=True, blank=True)


class WorkstationValue(models.Model):
    workstation_kpi = models.ForeignKey(WorkstationKPI, on_delete=models.CASCADE, related_name='monthly_values')
    month           = models.PositiveSmallIntegerField()
    year            = models.PositiveSmallIntegerField()
    actual          = models.FloatField(null=True, blank=True)
    remarks         = models.TextField(blank=True)

    class Meta:
        unique_together = ('workstation_kpi', 'month', 'year')
```

---

## PART 6 — DJANGO PROJECT STRUCTURE

```
jspl_tpm/                          ← project root
├── manage.py
├── requirements.txt
├── .env                           ← SECRET_KEY, DB credentials (never commit)
├── jspl_tpm/                      ← Django project package
│   ├── settings.py
│   ├── urls.py
│   └── wsgi.py
├── tpm/                           ← main app
│   ├── models.py                  ← all models (above)
│   ├── admin.py                   ← Django admin registration
│   ├── views/
│   │   ├── __init__.py
│   │   ├── auth_views.py          ← login / logout
│   │   ├── dashboard_views.py     ← plant-wide admin dashboard
│   │   ├── department_views.py    ← dept overview
│   │   ├── pillar_views.py        ← pillar entry + analytics (HTMX-powered)
│   │   ├── ws_kpi_views.py        ← workstation KPI (different layout)
│   │   ├── report_views.py        ← PDF + Excel export
│   │   └── admin_views.py         ← user management
│   ├── forms/
│   │   ├── __init__.py
│   │   ├── pillar_forms.py        ← PillarEntry + KPIValue formsets
│   │   └── ws_kpi_forms.py        ← WorkstationValue forms
│   ├── utils/
│   │   ├── kpi_definitions.py     ← all KPI lists as Python dicts (immutable source of truth)
│   │   ├── calculations.py        ← achievement %, PRODUCTION, status logic
│   │   └── export.py              ← ReportLab PDF + openpyxl Excel helpers
│   ├── templatetags/
│   │   └── tpm_tags.py            ← custom template tags (achievement_badge, status_color)
│   ├── templates/
│   │   ├── base.html              ← shell layout (sidebar + topbar)
│   │   ├── partials/              ← HTMX partial templates (swapped inline)
│   │   │   ├── _kpi_table.html
│   │   │   ├── _kpi_row.html
│   │   │   ├── _analytics_charts.html
│   │   │   ├── _dept_card.html
│   │   │   ├── _ws_card.html
│   │   │   └── _toast.html
│   │   ├── auth/
│   │   │   └── login.html
│   │   ├── dashboard/
│   │   │   └── plant_dashboard.html
│   │   ├── department/
│   │   │   ├── overview.html
│   │   │   ├── pillar_entry.html
│   │   │   ├── ws_kpi.html
│   │   │   └── report.html
│   │   └── admin/
│   │       ├── users.html
│   │       └── departments.html
│   ├── static/
│   │   ├── css/
│   │   │   └── tpm.css            ← JSPL brand tokens + layout CSS
│   │   ├── js/
│   │   │   └── tpm.js             ← Alpine.js component definitions (PRODUCTION compute, etc.)
│   │   └── img/
│   │       └── jspl_logo.png
│   ├── urls.py
│   └── migrations/
├── fixtures/
│   └── seed_data.json             ← initial departments, KPI configs, demo users
└── Dockerfile                     ← optional, for containerised deploy
```

---

## PART 7 — URL CONFIGURATION

```python
# tpm/urls.py

from django.urls import path
from tpm.views import auth_views, dashboard_views, department_views
from tpm.views import pillar_views, ws_kpi_views, report_views, admin_views

urlpatterns = [
    # Auth
    path('',             auth_views.redirect_root,   name='root'),
    path('login/',       auth_views.login_view,       name='login'),
    path('logout/',      auth_views.logout_view,      name='logout'),

    # Admin plant-wide dashboard
    path('dashboard/',   dashboard_views.plant_dashboard, name='plant_dashboard'),

    # Department
    path('department/<int:dept_id>/',
         department_views.dept_overview, name='dept_overview'),

    # Pillar (standard 8)
    path('department/<int:dept_id>/pillar/<str:pillar_id>/',
         pillar_views.pillar_page, name='pillar_page'),

    # HTMX partial: load/refresh KPI table (swaps #kpi-table-container)
    path('department/<int:dept_id>/pillar/<str:pillar_id>/table/',
         pillar_views.kpi_table_partial, name='kpi_table_partial'),

    # HTMX partial: save a single KPI row inline
    path('department/<int:dept_id>/pillar/<str:pillar_id>/save-row/',
         pillar_views.save_kpi_row, name='save_kpi_row'),

    # HTMX partial: submit full pillar entry (lock it)
    path('department/<int:dept_id>/pillar/<str:pillar_id>/submit/',
         pillar_views.submit_pillar_entry, name='submit_pillar_entry'),

    # HTMX partial: analytics tab (swaps #analytics-container)
    path('department/<int:dept_id>/pillar/<str:pillar_id>/analytics/',
         pillar_views.analytics_partial, name='analytics_partial'),

    # Workstation KPI
    path('department/<int:dept_id>/pillar/ws-kpi/',
         ws_kpi_views.ws_kpi_page, name='ws_kpi_page'),

    path('department/<int:dept_id>/pillar/ws-kpi/save/<int:ws_id>/',
         ws_kpi_views.save_workstation, name='save_workstation'),

    # Reports
    path('department/<int:dept_id>/report/',
         report_views.report_page, name='report_page'),
    path('department/<int:dept_id>/report/pdf/',
         report_views.export_pdf, name='export_pdf'),
    path('department/<int:dept_id>/report/excel/',
         report_views.export_excel, name='export_excel'),

    # Admin
    path('admin-panel/users/',       admin_views.users_list,    name='admin_users'),
    path('admin-panel/users/add/',   admin_views.add_user,      name='admin_add_user'),
    path('admin-panel/users/<int:user_id>/edit/',
         admin_views.edit_user,      name='admin_edit_user'),
    path('admin-panel/departments/', admin_views.departments,   name='admin_departments'),

    # HTMX: admin unlock a locked entry
    path('admin-panel/unlock-entry/<int:entry_id>/',
         admin_views.unlock_entry,   name='unlock_entry'),
]
```

---

## PART 8 — VIEWS (Full Specification)

### auth_views.py

```python
def redirect_root(request):
    if request.user.is_authenticated:
        if request.user.is_admin():
            return redirect('plant_dashboard')
        return redirect('dept_overview', dept_id=request.user.department_id)
    return redirect('login')

def login_view(request):
    # Standard Django authenticate() + login()
    # On success → redirect_root()
    # Session expiry: SESSION_COOKIE_AGE = 28800  (8 hours in settings.py)

def logout_view(request):
    # Django logout(), redirect to login
```

### dashboard_views.py

```python
@login_required
@admin_required
def plant_dashboard(request):
    # Fetch all 28 departments
    # Aggregate: plant PRODUCTION (avg KK row 1 actuals), total kaizens YTD, SHE LTI count, PM compliance
    # Dept status cards: compute avg achievement per dept for current month
    # Pass to template: depts, plant_PRODUCTION, total_kaizens, lti_count, pm_compliance
    # Chart data passed as JSON in context for Chart.js
```

### department_views.py

```python
@login_required
@dept_access_required   # decorator: admin sees any, user sees only own dept
def dept_overview(request, dept_id):
    # 9 pillar score cards for this dept (current month)
    # PRODUCTION trend data (last 12 months) → JSON for Chart.js
    # Recent 6-month submissions table
    # Radar chart data (9 axes) → JSON for Chart.js
```

### pillar_views.py

```python
@login_required
@dept_access_required
def pillar_page(request, dept_id, pillar_id):
    """Full page — renders shell + initial data entry tab"""
    # Selected month/year from GET params (default: current month)
    # Check if PillarEntry exists for this dept/pillar/month/year
    # Pass KPI definitions from kpi_definitions.py for this pillar
    # Pass is_locked, submitted_at

@login_required
@dept_access_required
def kpi_table_partial(request, dept_id, pillar_id):
    """HTMX GET — returns only the #kpi-table-container partial
       Triggered when user changes Month or Year selector"""
    # Used with: hx-get="/department/1/pillar/KK/table/?month=5&year=2026"
    #            hx-target="#kpi-table-container"
    #            hx-trigger="change"

@login_required
@dept_access_required
@require_POST
def save_kpi_row(request, dept_id, pillar_id):
    """HTMX POST — saves one KPI row inline (auto-save on blur)
       Returns updated row HTML fragment with achievement badge"""
    # Gets or creates PillarEntry for the period
    # Updates/creates KPIValue for the specific sl_no
    # Computes achievement % using calculations.py
    # Returns: _kpi_row.html partial (just the one <tr>)
    # If entry is locked, returns 403 with toast message

@login_required
@dept_access_required
@require_POST
def submit_pillar_entry(request, dept_id, pillar_id):
    """HTMX POST — locks the entire pillar entry for the month"""
    # Sets submitted_at = now(), submitted_by = request.user
    # Returns updated table partial with lock overlay

@login_required
@dept_access_required
def analytics_partial(request, dept_id, pillar_id):
    """HTMX GET — returns analytics charts partial
       Triggered when user clicks Analytics tab"""
    # Aggregates last 12 months of actuals vs targets
    # Returns: _analytics_charts.html with Chart.js JSON data embedded
```

### ws_kpi_views.py

```python
@login_required
@dept_access_required
def ws_kpi_page(request, dept_id):
    """Workstation KPI page — card-based layout, one card per workstation"""

@login_required
@dept_access_required
@require_POST
def save_workstation(request, dept_id, ws_id):
    """HTMX POST — saves all KPI actuals for one workstation card"""
    # Returns updated workstation card partial
```

---

## PART 9 — BUSINESS LOGIC (`tpm/utils/calculations.py`)

```python
LOWER_IS_BETTER_KEYWORDS = [
    'total breakdown', 'mttr', 'total losses', 'rejection', 'rework',
    'response time', 'repetitive breakdown', 'customer complaint',
    'fatal', 'lti', 'mti', 'near miss',
]

def compute_achievement(actual: float, target: float, kpi_name: str) -> float:
    """Returns achievement % (can exceed 100 for over-performers)"""
    lower_is_better = any(
        kw in kpi_name.lower() for kw in LOWER_IS_BETTER_KEYWORDS
    )
    if lower_is_better:
        if target == 0:
            return 100.0 if actual == 0 else 0.0
        return min(100.0, (target / actual) * 100) if actual != 0 else 100.0
    else:
        if target == 0:
            return 100.0
        return (actual / target) * 100

def compute_PRODUCTION(availability: float, performance: float, quality: float) -> float:
    """PRODUCTION = A × P × Q (inputs as percentages, output as percentage)"""
    return (availability / 100) * (performance / 100) * (quality / 100) * 100

def get_status(achievement: float) -> str:
    """Returns 'on-track' | 'at-risk' | 'behind'"""
    if achievement >= 90:
        return 'on-track'
    if achievement >= 75:
        return 'at-risk'
    return 'behind'

def get_status_css_class(status: str) -> str:
    return {
        'on-track': 'badge-green',
        'at-risk':  'badge-amber',
        'behind':   'badge-red',
    }.get(status, '')
```

---

## PART 10 — KPI DEFINITIONS (`tpm/utils/kpi_definitions.py`)

```python
# This is the single source of truth for all KPI structures.
# Never hardcode KPI names or sl_no values in templates or views.

KPI_DEFINITIONS = {
    'KK': [
        {'sl_no': '1',  'name': 'Overall equipment efficiency-OEE(%)', 'uom': '%',
         'benchmark': 80.0, 'target': 90.0, 'is_PRODUCTION_row': True},
        {'sl_no': '2',  'name': 'Productivity (Ton/Man or MWh/Man) (considering Company Employee only)', 'uom': 'Ton/Man',
         'benchmark': 480.0, 'target': 460.0},
        {'sl_no': '5',  'name': 'Total losses [Updation of Loss Tree] (Hrs.)', 'uom': 'Hrs',
         'benchmark': 250.0, 'target': 0.0},
        {'sl_no': '6',  'name': 'Kobetsu Kaizen registered (Nos.)', 'uom': 'Nos',
         'benchmark': 3.0, 'target': 3.0},
        {'sl_no': '7',  'name': 'Kobetsu Kaizen completed (Nos.)', 'uom': 'Nos',
         'benchmark': 3.0, 'target': 3.0},
        {'sl_no': '8',  'name': 'Total Saving through Kaizen (Rs.)', 'uom': 'Rs',
         'benchmark': 500000.0, 'target': 200000.0},
        {'sl_no': '10', 'name': 'Training on KK to improve the performance (Man Hours)', 'uom': 'Man Hours',
         'benchmark': 10.0, 'target': 20.0},
    ],
    'JH': [
        {'sl_no': '1',   'name': 'Compliance of JH Steps as per JH Master Plan (% [Actual/Planned])', 'uom': '%',
         'benchmark': 100.0, 'target': 100.0},
        {'sl_no': '2',   'name': 'White Fuguai Identified (Nos./month)', 'uom': 'Nos/month',
         'benchmark': 1200.0, 'target': 1200.0},
        {'sl_no': '3',   'name': 'White Fuguai Rectified (Nos./month)', 'uom': 'Nos/month',
         'benchmark': 1200.0, 'target': 1200.0},
        {'sl_no': '4',   'name': 'Red Fuguai Identified (Nos./month)', 'uom': 'Nos/month',
         'benchmark': 100.0, 'target': 100.0},
        {'sl_no': '5',   'name': 'Red Fuguai Rectified (Nos./month)', 'uom': 'Nos/month',
         'benchmark': 100.0, 'target': 100.0},
        {'sl_no': '6',   'name': 'JH Kaizen Completed (Nos.)', 'uom': 'Nos',
         'benchmark': 50.0, 'target': 50.0},
        {'sl_no': '7',   'name': 'OPL Developed (Nos.)', 'uom': 'Nos',
         'benchmark': 50.0, 'target': 50.0},
        {'sl_no': '8A',  'name': 'Rank A machine with JH Step 1 Completed (Nos.)', 'uom': 'Nos',
         'benchmark': 0.0, 'target': 0.0},
        {'sl_no': '8B',  'name': 'Rank A machine with JH Step 2 Completed (Nos.)', 'uom': 'Nos',
         'benchmark': 0.0, 'target': 0.0},
        {'sl_no': '8C',  'name': 'Rank A machine with JH Step 3 Completed (Nos.)', 'uom': 'Nos',
         'benchmark': 0.0, 'target': 0.0},
        {'sl_no': '9A',  'name': 'Rank B machine with JH Step 1 Completed (Nos.)', 'uom': 'Nos',
         'benchmark': 0.0, 'target': 0.0},
        {'sl_no': '9B',  'name': 'Rank B machine with JH Step 2 Completed (Nos.)', 'uom': 'Nos',
         'benchmark': 0.0, 'target': 0.0},
        {'sl_no': '9C',  'name': 'Rank B machine with JH Step 3 Completed (Nos.)', 'uom': 'Nos',
         'benchmark': 0.0, 'target': 0.0},
        {'sl_no': '10A', 'name': 'Rank C machine with JH Step 1 Completed (Nos.)', 'uom': 'Nos',
         'benchmark': 0.0, 'target': 0.0},
        {'sl_no': '10B', 'name': 'Rank C machine with JH Step 2 Completed (Nos.)', 'uom': 'Nos',
         'benchmark': 0.0, 'target': 0.0},
        {'sl_no': '10C', 'name': 'Rank C machine with JH Step 3 Completed (Nos.)', 'uom': 'Nos',
         'benchmark': 0.0, 'target': 0.0},
        {'sl_no': '11',  'name': 'Training on JH to improve the performance (Man hours)', 'uom': 'Man hours',
         'benchmark': 100.0, 'target': 100.0},
    ],
    'PM': [
        {'sl_no': '1',  'name': 'Total breakdown nos. (Rank A + B + C machine)', 'uom': 'Nos',
         'benchmark': 25.0, 'target': 0.0},
        {'sl_no': '2',  'name': 'Total breakdown hours (Rank A + B + C machine)', 'uom': 'Hrs',
         'benchmark': 30.0, 'target': 0.0},
        {'sl_no': '3',  'name': 'No. of Machine with Repetitive breakdown (Nos./month)', 'uom': 'Nos/month',
         'benchmark': 0.0, 'target': 0.0},
        {'sl_no': '4',  'name': 'MTTR (Hours)', 'uom': 'Hrs',
         'benchmark': 1.15, 'target': 0.0},
        {'sl_no': '5',  'name': 'MTBF (Hours)', 'uom': 'Hrs',
         'benchmark': 48.08, 'target': 60.0},
        {'sl_no': '8',  'name': 'Equipment Availability (%)', 'uom': '%',
         'benchmark': 92.0, 'target': 100.0},
        {'sl_no': '9',  'name': 'CAPA Made (Nos.)', 'uom': 'Nos',
         'benchmark': 6.0, 'target': 5.0},
        {'sl_no': '10', 'name': 'PM Kaizen done (Nos.)', 'uom': 'Nos',
         'benchmark': 2.0, 'target': 2.0},
        {'sl_no': '11', 'name': 'One point Lesson (Nos.)', 'uom': 'Nos',
         'benchmark': 2.0, 'target': 2.0},
        {'sl_no': '13', 'name': 'Shutdown Maintenance rate (%)', 'uom': '%',
         'benchmark': 100.0, 'target': 100.0},
        {'sl_no': '14', 'name': 'PM Schedule compliance [as per SAP] (%)', 'uom': '%',
         'benchmark': 100.0, 'target': 100.0},
        {'sl_no': '15', 'name': 'Training on PM to improve the performance (Man hours)', 'uom': 'Man hours',
         'benchmark': 75.0, 'target': 30.0},
        {'sl_no': '16', 'name': 'Number of Breakdowns >= 30 minutes (nos.)', 'uom': 'Nos',
         'benchmark': 5.0, 'target': 0.0},
    ],
    'QM': [
        {'sl_no': '1A', 'name': 'Customer complaint (Matric T/Dispatched Qty.), %', 'uom': '%',
         'benchmark': None, 'target': None},
        {'sl_no': '1B', 'name': 'Response time to customer against complaint (Days)', 'uom': 'Days',
         'benchmark': None, 'target': None},
        {'sl_no': '2',  'name': 'Rejection (%)', 'uom': '%',
         'benchmark': None, 'target': None},
        {'sl_no': '3',  'name': 'Rework (%)', 'uom': '%',
         'benchmark': None, 'target': None},
        {'sl_no': '4',  'name': 'QM Kaizen/Project taken (Nos.)', 'uom': 'Nos',
         'benchmark': None, 'target': None},
        {'sl_no': '5',  'name': 'QA Matrix developed (Nos.)', 'uom': 'Nos',
         'benchmark': None, 'target': None},
        {'sl_no': '6',  'name': 'Training on QM to improve the performance (Man hours)', 'uom': 'Man hours',
         'benchmark': None, 'target': None},
    ],
    'ET': [
        {'sl_no': '1',  'name': 'Compliance of Skill evaluation of employees (%)', 'uom': '%',
         'benchmark': 97.0, 'target': 100.0},
        {'sl_no': '2',  'name': 'Trainings (Depts. Classroom) during the month (Nos. Actual/Planned)', 'uom': 'Nos',
         'benchmark': 13.0, 'target': 4.0},
        {'sl_no': '3',  'name': 'Employees covered (Depts. Classroom) during the month (%)', 'uom': '%',
         'benchmark': 0.80, 'target': 1.0},
        {'sl_no': '4',  'name': 'Training Man-hours (Man hrs./Emp.)', 'uom': 'Man hrs/Emp',
         'benchmark': 0.80, 'target': 1.0},
        {'sl_no': '5',  'name': 'On-The-Job Training during the month (Nos.)', 'uom': 'Nos',
         'benchmark': 10.0, 'target': 1.0},
        {'sl_no': '6',  'name': 'Employees covered (On the job) during the month (%)', 'uom': '%',
         'benchmark': 25.0, 'target': 20.0},
        {'sl_no': '7',  'name': "OPL's developed during the month (Including all Pillar) (Nos.)", 'uom': 'Nos',
         'benchmark': 1.0, 'target': 1.0},
        {'sl_no': '8A', 'name': 'Multi skilled Manpower_Uni-athlete (%)', 'uom': '%',
         'benchmark': 100.0, 'target': 100.0},
        {'sl_no': '8B', 'name': 'Multi skilled Manpower_Bi-athlete (%)', 'uom': '%',
         'benchmark': 92.0, 'target': 80.0},
        {'sl_no': '8C', 'name': 'Multi skilled Manpower_Tri-athlete (%)', 'uom': '%',
         'benchmark': 60.0, 'target': 60.0},
        {'sl_no': '9',  'name': 'Skill Gap of Employee (0-5) (Score)', 'uom': 'Score',
         'benchmark': 2.0, 'target': 2.0},
        {'sl_no': '10', 'name': 'In-house trainers developed (Annual) (Nos.)', 'uom': 'Nos',
         'benchmark': 4.0, 'target': 2.0},
        {'sl_no': '11', 'name': 'Training on E&T to improve the performance (quarterly) (Nos.)', 'uom': 'Nos',
         'benchmark': 1.0, 'target': 1.0},
    ],
    'DM': [
        {'sl_no': '1', 'name': 'Sales from upgraded & New products over total sales (Nos.)', 'uom': 'Nos',
         'benchmark': 0.0, 'target': 0.0},
        {'sl_no': '2', 'name': 'New product developments (Percentage)', 'uom': '%',
         'benchmark': 0.0, 'target': 0.0},
        {'sl_no': '3', 'name': 'Design related complaints/failures (Nos.)', 'uom': 'Nos',
         'benchmark': 0.0, 'target': 0.0},
        {'sl_no': '4', 'name': 'New equipment/process developed (Nos.)', 'uom': 'Nos',
         'benchmark': 0.0, 'target': 0.0},
        {'sl_no': '5', 'name': 'Modification done in existing equipment/processes (Nos.)', 'uom': 'Nos',
         'benchmark': 0.0, 'target': 0.0},
        {'sl_no': '6', 'name': 'Number of MP Sheet Developed (Nos.)', 'uom': 'Nos',
         'benchmark': 0.0, 'target': 0.0},
        {'sl_no': '7', 'name': 'Number of LCC Sheet Developed (Nos.)', 'uom': 'Nos',
         'benchmark': 0.0, 'target': 0.0},
        {'sl_no': '8', 'name': 'Training on DM to improve the performance (Nos.)', 'uom': 'Nos',
         'benchmark': 0.0, 'target': 0.0},
    ],
    'SHE': [
        {'sl_no': '1A', 'name': 'Safety Observations made (Nos.)', 'uom': 'Nos', 'benchmark': None, 'target': None},
        {'sl_no': '1B', 'name': 'Safety Observations rectified (Nos.)', 'uom': 'Nos', 'benchmark': None, 'target': None},
        {'sl_no': '1C', 'name': 'Number of Near Misses Reported (Nos.)', 'uom': 'Nos', 'benchmark': None, 'target': None},
        {'sl_no': '2A', 'name': 'Numbers of Fatal accidents (Nos.)', 'uom': 'Nos', 'benchmark': None, 'target': None},
        {'sl_no': '2B', 'name': 'Numbers of reportable accidents (LTI) (Nos.)', 'uom': 'Nos', 'benchmark': None, 'target': None},
        {'sl_no': '2C', 'name': 'Numbers of MTI & First Aid Cases (Nos.)', 'uom': 'Nos', 'benchmark': None, 'target': None},
        {'sl_no': '3A', 'name': 'Employee (below executive) health check-up compliance adherence (%), monthly', 'uom': '%', 'benchmark': None, 'target': None},
        {'sl_no': '3B', 'name': 'Employee (executive & above) health check-up compliance adherence (%), Quarterly', 'uom': '%', 'benchmark': None, 'target': None},
        {'sl_no': '3C', 'name': 'Electrical Energy consumed (MWH) in PCDs-Pollution Control Devices', 'uom': 'MWH', 'benchmark': None, 'target': None},
        {'sl_no': '4',  'name': 'Compliance of Monitoring of environment parameters (as per limits)', 'uom': '', 'benchmark': None, 'target': None},
        {'sl_no': '5',  'name': 'Water Consumption (kL/Ton)', 'uom': 'kL/Ton', 'benchmark': None, 'target': None},
        {'sl_no': '6',  'name': 'Dust level monitoring at workplace (ug/M3)', 'uom': 'ug/M3', 'benchmark': None, 'target': None},
        {'sl_no': '7',  'name': 'Noise level monitoring (db)', 'uom': 'db', 'benchmark': None, 'target': None},
        {'sl_no': '8',  'name': 'Low Illuminated area identified (Nos.)', 'uom': 'Nos', 'benchmark': None, 'target': None},
        {'sl_no': '9',  'name': 'Low Illuminated area rectified (Nos.)', 'uom': 'Nos', 'benchmark': None, 'target': None},
        {'sl_no': '10', 'name': 'Dust level monitoring at stacks (mg/M3)', 'uom': 'mg/M3', 'benchmark': None, 'target': None},
        {'sl_no': '11', 'name': 'No. of Kaizen themes or improvement project taken for improvement in Safety (Nos.)', 'uom': 'Nos', 'benchmark': None, 'target': None},
        {'sl_no': '12', 'name': 'Training on SHE (Man hours)', 'uom': 'Man hours', 'benchmark': None, 'target': None},
    ],
    'OTPM': [
        {'sl_no': '1',  'name': 'Losses Identified in Office TPM process (Hours)', 'uom': 'Hours', 'benchmark': 0.0, 'target': 0.0},
        {'sl_no': '2',  'name': 'Losses rectified in Office TPM process (Hours)', 'uom': 'Hours', 'benchmark': 0.0, 'target': 0.0},
        {'sl_no': '3',  'name': 'No. of Kaizen themes/improvement project taken/registered for reduction in losses', 'uom': 'Nos', 'benchmark': 0.0, 'target': 0.0},
        {'sl_no': '4',  'name': 'No. of Kaizen themes/improvement project completed for reduction in losses', 'uom': 'Nos', 'benchmark': 0.0, 'target': 0.0},
        {'sl_no': '5',  'name': 'OPL/SOPs prepared and displayed (Nos.)', 'uom': 'Nos', 'benchmark': 0.0, 'target': 0.0},
        {'sl_no': '6',  'name': 'Fuguai identified (Nos.)', 'uom': 'Nos', 'benchmark': 0.0, 'target': 0.0},
        {'sl_no': '7',  'name': 'Fuguai rectified (Nos.)', 'uom': 'Nos', 'benchmark': 0.0, 'target': 0.0},
        {'sl_no': '8',  'name': 'Area/Store/Offices identified for 1S (Nos.)', 'uom': 'Nos', 'benchmark': 0.0, 'target': 0.0},
        {'sl_no': '9',  'name': 'Area/Store/Offices completed for 1S (Nos.)', 'uom': 'Nos', 'benchmark': 0.0, 'target': 0.0},
        {'sl_no': '10', 'name': 'Area/Store/Offices identified for 2S (Nos.)', 'uom': 'Nos', 'benchmark': 0.0, 'target': 0.0},
        {'sl_no': '11', 'name': 'Area/Store/Offices completed for 2S (Nos.)', 'uom': 'Nos', 'benchmark': 0.0, 'target': 0.0},
        {'sl_no': '12', 'name': 'Area/Store/Offices identified for 3S (Nos.)', 'uom': 'Nos', 'benchmark': 0.0, 'target': 0.0},
        {'sl_no': '13', 'name': 'Area/Store/Offices completed for 3S (Nos.)', 'uom': 'Nos', 'benchmark': 0.0, 'target': 0.0},
        {'sl_no': '14', 'name': 'Area/Store/Offices identified for 4S (Nos.)', 'uom': 'Nos', 'benchmark': 0.0, 'target': 0.0},
        {'sl_no': '15', 'name': 'Area/Store/Offices completed for 4S (Nos.)', 'uom': 'Nos', 'benchmark': 0.0, 'target': 0.0},
        {'sl_no': '16', 'name': 'Area/Store/Offices identified for 5S (Nos.)', 'uom': 'Nos', 'benchmark': 0.0, 'target': 0.0},
        {'sl_no': '17', 'name': 'Area/Store/Offices completed for 5S (Nos.)', 'uom': 'Nos', 'benchmark': 0.0, 'target': 0.0},
        {'sl_no': '18', 'name': 'Area (Contractors) identify for 1S (Nos.)', 'uom': 'Nos', 'benchmark': 0.0, 'target': 0.0},
        {'sl_no': '19', 'name': 'Area (Contractors) completed for 1S (Nos.)', 'uom': 'Nos', 'benchmark': 0.0, 'target': 0.0},
        {'sl_no': '20', 'name': 'Area (Contractors) identify for 2S (Nos.)', 'uom': 'Nos', 'benchmark': 0.0, 'target': 0.0},
        {'sl_no': '21', 'name': 'Area (Contractors) completed for 2S (Nos.)', 'uom': 'Nos', 'benchmark': 0.0, 'target': 0.0},
        {'sl_no': '22', 'name': 'Area (Contractors) identify for 3S (Nos.)', 'uom': 'Nos', 'benchmark': 0.0, 'target': 0.0},
        {'sl_no': '23', 'name': 'Area (Contractors) completed for 3S (Nos.)', 'uom': 'Nos', 'benchmark': 0.0, 'target': 0.0},
        {'sl_no': '24', 'name': 'Training on OTPM to improve the performance (Man hours)', 'uom': 'Man hours', 'benchmark': 0.0, 'target': 0.0},
    ],
}
```

---

## PART 11 — JSPL BRAND / VISUAL THEME

Primary reference: https://www.jindalsteel.in/chhattisgarh

```css
/* tpm/static/css/tpm.css — JSPL Color Tokens */
:root {
  --jspl-navy:   #003478;   /* Primary — headers, sidebar, buttons */
  --jspl-blue:   #0057A8;   /* Secondary blue */
  --jspl-orange: #F47920;   /* Accent — CTA, highlights, active states */
  --jspl-light:  #E8F0FA;   /* Background tints */
  --jspl-white:  #FFFFFF;
  --jspl-gray:   #F4F6F9;   /* Page background */
  --jspl-border: #D1DCF0;
  --jspl-text:   #1A2640;   /* Body text */
  --jspl-muted:  #6B7A99;

  /* Status colors */
  --status-green: #16A34A;
  --status-amber: #D97706;
  --status-red:   #DC2626;
  --status-blue:  #2563EB;
}
```

Sidebar: `--jspl-navy` background, white text, `--jspl-orange` active indicator.
Topbar: White with `--jspl-navy` text, `--jspl-orange` accent.
Cards: White surface, `--jspl-border` border, subtle shadow.
All numeric KPI values: `JetBrains Mono` font.
All headings/labels: `Sora` font.

---

## PART 12 — TEMPLATE STRUCTURE (HTMX Pattern)

### base.html (Shell Layout — all authenticated pages)

```html
{# base.html #}
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>JSPL TPM Portal</title>
  <link rel="stylesheet" href="{% static 'css/tpm.css' %}">
  <!-- Google Fonts, HTMX, Alpine.js, Chart.js from CDN (see Part 4) -->
</head>
<body>
  <!-- TOPBAR (60px, sticky) -->
  <header id="topbar">
    <img src="{% static 'img/jspl_logo.png' %}" alt="JSPL">
    <nav class="breadcrumb">{% block breadcrumb %}{% endblock %}</nav>
    <div class="user-menu">
      {{ request.user.get_full_name }} |
      <a href="{% url 'logout' %}">Logout</a>
    </div>
  </header>

  <div id="shell">
    <!-- SIDEBAR (240px) -->
    <aside id="sidebar" x-data="sidebarState()">
      <div class="sidebar-logo">TPM Portal</div>
      {% if request.user.is_admin %}
        <a href="{% url 'plant_dashboard' %}">🏭 Plant Overview</a>
      {% endif %}
      <!-- Department accordion — rendered server-side, Alpine handles open/close -->
      {% for dept in sidebar_departments %}
        <div x-data="{ open: {{ dept.id }} == {{ active_dept_id|default:0 }} }">
          <button @click="open = !open" class="dept-accordion-btn">
            <span>{{ dept.name }}</span>
            <span x-text="open ? '▲' : '▼'"></span>
          </button>
          <div x-show="open" x-transition>
            {% for pillar in pillars %}
              <a href="{% url 'pillar_page' dept.id pillar.id %}">{{ pillar.label }}</a>
            {% endfor %}
            <a href="{% url 'ws_kpi_page' dept.id %}">Workstation KPI</a>
          </div>
        </div>
      {% endfor %}
    </aside>

    <!-- MAIN CONTENT -->
    <main id="content">
      <!-- HTMX response toasts (OOB swap target) -->
      <div id="toast-container" aria-live="polite"></div>
      {% block content %}{% endblock %}
    </main>
  </div>

  {% block extra_js %}{% endblock %}
</body>
</html>
```

### partials/_kpi_table.html (HTMX partial — swapped on month/year change)

```html
{# Targeted by: hx-target="#kpi-table-container" #}
<div id="kpi-table-container">
  {% if is_locked %}
    <div class="lock-banner">
      🔒 Submitted on {{ entry.submitted_at|date:"d M Y H:i" }} by {{ entry.submitted_by.get_full_name }}
      {% if request.user.is_admin %}
        <button hx-post="{% url 'unlock_entry' entry.id %}"
                hx-target="#kpi-table-container"
                hx-confirm="Unlock this entry for editing?">
          Unlock
        </button>
      {% else %}
        <span class="muted">Contact admin to edit</span>
      {% endif %}
    </div>
  {% endif %}

  <table class="kpi-table">
    <thead>
      <tr>
        <th>Sl No.</th>
        <th>KPI (UOM)</th>
        <th>Benchmark</th>
        <th>Target</th>
        <th>Actual</th>
        {% if pillar_id == 'KK' %}<th>Avail.</th><th>Perf.</th><th>Quality</th>{% endif %}
        <th>Achievement</th>
        <th>Remarks</th>
      </tr>
    </thead>
    <tbody>
      {% for row in kpi_rows %}
        {% include "partials/_kpi_row.html" with row=row is_locked=is_locked %}
      {% endfor %}
    </tbody>
  </table>

  {% if not is_locked %}
    <button class="btn-primary"
            hx-post="{% url 'submit_pillar_entry' dept.id pillar_id %}?month={{ month }}&year={{ year }}"
            hx-target="#kpi-table-container"
            hx-confirm="Submit and lock data for {{ month_label }} {{ year }}?">
      Submit & Lock
    </button>
  {% endif %}
</div>
```

### partials/_kpi_row.html (HTMX partial — swapped on inline save)

```html
{# Each <tr> is independently HTMX-saveable via hx-trigger="blur" #}
<tr id="row-{{ row.sl_no }}"
    x-data="kpiRow({ actual: {{ row.actual|default:'null' }}, target: {{ row.target|default:'null' }}, kpiName: '{{ row.kpi_name|escapejs }}', isPRODUCTIONRow: {{ row.is_PRODUCTION_row|yesno:'true,false' }} })">

  <td class="mono">{{ row.sl_no }}</td>
  <td>{{ row.kpi_name }}<br><small class="muted">{{ row.uom }}</small></td>
  <td class="mono">{{ row.benchmark|default:"—" }}</td>
  <td class="mono">
    {% if request.user.is_admin %}
      <input type="number" name="target" value="{{ row.target|default:'' }}"
             class="input-mono"
             hx-post="{% url 'save_kpi_row' dept.id pillar_id %}?month={{ month }}&year={{ year }}&sl_no={{ row.sl_no }}"
             hx-trigger="blur" hx-target="#row-{{ row.sl_no }}" hx-swap="outerHTML"
             {% if is_locked %}disabled{% endif %}>
    {% else %}
      <span class="mono">{{ row.target|default:"—" }}</span>
    {% endif %}
  </td>
  <td>
    <input type="number" name="actual" x-model="actual" step="any"
           value="{{ row.actual|default:'' }}" class="input-mono"
           hx-post="{% url 'save_kpi_row' dept.id pillar_id %}?month={{ month }}&year={{ year }}&sl_no={{ row.sl_no }}"
           hx-trigger="blur" hx-include="closest tr"
           hx-target="#row-{{ row.sl_no }}" hx-swap="outerHTML"
           {% if is_locked %}disabled{% endif %}>
  </td>

  {% if pillar_id == 'KK' %}
  <td>
    <input type="number" name="availability" x-model="availability" step="any"
           value="{{ row.availability|default:'' }}" class="input-mono"
           {% if row.sl_no != '1' or is_locked %}disabled{% endif %}
           @input="computePRODUCTION()">
  </td>
  <td>
    <input type="number" name="performance" x-model="performance" step="any"
           value="{{ row.performance|default:'' }}" class="input-mono"
           {% if row.sl_no != '1' or is_locked %}disabled{% endif %}
           @input="computePRODUCTION()">
  </td>
  <td>
    <input type="number" name="quality" x-model="quality" step="any"
           value="{{ row.quality|default:'' }}" class="input-mono"
           {% if row.sl_no != '1' or is_locked %}disabled{% endif %}
           @input="computePRODUCTION()">
  </td>
  {% endif %}

  <td>
    <!-- Achievement badge: computed client-side by Alpine.js immediately on input -->
    <span class="badge" :class="achievementClass()" x-text="achievementLabel()"></span>
  </td>
  <td>
    <textarea name="remarks" rows="1" class="input-remarks"
              hx-post="{% url 'save_kpi_row' dept.id pillar_id %}?month={{ month }}&year={{ year }}&sl_no={{ row.sl_no }}"
              hx-trigger="blur" hx-include="closest tr"
              hx-target="#row-{{ row.sl_no }}" hx-swap="outerHTML"
              {% if is_locked %}disabled{% endif %}>{{ row.remarks }}</textarea>
  </td>
</tr>
```

---

## PART 13 — USER ROLES & AUTH

### Two Roles

**ADMIN**
- Sees complete plant-wide dashboard
- Can access ALL 25 departments
- Can EDIT data for any department any pillar
- Can manage users (create/edit/delete department users)
- Sees audit trail of all submissions
- Can export any report for any dept

**USER (Department User)**
- Locked to their own department (enforced server-side via session)
- Cannot see other departments' data (except plant-wide summary which shows aggregate only)
- Can EDIT data only for their own department's pillars
- Can VIEW analytics for their own department
- Can generate reports for their own department

### Access Control Decorators

```python
# tpm/utils/decorators.py

from functools import wraps
from django.core.exceptions import PermissionDenied
from django.contrib.auth.decorators import login_required

def admin_required(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_admin():
            raise PermissionDenied
        return view_func(request, *args, **kwargs)
    return wrapper

def dept_access_required(view_func):
    """Admin passes through. USER must own the requested dept_id."""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        dept_id = kwargs.get('dept_id')
        if not request.user.is_admin():
            if request.user.department_id != dept_id:
                raise PermissionDenied
        return view_func(request, *args, **kwargs)
    return wrapper
```

### Login Page
JSPL-branded login:
- JSPL logo top center
- "TPM Analytics Portal" title
- Email + Password fields
- Django `authenticate()` + `login()` (credentials auth)
- On success → redirect based on role:
  - ADMIN → `/dashboard` (plant-wide view)
  - USER → `/department/<dept_id>` (their dept dashboard)
- Session persistence: `SESSION_COOKIE_AGE = 28800` (8-hour expiry in settings.py)

---

## PART 14 — APPLICATION ROUTES (All Pages)

```
/                          → redirect to /login (or dept/dashboard if logged in)
/login/                    → Login page
/logout/                   → Logout
/dashboard/                → Plant-wide admin dashboard (admin only)
/department/<dept_id>/                              → Department overview
/department/<dept_id>/pillar/<pillar_id>/           → Pillar KPI entry + analytics
/department/<dept_id>/pillar/ws-kpi/               → Workstation KPI (special layout)
/department/<dept_id>/report/                       → Report generator for dept
/department/<dept_id>/report/pdf/                   → Download PDF
/department/<dept_id>/report/excel/                 → Download Excel
/admin-panel/users/                                 → User management (admin only)
/admin-panel/users/add/                             → Add user form
/admin-panel/users/<user_id>/edit/                  → Edit user
/admin-panel/departments/                           → Department config (admin only)
/admin-panel/unlock-entry/<entry_id>/               → HTMX: unlock a locked entry
```

---

## PART 15 — PAGE SPECIFICATIONS

### PAGE 1 — PLANT-WIDE DASHBOARD (`/dashboard/`) [ADMIN ONLY]

**Section 1: Summary KPI Ribbon (4 cards across)**
- Plant Overall PRODUCTION % (aggregated KK pillar row 1 across all depts)
- Total Kaizens Implemented YTD (sum across all KK pillars)
- SHE: Zero LTI count (green if 0, red if >0)
- PM Compliance % (average PM pillar row 14 across depts)

**Section 2: Department Status Grid (28 cards)**
One card per department showing:
- Department name
- Overall achievement % (average of all 9 pillar scores)
- Colored status badge: On Track (≥90%) / At Risk (75–89%) / Behind (<75%)
- Mini sparkline (Chart.js inline mini chart, last 6 months)
- Clicking opens `/department/<dept_id>/`

**Section 3: Charts Row (rendered with Chart.js)**
Left (60%): Monthly Plant PRODUCTION trend — line chart, Jan–Dec, actual vs target (85%)
Right (40%): Pillar radar — 9 axes (8 pillars + WS KPI), plant average per pillar

**Section 4: Department Compliance Heatmap**
Rows: 28 departments
Columns: Last 6 months
Cell: % achievement, colored green/amber/red with CSS
Hover detail via Alpine.js tooltip

**Section 5: Top/Bottom Performance Table**
- Recent month's top performing and bottom performing departments
- Any SHE incidents flagged in red

---

### PAGE 2 — DEPARTMENT OVERVIEW (`/department/<dept_id>/`)

**Header Bar:** Department name + current month/year selector + "Add Entry" button

**Pillar Status Grid (9 cards — one per pillar)**
Card contains: pillar name, icon, score%, status badge, mini progress bar.
Clicking a card → navigates to that pillar's detail page.

**Charts Section**
Left: Department's own PRODUCTION trend (monthly, Chart.js)
Right: 9-axis radar of this dept's pillar scores (Chart.js)

**Recent Submissions Table**
Last 6 month submissions for this department — all pillars, status (submitted/pending/locked)

---

### PAGE 3 — PILLAR KPI PAGE (`/department/<dept_id>/pillar/<pillar_id>/`)

This page has TWO MODES toggled by tabs using HTMX:

```
[ Data Entry ]  [ Analytics ]
```

Clicking "Analytics" triggers:
```html
<button hx-get="/department/{{ dept.id }}/pillar/{{ pillar_id }}/analytics/?month={{ month }}&year={{ year }}"
        hx-target="#tab-content"
        hx-swap="innerHTML">
  Analytics
</button>
```

**MODE 1: DATA ENTRY TAB**

Filter Bar (top):
```
Department: [SMS-II]    Month: [May ▼]    Year: [2026 ▼]    Data Entry Type: ● Monthly ○ Weekly
```
Month/Year selectors trigger HTMX reload of the KPI table:
```html
<select name="month"
        hx-get="/department/{{ dept.id }}/pillar/{{ pillar_id }}/table/"
        hx-trigger="change"
        hx-target="#kpi-table-container"
        hx-include="[name='month'],[name='year']">
```
Department selector: USER sees locked display; ADMIN sees full dropdown.

KPI Entry Table (see _kpi_table.html and _kpi_row.html partials above).

Rules per pillar:
- Benchmark column: always READ-ONLY (static text, not input)
- Target column: READ-ONLY for users, editable for admin
- Actual column: EDITABLE number input, validated
- Availability / Performance / Quality: only shown for KK Pillar row 1 (PRODUCTION). Hidden for all other rows and all other pillars.
- Remarks: always editable textarea

Validation rules (server-side in Django views + client-side in Alpine.js):
- All numeric inputs: must be valid numbers
- PRODUCTION %: 0–100
- Nos: non-negative integer
- Hours/Man hours: non-negative float
- Rs (currency): non-negative float
- If actual is entered, auto-compute achievement % and display inline
- For KK row 1: if Availability + Performance + Quality entered, auto-compute PRODUCTION = A × P × Q via Alpine.js `computePRODUCTION()`

Achievement indicator (inline, next to Actual input via Alpine.js):
- Green ✓ if actual meets/exceeds target (higher-is-better KPIs)
- Red ✗ if actual is below target
- Amber ~ if within 10% of target

Submit button behavior:
- Validate all required actuals are filled (Django form validation)
- Alpine.js confirmation dialog before HTMX POST
- On confirm: POST to view, entry locked, success toast via HTMX OOB swap
- After submit: data becomes locked for that month (admin can unlock)

**COMPLETE KPI LISTS — use exactly the definitions in Part 10 (kpi_definitions.py)**

**MODE 2: ANALYTICS TAB (HTMX partial swap)**

Row 1: Trend Chart (full width)
Line chart (Chart.js) — monthly trend of each KPI's actual vs target (last 12 months)
- Multi-line (one line per KPI, color-coded)
- Toggle individual KPIs on/off via Chart.js legend
- X-axis: months, Y-axis: value (auto-scaled per KPI)

Row 2: Achievement Bar Chart (left) + KPI Scorecard (right)
Left — Horizontal bar chart: All KPIs for this pillar, sorted by achievement %. Color: green/amber/red.
Right — Scorecard table:
| KPI | Target | Actual | Achievement | Status |
Inline sparkline per KPI showing last 6 months trend.

Row 3: Year-over-Year Comparison (if prior year data exists)
Grouped bar chart (Chart.js): This year vs last year per KPI.

Export buttons: "Export PDF" / "Export Excel" for this analytics view.

---

### PAGE 4 — WORKSTATION KPI PAGE (`/department/<dept_id>/pillar/ws-kpi/`)

This pillar has a fundamentally different layout from the 8 standard pillars.

**Filter Bar:**
```
Plant: [SMS-II ▼]   Month: [May ▼]   Year: [2026 ▼]
```

**Workstation Cards (one card per workstation, Alpine.js accordion):**
```
┌─────────────────────────────────────────────────┐
│ 🏭 Furnace Area           Leader: D. Sao        │
│ Inception: 24.04.2025                           │
├─────┬──────────────┬──────┬───────┬──────┬──────┤
│ KPI │ UOM          │ Base │ Comm. │Actual│Rmrks │
├─────┼──────────────┼──────┼───────┼──────┼──────┤
│Break│ Min/Month    │  177 │   120 │[___] │[___] │
│Fuel │ MCAL/MT      │  421 │   410 │[___] │[___] │
│Zero │ Nos.         │    0 │     0 │[___] │[___] │
└─────┴──────────────┴──────┴───────┴──────┴──────┘
  [Submit Workstation]
```

Goodness indicator (↑ or ↓ icon) shown next to KPI name.
Submit per workstation (not all at once).
Each card submits via HTMX POST, swaps back updated card partial.

Admin Extra: "Add Workstation" / "Add KPI to Workstation" buttons (open modal via HTMX).

**Analytics Mode (WS KPI)**
Workstation Selector (dropdown)
KPI Trend Charts (Chart.js): For selected workstation, each KPI as a separate mini-chart:
- Monthly actual vs commitment (target) line
- Baseline shown as horizontal reference line
- Goodness indicator shown (↑/↓) with appropriate coloring

Summary Table:
All workstations in dept — rows = workstations, columns = KPIs, cells = latest month actual, colored by achievement vs commitment.

---

### PAGE 5 — REPORT GENERATOR (`/department/<dept_id>/report/`)

Controls:
```
Pillar: [All Pillars ▼]   Year: [2026 ▼]   Month: [May ▼]   [Generate Report]
```

Report Output (rendered as Django template, printable):
- Department header with JSPL logo
- Period label
- 4 summary KPI cards (total KPIs / on track / at risk / behind)
- Pillar-by-pillar sections with tables and mini charts (Chart.js)
- Action items list (any KPI with achievement <80% flagged as "Action Required")

Export buttons:
- **PDF:** ReportLab generates a server-side PDF → streamed as `application/pdf` download
- **Excel:** openpyxl generates an `.xlsx` file with one sheet per pillar → streamed as download

---

### PAGE 6 — ADMIN USER MANAGEMENT (`/admin-panel/users/`)

Table of all users with:
- Name, Email, Role, Department, Last Login, Status (Active/Inactive)
- Actions: Edit (HTMX modal), Reset Password, Deactivate

Add User form (HTMX modal):
- Name, Email, Password (auto-generated, shown once)
- Role: Admin / User
- Department: (dropdown of all depts, only shown if Role = User)

---

## PART 16 — ALPINE.JS CLIENT-SIDE LOGIC (`tpm/static/js/tpm.js`)

```javascript
// Alpine.js component for KPI row — achievement badge + PRODUCTION auto-compute
function kpiRow({ actual, target, kpiName, isPRODUCTIONRow }) {
  return {
    actual: actual,
    target: target,
    availability: null,
    performance: null,
    quality: null,

    computePRODUCTION() {
      if (isPRODUCTIONRow && this.availability && this.performance && this.quality) {
        this.actual = (
          (this.availability / 100) *
          (this.performance / 100) *
          (this.quality / 100) * 100
        ).toFixed(2);
      }
    },

    achievement() {
      if (this.actual === null || this.actual === '' || this.target === null) return null;
      const lowerKeywords = ['breakdown','mttr','losses','rejection','rework','response time','repetitive','complaint','fatal','lti','mti','near miss'];
      const lowerIsBetter = lowerKeywords.some(kw => kpiName.toLowerCase().includes(kw));
      if (lowerIsBetter) {
        if (this.target == 0) return this.actual == 0 ? 100 : 0;
        return this.actual != 0 ? Math.min(100, (this.target / this.actual) * 100) : 100;
      } else {
        if (this.target == 0) return 100;
        return (this.actual / this.target) * 100;
      }
    },

    achievementLabel() {
      const a = this.achievement();
      if (a === null) return '—';
      return a.toFixed(1) + '%';
    },

    achievementClass() {
      const a = this.achievement();
      if (a === null) return 'badge-muted';
      if (a >= 90) return 'badge-green';
      if (a >= 75) return 'badge-amber';
      return 'badge-red';
    }
  };
}

// Alpine.js sidebar accordion state
function sidebarState() {
  return {
    // Active dept from URL — set via data attribute on <aside>
    activeDept: document.querySelector('#sidebar').dataset.activeDept || null
  };
}
```

---

## PART 17 — DJANGO SETTINGS (Key Configuration)

```python
# jspl_tpm/settings.py (key sections)

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django_htmx',          # django-htmx middleware
    'crispy_forms',
    'crispy_bootstrap5',
    'tpm',
]

AUTH_USER_MODEL = 'tpm.User'

MIDDLEWARE = [
    # ... standard Django middleware ...
    'django_htmx.middleware.HtmxMiddleware',  # adds request.htmx
    'django_ratelimit.middleware.RatelimitMiddleware',
]

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.environ['DB_NAME'],
        'USER': os.environ['DB_USER'],
        'PASSWORD': os.environ['DB_PASSWORD'],
        'HOST': os.environ.get('DB_HOST', 'localhost'),
        'PORT': os.environ.get('DB_PORT', '5432'),
    }
}

SESSION_COOKIE_AGE = 28800       # 8 hours
SESSION_EXPIRE_AT_BROWSER_CLOSE = False
LOGIN_URL = '/login/'

STATIC_URL = '/static/'
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

CRISPY_ALLOWED_TEMPLATE_PACKS = 'bootstrap5'
CRISPY_TEMPLATE_PACK = 'bootstrap5'

# Rate limiting: 100 requests/min per user
RATELIMIT_VIEW = 'tpm.views.auth_views.ratelimited_view'
```

---

## PART 18 — SEED DATA

Create a Django management command `tpm/management/commands/seed.py` that:

1. Creates 1 admin user: `admin@jspl.com` / `Admin@1234`
2. Creates department users for each dept: e.g. `bf1@jspl.com` / `Dept@1234`
3. Creates all 28 departments (from list in Part 3)
4. Seeds KPI config (benchmark + target defaults) for all 8 standard pillars from `kpi_definitions.py`
5. Seeds 3 months of sample actual data for SMS-2 and Plate Mill (for demo charts)

Run with: `python manage.py seed`

Alternatively, use `fixtures/seed_data.json` with `python manage.py loaddata seed_data`.

---

## PART 19 — SECURITY & PRODUCTION REQUIREMENTS

- All views use `@login_required` — unauthenticated users redirect to `/login/`
- Department access enforced server-side via `@dept_access_required` decorator on every dept/pillar view
- CSRF protection: Django's built-in `{% csrf_token %}` in all forms; HTMX sends CSRF header automatically via `django-htmx`
- Rate limiting: `django-ratelimit` — 100 req/min per user on POST views
- Input sanitization: Django form validation on all inputs; no raw SQL — Django ORM only
- SQL injection prevention: Django ORM parameterized queries throughout
- Session security: `SESSION_COOKIE_HTTPONLY = True`, `SESSION_COOKIE_SECURE = True` (PRODUCTION), `SESSION_COOKIE_SAMESITE = 'Lax'`
- Static files: served via WhiteNoise (no separate nginx config needed for small deployment)
- Mobile responsive: sidebar collapses to bottom nav on mobile (pure CSS media queries, no JS framework needed)
- Print stylesheet: `@media print` in `tpm.css` — hides sidebar/topbar, shows only report content

---

## PART 20 — WHAT NOT TO DO

- Do NOT use Django REST Framework — all views return HTML (HTMX pattern), not JSON API
- Do NOT use React, Vue, or any npm-based frontend — HTMX + Alpine.js only
- Do NOT use class-based views with complex mixins — function-based views are clearer and easier to maintain
- Do NOT use Redux, Zustand, or any JS state management library
- Do NOT hardcode department user access — always check server-side session via `@dept_access_required`
- Do NOT allow Actual values to be submitted without validation (both client Alpine.js + server Django forms)
- Do NOT mix pillar data schemas — each pillar's KPI list is fixed (defined in `kpi_definitions.py`, never in templates)
- Do NOT make the Workstation KPI page look like the standard pillar pages — it has a different data model and card-based layout
- Do NOT use Django templates' `{% block %}` for HTMX partials — partials are standalone `_partial.html` files returned directly by partial views
- Do NOT use `eval()` or raw SQL anywhere

---

## PART 21 — DELIVERABLES EXPECTED FROM ANTIGRAVITY

1. Complete Django 5 project (all files, runnable with `python manage.py runserver`)
2. `tpm/models.py` with all models as specified in Part 5
3. All views in `tpm/views/` (auth, dashboard, department, pillar, ws_kpi, report, admin)
4. All templates in `tpm/templates/` (base, partials, all pages)
5. `tpm/utils/kpi_definitions.py` (complete KPI list from Part 10)
6. `tpm/utils/calculations.py` (achievement %, PRODUCTION, status logic from Part 9)
7. `tpm/utils/export.py` (ReportLab PDF + openpyxl Excel)
8. `tpm/static/css/tpm.css` (JSPL brand tokens + full layout)
9. `tpm/static/js/tpm.js` (Alpine.js components from Part 16)
10. `tpm/management/commands/seed.py` (seed command from Part 18)
11. `requirements.txt` (from Part 4)
12. `README.md` with:
    - Local dev setup instructions (`pip install -r requirements.txt`, DB setup, `migrate`, `seed`, `runserver`)
    - Environment variables list (DB_NAME, DB_USER, DB_PASSWORD, SECRET_KEY, DEBUG)
    - How to add a new KPI: edit `kpi_definitions.py` only
    - How to add a new department: run Django admin or add to `seed.py`
    - How to deploy on a local plant server (Linux, no Docker required)

---

*This prompt is self-contained. Build the complete PRODUCTION portal from this specification.*
*Stack: Django 5 + PostgreSQL + HTMX + Alpine.js + Chart.js. No npm, no React, no TypeScript.*
