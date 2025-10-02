# 📦 File Format Requirements

## ❌ Issue: Your file `unitLogs.bz2` cannot be processed

### Why?

The LiveU Log Analyzer expects **`.tar.bz2`** files (tar archives compressed with bzip2), not just **`.bz2`** files.

**Your file:** `unitLogs.bz2` (just compressed)
**Expected:** `unitLogs.tar.bz2` (compressed tar archive)

## ✅ Required File Format

### What is a `.tar.bz2` file?

A `.tar.bz2` file is:
1. A **tar archive** (collection of files/directories)
2. **Compressed** with bzip2

Think of it like a `.zip` file but using tar+bzip2 instead.

### File Structure

The expected structure inside the `.tar.bz2` file:

```
your-logs.tar.bz2
├── messages.log              # Current log file
├── messages.log.1.gz         # Older logs (compressed)
├── messages.log.2.gz
└── ...
```

OR for FFmpeg logs:

```
your-logs.tar.bz2
├── ffmpeg_streamId__cdn_0__outputIndex__0.txt
├── ffmpeg_streamId__cdn_0__outputIndex__0.txt.1.gz
└── ...
```

## 🔧 How to Fix Your File

### Option 1: If you have the original log directory

```bash
# Create proper tar.bz2 archive
tar -cjf unitLogs.tar.bz2 /path/to/logs/

# Example: If logs are in a directory called 'logs'
tar -cjf unitLogs.tar.bz2 logs/
```

### Option 2: If unitLogs.bz2 contains a tar file

```bash
# Decompress the .bz2 file
bunzip2 unitLogs.bz2

# This gives you unitLogs (which should be a .tar file)
# Verify it's a tar file
file unitLogs

# If it says "POSIX tar archive", compress it properly:
bzip2 unitLogs

# Rename to .tar.bz2
mv unitLogs.bz2 unitLogs.tar.bz2
```

### Option 3: If unitLogs.bz2 is just log data (not a tar)

```bash
# Decompress
bunzip2 unitLogs.bz2

# Create a directory structure
mkdir -p logs
mv unitLogs logs/messages.log

# Create proper tar.bz2
tar -cjf unitLogs.tar.bz2 logs/
```

## 🎯 Quick Check

### Is my file correct?

```bash
# Check file type
file yourfile.tar.bz2

# Should output something like:
# yourfile.tar.bz2: bzip2 compressed data

# List contents (doesn't extract)
tar -tjf yourfile.tar.bz2

# Should show files like:
# messages.log
# messages.log.1.gz
# etc.
```

### Common mistakes:

❌ `logs.bz2` - Just compressed, not a tar archive
❌ `logs.tar` - Tar archive, but not compressed
❌ `logs.tar.gz` - Tar archive compressed with gzip (should be bzip2)
✅ `logs.tar.bz2` - Correct format!

## 📋 Creating LiveU Log Archives

### From LiveU Unit

If you're extracting logs from a LiveU unit:

1. **Via Web Interface:**
   - Go to Settings → System → Logs
   - Click "Download Logs"
   - This should give you a `.tar.bz2` file automatically

2. **Via SSH:**
   ```bash
   # On the LiveU unit
   cd /var/log/
   tar -cjf /tmp/unit-logs.tar.bz2 messages.log*

   # Download using scp
   scp user@unit:/tmp/unit-logs.tar.bz2 ./
   ```

### From Log Files on Your Computer

If you have individual log files:

```bash
# Create a directory
mkdir liveu-logs

# Copy log files into it
cp messages.log* liveu-logs/

# Create tar.bz2 archive
tar -cjf liveu-logs.tar.bz2 liveu-logs/

# Upload liveu-logs.tar.bz2 to the analyzer
```

## 🔍 Troubleshooting

### Error: "Invalid file type"

**Cause:** File doesn't end with `.tar.bz2`

**Fix:** Ensure filename ends with `.tar.bz2` (not `.bz2`, `.tar`, or `.tgz`)

### Error: "Failed to extract"

**Cause:** File is corrupted or not a valid tar archive

**Fix:**
```bash
# Test the archive
tar -tjf yourfile.tar.bz2

# If it fails, recreate the archive
```

### Error: "No log files found"

**Cause:** Archive doesn't contain `messages.log` or `ffmpeg_*.txt` files

**Fix:** Ensure archive contains the expected log file structure

## 📊 File Size Limits

- **Maximum:** 500MB
- **Recommended:** < 100MB for faster processing
- **Typical LiveU log:** 10-50MB

### If your file is too large:

```bash
# Split by date/time
tar -cjf logs-part1.tar.bz2 --newer "2024-01-01" logs/
tar -cjf logs-part2.tar.bz2 --newer "2024-01-02" logs/

# OR compress with maximum compression
tar -c logs/ | bzip2 -9 > logs.tar.bz2
```

## ✅ Verification Checklist

Before uploading, verify:

- [ ] Filename ends with `.tar.bz2`
- [ ] File is < 500MB
- [ ] Archive contains log files:
  - `messages.log*` OR
  - `ffmpeg_*.txt*`
- [ ] Can list archive contents: `tar -tjf yourfile.tar.bz2`
- [ ] No error when testing: `tar -tjf yourfile.tar.bz2 > /dev/null`

## 💡 Pro Tips

### Faster Compression

Use parallel bzip2:
```bash
tar -c logs/ | pbzip2 -p4 > logs.tar.bz2
```

### Check Without Extracting

```bash
# List contents
tar -tjf logs.tar.bz2

# Find specific files
tar -tjf logs.tar.bz2 | grep messages.log

# Check size before extracting
tar -tjf logs.tar.bz2 | wc -l
```

### From Multiple Sources

```bash
# Combine logs from different times
mkdir all-logs
cp /source1/messages.log* all-logs/
cp /source2/messages.log* all-logs/
tar -cjf combined-logs.tar.bz2 all-logs/
```

## 🆘 Still Having Issues?

### Quick Test:

Create a test archive:
```bash
echo "test log line" > messages.log
tar -cjf test.tar.bz2 messages.log
```

Upload `test.tar.bz2` to verify the system works.

### Contact Information:

If you continue to have issues:
1. Check file with: `file yourfile.tar.bz2`
2. List contents: `tar -tjf yourfile.tar.bz2`
3. Check size: `ls -lh yourfile.tar.bz2`
4. Report findings with error messages

---

**Summary:** Upload `.tar.bz2` files (tar archives compressed with bzip2), not plain `.bz2` files!
