# 🚀 Quick Start Guide

Get up and running with LiveU Log Analyzer in 2 minutes!

## Prerequisites Check

Make sure you have Docker installed:
```bash
docker --version
docker-compose --version
```

If not installed, get Docker from: https://docs.docker.com/get-docker/

## Installation & Launch

### Option 1: Using the Start Script (Recommended)

```bash
./start.sh
```

That's it! The script will:
- Build the Docker containers
- Start the application
- Display access URLs
- Remind you to run database migrations and seed the admin user

### Option 2: Manual Docker Compose

```bash
docker-compose up --build
```

### Initial Setup (first run only)

```bash
# Copy the sample environment and customise secrets
cp .env.example .env
# Edit .env to set strong JWT/DB secrets and production CORS origins

# Apply migrations and seed the default admin user
docker-compose exec backend alembic upgrade head
docker-compose exec backend python3 init_admin.py
```

## Access the Application

Once started, open your browser to:

**🌐 http://localhost:3000**

Sign in with the seeded admin account (`admin` / `Admin123!`) and change the password immediately.

## First Analysis

1. **Upload a Log File**
   - Drag & drop a `.tar.bz2` file from your LiveU device
   - Or click the upload area to browse

2. **Select Parse Mode**
   - Start with `Modem Statistics` for visual charts
   - Or try `Sessions` to see streaming sessions

3. **Click "Analyze Log"**
   - Wait for processing (usually 10-60 seconds)
   - View results in the visualization tab

## Example Workflows

### 📊 Analyze Modem Performance
1. Upload log file
2. Select: **"Modem Statistics"**
3. Click: **"Analyze Log"**
4. View: Interactive charts showing bandwidth, loss, and delay

### 🎬 Track Streaming Sessions
1. Upload log file
2. Select: **"Sessions"**
3. Click: **"Analyze Log"**
4. View: Table of all streaming sessions with durations

### 📈 View Bandwidth Over Time
1. Upload log file
2. Select: **"Bandwidth"** (or "Modem Bandwidth")
3. Click: **"Analyze Log"**
4. View: Time-series charts of bandwidth usage

## Stopping the Application

```bash
docker-compose down
```

## Troubleshooting

### "Port already in use" error
```bash
# Stop any running Docker containers
docker-compose down

# Or change ports in docker-compose.yml
```

### "Cannot connect to Docker daemon"
```bash
# Make sure Docker Desktop is running
# On Mac: Check menu bar for Docker icon
# On Linux: sudo systemctl start docker
```

### Container won't build
```bash
# Clean rebuild
docker-compose down -v
docker system prune -a
docker-compose up --build
```

## Next Steps

- Use **Admin → Users** to create regular accounts (self-registration is disabled by default)
- Read the full [README.md](README.md) for detailed documentation
- Explore all 19 parsing modes
- Try date range filtering
- Export and share results

## Need Help?

Check the logs:
```bash
docker-compose logs backend
docker-compose logs frontend
```

---

**Happy Analyzing! 📊**
