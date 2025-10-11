# Parallel Parsing Implementation Plan

## Problem
Currently, log file parsing only uses **one CPU core**, making it slow for large files (7+ minutes for unitLogs_16.bz2).

## Root Cause Analysis
1. **lula2.py** is a single-threaded Python script (3,015 lines)
2. Python's **Global Interpreter Lock (GIL)** prevents multi-threading for CPU-bound tasks
3. Standard `bzip2` decompression is single-threaded
4. Log files processed sequentially, not in parallel

## Multi-Phase Improvement Plan

### Phase 1: Parallel Decompression ⚡ (Quick Win - CURRENT)
**Expected Speedup:** 2-4x faster
**Effort:** Low (15-30 minutes)
**Status:** IN PROGRESS

#### Implementation Steps
1. ✅ Verify `pbzip2` and `pigz` are installed in Docker container
2. Configure tar to use parallel decompression tools
3. Update lula2.py or wrapper to force parallel decompression
4. Test with real log files to verify:
   - Parsing still works correctly
   - Performance improvement measured
   - No broken parsers

#### Technical Details
- **pbzip2**: Parallel bzip2 compression/decompression (uses all CPU cores)
- **pigz**: Parallel gzip compression/decompression (uses all CPU cores)
- Both are **drop-in replacements** for bzip2/gzip
- Already installed in backend Docker image (see `backend/Dockerfile:13`)

#### Testing Strategy
- Test each parser mode individually:
  - ✅ sessions
  - ✅ bw (bandwidth)
  - ✅ md (modem stats)
  - ✅ known (errors)
  - ✅ grading
  - ✅ memory
- Compare results before/after to ensure identical output
- Measure time improvement with `time` command

---

### Phase 2: Multi-File Parallel Processing (Medium Effort)
**Expected Speedup:** 3-6x faster (cumulative with Phase 1)
**Effort:** Medium (2-4 hours)
**Status:** PLANNED

#### Approach
LiveU log archives contain multiple compressed log files:
```
unitLogs.tar.bz2
├── messages.log.1.gz
├── messages.log.2.gz
├── messages.log.3.gz
└── messages.log.4.gz
```

**Strategy:**
1. Extract list of compressed log files from archive
2. Process each `.gz` file in parallel using Python `multiprocessing`
3. Merge results chronologically
4. Maintain compatibility with existing parser interface

#### Implementation Options
**Option A: Modify lula2.py**
- Add multiprocessing support to lula2.py
- Process files in parallel, merge results
- Pros: Centralized, works for all use cases
- Cons: Requires modifying battle-tested code

**Option B: Create parallel wrapper**
- Keep lula2.py unchanged
- Create new `lula2_parallel.py` wrapper
- Splits work, calls lula2.py in parallel
- Pros: Preserves original lula2.py, safer
- Cons: More complex architecture

**Recommendation:** Option B - parallel wrapper

---

### Phase 3: Async Celery Background Jobs (High Effort)
**Expected Speedup:** Better UX, horizontal scalability
**Effort:** Medium-High (3-5 hours)
**Status:** PLANNED (Celery already installed!)

#### Benefits
1. **Non-blocking uploads**: Return immediately, process in background
2. **Horizontal scaling**: Add more Celery workers on different machines
3. **Better UX**: Progress bars, real-time updates via WebSocket/polling
4. **Queue management**: Handle multiple concurrent uploads
5. **Retry logic**: Automatic retry on failures

#### Architecture
```
User Upload → Flask API → Celery Task Queue → Worker Pool
                           ↓                       ↓
                       Redis Queue          [Worker 1] [Worker 2] [Worker 3]
                                                 ↓          ↓          ↓
                                            Process logs in parallel
```

#### Implementation Steps
1. Move `upload_file()` logic to Celery task
2. Return task ID immediately to frontend
3. Frontend polls for task status
4. Store results in database when complete
5. Update UI with progress/results

#### Notes
- **Celery already installed** in docker-compose.yml
- Workers: `celery_worker-1`
- Beat scheduler: `celery_beat-1`
- Redis: `redis-1` (already used for task queue)

---

## Performance Expectations

### Current Performance (Baseline)
- **unitLogs_16.bz2**: ~7 minutes (sessions mode)
- **CPU utilization**: 1 core (12.5% on 8-core system)

### Phase 1: Parallel Decompression
- **Expected time**: 2-3 minutes (2-3x faster)
- **CPU utilization**: 4-8 cores during decompression
- **Speedup**: Most time spent in decompression

### Phase 2: Multi-File Processing
- **Expected time**: 1-2 minutes (cumulative 5-7x faster)
- **CPU utilization**: 8+ cores (full system)
- **Speedup**: Process multiple log files simultaneously

### Phase 3: Async Celery
- **User-perceived time**: Instant (returns immediately)
- **Actual processing**: Same as Phase 1+2
- **Scalability**: Add more workers = more concurrent jobs

---

## Testing Protocol

### Before Each Change
1. Take baseline measurements:
   ```bash
   time docker-compose exec backend python3 lula2.py <file> -p sessions -t UTC
   ```
2. Save output for comparison

### After Each Change
1. Run same command, measure time
2. Compare output byte-for-byte: `diff before.txt after.txt`
3. Test all parser modes (sessions, bw, md, known, grading, memory)
4. Verify UI displays results correctly

### Regression Testing
- Keep test log files in `/test_data/`
- Automated test script: `test_all_parsers.sh`
- Run after any parser changes

---

## Risk Mitigation

### Phase 1 Risks
- **Low risk**: pbzip2/pigz are mature, stable tools
- **Mitigation**: Keep original lula2.py unchanged, only modify wrapper
- **Rollback**: Simple - remove parallel decompression flags

### Phase 2 Risks
- **Medium risk**: Parallel processing can cause race conditions
- **Mitigation**: Test thoroughly, use parallel wrapper (not modify lula2.py)
- **Rollback**: Fall back to Phase 1 implementation

### Phase 3 Risks
- **Medium risk**: Async adds complexity (frontend polling, error handling)
- **Mitigation**: Phase 1+2 improvements work synchronously too
- **Rollback**: Keep sync endpoint, make async optional

---

## Success Criteria

### Phase 1
- ✅ All parsers produce identical output
- ✅ 2x or better speedup measured
- ✅ CPU utilization increases to 50%+
- ✅ No broken visualizations in UI

### Phase 2
- ✅ All parsers produce identical output
- ✅ 5x or better cumulative speedup
- ✅ CPU utilization increases to 80%+
- ✅ Works with archives containing 1-100 log files

### Phase 3
- ✅ Upload returns in <1 second
- ✅ Frontend shows real-time progress
- ✅ Background processing completes successfully
- ✅ Multiple concurrent uploads supported

---

## Timeline

- **Phase 1**: 15-30 minutes (CURRENT)
- **Phase 2**: 2-4 hours (NEXT)
- **Phase 3**: 3-5 hours (FUTURE)

**Total estimated time**: 6-10 hours for all phases

---

## Current Status

**Phase 1: IN PROGRESS**
- ✅ Analysis complete
- ✅ Plan documented
- 🔄 Implementation starting
- ⏳ Testing pending

---

## References

- lula2.py: `/Users/alonraif/Code/ngl/lula2.py` (3,015 lines)
- Parser wrapper: `backend/parsers/lula_wrapper.py`
- Docker backend: `backend/Dockerfile`
- Celery config: `backend/celery_app.py`

---

**Last Updated**: 2025-10-11
**Author**: Claude Code
