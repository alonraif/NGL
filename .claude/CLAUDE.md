# NGL - Next Generation LiveU Log Analyzer - Project Overview

## What is NGL?

**NGL (Next Gen LULA)** is a modern, full-stack web application for analyzing LiveU device logs. It provides a beautiful, user-friendly interface with powerful visualization capabilities for log file analysis.

## Project Summary

- **Type**: Full-stack web application
- **Purpose**: LiveU device log analysis with interactive visualizations
- **Stack**: React 18 (frontend) + Flask (backend) + PostgreSQL + Redis
- **Deployment**: Docker Compose
- **Current Version**: 4.0.0 (with database & authentication)
- **Parser Version**: 3.0.0 (modular hybrid architecture)

## Core Architecture

### Technology Stack

**Frontend:**
- React 18 with React Router
- Recharts for data visualization
- Axios for API communication
- React Context for state management (Auth)
- Nginx for production serving

**Backend:**
- Flask REST API with CORS
- PostgreSQL 15 (database)
- Redis 7 (task queue & caching)
- Celery (background workers & scheduled tasks)
- JWT authentication with bcrypt
- SQLAlchemy ORM

**Infrastructure:**
- Docker Compose orchestration
- 6 services: frontend, backend, postgres, redis, celery_worker, celery_beat
- Persistent volumes for data
- Health checks on all services

### Key Features

#### 1. Authentication & User Management
- **JWT-based authentication** with secure token storage
- **Role-based access control**: User vs Admin roles
- **Auto-logout** after 10 minutes of inactivity
- **Password requirements**: 8+ chars, uppercase, lowercase, number
- **Storage quotas**: 10GB per user, 100GB for admins
- **Session tracking** with audit logging

#### 2. Log Analysis (19+ Parse Modes)
- **Error Analysis**: known, error, v (verbose), all
- **Bandwidth Analysis**: bw (stream), md-bw (modem), md-db-bw (data bridge)
- **Modem Statistics**: md (signal, throughput, packet loss)
- **Sessions**: Streaming session tracking with duration calculation
- **System Metrics**: memory usage, CPU, modem grading
- **Device Info**: Device/server IDs

#### 3. Interactive Visualizations
- **Modem Stats**: Bar charts, line graphs, tables
- **Bandwidth Charts**: Time-series area/line charts with per-modem analysis
- **Sessions Table**: Filterable, chronologically sorted with complete/incomplete detection
- **Memory Usage**: Component-based time-series (VIC/Corecard/Server)
- **Modem Grading**: Service level timeline, quality metrics
- **Real-time Updates**: Live progress tracking during parsing

#### 4. Database System
**12 Tables:**
- `users` - User accounts with authentication
- `parsers` - Parser registry with availability controls
- `parser_permissions` - Granular per-user parser access
- `log_files` - File metadata with lifecycle tracking
- `analyses` - Analysis job records with status
- `analysis_results` - Parser output storage
- `retention_policies` - Configurable cleanup rules
- `deletion_log` - Complete deletion audit trail
- `audit_log` - All user actions logged
- `sessions` - JWT session management
- `notifications` - In-app notification system
- `alert_rules` - Custom user alerts

#### 5. File Lifecycle Management
- **Automated retention**: 30 days default (configurable)
- **Soft delete**: 90-day grace period for recovery
- **Hard delete**: Permanent removal after grace period
- **File pinning**: Exempt important files from auto-deletion
- **SHA256 hashing**: File deduplication
- **Quota enforcement**: Storage limits per user

#### 6. Admin Dashboard
- **Statistics Tab**: Users, files, analyses, storage overview
- **Users Tab**: Manage users, roles, quotas, activation
- **Parsers Tab**: Control parser visibility and availability
- **System Controls**: Soft/hard delete, user management

#### 7. Analysis History
- **Per-user history**: View all past analyses
- **Status tracking**: Pending, running, completed, failed
- **Session naming**: User-friendly identification
- **Zendesk integration**: Optional case number tracking
- **Result retrieval**: View any past analysis result
- **Processing metrics**: Duration, timestamps

## Parser Architecture (Modular Hybrid)

### Design Philosophy
NGL uses a **hybrid modular architecture** that combines:
- **Modular structure**: Each parse mode is a separate class
- **Proven parsing**: Delegates to lula2.py (battle-tested, 3,015 lines)
- **Wrapper pattern**: Parsers wrap lula2.py output into structured JSON

### Parser Implementations
All parsers inherit from `LulaWrapperParser`:
- `BandwidthParser` - bw, md-bw, md-db-bw modes
- `ModemStatsParser` - md mode
- `SessionsParser` - sessions mode
- `ErrorParser` - known, error, v, all modes
- `SystemParser` - memory, grading modes
- `DeviceIDParser` - id mode

### Benefits
- **Quick development**: Add new parser in 15-30 minutes
- **Reliable parsing**: Uses lula2.py's proven logic
- **Easy testing**: Unit test each parser wrapper
- **Clear organization**: One parser class per mode
- **6x smaller code**: ~50-100 lines per parser vs ~250 lines in monolithic

## API Endpoints

