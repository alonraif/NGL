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
- 7 services: frontend, backend, postgres, redis, celery_worker, celery_beat, certbot
- Persistent volumes for data (uploads, temp, postgres_data, redis_data, certbot_www, certbot_certs, nginx_runtime, nginx_ssl)
- Health checks on all services
- Docker socket integration for service monitoring

### Key Features

#### 1. Authentication & User Management
- **JWT-based authentication** with secure token storage
- **Role-based access control**: User vs Admin roles
- **Auto-logout** after 10 minutes of inactivity
- **Password requirements**: 12+ chars, uppercase, lowercase, number, special character
- **Password change**: User-initiated password updates
- **Admin password reset**: Admins can reset user passwords
- **Storage quotas**: 10GB per user, 100GB for admins (configurable)
- **Session tracking** with audit logging
- **Last login tracking**: Display last login time for users
- **Geolocation tracking**: IP-based location tracking in audit logs

#### 2. Log Analysis (19+ Parse Modes)
- **Error Analysis**: known, error, v (verbose), all
- **Bandwidth Analysis**: bw (stream), md-bw (modem), md-db-bw (data bridge)
- **Modem Statistics**: md (signal, throughput, packet loss)
- **Sessions**: Streaming session tracking with duration calculation
- **System Metrics**: memory usage, CPU, modem grading
- **Device Info**: Device/server IDs
- **Archive Pre-filtering**: Automatic time-range filtering before parsing for massive performance gains
  - Reduces archive size by filtering files by modification time
  - Configurable buffer hours before/after time range
  - Supports tar.bz2, tar.gz, and zip formats
  - Only filters when >20% reduction is achievable
  - Automatic fallback to original archive if filtering fails

#### 3. Interactive Visualizations
- **Modem Stats**: Bar charts, line graphs, tables
- **Bandwidth Charts**: Time-series area/line charts with per-modem analysis
- **Sessions Table**: Filterable, chronologically sorted with complete/incomplete detection
- **Memory Usage**: Component-based time-series (VIC/Corecard/Server)
- **Modem Grading**: Service level timeline, quality metrics
- **Real-time Updates**: Live progress tracking during parsing

#### 4. Database System
**15 Tables:**
- `users` - User accounts with authentication & quotas
- `parsers` - Parser registry with availability controls
- `parser_permissions` - Granular per-user parser access
- `log_files` - File metadata with lifecycle tracking (local/S3)
- `analyses` - Analysis job records with status & drill-down tracking
- `analysis_results` - Parser output storage (JSON + raw)
- `retention_policies` - Configurable cleanup rules
- `deletion_log` - Complete deletion audit trail with recovery tracking
- `audit_log` - All user actions logged with geolocation
- `sessions` - JWT session management with activity tracking
- `notifications` - In-app notification system
- `alert_rules` - Custom user alerts with conditions
- `bookmarks` - User bookmarks for analyses
- `s3_configurations` - S3 storage configuration (singleton)
- `ssl_configurations` - SSL/HTTPS configuration (singleton)

#### 5. File Lifecycle Management
- **Automated retention**: 30 days default (configurable)
- **Soft delete**: 90-day grace period for recovery
- **Hard delete**: Permanent removal after grace period
- **File pinning**: Exempt important files from auto-deletion
- **SHA256 hashing**: File deduplication
- **Quota enforcement**: Storage limits per user
- **Dual storage**: Local filesystem or S3 (configurable per file)
- **S3 integration**: AWS S3 support with server-side encryption
- **Storage migration**: Files can be moved between local and S3

#### 6. Admin Dashboard
- **Statistics Tab**: Users, files, analyses, storage overview (local + S3)
- **Users Tab**: Manage users, roles, quotas, activation, password reset
- **Parsers Tab**: Control parser visibility and availability
- **System Controls**: Soft/hard delete, bulk operations
- **S3 Configuration**: Configure, test, enable/disable S3 storage
- **SSL Management**: Configure HTTPS with Let's Encrypt or upload certificates
- **Audit Logs**: View, filter, and export all user actions
- **Audit Statistics**: Analyze user activity patterns
- **Docker Logs**: View logs from all Docker services in real-time
- **Service Status**: Monitor health of all Docker containers

