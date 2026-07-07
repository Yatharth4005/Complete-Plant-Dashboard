# Jindal Steel Operations Portal - Unified Departments & Modules Hub (RGH Plant)

This repository houses the **Jindal Steel Operations Portal** for the RGH Plant. Acting as a Single Sign-On (SSO) central gateway, it consolidates **28 plant departments** and **13 operational modules** (TPM, CMC, ISO, Delays, OEE, Availability, FMEA, CAPA, Safety, Production, Quality, Spare Management, Improvement Project Dakshata) under a unified Django project sharing a single database runtime.

---

## 1. Project Directory Structure & Repository Map

Below is the directory map of the Django applications and templates. Use this as a reference to locate models, templates, and view files.

```
DEPARTMENTS DASHBOARD/
│
├── main_portal/                        # Central configuration hub
│   ├── settings.py                     # Global DB connections, session sharing, auth backends
│   ├── urls.py                         # Master router mounting all sub-module URLs
│   └── wsgi.py / asgi.py
│
├── portal/                             # Main Single Sign-On Gateway & Admin Portal
│   ├── models.py                       # UserModuleAccess, AccessRequest, and PortalNotification
│   ├── urls.py                         # Main landing dashboard routes and admin controls
│   ├── views/                          # Route handlers (auth_views, admin_views, dashboard_views)
│   ├── static/portal/                  # Static assets
│   │   ├── css/portal.css              # Baseline style system for layout & accordions
│   │   ├── js/                         # Alpine.js interactive components
│   │   └── img/                        # Icons and graphics
│   └── templates/portal/               # Gateway Template Files
│       ├── base.html                   # Main page layout wrapper, top navigation, sidebar drawer
│       ├── auth/
│       │   ├── login.html              # Secure credentials gateway
│       │   └── reset_password.html     # Account recovery screen
│       ├── dashboard/
│       │   ├── plant_dashboard.html    # Core directory listing 28 departments with accordion grids
│       │   └── overall_plant_dashboard.html # Global stats & plant-wide KPI analytics
│       ├── department/
│       │   ├── dept_hub.html           # Dedicated departmental sub-modules panel
│       │   └── coming_soon.html        # Fallback screen for modules undergoing staging
│       └── admin/
│           ├── manage_access.html      # Access Matrix (HTMX-driven grid mapping users to permissions)
│           ├── user_informations.html  # Directory lists for user account creations/edits
│           └── manage_departments.html # Registers of plant departments and metadata
│
├── TPM Portal/                         # Total Productive Maintenance Module (Pillars 1-9)
│   └── tpm/
│       ├── models.py                   # PillarEntry, KPIValue, CustomKPIDefinition, Workstation, KaizenSheet
│       ├── urls.py                     # TPM analytics & KPI entry routing
│       └── templates/                  # TPM Screens
│           ├── base.html               # Sub-module baseline layout with side-drawer navigation
│           ├── dashboard/
│           │   └── plant_dashboard.html # TPM pillar compliance charts & overall plant OEE status
│           ├── department/
│           │   ├── overview.html       # Monthly 8-Pillar grid scores (colored statuses: Open/Done)
│           │   ├── pillar_entry.html   # Excel-style editable KPI entries per pillar
│           │   ├── report.html         # Exportable summary tables & compliance documents
│           │   └── ws_kpi.html         # Workstation-specific KPI entries
│           ├── governance/
│           │   ├── structure.html      # Organization chart: Sponsors, HODs, Coordinators
│           │   └── users.html          # Sub-admin role management interfaces
│           └── partials/               # HTMX micro-templates (modals, Kaizen lists, CAPA templates)
│
├── CMC Portal/                         # Condition Monitoring Cell (Machinery Health)
│   └── cmc/
│       ├── models.py                   # Lubrication schedules, vibration indices, Wear Debris Analysis (WDA)
│       ├── urls.py                     # Route mapping for machinery inspection and grease reports
│       └── templates/cmc/
│           ├── base_cmc.html           # CMC core visual layout
│           ├── dashboard.html          # Vibrational analysis graphs, alarms, alert indicators
│           ├── vibration/              # Machine-wise amplitude logs, frequencies, measurement tables
│           ├── oil_test/               # Lubrication quality reports (viscosity, contamination logs)
│           ├── wda/                    # Wear Debris Analysis matrices
│           └── schedule/               # Periodic routing schedules (excel import list)
│
├── Delays Portal/                      # Downtime Logs & Operations Bottlenecks
│   └── delays/
│       ├── models.py                   # Downtime instances, category maps, delay reasons
│       ├── urls.py                     # Delay analytics & manual entry lists
│       └── templates/delays/
│           ├── base_delays.html        # Layout wrapper
│           ├── dashboard.html          # Downtime duration graphs (Breakdown hours, loss summaries)
│           ├── log_entry.html          # Production delay logger (forms for start-time, stop-time, remarks)
│           └── manage_options.html     # Configuration tables for delay reason codes
│
├── EFMEA/                              # Failure Mode and Effects Analysis
│   └── fmea/
│       ├── models.py                   # RPN indices (Severity × Occurrence × Detection)
│       └── templates/fmea/
│           ├── dashboard.html          # Master FMEA risk index, Top 10 risks list
│           ├── identification.html     # Action items logger
│           ├── register.html           # failure mode register spreadsheet
│           └── report.html             # Multi-department action plan exports
│
├── capa/                               # Corrective & Preventive Actions
│   ├── docx_parser.py                  # Standard docx layout parser
│   ├── models.py                       # 5-Whys, 5M (Man, Machine, Material...) matrices, CAPAReport
│   └── templates/capa/
│       ├── dashboard.html              # CAPA status tracking (Open, Closed, Overdue)
│       ├── manual_entry.html           # Form logic for Incident description, 5-Whys, Actions
│       └── report.html                 # CAPA certificate format, printable sheet layout
│
├── Safety/                             # Hazard Logging & Incident Tracking
│   ├── models.py                       # Near-miss reports, safety hazard audits
│   └── templates/safety/
│       └── im_dashboard.html           # Incident manager dashboard (hazard lists, charts, safety KPI indicators)
│
├── quality/                            # Quality Control Parameters
│   ├── models.py                       # Rejection metrics, heat-wise chemical analyses
│   └── templates/quality/
│       ├── dashboard.html              # Chemistry charts, daily production quality graphs
│       ├── quality_entry.html          # Lab values logger (high/low tolerance indicators)
│       └── summary_report.html         # Quality assurance compliance summary
│
├── hod_kpi/                            # HOD Key Performance Indicators
│   ├── models.py                       # Month-wise KPI parameters & targets
│   └── templates/hod_kpi/
│       └── dashboard.html              # High-density actual vs target comparison tables
│
└── db.sqlite3                          # Unified Shared SQLite Database
```

