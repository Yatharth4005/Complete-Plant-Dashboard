# Jindal Steel Operations Portal - Unified Departments & Modules Hub (RGH Plant)

This repository contains the **Jindal Steel Operations Portal** for the RGH Plant. It acts as a Single Sign-On (SSO) central gateway, linking **28 departments** and **8 operational modules** (TPM, CMC, ISO, Delays, OEE, Availability, FMEA, CAPA) through a secure, permission-controlled landing hub.

The sub-portals and modules are fully consolidated under a unified Django project, allowing the entire ecosystem to run seamlessly on a single server instance.

---

## 1. System Architecture & Consolidations

All departments and modules are served through a single Django entry point:

1. **Unified Gateway Dashboard**:
   - Built using Django, custom CSS design systems, HTMX, and Alpine.js.
   - Houses the central database models (`User`, `Department`, `Module`, `UserModuleAccess`, `AuditLog`).
   - Serves the Single Sign-In page and the master **Plant Dashboard** displaying all 28 department accordions.
   - Features the real-time **Access Control Matrix** admin panel, driven by **HTMX** for instantaneous permission updates.

2. **Consolidated Modules (Run on Port 8000)**:
   - **Total Productive Maintenance (TPM)**: KPI tracking across 8 pillars + Workstation KPIs (resides in `TPM Portal/tpm`).
   - **Condition Monitoring Cell (CMC)**: Machinery health, vibration monitoring, oil testing, and wear debris analysis (resides in `CMC Portal/cmc`).
   - **Delay Logs & Tracking**: Production line downtime, log summaries, and breakdown analysis (resides in `Delays Portal/delays`).
   - **FMEA**: Failure Mode and Effects Analysis for risk identification and mitigation (resides in `EFMEA/fmea`).
   - **CAPA**: Corrective Action and Preventive Action tracking and report generation (resides in `capa`).

Since all modules are part of the same Django runtime, they share a single database, session state, and user authentication model seamlessly without needing cross-port cookies.

---

## 2. Main Dashboard & Sidenav Features

- **Department Accordions**: All 28 plant departments are displayed as clean, compact cards. Clicking a card expands it downward to reveal its modules list. Clicking again collapses it.
- **Smart Auto-Expansion**: The landing dashboard checks the logged-in user's profile and automatically expands their assigned primary department (e.g. `SMS2` expands automatically for SMS-2 users).
- **Responsive Sidenav Toggling**: A collapse menu toggle (`☰`) is present in the topbar on both desktop and mobile views. The sidebar retracts smoothly with CSS width slide transitions.
- **Access Control Matrix**: Admins can visit `/admin/access/` to view and update access levels (EDIT, VIEW, NONE) for all users across all departments in real-time.

---

## 3. Installation & Setup Instructions

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
# 4a. Seed the main portal gateway (departments, modules, permissions, and default users)
python manage.py seed_portal

# 4b. Seed the TPM module data (pillar KPIs, workstation structures, and demo actuals)
python manage.py seed

# 4c. Seed the CMC module data (vibration schedule list from Excel sheet)
python manage.py seed_cmc
```

---

## 4. Running the Development Server

Start the single unified server from the root directory:

```bash
python manage.py runserver
```

Once running, access the portal in your browser:
**`http://127.0.0.1:8000/`**

---

## 5. User Credentials & Roles

The database seeding command (`seed_portal`) populates standard test users and role-based access assignments:

- **Plant Admin User**:
  - **Username**: `saurabh.agrawal@jindalsteel.in`
  - **Password**: `Admin@1234`
  - **Role**: Administrator with full Access Matrix controls.

- **Department User (SMS-2)**:
  - **Username**: `lalit.goyal@jindalsteel.in`
  - **Password**: `Dept@1234`
  - **Role**: Departmental user with TPM Edit and CMC View permissions configured in SMS-2.

To create a new custom administrator account with full privileges on your system, run:
```bash
python manage.py createsuperuser
```

---

## 6. Technologies Used

- **Back-End**: Python (Django Framework)
- **Front-End**: Vanilla HTML5, CSS3 Custom Properties (Design System), Alpine.js
- **Dynamic Networking**: HTMX (for asynchronous state updates without page reloading)
- **Document Parsers**: python-docx (for DOCX parsing), pypdf (for PDF parsing)
- **Database**: SQLite3
