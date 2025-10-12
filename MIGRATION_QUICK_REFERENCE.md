# MySQL Migration Quick Reference Card

**Print this and keep it handy during migration!**

---

## 📝 Pre-Migration Checklist

```bash
# 1. Backup database
docker-compose exec postgres pg_dump -U ngl_user ngl_db > backup_$(date +%Y%m%d_%H%M%S).sql

# 2. Backup volumes
docker run --rm -v ngl_uploads:/data -v $(pwd):/backup alpine tar czf /backup/uploads_backup.tar.gz /data

# 3. Check disk space
df -h

# 4. Export data
docker-compose exec backend python migrate_pg_to_mysql.py export
```

---

## 🚀 Migration Commands (In Order)

```bash
# 1. Stop everything
docker-compose down

# 2. Switch configuration
cp docker-compose.mysql.yml docker-compose.yml
cp backend/requirements.mysql.txt backend/requirements.txt
cp backend/config.mysql.py backend/config.py

# 3. Start MySQL
docker-compose up -d mysql
# Wait 30 seconds...

# 4. Create schema
docker-compose up -d backend
docker-compose exec backend alembic upgrade head

# 5. Import data
export MYSQL_DATABASE_URL='mysql+pymysql://ngl_user:ngl_password@localhost:3306/ngl_db?charset=utf8mb4'
docker-compose exec backend python migrate_pg_to_mysql.py import

# 6. Verify
docker-compose exec backend python migrate_pg_to_mysql.py verify

# 7. Start all services
docker-compose up -d

# 8. Run tests
./test_migration.sh
```

---

## 🔍 Quick Verification Commands

```bash
# Check all services
docker-compose ps

# Check MySQL tables
docker-compose exec mysql mysql -u ngl_user -pngl_password ngl_db -e "SHOW TABLES;"

# Count users
docker-compose exec mysql mysql -u ngl_user -pngl_password ngl_db -e "SELECT COUNT(*) FROM users;"

# Test login
curl -X POST http://localhost:5000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"Admin123!"}'

# Check health
curl http://localhost:5000/api/health
```

---

## 🐛 Troubleshooting Quick Fixes

### Login fails
```bash
docker-compose exec backend python init_admin.py
docker-compose exec mysql mysql -u ngl_user -pngl_password ngl_db -e "DELETE FROM sessions;"
docker-compose restart backend
```

### Foreign key errors during import
```bash
docker-compose exec mysql mysql -u ngl_user -pngl_password ngl_db -e "SET FOREIGN_KEY_CHECKS=0;"
docker-compose exec backend python migrate_pg_to_mysql.py import
docker-compose exec mysql mysql -u ngl_user -pngl_password ngl_db -e "SET FOREIGN_KEY_CHECKS=1;"
```

### Service won't start
```bash
docker-compose logs backend
docker-compose logs mysql
docker-compose down
docker-compose up -d
```

---

## 🔄 Rollback Commands (Emergency)

```bash
# 1. Stop everything
docker-compose down

# 2. Restore original files
git checkout docker-compose.yml backend/requirements.txt backend/config.py

# 3. Restore database
docker-compose up -d postgres
# Wait 30 seconds...
docker-compose exec -T postgres psql -U ngl_user -d ngl_db < backup_YYYYMMDD_HHMMSS.sql

# 4. Start everything
docker-compose up -d
```

---

## 📊 Monitoring Commands

```bash
# Watch logs
docker-compose logs -f backend

# MySQL processlist
docker-compose exec mysql mysql -u ngl_user -pngl_password -e "SHOW PROCESSLIST;"

# Check slow queries
docker-compose exec mysql mysql -u ngl_user -pngl_password -e "SHOW STATUS LIKE 'Slow_queries';"

# Database size
docker-compose exec mysql mysql -u ngl_user -pngl_password ngl_db -e "SELECT table_schema AS 'Database', ROUND(SUM(data_length + index_length) / 1024 / 1024, 2) AS 'Size (MB)' FROM information_schema.tables WHERE table_schema='ngl_db';"
```

---

## 📞 Emergency Contacts

- **DBA**: _______________
- **DevOps**: _______________
- **On-Call**: _______________

## 🕐 Migration Timeline

- Start Time: _______________
- Export Complete: _______________
- Import Complete: _______________
- Verification Done: _______________
- Services Started: _______________
- Tests Passed: _______________
- End Time: _______________

## ✅ Sign-Off

- [ ] Data exported successfully
- [ ] MySQL schema created
- [ ] Data imported successfully
- [ ] Verification passed
- [ ] All services running
- [ ] Tests passed
- [ ] Team notified

**Migrated by**: _______________
**Date**: _______________
**Sign**: _______________

---

## 📁 Important Files

- Migration script: `backend/migrate_pg_to_mysql.py`
- Test script: `test_migration.sh`
- Full guide: `MYSQL_MIGRATION_GUIDE.md`
- Backup location: `backup_$(date).sql`
- Migration data: `/app/migration_data/`

## 🔗 Useful URLs

- Frontend: http://localhost:3000
- Backend Health: http://localhost:5000/api/health
- API Docs: http://localhost:5000/api/
- MySQL Port: localhost:3306

---

**Keep PostgreSQL backups for 30 days after successful migration!**
