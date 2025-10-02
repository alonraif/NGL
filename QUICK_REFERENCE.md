# 📋 Quick Reference Card

## Essential Commands

### Start Application
```bash
./start.sh
# OR
docker-compose up -d
```

### Stop Application
```bash
docker-compose down
```

### Rebuild After Changes
```bash
docker-compose up --build -d
```

### View Logs
```bash
# All logs
docker-compose logs -f

# Backend only
docker-compose logs -f backend

# Frontend only
docker-compose logs -f frontend
```

### Restart Service
```bash
# Restart backend
docker-compose restart backend

# Restart frontend
docker-compose restart frontend
```

### Clean Everything
```bash
docker-compose down -v
docker system prune -a
```

---

## Access URLs

| Service | URL | Description |
|---------|-----|-------------|
| **Frontend** | http://localhost:3000 | Web UI |
| **Backend** | http://localhost:5000 | API Server |
| **Health Check** | http://localhost:5000/api/health | API Status |
| **Parse Modes** | http://localhost:5000/api/parse-modes | Available modes |

---

## Parse Modes Quick Guide

| Mode | Use Case | Visualization |
|------|----------|---------------|
| `known` | Common errors | Text |
| `error` | All errors | Text |
| `md` | **Modem stats** | **📊 Charts** |
| `bw` | **Stream bandwidth** | **📈 Charts** |
| `md-bw` | **Modem bandwidth** | **📈 Charts** |
| `sessions` | **Session tracking** | **📋 Table** |
| `memory` | Memory usage | Text |
| `cpu` | CPU usage | Text |

**Bold** = Has interactive visualizations

---

## File Requirements

### Supported Formats
- `.tar.bz2` (required)

### Size Limits
- **Maximum:** 500MB
- **Recommended:** <100MB for faster processing

### Creating Compatible Files
```bash
# Compress logs directory
tar -cjf logs.tar.bz2 logs/

# With high compression
tar -c logs/ | bzip2 -9 > logs.tar.bz2
```

---

## Troubleshooting Quick Fixes

### Issue: 413 Upload Error
```bash
docker-compose up --build frontend
```

### Issue: Timezone Error
```bash
docker-compose up --build backend
```

### Issue: Blank Page
```bash
# Clear cache
Ctrl+Shift+R (Windows/Linux)
Cmd+Shift+R (Mac)

# Or rebuild
docker-compose up --build frontend
```

### Issue: Connection Failed
```bash
# Check backend
docker-compose ps
curl http://localhost:5000/api/health

# Restart if needed
docker-compose restart backend
```

### Issue: Port Already in Use
```bash
# Find process
lsof -i :3000
lsof -i :5000

# Kill process
kill -9 <PID>

# Or change ports in docker-compose.yml
```

---

## Date Range Filtering

### Format Examples
```
2024-01-01 12:00:00
2024-01-01T12:00:00
2024-01-01 12:00:00+00:00
2024-01-01T12:00:00Z
```

### Timezone Options
- `US/Eastern` (Default)
- `US/Central`
- `US/Pacific`
- `UTC`
- `Europe/London`
- `Asia/Tokyo`

---

## Development

### Run Backend Locally
```bash
cd backend
pip install -r requirements.txt
python app.py
# Access: http://localhost:5000
```

### Run Frontend Locally
```bash
cd frontend
npm install
npm start
# Access: http://localhost:3000
```

### Test API Endpoint
```bash
# Health check
curl http://localhost:5000/api/health

# Get parse modes
curl http://localhost:5000/api/parse-modes

# Upload file
curl -X POST -F "file=@test.tar.bz2" \
     -F "parse_mode=md" \
     http://localhost:5000/api/upload
```

---

## Docker Commands

### Container Management
```bash
# List containers
docker-compose ps

# Stop specific service
docker-compose stop backend

# Remove containers
docker-compose rm -f

# Shell access
docker-compose exec backend bash
docker-compose exec frontend sh
```

### Image Management
```bash
# List images
docker images

# Remove image
docker rmi ngl-backend
docker rmi ngl-frontend

# Rebuild without cache
docker-compose build --no-cache
```

### Volume Management
```bash
# List volumes
docker volume ls

# Remove volumes
docker-compose down -v

# Clean unused volumes
docker volume prune
```

### Logs Management
```bash
# Follow logs
docker-compose logs -f

# Last 50 lines
docker-compose logs --tail=50

# Since timestamp
docker-compose logs --since 2024-01-01T00:00:00
```

---

## Performance Tips

### Faster Uploads
1. Use smaller files (<100MB)
2. Filter by date range
3. Use simple parse modes first

### Faster Processing
1. Close other applications
2. Increase Docker resources
   - Docker Desktop → Settings → Resources
   - Increase CPUs and Memory
3. Use specific parse modes (not `all`)

### Faster Development
1. Use hot reload (npm start)
2. Mount volumes for live editing
3. Use `docker-compose logs -f` to watch changes

---

## File Locations

### Configuration
```
docker-compose.yml       # Docker orchestration
backend/requirements.txt # Python dependencies
frontend/package.json    # Node dependencies
```

### Application Code
```
backend/app.py              # Flask API
backend/lula2.py            # Log analyzer
frontend/src/App.js         # Main React app
frontend/src/components/    # UI components
```

### Data Directories
```
backend/uploads/   # Uploaded files (temporary)
backend/temp/      # Processing workspace
```

---

## Common Workflows

### Analyze Modem Performance
1. Upload `.tar.bz2` file
2. Select **"Modem Statistics"** mode
3. Click **"Analyze Log"**
4. View charts in Visualization tab

### Track Sessions
1. Upload log file
2. Select **"Sessions"** mode
3. View complete/incomplete sessions
4. Filter by status

### Find Errors
1. Upload log file
2. Select **"Error"** mode
3. Search in Raw Output tab
4. Copy or download results

### Export Data
1. After analysis completes
2. Go to **"Raw Output"** tab
3. Click **"Download Output"** or **"Copy to Clipboard"**

---

## Getting Help

1. **Check logs first:** `docker-compose logs -f`
2. **Read error message** - it usually tells you what's wrong
3. **Search TROUBLESHOOTING.md** - most issues are documented
4. **Try clean restart:** `docker-compose down && docker-compose up --build`
5. **Check README.md** for full documentation

---

## Documentation Files

| File | Purpose |
|------|---------|
| `README.md` | Complete documentation |
| `QUICKSTART.md` | 2-minute setup guide |
| `TROUBLESHOOTING.md` | Common issues & solutions |
| `DEVELOPMENT.md` | Developer guide |
| `FEATURES.md` | Feature list |
| `FIXES.md` | Bug fixes applied |
| `QUICK_REFERENCE.md` | This file! |

---

**Tip:** Bookmark this file for quick access! 🔖
