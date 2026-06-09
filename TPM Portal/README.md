# JSPL TPM Portal — PRODUCTION-Grade Plant Analytics Portal

A complete Django 5 + HTMX + Alpine.js dashboard system designed for Jindal Steel & Power Ltd to track plant-wide TPM (Total Productive Maintenance) analytics across 28 departments.

No separate frontend building tools (npm/node_modules) are required. It operates natively using Django templates enhanced with HTMX dynamic page swaps and Alpine.js inline calculators.

---

## 📋 Table of Contents

- [Features](#-features)
- [Technology Stack](#-technology-stack)
- [Project Structure](#-project-structure)
- [Quick Start](#-quick-start)
- [Configuration](#-configuration)
- [Default Accounts](#-default-accounts)
- [Operating Guides](#-operating-guides)
- [Deployment](#-deployment)
- [Troubleshooting](#-troubleshooting)
- [Contributing](#-contributing)
- [License](#-license)

---

## ✨ Features

### Core Functionality
- **Plant-Wide Dashboard**: Comprehensive overview of all 28 departments with PRODUCTION trends, Kaizen tracking, and SHE incident monitoring
- **Department-Specific Dashboards**: Individual department analytics with pillar-wise performance metrics
- **8 TPM Pillars**: Complete implementation of standard TPM pillars:
  - KK (Kobetsu Kaizen)
  - JH (Jishu Hozen)
  - PM (Planned Maintenance)
  - SHE (Safety, Health, Environment)
  - QM (Quality Maintenance)
  - ED (Education & Training)
  - AM (Autonomous Maintenance)
  - FI (Focused Improvement)
- **Workstation KPI Tracking**: 9th pillar for granular workstation-level metrics
- **Interactive Analytics**: Real-time charts using Chart.js with HTMX-powered dynamic updates
- **Report Generation**: Exportable PDF and Excel reports with professional letterheads
- **User Management**: Role-based access control (Admin vs Department Users)
- **Data Entry Locking**: Monthly submission locking to ensure data integrity

### Technical Features
- **Zero Build Step**: No frontend build tools required
- **HTMX Integration**: Dynamic page swaps without full page reloads
- **Alpine.js**: Inline reactive components for calculators and UI state
- **Responsive Design**: Mobile-friendly interface with adaptive layouts
- **Print-Optimized Reports**: CSS print media queries for professional document generation
- **SQLite/PostgreSQL Support**: Flexible database backend configuration
- **WhiteNoise Middleware**: PRODUCTION-ready static file serving
- **CSRF Protection**: Built-in security for all form submissions

---

## 🛠️ Technology Stack

### Backend
- **Django 5.0**: Python web framework
- **Python 3.11+**: Runtime environment
- **SQLite/PostgreSQL**: Database backend
- **WhiteNoise**: Static file serving

### Frontend
- **HTMX 1.9.12**: Dynamic HTML updates
- **Alpine.js 3.14.1**: Lightweight JavaScript framework
- **Chart.js 4.4.3**: Data visualization
- **Sora Font**: Primary typography
- **JetBrains Mono**: Monospace font for data

### Styling
- **Custom CSS**: JSPL brand color system
- **CSS Variables**: Theme consistency
- **Responsive Grid**: Mobile-first design

---

## 📁 Project Structure

```
TPM Portal/
├── jspl_tpm/                 # Django project settings
│   ├── settings.py           # Main configuration
│   ├── urls.py               # Root URL routing
│   └── wsgi.py               # WSGI configuration
├── tpm/                      # Main application
│   ├── models.py             # Database models
│   ├── views/                # View logic
│   │   ├── auth.py           # Authentication views
│   │   ├── admin.py          # Admin panel views
│   │   ├── department.py     # Department views
│   │   └── plant.py          # Plant dashboard views
│   ├── templates/            # HTML templates
│   │   ├── base.html         # Base template
│   │   ├── auth/             # Authentication pages
│   │   ├── dashboard/       # Dashboard pages
│   │   ├── department/      # Department pages
│   │   ├── admin/           # Admin panel pages
│   │   └── partials/        # Reusable components
│   ├── static/              # Static assets
│   │   ├── css/            # Stylesheets
│   │   ├── js/             # JavaScript files
│   │   ├── images/         # Logo images
│   │   └── media/          # Media files (videos)
│   ├── utils/              # Utility functions
│   │   ├── kpi_definitions.py  # KPI configuration
│   │   └── seed.py         # Database seeding
│   ├── urls.py             # Application URL routing
│   └── admin.py            # Django admin configuration
├── venv/                    # Virtual environment (gitignored)
├── db.sqlite3              # SQLite database (gitignored)
├── manage.py               # Django management script
├── requirements.txt        # Python dependencies
└── README.md              # This file
```

---

## ⚡ Quick Start

### Prerequisites
- **Python 3.11+** installed
- **PostgreSQL** (Optional - falls back to SQLite if not configured)
- **Git** for version control

### Installation Steps

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd TPM Portal
   ```

2. **Create virtual environment**
   ```bash
   python -m venv venv
   ```

3. **Activate virtual environment**
   - Windows (PowerShell):
     ```powershell
     .\venv\Scripts\Activate.ps1
     ```
   - Linux/Mac:
     ```bash
     source venv/bin/activate
     ```

4. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

5. **Configure environment variables** (Optional)
   Create a `.env` file in the project root:
   ```ini
   SECRET_KEY=your-django-PRODUCTION-secret-key
   DEBUG=True
   DB_NAME=tpm_db
   DB_USER=postgres
   DB_PASSWORD=yourpassword
   DB_HOST=localhost
   DB_PORT=5432
   ```
   *Note: If no database environment variables are defined, SQLite will run by default.*

6. **Run migrations**
   ```bash
   python manage.py makemigrations
   python manage.py migrate
   ```

7. **Seed the database**
   ```bash
   python manage.py seed
   ```
   This creates:
   - Default roles (Admin, User)
   - 28 plant departments
   - Admin and department user accounts
   - 5 months of mock KPI data for testing

8. **Run development server**
   ```bash
   python manage.py runserver
   ```

9. **Access the application**
   Navigate to: `http://127.0.0.1:8000`

---

## ⚙️ Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `SECRET_KEY` | Django secret key | Auto-generated |
| `DEBUG` | Debug mode | `True` |
| `DB_NAME` | Database name | `db.sqlite3` |
| `DB_USER` | Database user | `postgres` |
| `DB_PASSWORD` | Database password | - |
| `DB_HOST` | Database host | `localhost` |
| `DB_PORT` | Database port | `5432` |

### Static Files

Static files are served using WhiteNoise middleware. To collect static files for PRODUCTION:

```bash
python manage.py collectstatic
```

### Media Files

Media files (user uploads, reports) are stored in the `media/` directory.

---

## 🔑 Default Accounts

### Administrator Account
- **Username**: `admin`
- **Password**: `Admin@1234`
- **Access**: Plant-wide dashboard, user management, department management

### Department User Accounts
All department users share the same password: `Dept@1234`

| Department | Username | Code |
|------------|----------|------|
| Plate Mill | `pm` | PM |
| SMS-2 | `sms2` | SMS2 |
| Blast Furnace-1 | `bf1` | BF1 |
| Blast Furnace-2 | `bf2` | BF2 |
| DRI-1 | `dri1` | DRI1 |
| Oxygen Plant | `op` | OP |
| Sinter | `sint` | SINT |

*Supports all 28 department code acronyms in lowercase*

---

## 📖 Operating Guides

### Adding a New KPI

**Do NOT hardcode KPI definitions in templates.**

All KPI structures are defined in the central configuration file:
`tpm/utils/kpi_definitions.py`

To add a new metric to any pillar:

```python
# Example: Adding to KK pillar
KK_KPIS = [
    # ... existing KPIs ...
    {
        'sl_no': '17',
        'name': 'New Custom KPI Name',
        'uom': 'Nos',
        'benchmark': 0.0,
        'target': 1.0
    }
]
```

The application automatically pulls this configuration when rendering forms, reports, and analytics.

### Adding a New Department

**Option 1: Command Line**
- Add entry to `tpm/utils/seed.py` and run `python manage.py seed`

**Option 2: Django Admin**
- Navigate to `http://127.0.0.1:8000/admin/`
- Log in with admin credentials
- Add entry under Department model

**Option 3: UI Panel**
- Navigate to `http://127.0.0.1:8000/admin-panel/departments/`
- Create department from the form

### Monthly Data Entry Workflow

1. **Login** with department credentials
2. **Navigate** to your department dashboard
3. **Select month/year** from dropdown filters
4. **Enter KPI data** for each pillar
5. **Submit** to lock the month's data
6. **View analytics** in the Analytics tab
7. **Generate reports** from the Report Generator page

### Report Generation

1. Navigate to your department's Report Generator page
2. Select month and year
3. Click "Export PDF" or "Export Excel"
4. Reports include:
   - Department letterhead with logo
   - Pillar-wise achievement scores
   - Action required KPIs (achievement < 80%)
   - Detailed KPI breakdown tables
   - Signature blocks

---

## 🚀 Deployment

### PRODUCTION Settings

Update `jspl_tpm/settings.py`:

```python
DEBUG = False
ALLOWED_HOSTS = ['your-domain.com', 'www.your-domain.com']

# Security
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_SSL_REDIRECT = True
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
```

### Static Files

```bash
python manage.py collectstatic --noinput
```

### Database Migration

```bash
python manage.py makemigrations
python manage.py migrate
```

### Using Gunicorn (Recommended)

```bash
pip install gunicorn
gunicorn jspl_tpm.wsgi:application --bind 0.0.0.0:8000
```

### Using Docker (Optional)

Create a `Dockerfile`:

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
RUN python manage.py collectstatic --noinput
CMD ["gunicorn", "jspl_tpm.wsgi:application", "--bind", "0.0.0.0:8000"]
```

### Nginx Configuration (Example)

```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    location /static/ {
        alias /app/staticfiles/;
    }

    location /media/ {
        alias /app/media/;
    }
}
```

---

## 🔧 Troubleshooting

### Common Issues

**Issue: Static files not loading**
- Solution: Run `python manage.py collectstatic`

**Issue: Database migration errors**
- Solution: Delete `db.sqlite3` and run migrations again

**Issue: Permission denied on venv activation (Windows)**
- Solution: Run PowerShell as Administrator or use:
  ```powershell
  Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
  ```

**Issue: HTMX requests not working**
- Solution: Ensure CSRF tokens are properly included in forms

**Issue: Charts not rendering**
- Solution: Check browser console for JavaScript errors, ensure Chart.js is loaded

### Getting Help

- Check Django documentation: https://docs.djangoproject.com/
- Review HTMX documentation: https://htmx.org/docs/
- Check Alpine.js documentation: https://alpinejs.dev/

---

## 🤝 Contributing

### Development Workflow

1. Create a feature branch
2. Make your changes
3. Test thoroughly
4. Update documentation if needed
5. Submit a pull request

### Code Style

- Follow PEP 8 guidelines
- Use meaningful variable names
- Add comments for complex logic
- Keep functions focused and small

### Testing

- Test all features before committing
- Verify responsive design on different screen sizes
- Check database migrations work correctly
- Test with both SQLite and PostgreSQL

---

## 📄 License

This project is proprietary software for Jindal Steel & Power Ltd. All rights reserved.

---

## 📞 Support

For technical support or questions, contact:
- **Email**: admin@jspl.com
- **Extension**: 4501 / Desk 12

---

## 🎯 Roadmap

### Planned Features
- [ ] Real-time data synchronization
- [ ] Mobile application
- [ ] Advanced analytics with AI insights
- [ ] Integration with plant ERP systems
- [ ] Multi-language support
- [ ] Enhanced reporting with custom templates

---

**Built with ❤️ for Jindal Steel & Power Ltd**
