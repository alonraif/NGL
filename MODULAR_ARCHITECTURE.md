# Modular Parser Architecture

## Overview

The LiveU Log Analyzer uses a **hybrid modular architecture**:
- **Modular structure**: Each parse mode has its own dedicated parser class
- **Proven parsing**: Delegates to `lula2.py` for actual log parsing (battle-tested)
- **Best of both worlds**: Easy extensibility + reliable parsing

This provides a clean, maintainable codebase while leveraging lula2.py's 3,015 lines of proven parsing logic.

## Architecture

```
backend/
├── app.py                    # Main Flask application (v3.0.0)
├── lula2.py                  # Original parsing script (3,015 lines)
├── parsers/
│   ├── __init__.py          # Parser registry and factory
│   ├── base.py              # BaseParser abstract class
│   ├── lula_wrapper.py      # LulaWrapperParser - delegates to lula2.py
│   ├── bandwidth.py         # [Legacy] Native BandwidthParser
│   ├── modem_stats.py       # [Legacy] Native ModemStatsParser
│   ├── sessions.py          # [Legacy] Native SessionsParser
│   ├── errors.py            # [Legacy] Native ErrorParser
│   ├── system.py            # [Legacy] Native SystemParser
│   └── device_id.py         # [Legacy] Native DeviceIDParser
└── test_parsers.py          # Parser test suite
```

**Active Parsers**: All parsers in `lula_wrapper.py` (used in production)
**Legacy Parsers**: Native implementations in individual files (for reference/future use)

## Benefits

### 1. **Modularity**
- Each parse mode is self-contained
- Easy to understand and maintain individual parsers
- Clear separation of concerns

### 2. **Extensibility**
- Adding a new parse mode = creating a new parser class
- No need to modify 3,000+ lines of code
- Simple plugin architecture

### 3. **Testability**
- Each parser can be unit tested independently
- Mock data can be created for specific parsers
- Easier to debug issues

### 4. **Performance**
- Only load parsing logic needed for the selected mode
- Can optimize individual parsers without affecting others
- Potential for parallel processing in the future

### 5. **Maintainability**
- Smaller, focused code files
- Easier to onboard new developers
- Clear code organization

## Parser Classes

### LulaWrapperParser (Current Implementation)

**All current parsers inherit from `LulaWrapperParser`** which:
- Delegates parsing to `lula2.py` (proven, battle-tested logic)
- Parses lula2.py's output into structured data
- Provides modular structure with reliable parsing

**Key Implementation Details:**
- **Does NOT extract archives** - passes archive file directly to lula2.py
- lula2.py handles extraction, parsing, and date filtering
- Wrapper parses lula2.py's text/CSV output into JSON

```python
from parsers.lula_wrapper import LulaWrapperParser

class MyParser(LulaWrapperParser):
    def parse_output(self, output):
        # Parse lula2.py's output into structured data
        return {
            'parsed_field': 'value',
            ...
        }

    # process() method is inherited - calls lula2.py with archive file
```

**Important**: Override `process()`, not `parse()`. The wrapper calls lula2.py with the archive file directly, not an extracted directory.

### BaseParser (Legacy/Future)

The original `BaseParser` is available for native implementations:
- **Archive extraction**: Automatic handling of `.bz2`, `.tar.bz2`, `.gz`, `.tar.gz`
- **Log file discovery**: Finds `messages.log` in extracted archives
- **Cleanup**: Automatic temporary file cleanup

**Use this when**: Building a native parser that reads messages.log directly (future enhancement)

### BandwidthParser

**Modes**: `bw`, `md-bw`, `md-db-bw`

**Purpose**: Extract bandwidth information from logs

**Output Format**:
```python
{
    'raw_output': 'datetime,total bitrate,video bitrate,notes\n...',
    'parsed_data': [
        {
            'datetime': '2025-09-23 11:41:31',
            'total bitrate': '3350',
            'video bitrate': '2293',
            'notes': ''
        },
        ...
    ]
}
```

### ModemStatsParser

**Mode**: `md`

**Purpose**: Extract modem statistics (signal, throughput)

**Output Format**:
```python
{
    'raw_output': 'Modem 1: Type=LTE, Signal=-75dBm...',
    'parsed_data': [
        {
            'modem_id': '1',
            'type': 'LTE',
            'avg_signal': -75.3,
            'min_signal': -90,
            'max_signal': -60,
            'avg_throughput': 4200,
            'sample_count': 150
        },
        ...
    ]
}
```

### SessionsParser

**Mode**: `sessions`

**Purpose**: Extract streaming session information

**Output Format**:
```python
{
    'raw_output': 'Session started at 2025-09-23 11:00:00...',
    'parsed_data': [
        {
            'start_time': '2025-09-23 11:00:00',
            'end_time': '2025-09-23 12:30:00',
            'duration': 5400,
            'session_id': 'abc-123',
            'avg_bitrate': 4000
        },
        ...
    ]
}
```

### ErrorParser

**Modes**: `known`, `error`, `v`, `all`

**Purpose**: Filter log lines by error patterns

**Patterns**:
- `known`: Small set of known errors (error, failed, timeout, etc.)
- `error`: Any line containing "ERROR"
- `v`: Verbose - includes warnings, retries, etc.
- `all`: All log lines

**Output Format**:
```python
{
    'raw_output': 'line1\nline2\n...',
    'parsed_data': {
        'total_lines': 50000,
        'matched_lines': 234,
        'mode': 'known',
        'lines': ['error line 1', 'error line 2', ...]
    }
}
```

