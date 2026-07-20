# Jindal PRISM - Unified Departments & Modules Hub (RGH Plant)

> **PRISM**: **P**lant **R**eporting & **I**ntegrated **S**mart **M**anagement System

This repository houses **Jindal PRISM** for the RGH Plant. Acting as a Single Sign-On (SSO) central gateway, it consolidates **28 plant departments** and operational modules (TPM, CMC, Delays, FMEA, CAPA, Safety, Quality, HOD KPI, SMED, REST API, Mobile App) under a unified Django project sharing a single database runtime.

### 🗄️ Dual Database Runtime Architecture
* **Development & Local Testing**: Uses a zero-configuration shared **SQLite3** database (`db.sqlite3`).
* **Production Deployment**: Uses enterprise-grade **PostgreSQL** configured dynamically via environment variables (`DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT`) using `psycopg2-binary`.

---

## 1. Project Directory Structure & Repository Map

Below is the directory map of the Django applications, mobile app, and templates. Use this as a reference to locate models, views, templates, and API components.

```
DEPARTMENTS DASHBOARD/
│
├── main_portal/                        # Central configuration hub
│   ├── settings.py                     # Global DB connections (SQLite / PostgreSQL), session sharing, auth backends
│   ├── urls.py                         # Master router mounting all sub-module URLs & API routes
│   └── wsgi.py / asgi.py
│
├── portal/                             # Main Single Sign-On Gateway & Admin Portal
│   ├── models.py                       # UserModuleAccess, AccessRequest, and PortalNotification
│   ├── urls.py                         # Main landing dashboard routes and admin controls
│   ├── views/                          # Route handlers (auth_views, admin_views, dashboard_views)
│   ├── static/portal/                  # Static assets (CSS design system, Alpine.js, images)
│   └── templates/portal/               # Gateway Template Files (Landing, Department Grid, Access Matrix)
│
├── TPM Portal/                         # Total Productive Maintenance Module (Pillars 1-8)
│   └── tpm/
│       ├── models.py                   # PillarEntry, KPIValue, CustomKPIDefinition, Workstation, KaizenSheet
│       ├── urls.py                     # TPM analytics & KPI entry routing
│       └── templates/                  # TPM Screens (Governance, Pillar entries, Kaizen forms)
│
├── CMC Portal/                         # Condition Monitoring Cell (Machinery Health)
│   └── cmc/
│       ├── models.py                   # Lubrication schedules, vibration indices, Wear Debris Analysis (WDA)
│       ├── urls.py                     # Route mapping for machinery inspection and grease reports
│       └── templates/cmc/              # Vibrational graphs, oil testing, WDA matrices
│
├── Delays Portal/                      # Downtime Logs & Operations Bottlenecks
│   └── delays/
│       ├── models.py                   # Downtime instances, category maps, delay reasons
│       ├── urls.py                     # Delay analytics & manual entry lists
│       └── templates/delays/           # Breakdown graphs, log entry forms, checklists
│
├── EFMEA/                              # Failure Mode and Effects Analysis
│   └── fmea/
│       ├── models.py                   # RPN indices (Severity × Occurrence × Detection)
│       └── templates/fmea/             # Risk index, top 10 risks, failure register spreadsheet
│
├── capa/                               # Corrective & Preventive Actions
│   ├── docx_parser.py                  # Standard docx layout parser
│   ├── models.py                       # 5-Whys, 5M matrices, CAPAReport
│   └── templates/capa/                 # Incident description, 5-Whys logger, printable sheets
│
├── Safety/                             # Hazard Logging & Incident Tracking
│   ├── models.py                       # Near-miss reports, safety hazard audits
│   └── templates/safety/               # Incident manager dashboard (hazard lists, KPI indicators)
│
├── quality/                            # Quality Control Parameters
│   ├── models.py                       # Rejection metrics, heat-wise chemical analyses
│   └── templates/quality/              # Daily quality graphs, lab value logger, summary reports
│
├── hod_kpi/                            # HOD Key Performance Indicators
│   ├── models.py                       # Month-wise KPI parameters & targets
│   └── templates/hod_kpi/              # High-density actual vs target comparison tables
│
├── smed/                               # Single-Minute Exchange of Die (Quick Changeover)
│   ├── models.py                       # Changeover logs, internal/external activity metrics
│   ├── views.py                        # SMED analytics & stage execution tracking
│   └── templates/smed/                 # Stage tracking, activity breakdown charts
│
├── api/                                # REST API Backend Layer (Django REST Framework + JWT)
│   ├── views.py                        # Authentication, department status, module telemetry APIs
│   ├── serializers.py                  # JSON serialization for mobile client
│   └── urls.py                         # REST API endpoints `/api/v1/`
│
├── jspl_mobile/                        # React Native / Expo Mobile Application
│   ├── src/                            # App views, webview integration, JWT auth storage
│   ├── app.json                        # Expo app configuration
│   └── package.json                    # React Native dependencies
│
├── db.sqlite3                          # Shared Local Development SQLite Database
└── requirements.txt                    # Project dependencies (Django 5.1, psycopg2-binary, etc.)
```

