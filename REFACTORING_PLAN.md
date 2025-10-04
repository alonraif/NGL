# Parser Refactoring Plan: Standalone Efficient Parsers

## Executive Summary

**Objective**: Replace subprocess-based `lula2.py` (3,038 lines) with efficient standalone parsers to improve performance and simplify architecture.

**Current State**: All parse modes use `lula_wrapper.py` which spawns `lula2.py` as subprocess, parses text output, then converts to JSON.

**Target State**: Direct in-process parsing using existing standalone parser files.

**Expected Benefits**:
- ✅ 2-5x faster parsing (no subprocess overhead)
- ✅ 50% less memory usage (single-pass parsing)
- ✅ <1s cancellation latency (in-process)
- ✅ Remove 3,934 lines of code
- ✅ Simpler architecture and better maintainability

---

## Current Architecture Analysis

### Existing Files
```
backend/parsers/
├── __init__.py           # Parser registry (uses lula_wrapper)
├── base.py              # Base parser with extract/cleanup (101 lines)
├── bandwidth.py         # ✅ Standalone (85 lines)
├── modem_stats.py       # ✅ Standalone (75 lines)
├── errors.py            # ✅ Standalone (122 lines)
├── sessions.py          # ✅ Standalone (112 lines)
├── system.py            # ✅ Standalone (116 lines)
├── device_id.py         # ✅ Standalone (77 lines)
├── lula_wrapper.py      # ❌ Subprocess wrapper (896 lines) - TO DELETE
└── lula2.py             # ❌ Legacy monolith (3,038 lines) - TO DELETE
```

### Current Flow (Inefficient)
```
Request → lula_wrapper.py → subprocess.Popen(lula2.py) → parse → stdout text
                                                                        ↓
Frontend ← JSON ← parse text output ← capture stdout ← lula2.py completes
```

**Problems**:
1. Subprocess spawn overhead (~200ms)
2. Double parsing (lula2.py parses, wrapper re-parses)
3. Temp files for stdout/stderr
4. Hard to cancel (must kill process group)
5. Complex error handling

### Target Flow (Efficient)
```
Request → standalone parser → extract archive → parse messages.log → JSON
                                                                        ↓
Frontend ← JSON directly ← single-pass parsing ← in-memory processing
```

**Benefits**:
1. No subprocess overhead
2. Single-pass parsing
3. Streaming for large files
4. Easy cancellation (in-process flag)
5. Clean error handling

---

## Implementation Plan

### Phase 1: Switch Parser Registry (5 minutes)

**File**: `backend/parsers/__init__.py`

**Current**:
```python
from .lula_wrapper import (
    BandwidthParser,
    ModemStatsParser,
    # ...
)
```

**Change to**:
```python
from .bandwidth import BandwidthParser
from .modem_stats import ModemStatsParser
from .sessions import SessionsParser
from .errors import ErrorParser
from .system import SystemParser
from .device_id import DeviceIDParser
```

**Impact**: Zero API changes, parsers work immediately

**Test**: Upload small file with each mode, verify output format unchanged

---

### Phase 2: Enhance Standalone Parsers (30 minutes)

#### 2.1 Handle Compressed Nested Logs (15 min)

**Problem**: LiveU logs often have `messages.log.gz` inside `.tar.bz2`

**Solution**: Add to `base.py`:
```python
def find_messages_log(self, directory):
    """Find messages.log or messages.log.gz"""
    for root, dirs, files in os.walk(directory):
        for file in files:
            if file == 'messages.log':
                return os.path.join(root, file)
            elif file.endswith('messages.log.gz'):
                return self._decompress_gz(os.path.join(root, file))
            elif file.endswith('messages.log.bz2'):
                return self._decompress_bz2(os.path.join(root, file))
    raise FileNotFoundError("messages.log not found")

def _decompress_gz(self, path):
    """Decompress .gz file to temp location"""
    import gzip
    output = path[:-3]  # Remove .gz
    with gzip.open(path, 'rb') as f_in:
        with open(output, 'wb') as f_out:
            shutil.copyfileobj(f_in, f_out)
    return output
```

#### 2.2 Parallel Decompression (5 min)

**Enhancement**: Use `pigz`/`pbzip2` for faster extraction

**File**: `base.py`
```python
def extract_logs(self, archive_path):
    if archive_path.endswith('.bz2'):
        # Try pbzip2 (parallel), fallback to bzip2
        try:
            cmd = ['tar', '-I', 'pbzip2', '-xf', archive_path, '-C', self.temp_dir]
        except:
            cmd = ['tar', 'xjf', archive_path, '-C', self.temp_dir]
    # Similar for .gz with pigz
```

**Benefit**: 2-3x faster on multi-core systems

#### 2.3 Streaming for Large Files (10 min)

**Problem**: Loading 100MB+ files into memory is inefficient

