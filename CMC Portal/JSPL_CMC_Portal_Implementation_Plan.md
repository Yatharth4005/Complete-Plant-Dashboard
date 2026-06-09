# JSPL CMC (Condition Monitoring Cell) Portal — Complete Implementation Plan
## Antigravity Prompt: Django 5 + HTMX + Alpine.js (Same Stack as TPM)
### Integrated into the Unified JSPL Plant Portal (no separate login)

---

> **Context for Antigravity:**
> The JSPL Unified Plant Portal already exists (built previously — see JSPL_Unified_Portal_Complete_Plan.md).
> The TPM module is already built (see JSPL_TPM_Portal_Django_HTMX_Implementation_Plan.md).
> This document specifies the CMC module — a NEW app to be added alongside TPM.
> When a user clicks "CMC" in the department hub, they land here — no separate login, same session.
>
> **What CMC does today (manual/paper):**
> The Condition Monitoring Cell (CMC) at JSPL Raigarh monitors the health of rotating machinery
> across all plant departments. They currently use three physical registers/logbooks:
> 1. Oil Testing Register — records oil samples collected from gearboxes and compressors
> 2. WDA Report (Wear Debris Analysis) — records wear particle data from oil samples
> 3. Vibration Monitoring Log Sheet — records vibration readings (H/R1, V/R2, Axial) from bearings
>
> They also maintain a Predictive Maintenance Schedule (the Excel file) that shows
> WHICH equipment gets checked on WHICH days of the month, across ALL 28 departments.
>
> **Goal:** Digitize all three logbooks + the PM schedule into a web portal,
> add analytics dashboards, and integrate it with the unified plant portal.

---

## PART 1 — WHAT CMC DOES (Complete Understanding)

### The Three Core Activities

**Activity 1: Vibration Monitoring**
CMC engineers visit equipment on scheduled dates (from the PM Schedule).
They use instruments (ENPAC / SKF / CSI) to measure vibrations at each bearing point.
Per equipment, they record:
- Plant, Equipment name, Instrument used, Report type (Route / On Request)
- Date, Time, "Stored in" (where data is archived in the instrument)
- Bearing points (up to 8 bearing positions per machine)
- For each bearing: Bearing Point label, optional Bearing No., Horizontal/R1, Vertical/R2, Axial readings
- Final Status: OK / NOT OK / UM (Under Monitoring)
- Remarks

**Activity 2: Oil Testing**
CMC collects oil samples from equipment (on request or scheduled).
Laboratory tests measure:
- Viscosity (cSt — e.g. 32 cSt, 46 cSt, 68 cSt, 220 cSt, 320 cSt)
- Moisture (in % or ppm — e.g. <0.1%, <200ppm, >12%)
- NAS (Cleanliness class — e.g. 11, 12, >12)
- Test No. (sequential test number)
- Status: OK / NOT OK
- Notification No. (SAP notification raised if Not OK — e.g. "10469680,Mt")
- Login (who sent the notification — PKA, NT, AG, TS etc.)
- Sent Date (when SAP notification was sent)
- Remarks

**Activity 3: WDA (Wear Debris Analysis)**
WDA is a deeper oil analysis — it looks at the PARTICLES in the oil to identify
what type of wear is occurring (ferrous, non-ferrous, etc.).
WDA is done per equipment with a fixed logbook structure per department.
Each entry records:
- Date, Sample Ratio (e.g. 1:10, 1:100)
- DL (Direct Load reading)
- DS (Direct Sediment reading)
- WPC (Wear Particle Count)
- Slide (used for microscopy)
- Checked By (e.g. NT, PKA, AG, TS)
- Final Status: OK / Need Attention / Not OK / NA
- Notification No. (SAP)
- Sent Login, Sent Date
- Remarks

### The PM Schedule (Predictive Maintenance Schedule)

The Excel file (Sheet: CMC Schedule) is the master schedule for vibration monitoring.
It lists every piece of equipment that CMC monitors, with:

**Equipment Master Fields:**
- Date (day of month when monitoring happens — e.g. "1, 15" means 1st and 15th)
- Department (e.g. PP-3, BF-2, DRI-2, SMS-2, Plate Mill, etc.)
- Equipment Description (e.g. "ID Fan-1, WHRB-11 (RMH Side)")
- Class (A or B — A = critical, B = important)
- SAP Code Mech (mechanical SAP asset code)
- SAP Code Elec (electrical SAP asset code)
- Asset Cost (e.g. "M-2.2L" = Mechanical bearing replacement cost 2.2 Lakh)
- Production Loss (cost of production loss if equipment fails)
- Rating (kW — motor power)
- Frequency: Weekly / Fortnightly / Monthly / Quarterly
- Category: Route monitoring schedule identifier

**Monthly Tracking Grid:**
For each equipment, each month (Apr'26 to Jan'27 in the file) has 4 columns: A, B, C, D.
These represent the 4 scheduled visits per month (e.g. days 1, 8, 15, 22).
Values in cells: day number when monitoring was done, or "NR" (Not Running), "SD" (Shutdown),
"NA" (Not Applicable), "NP" (Not Approachable), or blank (not yet done).

**Total equipment count:** 600+ pieces of equipment across all departments.

### WDA Department Coverage (from Sheet 3):
DRI-1, DRI-2, SMS-2, SMS-3, BF-1, BF-2, PP-1, PP-2, PP-2 Phase-3, PP-3,
SMSP, BSM/SPM, Sinter Plant, LDP, RMH, CM-1, CM-2, Plate Mill, Plate Mill EOTC,
BRM Plant, Cement Plant, SPM (New), Miscellaneous

### Vibration Log Sheet Structure (from official JSPL Form F-520):
```
Header:
  Plant | Equipment | Date | Time
  Instrument: ENPAC / SKF / CSI
  Reported Through | Type: Route / On Request | Stored in

Bearing Grid (multi-column — each column = one bearing point):
  Bearing Point → [BP1] [BP2] [BP3] [BP4] [BP5] [BP6] [BP7] [BP8]
  Bearing No. (Optional)
  Horizontal / R1
  Vertical / R2
  Axial

Status: OK / NOT OK / UM
Remarks
Signature
```

---

## PART 2 — DATABASE MODELS (`cmc/models.py`)

