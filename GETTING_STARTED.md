# NGL - Getting Started Guide

## Complete System Setup and Testing

This guide will walk you through setting up the complete NGL system with database, authentication, and testing it end-to-end.

## Prerequisites

- Docker and Docker Compose installed
- At least 2GB free disk space
- Ports 3000, 5000, 5432, 6379 available

## Step 1: Build and Start Services

```bash
cd /Users/alonraif/Code/ngl

# Stop any existing containers
docker-compose down

# Build and start all services
docker-compose up --build -d
```

This will start:
- **PostgreSQL** (database) on port 5432
- **Redis** (task queue) on port 6379
- **Backend API** on port 5000
- **Frontend** on port 3000
- **Celery Worker** (background tasks)
- **Celery Beat** (scheduled tasks)

## Step 2: Wait for Services to Be Ready

```bash
# Watch logs to see when services are ready
docker-compose logs -f

# Wait for these messages:
# - postgres: "database system is ready to accept connections"
# - backend: "Booting worker"
# - frontend: "webpack compiled successfully"
```

Press `Ctrl+C` to stop following logs.

## Step 3: Initialize Database and Create Admin

```bash
# Run inside backend container to create tables and admin user
docker-compose exec backend python3 init_admin.py
```

You should see:
```
Initializing database...
Creating admin user...
✓ Admin user created successfully!
  Username: admin
  Password: Admin123!
  ⚠️  Please change this password after first login!
```

## Step 4: Test the Application

### Open the Application

Open your browser and go to: **http://localhost:3000**

You should see the login page.

### Test Login

1. **Login as Admin:**
   - Username: `admin`
   - Password: `Admin123!`
   - Click "Sign In"

2. **You should be redirected to the upload page** with:
   - Your username in the header
   - "Admin" badge
   - Storage quota display
   - Navigation buttons (History, Admin, Logout)

### Test User Registration

1. **Logout** from admin account
2. **Click "Register"** on login page
3. **Create a new user:**
   - Username: `testuser` (min 3 chars)
   - Email: `test@example.com`
   - Password: `Test123!` (must have uppercase, lowercase, number, 8+ chars)
   - Confirm Password: `Test123!`
4. **Click "Create Account"**
5. **You should be automatically logged in** and redirected to upload page

### Test File Upload

1. **Select a log file** (.tar.bz2 or .tar.gz)
2. **Choose parser(s)** - check one or more boxes
3. **Select timezone** (default: US/Eastern)
4. **Optionally set date filters**
5. **Click "Analyze Log"**

You should see:
- Progress indicators for each parser
- Live time estimation with countdown
- Results displayed when complete
- Analysis saved to database (visible in History)

### Test Analysis History

1. **Click "History"** button in header
2. **You should see:**
   - List of all your analyses
   - Status badges (Completed, Failed, Running)
   - Creation timestamps
   - Processing times
3. **Click "View"** on any analysis to see full results

### Test Admin Features (Admin Login Only)

1. **Login as admin** (if not already)
2. **Click "Admin"** button in header

**Statistics Tab:**
- Total users, files, analyses
- Storage usage
- System overview

**Users Tab:**
- See all registered users
- Activate/Deactivate users
- Make users admin
- View storage quotas

**Parsers Tab:**
- See all available parsers
- Enable/disable parsers
- Control visibility to regular users
- Set admin-only parsers

### Test Parser Access Control

1. **As admin, go to Admin → Parsers**
2. **Click "Hide from Users"** on one parser
3. **Logout and login as regular user** (testuser)
4. **Go to upload page**
5. **Verify that parser is no longer visible** in the list

## Step 5: Verify Background Tasks

### Check Celery Worker

```bash
# View celery worker logs
docker-compose logs celery_worker

# Should show:
# - celery@<hostname> v5.3.4 (emerald-rush)
# - Tasks registered
```

### Check Scheduled Tasks

```bash
# View celery beat logs
docker-compose logs celery_beat

# Should show scheduled tasks:
# - cleanup-expired-files (every hour)
# - hard-delete-old-soft-deletes (daily)
```

### Manually Trigger Cleanup Task

```bash
# Execute cleanup task manually
docker-compose exec backend python3 -c "from tasks import cleanup_expired_files; print(cleanup_expired_files())"
```

## Step 6: Test API Endpoints Directly

### Get Health Status

```bash
curl http://localhost:5000/api/health
```

Response should show database connected:
```json
{
  "status": "healthy",
  "version": "4.0.0",
  "mode": "modular-with-database",
  "features": ["modular-parsers", "database", "authentication", "user-management"],
  "database": "connected"
}
```

### Test Login API

```bash
curl -X POST http://localhost:5000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"Admin123!"}'
```

Response includes access token:
```json
{
  "success": true,
  "access_token": "eyJ0eXAiOiJKV1...",
  "user": { ... }
}
```

### Test Authenticated Endpoint

```bash
# Replace <TOKEN> with actual token from login response
curl http://localhost:5000/api/auth/me \
  -H "Authorization: Bearer <TOKEN>"
```

## Troubleshooting

### Frontend won't load

```bash
# Check frontend logs
docker-compose logs frontend

# Rebuild frontend
docker-compose up --build frontend
```

### Backend 500 errors

```bash
# Check backend logs
docker-compose logs backend

# Check database connection
docker-compose exec postgres psql -U ngl_user -d ngl_db -c '\dt'
```

### Database connection failed

```bash
# Restart postgres
docker-compose restart postgres

# Check postgres health
docker-compose exec postgres pg_isready -U ngl_user -d ngl_db
```

### Clear all data and start fresh

```bash
# Stop containers
docker-compose down

# Remove volumes (⚠️ deletes all data!)
docker volume rm ngl_postgres_data ngl_redis_data

# Rebuild everything
docker-compose up --build -d

# Reinitialize
docker-compose exec backend python3 init_admin.py
```

## Default Credentials

### Admin User
- **Username:** admin
- **Password:** Admin123!
- **⚠️ Change this immediately in production!**

### Test User (create manually)
- **Username:** testuser
- **Password:** Test123!

## Security Notes

1. **Change admin password** after first login via the frontend
2. **Change JWT_SECRET_KEY** in docker-compose.yml before production
3. **Use environment variables** for production secrets
4. **Enable HTTPS** in production
5. **Regular database backups** recommended

## Next Steps

- Change default admin password
- Configure retention policies (default: 30 days)
- Set up email notifications (optional)
- Configure automated backups
- Review audit logs regularly
- Adjust storage quotas per user needs

## Key Features Implemented

✅ User authentication with JWT
✅ Role-based access (User/Admin)
✅ File upload with storage quotas
✅ Multi-parser selection and progress tracking
✅ Analysis history per user
✅ Admin dashboard (users, parsers, stats)
✅ Automated file lifecycle management
✅ Soft delete with 90-day recovery
✅ Complete audit logging
✅ Background task processing

## Support

For issues or questions, check:
- Backend logs: `docker-compose logs backend`
- Frontend logs: `docker-compose logs frontend`
- Database logs: `docker-compose logs postgres`
- All logs: `docker-compose logs -f`

Enjoy using NGL! 🚀
