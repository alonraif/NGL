# NGL (Next Gen LULA)

NGL is a web-based LiveU log analyzer with a modern React UI and a Flask backend. It supports multiple parse modes, interactive visualizations, time-range filtering, and admin operations like user management, storage, and SSL configuration.

## Platform Overview

- Purpose: Analyze LiveU log archives with rich visualizations and structured insights.
- Access: Authenticated users only (public registration disabled).
- Admins manage users, invites, storage, SSL, parsers, and audits.

## Technology Stack

- Frontend: React 18, Axios, Recharts
- Backend: Flask 3, SQLAlchemy, Alembic, JWT auth
- Parsing: Modular parser wrappers around `lula2.py`
- Database: PostgreSQL (MySQL option supported in config)
- Background tasks: Celery + Redis
- Deployment: Docker + Docker Compose, Nginx for frontend

## Architecture

- `frontend/`: React UI with analysis pages, admin dashboard, and auth flows.
- `backend/`: Flask API, auth, admin routes, parsers, and background tasks.
- `backend/parsers/`: Modular parser registry; production parsers delegate to `lula2.py`.
- `backend/alembic/`: Schema migrations.
- `docker-compose.yml`: Orchestrates Postgres, Redis, backend, frontend, Celery.

## Core Features

- Interactive charts for modem stats, bandwidth, memory, sessions, grading.
- Session drill-down and time-range pre-filtering for faster parsing.
- Role-based access, audit logging, and admin controls.
- S3 storage integration and HTTPS management (Let’s Encrypt or custom certs).

## Quick Start (Docker)

1) Start services:
```bash
docker compose up -d --build
```

2) Run migrations:
```bash
docker compose exec backend alembic upgrade head
```

3) Create the default admin user:
```bash
docker compose exec backend python3 init_admin.py
```

4) Open the app:
- Frontend: `http://localhost:3000`
- Backend API: `http://localhost:5001` (host mapping in `docker-compose.yml`)

Default admin credentials:
- Username: `admin`
- Password: `Admin123!` (change after first login)

## Configuration

- `backend/config.py` and `backend/config.mysql.py` contain runtime settings.
- Important environment variables:
  - `DATABASE_URL`, `REDIS_URL`, `JWT_SECRET_KEY`
  - `CORS_ORIGINS`, `UPLOAD_RETENTION_DAYS`
  - SMTP placeholders for future email delivery (`SMTP_HOST`, `SMTP_PORT`, etc.)

## Invite-Based Users

- Admins invite users by email only.
- Users set their password via a one-time link (valid for 48 hours) and are auto-logged in.
- Invite reissue regenerates a fresh link and invalidates the previous one.

## Development Notes

- The backend container mounts `./backend` for live reload in development.
- The frontend container mounts `./frontend` and serves via Nginx.

## Useful Commands

```bash
# Logs
Docker compose logs -f backend

# Stop services
Docker compose down
```

## Security Notes

- Public registration is disabled; use invites or admin tools.
- JWT sessions are stored in the DB and audited.
- SSL configuration is handled through the admin dashboard.