---

## 2. Database Configuration (Development vs Production)

The portal dynamically selects the database engine based on the environment configuration in `main_portal/settings.py`.

### 🔹 Local Development (SQLite3)
By default, if no environment variables are set, the portal uses the lightweight SQLite database located at `db.sqlite3`:

```python
# Automatic default fallback in main_portal/settings.py
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}
```

### 🔹 Production Deployment (PostgreSQL)
In production environments (e.g., Company Server), set `DB_NAME` and associated credentials in your environment variables. The portal automatically switches to **PostgreSQL** using `psycopg2-binary`:

```python
if os.environ.get('DB_NAME'):
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': os.environ['DB_NAME'],
            'USER': os.environ.get('DB_USER', 'dept_db_user'),
            'PASSWORD': os.environ.get('DB_PASSWORD', 'your_secure_password'),
            'HOST': os.environ.get('DB_HOST', '172.17.0.20'),
            'PORT': os.environ.get('DB_PORT', '5432'),
        }
    }
```

#### Environment Variables Summary for Production PostgreSQL:
| Variable | Description | Example / Default |
| :--- | :--- | :--- |
| `DB_NAME` | PostgreSQL Database Name | `jspl_operations_db` |
| `DB_USER` | Database Username | `dept_db_user` |
| `DB_PASSWORD` | Database User Password | `TMPortal@4321` |
| `DB_HOST` | Database Host / IP Address | `172.17.0.20` |
| `DB_PORT` | Database Server Port | `5432` |

---

## 3. Design System Guidelines (For Figma / UI Designers)

We aim to replace the default bootstrap layouts with a **minimal, small-looking UI**. Focus on a compact, information-dense, yet clean aesthetic.

### 🎨 Color Palette & Theming
*   **Brand Colors**: Professional corporate steel and energy tones.
    *   *Primary (Steel Blue)*: HSL `218, 30%, 20%` (Sleek dark blue-grey).
    *   *Secondary (Industrial Orange)*: HSL `28, 90%, 50%` (Accent details/buttons).
*   **Backgrounds**: Off-white HSL `210, 20%, 98%` with card backgrounds in pure white.
*   **State Indicators (Micro Badges)**:
    *   *Access Granted (EDIT)*: HSL `145, 60%, 45%` (Soft green).
    *   *Access Read-Only (VIEW)*: HSL `200, 70%, 45%` (Soft blue).
    *   *Restricted (LOCKED)*: HSL `0, 0%, 40%` (Cool charcoal grey).

### 📐 Layout & Spacing
*   **Compact Density**: Reduce padding and margins (`p-2` / `p-3` standard). Tables should use tight padding (`py-1.5 px-3`) to maximize content visible on small display resolutions.
*   **Typography**: Clean sans-serif fonts such as **Inter**, **Roboto**, or **Outfit**. Text sizes should range from `12px` (sub-details, metadata) to `24px` (dashboard header).
*   **Component Cards**: Border radius of `8px` or `12px` maximum. Subtle, soft shadows (`box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05)`).
*   **Navigation Elements**:
    *   *Collapsible Side-Drawer (`☰`)*: Smooth sliding transition (`width 0.25s ease`). Thin, icons-only state when collapsed.
    *   *Header Breadcrumbs*: Light text links divided by simple separators (`›`) for quick module context.

