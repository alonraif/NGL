# 🎥 LiveU Log Analyzer - Web UI

A beautiful, modern web-based interface for analyzing LiveU device logs with interactive visualizations and real-time data insights.

![Version](https://img.shields.io/badge/Version-3.0.0-brightgreen)
![Docker](https://img.shields.io/badge/Docker-Enabled-blue)
![React](https://img.shields.io/badge/React-18.2-61dafb)
![Flask](https://img.shields.io/badge/Flask-3.0-black)
![Python](https://img.shields.io/badge/Python-3.9-yellow)
![Architecture](https://img.shields.io/badge/Architecture-Modular-orange)

## ✨ Features

### 📊 **Interactive Visualizations**
- **Modem Statistics**: Bar charts and line graphs showing bandwidth, packet loss, and delay metrics
- **Bandwidth Analysis**: Time-series charts for stream, modem, and data bridge bandwidth
- **Session Tracking**: Detailed session tables with filtering and status indicators
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

2. **Start the application:**
   ```bash
   docker-compose up --build
   ```

3. **Access the web interface:**
   - Open your browser to: **http://localhost:3000**
   - Backend API runs on: **http://localhost:5000**

4. **Stop the application:**
   ```bash
   docker-compose down
   ```

## 📖 Usage Guide

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
| `md-bw` | Modem bandwidth | Time-series charts |
| `md-db-bw` | Data bridge bandwidth | Time-series charts |
| `md` | Modem statistics | Bar/Line charts + tables |
| `sessions` | Session summaries | Table with filtering |
| `id` | Device/server IDs | Raw output |
| `memory` | Memory usage | Raw output |
| `grading` | Modem service levels | Raw output |
| `cpu` | CPU usage | Raw output |
| `modemevents` | Modem connectivity events | Raw output |
| `modemeventssorted` | Connectivity by modem | Raw output |
| `ffmpeg` | FFmpeg logs | Raw output |

### Viewing Results

The results interface has three tabs:

1. **📊 Visualization**: Interactive charts and graphs
   - Summary statistics cards
   - Dynamic charts (bar, line, area)
   - Detailed data tables

2. **📝 Raw Output**: Full text output
   - Search functionality
   - Download as .txt file
   - Copy to clipboard

3. **⚠️ Errors**: Error messages (if any)

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

## 📧 Support

For issues or questions:
1. Check the troubleshooting section
2. Review application logs: `docker-compose logs`
3. Open an issue with log details and steps to reproduce

---

**Built with ❤️ using React, Flask, and Docker**