#### 7. Analysis History & Management
- **Per-user history**: View all past analyses
- **Shared history**: View all analyses across all users (admin/filtered access)
- **Advanced filtering**: Multi-field search (session name, Zendesk case, parse mode, user)
- **Status tracking**: Pending, running, completed, failed
- **Session naming**: User-friendly identification
- **Zendesk integration**: Optional case number tracking
- **Result retrieval**: View any past analysis result
- **Processing metrics**: Duration, timestamps
- **Bookmarks**: Save important analyses for quick access
- **Drill-down tracking**: Parent-child relationships for detailed analysis
- **Analysis download**: Export analysis results
- **Analysis cancellation**: Cancel running analyses
- **Bulk deletion**: Delete multiple analyses at once (admin)

#### 8. SSL/HTTPS Management
- **Let's Encrypt integration**: Automatic SSL certificate issuance via Certbot
- **Certificate upload**: Upload custom SSL certificates (cert, key, chain)
- **HTTPS enforcement**: Optional redirect from HTTP to HTTPS
- **Multi-domain support**: Primary domain + alternate domains
- **Auto-renewal**: Automatic certificate renewal before expiration
- **Health checks**: Verify HTTPS endpoint functionality
- **Certificate metadata**: View expiry dates, fingerprints, domains
- **Dynamic Nginx config**: Automatic Nginx configuration updates

#### 9. Rate Limiting & Security
- **Configurable rate limiting**: Protect endpoints from abuse
- **IP-based throttling**: Per-IP request limits
- **Geolocation tracking**: Track user locations via IP address
- **Audit trail**: Complete history of all actions with context
- **Session management**: Active session tracking and termination

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
- `POST /upload` - Upload log file with auth (saves to DB, applies pre-filtering)
- `GET /download-progress` - Get file upload progress
- `POST /cancel` - Cancel running analysis
- `GET /parse-modes` - Get available parsers (filtered by permissions)

### Analysis History (`/api/`)
- `GET /analyses` - Get user's analysis history
- `GET /analyses/all` - Get shared analysis history (with filtering)
- `GET /analyses/<id>` - Get specific analysis with results
- `GET /analyses/search` - Search analyses with advanced filters
- `POST /analyses/from-session` - Create new analysis from existing session
- `GET /analyses/<id>/download` - Download analysis results

### Bookmarks (`/api/`)
- `GET /bookmarks` - Get user's bookmarked analyses
- `POST /bookmarks/<id>` - Bookmark an analysis
- `DELETE /bookmarks/<id>` - Remove bookmark

### Admin - User Management (`/api/admin/`)
- `GET /users` - List all users
- `POST /users` - Create new user
- `PUT /users/<id>` - Update user (role, quota, status)
- `POST /users/<id>/reset-password` - Reset user password
- `DELETE /users/<id>` - Delete user

### Admin - Parser Management (`/api/admin/`)
- `GET /parsers` - List all parsers
- `PUT /parsers/<id>` - Control parser availability

### Admin - File & Analysis Management (`/api/admin/`)
- `GET /analyses` - List all analyses with filters
- `POST /analyses/bulk-delete` - Bulk delete analyses
- `DELETE /files/<id>/delete?type=soft|hard` - Delete log files
- `DELETE /analyses/<id>/delete?type=soft|hard` - Delete analyses

### Admin - S3 Configuration (`/api/admin/`)
- `GET /s3/config` - Get S3 configuration
- `PUT /s3/config` - Update S3 configuration
- `POST /s3/test` - Test S3 connection
- `POST /s3/enable` - Enable S3 storage
- `POST /s3/disable` - Disable S3 storage
- `GET /s3/stats` - Get S3 storage statistics

### Admin - SSL Management (`/api/admin/`)
- `GET /ssl` - Get SSL configuration
- `POST /ssl/settings` - Update SSL settings
- `POST /ssl/upload` - Upload SSL certificates
- `POST /ssl/issue` - Issue Let's Encrypt certificate
- `POST /ssl/renew` - Renew SSL certificate
- `POST /ssl/enforce` - Enable/disable HTTPS enforcement
- `POST /ssl/health-check` - Verify HTTPS endpoint

