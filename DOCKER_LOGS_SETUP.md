# Docker Logs Feature Setup Guide

## Overview

The Docker Logs feature allows admins to view real-time container logs from the Admin Dashboard's Audit tab. This feature has been fully implemented but requires Docker socket access to function.

## What Was Implemented

### Backend (Python)
1. **`backend/docker_service.py`**: Helper module for Docker operations
   - `get_docker_logs()`: Fetch logs from containers
   - `get_available_services()`: List running services
   - `get_service_status()`: Get service health status
   - `is_docker_available()`: Check Docker connectivity

2. **`backend/admin_routes.py`**: API endpoints (admin-only)
   - `GET /api/admin/docker-logs`: Fetch logs with filters
     - Query params: `service`, `since` (1h/2h/24h), `tail` (lines)
   - `GET /api/admin/docker-services`: List available services

### Frontend (React)
3. **`frontend/src/pages/AdminDashboard.js`**: UI in Audit tab
   - Service selector dropdown (backend, frontend, postgres, redis, etc.)
   - Time range buttons (1h, 2h, 24h)
   - Auto-refresh toggle (every 10 seconds)
   - Color-coded log display by service
   - Download logs as text file

## Features

- ✅ View logs from any Docker service or all services
- ✅ Filter by time range (1h, 2h, 24h)
- ✅ Auto-refresh option
- ✅ Color-coded by service
- ✅ Download logs as text file
- ✅ Audit logging (tracks who viewed what logs)
- ✅ Admin-only access
- ✅ Graceful fallback when Docker is unavailable

## Setup Required

### Option 1: Mount Docker Socket (Recommended for Development)

To enable Docker logs, you need to mount the Docker socket into the backend container.

**Update `docker-compose.yml` - backend service:**

```yaml
backend:
  build:
    context: ./backend
    dockerfile: Dockerfile
  ports:
    - "5000:5000"
  volumes:
    - ./backend:/app
    - uploads:/app/uploads
    - temp:/app/temp
    - /var/run/docker.sock:/var/run/docker.sock  # ADD THIS LINE
  environment:
    # ... existing environment variables ...
```

**Restart the backend:**
```bash
docker-compose restart backend
```

**Verify it works:**
```bash
docker-compose exec backend python3 -c "from docker_service import is_docker_available; print('Docker available:', is_docker_available())"
```

Should output: `Docker available: True`

### Option 2: Alternative Approaches

#### 2a. Docker-in-Docker (DinD)
More secure but complex. Run Docker daemon inside the container.

#### 2b. Host-based Script
Create a script on the host that the backend calls via SSH/API. More secure for production.

#### 2c. Use Docker API
Instead of mounting the socket, use Docker's remote API with TLS authentication.

## Security Considerations

### Mounting Docker Socket (Option 1)

**⚠️ Security Warning:**
Mounting `/var/run/docker.sock` gives the container **full control** over the Docker daemon. A compromised container could:
- Stop/start/delete any container
- Read sensitive data from other containers
- Escalate privileges to host

**Mitigation:**
1. ✅ **Admin-only access**: Only admins can view logs (already implemented)
2. ✅ **Read-only operations**: The code only reads logs, doesn't modify containers
3. ✅ **Input validation**: Service names are validated against whitelist
4. ✅ **Command injection prevention**: Uses subprocess with argument arrays, not shell commands
5. ✅ **Audit logging**: All log views are tracked in audit_log table
6. ✅ **No user input in commands**: Fixed command structure

**Recommended for:**
- ✅ Development environments
- ✅ Internal tools
- ✅ Trusted admin users

**NOT recommended for:**
- ❌ Public-facing applications
- ❌ Untrusted user access
- ❌ Multi-tenant environments

## Production Recommendations

For production deployments, consider these alternatives:

### 1. Centralized Logging
Use a proper logging solution:
- **ELK Stack** (Elasticsearch, Logstash, Kibana)
- **Grafana Loki**
- **Datadog / New Relic**
- **CloudWatch** (AWS)