---

## 2. Design System Guidelines (For Figma / UI Designers)

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

## 3. Screen-by-Screen UI Specifications

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
        *   Inside the expanded department, render grid blocks for each of the 13 modules.
        *   *If Accessible*: Bright block displaying module icon, title, description, and an access-level tag ("View Only" or "View + Edit").
        *   *If Restricted*: Grayed-out block showing a padlock icon with a "Locked" badge.

### Screen C: Admin Access Control Matrix (`portal/templates/portal/admin/manage_access.html`)
*   **Purpose**: Dynamic grid for adjusting permissions in real-time.
*   **Elements**:
    1.  **Search & Filter Bar**: Instant filter by Username, Department, or Access levels.
    2.  **Access Grid (Matrix Table)**:
        *   *Rows*: User details (Employee ID, Name, Department).
        *   *Columns*: Sub-modules (TPM, CMC, Delays, FMEA, CAPA, etc.).
        *   *Cells*: A dynamic dropdown/pill button with values: `NONE` (grayed out), `VIEW` (blue badge), `EDIT` (green badge). Changing the dropdown fires an HTMX request to save permissions instantly without page reload.
    3.  **Access SignUp Requests Panel**: A drawer/section listing users waiting for approval, with "Approve" (green button) and "Reject" (red button) options.

### Screen D: HOD KPI Month-Wise Matrix Grid (`hod_kpi/templates/hod_kpi/dashboard.html`)
*   **Purpose**: Executive dashboard displaying KPI actuals vs target performance metrics.
*   **Elements**:
    1.  Fiscal Year selection filter.
    2.  High-density grid/table with the following columns:
        *   *Metric name / KPI descriptor*
        *   *Unit of Measure (UOM)*
        *   *Target*
        *   *12 Columns (April to March)*: Each cell displays the **Actual** value. If Actual meets Target, highlight with a subtle green border/dot. If below target, highlight with a subtle orange border/dot.

### Screen E: TPM Pillar Tracking & Entry Sheets (`TPM Portal/tpm/templates/`)
*   **Governance Structure (`governance/structure.html`)**: Organizational layout displaying cards for Sponsors, Steering Committee, Pillar Coordinators, and HODs, showing contact information.
*   **Pillar KPI Matrix (`department/overview.html`)**: Grid of the 8 TPM pillars (KK, JH, PM, QM, ET, DM, SHE, OTPM) showing a calendar summary (month-wise) color-coded by submission status (Submitted/Approved = Green, Draft = Blue, Overdue = Red).
*   **Excel-style Entry Table (`department/pillar_entry.html`)**: Interactive data spreadsheet with columns: `Serial No`, `KPI Name`, `UOM`, `Benchmark`, `Target`, `Actual`, and `Remarks`. Includes an auto-calculating "OEE" row for production indicators.
*   **Kaizen Sheets Logger (`partials/_kaizen_form.html`)**: Form layout for submitting continuous improvement ideas. Includes:
    *   Target loss categorizations checkboxes.
    *   Before and After photo upload placeholders side-by-side.
    *   Tangible & Intangible benefit lists (editable list rows).
    *   Horizontal Deployment matrix.