---

## 4. Screen-by-Screen UI Specifications

Use these specifications to build wireframes in Figma:

### Screen A: Single Sign-On Gateway Landing (`portal/templates/portal/auth/login.html`)
*   **Purpose**: Authentication access-point for plant members.
*   **Elements**:
    1.  Centred clean login box (User credentials field, password input with password toggler eye icon).
    2.  "Request Portal Access" button leading to a signup modal/slide-over (fields: First/Last Name, Email, Department selection dropdown, Designation, Phone number).
    3.  Password Recovery trigger.

### Screen B: Main Plant Directory Dashboard (`portal/templates/portal/dashboard/plant_dashboard.html`)
*   **Purpose**: Central hub routing users to their authorized operational apps.
*   **Elements**:
    1.  **Header section**: breadcrumbs, notifications button (bell icon with unread indicator badge), and user profile dropdown showing active department/role.
    2.  **28 Department Cards Accordion Grid**:
        *   Compact cards showing Department Code (e.g. `SMS-2`, `BF-1`) and Department Name.
        *   Clicking a card expands/collapses it downward. The user's primary department is automatically expanded on load.
    3.  **Expanded Module Buttons Grid**:
        *   Inside the expanded department, render grid blocks for each of the operational modules.
        *   *If Accessible*: Bright block displaying module icon, title, description, and an access-level tag ("View Only" or "View + Edit").
        *   *If Restricted*: Grayed-out block showing a padlock icon with a "Locked" badge.

### Screen C: Admin Access Control Matrix (`portal/templates/portal/admin/manage_access.html`)
*   **Purpose**: Dynamic grid for adjusting permissions in real-time.
*   **Elements**:
    1.  **Search & Filter Bar**: Instant filter by Username, Department, or Access levels.
    2.  **Access Grid (Matrix Table)**:
        *   *Rows*: User details (Employee ID, Name, Department).
        *   *Columns*: Sub-modules (TPM, CMC, Delays, FMEA, CAPA, Safety, SMED, etc.).
        *   *Cells*: A dynamic dropdown/pill button with values: `NONE` (grayed out), `VIEW` (blue badge), `EDIT` (green badge). Changing the dropdown fires an HTMX request to save permissions instantly without page reload.
    3.  **Access SignUp Requests Panel**: A drawer/section listing users waiting for approval, with "Approve" (green button) and "Reject" (red button) options.

### Screen D: HOD KPI Month-Wise Matrix Grid (`hod_kpi/templates/hod_kpi/dashboard.html`)
*   **Purpose**: Executive dashboard displaying KPI actuals vs target performance metrics.
*   **Elements**:
    1.  Fiscal Year selection filter.
    2.  High-density grid/table with columns: Metric name, Unit of Measure (UOM), Target, and 12 Monthly Columns (April to March) showing Actuals.

### Screen E: TPM Pillar Tracking & Entry Sheets (`TPM Portal/tpm/templates/`)
*   **Governance Structure (`governance/structure.html`)**: Organizational layout displaying cards for Sponsors, Steering Committee, Pillar Coordinators, and HODs.
*   **Pillar KPI Matrix (`department/overview.html`)**: Grid of the 8 TPM pillars (KK, JH, PM, QM, ET, DM, SHE, OTPM) showing monthly submission statuses.
*   **Excel-style Entry Table (`department/pillar_entry.html`)**: Interactive data spreadsheet with KPI benchmark, target, actual, and remarks.

### Screen F: Condition Monitoring Machinery Hub (`CMC Portal/cmc/templates/cmc/dashboard.html`)
*   **Vibrational Diagnostics Table**: Grid list of heavy plant machinery showing vibration levels with alert flags (Normal, Warning, Alarm).
*   **Oil Testing & Wear Debris Analysis (WDA)**: Analysis cards displaying particle counts, viscosity metrics, and reports.

### Screen G: Delays Portal & Checklists (`Delays Portal/delays/templates/delays/`)
*   **Delays Dashboard**: Breakdown graphs, MTTR/MTBF reliability tables, and monthly summaries.
*   **Checklist Logger**: Check item actions with OK / NOT OK triggers and dynamic remarks logging.

