# PostgreSQL to MySQL Migration Guide

Complete step-by-step guide for migrating NGL from PostgreSQL to MySQL in staging/production.

## 🎯 Overview

This migration moves all NGL data from PostgreSQL to MySQL while preserving:
- ✅ All user accounts and passwords
- ✅ All uploaded files and metadata
- ✅ All analysis history and results
- ✅ All audit logs and sessions
- ✅ All configuration and permissions

**Estimated Time**: 2-3 hours (depending on data volume)

---

## 📋 Prerequisites

### Before You Start

1. **Backup Everything** (CRITICAL!)
   ```bash
   # Backup PostgreSQL database
   docker-compose exec postgres pg_dump -U ngl_user ngl_db > backup_$(date +%Y%m%d_%H%M%S).sql

   # Backup uploaded files volume
   docker run --rm -v ngl_uploads:/data -v $(pwd):/backup alpine tar czf /backup/uploads_backup.tar.gz /data
   ```

2. **Verify Disk Space**
   ```bash
   # Check available space
   df -h

   # Check current database size
   docker-compose exec postgres psql -U ngl_user -d ngl_db -c "SELECT pg_size_pretty(pg_database_size('ngl_db'));"
   ```

3. **Schedule Downtime**
   - Notify users of maintenance window
   - Plan for 2-3 hours of downtime
   - Have rollback plan ready

---

## 🚀 Migration Steps

### Step 1: Export Data from PostgreSQL (30 min)

```bash
# Make sure your application is running on PostgreSQL
docker-compose ps

# Export all data
docker-compose exec backend python migrate_pg_to_mysql.py export

# Verify export succeeded
ls -lh /path/to/migration_data/
# Should see: users.json, analyses.json, migration_manifest.json, etc.
```

**Expected Output:**
```
==============================================================
POSTGRESQL DATA EXPORT
==============================================================
Source: postgres:5432/ngl_db
Output: /app/migration_data

  Exporting users... ✓ 15 rows (checksum: a3f2b891...)
  Exporting parsers... ✓ 19 rows (checksum: b7e4c912...)
  Exporting log_files... ✓ 234 rows (checksum: c8d5e023...)
  ...

==============================================================
✓ Export completed successfully!
  Total tables: 14
  Total rows: 1,458
  Manifest: /app/migration_data/migration_manifest.json
==============================================================
```

### Step 2: Stop the Application (5 min)

```bash
# Stop all services gracefully
docker-compose down

# Verify everything is stopped
docker-compose ps
# Should show: no services running
```

### Step 3: Switch to MySQL Configuration (10 min)

```bash
# Option A: Replace files (recommended for clean migration)
cp backend/requirements.mysql.txt backend/requirements.txt
cp backend/config.mysql.py backend/config.py
cp docker-compose.mysql.yml docker-compose.yml

# Option B: Use MySQL compose file directly
# docker-compose -f docker-compose.mysql.yml up -d
```

**Create `.env.mysql` file** (optional but recommended):
```bash
cat > .env.mysql <<EOF
# MySQL Configuration
MYSQL_DATABASE=ngl_db
MYSQL_USER=ngl_user
MYSQL_PASSWORD=ngl_password
MYSQL_ROOT_PASSWORD=secure_root_password_here

# Application
JWT_SECRET_KEY=your-production-secret-key
UPLOAD_RETENTION_DAYS=30
CORS_ORIGINS=http://localhost:3000,https://your-domain.com
EOF
```

### Step 4: Start MySQL and Create Schema (15 min)

```bash
# Start only MySQL service first
docker-compose up -d mysql

# Wait for MySQL to be healthy (watch for "healthy" status)
docker-compose ps mysql

# Check MySQL logs
docker-compose logs mysql

# Create database schema using Alembic
docker-compose up -d backend
docker-compose exec backend alembic upgrade head

# Verify tables were created
docker-compose exec mysql mysql -u ngl_user -pngl_password ngl_db -e "SHOW TABLES;"
```

**Expected Output:**
```
+------------------------+
| Tables_in_ngl_db       |
+------------------------+
| alert_rules            |
| analyses               |
| analysis_results       |
| audit_log              |
| deletion_log           |
| log_files              |
| notifications          |
| parser_permissions     |
| parsers                |
| retention_policies     |
| s3_configurations      |
| sessions               |
| ssl_configurations     |
| users                  |
+------------------------+
```

### Step 5: Import Data into MySQL (30 min - 1 hour)

```bash
# Set MySQL URL for migration script
export MYSQL_DATABASE_URL='mysql+pymysql://ngl_user:ngl_password@localhost:3306/ngl_db?charset=utf8mb4'

# Import all data
docker-compose exec backend python migrate_pg_to_mysql.py import
```

