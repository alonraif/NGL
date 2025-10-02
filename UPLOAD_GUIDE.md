# 📤 Upload Guide - Quick Reference

## ❗ IMPORTANT: File Format

### ✅ ONLY `.tar.bz2` files are accepted!

```
yourfile.tar.bz2  ✅ CORRECT
yourfile.bz2      ❌ WRONG (just compressed, not a tar archive)
yourfile.tar      ❌ WRONG (not compressed)
yourfile.tar.gz   ❌ WRONG (wrong compression)
yourfile.zip      ❌ WRONG (different format)
```

## 🔧 Quick Fix Guide

### If you have `unitLogs.bz2`:

```bash
# Step 1: Decompress
bunzip2 unitLogs.bz2

# Step 2: Check if it's a tar file
file unitLogs

# If output says "POSIX tar archive":
bzip2 unitLogs
mv unitLogs.bz2 unitLogs.tar.bz2

# If output says something else:
mkdir logs
mv unitLogs logs/messages.log
tar -cjf unitLogs.tar.bz2 logs/
```

### If you have log files in a directory:

```bash
# Create .tar.bz2 from directory
tar -cjf mylogs.tar.bz2 /path/to/log-directory/

# Example:
tar -cjf device-logs.tar.bz2 logs/
```

## ✅ Verify Before Upload

```bash
# 1. Check it's the right format
file mylogs.tar.bz2
# Should output: "bzip2 compressed data"

# 2. List what's inside (doesn't extract)
tar -tjf mylogs.tar.bz2
# Should show files like:
#   messages.log
#   messages.log.1.gz
#   etc.

# 3. Check file size
ls -lh mylogs.tar.bz2
# Should be < 500MB
```

## 📋 What Should Be Inside?

Your `.tar.bz2` file should contain:

```
logs/
├── messages.log          # Current log
├── messages.log.1.gz     # Older logs
├── messages.log.2.gz
└── ...
```

OR for FFmpeg logs:

```
logs/
├── ffmpeg_streamId__cdn_0__outputIndex__0.txt
├── ffmpeg_streamId__cdn_0__outputIndex__0.txt.1.gz
└── ...
```

## 🚀 Quick Commands

### Create from LiveU unit (via SSH):
```bash
ssh user@liveu-ip
cd /var/log
tar -cjf /tmp/logs.tar.bz2 messages.log*
exit
scp user@liveu-ip:/tmp/logs.tar.bz2 ./
```

### Create from local files:
```bash
# Option 1: From directory
tar -cjf output.tar.bz2 log-directory/

# Option 2: Specific files only
tar -cjf output.tar.bz2 messages.log*

# Option 3: With date range
tar -cjf output.tar.bz2 --newer "2024-01-01" logs/
```

## 📏 Size Limits

- **Maximum:** 500MB
- **Recommended:** < 100MB
- **Typical:** 10-50MB

### If file is too large:

```bash
# Split by time period
tar -cjf jan-logs.tar.bz2 --newer "2024-01-01" --older "2024-02-01" logs/
tar -cjf feb-logs.tar.bz2 --newer "2024-02-01" --older "2024-03-01" logs/

# OR use maximum compression
tar -c logs/ | bzip2 -9 > logs.tar.bz2
```

## 🎯 Upload Checklist

Before uploading, check:

- [ ] Filename ends with `.tar.bz2`
- [ ] File size < 500MB
- [ ] Contains log files (verified with `tar -tjf`)
- [ ] No errors when testing archive

## ⚠️ Common Mistakes

| Mistake | Fix |
|---------|-----|
| Uploaded `.bz2` file | Add `.tar` - create proper archive |
| Uploaded `.tar.gz` file | Re-compress with bzip2 instead of gzip |
| Uploaded `.zip` file | Convert to `.tar.bz2` format |
| Empty archive | Ensure log files are included |
| Archive too large | Split by date or compress more |

## 💡 Pro Tips

### Fastest Creation:
```bash
# Use parallel compression (4x faster)
tar -c logs/ | pbzip2 -p4 > logs.tar.bz2
```

### Test Archive:
```bash
# Test extraction without actually extracting
tar -tjf logs.tar.bz2 > /dev/null && echo "Archive OK"
```

### Check Log Content:
```bash
# Preview first log file
tar -Oxjf logs.tar.bz2 messages.log | head -20
```

## 🆘 Still Not Working?

1. **Read:** [FILE_FORMAT.md](FILE_FORMAT.md) for detailed guide
2. **Check:** Run verification commands above
3. **Test:** Create a simple test archive:
   ```bash
   echo "test" > messages.log
   tar -cjf test.tar.bz2 messages.log
   ```
4. **Upload:** test.tar.bz2 to verify system works

---

**Quick Summary:** Upload `.tar.bz2` files only!
