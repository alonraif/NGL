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
        Returns path to extracted directory
        """
        self.temp_dir = tempfile.mkdtemp(prefix='lula_')

        # Detect compression and extract
        if archive_path.endswith('.bz2'):
            # Use tar with bzip2
            cmd = ['tar', 'xjf', archive_path, '-C', self.temp_dir]
        elif archive_path.endswith('.gz'):
            cmd = ['tar', 'xzf', archive_path, '-C', self.temp_dir]
        else:
            cmd = ['tar', 'xf', archive_path, '-C', self.temp_dir]

        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode != 0:
            raise Exception(f"Failed to extract archive: {result.stderr}")

        return self.temp_dir

    def find_messages_log(self, directory):
        """
        Find messages.log file in extracted directory
        Returns path to messages.log
        """
        for root, dirs, files in os.walk(directory):
            for file in files:
                if file == 'messages.log':
                    return os.path.join(root, file)

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
