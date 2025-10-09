# 🔧 Troubleshooting Guide

Common issues and their solutions for LiveU Log Analyzer Web UI.

## Upload Issues

### 413 Request Entity Too Large ✅ FIXED

**Error:** `Failed to load resource: the server responded with a status of 413 (Request Entity Too Large)`

**Cause:** File size exceeds Nginx's default upload limit (1MB).

**Solution:** The Nginx configuration has been updated to support files up to 500MB.

If you still see this error:
```bash
# Rebuild the frontend container
docker-compose down
docker-compose up --build -d
```

**Configuration (already applied):**
```nginx
# In frontend/nginx.conf
client_max_body_size 500M;
client_body_timeout 300s;
```

### File Upload Hangs

**Symptoms:** Upload progress stalls or browser shows "waiting"

**Solutions:**

1. **Check file size:**
   ```bash
   ls -lh your-file.tar.bz2
   ```
   Files larger than 500MB need configuration adjustment.

2. **Increase timeout in docker-compose.yml:**
   ```yaml
   backend:
     environment:
       - UPLOAD_TIMEOUT=600  # 10 minutes
   ```

3. **Check backend logs:**
   ```bash
   docker-compose logs -f backend
   ```

### Invalid File Type Error

**Error:** `Invalid file type. Please upload .tar.bz2 files`

**Solutions:**

1. **Verify file extension:**
   - File must end in `.tar.bz2`
   - Case-sensitive on Linux/Mac

2. **Check file format:**
   ```bash
   file your-file.tar.bz2
   # Should show: bzip2 compressed data
   ```

3. **Re-compress if needed:**
   ```bash
   tar -cjf logs.tar.bz2 logs/
   ```

### Uploaded Files Are 0 Bytes / "untar failed with: ex failed with: 2:" ✅ FIXED

**Error:** `The untar failed with: ex failed with: 2:`

**Symptoms:**
- Files upload successfully but parsing fails
- Checking `/app/uploads/` shows 0-byte files
- Database shows correct file size but disk file is empty

**Cause:** A bug in the local storage implementation was causing files to overwrite themselves during the save process. The code was:
1. Saving uploaded file to temporary location
2. Reopening the same file
3. Attempting to save it again to the same path (overwriting while reading)
4. Result: 0-byte corrupted files

**Solution:** Fixed in app.py - local storage now skips the redundant save operation since the file is already in the correct location. Only S3 uploads perform the additional save step.

**Status:** ✅ Fixed as of October 6, 2025

If you still see this error:
```bash
# Restart backend to get latest code
docker-compose restart backend
```

## Processing Issues

### Timezone Comparison Error ✅ FIXED

**Error:** `TypeError: can't compare offset-naive and offset-aware datetimes`

**Cause:** The original lula2.py script had issues comparing datetimes with different timezone awareness when using date range filters.

**Solution:** The DateRange class has been updated to handle timezone-aware and timezone-naive datetime objects properly.

If you still see this error:
```bash
# Rebuild the backend container
docker-compose up --build -d backend
```

**Workaround:** Don't use the begin/end date filters, or ensure your dates include timezone info:
```
# Good: Include timezone
2024-01-01 12:00:00+00:00

# Also good: UTC format
2024-01-01T12:00:00Z
```

### Processing Timeout (408)

**Error:** `Processing timeout (>5 minutes)`

**Cause:** Log file is very large or complex.

**Solutions:**

1. **Increase timeout in backend/app.py:**
   ```python
   result = subprocess.run(
       cmd,
       capture_output=True,
       text=True,
       timeout=600  # Change from 300 to 600 (10 minutes)
   )
   ```

2. **Rebuild backend:**
   ```bash
   docker-compose up --build backend
   ```

### No Visualization Available

**Symptoms:** "No visualization available for this parse mode" message

**Explanation:** Only certain parse modes have visualizations:
- `md` (Modem Statistics) → Bar/Line charts
- `bw`, `md-bw`, `md-db-bw` → Bandwidth charts
- `sessions` → Session table

**Solution:** Check "Raw Output" tab for results, or choose a different parse mode.

### Empty Results

**Cause:** No matching data found in log file.

## Authentication Issues

### Login fails right after enabling HTTPS enforcement

**Symptoms:** Login/API calls from the browser fail immediately after toggling **Enforce HTTPS** in the admin dashboard. Browser devtools show the original request redirected (HTTP 301) to `https://…/api/auth/login`, followed by a `405 Method Not Allowed` or a blank JSON error.