```python
from django.db import models
from portal.models import User, Department  # shared from unified portal


# ─────────────────────────────────────────────────────────
# EQUIPMENT MASTER (from PM Schedule)
# ─────────────────────────────────────────────────────────

class Equipment(models.Model):
    """
    Master list of all equipment monitored by CMC.
    Seeded from the CMC Schedule Excel file (~600+ rows).
    Admin can add/edit via Django admin.
    """
    class EquipmentClass(models.TextChoices):
        A = 'A', 'Class A (Critical)'
        B = 'B', 'Class B (Important)'

    class FrequencyType(models.TextChoices):
        WEEKLY       = 'WEEKLY',       'Weekly'
        FORTNIGHTLY  = 'FORTNIGHTLY',  'Fortnightly'
        MONTHLY      = 'MONTHLY',      'Monthly'
        QUARTERLY    = 'QUARTERLY',    'Quarterly'
        BIMONTHLY    = 'BIMONTHLY',    'Bi-Monthly'

    department         = models.ForeignKey(Department, on_delete=models.CASCADE, related_name='cmc_equipment')
    name               = models.CharField(max_length=300)  # full equipment description
    equipment_class    = models.CharField(max_length=2, choices=EquipmentClass.choices)
    sap_code_mech      = models.CharField(max_length=30, blank=True)
    sap_code_elec      = models.CharField(max_length=30, blank=True)
    asset_cost         = models.CharField(max_length=50, blank=True)   # e.g. "M-2.2L"
    production_loss    = models.CharField(max_length=50, blank=True)   # e.g. "F-3.8L"
    rating_kw          = models.FloatField(null=True, blank=True)       # motor power in kW
    frequency          = models.CharField(max_length=15, choices=FrequencyType.choices)
    scheduled_days     = models.CharField(max_length=50, blank=True)   # e.g. "1, 15" or "2, 9, 16, 23"
    category           = models.CharField(max_length=10, blank=True)   # Route category
    is_active          = models.BooleanField(default=True)
    notes              = models.TextField(blank=True)

    class Meta:
        ordering = ['department__name', 'name']

    def __str__(self):
        return f"{self.department.code} — {self.name}"


class EquipmentBearingPoint(models.Model):
    """
    Each equipment can have 1–8 named bearing points for vibration measurement.
    Pre-defined when equipment is set up; used as column headers in vibration entry.
    """
    equipment     = models.ForeignKey(Equipment, on_delete=models.CASCADE, related_name='bearing_points')
    label         = models.CharField(max_length=100)  # e.g. "DE", "NDE", "Pump Bearing", "Motor NDE"
    bearing_no    = models.CharField(max_length=50, blank=True)   # optional bearing number
    sort_order    = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ['sort_order']

    def __str__(self):
        return f"{self.equipment.name} → {self.label}"


# ─────────────────────────────────────────────────────────
# PM SCHEDULE TRACKING (which equipment was checked when)
# ─────────────────────────────────────────────────────────

class PMScheduleEntry(models.Model):
    """
    Tracks whether equipment was monitored on a given date.
    One record per equipment per visit.
    Status mirrors the Excel grid: done date / NR / SD / NA / NP / blank
    """
    class VisitStatus(models.TextChoices):
        DONE            = 'DONE',   'Completed'
        NOT_RUNNING     = 'NR',     'Not Running'
        SHUTDOWN        = 'SD',     'Shutdown'
        NOT_APPLICABLE  = 'NA',     'Not Applicable'
        NOT_APPROACHABLE = 'NP',    'Not Approachable'
        PENDING         = 'PENDING', 'Pending'

    equipment     = models.ForeignKey(Equipment, on_delete=models.CASCADE, related_name='schedule_entries')
    scheduled_date = models.DateField()
    actual_date   = models.DateField(null=True, blank=True)
    status        = models.CharField(max_length=15, choices=VisitStatus.choices, default='PENDING')
    done_by       = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL)
    notes         = models.TextField(blank=True)

    class Meta:
        unique_together = ('equipment', 'scheduled_date')
        ordering = ['scheduled_date']


# ─────────────────────────────────────────────────────────
# VIBRATION MONITORING LOG
# ─────────────────────────────────────────────────────────

class VibrationLog(models.Model):
    """
    One vibration monitoring session for one piece of equipment.
    Digitizes the JSPL Form F-520 (Vibration Monitoring Log Sheet).
    """
    class InstrumentType(models.TextChoices):
        ENPAC = 'ENPAC', 'ENPAC'
        SKF   = 'SKF',   'SKF'
        CSI   = 'CSI',   'CSI'
        OTHER = 'OTHER', 'Other'

    class ReportType(models.TextChoices):
        ROUTE      = 'ROUTE',      'Route'
        ON_REQUEST = 'ON_REQUEST', 'On Request'

    class VibrationStatus(models.TextChoices):
        OK            = 'OK',         'OK'
        NOT_OK        = 'NOT_OK',     'Not OK'
        UNDER_MONITOR = 'UM',         'Under Monitoring (UM)'
        NEED_ATTENTION = 'ATTENTION', 'Need Attention'

    equipment       = models.ForeignKey(Equipment, on_delete=models.CASCADE, related_name='vibration_logs')
    date            = models.DateField()
    time            = models.TimeField(null=True, blank=True)
    instrument      = models.CharField(max_length=10, choices=InstrumentType.choices)
    report_type     = models.CharField(max_length=15, choices=ReportType.choices, default='ROUTE')
    stored_in       = models.CharField(max_length=100, blank=True)  # instrument data storage ref
    reported_through = models.CharField(max_length=100, blank=True)  # who requested
    status          = models.CharField(max_length=15, choices=VibrationStatus.choices)
    remarks         = models.TextField(blank=True)
    entered_by      = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL)
    created_at      = models.DateTimeField(auto_now_add=True)

    # Link to PM schedule visit (optional — if this was a scheduled visit)
    schedule_entry  = models.OneToOneField(
        PMScheduleEntry, null=True, blank=True,
        on_delete=models.SET_NULL, related_name='vibration_log'
    )

    class Meta:
        ordering = ['-date', 'equipment__name']


class VibrationReading(models.Model):
    """
    One row in the vibration log grid — readings for one bearing point.
    Each VibrationLog can have 1–8 VibrationReadings (one per bearing point).
    """
    vibration_log   = models.ForeignKey(VibrationLog, on_delete=models.CASCADE, related_name='readings')
    bearing_point   = models.ForeignKey(
        EquipmentBearingPoint, null=True, blank=True,
        on_delete=models.SET_NULL
    )
    bearing_label   = models.CharField(max_length=100)  # stored as text in case bearing point changes
    bearing_no      = models.CharField(max_length=50, blank=True)
    horizontal_r1   = models.FloatField(null=True, blank=True)   # mm/s or µm pk-pk
    vertical_r2     = models.FloatField(null=True, blank=True)
    axial           = models.FloatField(null=True, blank=True)
    unit            = models.CharField(max_length=20, default='mm/s')  # mm/s or µm
    iso_limit       = models.FloatField(null=True, blank=True)   # acceptable limit for this bearing
    notes           = models.CharField(max_length=200, blank=True)

    class Meta:
        ordering = ['bearing_point__sort_order']


# ─────────────────────────────────────────────────────────
# OIL TESTING LOG
# ─────────────────────────────────────────────────────────

class OilTestLog(models.Model):
    """
    One oil sample test record — digitizes the Oil Testing Register logbook.
    """
    class OilStatus(models.TextChoices):
        OK     = 'OK',     'OK'
        NOT_OK = 'NOT_OK', 'Not OK'

    equipment     = models.ForeignKey(Equipment, on_delete=models.CASCADE, related_name='oil_tests')
    date          = models.DateField()
    viscosity     = models.FloatField(null=True, blank=True)    # in cSt
    moisture      = models.CharField(max_length=50, blank=True) # e.g. "<0.1%", "<200ppm", "1500ppm"
    nas_class     = models.CharField(max_length=10, blank=True) # NAS cleanliness class, e.g. "11", ">12"
    test_no       = models.PositiveIntegerField(null=True, blank=True)
    status        = models.CharField(max_length=10, choices=OilStatus.choices)
    notification_no = models.CharField(max_length=50, blank=True)   # SAP notification, e.g. "10469680,Mt"
    login_by      = models.CharField(max_length=20, blank=True)     # initials, e.g. "PKA", "NT", "AG"
    sent_date     = models.DateField(null=True, blank=True)
    remarks       = models.TextField(blank=True)
    entered_by    = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL)
    created_at    = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-date', 'equipment__name']


# ─────────────────────────────────────────────────────────
# WDA (WEAR DEBRIS ANALYSIS) LOG
# ─────────────────────────────────────────────────────────

class WDALog(models.Model):
    """
    One WDA test record — digitizes the WDA Report logbook.
    WDA is tracked per department (not per individual equipment in some cases).
    """
    class WDAStatus(models.TextChoices):
        OK             = 'OK',         'OK'
        NEED_ATTENTION = 'ATTENTION',  'Need Attention'
        NOT_OK         = 'NOT_OK',     'Not OK'
        NA             = 'NA',         'Not Applicable'

    equipment       = models.ForeignKey(Equipment, on_delete=models.CASCADE, related_name='wda_logs')
    date            = models.DateField()
    ratio           = models.CharField(max_length=20, blank=True)  # e.g. "1:10", "1:100", "1:1000"
    dl              = models.FloatField(null=True, blank=True)      # Direct Load
    ds              = models.FloatField(null=True, blank=True)      # Direct Sediment
    wpc             = models.FloatField(null=True, blank=True)      # Wear Particle Count
    slide           = models.CharField(max_length=50, blank=True)   # Slide type used
    checked_by      = models.CharField(max_length=20, blank=True)   # initials, e.g. "AG", "NT", "PKA", "TS"
    final_status    = models.CharField(max_length=15, choices=WDAStatus.choices)
    notification_no = models.CharField(max_length=100, blank=True)  # SAP notification ref
    sent_login      = models.CharField(max_length=20, blank=True)
    sent_date       = models.DateField(null=True, blank=True)
    remarks         = models.TextField(blank=True)
    entered_by      = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL)
    created_at      = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-date', 'equipment__name']


# ─────────────────────────────────────────────────────────
# SAP NOTIFICATION TRACKER (cross-referenced by all 3 modules)
# ─────────────────────────────────────────────────────────

class SAPNotification(models.Model):
    """
    Tracks SAP maintenance notifications raised due to CMC findings.
    Can be linked to any combination of oil test, WDA, or vibration log.
    """
    class NotifStatus(models.TextChoices):
        OPEN   = 'OPEN',   'Open'
        CLOSED = 'CLOSED', 'Closed'
        PENDING = 'PENDING', 'Pending Action'

    notification_no = models.CharField(max_length=50, unique=True)
    equipment       = models.ForeignKey(Equipment, on_delete=models.CASCADE, related_name='sap_notifications')
    raised_by       = models.CharField(max_length=20)  # initials
    raised_date     = models.DateField()
    description     = models.TextField(blank=True)
    status          = models.CharField(max_length=10, choices=NotifStatus.choices, default='OPEN')
    closed_date     = models.DateField(null=True, blank=True)
    action_taken    = models.TextField(blank=True)

    # FK links to source records
    vibration_log   = models.ForeignKey(VibrationLog, null=True, blank=True, on_delete=models.SET_NULL)
    oil_test        = models.ForeignKey(OilTestLog, null=True, blank=True, on_delete=models.SET_NULL)
    wda_log         = models.ForeignKey(WDALog, null=True, blank=True, on_delete=models.SET_NULL)
```