### Authentication (`/api/auth/`)
- `POST /register` - Create new user account (admin-only in production)
- `POST /login` - Authenticate and get JWT token
- `GET /me` - Get current user info
- `POST /logout` - Invalidate session
- `POST /change-password` - Update password

### File Upload & Analysis (`/api/`)
- `POST /upload` - Upload log file with auth (saves to DB)
- `GET /analyses` - Get user's analysis history
- `GET /analyses/<id>` - Get specific analysis with results
- `GET /parse-modes` - Get available parsers (filtered by permissions)

### Admin Only (`/api/admin/`)
- `GET /users` - List all users
- `PUT /users/<id>` - Update user (role, quota, status)
- `DELETE /users/<id>` - Delete user
- `GET /parsers` - List all parsers
- `PUT /parsers/<id>` - Control parser availability
- `DELETE /files/<id>/delete?type=soft|hard` - Delete log files
- `DELETE /analyses/<id>/delete?type=soft|hard` - Delete analyses
- `GET /stats` - System statistics

### Health Check
- `GET /api/health` - Database connection, version, features

## Project Structure

```
ngl/
├── docker-compose.yml          # Docker orchestration (6 services)
├── .env.example                # Environment template
├── lula2.py                    # Original parser (3,015 lines)
│
├── backend/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── app.py                  # Main Flask application
│   ├── config.py               # Configuration management
│   ├── database.py             # DB connection & session
│   ├── models.py               # SQLAlchemy models (12 tables)
│   ├── auth.py                 # JWT utilities & decorators
│   ├── auth_routes.py          # Authentication endpoints
│   ├── admin_routes.py         # Admin management endpoints
│   ├── celery_app.py           # Celery configuration
│   ├── tasks.py                # Background cleanup tasks
│   ├── init_admin.py           # Create default admin user
│   ├── lula2.py                # Copy of parser
│   ├── parsers/
│   │   ├── __init__.py         # Parser registry & factory
│   │   ├── base.py             # BaseParser abstract class
│   │   ├── lula_wrapper.py     # LulaWrapperParser (all parsers)
│   │   └── [legacy files]      # Native implementations (reference)
│   └── alembic/                # Database migrations
│
└── frontend/
    ├── Dockerfile
    ├── nginx.conf
    ├── package.json
    ├── public/
    └── src/
        ├── App.js              # Routes & auth guards
        ├── App.css
        ├── index.js
        ├── context/
        │   ├── AuthContext.js  # Auth state management
        │   └── ParsingContext.js # Parsing state
        ├── pages/
        │   ├── Login.js        # Login page
        │   ├── Register.js     # Registration (disabled in prod)
        │   ├── UploadPage.js   # Main upload interface
        │   ├── AnalysisHistory.js # History view
        │   └── AdminDashboard.js  # Admin interface
        └── components/
            ├── FileUpload.js
            ├── Results.js
            ├── ParserProgress.js
            ├── ModemStats.js
            ├── BandwidthChart.js
            ├── ModemBandwidthChart.js
            ├── SessionsTable.js
            ├── MemoryChart.js
            ├── ModemGradingChart.js
            └── RawOutput.js
```

## Important Implementation Details

### Authentication Flow
1. User logs in → JWT token generated
2. Token stored in localStorage and axios headers
3. All API requests include `Authorization: Bearer <token>`
4. Auto-logout after 10 minutes of inactivity
5. Activity tracked: mouse, keyboard, scroll, touch events

### File Upload Flow
1. User selects file + parse mode(s) + timezone + date range
2. File uploaded to `/api/upload` with JWT token
3. Backend saves file metadata to `log_files` table
4. Creates analysis record in `analyses` table
5. Calls lula2.py with archive file directly (no extraction)
6. Parses lula2.py output into structured JSON
7. Saves results to `analysis_results` table
8. Returns results to frontend for visualization

### Parser Execution Flow
1. Archive file passed directly to lula2.py (no extraction)
2. lula2.py handles: extraction, filtering, date ranges, timezone
3. lula2.py outputs text/CSV to stdout
4. Wrapper parser captures output
5. Parser's `parse_output()` converts text to structured JSON
6. JSON returned to API → database → frontend

### Lifecycle Management
- **Celery Beat** schedules tasks
- **Hourly**: `cleanup_expired_files` - soft-deletes files older than retention period
- **Daily**: `hard_delete_old_soft_deletes` - permanently removes files after 90 days
- **Pinned files**: Exempt from auto-deletion
- **Admin override**: Can manually soft/hard delete anytime

## Default Credentials

**Admin User** (created by `init_admin.py`):
- Username: `admin`
- Password: `Admin123!`
- **⚠️ Change immediately in production!**

## Environment Variables

Key configuration in `docker-compose.yml`:
- `DATABASE_URL`: PostgreSQL connection string
- `REDIS_URL`: Redis connection string
- `JWT_SECRET_KEY`: Secret for JWT signing (change in production!)
- `UPLOAD_RETENTION_DAYS`: File retention period (default: 30)

## Recent Major Changes