**Expected Output:**
```
==============================================================
MYSQL DATA IMPORT
==============================================================
Target: mysql:3306/ngl_db
Source: /app/migration_data

Manifest: 2025-10-12T15:30:00.000000
Tables: 14

  Importing users... ✓ 15 rows
  Importing parsers... ✓ 19 rows
  Importing parser_permissions... ✓ 285 rows
  Importing log_files... ✓ 234 rows
  Importing analyses... ✓ 567 rows
  Importing analysis_results... ✓ 567 rows
  ...

==============================================================
✓ Import completed successfully!
  Total tables: 14
  Total rows: 1,458
==============================================================
```

### Step 6: Verify Data Integrity (15 min)

```bash
# Run verification script
docker-compose exec backend python migrate_pg_to_mysql.py verify
```

**Expected Output:**
```
==============================================================
MIGRATION VERIFICATION
==============================================================
  users: ✓ 15 rows
  parsers: ✓ 19 rows
  parser_permissions: ✓ 285 rows
  log_files: ✓ 234 rows
  analyses: ✓ 567 rows
  analysis_results: ✓ 567 rows
  retention_policies: ✓ 1 rows
  deletion_log: ✓ 23 rows
  audit_log: ✓ 1234 rows
  sessions: ✓ 3 rows
  notifications: ✓ 45 rows
  alert_rules: ✓ 7 rows
  s3_configurations: ✓ 0 rows
  ssl_configurations: ✓ 1 rows

==============================================================
✓ All tables verified successfully!
==============================================================
```

### Step 7: Start All Services (10 min)

```bash
# Start all services
docker-compose up -d

# Check health of all services
docker-compose ps

# Watch logs for any errors
docker-compose logs -f backend
```

### Step 8: Test the Application (30 min)

#### Critical Tests:

1. **Authentication**
   ```bash
   # Test login with existing user
   curl -X POST http://localhost:5000/api/auth/login \
     -H "Content-Type: application/json" \
     -d '{"username":"admin","password":"Admin123!"}'
   ```

2. **File Upload**
   - Log in to frontend: http://localhost:3000
   - Upload a test log file
   - Verify parsing works
   - Check results display correctly

3. **Analysis History**
   - Navigate to Analysis History page
   - Verify all past analyses are visible
   - Click on an analysis to view details

4. **Admin Dashboard**
   - Log in as admin
   - Check Statistics tab (users, files, analyses)
   - Verify Users tab shows all users
   - Check Parsers tab

5. **Database Queries**
   ```bash
   # Count records in key tables
   docker-compose exec mysql mysql -u ngl_user -pngl_password ngl_db <<EOF
   SELECT 'Users' as Table, COUNT(*) as Count FROM users
   UNION ALL
   SELECT 'Log Files', COUNT(*) FROM log_files
   UNION ALL
   SELECT 'Analyses', COUNT(*) FROM analyses
   UNION ALL
   SELECT 'Sessions', COUNT(*) FROM sessions;
   EOF
   ```

### Step 9: Monitor for 24-48 Hours

```bash
# Watch application logs
docker-compose logs -f backend celery_worker

# Monitor MySQL performance
docker-compose exec mysql mysql -u ngl_user -pngl_password -e "SHOW PROCESSLIST;"

# Check error logs
docker-compose logs backend | grep -i error
```

---

## 🔄 Rollback Plan

If something goes wrong, you can quickly rollback to PostgreSQL:

```bash
# Stop everything
docker-compose down

# Restore original files
git checkout docker-compose.yml backend/requirements.txt backend/config.py

# Restore PostgreSQL from backup
docker-compose up -d postgres
docker-compose exec -T postgres psql -U ngl_user -d ngl_db < backup_YYYYMMDD_HHMMSS.sql

# Start all services
docker-compose up -d

# Verify application works
curl http://localhost:5000/api/health
```

---

## 🐛 Troubleshooting

### Issue: Import fails with "Foreign key constraint fails"

**Solution:**
```bash
# The script automatically disables FK checks, but if it fails:
docker-compose exec mysql mysql -u ngl_user -pngl_password ngl_db -e "SET FOREIGN_KEY_CHECKS=0;"
# Re-run import
docker-compose exec backend python migrate_pg_to_mysql.py import
```

### Issue: Row count mismatch in verification

**Solution:**
```bash
# Check which table has the issue
docker-compose exec backend python migrate_pg_to_mysql.py verify

# Manually compare counts
docker-compose exec mysql mysql -u ngl_user -pngl_password ngl_db -e "SELECT COUNT(*) FROM users;"

# Check migration logs for errors
cat /path/to/migration_data/migration_manifest.json
```