### SystemParser

**Modes**: `memory`, `grading`

**Purpose**: Extract system metrics

**Output Format (memory)**:
```python
{
    'raw_output': '2025-09-23 11:00:00 Memory: 256 MB\n...',
    'parsed_data': [
        {
            'datetime': '2025-09-23 11:00:00',
            'memory_mb': 256.0,
            'original_value': '256 MB'
        },
        ...
    ]
}
```

### DeviceIDParser

**Mode**: `id`

**Purpose**: Extract device and server identification

**Output Format**:
```python
{
    'raw_output': 'Boss ID: 12345\nDevice ID: abc-def\n...',
    'parsed_data': {
        'boss_id': '12345',
        'device_id': 'abc-def',
        'server_id': 'server-001',
        'serial_number': 'SN-789456'
    }
}
```

## Adding a New Parser

### Two Approaches

#### Approach 1: Wrapper (Recommended - Easiest)

**When to use**: When lula2.py already supports the mode (most common)

**Step 1**: Add parser to `lula_wrapper.py`:

```python
class MyParser(LulaWrapperParser):
    """Parser for mymode"""

    def parse_output(self, output):
        """Parse lula2.py output into structured data"""
        # Parse text/CSV output from lula2.py
        lines = output.strip().split('\n')

        data = []
        for line in lines:
            # Your parsing logic here
            data.append({'field': line.strip()})

        return data
```

**Step 2**: Register in `backend/parsers/__init__.py`:

```python
from .lula_wrapper import MyParser

PARSERS = {
    ...
    'mymode': MyParser,
}
```

**Step 3**: Add to `backend/app.py`:

```python
PARSE_MODES = [
    ...
    {'value': 'mymode', 'label': 'My Mode', 'description': 'Description here'},
]
```

**Step 4**: Test:

```bash
docker-compose exec backend python3 /app/test_parsers.py
# Then test with real file upload
```

**That's it!** lula2.py handles extraction, parsing, and filtering. You just parse its output.

---

#### Approach 2: Native Parser (Advanced - Future)

**When to use**: For new log formats not supported by lula2.py

**Step 1**: Create `backend/parsers/myparser.py`:

```python
from .base import BaseParser

class MyParser(BaseParser):
    """Native parser for custom log format"""

    def parse(self, log_path, timezone='US/Eastern', begin_date=None, end_date=None):
        """
        Parse custom data from messages.log directly

        Args:
            log_path: Path to extracted messages.log file
        """
        data = []

        with open(log_path, 'r', encoding='utf-8', errors='ignore') as f:
            for line in f:
                # Your custom parsing logic
                if 'my_pattern' in line:
                    data.append(line.strip())

        return {
            'raw_output': '\n'.join(data),
            'parsed_data': data
        }
```

**Step 2-4**: Same registration steps as Approach 1

**Note**: This approach requires implementing:
- Date filtering logic
- Timezone conversion
- Error handling
- All parsing from scratch

---

### Key Differences

| Aspect | Wrapper Approach | Native Approach |
|--------|------------------|-----------------|
| **Complexity** | Low - just parse output | High - parse raw logs |
| **Code needed** | ~20-50 lines | ~100-300 lines |
| **Extraction** | lula2.py handles it | You implement it |
| **Date filtering** | lula2.py handles it | You implement it |
| **Timezone** | lula2.py handles it | You implement it |
| **When to use** | Mode exists in lula2.py | New log format |

**Recommendation**: Start with Approach 1 (Wrapper). Only use Approach 2 for completely new log formats.

## Migration from lula2.py

### Before (lula2.py approach)
```python
# 3,015 lines of monolithic code
# All modes in one file
# Hard to extend or modify
# Difficult to test individual modes
```

### After (Modular approach)
```python
# ~50-100 lines per parser
# Each mode is independent
# Easy to add new modes
# Simple to test and debug
```

## Testing

Run the test suite:

```bash
# Inside container
docker-compose exec backend python3 /app/test_parsers.py

# Or from host
docker-compose exec backend python3 -c "from parsers import get_parser; print(get_parser('bw'))"
```

## Future Enhancements

1. **Async Processing**: Use Python's `asyncio` for parallel log parsing
2. **Streaming Parsers**: Process large files without loading into memory
3. **Plugin System**: Load parsers from external packages
4. **Parser Chaining**: Combine multiple parsers in one request
5. **Custom Regex**: Allow users to define custom patterns via API
6. **Parser Caching**: Cache frequently used parse results

## Performance Comparison

| Metric | lula2.py | Modular |
|--------|----------|---------|
| Code per mode | ~250 lines | ~50-100 lines |
| Import time | Full script | Only needed parser |
| Test coverage | Difficult | Easy |
| Extend time | Hours | Minutes |
| Debug time | High | Low |

## Version History

- **v1.0.0**: Initial release with lula2.py
- **v2.0.0**: Async processing added
- **v2.1.0**: Synchronous processing for stability
- **v3.0.0**: Modular parser architecture ← **Current**

## Support

For questions or issues with the modular parsers:

1. Check parser test suite: `test_parsers.py`
2. Review individual parser source code in `parsers/`
3. Check backend logs: `docker-compose logs backend`

## Backward Compatibility

The modular architecture maintains **full API compatibility** with previous versions:

- Same REST endpoints
- Same request/response formats
- Same parse mode names
- Drop-in replacement for lula2.py

Existing frontend code requires **no changes**.