### Version 4.0.0 (October 2025)
- Added complete database system (PostgreSQL)
- Implemented JWT authentication
- Added user management & admin dashboard
- Implemented file lifecycle management
- Added Celery for background tasks
- Created login/register UI
- Added analysis history tracking
- Implemented session naming & Zendesk integration

### Version 3.0.0 (October 2025)
- Refactored to modular parser architecture
- All parsers use LulaWrapperParser pattern
- Delegates parsing to lula2.py (proven logic)
- ~50-100 lines per parser (vs 250+ monolithic)

### Key Git Commits
- `19791ef` - Fix login page design to match platform styling
- `44775d3` - Redesign login page to match platform UI with LiveU branding
- `de512fb` - Add automatic logout after 10 minutes of inactivity
- `20a3594` - Implement admin-only user management and disable public registration
- `7dabe8a` - Add persistent parsing progress across page navigation and refresh

## Common Development Tasks

### Start the Application
```bash
cd /Users/alonraif/Code/ngl
docker-compose up --build -d
docker-compose exec backend python3 init_admin.py
open http://localhost:3000
```

### View Logs
```bash
docker-compose logs -f                    # All services
docker-compose logs backend               # Backend only
docker-compose logs frontend              # Frontend only
docker-compose logs celery_worker         # Background tasks
```

### Database Operations
```bash
# Access PostgreSQL
docker-compose exec postgres psql -U ngl_user -d ngl_db

# Check database tables
docker-compose exec postgres psql -U ngl_user -d ngl_db -c '\dt'

# Reset database (⚠️ deletes all data!)
docker-compose down
docker volume rm ngl_postgres_data
docker-compose up -d
docker-compose exec backend python3 init_admin.py
```

### Adding a New Parser
1. Add parser class to `backend/parsers/lula_wrapper.py`
2. Register in `backend/parsers/__init__.py`
3. Add to `PARSE_MODES` in `backend/app.py`
4. Test with `docker-compose exec backend python3 test_parsers.py`

## Security Features

- **Password hashing**: bcrypt with salt
- **JWT tokens**: Signed with secret key
- **Session tracking**: All sessions logged
- **Audit logging**: All user actions tracked
- **Input validation**: Username, email, password requirements
- **Storage quotas**: Prevent disk space abuse
- **Inactivity timeout**: Auto-logout after 10 minutes
- **CORS**: Configured for frontend domain

## Known Limitations

- **Session metadata extraction**: Currently disabled for performance (large compressed archives)
- **Public registration**: Disabled in production (admin-only user creation)
- **Max file size**: 500MB
- **Retention period**: Hard-coded to 30 days (configurable via env var)

## Documentation Files

Key documentation to reference:
- `README.md` - Complete feature overview
- `DATABASE_SETUP.md` - Database & API documentation
- `GETTING_STARTED.md` - Setup & testing guide
- `IMPLEMENTATION_SUMMARY.md` - Database implementation details
- `MODULAR_ARCHITECTURE.md` - Parser architecture
- `PARSER_DEVELOPMENT.md` - Quick reference for adding parsers
- `CHANGELOG.md` - Version history
- `TROUBLESHOOTING.md` - Common issues

## Future Enhancements (Potential)

- Email notifications (SMTP)
- Password reset flow
- 2FA authentication
- WebSocket for real-time updates
- S3 storage for files
- Multi-tenancy / organizations
- Advanced analytics & trends
- Mobile app (React Native)
- Parser chaining
- Custom regex patterns via API

## Support & Debugging

**Common Issues:**
1. **Database connection failed** → Check PostgreSQL health: `docker-compose logs postgres`
2. **Login not working** → Check JWT_SECRET_KEY is set: `docker-compose logs backend`
3. **Upload fails** → Check storage quota: Admin → Users tab
4. **Parser not visible** → Check parser permissions: Admin → Parsers tab

**Logs to check:**
- Backend errors: `docker-compose logs backend`
- Frontend errors: Browser console (F12)
- Database: `docker-compose logs postgres`
- Background tasks: `docker-compose logs celery_worker`

## Claude Code Context

When helping with NGL development:

1. **Authentication**: All API endpoints (except login/register) require JWT token in `Authorization: Bearer <token>` header
2. **Parsers**: Use LulaWrapperParser pattern, delegate to lula2.py, parse its output
3. **Database**: Use SQLAlchemy models, always use `SessionLocal()` for DB access
4. **Frontend**: React Router, AuthContext for auth, protected routes, admin guards
5. **File handling**: Pass archives directly to lula2.py (no extraction in wrapper)
6. **Testing**: Always test with real log files after changes
7. **Security**: Never commit JWT_SECRET_KEY, change admin password in production

## Quick Reference

**Ports:**
- Frontend: 3000
- Backend: 5000
- PostgreSQL: 5432
- Redis: 6379

**Default Admin:**
- Username: admin
- Password: Admin123!

**Key Commands:**
- Start: `docker-compose up -d`
- Stop: `docker-compose down`
- Rebuild: `docker-compose up --build`
- Logs: `docker-compose logs -f`
- Init DB: `docker-compose exec backend python3 init_admin.py`

---

**Last Updated**: October 2025
**Current Version**: 4.0.0
**Status**: Production-ready with database & authentication
