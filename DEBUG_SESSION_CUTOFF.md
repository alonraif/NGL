# Debug Guide: Session Drill-Down Data Cutoff

## Problem
Session drill-down shows data only up to `10:00:14`, but session ends at `10:05:14`. The missing 5 minutes show as "(forward filled)" instead of real data.

## Root Cause Analysis

After investigation, the timestamp normalization fix is correct, but data is still missing. This means **one of these is true**:

### Possibility 1: Timezone Mismatch ⚠️ MOST LIKELY

The session times in the database are stored in **UTC** (`+00:00`), but the drill-down might be using a **different timezone** for parsing.

**Example:**
- Session end (database): `2025-10-28 10:05:14+00:00` (UTC)
- Parser timezone: `US/Eastern` (UTC-5)
- Parser thinks end time is: `2025-10-28 10:05:14 Eastern` = `2025-10-28 15:05:14 UTC`
- But the parser is looking for logs timestamped `10:05:14 Eastern`, which would be `05:05:14` in the log files (if logs are in UTC)

**How to Check:**
1. Check what timezone was used in the original analysis:
   ```sql
   SELECT timezone FROM analyses WHERE id = <parent_analysis_id>;
   ```

2. Check the backend logs during drill-down for timezone info:
   ```bash
   docker compose logs backend | grep -i "timezone\|drill-down"
   ```

3. **FIX**: Make sure drill-down uses **UTC** timezone if session times are in UTC:
   - Modify `SessionDrillDown.js` line 281 to force UTC:
     ```javascript
     timezone: 'UTC',  // Force UTC instead of analysisData.timezone
     ```

### Possibility 2: Archive Filtering Excluding Files

The archive pre-filtering (based on file modification times) might be excluding files that contain logs from 10:00-10:05.

**How to Check:**
```bash
docker compose exec backend python3 /app/diagnose_session_data.py
```

Look for:
- "Files within session time range: 0" → Archive filtering is the problem
- "Files within session time range: X" → Files exist, so it's a parsing issue

**Potential Fix:**
Temporarily disable archive filtering to test:
- Edit `backend/app.py` line 1103
- Change `if begin_date and end_date:` to `if False:  # TEMPORARY DEBUG`
- Restart backend and test

### Possibility 3: No Actual Log Data

The device might not have generated modem bandwidth logs during that 5-minute period.

**How to Check:**
1. Extract and examine the archive manually:
   ```bash
   tar -xjf your_archive.tar.bz2
   grep "10:0[0-5]:" messages.log | grep "Modem Statistics"
   ```

2. Check if logs exist for that time period

**If this is the case:**
- Forward-filling is correct behavior
- The visualization accurately shows "no data available"

## Quick Debug Steps

### Step 1: Check Timezone
```bash
# In Docker container
docker compose exec backend python3 << 'EOF'
from database import SessionLocal
from models import Analysis
db = SessionLocal()
analysis = db.query(Analysis).filter(Analysis.id == YOUR_ANALYSIS_ID).first()
print(f"Timezone: {analysis.timezone}")
print(f"Begin: {analysis.begin_date}")
print(f"End: {analysis.end_date}")
EOF
```

### Step 2: Check Backend Logs
```bash
docker compose logs backend --tail=100 | grep -A 5 -B 5 "10:05:14"
```

Look for:
- "Normalized timestamps for lula2.py" → Confirms fix is working
- "Archive filtered successfully" → Filtering is active
- "Less than 20% reduction" → Filtering was skipped

### Step 3: Force UTC Timezone

**File: `frontend/src/components/SessionDrillDown.js`**

Change line 281 from:
```javascript
timezone: analysisData.timezone || 'UTC',
```

To:
```javascript
timezone: 'UTC',  // DEBUG: Force UTC to match session times
```

Rebuild frontend:
```bash
docker compose restart frontend
```

### Step 4: Test Without Archive Filtering

**File: `backend/app.py`**

Change line 1103 from:
```python
if begin_date and end_date:
```

To:
```python
if False:  # DEBUG: Disable archive filtering
```

Restart backend:
```bash
docker compose restart backend
```

## Expected Behavior After Fix

If timezone is the issue:
- ✓ Data will extend to 10:05:14
- ✓ Real data points appear (not forward-filled)
- ✓ Visualization shows complete session

If archive filtering is the issue:
- ✓ More files will be processed
- ✓ Processing will be slower
- ✓ Complete data will be available

If no logs exist:
- Forward-filling is correct
- No fix possible (data doesn't exist)

## Recommended Fix

Based on the symptoms, the most likely issue is **timezone mismatch**. The fastest fix:

1. **Force UTC timezone in drill-down** (frontend change above)
2. **OR** Convert session times to match parser timezone (backend change)

### Permanent Solution

Store session times with explicit timezone in the database, and always use matching timezone for drill-down parsing.

**File: `backend/parsers/sessions_native.py`**

Ensure sessions are stored with timezone info, not as naive timestamps.

## Contact

If none of these fixes work, provide:
1. Output of timezone check (Step 1)
2. Backend logs during drill-down (Step 2)
3. Result of archive file analysis
4. Original analysis timezone used

This will help identify the exact root cause.