---

## PART 3 — CMC APP FOLDER STRUCTURE

```
cmc/                                   ← CMC module app
├── models.py                          ← all models above
├── admin.py                           ← equipment master admin (CRUD for 600+ equipment)
├── apps.py                            ← app_name = 'cmc'
├── views/
│   ├── __init__.py
│   ├── dashboard_views.py             ← CMC dept overview dashboard
│   ├── schedule_views.py              ← PM schedule grid + entry
│   ├── vibration_views.py             ← vibration log entry + history + analytics
│   ├── oil_test_views.py              ← oil test entry + history + analytics
│   ├── wda_views.py                   ← WDA entry + history + analytics
│   ├── notification_views.py          ← SAP notification tracker
│   └── report_views.py                ← PDF + Excel export for all modules
├── forms/
│   ├── vibration_forms.py
│   ├── oil_test_forms.py
│   └── wda_forms.py
├── utils/
│   ├── schedule_generator.py          ← generates scheduled dates for each equipment
│   ├── status_logic.py                ← determines equipment health status
│   └── export.py                      ← ReportLab PDF + openpyxl Excel
├── templatetags/
│   └── cmc_tags.py                    ← {% vibration_status_badge %}, {% oil_status_badge %}
├── templates/
│   └── cmc/
│       ├── base_cmc.html              ← extends portal/base.html
│       ├── dashboard.html             ← dept CMC overview
│       ├── schedule/
│       │   ├── schedule_grid.html     ← monthly PM schedule grid (big table)
│       │   └── _schedule_cell.html    ← HTMX partial: individual cell update
│       ├── vibration/
│       │   ├── log_list.html          ← list of all vibration logs for dept
│       │   ├── log_entry.html         ← NEW vibration entry form
│       │   ├── log_detail.html        ← view single log entry
│       │   └── analytics.html         ← vibration trend charts
│       ├── oil_test/
│       │   ├── log_list.html
│       │   ├── log_entry.html         ← oil test form
│       │   └── analytics.html
│       ├── wda/
│       │   ├── log_list.html
│       │   ├── log_entry.html         ← WDA form
│       │   └── analytics.html
│       ├── notifications/
│       │   └── tracker.html           ← SAP notification status board
│       └── partials/
│           ├── _equipment_search.html  ← HTMX: search equipment by name/dept
│           ├── _vibration_row.html
│           ├── _oil_row.html
│           ├── _wda_row.html
│           ├── _schedule_cell.html
│           └── _status_badge.html
├── static/
│   └── cmc/
│       ├── css/cmc.css
│       └── js/cmc.js                  ← Alpine.js for vibration form (dynamic bearing rows)
├── management/
│   └── commands/
│       └── seed_cmc.py                ← seeds Equipment from the Excel PM schedule
├── urls.py
└── migrations/
```