### Admin - Audit & Monitoring (`/api/admin/`)
- `GET /audit-logs` - Get audit logs with filtering
- `GET /audit-stats` - Get audit statistics
- `GET /audit-export` - Export audit logs
- `GET /docker-logs` - Get Docker service logs
- `GET /docker-services` - Get Docker service status
- `GET /stats` - System statistics

### Health Check
- `GET /api/health` - Database connection, version, features

## Project Structure

```
ngl/
├── docker-compose.yml          # Docker orchestration (7 services)
├── .env.example                # Environment template
├── lula2.py                    # Original parser (3,015 lines)
│
├── backend/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── app.py                  # Main Flask application
│   ├── config.py               # Configuration management
│   ├── database.py             # DB connection & session
│   ├── models.py               # SQLAlchemy models (15 tables)
│   ├── auth.py                 # JWT utilities & decorators
│   ├── auth_routes.py          # Authentication endpoints
│   ├── admin_routes.py         # Admin management endpoints (2000+ lines)
│   ├── celery_app.py           # Celery configuration
│   ├── tasks.py                # Background cleanup tasks & SSL renewal
│   ├── init_admin.py           # Create default admin user
│   ├── lula2.py                # Copy of parser
│   ├── archive_filter.py       # Archive pre-filtering utility
│   ├── rate_limiter.py         # Rate limiting configuration
│   ├── geo_service.py          # IP geolocation service
│   ├── ssl_service.py          # SSL certificate management
│   ├── docker_service.py       # Docker logs & monitoring
│   ├── storage_service.py      # Storage abstraction (local/S3)
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
        │   ├── AnalysisHistory.js # History view (personal)
        │   ├── SharedHistory.js   # Shared history (all users)
        │   └── AdminDashboard.js  # Admin interface (multi-tab)
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
3. Backend saves file to local storage or S3 (based on configuration)
4. SHA256 hash computed for deduplication
5. File metadata saved to `log_files` table
6. Creates analysis record in `analyses` table
7. **Archive pre-filtering**: If date range specified, filter archive files by modification time
8. Calls lula2.py with filtered archive (or original if no filtering)
9. Parses lula2.py output into structured JSON
10. Saves results to `analysis_results` table
11. Returns results to frontend for visualization
12. Audit log entry created with geolocation

### Parser Execution Flow
1. Archive file retrieved from storage (local or S3)
2. **Pre-filtering applied** (if date range provided):
   - Extract file list with modification times
   - Filter files within time range + buffer
   - Create new temporary archive with filtered files
   - Only if >20% reduction, otherwise use original
3. Filtered/original archive passed to lula2.py (no extraction in wrapper)
4. lula2.py handles: extraction, filtering, date ranges, timezone
5. lula2.py outputs text/CSV to stdout
6. Wrapper parser captures output
7. Parser's `parse_output()` converts text to structured JSON
8. JSON returned to API → database → frontend
9. Temporary filtered archives cleaned up

### Lifecycle Management
- **Celery Beat** schedules tasks
- **Hourly**: `cleanup_expired_files` - soft-deletes files older than retention period
- **Daily**: `hard_delete_old_soft_deletes` - permanently removes files after 90 days
- **Daily**: `renew_ssl_certificates` - checks and renews SSL certificates before expiry
- **Pinned files**: Exempt from auto-deletion
- **Admin override**: Can manually soft/hard delete anytime
- **Bulk operations**: Admins can bulk delete analyses with filters

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
- `CORS_ORIGINS`: Allowed CORS origins (default: http://localhost:3000)
- `CERTBOT_WEBROOT`: Path for Let's Encrypt challenges
- `LE_LIVE_BASE`: Let's Encrypt certificates base path
- `NGINX_RUNTIME_DIR`: Nginx runtime configuration directory
- `UPLOAD_CERT_DIR`: Directory for uploaded SSL certificates
- `FORCE_DISABLE_HTTPS_ENFORCEMENT`: Override HTTPS enforcement (default: false)

## Recent Major Changes

### Version 4.5.0 (October 2025) - Current
- **Archive Pre-filtering**: Massive performance gains by filtering archives before parsing
- **SSL/HTTPS Management**: Full Let's Encrypt integration + custom certificate upload
- **S3 Storage**: AWS S3 integration for file storage with dual-mode support
- **Geolocation Service**: IP-based user location tracking in audit logs
- **Docker Integration**: View service logs and status from admin dashboard
- **Rate Limiting**: Configurable per-endpoint rate limiting
- **Shared History**: Cross-user analysis browsing with advanced filters
- **Bookmarks**: Save and organize important analyses
- **Drill-down Analysis**: Parent-child relationships for detailed investigations
- **Bulk Operations**: Mass delete analyses with filters
- **Password Security**: Enhanced to 12+ chars with special character requirement
- **Consistent UI**: Unified header layout across all pages
- **Audit Export**: Export audit logs for compliance

### Version 4.0.0 (October 2025)
- Added complete database system (PostgreSQL with 15 tables)
- Implemented JWT authentication with session tracking
- Added user management & admin dashboard
- Implemented file lifecycle management with soft/hard delete
- Added Celery for background tasks (3 scheduled tasks)
- Created login/register UI
- Added analysis history tracking with Zendesk integration
- Implemented session naming for easy identification

### Version 3.0.0 (October 2025)
- Refactored to modular parser architecture
- All parsers use LulaWrapperParser pattern
- Delegates parsing to lula2.py (proven logic)
- ~50-100 lines per parser (vs 250+ monolithic)

### Key Recent Commits
- `53b9eea` - Fix: automatically update Nginx configuration when SSL certificates are issued or renewed
- `bc65826` - Handle non-UTF8 archives and prevent upload timeout
- `f9d5d9b` - Docs: add comprehensive release notes for archive pre-filtering feature
- `7bcab8f` - Feat: implement automatic archive pre-filtering for massive performance gains
- `939dc51` - Make rate limiting configurable
- `ef20319` - Feat: implement shared analysis history with advanced multi-field filtering
- `ede36af` - Feat: implement consistent header layout across all pages
- `867ddd0` - Feat: add user-initiated password change and enforce 12-char minimum
- `4b122de` - Improve inactivity handling and expose last login info
- `1a38a57` - Make Alembic migrations idempotent

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
- **JWT tokens**: Signed with secret key, session tracking
- **Strong passwords**: 12+ chars with uppercase, lowercase, number, special character
- **Session management**: All sessions logged with IP and user agent
- **Audit logging**: Complete action history with geolocation
- **Input validation**: Username, email, password, domain validation
- **Storage quotas**: Prevent disk space abuse (configurable per user)
- **Inactivity timeout**: Auto-logout after 10 minutes
- **CORS**: Configured for frontend domain
- **Rate limiting**: Configurable per-endpoint throttling
- **HTTPS support**: Let's Encrypt or custom certificates
- **Certificate validation**: Verify certificate-key pairs before deployment
- **Geolocation tracking**: IP-based location for security monitoring

## Known Limitations

- **Public registration**: Disabled in production (admin-only user creation)
- **Max file size**: 500MB upload limit
- **Archive pre-filtering**: Only >20% reduction triggers filtering (optimization)
- **S3 migration**: Files not automatically migrated between local/S3 on config change
- **SSL renewal**: Requires certbot service running for Let's Encrypt
- **Geolocation**: Limited accuracy, depends on IP database

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

- Email notifications (SMTP) - infrastructure ready via notification system
- Password reset flow via email
- 2FA authentication
- WebSocket for real-time updates (polling currently used)
- ~~S3 storage for files~~ ✅ **IMPLEMENTED**
- Multi-tenancy / organizations
- Advanced analytics & trends
- Mobile app (React Native)
- Parser chaining
- Custom regex patterns via API
- Auto-migration between local/S3 storage
- Azure Blob Storage support
- Analysis comparison view
- Scheduled analyses
- Alert webhooks (Slack, Teams, Discord)

## Support & Debugging

**Common Issues:**
1. **Database connection failed** → Check PostgreSQL health: `docker-compose logs postgres`
2. **Login not working** → Check JWT_SECRET_KEY is set: `docker-compose logs backend`
3. **Upload fails** → Check storage quota: Admin → Users tab, or check S3 config if enabled
4. **Parser not visible** → Check parser permissions: Admin → Parsers tab
5. **HTTPS not working** → Check SSL config, verify certificate paths, check Nginx logs
6. **Slow parsing** → Archive pre-filtering should help; check date range is provided
7. **S3 errors** → Verify credentials, bucket permissions, region settings
8. **Rate limiting errors** → Check rate_limiter.py configuration

**Logs to check:**
- Backend errors: `docker-compose logs backend` or Admin → Docker Logs
- Frontend errors: Browser console (F12)
- Database: `docker-compose logs postgres`
- Background tasks: `docker-compose logs celery_worker`
- SSL/Certbot: `docker-compose logs certbot`
- Nginx: Check frontend logs or Admin → Docker Logs
- All services: Admin Dashboard → Docker Logs tab (real-time)

## Claude Code Context

When helping with NGL development:

1. **Authentication**: All API endpoints (except login/register) require JWT token in `Authorization: Bearer <token>` header
2. **Parsers**: Use LulaWrapperParser pattern, delegate to lula2.py, parse its output
3. **Database**: Use SQLAlchemy models (15 tables), always use `SessionLocal()` for DB access
4. **Frontend**: React Router, AuthContext for auth, protected routes, admin guards
5. **File handling**:
   - Archives may be stored locally or in S3 (check `storage_type` in LogFile model)
   - Apply archive pre-filtering before passing to lula2.py for time-range queries
   - Pass filtered/original archives directly to lula2.py (no extraction in wrapper)
6. **Archive pre-filtering**: Use `ArchiveFilter` class from `archive_filter.py` for time-range optimization
7. **Storage**: Use `StorageFactory` from `storage_service.py` for local/S3 abstraction
8. **Geolocation**: Use `geo_service.py` for IP-based location tracking in audit logs
9. **SSL Management**: Use `ssl_service.py` for certificate operations, always validate before deployment
10. **Docker Integration**: Use `docker_service.py` for accessing container logs and status
11. **Rate Limiting**: Configure in `rate_limiter.py`, applied via decorators
12. **Testing**: Always test with real log files after changes
13. **Security**:
    - Never commit JWT_SECRET_KEY, AWS credentials, or SSL private keys
    - Change admin password in production
    - Use 12+ char passwords with special characters
    - Validate all user inputs (domains, emails, passwords)
14. **Background Tasks**: Use Celery for long-running operations (cleanup, SSL renewal)
15. **Audit Trail**: Log all significant actions with `log_audit()` from `auth.py`

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

**Last Updated**: October 31, 2025
**Current Version**: 4.5.0
**Status**: Production-ready with full enterprise features

## Key Metrics

- **Database Tables**: 15
- **Docker Services**: 7
- **API Endpoints**: 60+
- **Parse Modes**: 19+
- **Backend Services**: 9 (app, auth, admin, geo, ssl, docker, storage, rate limiter, archive filter)
- **Background Tasks**: 3 (cleanup, hard delete, SSL renewal)
- **Frontend Pages**: 6 (Login, Upload, History, Shared History, Admin, Register)
- **Lines of Code**: ~2,000+ (admin_routes), ~1,800+ (app), ~450 (archive_filter), ~170 (lula2 wrapper)

## Technology Summary

**Languages**: Python 3, JavaScript (React 18)
**Frameworks**: Flask, React, SQLAlchemy, Celery
**Databases**: PostgreSQL 15, Redis 7
**Storage**: Local filesystem, AWS S3
**Security**: JWT, bcrypt, Let's Encrypt, SSL/TLS
**Infrastructure**: Docker Compose, Nginx, Certbot
**Monitoring**: Audit logs, geolocation, Docker logs integration
**Performance**: Archive pre-filtering (20%+ reduction threshold)
