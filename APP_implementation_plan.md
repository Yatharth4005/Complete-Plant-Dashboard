# 📱 JSPL Departments Dashboard — Mobile App Implementation Plan

## Overview

You have a Django + PostgreSQL web portal with multiple modules:
**TPM, CMC, Delays, FMEA, CAPA, Safety, HOD KPI, Quality**

The goal is to build a **downloadable mobile app (Android + iOS)** that connects to the **same production PostgreSQL database** — so everything is in sync in real-time, and you can work from home without needing VPN.

---

## 🏗️ Architecture Overview

```
📱 Mobile App (React Native)
         ↕  HTTPS / REST API
🌐 Django REST API (New Layer on top of existing Django)
         ↕
🐘 PostgreSQL (Same Production DB — untouched)
```

> The mobile app **never talks to Postgres directly**.
> It talks to a **REST API** you add on top of your existing Django project.
> The DB stays the same. No migration needed.

---

## 🔑 Key Decisions

| Decision | Choice | Reason |
|---|---|---|
| Mobile Framework | **React Native (Expo)** | One codebase → Android + iOS. Expo makes it easy to build & distribute |
| API Layer | **Django REST Framework (DRF)** | Already using Django. Just add DRF on top |
| Auth | **JWT Tokens** | Mobile-friendly, no session cookies needed |
| Distribution | **APK (Android)** + App Store (iOS) | APK = shareable file, no Play Store needed |
| Hosting | **Your existing server or free cloud** | Render / Railway free tier works |

---

## 📋 Phase-by-Phase Plan

---

## ✅ PHASE 1 — Django REST API (Backend)
> **Time: 3–5 days | Done on your office PC or from home once deployed**

### What you'll do:
Add `djangorestframework` and `djangorestframework-simplejwt` to your existing project.

### Step 1.1 — Install packages
```bash
pip install djangorestframework djangorestframework-simplejwt django-cors-headers
```

Add to `requirements.txt`:
```
djangorestframework==3.15.2
djangorestframework-simplejwt==5.3.1
django-cors-headers==4.4.0
```

### Step 1.2 — Update `settings.py`
```python
INSTALLED_APPS = [
    ...
    'rest_framework',
    'corsheaders',
]

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',  # Must be first
    ...
]

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ),
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.IsAuthenticated',
    ),
}

CORS_ALLOWED_ORIGINS = [
    "http://localhost:8081",  # Expo dev
    "https://yourdomain.com",  # Production
]
```

### Step 1.3 — Create API URLs (`main_portal/urls.py`)
```python
path('api/', include('api.urls')),
```

### Step 1.4 — Create `api/` Django app with endpoints

#### Auth Endpoints:
| Method | URL | Description |
|---|---|---|
| POST | `/api/auth/login/` | Login → returns JWT token |
| POST | `/api/auth/refresh/` | Refresh token |
| GET | `/api/auth/me/` | Get current user info |

#### Dashboard Endpoints:
| Method | URL | Description |
|---|---|---|
| GET | `/api/dashboard/` | Modules + departments user can access |
| GET | `/api/notifications/` | User notifications |

#### Module Endpoints (one per module):
| Method | URL | Description |
|---|---|---|
| GET | `/api/tpm/` | TPM data |
| GET | `/api/checklists/` | Checklist list |
| POST | `/api/checklists/{id}/submit/` | Submit checklist |
| GET | `/api/delays/` | Delays data |
| GET | `/api/capa/` | CAPA reports |
| GET | `/api/safety/` | Safety records |
| GET | `/api/hod-kpi/` | HOD KPI data |
| GET | `/api/quality/` | Quality data |

---

## ✅ PHASE 2 — Make Django Accessible from Internet
> **Time: 1–2 days | This solves your "work from home" problem too!**