**Solution**: Add generator-based parsing
```python
def parse_streaming(self, log_path, timezone, begin_date, end_date):
    """Parse file line-by-line without loading into memory"""
    with open(log_path, 'r', encoding='utf-8', errors='ignore') as f:
        for line in f:
            # Process line immediately
            if self._matches_filters(line, begin_date, end_date):
                yield self._parse_line(line)
```

**Apply to**: bandwidth.py, errors.py, sessions.py

---

### Phase 3: Performance Optimizations (20 minutes)

#### 3.1 Pre-compile Regex Patterns

**Current** (errors.py):
```python
def parse(self, log_path, ...):
    patterns = [re.compile(p, re.IGNORECASE) for p in self.KNOWN_ERRORS]
```

**Optimized**:
```python
class ErrorParser(BaseParser):
    # Compile once at class level
    COMPILED_KNOWN = [re.compile(p, re.IGNORECASE) for p in KNOWN_ERRORS]
    COMPILED_VERBOSE = [re.compile(p, re.IGNORECASE) for p in VERBOSE_ERRORS]

    def parse(self, log_path, ...):
        patterns = self.COMPILED_KNOWN if self.mode == 'known' else ...
```

**Apply to**: All parsers with regex

#### 3.2 Online Statistics for Modem Parser

**Current** (modem_stats.py):
```python
# Stores all samples
modems[id]['signal_samples'].append(signal)
# Later: avg_signal = sum(samples) / len(samples)
```

**Optimized**:
```python
# Running statistics - O(1) memory
class RunningStats:
    def __init__(self):
        self.count = 0
        self.sum = 0
        self.min = float('inf')
        self.max = float('-inf')

    def add(self, value):
        self.count += 1
        self.sum += value
        self.min = min(self.min, value)
        self.max = max(self.max, value)

    @property
    def avg(self):
        return self.sum / self.count if self.count > 0 else 0
```

**Benefit**: Constant memory for any log size

#### 3.3 Fast Keyword Filtering

**Current**:
```python
if 'bitrate' in line.lower():  # Slow: creates new string
    match = PATTERN.search(line)
```

**Optimized**:
```python
# Use bytes for faster matching
KEYWORD = b'bitrate'
with open(log_path, 'rb') as f:
    for line_bytes in f:
        if KEYWORD in line_bytes:  # Fast: no string creation
            line = line_bytes.decode('utf-8', errors='ignore')
            match = PATTERN.search(line)
```

**Benefit**: 20-30% faster for large files

---

### Phase 4: Update Cancellation (15 minutes)

**Problem**: Current cancellation kills subprocess via PID. With in-process parsers, need different approach.

**Solution**: Use threading.Event for cancellation flag

**File**: `backend/parsers/base.py`
```python
class BaseParser(ABC):
    def __init__(self, mode):
        self.mode = mode
        self.temp_dir = None
        self.cancelled = threading.Event()  # NEW

    def cancel(self):
        """Signal parser to stop"""
        self.cancelled.set()

    def check_cancelled(self):
        """Check if cancellation requested"""
        if self.cancelled.is_set():
            raise CancellationException("Parsing cancelled by user")
```

**File**: Each parser
```python
def parse(self, log_path, ...):
    line_count = 0
    for line in f:
        line_count += 1
        if line_count % 1000 == 0:  # Check every 1000 lines
            self.check_cancelled()

        # Normal parsing...
```

**File**: `backend/app.py`
```python
# Store parser instance in Redis for cancellation
parser = get_parser(parse_mode)
redis_client.setex(f"parser:{user_id}:instance", 3600, id(parser))

# Cancel endpoint
def cancel_analysis(current_user, db):
    parser_id = redis_client.get(f"parser:{current_user.id}:instance")
    if parser_id:
        # Find parser by ID and call cancel()
        parser.cancel()
```

**Benefit**: <100ms cancellation latency (vs 1-2s for subprocess kill)

---

### Phase 5: Cleanup (5 minutes)

**Files to delete**:
- `backend/parsers/lula_wrapper.py` (896 lines)
- `backend/lula2.py` (3,038 lines)

**Files to update**:
- `backend/app.py` - Remove subprocess/PID tracking logic
- `backend/parsers/__init__.py` - Remove lula_wrapper imports (already done in Phase 1)

**Verification**:
```bash
# Ensure no references remain
grep -r "lula2" backend/
grep -r "lula_wrapper" backend/
```

---

## Testing Plan

### Unit Tests (Per Parser)