**Cause:** Older runtime builds returned a `301` from Flask and Nginx when redirecting HTTP→HTTPS. Browsers replay `POST`/`PUT` requests as `GET` on a `301`, so the login body was dropped once HTTPS was enforced.

**Fix (already patched in codebase):**
- Flask now issues a `308` redirect that preserves the HTTP method/body.
- The SSL redirect snippet written for Nginx also defaults to status `308`. You can override with `HTTPS_REDIRECT_STATUS` if your ingress needs a different code.

**Apply the fix to an existing deployment:**
1. Pull/rebuild the updated backend container so the new redirect handler is in place.
2. Regenerate the Nginx snippet (either toggle **Enforce HTTPS** off/on in the admin UI or run `docker-compose restart frontend` after redeploy so `/etc/nginx/runtime/ssl-redirect.conf` is rewritten).
3. Clear browser caches if an old HSTS/redirect is cached, then retry login over `https://`.

**Need to temporarily disable HTTPS during maintenance?**
- Set `FORCE_DISABLE_HTTPS_ENFORCEMENT=true` in your `.env`, redeploy backend/frontend, and NGL will automatically stop redirecting or advertising enforced HTTPS until you flip it back.
- Want HTTPS to stay available while still allowing HTTP? Leave `SSL_ALLOW_OPTIONAL_HTTPS=true`, toggle **Enforce HTTPS** off in the admin UI (or call `/api/admin/ssl/enforce` with `{"enforce": false}`), and the cert-backed 443 listener stays up while redirects remain off.
- Browser still bouncing you back to HTTPS after disabling enforcement? That means it cached the previous HSTS header. Redeploy with enforcement off (or `FORCE_DISABLE_HTTPS_ENFORCEMENT=true`) and refresh using a new session—NGL now sends `Strict-Transport-Security: max-age=0`, but you may still need to clear the browser’s HSTS cache or use an incognito window the first time.

**Solutions:**

1. **Try different parse mode:**
   - Start with `all` to see if data exists
   - Then try specific modes

2. **Check date range:**
   - Remove begin/end date filters
   - Verify timezone is correct

3. **Verify log file content:**
   ```bash
   # Extract and check
   tar -xjf your-file.tar.bz2
   ls -la
   cat messages.log | head -20
   ```

## Docker Issues

### Port Already in Use

**Error:** `Bind for 0.0.0.0:3000 failed: port is already allocated`

**Solutions:**

1. **Stop conflicting services:**
   ```bash
   # Find what's using the port
   lsof -i :3000
   lsof -i :5000

   # Kill if needed
   kill -9 <PID>
   ```

2. **Change ports in docker-compose.yml:**
   ```yaml
   frontend:
     ports:
       - "3001:80"  # Use 3001 instead
   backend:
     ports:
       - "5001:5000"  # Use 5001 instead
   ```

3. **Update frontend to use new backend port:**
   - Nginx will still route to backend:5000 internally
   - No changes needed!

### Cannot Connect to Docker Daemon

**Error:** `Cannot connect to the Docker daemon`

**Solutions:**

1. **Start Docker Desktop:**
   - Mac: Check menu bar for Docker icon
   - Linux: `sudo systemctl start docker`
   - Windows: Start Docker Desktop

2. **Check Docker status:**
   ```bash
   docker info
   docker ps
   ```

### Container Exits Immediately

**Check logs:**
```bash
docker-compose logs backend
docker-compose logs frontend
```

**Common causes:**

1. **Port conflict** - See "Port Already in Use" above
2. **Missing dependencies** - Rebuild: `docker-compose build --no-cache`
3. **Syntax error** - Check application logs

### Out of Disk Space

**Error:** `no space left on device`

**Solutions:**

1. **Clean Docker resources:**
   ```bash
   docker system prune -a
   docker volume prune
   ```

2. **Check disk space:**
   ```bash
   df -h
   ```

3. **Clear uploads/temp:**
   ```bash
   rm -rf backend/uploads/*
   rm -rf backend/temp/*
   ```

## Frontend Issues

### Blank Page / White Screen

**Solutions:**

1. **Check browser console:**
   - Open DevTools (F12)
   - Look for JavaScript errors

2. **Clear browser cache:**
   - Hard refresh: Ctrl+Shift+R (Cmd+Shift+R on Mac)
   - Or: Settings → Clear Cache