---

## PART 4 — URL CONFIGURATION (`cmc/urls.py`)

```python
from django.urls import path
from cmc.views import dashboard_views, schedule_views, vibration_views
from cmc.views import oil_test_views, wda_views, notification_views, report_views

app_name = 'cmc'

urlpatterns = [
    # ── CMC Entry Point ──────────────────────────────────────
    # This is where portal redirects when user clicks CMC module card
    path('department/<int:dept_id>/',
         dashboard_views.dept_overview,      name='dept_overview'),

    # ── PM Schedule ──────────────────────────────────────────
    path('department/<int:dept_id>/schedule/',
         schedule_views.schedule_grid,        name='schedule_grid'),

    # HTMX: update a single schedule cell
    path('department/<int:dept_id>/schedule/update-cell/',
         schedule_views.update_cell,          name='update_cell'),

    # ── Vibration Monitoring ──────────────────────────────────
    path('department/<int:dept_id>/vibration/',
         vibration_views.log_list,            name='vibration_list'),

    path('department/<int:dept_id>/vibration/new/',
         vibration_views.log_entry,           name='vibration_new'),

    path('department/<int:dept_id>/vibration/<int:log_id>/',
         vibration_views.log_detail,          name='vibration_detail'),

    path('department/<int:dept_id>/vibration/analytics/',
         vibration_views.analytics,           name='vibration_analytics'),

    # HTMX: search equipment when filling vibration form
    path('department/<int:dept_id>/vibration/search-equipment/',
         vibration_views.search_equipment,    name='vibration_equip_search'),

    # ── Oil Testing ───────────────────────────────────────────
    path('department/<int:dept_id>/oil-test/',
         oil_test_views.log_list,             name='oil_list'),

    path('department/<int:dept_id>/oil-test/new/',
         oil_test_views.log_entry,            name='oil_new'),

    path('department/<int:dept_id>/oil-test/analytics/',
         oil_test_views.analytics,            name='oil_analytics'),

    # ── WDA ───────────────────────────────────────────────────
    path('department/<int:dept_id>/wda/',
         wda_views.log_list,                  name='wda_list'),

    path('department/<int:dept_id>/wda/new/',
         wda_views.log_entry,                 name='wda_new'),

    path('department/<int:dept_id>/wda/analytics/',
         wda_views.analytics,                 name='wda_analytics'),

    # ── SAP Notification Tracker ──────────────────────────────
    path('department/<int:dept_id>/notifications/',
         notification_views.tracker,          name='notification_tracker'),

    path('department/<int:dept_id>/notifications/<int:notif_id>/close/',
         notification_views.close_notif,      name='close_notification'),

    # ── Reports ───────────────────────────────────────────────
    path('department/<int:dept_id>/reports/',
         report_views.report_page,            name='report_page'),

    path('department/<int:dept_id>/reports/pdf/',
         report_views.export_pdf,             name='export_pdf'),

    path('department/<int:dept_id>/reports/excel/',
         report_views.export_excel,           name='export_excel'),

    # ── HTMX: equipment search (shared across all forms) ─────
    path('api/equipment-search/',
         dashboard_views.equipment_search,    name='equipment_search'),
]
```

---

## PART 5 — ALL PAGES (Complete Specification)

### PAGE 1 — CMC DEPARTMENT OVERVIEW (`/cmc/department/<dept_id>/`)

**Breadcrumb:** 🏭 Plant › [Dept Name] › CMC

**Header:** Department name + "CMC — Condition Monitoring Cell"

**Section 1: Summary Ribbon (4 cards)**
- Equipment Monitored This Month (count of PMScheduleEntry with status=DONE for current month)
- Equipment Due Today (count of PMScheduleEntry with scheduled_date = today and status=PENDING)
- Open SAP Notifications (count of SAPNotification status=OPEN for this dept)
- Last Oil Test Status (most recent oil test status across dept equipment)

**Section 2: 4 Module Entry Cards (large, clickable)**
```
┌─────────────────────┐  ┌─────────────────────┐
│  📅 PM Schedule     │  │  📳 Vibration        │
│  Track monitoring   │  │  Monitoring          │
│  compliance         │  │  Log & analytics     │
│  [Open Schedule →]  │  │  [Open Logs →]       │
└─────────────────────┘  └─────────────────────┘
┌─────────────────────┐  ┌─────────────────────┐
│  🧪 Oil Testing     │  │  🔬 WDA Analysis     │
│  Sample register    │  │  Wear debris         │
│  & lab results      │  │  particle analysis   │
│  [Open Register →]  │  │  [Open WDA →]        │
└─────────────────────┘  └─────────────────────┘
```

**Section 3: Equipment Health Board (Class A Critical Equipment)**
Table of Class A equipment for this department:
| Equipment | Last Vibration | Last Oil Test | Last WDA | Current Status |
Status is color-coded: Green (OK) / Amber (Need Attention) / Red (Not OK / Overdue)

**Section 4: Upcoming Schedule (Next 7 Days)**
List of equipment due for monitoring in the next 7 days, with their scheduled dates.

---

### PAGE 2 — PM SCHEDULE GRID (`/cmc/department/<dept_id>/schedule/`)

**Filter Bar:**
```
Month: [June ▼]  Year: [2026 ▼]  Class: [All ▼]  Equipment: [Search...]
```

