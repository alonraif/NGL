"""
Base parser class for all log parsers
"""
import os
import tempfile
import subprocess
from abc import ABC, abstractmethod


class BaseParser(ABC):
    """Base class for all log parsers"""

    def __init__(self, mode):
        self.mode = mode
        self.temp_dir = None

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
        Find messages.log file in extracted directory
        Handles compressed files (.log.gz, .log.bz2)
        Returns path to messages.log
        """
        import gzip
        import bz2

        for root, dirs, files in os.walk(directory):
            for file in files:
                filepath = os.path.join(root, file)

                # Direct match
                if file == 'messages.log':
                    return filepath

                # Compressed with gz
                elif file.endswith('messages.log.gz') or file == 'messages.log.gz':
                    decompressed_path = filepath[:-3]  # Remove .gz
                    with gzip.open(filepath, 'rb') as f_in:
                        with open(decompressed_path, 'wb') as f_out:
                            import shutil
                            shutil.copyfileobj(f_in, f_out)
                    return decompressed_path

                # Compressed with bz2
                elif file.endswith('messages.log.bz2') or file == 'messages.log.bz2':
                    decompressed_path = filepath[:-4]  # Remove .bz2
                    with bz2.open(filepath, 'rb') as f_in:
                        with open(decompressed_path, 'wb') as f_out:
                            import shutil
                            shutil.copyfileobj(f_in, f_out)
                    return decompressed_path

        raise FileNotFoundError("messages.log not found in archive")

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