3. **Rebuild frontend:**
   ```bash
   docker-compose up --build frontend
   ```

### Charts Not Rendering

**Symptoms:** See data but no graphs appear

**Solutions:**

1. **Check browser console** for errors

2. **Verify Recharts installed:**
   ```bash
   cd frontend
   npm list recharts
   ```

3. **Reinstall dependencies:**
   ```bash
   cd frontend
   rm -rf node_modules package-lock.json
   npm install
   ```

4. **Try different browser** (Chrome, Firefox, Safari)

### API Connection Failed

**Error:** `Network Error` or `ERR_CONNECTION_REFUSED`

**Solutions:**

1. **Check backend is running:**
   ```bash
   docker-compose ps
   curl http://localhost:5000/api/health
   ```

2. **Check backend logs:**
   ```bash
   docker-compose logs backend
   ```

3. **Verify network connectivity:**
   ```bash
   docker-compose exec frontend ping backend
   ```

## Backend Issues

### Python Import Errors

**Error:** `ModuleNotFoundError: No module named 'regex'`

**Solutions:**

1. **Rebuild backend:**
   ```bash
   docker-compose build --no-cache backend
   ```

2. **Verify requirements.txt:**
   ```bash
   cat backend/requirements.txt
   ```

3. **Check Python version:**
   ```bash
   docker-compose exec backend python --version
   # Should be Python 3.9+
   ```

### lula2.py Errors

**Error:** Issues from the original script

**Solutions:**

1. **Check lula2.py is copied to backend:**
   ```bash
   ls -la backend/lula2.py
   ```

2. **Verify file permissions:**
   ```bash
   chmod +x backend/lula2.py
   ```

3. **Test lula2.py directly:**
   ```bash
   docker-compose exec backend python lula2.py --help
   ```

### File Permission Errors

**Error:** `Permission denied` when creating uploads/temp

**Solutions:**

1. **Check directory permissions:**
   ```bash
   ls -la backend/
   ```

2. **Create directories manually:**
   ```bash
   mkdir -p backend/uploads backend/temp
   chmod 777 backend/uploads backend/temp
   ```

3. **Run Docker as root (not recommended):**
   ```yaml
   backend:
     user: root
   ```

## Performance Issues

### Slow Upload

**Causes:**
- Large file size
- Slow network
- Low disk speed

**Solutions:**

1. **Check file size:**
   ```bash
   ls -lh your-file.tar.bz2
   ```

2. **Monitor upload progress** in browser DevTools → Network tab

3. **Compress log files more:**
   ```bash
   tar -cjf logs.tar.bz2 logs/
   # Or use higher compression
   tar -c logs/ | bzip2 -9 > logs.tar.bz2
   ```

### Slow Processing

**Solutions:**

1. **Use simpler parse modes** (`known`, `error`)
2. **Filter by date range** to process less data
3. **Increase Docker resources:**
   - Docker Desktop → Preferences → Resources
   - Increase CPUs and Memory

## Development Issues

### Hot Reload Not Working

**Backend:**
```bash
# Set Flask debug mode
export FLASK_ENV=development
export FLASK_DEBUG=1
python backend/app.py
```

**Frontend:**
```bash
cd frontend
npm start
```

### Module Not Found in Development

**Backend:**
```bash
cd backend
pip install -r requirements.txt
```

**Frontend:**
```bash
cd frontend
npm install
```

## Getting More Help

### Enable Debug Logging

**Backend (app.py):**
```python
app.run(host='0.0.0.0', port=5000, debug=True)
```

**Docker:**
```bash
docker-compose logs -f
```

### Collect Diagnostic Info

```bash
# System info
docker --version
docker-compose --version
docker info

# Container status
docker-compose ps

# Logs
docker-compose logs backend > backend.log
docker-compose logs frontend > frontend.log

# Network
docker-compose exec frontend ping backend
curl http://localhost:5000/api/health
curl http://localhost:3000
```

### Clean Slate Restart

When all else fails:

```bash
# Stop everything
docker-compose down -v

# Remove all Docker resources
docker system prune -a --volumes

# Rebuild from scratch
docker-compose build --no-cache
docker-compose up
```

## Still Having Issues?

1. **Check the logs** - Most errors show up there
2. **Review the error message** - It usually hints at the solution
3. **Search this guide** - Use Ctrl+F to find keywords
4. **Check Docker/React/Flask documentation** - For framework-specific issues

---

**Most common fix:** `docker-compose down && docker-compose up --build`