**Main Grid — Big scrollable table (HTMX-powered):**
```
Equipment             | Class | kW  | Freq    | 1  | 2  | 3  | ... | 31
─────────────────────────────────────────────────────────────────────────────
ID Fan-1 WHRB-11     |  A   | 132 | Fortnl. | ✓  |    |    | ... | NR
ID Fan-2 WHRB-11     |  A   | 132 | Fortnl. |    | NR |    | ... | ✓
Turbine-3            |  A   |25000| Weekly  | ✓  | ✓  | ✓  | ... |
...
```

Each cell is colored:
- Blue with date number = monitoring done on that date
- Gray "NR" = Not Running
- Orange "SD" = Shutdown
- Purple "NA" = Not Applicable
- Dark "NP" = Not Approachable
- Empty = pending / not scheduled
- Red empty = overdue (past date, no entry)

**Cell Update via HTMX:**
Clicking a cell opens an inline dropdown:
```html
<select hx-post="/cmc/department/1/schedule/update-cell/"
        hx-target="#cell-eq123-day15"
        hx-include="[name='equipment_id'],[name='day']">
  <option value="DONE">✓ Done</option>
  <option value="NR">NR — Not Running</option>
  <option value="SD">SD — Shutdown</option>
  <option value="NA">NA — Not Applicable</option>
  <option value="NP">NP — Not Approachable</option>
</select>
```
On select → HTMX POST → cell updates inline without page reload.

**Schedule Summary Stats (side panel):**
- Compliance % = DONE / (DONE + Pending scheduled) × 100
- Overdue count (past scheduled date, still PENDING)
- Per-frequency compliance (Weekly / Fortnightly / Monthly)

---

### PAGE 3 — VIBRATION LOG LIST (`/cmc/department/<dept_id>/vibration/`)

**Filter Bar:** Equipment search | Date range | Status (OK / NOT OK / UM) | Instrument type

**Table:**
| Date | Equipment | Status | H/R1 max | V/R2 max | Axial max | Remarks | Actions |
Rows color-coded by status (green/amber/red).
[+ New Entry] button → opens new vibration log form.

**HTMX: search/filter updates table without page reload**

---

### PAGE 4 — VIBRATION LOG ENTRY (`/cmc/department/<dept_id>/vibration/new/`)

This is the digital version of Form F-520.

```
Header Fields:
  Equipment: [search box → HTMX autocomplete from Equipment table]
  Date: [date picker]    Time: [time picker]
  Instrument: [ENPAC ◉ SKF ○ CSI ○ Other ○]
  Report Type: [Route ◉ On Request ○]
  Reported Through: [text]
  Stored In: [text]

Bearing Grid (Alpine.js dynamic):
  ┌──────────────┬──────────┬──────────┬──────────┬──────────┐
  │              │  BP-1    │  BP-2    │  BP-3    │ [+] Add  │
  │              │ (DE)     │ (NDE)    │ (Pump)   │          │
  ├──────────────┼──────────┼──────────┼──────────┼──────────┤
  │Bearing No.   │ [_____]  │ [_____]  │ [_____]  │          │
  │Horizontal/R1 │ [_____]  │ [_____]  │ [_____]  │          │
  │Vertical/R2   │ [_____]  │ [_____]  │ [_____]  │          │
  │Axial         │ [_____]  │ [_____]  │ [_____]  │          │
  └──────────────┴──────────┴──────────┴──────────┴──────────┘

  ← When equipment is selected, bearing points auto-populate from EquipmentBearingPoint
  ← Alpine.js lets user add/remove bearing point columns dynamically

Status: [OK ◉] [NOT OK ○] [Under Monitoring ○] [Need Attention ○]
Remarks: [textarea]

[Submit]
```

**Equipment Search (HTMX autocomplete):**
```html
<input type="text" name="equipment_search"
       hx-get="/cmc/api/equipment-search/?dept_id={{ dept.id }}"
       hx-trigger="keyup[value.length>2]"
       hx-target="#equipment-results">
<div id="equipment-results"></div>
<!-- Results show: Equipment name + SAP code + Class + frequency -->
<!-- On click: fills hidden equipment_id field + loads bearing points -->
```

---

### PAGE 5 — OIL TESTING LOG ENTRY (`/cmc/department/<dept_id>/oil-test/new/`)

Digital version of the Oil Testing Register logbook.

```
Equipment: [search/autocomplete — same as vibration]
Date: [date picker]

Test Results:
  Viscosity (cSt): [____]
  Moisture: [____]  (e.g. <0.1%, <200ppm, type text)
  NAS Class: [__]   (e.g. 11, >12)
  Test No.: [____]

Status: [OK ◉] [NOT OK ○]

If NOT OK (Alpine.js shows additional fields):
  SAP Notification No.: [__________]
  Login By (initials): [___]
  Sent Date: [date picker]

Remarks: [textarea]

[Submit Entry]
```

---

### PAGE 6 — WDA LOG ENTRY (`/cmc/department/<dept_id>/wda/new/`)

Digital version of the WDA Report logbook.

```
Equipment: [search/autocomplete — WDA covers more departments than oil testing]
Date: [date picker]

Sample Data:
  Ratio: [1:10 ▼]   (options: 1:10, 1:100, 1:1000, custom)
  DL (Direct Load): [____]
  DS (Direct Sediment): [____]
  WPC (Wear Particle Count): [____]
  Slide: [____]
  Checked By: [___]   (initials — PKA, NT, AG, TS, etc.)

Final Status: [OK ◉] [Need Attention ○] [Not OK ○] [NA ○]

If Need Attention / Not OK (Alpine.js shows):
  SAP Notification No.: [__________]
  Sent Login: [___]
  Sent Date: [date picker]

Remarks: [textarea]

[Submit Entry]
```

---

### PAGE 7 — SAP NOTIFICATION TRACKER (`/cmc/department/<dept_id>/notifications/`)

**Header:** Open SAP Notifications — [Department Name]

**Active Notifications Table:**
| Notif No. | Equipment | Source | Raised By | Date | Days Open | Status | Action |
Rows colored: Red (>30 days open) / Amber (15-30 days) / Green (recent)

**Close Notification (HTMX):**
Click "Close" → inline form: Action Taken [textarea] + Close Date → HTMX POST → row updates to "Closed" and moves to closed section below.

**Closed Notifications (collapsible table)**

---

### PAGE 8 — VIBRATION ANALYTICS (`/cmc/department/<dept_id>/vibration/analytics/`)

**Filter:** Equipment selector + Date range

**Chart 1: Vibration Trend (Line Chart — Chart.js)**
X-axis: Date of readings
Y-axis: Vibration value (mm/s)
Lines: One per bearing point (H/R1, V/R2, Axial)
Reference line: ISO 10816 limit for this equipment class

