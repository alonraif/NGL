# Audit System Guide

## Overview

The NGL Audit System provides comprehensive security monitoring and activity tracking with IP geolocation. All user actions are logged and can be viewed by administrators through the Audit Logs tab.

## Features Implemented

### ✅ Core Features
- **Complete Audit Trail**: 13+ action types tracked automatically
- **IP Geolocation**: Real-time geolocation of all login/action IPs
- **Advanced Filtering**: Filter by user, action, entity, date range, status, search
- **Statistics Dashboard**: Total events, today's count, active users, failed logins
- **Geographic Distribution**: Top 10 countries with event counts and flags
- **Action Breakdown**: All actions with counts
- **User Activity**: Top 10 most active users
- **CSV Export**: Compliance-ready exports with all filters
- **Meta-Auditing**: Tracks who views audit logs

### 🔧 Technical Implementation

#### Backend Components

1. **IP Geolocation Service** ([backend/geo_service.py](backend/geo_service.py))
   - Two-tier geolocation: MaxMind GeoLite2 (offline) + ip-api.com (online fallback)
   - Returns: country, city, region, coordinates, timezone, flag emoji
   - LRU cache (1000 entries) for performance

2. **Audit API Endpoints** ([backend/admin_routes.py](backend/admin_routes.py))
   - `GET /api/admin/audit-logs` - Query logs with filtering, pagination, sorting
   - `GET /api/admin/audit-stats` - Statistics with geographic distribution
   - `GET /api/admin/audit-export` - CSV export with all filters

3. **IP Address Capture** ([backend/auth.py](backend/auth.py))
   - Extracts real client IP from `X-Forwarded-For` header
   - Handles proxy forwarding correctly
   - Captures IP for all logged actions

4. **Nginx Configuration** ([frontend/nginx.conf](frontend/nginx.conf))
   - Forwards `X-Real-IP` header
   - Forwards `X-Forwarded-For` header for proxy chains
   - Preserves original client IP through proxy

#### Frontend Components

1. **Audit Tab** ([frontend/src/pages/AdminDashboard.js](frontend/src/pages/AdminDashboard.js))
   - Statistics cards with key metrics
   - Comprehensive filters panel
   - Audit logs table with geolocation display
   - Geographic distribution cards with flags
   - Action breakdown cards
   - User activity table
   - CSV export button

## Tracked Actions

The following actions are automatically logged:

### Authentication
- `login` - User login (tracks IP, geolocation, success/failure)
- `logout` - User logout
- `change_password` - Password changes

### File Operations
- `upload_and_parse` - File uploads with parse mode
- `download_log_file` - File downloads

### Analysis Operations
- `view_analysis` - Viewing analysis results
- `cancel_analysis` - Cancelling running analyses
- `search_analyses` - Search queries

### Administrative Actions
- `create_user` - User creation
- `update_user` - User updates (role, quota, status)
- `delete_user` - User deletion
- `view_audit_logs` - Viewing audit logs (meta-auditing)

## How to Use

### Accessing the Audit System

1. Log in as an admin user
2. Navigate to **Admin Dashboard**
3. Click the **Audit Logs** tab

### Filtering Audit Logs

Use the filters panel to narrow down results:
- **User**: Select specific user or "All Users"
- **Action**: Filter by action type
- **Entity Type**: Filter by entity (user, analysis, log_file, parser)
- **Status**: Show only successful or failed actions
- **Date Range**: Set start/end dates
- **Search**: Search in IP addresses and details

### Exporting Audit Logs

Click the **"Export to CSV"** button to download audit logs with current filters applied. The CSV includes:
- Timestamp
- Username
- Action
- Entity type/ID
- IP address
- Country, City (geolocation)
- Status (success/failure)
- Error message (if failed)
- Additional details (JSON)

### Understanding Geolocation Data

Each audit log entry shows:
- **IP Address**: Real client IP (not Docker internal IP)
- **Location**: City, Country with flag emoji (e.g., 🇺🇸 New York, United States)
- **Source**: Where the geolocation data came from (maxmind or ip-api)

**Note**: Docker internal IPs (172.x.x.x) won't have geolocation data. Public IPs will show accurate geolocation.

## Testing the Audit System

### 1. Generate Audit Events

