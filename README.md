# 🎥 NGL - Next Gen LULA

**Next Generation LiveU Log Analyzer** - A beautiful, modern web-based interface for analyzing LiveU device logs with interactive visualizations and real-time data insights.

![Version](https://img.shields.io/badge/Version-3.0.0-brightgreen)
![Docker](https://img.shields.io/badge/Docker-Enabled-blue)
![React](https://img.shields.io/badge/React-18.2-61dafb)
![Flask](https://img.shields.io/badge/Flask-3.0-black)
![Python](https://img.shields.io/badge/Python-3.9-yellow)
![Architecture](https://img.shields.io/badge/Architecture-Modular-orange)

## ✨ Features

### 📊 **Interactive Visualizations**
- **Modem Statistics**: Bar charts and line graphs showing bandwidth, packet loss, and delay metrics
- **Modem Bandwidth Analysis**: Per-modem bandwidth and RTT charts with aggregated totals
- **Stream Bandwidth Analysis**: Time-series charts for stream and data bridge bandwidth
- **Session Tracking**: Complete/incomplete session detection with duration calculation, chronological sorting, and filtering
- **Memory Usage Analysis**: Component-based time-series charts (VIC, Corecard, Server) with warning detection and detailed stats
- **Modem Grading Visualization**: Service level transitions timeline, quality metrics tracking, per-modem health monitoring
- **Real-time Charts**: Dynamic graphs using Recharts library

### 🎨 **Beautiful UI**
- Modern gradient design with smooth animations
- Drag-and-drop file upload
- Responsive layout (mobile-friendly)
- Tabbed interface for easy navigation
- Color-coded status indicators

### 🔧 **Powerful Analysis**
- 19+ parsing modes (modem stats, bandwidth, sessions, CPU, memory, etc.)
- Timezone support (US/Eastern, UTC, and more)
- Date range filtering
- Search and filter capabilities
- Export results (download/copy)

### 🔒 **Security & Operations**
- Role-based access with auditable JWT sessions
- Automated HTTPS management (Let’s Encrypt issuance, custom certificate uploads, HSTS enforcement)
- Celery powered scheduled tasks (cleanup, SSL renewal, health checks)
- Fine-grained parser visibility controls for admins

### 🐳 **Docker-Based**
- One-command deployment
- Isolated containers for backend and frontend
- Persistent data volumes
- Easy scaling

### 🏗️ **Modular Architecture** (NEW v3.0!)
- **Modular parser system** - each parse mode is a separate module
- **No dependency on monolithic lula2.py** (eliminated 3,015 lines)
- **Easy extensibility** - add new parse modes in minutes
- **Better testability** - individual parsers can be unit tested
- **6x smaller code** - each parser is ~50-100 lines vs ~250 lines
- See [MODULAR_ARCHITECTURE.md](MODULAR_ARCHITECTURE.md) for details

## 🚀 Quick Start

### Prerequisites

- Docker (version 20.10+)
- Docker Compose (version 2.0+)

### Installation

1. **Clone or navigate to the project directory:**
   ```bash
   cd /path/to/ngl
   ```

2. **Configure environment (first run only):**
   ```bash
   cp .env.example .env
   # Edit .env and provide secure values (JWT secret, DB password, CORS origins, etc.)
   ```

3. **Start the application:**
   ```bash
   docker-compose up --build
   ```

4. **Apply database migrations and seed the admin user:**
   ```bash
   docker-compose exec backend alembic upgrade head
   docker-compose exec backend python3 init_admin.py
   ```

5. **Access the web interface:**
   - Open your browser to: **http://localhost:3000**
   - Backend API runs on: **http://localhost:5000**
   - Sign in with the seeded admin account (`admin` / `Admin123!`, then change the password)

6. **Stop the application:**
   ```bash
   docker-compose down
   ```

## 📚 Documentation

- [GETTING_STARTED.md](GETTING_STARTED.md) – End-to-end local setup checklist
- [LINUX_DEPLOYMENT_MANUAL.md](LINUX_DEPLOYMENT_MANUAL.md) – Production deployment on Linux with HTTPS
- [SECURITY_DEPLOYMENT_GUIDE.md](SECURITY_DEPLOYMENT_GUIDE.md) – Hardening steps and SSL operations
- [DEVELOPMENT.md](DEVELOPMENT.md) – Local development workflows

## 📖 Usage Guide

You must be signed in to access the application. The default admin user is created via `init_admin.py`. Public self-registration is disabled; admins can add or reset users from the **Admin → Users** tab.

### Uploading Log Files

1. **Drag & Drop** or **Click** the upload area
2. Select a `.tar.bz2` log file from your LiveU device
3. Choose your analysis options:
   - **Parse Mode**: Select the type of analysis
   - **Timezone**: Set your preferred timezone
   - **Date Range** (optional): Filter logs by date/time

4. Click **"Analyze Log"** to process

### Parse Modes

| Mode | Description | Visualization |
|------|-------------|---------------|
| `known` | Known errors and events (default) | Raw output |
| `error` | All ERROR lines | Raw output |
| `v` | Verbose (includes common errors) | Raw output |
| `all` | All log lines | Raw output |
| `bw` | Stream bandwidth | Time-series charts |
| `md-bw` | Modem bandwidth | Per-modem bandwidth/RTT + aggregated total |
| `md-db-bw` | Data bridge bandwidth | Time-series charts |
| `md` | Modem statistics | Bar/Line charts + tables |
| `sessions` | Session summaries | Stats cards + chronologically sorted table with complete/incomplete sessions, start/end times, durations |
| `id` | Device/server IDs | Raw output |
| `memory` | Memory usage | Interactive time-series charts per component (VIC/Corecard/Server), stats cards, detailed table |
| `grading` | Modem service levels | Service level timeline, quality metrics charts, per-modem stats cards, event history table |
| `cpu` | CPU usage | Raw output |
| `modemevents` | Modem connectivity events | Raw output |
| `modemeventssorted` | Connectivity by modem | Raw output |
| `ffmpeg` | FFmpeg logs | Raw output |

### Viewing Results

The results interface has three tabs:

1. **📊 Visualization**: Interactive charts and graphs
   - Summary statistics cards
   - Dynamic charts (bar, line, area)
   - Per-modem analysis with bandwidth and RTT metrics (md-bw mode)
   - Aggregated bandwidth totals
   - Session tables with chronological sorting and filtering by type
   - Detailed data tables

2. **📝 Raw Output**: Full text output
   - Search functionality
   - Download as .txt file
   - Copy to clipboard

3. **⚠️ Errors**: Error messages (if any)

### Sessions Parser Details

The `sessions` parse mode provides comprehensive session tracking:

**Visualization Features:**
- **Summary Cards**: Total sessions, complete sessions count, incomplete sessions count
- **Session Types**:
  - `Complete`: Sessions with both start and end timestamps
  - `Start Only`: Sessions that began but have no recorded end
  - `End Only`: Sessions with an end timestamp but no recorded start
- **Filtering**: Filter table by All Sessions, Complete Only, Start Only, or End Only
- **Chronological Sorting**: Sessions sorted by timestamp (not session ID)
- **Duration Calculation**: Automatic duration calculation for complete sessions

**Data Displayed:**
- Session ID
- Session type (color-coded badge)
- Start timestamp
- End timestamp
- Duration (for complete sessions)

**Known Limitations:**
- Session metadata extraction (server info, network config, timing metrics, active modems) is currently disabled due to performance constraints with large compressed archives
- Future optimization planned to enable detailed metadata visualization

### Memory Parser Details

The `memory` parse mode provides comprehensive memory usage analysis with interactive visualizations:

**Visualization Features:**
- **Component-Based Analysis**: Separate tracking for VIC, Corecard, and Server components
- **Summary Cards**:
  - Average, max, and min memory usage percentages
  - Peak memory usage in MB
  - Warning count per component
  - Total data points collected
- **Interactive Time-Series Chart**:
  - Line chart showing memory usage over time
  - Filter by component (click cards to toggle)
  - Warning threshold line at 80%
  - Color-coded by component
- **Detailed Data Table**:
  - Timestamp, component, usage %, used MB, total MB, cached MB
  - Warning indicators (highlighted rows)
  - First 100 data points displayed
  - Filterable by selected component

**Data Displayed:**
- Memory usage percentage (always available)
- Used memory (MB) - when available in detailed logs
- Total memory (MB) - when available in detailed logs
- Cached memory (MB) - when available in detailed logs
- Warning status
- Timestamp for each measurement

**Supported Components:**
- **VIC**: Video Input Card memory monitoring
- **Corecard**: Corecard component memory monitoring
- **Server**: Server-side memory monitoring

**Supported Log Formats:**
- Simple percentage: `COR: 7.8%` or `VIC: 25.7%`
- Detailed format: `25.7% (531 MB out of 2069 MB), cached - 145 MB`
- Warning format: `Memory usage is too high: 95.7%`

### Modem Grading Parser Details

The `grading` parse mode provides modem service level monitoring with interactive visualizations:

**Visualization Features:**
- **Per-Modem Summary Cards**:
  - Current service level (Full/Limited)
  - Service change counts
  - Quality metric counts (good/bad)
  - Color-coded borders (green for Full, red for Limited)
  - Click to filter timeline/charts
- **Service Level Timeline Chart**:
  - Step chart showing service transitions over time
  - Visual representation of Full Service (1) vs Limited Service (0)
  - Interactive tooltips with timestamps
  - Filterable by modem
- **Quality Metrics Bar Chart**:
  - Two metrics displayed as bars
  - Color-coded by quality status (green=good, red=bad)
  - First 50 measurements shown
  - Filterable by modem
- **Service Change Events Table**:
  - Chronological list of service level changes
  - Highlighted rows for Limited Service events
  - Timestamps and modem IDs
  - First 100 events displayed

**Data Displayed:**
- Service level transitions (Full ↔ Limited)
- Quality metrics (numeric values with status)
- Event timestamps
- Per-modem statistics

**Event Types:**
- **Service Change**: Modem transitions between Full and Limited service
- **Quality Metric**: Numeric quality measurements with threshold evaluation

**Typical Log Pattern:**
```
ModemID 0 Full Service
ModemID 0 126 86 Good enough for full service
ModemID 0 539 490 Not good enough for full service
ModemID 0 Limited Service
```

## 🏗️ Architecture

```
┌─────────────────────────────────────────┐
│           Docker Compose                │
├─────────────────┬───────────────────────┤
│   Frontend      │      Backend          │
│   (React)       │      (Flask)          │
│   Port: 3000    │      Port: 5000       │
│   + Nginx       │      + lula2.py       │
└─────────────────┴───────────────────────┘
         │                    │
         └────────────────────┘
              Network Bridge
```

### Components

**Frontend (React)**
- Modern React 18 application
- Recharts for data visualization
- React Dropzone for file uploads
- Axios for API communication
- Nginx for production serving

**Backend (Flask)**
- RESTful API
- Wraps original `lula2.py` script
- Parses and structures output data
- File upload handling

**Docker**
- Multi-stage builds for optimization
- Persistent volumes for uploads/temp files
- Network isolation

## 🛠️ Development

### Project Structure

```
ngl/
├── docker-compose.yml          # Docker orchestration
├── lula2.py                    # Original log analyzer script
├── backend/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── app.py                  # Flask API
│   └── lula2.py                # Copy of analyzer
└── frontend/
    ├── Dockerfile
    ├── nginx.conf
    ├── package.json
    ├── public/
    │   └── index.html
    └── src/
        ├── App.js
        ├── App.css
        ├── index.js
        ├── index.css
        └── components/
            ├── FileUpload.js
            ├── Results.js
            ├── ModemStats.js
            ├── BandwidthChart.js
            ├── ModemBandwidthChart.js
            ├── SessionsTable.js
            └── RawOutput.js
```

### Running in Development Mode

**Backend (with hot reload):**
```bash
cd backend
pip install -r requirements.txt
python app.py
```

**Frontend (with hot reload):**
```bash
cd frontend
npm install
npm start
```

### Building for Production

```bash
docker-compose up --build -d
```

## 🔌 API Endpoints

### `GET /api/health`
Health check endpoint

**Response:**
```json
{
  "status": "healthy",
  "version": "3.0.0",
  "mode": "modular",
  "features": ["modular-parsers", "no-lula2-dependency"]
}
```

### `GET /api/parse-modes`
Get available parsing modes

**Response:**
```json
[
  {
    "value": "known",
    "label": "Known Errors (Default)",
    "description": "Small set of known errors and events"
  },
  ...
]
```

### `POST /api/upload`
Upload and analyze log file

**Parameters:**
- `file` (multipart/form-data): Log file (.tar.bz2)
- `parse_mode` (form): Parse mode (default: "known")
- `timezone` (form): Timezone (default: "US/Eastern")
- `begin_date` (form, optional): Start date filter
- `end_date` (form, optional): End date filter

**Response:**
```json
{
  "success": true,
  "output": "Raw output text...",
  "error": null,
  "parsed_data": [...],
  "parse_mode": "md",
  "filename": "log.tar.bz2"
}
```

## 🐛 Troubleshooting

### Port Already in Use
If ports 3000 or 5000 are already in use, modify `docker-compose.yml`:
```yaml
ports:
  - "3001:80"  # Change frontend port
  - "5001:5000"  # Change backend port
```

### File Upload Fails
- Check file size (max 500MB)
- Ensure file is `.tar.bz2` format
- Check backend logs: `docker-compose logs backend`

### Charts Not Displaying
- Verify parsed_data is returned from backend
- Check browser console for errors
- Ensure parse mode supports visualization

### Docker Build Issues
```bash
# Clean rebuild
docker-compose down -v
docker-compose build --no-cache
docker-compose up
```

## 🏗️ Modular Architecture (v3.0)

The application now uses a **modular parser architecture** that eliminates dependency on the monolithic `lula2.py` script.

### Parser Structure

```
backend/parsers/
├── base.py              # BaseParser abstract class
├── bandwidth.py         # BandwidthParser (bw, md-bw, md-db-bw)
├── modem_stats.py       # ModemStatsParser (md)
├── sessions.py          # SessionsParser (sessions)
├── errors.py            # ErrorParser (known, error, v, all)
├── system.py            # SystemParser (memory, grading)
└── device_id.py         # DeviceIDParser (id)
```

### Adding a New Parser

**Quick Start** (3 steps, ~30 minutes):

1. Add parser class to `backend/parsers/lula_wrapper.py`
2. Register in `backend/parsers/__init__.py`
3. Add to `PARSE_MODES` in `backend/app.py`

**Resources:**
- 📖 [PARSER_DEVELOPMENT.md](PARSER_DEVELOPMENT.md) - Quick reference guide
- 📚 [MODULAR_ARCHITECTURE.md](MODULAR_ARCHITECTURE.md) - Complete documentation
- 📋 [CHANGELOG.md](CHANGELOG.md) - Version history

### Benefits

- **Hybrid approach**: Modular structure + proven lula2.py parsing
- **Quick development**: Add new modes in 15-30 minutes
- **Reliable parsing**: Uses battle-tested lula2.py logic
- **Easy testing**: Unit test each parser wrapper
- **Clear organization**: One parser class per mode

## 📝 License

This project extends the original `lula2.py` script (version 4.2) with a modern web interface.

## 🤝 Contributing

Contributions welcome! Areas for improvement:
- Additional parser modules for new log types
- Real-time streaming of log processing
- User authentication
- Log history/database storage
- Advanced filtering options
- Export to PDF/Excel
- Session metadata extraction optimization (server info, network config, timing metrics, active modems)

## 📧 Support

For issues or questions:
1. Check the troubleshooting section
2. Review application logs: `docker-compose logs`
3. Open an issue with log details and steps to reproduce

---

**Built with ❤️ using React, Flask, and Docker**
