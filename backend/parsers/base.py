"""
Base parser class for all log parsers
"""
import os
import tempfile
import subprocess
import threading
from abc import ABC, abstractmethod


class CancellationException(Exception):
    """Exception raised when parsing is cancelled"""
    pass


class BaseParser(ABC):
    """Base class for all log parsers"""

    def __init__(self, mode):
        self.mode = mode
        self.temp_dir = None
        self.cancelled = threading.Event()  # Cancellation flag for in-process cancellation
        self._check_interval = 1000  # Check cancellation every N lines

    def extract_logs(self, archive_path):
        """
        Extract log archive to temporary directory
        Uses parallel decompression (pbzip2/pigz) when available for speed
        Returns path to extracted directory
        """
        self.temp_dir = tempfile.mkdtemp(prefix='lula_')

        # Detect compression and extract with parallel decompression if available
        if archive_path.endswith('.bz2'):
            # Try pbzip2 (parallel bzip2) first, fallback to standard bzip2
            try:
                cmd = ['tar', '-I', 'pbzip2', '-xf', archive_path, '-C', self.temp_dir]
                result = subprocess.run(cmd, capture_output=True, text=True)
                if result.returncode != 0:
                    raise Exception()  # Fallback to standard
            except:
                cmd = ['tar', 'xjf', archive_path, '-C', self.temp_dir]
                result = subprocess.run(cmd, capture_output=True, text=True)

        elif archive_path.endswith('.gz'):
            # Try pigz (parallel gzip) first, fallback to standard gzip
            try:
                cmd = ['tar', '-I', 'pigz', '-xf', archive_path, '-C', self.temp_dir]
                result = subprocess.run(cmd, capture_output=True, text=True)
                if result.returncode != 0:
                    raise Exception()  # Fallback to standard
            except:
                cmd = ['tar', 'xzf', archive_path, '-C', self.temp_dir]
                result = subprocess.run(cmd, capture_output=True, text=True)
        else:
            cmd = ['tar', 'xf', archive_path, '-C', self.temp_dir]
            result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode != 0:
            raise Exception(f"Failed to extract archive: {result.stderr}")

        return self.temp_dir

    def find_messages_log(self, directory):
        """
        Find ALL messages.log files in extracted directory (including rotated logs)
        Handles compressed files (.log.gz, .log.bz2) and rotated logs (messages.log.N.gz)
        Combines all logs into a single file and returns path
        """
        import gzip
        import bz2
        import shutil
        import re

        messages_files = []

        # Find all messages.log* files
        for root, dirs, files in os.walk(directory):
            for file in files:
                # Match messages.log, messages.log.N, messages.log.N.gz, messages.log.N.bz2, etc
                if file == 'messages.log' or file.startswith('messages.log.'):
                    filepath = os.path.join(root, file)
                    messages_files.append(filepath)

        if not messages_files:
            raise FileNotFoundError("No messages.log files found in archive")

        # Sort files numerically (messages.log.1, messages.log.2, ... messages.log.90)
        # messages.log (no number) should come last (most recent)
        def sort_key(path):
            filename = os.path.basename(path)
            # Extract number from messages.log.N or messages.log.N.gz
            match = re.search(r'messages\.log\.(\d+)', filename)
            if match:
                return int(match.group(1))
            else:
                # messages.log without number = most recent = last
                return 999999

        messages_files.sort(key=sort_key)

        # Combined output file
        combined_path = os.path.join(directory, 'combined_messages.log')

        # Decompress and concatenate all log files
        with open(combined_path, 'wb') as combined:
            for filepath in messages_files:
                try:
                    if filepath.endswith('.gz'):
                        with gzip.open(filepath, 'rb') as f:
                            shutil.copyfileobj(f, combined)
                    elif filepath.endswith('.bz2'):
                        with bz2.open(filepath, 'rb') as f:
                            shutil.copyfileobj(f, combined)
                    else:
                        with open(filepath, 'rb') as f:
                            shutil.copyfileobj(f, combined)
                except Exception as e:
                    # Log decompression error but continue with other files
                    print(f"Warning: Failed to process {filepath}: {e}")
                    continue

        return combined_path

    def cancel(self):
        """Signal the parser to stop processing"""
        self.cancelled.set()

    def check_cancelled(self):
        """Check if cancellation was requested and raise exception if so"""
        if self.cancelled.is_set():
            raise CancellationException("Parsing cancelled by user")

    def cleanup(self):
        """Clean up temporary files"""
        if self.temp_dir and os.path.exists(self.temp_dir):
            import shutil
            shutil.rmtree(self.temp_dir)

    @abstractmethod
    def parse(self, log_path, timezone='US/Eastern', begin_date=None, end_date=None):
        """
        Parse the log file and return structured data

        Args:
            log_path: Path to messages.log file or directory containing it
            timezone: Timezone for date parsing
            begin_date: Optional start date filter
            end_date: Optional end date filter

        Returns:
            dict with 'raw_output' (string) and 'parsed_data' (list/dict)
        """
        pass

    def process(self, archive_path, timezone='US/Eastern', begin_date=None, end_date=None):
        """
        Full processing pipeline: extract, parse, cleanup

        Args:
            archive_path: Path to compressed log archive
            timezone: Timezone for date parsing
            begin_date: Optional start date filter
            end_date: Optional end date filter

        Returns:
            dict with 'raw_output' and 'parsed_data'
        """
        try:
            # Extract archive
            extracted_dir = self.extract_logs(archive_path)

            # Find messages.log
            log_path = self.find_messages_log(extracted_dir)

            # Parse
            result = self.parse(log_path, timezone, begin_date, end_date)

            return result

        finally:
            # Always cleanup
            self.cleanup()
