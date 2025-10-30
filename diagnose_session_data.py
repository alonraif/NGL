#!/usr/bin/env python3
"""
Diagnostic script to check what data exists in the archive for a specific session
"""
import sys
import os

# Add backend directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

print("=" * 80)
print("SESSION DATA DIAGNOSTIC TOOL")
print("=" * 80)
print()
print("This script helps diagnose why data appears to be cut off.")
print()
print("To use this tool, you need:")
print("  1. The path to the log archive file")
print("  2. The session start time")
print("  3. The session end time")
print("  4. The timezone used for parsing")
print()

# Example values (update these with actual values)
EXAMPLE_ARCHIVE = "/app/uploads/your_log_file.tar.bz2"
EXAMPLE_START = "2025-10-28 09:44:07.163363+00:00"
EXAMPLE_END = "2025-10-28 10:05:14.218108+00:00"
EXAMPLE_TIMEZONE = "UTC"

print(f"Example Usage:")
print(f"  Archive: {EXAMPLE_ARCHIVE}")
print(f"  Start: {EXAMPLE_START}")
print(f"  End: {EXAMPLE_END}")
print(f"  Timezone: {EXAMPLE_TIMEZONE}")
print()

# Get user input or use examples
archive_path = input(f"Enter archive path (or press Enter for example): ").strip()
if not archive_path:
    archive_path = EXAMPLE_ARCHIVE

start_time = input(f"Enter session start (or press Enter for example): ").strip()
if not start_time:
    start_time = EXAMPLE_START

end_time = input(f"Enter session end (or press Enter for example): ").strip()
if not end_time:
    end_time = EXAMPLE_END

timezone = input(f"Enter timezone (or press Enter for UTC): ").strip()
if not timezone:
    timezone = EXAMPLE_TIMEZONE

print()
print("=" * 80)
print("RUNNING DIAGNOSTICS...")
print("=" * 80)
print()

# Check if file exists
if not os.path.exists(archive_path):
    print(f"✗ Archive file not found: {archive_path}")
    print()
    print("Please provide the correct path to the archive file.")
    print("You can find it by checking the Analysis record in the database:")
    print("  SELECT file_path FROM log_files WHERE id = <log_file_id>;")
    sys.exit(1)

print(f"✓ Archive file found: {archive_path}")
print(f"  Size: {os.path.getsize(archive_path) / 1024 / 1024:.2f} MB")
print()

# Parse timestamps
from dateutil import parser as date_parser
start_dt = date_parser.parse(start_time)
end_dt = date_parser.parse(end_time)

print(f"Session Time Range:")
print(f"  Start: {start_dt}")
print(f"  End:   {end_dt}")
print(f"  Duration: {(end_dt - start_dt).total_seconds() / 60:.2f} minutes")
print()

# Check archive file list
print("Archive File Analysis:")
print("-" * 80)

try:
    from backend.archive_filter import ArchiveFilter

    filter_obj = ArchiveFilter(archive_path)
    file_list = filter_obj.get_file_list()

    print(f"Total files in archive: {len(file_list)}")

    if file_list:
        # Find files in session range
        files_in_range = []
        for filename, mtime in file_list:
            # Make timezone-aware for comparison
            import pytz
            if mtime.tzinfo is None:
                mtime = pytz.UTC.localize(mtime)
            if start_dt.tzinfo is None:
                check_start = pytz.UTC.localize(start_dt)
                check_end = pytz.UTC.localize(end_dt)
            else:
                check_start = start_dt
                check_end = end_dt

            if check_start <= mtime <= check_end:
                files_in_range.append((filename, mtime))

        print(f"Files within session time range: {len(files_in_range)}")

        if files_in_range:
            print()
            print("Files in range:")
            for filename, mtime in sorted(files_in_range, key=lambda x: x[1]):
                print(f"  {mtime.strftime('%Y-%m-%d %H:%M:%S')} - {filename}")
        else:
            print()
            print("⚠ WARNING: No files found within session time range!")
            print("This means archive filtering would exclude ALL files.")
            print()
            print("Files closest to session:")
            # Find closest files
            sorted_files = sorted(file_list, key=lambda x: x[1])
            for filename, mtime in sorted_files[-5:]:
                if mtime.tzinfo is None:
                    mtime = pytz.UTC.localize(mtime)
                print(f"  {mtime.strftime('%Y-%m-%d %H:%M:%S')} - {filename}")

except Exception as e:
    print(f"✗ Error analyzing archive: {e}")
    import traceback
    traceback.print_exc()

print()
print("=" * 80)
print("NEXT STEPS")
print("=" * 80)
print()
print("If files ARE in range:")
print("  → The issue is with log content parsing or timezone mismatch")
print("  → Check what timezone was used for the original analysis")
print("  → Try running drill-down with different timezone")
print()
print("If NO files are in range:")
print("  → Archive filtering is excluding all relevant files")
print("  → The file modification times don't match log entry times")
print("  → Consider increasing buffer_hours or disabling filtering")
print()