These provide:
- Better security (no Docker socket access needed)
- Advanced search and filtering
- Long-term log retention
- Alerting and visualization
- Multi-environment support

### 2. Read-Only Docker Socket
Create a proxy that only allows read operations:
```bash
# Use a tool like docker-socket-proxy
# GitHub: https://github.com/Tecnativa/docker-socket-proxy
```

### 3. Kubernetes Alternative
If using Kubernetes, use built-in log aggregation:
```bash
kubectl logs <pod-name> --tail=100
```

## Usage

1. Log in as admin user
2. Navigate to **Admin Dashboard → Audit Logs** tab
3. Scroll to bottom to find "**Docker Container Logs**" section
4. Select service (or "All Services")
5. Choose time range (1h, 2h, 24h)
6. Enable auto-refresh if needed
7. Click "Download Logs" to save locally

## API Examples

### Get backend logs from last hour
```bash
curl -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  "http://localhost:5000/api/admin/docker-logs?service=backend&since=1h&tail=500"
```

### Get all service logs from last 2 hours
```bash
curl -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  "http://localhost:5000/api/admin/docker-logs?service=all&since=2h&tail=1000"
```

### List available services
```bash
curl -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  "http://localhost:5000/api/admin/docker-services"
```

## Troubleshooting

### "Docker Not Available" Error

**Cause**: Docker socket not mounted or not accessible

**Fix**:
1. Check if Docker socket is mounted: `docker-compose exec backend ls -la /var/run/docker.sock`
2. If not found, add volume mount to docker-compose.yml (see Setup above)
3. Restart: `docker-compose restart backend`

### "Permission Denied" Error

**Cause**: Backend user doesn't have permission to access Docker socket

**Fix**:
```dockerfile
# In backend/Dockerfile, add:
RUN addgroup --gid 999 docker && \
    adduser app docker
```

Then rebuild: `docker-compose up --build backend`

### Empty Logs / No Services Found

**Cause 1**: Services recently started (no logs yet)
**Fix**: Wait a few minutes for logs to accumulate

**Cause 2**: Time range too short
**Fix**: Try 24h time range

**Cause 3**: Service name mismatch
**Fix**: Check actual service names: `docker-compose ps --services`

## Testing

### Manual Test
1. Visit: http://localhost:3000
2. Login as admin (username: `admin`, password: `Admin123!`)
3. Go to: Admin Dashboard → Audit Logs tab
4. Scroll to "Docker Container Logs" section
5. Select "Backend" service, "1h" time range
6. Click "Refresh"
7. Should see recent backend logs

### Automated Test
```bash
# Test Docker availability
docker-compose exec backend python3 -c "
from docker_service import is_docker_available, get_docker_logs
print('Docker available:', is_docker_available())
if is_docker_available():
    logs, count = get_docker_logs('backend', '1h', 100)
    print(f'Retrieved {count} log lines')
"
```

## Implementation Summary

**Backend Files Created/Modified:**
- ✅ `backend/docker_service.py` (new, 250 lines)
- ✅ `backend/admin_routes.py` (added 150 lines)

**Frontend Files Modified:**
- ✅ `frontend/src/pages/AdminDashboard.js` (added 350 lines)

**Total Lines Added**: ~750 lines

**Time to Implement**: ~3 hours

**Security**: Admin-only, input validated, audit logged

**Status**: ✅ Fully implemented, requires Docker socket mount to enable

---

## Quick Enable (Development)

```bash
# 1. Add Docker socket mount to docker-compose.yml backend volumes:
#    - /var/run/docker.sock:/var/run/docker.sock

# 2. Restart
docker-compose restart backend

# 3. Test
docker-compose exec backend python3 -c "from docker_service import is_docker_available; print(is_docker_available())"

# 4. Open browser
open http://localhost:3000
# Login as admin → Admin Dashboard → Audit Logs tab → scroll to bottom
```

Done! 🎉