**Chart 2: Status History (Stacked Bar Chart)**
Monthly breakdown: OK / Need Attention / Not OK counts per equipment

**Chart 3: Equipment Comparison (Horizontal Bar)**
Latest vibration readings for all Class A equipment — sorted by severity

**Alert Section:** Trending equipment (vibration increasing over last 3 readings)

---

### PAGE 9 — OIL TEST ANALYTICS (`/cmc/department/<dept_id>/oil-test/analytics/`)

**Chart 1: Viscosity Trend** — line chart for selected equipment over time
**Chart 2: NAS Class Distribution** — pie/donut chart: OK vs Not OK
**Chart 3: Moisture Content Trend** — bar chart per equipment
**Summary Table:** Each equipment's last 5 oil tests with status trend arrow (↑ / ↓ / →)

---

### PAGE 10 — WDA ANALYTICS (`/cmc/department/<dept_id>/wda/analytics/`)

**Chart 1: WPC Trend** — Wear Particle Count over time per equipment (line)
**Chart 2: Status Distribution** — stacked bar: OK / Need Attention / Not OK monthly
**Chart 3: DL vs DS Scatter Plot** — direct load vs direct sediment to identify wear patterns
**Alert: Need Attention Equipment** — list of equipment with current "Need Attention" or "Not OK" WDA status

---

### PAGE 11 — CMC REPORT GENERATOR (`/cmc/department/<dept_id>/reports/`)

**Controls:**
```
Report Type: [All ▼ | Vibration | Oil Testing | WDA | PM Schedule | Notifications]
Equipment: [All ▼ | Search specific]
Month: [June ▼]  Year: [2026 ▼]
[Generate Report]  [Export PDF]  [Export Excel]
```

**PDF Report (ReportLab):**
- JSPL logo + "Condition Monitoring Cell — [Department]" header
- Period label (e.g. "June 2026")
- PM Schedule Compliance Summary
- Class A Equipment Health Status table
- Vibration readings for the period (table + mini trend charts if possible)
- Oil Test results table
- WDA results table
- Open SAP Notifications list

**Excel Export (openpyxl):**
- Sheet 1: PM Schedule (matching the original Excel format)
- Sheet 2: Oil Testing Register (matching original logbook format)
- Sheet 3: WDA Report (matching original format)
- Sheet 4: Vibration Summary

---

## PART 6 — VIEWS SPECIFICATION

### `cmc/views/dashboard_views.py`

```python
from django.contrib.auth.decorators import login_required
from portal.utils.decorators import module_access_required

@login_required
@module_access_required('CMC')   # ← uses unified portal access control
def dept_overview(request, dept_id):
    """
    CMC Department Dashboard.
    No separate CMC login — access is controlled by portal's UserModuleAccess.
    """
    # Summary stats
    today = date.today()
    current_month = today.month
    current_year = today.year

    equipment_count = Equipment.objects.filter(department_id=dept_id, is_active=True)

    monitored_this_month = PMScheduleEntry.objects.filter(
        equipment__department_id=dept_id,
        actual_date__month=current_month,
        actual_date__year=current_year,
        status='DONE'
    ).count()

    due_today = PMScheduleEntry.objects.filter(
        equipment__department_id=dept_id,
        scheduled_date=today,
        status='PENDING'
    ).count()

    open_notifications = SAPNotification.objects.filter(
        equipment__department_id=dept_id,
        status='OPEN'
    ).count()

    # Class A equipment health status
    class_a_equipment = Equipment.objects.filter(
        department_id=dept_id,
        equipment_class='A',
        is_active=True
    ).prefetch_related('vibration_logs', 'oil_tests', 'wda_logs')

    # Build health status for each Class A equipment
    health_board = []
    for equip in class_a_equipment:
        last_vib  = equip.vibration_logs.order_by('-date').first()
        last_oil  = equip.oil_tests.order_by('-date').first()
        last_wda  = equip.wda_logs.order_by('-date').first()
        health_board.append({
            'equipment': equip,
            'last_vibration': last_vib,
            'last_oil_test':  last_oil,
            'last_wda':       last_wda,
            'overall_status': compute_overall_status(last_vib, last_oil, last_wda),
        })

    context = {
        'department':           Department.objects.get(id=dept_id),
        'monitored_this_month': monitored_this_month,
        'due_today':            due_today,
        'open_notifications':   open_notifications,
        'health_board':         health_board,
        'upcoming_schedule':    get_upcoming_schedule(dept_id, days=7),
        'page_title':           'CMC Dashboard',
        'active_module':        'CMC',
    }
    return render(request, 'cmc/dashboard.html', context)


def equipment_search(request):
    """HTMX: autocomplete equipment search across all departments"""
    q = request.GET.get('q', '').strip()
    dept_id = request.GET.get('dept_id')
    qs = Equipment.objects.filter(is_active=True)
    if dept_id:
        qs = qs.filter(department_id=dept_id)
    if q:
        qs = qs.filter(name__icontains=q)[:20]
    return render(request, 'cmc/partials/_equipment_search.html', {'results': qs})
```

### `cmc/utils/status_logic.py`

```python
def compute_overall_status(last_vib, last_oil, last_wda):
    """
    Returns 'ok', 'attention', 'critical', or 'unknown'
    based on the latest readings from all three sources.
    """
    statuses = []
    if last_vib:
        if last_vib.status in ('NOT_OK',):
            statuses.append('critical')
        elif last_vib.status in ('ATTENTION', 'UM'):
            statuses.append('attention')
        else:
            statuses.append('ok')

    if last_oil:
        if last_oil.status == 'NOT_OK':
            statuses.append('critical')
        else:
            statuses.append('ok')

    if last_wda:
        if last_wda.final_status == 'NOT_OK':
            statuses.append('critical')
        elif last_wda.final_status == 'ATTENTION':
            statuses.append('attention')
        elif last_wda.final_status == 'OK':
            statuses.append('ok')

    if not statuses:
        return 'unknown'
    if 'critical' in statuses:
        return 'critical'
    if 'attention' in statuses:
        return 'attention'
    return 'ok'


def is_overdue(equipment, current_date):
    """Returns True if equipment is past its scheduled monitoring date with no entry."""
    latest_entry = PMScheduleEntry.objects.filter(
        equipment=equipment
    ).order_by('-scheduled_date').first()

    if not latest_entry:
        return False
    if latest_entry.status == 'PENDING' and latest_entry.scheduled_date < current_date:
        return True
    return False
```

---