### Screen H: Corrective & Preventive Action Reports (`capa/templates/capa/`)
*   **5-Whys Analysis Board & CAPA Plan Matrix**: Visual mapping of investigation process and action owner tracking.

### Screen I: SMED Changeover Tracking (`smed/templates/smed/`)
*   **Quick Changeover Dashboard**: Analysis of internal vs external activities, reduction targets, and changeover logs.

---

## 5. Installation & Setup Instructions

Follow these step-by-step instructions to get the unified portal running locally or in production:

### Step 1: Set Up the Virtual Environment
Create and activate a Python virtual environment at the workspace root:

```bash
# Create the virtual environment from the workspace root
python -m venv .venv

# On Windows (Command Prompt):
.venv\Scripts\activate

# On Windows (PowerShell):
.\.venv\Scripts\activate

# On Linux/macOS:
source .venv/bin/activate
```

### Step 2: Install Dependencies
Install all shared dependencies including Django, PostgreSQL driver (`psycopg2-binary`), UI helpers, document parsers, and REST API frameworks:

```bash
pip install -r requirements.txt
```

### Step 3: Configure Database

#### Option A: Local SQLite (Default)
No setup required! Leaving `DB_NAME` unset will cause the project to create/use `db.sqlite3`.

#### Option B: Production PostgreSQL
Set environment variables before running migrations or server commands:

```cmd
:: On Windows CMD
set DB_NAME=jspl_operations_db
set DB_USER=dept_db_user
set DB_PASSWORD=your_password
set DB_HOST=172.17.0.20
set DB_PORT=5432
```

```powershell
# On Windows PowerShell
$env:DB_NAME="jspl_operations_db"
$env:DB_USER="dept_db_user"
$env:DB_PASSWORD="your_password"
$env:DB_HOST="172.17.0.20"
$env:DB_PORT="5432"
```

```bash
# On Linux/macOS
export DB_NAME=jspl_operations_db
export DB_USER=dept_db_user
export DB_PASSWORD=your_password
export DB_HOST=172.17.0.20
export DB_PORT=5432
```

### Step 4: Apply Database Migrations
Generate and apply all unified database tables across all modules (works for both SQLite and PostgreSQL):

```bash
# Generate migrations
python manage.py makemigrations portal tpm cmc delays fmea capa Safety quality hod_kpi smed api

# Apply migrations
python manage.py migrate
```

### Step 5: Seed the Database
Populate master registries, module configurations, test data, and user accounts:

```bash
# Seed the main portal gateway (departments, modules, permissions, and default users)
python manage.py seed_portal

# Seed the TPM module data (pillar KPIs, workstation structures, and demo actuals)
python manage.py seed

# Seed the CMC module data (vibration schedule list)
python manage.py seed_cmc
```

---

## 6. Running the Development & Production Servers

### Running Locally (Development)
Start the unified Django development server:

```bash
python manage.py runserver
```

Once running, access the portal in your browser at:
**`http://127.0.0.1:8000/`**

### Running in Production (with PostgreSQL & WSGI/ASGI)
Collect static files and run using Waitress, Gunicorn, or uWSGI:

```bash
# Collect static assets into staticfiles/
python manage.py collectstatic --noinput

# Run via Waitress (Windows Production example):
pip install waitress
waitress-serve --port=8000 main_portal.wsgi:application
```

---

## 7. Technologies Used

*   **Back-End Core**: Python (Django 5.1 Framework)
*   **REST API Layer**: Django REST Framework + Simple JWT (Authentication for mobile app)
*   **Front-End**: Vanilla HTML5, CSS3 Custom Properties (Design System), Alpine.js
*   **Dynamic Networking**: HTMX (for asynchronous state updates without page reloading)
*   **Mobile App**: React Native / Expo (`jspl_mobile`)
*   **Document Parsers**: `python-docx` (DOCX parsing), `pypdf` (PDF parsing), `openpyxl`/`xlrd` (Excel import/export)
*   **Database Architecture**:
    *   **Development**: **SQLite3** (Lightweight, zero-config local database)
    *   **Production**: **PostgreSQL** (Enterprise relational database connected via `psycopg2-binary`)