### Screen F: Condition Monitoring Machinery Hub (`CMC Portal/cmc/templates/cmc/dashboard.html`)
*   **Vibrational Diagnostics Table**: Grid list of heavy plant machinery (Turbines, Compressors, Blowers) showing critical vibration levels. Includes color-coded alert flags (Normal = Green, Warning = Yellow, Alarm = Red).
*   **Oil Testing & Wear Debris Analysis (WDA)**: Multi-column analysis card displaying copper/iron particles count, viscosity metrics, and recommendation reports.

### Screen G: Delays Portal (Downtime & Checklist Tracking)
*   **Delays Dashboard / Delay Summary**: View breakdown graphs, MTTR/MTBF reliability tables, and monthly summaries.
*   **Production Delay Logging (`Delays Portal/delays/templates/delays/log_entry.html`)**: Form containing inputs for Start & End Date/Time, Duration, Agency info, Equipment, and Root Cause.
*   **Checklist Summary**: Table listing submitted checklists with columns: Date, Equipment, Checklist Type, Checked By, Status (Completed, Action Needed, Critical Issue), and Remarks.
*   **Manual Checklist**: Dual-column checklist builder containing:
    *   *Left Column (Categorization & Asset Info)*: Matching the Delay Entry style (Agency Type, Responsible Agency, Area, Sub Area, Equipment, Sub Equipment, Shift Incharge).
    *   *Right Column (Action Tab)*: 5 check items with **OK / NOT OK** buttons. Selecting an action dynamically displays a dedicated **Remarks tab** input for that specific check item.

### Screen H: Corrective & Preventive Action Reports (`capa/templates/capa/manual_entry.html`)
*   **5-Whys Analysis Board**: A clean, numbered visual list mapping the investigation process (Problem -> Why 1 -> Why 2 -> Why 3 -> Why 4 -> Why 5).
*   **CAPA Plan Matrix**: Table listing the actions taken:
    *   *Columns*: Action Description, Owner, Target Date, Completion Date, Status (Open / Closed).

### Screen I: Failure Mode register spreadsheet (`EFMEA/fmea/templates/fmea/register.html`)
*   **FMEA Analysis Grid**: Dense table showing fields: `Item/Function`, `Potential Failure Mode`, `Effect`, `Severity (S)`, `Potential Causes`, `Occurrence (O)`, `Current Controls`, `Detection (D)`, and calculated `RPN (S × O × D)`. High RPN columns (> 100) are marked with warning flags.

---

## 4. Shared Database Model References

Here are the key database configurations linked to the views:

```python
# User Profile Attributes
- username, email, password, first_name, last_name
- role (ADMIN, USER)
- department (Foreign Key to Department)
- is_plant_admin (Boolean)
- employee_id, designation, phone

# Access matrix registry
- user (ForeignKey to User)
- department (ForeignKey to Department)
- module (ForeignKey to Module)
- access_level (VIEW, EDIT)
```

---

## 5. Installation & Setup Instructions

Follow these step-by-step instructions to get the unified portal running locally:

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
Install all shared dependencies for the portal, databases, and document parsers:

```bash
pip install -r requirements.txt
```

### Step 3: Apply Database Migrations
Generate and apply all unified database tables and fields across all modules:

```bash
# Generate migrations
python manage.py makemigrations portal tpm cmc delays fmea capa

# Apply migrations
python manage.py migrate
```

### Step 4: Seed the Database
Populate the master registries, module configurations, test data, and user accounts:

```bash
# Seed the main portal gateway (departments, modules, permissions, and default users)
python manage.py seed_portal

# Seed the TPM module data (pillar KPIs, workstation structures, and demo actuals)
python manage.py seed

# Seed the CMC module data (vibration schedule list from Excel sheet)
python manage.py seed_cmc
```

---

## 6. Running the Development Server

Start the single unified server from the root directory:

```bash
python manage.py runserver
```

Once running, access the portal in your browser at:
**`http://127.0.0.1:8000/`**

---

## 7. Technologies Used

*   **Back-End**: Python (Django Framework)
*   **Front-End**: Vanilla HTML5, CSS3 Custom Properties (Design System), Alpine.js
*   **Dynamic Networking**: HTMX (for asynchronous state updates without page reloading)
*   **Document Parsers**: python-docx (for DOCX parsing), pypdf (for PDF parsing)
*   **Database**: SQLite3
