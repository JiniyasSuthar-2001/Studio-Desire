# STUDIO DESIRE — ARCHITECTURAL & INTERIOR DESIGN PLATFORM

A minimal, editorial portfolio experience and executive studio management platform for **Studio Desire**, showcasing architectural spaces, material integrity, spatial daylight, and client project management.

---

## Architecture Overview

The system is built with a clean separation of concerns:

```
[ FRONTEND (React 18 + TypeScript + Vite) ]
                    ↓  REST API (JSON)
[ BACKEND (Python 3.10–3.14 + FastAPI + Uvicorn) ]
                    ↓  SQLAlchemy 2.0 ORM
[ DATABASE (SQLite / Production PostgreSQL ready) ]
```

---

## 1. Quick Start (Centralized Startup)

Start **both** the Python/FastAPI backend and React/Vite frontend in a single terminal from the project root:

```bash
python start_up.py
```

### Access URLs:
- **Frontend App**: `http://localhost:5173`
- **FastAPI REST API**: `http://localhost:8000/api`
- **Interactive Swagger Docs**: `http://localhost:8000/docs`
- **Health Check**: `http://localhost:8000/api/health`

---

## 2. Environment Configuration

Copy `.env.example` to `.env` in the root or `backend/` directory:

```bash
cp .env.example .env
```

### Key Environment Variables:
- `ENVIRONMENT`: `development` or `production`
- `SECRET_KEY`: Cryptographically random 32+ character key (required in production)
- `CORS_ORIGINS`: Comma-separated list of allowed origins (e.g., `http://localhost:5173,https://studiodesire.com`)
- `SEED_DEMO_DATA`: `true` or `false` (default: `false`)
- `ACCESS_TOKEN_EXPIRE_MINUTES`: JWT token lifetime in minutes (default: `1440` = 24h)
- `INITIAL_ADMIN_PASSWORD`: Secure password for initial admin bootstrapping on fresh database

---

## 3. Manual Startup

### Backend
```bash
cd backend
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### Frontend
```bash
cd frontend
npm run dev
```

---

## 4. Database Backup & Disaster Recovery

Perform safe, consistent online backups of the SQLite database:

```bash
python backend/scripts/backup_db.py
```

To restore from a backup:
```bash
python backend/scripts/backup_db.py --restore backend/backups/studio_desire_backup_YYYYMMDD_HHMMSS.db
```

---

## 5. Automated Test Suites

Run the security regression suite:
```bash
python -m pytest backend/tests/test_security_fixes.py -v
```

Run the end-to-end business integration suite:
```bash
python backend/test_studio_desire_e2e.py
```

Run the enquiry lifecycle verification test:
```bash
python backend/verify_enquiry_e2e.py
```

Run frontend build & TypeScript verification:
```bash
cd frontend
npm run build
```