Perform various actions to generate audit logs:
```bash
# 1. Login (creates login event)
# 2. Upload a file (creates upload_and_parse event)
# 3. View analysis (creates view_analysis event)
# 4. Download a file (creates download_log_file event)
# 5. View audit logs (creates view_audit_logs event - meta-auditing)
```

### 2. Check Audit Logs

```bash
# View recent audit logs from database
docker-compose exec -T postgres psql -U ngl_user -d ngl_db -c "
SELECT
    timestamp,
    action,
    ip_address,
    success
FROM audit_log
ORDER BY timestamp DESC
LIMIT 10;
"
```

### 3. Test IP Capture

**From Local Machine (Docker IP)**:
```bash
# Login will show Docker internal IP (172.x.x.x)
curl -X POST http://localhost:3000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"Admin123!"}'
```

**From Browser (Real IP)**:
- Open http://localhost:3000
- Login through browser
- IP will be captured from browser's public IP (if accessible)

### 4. Test Geolocation

For public IPs, the system will automatically:
1. Try MaxMind GeoLite2 (offline database)
2. Fallback to ip-api.com (online service)
3. Return country, city, flag, coordinates

### 5. Verify in UI

1. Go to Admin Dashboard → Audit Logs tab
2. You should see:
   - Statistics cards with event counts
   - Geographic distribution (if public IPs)
   - Audit logs table with IP addresses and locations
   - Filters working correctly

## Troubleshooting

### Issue: No geolocation data shown

**Cause**: Using Docker internal IPs (172.x.x.x) or localhost (127.0.0.1)

**Solution**:
- Public IPs will show geolocation
- Local development uses Docker internal IPs (no geolocation)
- In production, real client IPs will be captured

### Issue: IP address shows as 172.x.x.x

**Cause**: Nginx not forwarding `X-Forwarded-For` header

**Verification**:
```bash
# Check nginx config has X-Forwarded-For
docker-compose exec -T frontend grep "X-Forwarded-For" /etc/nginx/nginx.conf
```

**Solution**: Already fixed - nginx now forwards client IP correctly

### Issue: Audit logs not showing in UI

**Cause**: Authentication or API endpoint issue

**Check**:
```bash
# Verify audit API endpoints are registered
docker-compose exec -T backend python3 -c "
from app import app
audit_routes = [str(r) for r in app.url_map.iter_rules() if 'audit' in str(r)]
print('\n'.join(audit_routes))
"
```

Expected output:
```
/api/admin/audit-logs
/api/admin/audit-stats
/api/admin/audit-export
```

## Database Schema

Audit logs are stored in the `audit_log` table:

```sql
-- View audit log schema
docker-compose exec -T postgres psql -U ngl_user -d ngl_db -c "\d audit_log"
```

Key fields:
- `id`: Unique audit log ID
- `user_id`: User who performed the action
- `timestamp`: When the action occurred
- `action`: Type of action (login, upload, etc.)
- `entity_type`: Type of entity affected (user, analysis, etc.)
- `entity_id`: ID of affected entity
- `details`: JSON details about the action
- `ip_address`: Client IP address
- `user_agent`: Client browser/user agent
- `success`: Whether action succeeded
- `error_message`: Error message if failed

## Security Considerations

### IP Address Privacy
- IP addresses are logged for security monitoring
- Only admins can view audit logs
- Consider compliance requirements (GDPR, etc.)

### Data Retention
- Audit logs are never automatically deleted
- Implement custom retention policy if needed
- Export to CSV for long-term archival

### Meta-Auditing
- Viewing audit logs is itself audited
- Tracks which admins viewed logs and when
- Includes filters used in the view

## Future Enhancements

Optional features not yet implemented:

1. **World Map Visualization**: Geographic heat map of login locations
2. **WebSocket Real-time Streaming**: Live audit event updates
3. **Alert System**: Email/Slack notifications for security events
4. **Automatic Anomaly Detection**: AI-based suspicious activity detection
5. **Custom Retention Policies**: Configurable audit log retention
6. **Report Scheduling**: Automated weekly/monthly audit reports

## Support

For issues or questions:
1. Check Docker logs: `docker-compose logs backend`
2. Check database: `docker-compose exec -T postgres psql -U ngl_user -d ngl_db`
3. Review [TROUBLESHOOTING.md](TROUBLESHOOTING.md)

---

**Last Updated**: October 2025
**Version**: 4.0.0 with Audit System