## PART 7 — SEED COMMAND (`cmc/management/commands/seed_cmc.py`)

```python
"""
Seeds the Equipment master table from the CMC Schedule Excel file.
Run with: python manage.py seed_cmc
"""
import openpyxl
from django.core.management.base import BaseCommand
from portal.models import Department
from cmc.models import Equipment


class Command(BaseCommand):
    help = 'Seed CMC Equipment master from Excel PM schedule'

    def handle(self, *args, **kwargs):
        wb = openpyxl.load_workbook('CMC_Requirements.xlsx', read_only=True)
        ws = wb['CMC Schedule']

        # Skip header rows (first 2 rows are headers)
        count = 0
        for row in ws.iter_rows(min_row=3, values_only=True):
            scheduled_days, dept_name, equip_name, equip_class = row[0], row[1], row[2], row[3]
            sap_mech, sap_elec = str(row[4] or ''), str(row[5] or '')
            asset_cost, prod_loss, rating, date_col, frequency = row[6], row[7], row[8], row[9], row[10]

            if not equip_name or not dept_name:
                continue

            # Map department name to Department object
            dept = self._get_or_create_dept(dept_name)
            if not dept:
                continue

            Equipment.objects.get_or_create(
                department=dept,
                name=str(equip_name).strip(),
                defaults={
                    'equipment_class': str(equip_class or 'B').strip(),
                    'sap_code_mech':   sap_mech,
                    'sap_code_elec':   sap_elec,
                    'asset_cost':      str(asset_cost or '').strip(),
                    'rating_kw':       float(rating) if rating else None,
                    'frequency':       self._map_frequency(str(frequency or '')),
                    'scheduled_days':  str(scheduled_days or '').strip(),
                }
            )
            count += 1

        self.stdout.write(self.style.SUCCESS(f'Seeded {count} equipment records'))

    def _get_or_create_dept(self, name):
        # Map CMC dept names to portal Department codes
        CMC_TO_PORTAL = {
            'PP-3': 'PP3', 'PP-2': 'PP2', 'PP-1': 'PP1', 'PP-2 Ph-3': 'PPP3',
            'BF-2': 'BF2', 'BF-1': 'BF1', 'DRI-2': 'DRI2', 'DRI-1': 'DRI1',
            'SMS-2': 'SMS2', 'SMS-3': 'SMS3', 'Plate Mill': 'PM', 'SPM': 'SPM',
            'Rail Mill': 'RM', 'SAF': 'SAF1', 'LDP': 'LDP', 'Sinter Plant': 'SINT',
            'Coke Oven': 'CO', 'Cement Plant': 'CP', 'Oxygen Plant': 'OP',
            'RMH-3': 'RMHS3', 'RMH-1': 'RMHS1', 'PGP-2': 'PGP2', 'PGP-3': 'PGP3',
            'CTL-3': 'PM',  # CTL is under Plate Mill
            'Coal Washery': 'CO',
        }
        code = CMC_TO_PORTAL.get(str(name).strip())
        if code:
            try:
                return Department.objects.get(code=code)
            except Department.DoesNotExist:
                pass
        return None

    def _map_frequency(self, freq_str):
        freq_lower = freq_str.lower()
        if 'weekly' in freq_lower:
            return 'WEEKLY'
        if 'fortnightly' in freq_lower or 'fortnight' in freq_lower:
            return 'FORTNIGHTLY'
        if 'quarterly' in freq_lower or 'quaterly' in freq_lower:
            return 'QUARTERLY'
        return 'MONTHLY'
```

---

## PART 8 — CMC CSS (Additions to portal theme)

```css
/* cmc/static/cmc/css/cmc.css */

/* CMC module accent color */
:root {
  --cmc-primary:  #7C3AED;   /* Purple — CMC brand */
  --cmc-light:    #F5F3FF;
  --cmc-border:   #DDD6FE;
}

/* Override module-tpm color for CMC context */
.module-cmc { border-top: 4px solid var(--cmc-primary); }

/* Equipment health status badges */
.health-ok       { background: #DCFCE7; color: #16A34A; }
.health-attention { background: #FEF3C7; color: #D97706; }
.health-critical  { background: #FEE2E2; color: #DC2626; }
.health-unknown   { background: #F3F4F6; color: #6B7280; }

/* PM Schedule Grid */
.schedule-grid table { font-size: 0.75rem; }
.schedule-cell { width: 32px; text-align: center; cursor: pointer; }
.cell-done          { background: #DCFCE7; color: #16A34A; font-weight: 700; }
.cell-nr            { background: #F3F4F6; color: #9CA3AF; }
.cell-sd            { background: #FEF3C7; color: #D97706; }
.cell-na            { background: #F5F3FF; color: #7C3AED; }
.cell-np            { background: #1F2937; color: #9CA3AF; }
.cell-overdue       { background: #FEE2E2; border: 1px solid #DC2626; }
.cell-pending       { background: #F9FAFB; }

/* Vibration bearing grid */
.bearing-grid-table { font-size: 0.8rem; }
.bearing-grid-table thead { background: var(--cmc-light); }
.bearing-reading-input { width: 70px; }

/* SAP Notification cards */
.notif-card        { border-left: 4px solid var(--cmc-primary); }
.notif-overdue     { border-left-color: var(--red); }
.notif-warning     { border-left-color: var(--amber); }

/* CMC Analytics */
.chart-container-cmc { min-height: 320px; }
```

---

## PART 9 — Alpine.js for Vibration Form (`cmc/static/cmc/js/cmc.js`)

```javascript
// Dynamic bearing columns in vibration entry form
function vibrationForm() {
  return {
    bearingPoints: [],    // loaded from equipment on selection
    customPoints: [],     // user-added extra bearing points

    loadEquipmentBearings(equipmentId) {
      // HTMX fetches bearing points for selected equipment
      // Then we update this.bearingPoints from the response
      fetch(`/cmc/api/equipment-bearing-points/?equipment_id=${equipmentId}`)
        .then(r => r.json())
        .then(data => {
          this.bearingPoints = data.bearing_points;
        });
    },

    addBearingPoint() {
      this.customPoints.push({
        id: Date.now(),
        label: '',
        bearing_no: '',
        horizontal_r1: null,
        vertical_r2: null,
        axial: null,
      });
    },

    removeBearingPoint(id) {
      this.customPoints = this.customPoints.filter(p => p.id !== id);
    },

    allPoints() {
      return [...this.bearingPoints, ...this.customPoints];
    }
  };
}

// PM Schedule cell click handling
function scheduleCell(equipmentId, scheduledDate, currentStatus) {
  return {
    status: currentStatus,
    open: false,

    updateStatus(newStatus) {
      this.status = newStatus;
      this.open = false;
      // HTMX handles the actual POST via hx-post on the select element
    }
  };
}
```

