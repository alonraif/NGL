# NGL Database Setup Guide

## Overview

NGL now includes a complete database system with:
- PostgreSQL 15 for data storage
- Redis for task queue and caching
- User authentication with JWT
- Role-based access control (User/Admin)
- Automated file lifecycle management
- Analysis history tracking

## Quick Start

### 1. Start the Services

```bash
cd /Users/alonraif/Code/ngl
docker-compose up -d
```

This will start:
- PostgreSQL (port 5432)
- Redis (port 6379)
- Backend API (port 5000)
- Frontend (port 3000)
- Celery worker (background tasks)
- Celery beat (scheduled tasks)

### 2. Initialize Database and Create Admin

```bash
# Run inside the backend container
docker-compose exec backend alembic upgrade head
docker-compose exec backend python3 init_admin.py
```

This creates the default admin user:
- **Username:** `admin`
- **Password:** `Admin123!`
- **⚠️ Change this password immediately after first login!**

### 3. Access the Application

Open http://localhost:3000 in your browser and log in with the admin credentials.

## API Endpoints

### Authentication

Public self-registration is disabled in production builds. The `/api/auth/register` endpoint returns `403` to enforce administrative onboarding. Create users through the Admin dashboard (`Admin → Users → Create User`) or by calling the admin user-management APIs.

#### Login
```bash
POST /api/auth/login
Content-Type: application/json

{
  "username": "john",
  "password": "SecurePass123!"
}

Response:
{
  "success": true,
  "access_token": "eyJ0eXAiOiJKV1...",
  "user": {
    "id": 1,
    "username": "john",
    "email": "john@example.com",
    "role": "user",
    "storage_quota_mb": 10240,
    "storage_used_mb": 0
  }
}
```

#### Get Current User
```bash
GET /api/auth/me
Authorization: Bearer <token>
```

#### Logout
```bash
POST /api/auth/logout
Authorization: Bearer <token>
```

#### Change Password
```bash
POST /api/auth/change-password
Authorization: Bearer <token>
Content-Type: application/json

{
  "current_password": "OldPass123!",
  "new_password": "NewPass123!"
}
```

### File Upload and Analysis

#### Upload File
```bash
POST /api/upload
Authorization: Bearer <token>
Content-Type: multipart/form-data

file: <log-file.tar.bz2>
parse_mode: known
timezone: US/Eastern
begin_date: (optional)
end_date: (optional)
```

#### Get Analysis History
```bash
GET /api/analyses
Authorization: Bearer <token>
```

#### Get Specific Analysis
```bash
GET /api/analyses/<id>
Authorization: Bearer <token>
```

### Admin Endpoints

All admin endpoints require admin role.

#### List All Users
```bash
GET /api/admin/users
Authorization: Bearer <admin-token>
```

#### Update User
```bash
PUT /api/admin/users/<user_id>
Authorization: Bearer <admin-token>
Content-Type: application/json

{
  "role": "admin",
  "is_active": true,
  "storage_quota_mb": 20480
}
```

#### Delete User
```bash
DELETE /api/admin/users/<user_id>
Authorization: Bearer <admin-token>
```

#### List Parsers
```bash
GET /api/admin/parsers
Authorization: Bearer <admin-token>
```

#### Update Parser Availability
```bash
PUT /api/admin/parsers/<parser_id>
Authorization: Bearer <admin-token>
Content-Type: application/json

{
  "is_enabled": true,
  "is_available_to_users": true,
  "is_admin_only": false
}
```

#### Delete Log File (Admin)
```bash
# Soft delete (recoverable for 90 days)
DELETE /api/admin/files/<file_id>/delete?type=soft
Authorization: Bearer <admin-token>

# Hard delete (permanent)
DELETE /api/admin/files/<file_id>/delete?type=hard
Authorization: Bearer <admin-token>
```

#### Delete Analysis (Admin)
```bash
# Soft delete
DELETE /api/admin/analyses/<analysis_id>/delete?type=soft
Authorization: Bearer <admin-token>

# Hard delete
DELETE /api/admin/analyses/<analysis_id>/delete?type=hard
Authorization: Bearer <admin-token>
```

#### Get System Statistics
```bash
GET /api/admin/stats
Authorization: Bearer <admin-token>
```

## Database Schema

### Key Tables

- **users** - User accounts and authentication
- **parsers** - Parser registry and availability settings
- **parser_permissions** - Granular per-user parser access
- **log_files** - Uploaded log file metadata
- **analyses** - Analysis job records
- **analysis_results** - Parser output storage
- **retention_policies** - Configurable cleanup rules
- **deletion_log** - Audit trail of deletions
- **audit_log** - Complete operation history
- **sessions** - User session management
- **notifications** - In-app notifications
- **alert_rules** - Custom alert configuration

## Lifecycle Management

### Automatic Cleanup

NGL automatically manages file lifecycle:

1. **Files** are kept for **30 days** by default (configurable via `UPLOAD_RETENTION_DAYS`)
2. **Soft delete**: Files older than retention period are marked deleted but kept for **90 days**
3. **Hard delete**: After 90 days, soft-deleted files are permanently removed

### Pinning Files

Files can be pinned to exempt them from automatic deletion:
```sql
UPDATE log_files SET is_pinned = true WHERE id = <file_id>;
```

### Celery Tasks

Background tasks run automatically:

- **cleanup-expired-files** - Runs every hour, soft-deletes expired files
- **hard-delete-old-soft-deletes** - Runs daily, permanently removes old soft-deletes

## Environment Variables

Configure in `docker-compose.yml`:

```yaml
# Database
DATABASE_URL: postgresql://ngl_user:ngl_password@postgres:5432/ngl_db

# Redis
REDIS_URL: redis://redis:6379/0

# JWT
JWT_SECRET_KEY: your-secret-key-change-in-production

# File Management
UPLOAD_RETENTION_DAYS: 30
```

## Password Requirements

Passwords must:
- Be at least 8 characters long
- Contain at least one uppercase letter
- Contain at least one lowercase letter
- Contain at least one number

## Storage Quotas

Default quotas:
- **Regular users**: 10GB (10,240 MB)
- **Admin users**: 100GB (100,000 MB)

Admins can adjust quotas via the `/api/admin/users/<id>` endpoint.

## Troubleshooting

### Database Connection Issues

```bash
# Check PostgreSQL health
docker-compose exec postgres pg_isready -U ngl_user -d ngl_db

# View PostgreSQL logs
docker-compose logs postgres
```

### Check Celery Tasks

```bash
# View celery worker logs
docker-compose logs celery_worker

# View celery beat logs
docker-compose logs celery_beat
```

### Reset Database

```bash
# Stop containers
docker-compose down

# Remove database volume
docker volume rm ngl_postgres_data

# Restart
docker-compose up -d
docker-compose exec backend python3 init_admin.py
```

## Security Notes

1. **Change default admin password** immediately after setup
2. **Change JWT_SECRET_KEY** in production (generate a strong random key)
3. **Use HTTPS** in production
4. **Backup database regularly**
5. **Review audit logs** regularly via the `audit_log` table

## Next Steps

The frontend login/register UI needs to be created to complete the authentication flow. The backend is fully functional and ready to use via API.
