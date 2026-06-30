# HOD KPI Review Module — Implementation Plan v2.0

> **Complete Plant Dashboard | Full KPI Domain Coverage**
> Production · Quality · OEE · Safety · Cost
> Pilot: Plate Mill → All Departments

---

## Quick Reference

| Item | Detail |
|---|---|
| Module | HOD KPI Review |
| Pilot Department | Plate Mill (all departments thereafter) |
| Excel Source | `Executive Summary Report- Plate Mil 25062026.xlsx` |
| Framework | Django + Vanilla CSS (Glassmorphism UI) |
| Prepared For | Antigravity Development Team |
| Version | 2.0 — Full KPI Domain Coverage |

---

## Table of Contents

1. [Objective & Scope](#1-objective--scope)
2. [HOD Workflow](#2-hod-workflow)
3. [KPI Domain Definitions & Data Mapping](#3-kpi-domain-definitions--data-mapping)
4. [Database Models](#4-database-models)
5. [Implementation Components](#5-implementation-components)
6. [UI / Design Guidelines](#6-ui--design-guidelines)
7. [Pre-Implementation Prerequisite](#7-pre-implementation-prerequisite)
8. [Verification Plan](#8-verification-plan)
9. [Summary of Changes](#9-summary-of-changes)

---

## 1. Objective & Scope

The HOD KPI Review Module digitizes the monthly performance review process for all departments within the Complete Plant Dashboard. Each HOD receives a dedicated KPI dashboard driven by their department's Excel report, eliminating the existing manual Excel-based review cycle.

### 1.1 Core Objectives

- Auto-populate KPI data from uploaded Excel files (no manual data entry by HOD)
- Cover all five KPI domains: Production, Quality, OEE, Safety, and Cost
- Provide YTD, MTD, and WTD views for production metrics
- Force accountability for every below-target KPI via structured deviation forms
- Generate AI-powered insights and improvement recommendations
- Enable formal review submission to higher management with notifications
- Maintain historical KPI performance and action plan tracking

### 1.2 KPI Domains Covered

| # | Domain | Key Metrics | View Granularity |
|---|---|---|---|
| 1 | **Production** | Q/T Production, CTL Production, Slitter Production, Finished Goods Production, Plan vs Actual | YTD / MTD / WTD |
| 2 | **Quality** | FTR (First Time Right), Yield (%) | MTD / Trend |
| 3 | **OEE** | Availability, Performance, Quality Component, Overall OEE (%) | MTD / Daily Trend |
| 4 | **Safety** | LTI, Near Misses, Unsafe Acts/Conditions, Safety Observation Closure %, TPM Score | MTD / Cumulative |
| 5 | **Cost** | Production Cost per Ton, Conversion Cost, Energy Cost, Power Cost | MTD / YTD |

---

## 2. HOD Workflow

The complete monthly review cycle follows six sequential steps. The HOD does not enter raw KPI values — the system reads all data from the uploaded Excel file automatically.

| Step | Action | Detail |
|---|---|---|
| 1 | **Upload Excel Report** | HOD uploads the monthly Excel report (e.g., `Executive Summary Report- Plate Mil 25062026.xlsx`) for the relevant month and year via the department hub. |
| 2 | **KPI Data Auto-Population** | System parses the Excel file and displays all KPI domains (Production, Quality, OEE, Safety, Cost) with Target, Actual, Achievement %, status coloring (Green/Yellow/Red), and YTD/MTD/WTD breakdowns. |
| 3 | **Below-Target Review** | For every KPI flagged Red or Yellow, the HOD completes a structured deviation form: Reason for deviation, Root cause, Corrective action, Responsible owner, Expected completion date, Remarks. |
| 4 | **Delay Analysis Review** | Dashboard displays parsed delay data — total delays, department-wise contributions, major reasons. HOD provides explanations for significant delays. |
| 5 | **Monthly Inputs & AI Insights** | HOD fills in monthly summary (Achievements, Risks, Support Required, Resources, Special Observations). System simultaneously generates AI-based performance insights and recommendations. |
| 6 | **Submit Review** | HOD submits the completed review. Data is stored, and higher management receives an automated notification that the department KPI review is ready for evaluation. |

---

## 3. KPI Domain Definitions & Data Mapping

This section defines what each KPI metric means, its unit of measurement, how it is parsed from the Excel source, and the thresholds used for status coloring.

### 3.1 Production KPIs (YTD / MTD / WTD)

| KPI / Metric | UOM | Source | Status Mapping |
|---|---|---|---|
| Q/T Production | MT | Production / Summary sheet — Plan vs Actual columns | Green ≥ 100% \| Yellow 90–99% \| Red < 90% |
| CTL Production | MT | Production / Summary sheet — Plan vs Actual columns | Green ≥ 100% \| Yellow 90–99% \| Red < 90% |
| Slitter Production | MT | Production / Summary sheet — Plan vs Actual columns | Green ≥ 100% \| Yellow 90–99% \| Red < 90% |
| Finished Goods Production | MT | Production / Summary sheet — Plan vs Actual columns | Green ≥ 100% \| Yellow 90–99% \| Red < 90% |
| Plan vs Actual Variance | % | Calculated: `(Actual / Plan) × 100` | Green ≥ 100% \| Yellow 90–99% \| Red < 90% |

> **Parser Note:** Extract YTD (cumulative to date), MTD (current month), and WTD (current week) from respective sheets or row groupings in the Excel file. These map to the three tab views on the dashboard.

---

### 3.2 Quality KPIs

| KPI / Metric | UOM | Source | Status Mapping |
|---|---|---|---|
| FTR – First Time Right | % | Quality / KPI sheet | Green ≥ Target \| Yellow within 2% below \| Red > 2% below |
| Yield | % | Quality / KPI sheet | Green ≥ Target \| Yellow within 2% below \| Red > 2% below |

---

### 3.3 OEE – Overall Equipment Effectiveness

| KPI / Metric | UOM | Source | Status Mapping |
|---|---|---|---|
| Availability | % | OEE / Equipment sheet | Green ≥ 90% \| Yellow 80–89% \| Red < 80% |
| Performance | % | OEE / Equipment sheet | Green ≥ 95% \| Yellow 85–94% \| Red < 85% |
| Quality Component | % | OEE / Equipment sheet | Green ≥ 99% \| Yellow 95–98% \| Red < 95% |
| Overall OEE | % | Calculated: `Availability × Performance × Quality` | Green ≥ 85% \| Yellow 75–84% \| Red < 75% |

> **Parser Note:** If Overall OEE is pre-calculated in the sheet, use that value directly. If not, compute from the three component values. Always validate against the Excel value if both exist.

---

### 3.4 Safety KPIs

| KPI / Metric | UOM | Source | Status Mapping |
|---|---|---|---|
| LTI – Lost Time Injury | Count | Safety / HSE sheet | Green = 0 \| Red ≥ 1 (zero tolerance — no Yellow) |
| Near Misses Reported | Count | Safety / HSE sheet | Higher = Better (reporting culture) — Green if ≥ target |
| Unsafe Acts / Conditions | Count | Safety / HSE sheet | Green ≤ Target \| Yellow 1–5 above \| Red > 5 above |
| Safety Observation Closure % | % | Safety / HSE sheet | Green ≥ 90% \| Yellow 75–89% \| Red < 75% |
| TPM Score | Score | TPM sheet | Green ≥ Target \| Yellow within 10% below \| Red > 10% below |

> **Parser Note:** LTI is zero-tolerance. Any value > 0 must trigger an immediate Red flag with a prominent alert on the Safety panel. This is the only KPI with no Yellow band.

---

### 3.5 Cost KPIs

| KPI / Metric | UOM | Source | Status Mapping |
|---|---|---|---|
| Production Cost per Ton | ₹/MT | Cost / Financial sheet | Green ≤ Target \| Yellow 0–5% above \| Red > 5% above |
| Conversion Cost | ₹/MT | Cost / Financial sheet | Green ≤ Target \| Yellow 0–5% above \| Red > 5% above |
| Energy Cost | ₹/MT | Cost / Financial sheet | Green ≤ Target \| Yellow 0–5% above \| Red > 5% above |
| Power Cost | ₹/MT | Cost / Financial sheet | Green ≤ Target \| Yellow 0–5% above \| Red > 5% above |

> **Parser Note:** Cost logic is **inverted** — lower actual vs target = better. Achievement % for cost = `(Target / Actual) × 100`. Status thresholds apply to this inverted percentage.

---

### 3.6 Delay Analysis

| Field | Source | Notes |
|---|---|---|
| Delay Reason | Delay / Downtime sheet | Category/reason string |
| Department Cause | Delay / Downtime sheet | Which dept caused the delay |
| Duration (mins) | Delay / Downtime sheet | Numeric — total minutes |
| Contribution % | Calculated | `(reason_duration / total_duration) × 100` |

---

## 4. Database Models

All models live in the `hod_kpi` Django app.

### Model 1: `HODKPIUpload`

Tracks each Excel file upload per department per reporting period.

```python
class HODKPIUpload(models.Model):
    department     = models.ForeignKey('tpm.Department', on_delete=models.CASCADE)
    uploaded_by    = models.ForeignKey('tpm.User', on_delete=models.SET_NULL, null=True)
    file           = models.FileField(upload_to='hod_kpi/uploads/%Y/%m/')
    month          = models.PositiveSmallIntegerField()          # 1–12
    year           = models.PositiveSmallIntegerField()
    reporting_date = models.DateField()                          # from Excel filename/content
    uploaded_at    = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('department', 'month', 'year')
        ordering = ['-year', '-month']
```

---

### Model 2: `HODKPIRecord`

One row per KPI metric per upload. Covers all five domains.

```python
class HODKPIRecord(models.Model):

    DOMAIN_CHOICES = [
        ('PRODUCTION', 'Production'),
        ('QUALITY',    'Quality'),
        ('OEE',        'OEE'),
        ('SAFETY',     'Safety'),
        ('COST',       'Cost'),
    ]

    VIEW_TYPE_CHOICES = [
        ('YTD', 'Year to Date'),
        ('MTD', 'Month to Date'),
        ('WTD', 'Week to Date'),
        ('NA',  'Not Applicable'),
    ]

    STATUS_CHOICES = [
        ('GREEN',  'Green'),
        ('YELLOW', 'Yellow'),
        ('RED',    'Red'),
    ]

    upload          = models.ForeignKey(HODKPIUpload, on_delete=models.CASCADE, related_name='records')
    domain          = models.CharField(max_length=20, choices=DOMAIN_CHOICES)
    kpi_name        = models.CharField(max_length=200)           # e.g. "Q/T Production", "OEE", "LTI"
    uom             = models.CharField(max_length=50, blank=True) # MT, %, Count, ₹/MT, Score
    view_type       = models.CharField(max_length=5, choices=VIEW_TYPE_CHOICES, default='NA')

    # Parsed values
    target          = models.FloatField(null=True, blank=True)
    actual          = models.FloatField(null=True, blank=True)
    achievement_pct = models.FloatField(null=True, blank=True)   # auto-calculated on save
    status          = models.CharField(max_length=10, choices=STATUS_CHOICES, default='GREEN')
    is_below_target = models.BooleanField(default=False)         # True if YELLOW or RED

    # HOD Feedback Fields (for below-target KPIs)
    reason_deviation   = models.TextField(blank=True, null=True)
    root_cause         = models.TextField(blank=True, null=True)
    corrective_action  = models.TextField(blank=True, null=True)
    responsible_owner  = models.CharField(max_length=150, blank=True, null=True)
    completion_date    = models.DateField(blank=True, null=True)
    remarks            = models.TextField(blank=True, null=True)

    class Meta:
        ordering = ['domain', 'kpi_name', 'view_type']
```

---

### Model 3: `HODKPIDelayRecord`

Captures delay analysis data extracted from the Excel file.

```python
class HODKPIDelayRecord(models.Model):
    upload            = models.ForeignKey(HODKPIUpload, on_delete=models.CASCADE, related_name='delays')
    reason            = models.CharField(max_length=300)
    department_cause  = models.CharField(max_length=150, blank=True)
    duration_mins     = models.FloatField(default=0.0)
    contribution_pct  = models.FloatField(null=True, blank=True)  # auto-calculated
    explanation       = models.TextField(blank=True)              # HOD explanation
```

---

### Model 4: `HODKPIMonthlySubmission`

The final submission record — links KPI data, HOD narrative inputs, AI insights, and review status.

```python
class HODKPIMonthlySubmission(models.Model):

    STATUS_CHOICES = [
        ('DRAFT',     'Draft'),
        ('SUBMITTED', 'Submitted'),
    ]

    department         = models.ForeignKey('tpm.Department', on_delete=models.CASCADE)
    upload             = models.ForeignKey(HODKPIUpload, on_delete=models.CASCADE)
    submitted_by       = models.ForeignKey('tpm.User', on_delete=models.SET_NULL, null=True)
    month              = models.PositiveSmallIntegerField()
    year               = models.PositiveSmallIntegerField()
    status             = models.CharField(max_length=15, choices=STATUS_CHOICES, default='DRAFT')
    submitted_at       = models.DateTimeField(null=True, blank=True)

    # Monthly Summary Inputs
    achievements       = models.TextField(blank=True)
    risks              = models.TextField(blank=True)
    support_required   = models.TextField(blank=True)
    resources_required = models.TextField(blank=True)
    special_observations = models.TextField(blank=True)

    # AI Insights
    ai_summary         = models.TextField(blank=True)
    ai_recommendations = models.TextField(blank=True)

    class Meta:
        unique_together = ('department', 'month', 'year')
```

---

## 5. Implementation Components

### Component 1 — System Integration & Django App Initialization

Create the `hod_kpi` Django app and wire it into the main portal.

| Tag | File / Path | Description |
|---|---|---|
| `NEW` | `hod_kpi/` | Full app boilerplate: models.py, views.py, urls.py, admin.py, apps.py, utils/, templates/, static/ |
| `MODIFY` | `main_portal/settings.py` | Add `'hod_kpi'` to `INSTALLED_APPS` |
| `MODIFY` | `main_portal/urls.py` | Include `hod_kpi.urls` with prefix `hod-kpi/` |
| `NEW` | `hod_kpi/management/commands/seed_hod_kpi.py` | Seeds Module record, grants HOD role access across all departments |

---

### Component 2 — Excel Parser Module

A Python utility using `openpyxl` that reads the uploaded Excel file and extracts structured data across all five KPI domains.

> **Must be calibrated against `excel_structure.txt` before writing final parser logic. See Section 7.**

| Tag | File / Path | Description |
|---|---|---|
| `NEW` | `hod_kpi/utils/parser.py` | Core Excel parser — all five domains, delay data, achievement % calculation, status classification |
| `NEW` | `hod_kpi/utils/inspect_hod_excel.py` | Diagnostic utility — prints sheet names, column headers, and data samples |

#### Parser Responsibilities by Domain

| Domain | Source Sheet(s) | Columns to Extract | Special Logic |
|---|---|---|---|
| Production | Production / Summary | Plan, Actual per product type | Detect YTD / MTD / WTD row groups |
| Quality | Quality / KPI | FTR %, Yield % | Compare vs target column |
| OEE | OEE / Equipment | Availability, Performance, Quality, Overall | Compute OEE = A×P×Q if not pre-calculated |
| Safety | Safety / HSE | LTI, Near Miss, Unsafe Acts, Closure % | LTI zero-tolerance flag |
| Cost | Cost / Financial | Cost per ton columns | Lower = better — invert achievement % |
| Delays | Delay / Downtime | Reason, Duration mins, Dept | Calculate contribution % per reason |

#### Parser Output Structure

```python
# parser.py returns this dict on successful parse:
{
    "upload_meta": {
        "reporting_date": "2026-06-25",
        "department": "Plate Mill",
    },
    "kpi_records": [
        {
            "domain": "PRODUCTION",
            "kpi_name": "Q/T Production",
            "uom": "MT",
            "view_type": "MTD",
            "target": 15000,
            "actual": 14200,
            "achievement_pct": 94.67,
            "status": "YELLOW",
            "is_below_target": True,
        },
        # ... one entry per KPI per view_type
    ],
    "delay_records": [
        {
            "reason": "Roll Change",
            "department_cause": "Maintenance",
            "duration_mins": 320,
            "contribution_pct": 28.5,
        },
        # ...
    ]
}
```

---

### Component 3 — HOD KPI Dashboard Interface

Premium dashboard using the existing portal's UI language — vanilla CSS with HSL color palettes and glassmorphism cards. No external CSS frameworks.

| Tag | File / Path | Description |
|---|---|---|
| `NEW` | `hod_kpi/templates/hod_kpi/dashboard.html` | Main dashboard template — all 11 sections |
| `NEW` | `hod_kpi/static/hod_kpi/css/hod_kpi.css` | Custom CSS — glassmorphism cards, status badges, progress bars, tab switcher |
| `NEW` | `hod_kpi/static/hod_kpi/js/hod_kpi.js` | Tab switching (YTD/MTD/WTD), inline form expand/collapse, AJAX auto-save |
| `NEW` | `hod_kpi/views.py` | All Django views (see Component 4) |
| `NEW` | `hod_kpi/urls.py` | URL patterns for all hod_kpi views |

#### Dashboard UI Sections

| # | Section | Details |
|---|---|---|
| 1 | **Upload & Period Selector** | Month/Year dropdowns, drag-and-drop Excel upload widget, reporting date display. Upload triggers auto-parse and page reload. |
| 2 | **KPI Summary Cards** | Five domain cards (Production, Quality, OEE, Safety, Cost). Each shows: overall achievement %, count of Green / Yellow / Red KPIs, delta vs last month. |
| 3 | **Production Detail Panel** | Tab switcher: `YTD \| MTD \| WTD`. Table with Q/T, CTL, Slitter, Finished Goods — Plan vs Actual with colour-coded variance bars. |
| 4 | **Quality & OEE Panel** | FTR and Yield with gauge/progress bar visuals. OEE breakdown: Availability × Performance × Quality = Overall OEE waterfall display. |
| 5 | **Safety Dashboard** | LTI counter (large red number if > 0 with alert banner), Near Miss trend, Unsafe Acts count, Safety Closure % donut, TPM Score gauge. |
| 6 | **Cost Panel** | Per-ton cost metrics with budget vs actual horizontal bars. Red highlight if over budget. |
| 7 | **Below-Target KPI Forms** | Auto-expanded inline forms for every Red / Yellow KPI. Fields: Reason for Deviation, Root Cause, Corrective Action, Responsible Owner, Completion Date, Remarks. Collapse animation on completion. |
| 8 | **Delay Analysis Panel** | Total delay summary card, department-wise horizontal contribution bars, top delay reasons ranked table. HOD explanation text field per major delay. |
| 9 | **AI Insights Panel** | Glassmorphism card with AI-generated performance summary and improvement recommendations. "Refresh Insights" button triggers API call. Skeleton loader during fetch. |
| 10 | **Monthly Summary Form** | Five text areas: Achievements, Current Risks, Support Required, Resources Required, Special Observations. |
| 11 | **Action Toolbar** | Sticky bottom bar: "Save Draft" (auto-save on change), "Submit Review" (confirmation modal, locks all fields on confirm). Status pill shows `DRAFT` / `SUBMITTED`. |

---

### Component 4 — Django Views & API Endpoints

| View / Endpoint | Method | Purpose |
|---|---|---|
| `hod_kpi_dashboard` | GET | Render main dashboard for HOD — fetches latest upload and submission for selected period |
| `upload_excel` | POST | Receive Excel file, run parser, create `HODKPIUpload` + `HODKPIRecord` + `HODKPIDelayRecord` rows, return JSON |
| `save_kpi_feedback` | POST (AJAX) | Save/update deviation form fields for a specific `HODKPIRecord` — called on field blur |
| `save_delay_explanation` | POST (AJAX) | Save HOD explanation for a `HODKPIDelayRecord` |
| `save_monthly_inputs` | POST (AJAX) | Save achievements, risks, support, resources, observations to `HODKPIMonthlySubmission` |
| `generate_ai_insights` | POST | Pass KPI data to AI model, return summary + recommendations, save to submission record |
| `submit_review` | POST | Validate all required fields complete, set `status=SUBMITTED`, trigger management notification |
| `review_history` | GET | List past submissions for the department with status and KPI scorecard summary |

#### URL Configuration

```python
# hod_kpi/urls.py
from django.urls import path
from . import views

app_name = 'hod_kpi'

urlpatterns = [
    path('dashboard/', views.hod_kpi_dashboard, name='dashboard'),
    path('upload/', views.upload_excel, name='upload_excel'),
    path('save/kpi-feedback/', views.save_kpi_feedback, name='save_kpi_feedback'),
    path('save/delay-explanation/', views.save_delay_explanation, name='save_delay_explanation'),
    path('save/monthly-inputs/', views.save_monthly_inputs, name='save_monthly_inputs'),
    path('ai-insights/', views.generate_ai_insights, name='generate_ai_insights'),
    path('submit/', views.submit_review, name='submit_review'),
    path('history/', views.review_history, name='review_history'),
]
```

---

### Component 5 — AI Insights Engine

The AI insights system aggregates all parsed KPI data and generates actionable intelligence.

| Tag | File / Path | Description |
|---|---|---|
| `NEW` | `hod_kpi/utils/ai_insights.py` | Builds structured prompt from KPI data, calls AI API, parses and returns insights |

#### AI Output Fields

```python
# ai_insights.py generates:
{
    "summary": "Overall department performance this month...",       # 2–3 paragraphs
    "recommendations": [
        "Focus on reducing roll change delay by...",
        "OEE Performance component dropped — investigate...",
        # ...
    ],
    "focus_areas": ["OEE Improvement", "Safety Closure Rate", "Cost Control"],
    "trend_flags": [
        {"kpi": "Q/T Production", "trend": "DECLINING", "periods": 3},
        {"kpi": "FTR", "trend": "IMPROVING", "periods": 2},
    ]
}
```

#### Prompt Structure

The AI prompt includes:
- Department name and reporting period
- All KPI values (target, actual, achievement %) grouped by domain
- Status summary (count of Red / Yellow / Green per domain)
- Top 3 delay reasons with contribution %
- Previous month's status for trend context

---

### Component 6 — Department Hub Integration & Module Registry

| Tag | File / Path | Description |
|---|---|---|
| `NEW` | `hod_kpi/management/commands/seed_hod_kpi.py` | Creates `Module` record, grants HOD role access across all departments |
| `MODIFY` | `tpm/templates/department_hub.html` | Add conditional HOD KPI card when `HODKPI` is in department's enabled modules |

#### HOD KPI Hub Card — Displayed Info

```
┌─────────────────────────────────────┐
│  📊 HOD KPI Review                  │
│                                     │
│  June 2026          ● SUBMITTED     │
│  Overall Score: 78%                 │
│  🟢 12   🟡 4   🔴 3               │
│                                     │
│  [Open Dashboard]                   │
└─────────────────────────────────────┘
```

- Shows: last submission date, DRAFT / SUBMITTED / NOT STARTED status, overall KPI score, Green/Yellow/Red counts
- Card is scoped per department — each HOD only sees their department's data

---

## 6. UI / Design Guidelines

The dashboard UI must be consistent with the existing Complete Plant Dashboard visual language.

| Element | Specification |
|---|---|
| **Color System** | Use existing `HSL` CSS variables from the portal — inherit from `:root` variables already defined. Do NOT introduce new color systems. |
| **Cards** | Glassmorphism: `backdrop-filter: blur(20px); background: rgba(255,255,255,0.08); border: 1px solid rgba(255,255,255,0.12)` |
| **Status Badges** | Green: `--success-color` \| Yellow: `--warning-color` \| Red: `--danger-color` — use existing border-radius and font conventions |
| **Tables** | Match existing dashboard table styles — sticky header, alternating row shading, hover highlight. No external DataTables dependency. |
| **Forms** | Below-target KPI forms use the same input styles as other portal forms. Expand/collapse via `max-height` CSS transition. |
| **Typography** | Match existing font stack. No new fonts. Keep heading sizes proportional to current dashboard hierarchy. |
| **Progress Bars** | Custom CSS bars for Plan vs Actual and delay contributions — same style as existing portal progress indicators. |
| **Responsive** | Desktop primary, tablet supported. Use existing grid breakpoints. |
| **Icons** | Use the same icon set already loaded in the portal. Do not add new icon libraries. |
| **Modals** | Submit confirmation modal — use the existing portal modal component/pattern. |
| **Loading States** | Skeleton loaders for AI Insights panel and initial KPI table load — match existing portal skeleton styles. |

---

## 7. Pre-Implementation Prerequisite

> ⚠️ **BLOCKER — Must complete before Component 2 (Parser) development begins.**

The Excel parser cannot be written until the exact sheet names and column structure of the Excel file are known. Run the following from the workspace root:

```powershell
.venv\Scripts\python inspect_hod_excel.py > excel_structure.txt
```

Share `excel_structure.txt` with the Antigravity team. The parser will then be built to match sheet names, column headers, and row structures exactly.

### What the inspection should reveal

- Sheet names (e.g., `Production`, `OEE Summary`, `Delay Analysis`, etc.)
- Column headers for Plan, Actual, Target in each sheet
- Row groupings for YTD / MTD / WTD in production sheets
- Presence or absence of pre-calculated OEE, achievement %, and cost variance
- Delay sheet structure (rows = reasons or reasons = columns)

---

## 8. Verification Plan

| # | Test | Expected Result |
|---|---|---|
| 1 | Excel Upload | Upload `Executive Summary Report- Plate Mil 25062026.xlsx`. All five KPI domain sections populate with correct Target vs Actual values. |
| 2 | Production YTD / MTD / WTD | Tab switching shows correct data for each time view. Q/T, CTL, Slitter, Finished Goods all display. |
| 3 | Status Classification | KPIs auto-color Green / Yellow / Red based on domain thresholds. Below-target KPIs show inline deviation form. |
| 4 | OEE Calculation | Overall OEE = Availability × Performance × Quality matches Excel value (if pre-calculated) or is computed correctly. |
| 5 | Safety LTI Zero-Tolerance | LTI > 0 triggers Red status and prominent alert banner on Safety panel. No Yellow intermediate state. |
| 6 | Cost Inversion | Cost KPIs flagged Red when actual > target (opposite of production logic). Inverted achievement % displays correctly. |
| 7 | Delay Visualization | Delay reasons appear with horizontal contribution bars ranked by % contribution. HOD explanation field saves via AJAX. |
| 8 | Deviation Form Save | Fill all 6 fields for a below-target KPI. "Save Draft" saves without error. Fields persist on page reload. |
| 9 | AI Insights | Click "Generate Insights" — AI summary, recommendations, and focus areas appear within 10 seconds. Saved to submission record. |
| 10 | Monthly Inputs | All 5 text areas save correctly. Status remains DRAFT. |
| 11 | Submit Review | Submit button shows confirmation modal. On confirm: status → SUBMITTED, form fields lock, management notification triggered in portal. |
| 12 | Department Hub Card | HOD KPI card appears in Plate Mill hub showing submission status, overall score, and Green/Yellow/Red counts. |
| 13 | Multi-Department Scope | Log in as a different department HOD — HOD KPI card appears in their hub with their department's data scoped correctly. No cross-department data leakage. |

---

## 9. Summary of Changes

### New Files

```
hod_kpi/
├── __init__.py
├── apps.py
├── admin.py
├── models.py                          # HODKPIUpload, HODKPIRecord, HODKPIDelayRecord, HODKPIMonthlySubmission
├── views.py                           # All 8 views/endpoints
├── urls.py                            # URL patterns
├── utils/
│   ├── parser.py                      # Excel parser — all 5 domains + delays
│   ├── inspect_hod_excel.py           # Diagnostic utility for Excel structure
│   └── ai_insights.py                 # AI insights prompt builder and API caller
├── templates/
│   └── hod_kpi/
│       └── dashboard.html             # Main dashboard (11 sections)
├── static/
│   └── hod_kpi/
│       ├── css/
│       │   └── hod_kpi.css            # Glassmorphism UI, status badges, bars
│       └── js/
│           └── hod_kpi.js             # Tab switching, AJAX saves, inline forms
└── management/
    └── commands/
        └── seed_hod_kpi.py            # Module seed + role permissions
```

### Modified Files

| File | Change |
|---|---|
| `main_portal/settings.py` | Add `'hod_kpi'` to `INSTALLED_APPS` |
| `main_portal/urls.py` | Include `hod_kpi.urls` under prefix `hod-kpi/` |
| `tpm/templates/department_hub.html` | Add HOD KPI card (conditional on module enabled) |

### Migration & Setup Commands

```bash
python manage.py makemigrations hod_kpi
python manage.py migrate
python manage.py seed_hod_kpi
python manage.py runserver
```

---

> **This plan (v2.0) fully supersedes the original v1.0 implementation plan.**
> All five KPI domains — Production, Quality, OEE, Safety, Cost — are covered with domain-appropriate parsing logic, status thresholds, and UI sections.
> The single prerequisite before development begins is generating and sharing `excel_structure.txt`.