### Issue: Login fails after migration

**Possible causes:**
1. Password hashes not migrated correctly
2. Session tokens invalid

**Solution:**
```bash
# Check user exists
docker-compose exec mysql mysql -u ngl_user -pngl_password ngl_db -e "SELECT id, username, email FROM users WHERE username='admin';"

# Reset admin password if needed
docker-compose exec backend python init_admin.py

# Clear old sessions
docker-compose exec mysql mysql -u ngl_user -pngl_password ngl_db -e "DELETE FROM sessions;"
```

### Issue: JSON queries not working

**Solution:**
Check your code for PostgreSQL-specific JSON syntax:
```python
# PostgreSQL syntax (won't work in MySQL):
filter(Model.data['key'].astext == 'value')

# MySQL-compatible syntax:
filter(Model.data['key'] == 'value')  # SQLAlchemy abstracts this
```

### Issue: Timezone issues with DateTime fields

**Solution:**
MySQL doesn't store timezone info. Ensure your application always uses UTC:
```python
from datetime import datetime, timezone

# Always use UTC
now = datetime.now(timezone.utc)
```

---

## 📊 Performance Comparison

After migration, monitor these metrics:

| Metric | PostgreSQL | MySQL | Notes |
|--------|-----------|-------|-------|
| Login time | ___ ms | ___ ms | Should be similar |
| File upload | ___ s | ___ s | Depends on file size |
| Parse time | ___ s | ___ s | Mostly CPU, not DB |
| Query latency | ___ ms | ___ ms | Check slow queries |
| Disk usage | ___ GB | ___ GB | MySQL may differ |

```bash
# Monitor query performance
docker-compose exec mysql mysql -u ngl_user -pngl_password -e "SHOW STATUS LIKE 'Slow_queries';"

# Enable slow query log
docker-compose exec mysql mysql -u ngl_user -pngl_password -e "SET GLOBAL slow_query_log = 'ON'; SET GLOBAL long_query_time = 1;"
```

---

## ✅ Post-Migration Checklist

- [ ] All services running and healthy
- [ ] Can log in with existing credentials
- [ ] Can upload new files
- [ ] Can view analysis history
- [ ] Admin dashboard accessible
- [ ] File downloads work
- [ ] Audit logs showing recent actions
- [ ] Celery tasks running (check `docker-compose logs celery_worker`)
- [ ] SSL certificates still valid (if using HTTPS)
- [ ] Backups configured for MySQL
- [ ] Monitoring/alerting updated for MySQL
- [ ] Documentation updated
- [ ] Team notified of completion

---

## 🗑️ Cleanup (After 1 Week of Successful Operation)

Once you're confident the migration was successful:

```bash
# Remove PostgreSQL data (CAREFUL!)
docker volume rm ngl_postgres_data

# Remove backup files (after archiving)
rm backup_*.sql
rm uploads_backup.tar.gz

# Remove migration data
docker-compose exec backend rm -rf /app/migration_data/*

# Update documentation to reflect MySQL
```

---

## 📞 Support

If you encounter issues:

1. Check logs: `docker-compose logs backend mysql`
2. Review this guide's Troubleshooting section
3. Test rollback procedure
4. Contact your DBA/DevOps team

---

## 📝 Key Differences: PostgreSQL vs MySQL

### Things That Work Differently:

1. **JSON Queries**
   - PostgreSQL: `->`, `->>`, `@>`, `?`
   - MySQL: `JSON_EXTRACT()`, `JSON_CONTAINS()`
   - SQLAlchemy usually handles this

2. **Timezone Handling**
   - PostgreSQL: Native timezone support
   - MySQL: Application must handle UTC conversion

3. **String Comparison**
   - PostgreSQL: Case-sensitive by default
   - MySQL: Case-insensitive by default (utf8mb4_unicode_ci)

4. **Boolean Values**
   - PostgreSQL: `TRUE`/`FALSE`
   - MySQL: `1`/`0` (but SQLAlchemy handles this)

5. **RETURNING Clause**
   - PostgreSQL: `INSERT ... RETURNING id`
   - MySQL 8.0.21+: Supported
   - Older MySQL: Use `LAST_INSERT_ID()`

---

## 🎉 Success!

If you've completed all steps and tests pass, congratulations! Your NGL application is now running on MySQL.

**Remember:**
- Keep PostgreSQL backups for at least 30 days
- Monitor performance closely for first week
- Update any documentation/runbooks
- Inform your team about the change

---

**Migration Script Version**: 1.0
**Last Updated**: October 2025
**Tested On**: MySQL 8.0, Python 3.11, SQLAlchemy 2.0.23
