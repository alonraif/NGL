#!/usr/bin/env python3
"""
Performance optimizations for log processing
"""
import subprocess
import os
import hashlib
import pickle
from functools import lru_cache

# Simple file-based cache
CACHE_DIR = '/app/temp/cache'
os.makedirs(CACHE_DIR, exist_ok=True)

def get_file_hash(filepath):
    """Get MD5 hash of file for caching"""
    hash_md5 = hashlib.md5()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()

def get_cache_key(filepath, parse_mode, timezone, begin_date, end_date):
    """Generate cache key for a processing request"""
    file_hash = get_file_hash(filepath)
    params = f"{file_hash}_{parse_mode}_{timezone}_{begin_date}_{end_date}"
    return hashlib.md5(params.encode()).hexdigest()

def get_cached_result(cache_key):
    """Retrieve cached result if available"""
    cache_file = os.path.join(CACHE_DIR, f"{cache_key}.pkl")
    if os.path.exists(cache_file):
        # Check if cache is less than 1 hour old
        if (os.path.getmtime(cache_file) - os.path.getctime(cache_file)) < 3600:
            try:
                with open(cache_file, 'rb') as f:
                    return pickle.load(f)
            except:
                pass
    return None

def save_cached_result(cache_key, result):
    """Save result to cache"""
    cache_file = os.path.join(CACHE_DIR, f"{cache_key}.pkl")
    try:
        with open(cache_file, 'wb') as f:
            pickle.dump(result, f)
    except:
        pass

def optimize_command(cmd):
    """Optimize lula2.py command for better performance"""
    # Add pypy3 if available (faster Python interpreter)
    if os.path.exists('/usr/bin/pypy3'):
        cmd[0] = 'pypy3'
    return cmd

def process_with_streaming_output(cmd, progress_callback=None):
    """
    Run subprocess with real-time output streaming for progress tracking
    """
    process = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1,
        universal_newlines=True
    )

    stdout_lines = []
    stderr_lines = []

    # Read output line by line
    while True:
        output = process.stdout.readline()
        if output == '' and process.poll() is not None:
            break
        if output:
            stdout_lines.append(output.strip())
            if progress_callback:
                # Estimate progress based on output lines
                progress_callback(len(stdout_lines))

    stderr = process.stderr.read()
    if stderr:
        stderr_lines.append(stderr)

    return_code = process.poll()
    stdout = '\n'.join(stdout_lines)
    stderr = '\n'.join(stderr_lines)

    return stdout, stderr, return_code

def parallel_extract(tar_file, dest_dir):
    """
    Extract tar file using parallel processing if pbzip2 available
    """
    # Check if pbzip2 (parallel bzip2) is available
    if os.path.exists('/usr/bin/pbzip2'):
        cmd = f"pbzip2 -dc {tar_file} | tar -x -C {dest_dir}"
        os.system(cmd)
    else:
        # Fallback to regular extraction
        import tarfile
        with tarfile.open(tar_file, 'r:bz2') as tar:
            tar.extractall(dest_dir)

# LRU cache for parse mode metadata
@lru_cache(maxsize=128)
def get_parse_mode_info(mode):
    """Cached parse mode information"""
    modes = {
        'known': {'complexity': 'low', 'est_time': 5},
        'error': {'complexity': 'low', 'est_time': 5},
        'all': {'complexity': 'high', 'est_time': 30},
        'md': {'complexity': 'medium', 'est_time': 15},
        'bw': {'complexity': 'medium', 'est_time': 15},
        'sessions': {'complexity': 'low', 'est_time': 10},
    }
    return modes.get(mode, {'complexity': 'medium', 'est_time': 15})

def estimate_processing_time(file_size_mb, parse_mode):
    """Estimate processing time based on file size and mode"""
    info = get_parse_mode_info(parse_mode)
    base_time = info['est_time']

    # Adjust for file size (roughly 5 seconds per 10MB)
    size_factor = file_size_mb / 10
    estimated = base_time + (size_factor * 5)

    return int(estimated)
