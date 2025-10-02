# ✅ Correct LiveU Log File Format

## The Issue

Your file `unitLogs.bz2` is **not** in the correct format.

**lula2.py requires a TAR ARCHIVE** (that may be compressed with bzip2).

## What lula2.py Expects

Looking at the code (line 2780):
```python
tar xf {source_file} -C{destination}
```

This means the file MUST be a **tar archive** that can be extracted.

## Required File Structure

```
yourfile.tar.bz2  (or .tar or .tgz)
│
└─ When extracted, contains:
   ├── messages.log
   ├── messages.log.1.gz
   ├── messages.log.2.gz
   └── ... other log files
```

## ❌ Your Current File

Based on your directory structure, you have the **extracted** contents.

Your `unitLogs.bz2` is probably:
- Just the directory compressed with bzip2
- NOT a tar archive

## ✅ How to Create the Correct File

### From your `unit-logs` directory:

```bash
# You are here:
# unit-logs/
#   ├── messages.log
#   ├── messages.log.1.gz
#   └── ...

# Go to PARENT directory
cd ..

# Create TAR archive, then compress with bzip2
tar -cjf unit-logs.tar.bz2 unit-logs/

# OR create tar first, then compress
tar -cf unit-logs.tar unit-logs/
bzip2 unit-logs.tar
# Results in: unit-logs.tar.bz2
```

### Verify it's correct:

```bash
# Test extraction (doesn't actually extract, just tests)
tar -tjf unit-logs.tar.bz2

# Should show:
# unit-logs/
# unit-logs/messages.log
# unit-logs/messages.log.1.gz
# unit-logs/messages.log.2.gz
# ...
```

## What lula2.py Does

1. **Extracts** the tar archive to a temp directory
2. **Looks for** `messages.log*` files in the extracted directory
3. **Processes** those log files with gzcat/zcat

## File Format Requirements Summary

| Format | Required? | Notes |
|--------|-----------|-------|
| **TAR archive** | ✅ YES | Must be extractable with `tar xf` |
| **Bzip2 compression** | ⚠️ Optional | Can be .tar, .tar.bz2, or .tar.gz |
| **Contains logs** | ✅ YES | Must have messages.log* inside |

## Quick Test

Create a test file:

```bash
# Create test structure
mkdir test-logs
echo "2024-01-01 00:00:00 INFO:Test log line" > test-logs/messages.log

# Create correct tar.bz2
tar -cjf test-logs.tar.bz2 test-logs/

# Verify
tar -tjf test-logs.tar.bz2

# Upload test-logs.tar.bz2 to verify system works
```

## Common Mistakes

| Mistake | Issue | Fix |
|---------|-------|-----|
| `unitLogs.bz2` | Just compressed, no tar | Add tar step |
| `unitLogs/` (directory) | Not archived | Create tar archive |
| Wrong contents | No messages.log inside | Check directory structure |
| Just `messages.log` | Single file, not directory | Put in directory first |

## Summary

**Your file MUST be:**
1. A TAR archive (created with `tar -c`)
2. Optionally compressed (bzip2, gzip, or uncompressed)
3. Contains a directory with `messages.log*` files

**Command to create from your directory:**
```bash
cd /path/to/parent/of/unit-logs
tar -cjf unit-logs.tar.bz2 unit-logs/
```

Then upload `unit-logs.tar.bz2` ✅