#### Test Template
```python
class TestBandwidthParser(unittest.TestCase):
    def setUp(self):
        self.parser = BandwidthParser('bw')
        self.test_archive = 'tests/fixtures/sample.tar.bz2'

    def test_basic_parsing(self):
        result = self.parser.process(self.test_archive)
        self.assertIn('raw_output', result)
        self.assertIn('parsed_data', result)
        self.assertIsInstance(result['parsed_data'], list)

    def test_date_filtering(self):
        result = self.parser.process(
            self.test_archive,
            begin_date='2025-01-01 00:00:00',
            end_date='2025-01-02 00:00:00'
        )
        # Verify only data in range

    def test_compressed_nested_logs(self):
        # Test .tar.bz2 with messages.log.gz inside

    def test_cancellation(self):
        import threading
        def parse_async():
            self.parser.process(large_archive)

        thread = threading.Thread(target=parse_async)
        thread.start()
        time.sleep(0.1)
        self.parser.cancel()
        thread.join(timeout=2)
        # Verify thread stopped

    def test_performance(self):
        start = time.time()
        result = self.parser.process(self.test_archive)
        duration = time.time() - start
        self.assertLess(duration, 5.0)  # Should complete in <5s
```

### Integration Tests

#### Compare with lula2.py Baseline
```python
def test_output_parity():
    """Ensure standalone parser produces same output as lula2.py"""
    # Parse with old lula_wrapper
    old_result = lula_wrapper_parse(archive, 'bw')

    # Parse with new standalone
    new_result = standalone_parse(archive, 'bw')

    # Compare outputs (should be identical or semantically equivalent)
    assert_equivalent(old_result, new_result)
```

#### Archive Format Tests
```python
def test_tar_bz2():
    """Test .tar.bz2 extraction"""
def test_tar_gz():
    """Test .tar.gz extraction"""
def test_nested_compression():
    """Test messages.log.gz inside .tar.bz2"""
def test_multiple_log_files():
    """Test archive with multiple messages.log.* files"""
```

### Performance Benchmarks

**Test Setup**:
```python
test_files = {
    'small': '1MB.tar.bz2',
    'medium': '10MB.tar.bz2',
    'large': '50MB.tar.bz2',
    'xlarge': '100MB.tar.bz2'
}

def benchmark_parser(parser_name, file_size):
    start_memory = get_memory_usage()
    start_time = time.time()

    result = parse(test_files[file_size], parser_name)

    end_time = time.time()
    peak_memory = get_peak_memory_usage()

    return {
        'time': end_time - start_time,
        'memory': peak_memory - start_memory
    }
```

**Expected Results**:
```
Mode: bandwidth, File: 10MB
Before: 3.2s, 180MB RAM
After:  1.1s, 95MB RAM
Speedup: 2.9x, Memory: 47% reduction

Mode: sessions, File: 50MB
Before: 8.5s, 450MB RAM
After:  2.8s, 180MB RAM
Speedup: 3.0x, Memory: 60% reduction
```

---

## Rollback Plan

If issues found after deployment:

**Immediate Rollback** (< 5 min):
```bash
git revert HEAD~5  # Revert last 5 commits (one per phase)
docker-compose restart backend
```

**Selective Rollback**:
```python
# Temporarily switch back to lula_wrapper in __init__.py
from .lula_wrapper import BandwidthParser  # etc.
```

**Testing Before Full Deployment**:
1. Deploy to staging environment first
2. Run full test suite
3. Compare outputs with production logs
4. Monitor performance metrics
5. Only deploy to production after 24h staging validation

---

## Success Metrics

### Performance
- ✅ Parsing time reduced by >50%
- ✅ Memory usage reduced by >40%
- ✅ Cancellation latency <1s (vs 1-2s)

### Code Quality
- ✅ Remove 3,934 lines of code
- ✅ Unit test coverage >80%
- ✅ No new bugs introduced (regression tests pass)

### User Experience
- ✅ No change to API (backward compatible)
- ✅ Faster response times (user perceivable)
- ✅ Reliable cancellation (no zombie processes)

---

## Timeline

**Phase 1**: 5 min (registry switch)
**Phase 2**: 30 min (feature enhancements)
**Phase 3**: 20 min (optimizations)
**Phase 4**: 15 min (cancellation)
**Phase 5**: 5 min (cleanup)
**Testing**: 45 min (unit + integration)

**Total**: ~2 hours

**Can be interrupted**: Each phase is independent, commit after each phase creates restore point.

---

## Notes for Continuation After 5-Hour Reset

If this refactoring is interrupted by the 5-hour conversation limit:

1. **Check git log** to see which phases completed:
   ```bash
   git log --oneline --since="2 hours ago"
   ```

2. **Check parser registry** to see current state:
   ```python
   cat backend/parsers/__init__.py | grep "^from"
   ```

3. **Resume from last phase**: Each phase is independent, pick up from next uncompleted phase

4. **Run tests** before continuing to verify current state:
   ```bash
   docker-compose exec backend python -m pytest tests/test_parsers.py
   ```

---

**Document Version**: 1.0
**Created**: 2025-10-04
**Status**: Ready for Implementation