---

## PART 10 — `cmc/templates/cmc/base_cmc.html`

```html
{% extends 'portal/base.html' %}
{% load static %}

{% block title %}CMC — {{ department.name }} — JSPL Portal{% endblock %}

{% block breadcrumb_items %}
  <span class="breadcrumb-sep">›</span>
  <a href="{% url 'portal:dept_hub' department.id %}">{{ department.name }}</a>
  <span class="breadcrumb-sep">›</span>
  <span class="breadcrumb-current" style="color: var(--cmc-primary);">CMC</span>
  {% block cmc_breadcrumb %}{% endblock %}
{% endblock %}

{% block module_badge %}
  <span class="active-module-badge" style="background: var(--cmc-light); color: var(--cmc-primary);">
    🔬 CMC
  </span>
{% endblock %}

{% block extra_css %}
  <link rel="stylesheet" href="{% static 'cmc/css/cmc.css' %}">
{% endblock %}

{% block content %}
  <!-- CMC Sub-navigation tabs (visible on all CMC pages) -->
  <div class="cmc-subnav">
    <a href="{% url 'cmc:dept_overview'     department.id %}"
       class="cmc-tab {% if active_tab == 'overview'   %}active{% endif %}">📊 Overview</a>
    <a href="{% url 'cmc:schedule_grid'     department.id %}"
       class="cmc-tab {% if active_tab == 'schedule'   %}active{% endif %}">📅 PM Schedule</a>
    <a href="{% url 'cmc:vibration_list'    department.id %}"
       class="cmc-tab {% if active_tab == 'vibration'  %}active{% endif %}">📳 Vibration</a>
    <a href="{% url 'cmc:oil_list'          department.id %}"
       class="cmc-tab {% if active_tab == 'oil'        %}active{% endif %}">🧪 Oil Testing</a>
    <a href="{% url 'cmc:wda_list'          department.id %}"
       class="cmc-tab {% if active_tab == 'wda'        %}active{% endif %}">🔬 WDA</a>
    <a href="{% url 'cmc:notification_tracker' department.id %}"
       class="cmc-tab {% if active_tab == 'notif'      %}active{% endif %}">🔔 SAP Notif.</a>
    <a href="{% url 'cmc:report_page'       department.id %}"
       class="cmc-tab {% if active_tab == 'reports'    %}active{% endif %}">📋 Reports</a>
  </div>

  {% block cmc_content %}{% endblock %}
{% endblock %}

{% block extra_js %}
  <script src="{% static 'cmc/js/cmc.js' %}"></script>
{% endblock %}
```

---

## PART 11 — INTEGRATION WITH UNIFIED PORTAL

**Already handled in the unified portal plan. CMC just needs:**

1. `app_name = 'cmc'` in `cmc/apps.py`
2. `url_namespace = 'cmc:dept_overview'` in Module seed data (already seeded in `seed_portal.py`)
3. All CMC views decorated with `@login_required` + `@module_access_required('CMC')`
4. `cmc` in `INSTALLED_APPS` in `settings.py`
5. `path('cmc/', include('cmc.urls', namespace='cmc'))` in root `urls.py`

**Access flow (no second login):**
```
User logs in → portal session created
→ Clicks CMC card in dept hub
→ enter_module() checks UserModuleAccess for CMC
→ Redirects to /cmc/department/<dept_id>/
→ @login_required passes (already authenticated)
→ @module_access_required('CMC') passes
→ CMC dashboard loads
```

---

## PART 12 — WHAT NOT TO DO (CMC-specific)

- Do NOT create a separate login for CMC — same unified portal session
- Do NOT mix Vibration, Oil Test, and WDA data in one form — they are three separate entry flows
- Do NOT hardcode equipment in templates — all equipment comes from the Equipment model (seeded from Excel)
- Do NOT confuse "WDA department" scope with "Oil Test equipment" scope — WDA in the logbook is per department section, but we link it to individual equipment in the database
- Do NOT skip the PM Schedule grid — it is the core of CMC's daily workflow and must be easy to update
- Do NOT require logging an actual vibration reading just to mark equipment as "NR" — the status update in the schedule grid is a separate lightweight operation
- Do NOT add complex analytics before the basic entry forms work — prioritize: entry forms → schedule grid → analytics → reports
- Do NOT use a different base template than `portal/base.html` — all pages must share the unified portal shell so breadcrumb and sidebar work

---

## PART 13 — DELIVERABLES EXPECTED FROM ANTIGRAVITY (CMC)

1. Complete `cmc/` Django app folder with all files listed in Part 3
2. `cmc/models.py` — all 8 models as specified in Part 2
3. All views as specified in Part 5 and Part 6
4. All templates in `cmc/templates/cmc/` (base_cmc.html + all 11 pages)
5. `cmc/forms/` — form classes for VibrationLog, OilTestLog, WDALog
6. `cmc/utils/status_logic.py` — compute_overall_status(), is_overdue()
7. `cmc/utils/schedule_generator.py` — generate scheduled dates for given month/year per equipment frequency
8. `cmc/utils/export.py` — PDF (ReportLab) + Excel (openpyxl) for CMC reports
9. `cmc/static/cmc/css/cmc.css` — CMC theme tokens from Part 8
10. `cmc/static/cmc/js/cmc.js` — Alpine.js dynamic bearing form from Part 9
11. `cmc/management/commands/seed_cmc.py` — seed from Excel as in Part 7
12. `cmc/urls.py` — all URLs from Part 4
13. `cmc/admin.py` — Equipment and EquipmentBearingPoint registered with Django admin (inline bearing points, search by dept/name/SAP code, list_filter by class and frequency)
14. Updated `portal/seeds/seed_portal.py` — ensure CMC module is seeded with `url_namespace='cmc:dept_overview'`
15. Updated root `jspl_portal/urls.py` — add `path('cmc/', include('cmc.urls', namespace='cmc'))`
16. Updated `settings.py` — add `'cmc'` to INSTALLED_APPS
17. Migrations for all cmc models

---

*This is the COMPLETE CMC implementation specification.*
*Stack: Django 5 + PostgreSQL + HTMX + Alpine.js. Same stack as TPM. Same portal session.*
*Give Antigravity both this file AND the JSPL_Unified_Portal_Complete_Plan.md AND the JSPL_TPM_Portal_Django_HTMX_Implementation_Plan.md together.*