### Option A: Deploy to Render (FREE — Recommended)
1. Push your Django project to GitHub (already done — you have `.git`)
2. Go to [render.com](https://render.com) → New Web Service
3. Connect your GitHub repo
4. Set environment variables (DB credentials, SECRET_KEY)
5. Render gives you a public URL like `https://jspl-dashboard.onrender.com`

> Your PostgreSQL stays on the company server.
> Render just runs your Django app and connects to your company DB.
> **But** — this needs your DB to be accessible from the internet (may need IT help once).

### Option B: Run on Company Server (If already has a public IP)
If your Django server has a public IP:
```bash
# In settings.py
ALLOWED_HOSTS = ['your-server-ip', 'yourdomain.com']

# Run with:
python manage.py runserver 0.0.0.0:8000
# Or with gunicorn for production:
gunicorn main_portal.wsgi:application --bind 0.0.0.0:8000
```

### Option C: Cloudflare Tunnel (Best for company network — No IT needed)
Run this on the office server:
```bash
# Install cloudflared, then:
cloudflared tunnel --url http://localhost:8000
```
Gets you a public HTTPS URL instantly, for FREE, without opening any firewall ports.

---

## ✅ PHASE 3 — React Native Mobile App (Frontend)
> **Time: 1–2 weeks | Done entirely from home**

### Step 3.1 — Setup
```bash
npx create-expo-app@latest JSPLMobileApp
cd JSPLMobileApp
npx expo install axios @react-navigation/native @react-navigation/stack
npx expo install react-native-safe-area-context react-native-screens
npx expo install @react-native-async-storage/async-storage
```

### Step 3.2 — App Structure
```
JSPLMobileApp/
├── app/
│   ├── (auth)/
│   │   └── login.tsx          ← Login screen
│   ├── (tabs)/
│   │   ├── dashboard.tsx      ← Main dashboard
│   │   ├── tpm.tsx            ← TPM module
│   │   ├── checklists.tsx     ← Checklists
│   │   ├── delays.tsx         ← Delays
│   │   ├── capa.tsx           ← CAPA
│   │   ├── safety.tsx         ← Safety
│   │   ├── kpi.tsx            ← HOD KPI
│   │   └── quality.tsx        ← Quality
├── services/
│   └── api.ts                 ← All API calls (axios)
├── store/
│   └── authStore.ts           ← JWT token storage
└── components/
    ├── ModuleCard.tsx
    ├── DataTable.tsx
    └── FormFields.tsx
```

### Step 3.3 — Core API Service (`services/api.ts`)
```typescript
import axios from 'axios';
import AsyncStorage from '@react-native-async-storage/async-storage';

const API_BASE = 'https://jspl-dashboard.onrender.com/api';  // Your deployed URL

const api = axios.create({ baseURL: API_BASE });

// Auto-attach JWT token to every request
api.interceptors.request.use(async (config) => {
  const token = await AsyncStorage.getItem('access_token');
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

export default api;
```

### Step 3.4 — Screens to Build
| Screen | Features |
|---|---|
| **Login** | Email + password, JWT login, remember me |
| **Dashboard** | Cards for each module (TPM, CMC, etc.), notifications bell |
| **TPM** | View checklists, submit, upload photos |
| **Delays** | View/add delay entries by department |
| **CAPA** | List CAPA reports, view details, update status |
| **Safety** | Safety incident list, add new |
| **HOD KPI** | KPI charts, progress bars |
| **Quality** | Quality metrics |
| **Profile** | User info, logout |

---

## ✅ PHASE 4 — Build Downloadable APK (Android)
> **Time: 1 day**

### Method A: Expo EAS Build (Easiest — builds in cloud, no Android Studio needed)
```bash
npm install -g eas-cli
eas login          # Create free Expo account
eas build:configure

# Build APK (shareable file, no Play Store needed)
eas build -p android --profile preview
```
→ Downloads a `.apk` file
→ **Send to anyone via WhatsApp, email, or shared drive**
→ They install it like any normal APK

### Method B: Local Build (If you have Android Studio)
```bash
npx expo run:android --variant release
```
Generates APK in `android/app/build/outputs/apk/release/`

### For iOS (Optional — needs Mac or CI):
```bash
eas build -p ios --profile preview
```
→ Generates `.ipa` file → Can be installed via TestFlight

---

## ✅ PHASE 5 — Distribution
> **Time: 1 hour**

### Internal Distribution (No App Store — Recommended for company use)
| Method | How |
|---|---|
| **WhatsApp/Email** | Send `.apk` file directly |
| **Google Drive link** | Upload APK, share link |
| **Company intranet** | Host on internal server |
| **Firebase App Distribution** | Free, professional, update notifications |

### Firebase App Distribution (Best for team):
1. Go to [Firebase Console](https://console.firebase.google.com)
2. Create project → App Distribution
3. Upload APK → Add tester emails
4. Testers get email with download link
5. When you update, they get notified automatically

---

## 🗓️ Complete Timeline

| Week | What you build |
|---|---|
| **Week 1** | Phase 1: Django REST API (login + dashboard endpoints) |
| **Week 1–2** | Phase 2: Deploy Django to internet (Render/Cloudflare) |
| **Week 2–3** | Phase 3: React Native app — Login + Dashboard screens |
| **Week 3–4** | Phase 3: All module screens (TPM, CAPA, Safety, etc.) |
| **Week 4** | Phase 4: Build APK + Phase 5: Distribute to team |

**Total: ~4 weeks working part-time (evenings/weekends)**

---

## 💻 Tools You Need (All Free)

| Tool | Purpose | Download |
|---|---|---|
| Node.js | Run React Native/Expo | nodejs.org |
| Expo Go app | Test on your phone instantly | Play Store |
| VS Code | Code editor | Already have it |
| Expo account | Build APKs in cloud | expo.dev |
| Render account | Host Django API | render.com |
| Firebase account | Distribute APK | firebase.google.com |

---

## 🚀 Where to Start RIGHT NOW

1. **Today**: Run `pip install djangorestframework djangorestframework-simplejwt django-cors-headers` in your existing project
2. **Today**: Create `api/` Django app, add login endpoint
3. **Test from home**: Deploy to Render → test the API from your phone browser
4. **Once API works**: Start the React Native app with `npx create-expo-app`

---

## ⚠️ Open Questions

> [!IMPORTANT]
> **Q1: Does your production Django server have a public IP or domain?**
> If yes → Option B (run directly on server) is easiest.
> If no → Use Cloudflare Tunnel (no IT needed) or Render.

> [!IMPORTANT]
> **Q2: Do you need iOS support or just Android?**
> Android APK = can be done entirely by yourself, no cost.
> iOS = needs an Apple Developer account ($99/year) or a Mac.

> [!NOTE]
> **Q3: Which modules do you want in the mobile app first?**
> Checklists & CAPA are usually the highest priority for mobile. Confirm the priority order.

> [!NOTE]
> **Q4: Should the mobile app be read-only or also allow data entry?**
> E.g., submitting checklists, adding delay records, updating CAPA status from phone?
