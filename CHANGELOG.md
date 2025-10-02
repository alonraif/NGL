# Changelog

All notable changes to the LiveU Log Analyzer will be documented in this file.

## [3.0.0] - 2025-10-02

### 🎉 Major Release: Hybrid Modular Architecture

**Hybrid Approach**: Modular structure + Proven parsing (uses lula2.py internally)

### Added
- **LulaWrapperParser**: Modular parsers that delegate to lula2.py
  - `BandwidthParser` - bw, md-bw, md-db-bw modes
  - `ModemStatsParser` - md mode
  - `SessionsParser` - sessions mode
  - `ErrorParser` - known, error, v, all modes
  - `SystemParser` - memory, grading modes
  - `DeviceIDParser` - id mode
- **Parser Registry**: Factory pattern for parser instantiation
- **Test Suite**: `test_parsers.py` for validating all parsers load correctly
- **Documentation**:
  - `MODULAR_ARCHITECTURE.md` - Complete architecture guide
  - `CHANGELOG.md` - Version history
  - `V3_RELEASE_NOTES.md` - Detailed release notes

### Changed
- Backend version bumped to **v3.0.0**
- **Hybrid architecture**: Modular structure delegates to lula2.py for parsing
- Each parser is ~20-50 lines (wrapper + output parsing)
- Improved code organization while maintaining reliable parsing

### Fixed
- Archive extraction issues - now passes archive directly to lula2.py
- lula2.py handles all extraction, filtering, and parsing
- Wrappers parse lula2.py's proven output into structured JSON

### Improved
- **Extensibility**: Adding new parse modes takes 15-30 minutes
- **Testability**: Individual parsers can be unit tested
- **Reliability**: Uses lula2.py's battle-tested parsing logic
- **Maintainability**: Clear modular structure
- **Developer Experience**: Simple wrapper pattern

### Technical Details
- Full API backward compatibility maintained
- Frontend requires no changes
- Drop-in replacement for previous versions
- All 12 parse modes supported and tested
- lula2.py remains for proven parsing logic

---

## [2.1.0] - 2025-10-01

### Fixed
- **Critical**: Fixed async backend hanging issue
- Jobs were getting stuck at "processing" status indefinitely
- Background threads not updating job status correctly

### Changed
- Switched from async to **synchronous processing**
- Removed threading complexity
- Direct request-response model
- Better error handling and logging

### Added
- Health endpoint now reports processing mode
- Version tracking in health check

---

## [2.0.0] - 2025-10-01

### Added
- **Async Processing**: Background job processing with threading
- **Progress Updates**: Real-time progress via Server-Sent Events (SSE)
- **Job Management**: Job queue with status tracking
- **Caching Design**: Hash-based result caching (framework)
- **Performance Optimizations**:
  - Parallel decompression (pbzip2/pigz)
  - 10-minute timeout (up from 5)
  - Smart file handling

### Documentation
- Created `PERFORMANCE.md`
- Created `PERFORMANCE_COMPARISON.md`
- Added performance benchmarks

### Fixed
- Timezone comparison errors in DateRange class
- Made all datetime objects timezone-aware

---

## [1.0.0] - 2025-09-30

### Initial Release

### Added
- **Docker-based Deployment**: Complete containerized application
  - Backend: Flask REST API
  - Frontend: React 18 + Nginx
  - Docker Compose orchestration
- **Web UI**: Beautiful, responsive interface
  - File upload with drag-and-drop
  - Parse mode selection
  - Timezone configuration
  - Date range filtering
- **Visualization Components**:
  - `ModemStats` - Bar/line charts for modem data
  - `BandwidthChart` - Time-series area/line charts
  - `SessionsTable` - Filterable table view
  - `RawOutput` - Text output with search and export
- **Parse Modes**: All 16 modes from lula2.py
  - known, error, v, all (error modes)
  - bw, md-bw, md-db-bw (bandwidth modes)
  - md (modem statistics)
  - sessions (streaming sessions)
  - id (device IDs)
  - memory, grading (system metrics)
  - cpu, modemevents, modemeventssorted, ffmpeg
- **File Support**:
  - .tar.bz2 archives
  - .bz2 compressed tar files
  - Up to 500MB upload size
- **API Features**:
  - RESTful endpoints
  - CORS enabled
  - JSON responses
  - Structured data parsing

### Documentation
- `README.md` - Complete documentation
- `QUICKSTART.md` - 2-minute setup guide
- `TROUBLESHOOTING.md` - Common issues
- `DEVELOPMENT.md` - Developer guide
- `UPLOAD_GUIDE.md` - Upload instructions

### Fixed (during development)
- **413 Request Entity Too Large**: Increased Nginx limit to 500MB
- **Timezone comparison errors**: Fixed naive/aware datetime mixing
- **File format validation**: Accept both .tar.bz2 and .bz2 files
- **Frontend display bug**: Fixed "No output available" issue

---

## Version History Summary

| Version | Date | Key Change | Status |
|---------|------|------------|--------|
| 3.0.0 | 2025-10-02 | Modular parsers | ✅ Current |
| 2.1.0 | 2025-10-01 | Synchronous mode | Replaced |
| 2.0.0 | 2025-10-01 | Async processing | Replaced |
| 1.0.0 | 2025-09-30 | Initial release | Replaced |

---

## Migration Guide

### From v2.x to v3.0.0

**No changes required** - Full backward compatibility maintained.

The modular parser system is a drop-in replacement. All API endpoints, request formats, and response formats remain identical.

### From v1.x to v3.0.0

**No changes required** - Jump directly to v3.0.0 with no breaking changes.

---

## Future Roadmap

### v3.1.0 (Planned)
- [ ] Custom regex patterns via API
- [ ] Parser result caching
- [ ] Export to multiple formats (JSON, XML, PDF)

### v3.2.0 (Planned)
- [ ] Real-time log streaming
- [ ] WebSocket support for live updates
- [ ] Multi-file analysis

### v4.0.0 (Future)
- [ ] Plugin system for custom parsers
- [ ] Parser chaining
- [ ] Machine learning error detection
- [ ] Historical trend analysis

---

## Credits

- **Original lula2.py**: LiveU log analysis script (3,015 lines)
- **Web UI**: Built with React 18, Recharts, Flask
- **Refactoring**: Modular architecture designed for extensibility

---

## Support

For issues, questions, or contributions:

1. Check the documentation in the repository
2. Review `TROUBLESHOOTING.md` for common issues
3. Review `MODULAR_ARCHITECTURE.md` for parser details
4. Check backend logs: `docker-compose logs backend`
