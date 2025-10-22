"""
Archive Pre-filtering Utility

This module provides functionality to filter compressed log archives by time range
before passing them to lula2.py for parsing. This significantly improves performance
by reducing the amount of data lula2.py needs to process.

Key Features:
- Filter by time range (with configurable buffer before/after)
- Filter by session (keep only files within session time range)
- Preserve original archive format (tar.bz2, tar.gz, zip)
- Fallback to original archive if filtering fails
"""

import os
import tarfile
import zipfile
import tempfile
import logging
from datetime import datetime, timedelta
from typing import List, Tuple, Optional

logger = logging.getLogger(__name__)


class ArchiveFilter:
    """Handles filtering of compressed log archives based on time ranges."""

    def __init__(self, archive_path: str):
        """
        Initialize the archive filter.

        Args:
            archive_path: Path to the original archive file
        """
        self.archive_path = archive_path
        self.archive_format = self._detect_format()

    def _detect_format(self) -> str:
        """Detect the archive format based on file extension or magic bytes."""
        # First try by extension
        if self.archive_path.endswith('.tar.bz2') or self.archive_path.endswith('.bz2'):
            return 'tar.bz2'
        elif self.archive_path.endswith('.tar.gz') or self.archive_path.endswith('.gz'):
            return 'tar.gz'
        elif self.archive_path.endswith('.zip'):
            return 'zip'

        # If extension doesn't match, try to detect by reading file header
        try:
            with open(self.archive_path, 'rb') as f:
                header = f.read(10)

                # Check for bzip2 magic bytes (BZ)
                if header[:2] == b'BZ':
                    return 'tar.bz2'

                # Check for gzip magic bytes (0x1f 0x8b)
                if header[:2] == b'\x1f\x8b':
                    return 'tar.gz'

                # Check for zip magic bytes (PK)
                if header[:2] == b'PK':
                    return 'zip'
        except Exception as e:
            logger.warning(f"Could not read file header: {e}")

        raise ValueError(f"Unsupported archive format: {self.archive_path}")

    def _get_file_list_tar(self) -> List[Tuple[str, datetime, object]]:
        """
        Get list of files with their modification times from tar archive.

        Returns:
            List of tuples: (filename, modification_time, tarinfo_object)
        """
        files = []
        try:
            with tarfile.open(self.archive_path, 'r:*') as tar:
                for member in tar.getmembers():
                    if member.isfile():
                        mod_time = datetime.fromtimestamp(member.mtime)
                        files.append((member.name, mod_time, member))
        except Exception as e:
            logger.error(f"Error reading tar archive: {e}")
            raise

        return files

    def _get_file_list_zip(self) -> List[Tuple[str, datetime, object]]:
        """
        Get list of files with their modification times from zip archive.

        Returns:
            List of tuples: (filename, modification_time, zipinfo_object)
        """
        files = []
        try:
            with zipfile.ZipFile(self.archive_path, 'r') as zf:
                for info in zf.infolist():
                    if not info.is_dir():
                        # Convert ZipInfo date_time tuple to datetime
                        mod_time = datetime(*info.date_time)
                        files.append((info.filename, mod_time, info))
        except Exception as e:
            logger.error(f"Error reading zip archive: {e}")
            raise

        return files

    def get_file_list(self) -> List[Tuple[str, datetime]]:
        """
        Get list of all files in archive with their modification times.

        Returns:
            List of tuples: (filename, modification_time)
        """
        if self.archive_format.startswith('tar'):
            files = self._get_file_list_tar()
        else:
            files = self._get_file_list_zip()

        # Return without the member object
        return [(name, mtime) for name, mtime, _ in files]

    def filter_by_time_range(
        self,
        start_time: datetime,
        end_time: datetime,
        buffer_hours: int = 1,
        output_path: Optional[str] = None
    ) -> str:
        """
        Create a filtered archive containing only files within the time range.

        Args:
            start_time: Start of time range
            end_time: End of time range
            buffer_hours: Hours to include before/after range (default: 1)
            output_path: Path for filtered archive (default: temp file)

        Returns:
            Path to filtered archive
        """
        logger.info(f"Filtering archive by time range: {start_time} to {end_time}")
        logger.info(f"Buffer: {buffer_hours} hour(s) before/after")

        # Add buffer
        buffered_start = start_time - timedelta(hours=buffer_hours)
        buffered_end = end_time + timedelta(hours=buffer_hours)

        try:
            if self.archive_format.startswith('tar'):
                return self._filter_tar(buffered_start, buffered_end, output_path)
            else:
                return self._filter_zip(buffered_start, buffered_end, output_path)
        except Exception as e:
            logger.error(f"Error filtering archive: {e}")
            logger.warning("Falling back to original archive")
            return self.archive_path

    def filter_by_session(
        self,
        session_start: datetime,
        session_end: datetime,
        buffer_minutes: int = 5,
        output_path: Optional[str] = None
    ) -> str:
        """
        Create a filtered archive containing only files within a session's time range.

        Args:
            session_start: Session start time
            session_end: Session end time
            buffer_minutes: Minutes to include before/after session (default: 5)
            output_path: Path for filtered archive (default: temp file)

        Returns:
            Path to filtered archive
        """
        logger.info(f"Filtering archive by session: {session_start} to {session_end}")
        logger.info(f"Buffer: {buffer_minutes} minute(s) before/after")

        # Add buffer
        buffered_start = session_start - timedelta(minutes=buffer_minutes)
        buffered_end = session_end + timedelta(minutes=buffer_minutes)

        try:
            if self.archive_format.startswith('tar'):
                return self._filter_tar(buffered_start, buffered_end, output_path)
            else:
                return self._filter_zip(buffered_start, buffered_end, output_path)
        except Exception as e:
            logger.error(f"Error filtering archive: {e}")
            logger.warning("Falling back to original archive")
            return self.archive_path

    def _filter_tar(
        self,
        start_time: datetime,
        end_time: datetime,
        output_path: Optional[str] = None
    ) -> str:
        """Filter tar archive and create new archive with selected files."""

        # Get all files with metadata
        all_files = self._get_file_list_tar()

        # Normalize timezone awareness for comparison
        # If start_time is timezone-aware, make all datetimes timezone-aware (UTC)
        # If start_time is naive, make all datetimes naive
        if start_time.tzinfo is not None:
            # start_time is timezone-aware, convert naive mtimes to UTC
            import pytz
            utc = pytz.UTC
            normalized_files = [
                (name, mtime.replace(tzinfo=utc) if mtime.tzinfo is None else mtime, member)
                for name, mtime, member in all_files
            ]
        else:
            # start_time is naive, strip timezone from any aware mtimes
            normalized_files = [
                (name, mtime.replace(tzinfo=None) if mtime.tzinfo is not None else mtime, member)
                for name, mtime, member in all_files
            ]

        # Filter files by time range
        filtered_files = [
            (name, mtime, member)
            for name, mtime, member in normalized_files
            if start_time <= mtime <= end_time
        ]

        original_count = len(all_files)
        filtered_count = len(filtered_files)

        logger.info(f"Files: {original_count} original, {filtered_count} after filtering")
        logger.info(f"Reduction: {100 * (1 - filtered_count / original_count):.1f}%")

        # If less than 20% reduction, not worth the overhead
        if filtered_count > 0.8 * original_count:
            logger.info("Less than 20% reduction, using original archive")
            return self.archive_path

        # If no files match, fall back to original
        if filtered_count == 0:
            logger.warning("No files in time range, using original archive")
            return self.archive_path

        # Create output path if not specified
        if output_path is None:
            fd, output_path = tempfile.mkstemp(suffix=f'.{self.archive_format}')
            os.close(fd)

        # Create filtered archive
        compression_mode = 'w:bz2' if self.archive_format == 'tar.bz2' else 'w:gz'

        with tarfile.open(self.archive_path, 'r:*') as src_tar:
            with tarfile.open(output_path, compression_mode) as dst_tar:
                for name, mtime, member in filtered_files:
                    # Extract file data from source
                    file_data = src_tar.extractfile(member)
                    if file_data:
                        dst_tar.addfile(member, file_data)

        logger.info(f"Created filtered archive: {output_path}")
        return output_path

    def _filter_zip(
        self,
        start_time: datetime,
        end_time: datetime,
        output_path: Optional[str] = None
    ) -> str:
        """Filter zip archive and create new archive with selected files."""

        # Get all files with metadata
        all_files = self._get_file_list_zip()

        # Normalize timezone awareness for comparison
        if start_time.tzinfo is not None:
            # start_time is timezone-aware, convert naive mtimes to UTC
            import pytz
            utc = pytz.UTC
            normalized_files = [
                (name, mtime.replace(tzinfo=utc) if mtime.tzinfo is None else mtime, info)
                for name, mtime, info in all_files
            ]
        else:
            # start_time is naive, strip timezone from any aware mtimes
            normalized_files = [
                (name, mtime.replace(tzinfo=None) if mtime.tzinfo is not None else mtime, info)
                for name, mtime, info in all_files
            ]

        # Filter files by time range
        filtered_files = [
            (name, mtime, info)
            for name, mtime, info in normalized_files
            if start_time <= mtime <= end_time
        ]

        original_count = len(all_files)
        filtered_count = len(filtered_files)

        logger.info(f"Files: {original_count} original, {filtered_count} after filtering")
        logger.info(f"Reduction: {100 * (1 - filtered_count / original_count):.1f}%")

        # If less than 20% reduction, not worth the overhead
        if filtered_count > 0.8 * original_count:
            logger.info("Less than 20% reduction, using original archive")
            return self.archive_path

        # If no files match, fall back to original
        if filtered_count == 0:
            logger.warning("No files in time range, using original archive")
            return self.archive_path

        # Create output path if not specified
        if output_path is None:
            fd, output_path = tempfile.mkstemp(suffix='.zip')
            os.close(fd)

        # Create filtered archive
        with zipfile.ZipFile(self.archive_path, 'r') as src_zip:
            with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as dst_zip:
                for name, mtime, info in filtered_files:
                    data = src_zip.read(info.filename)
                    dst_zip.writestr(info, data)

        logger.info(f"Created filtered archive: {output_path}")
        return output_path

    def get_statistics(self) -> dict:
        """
        Get statistics about the archive.

        Returns:
            Dictionary with archive statistics
        """
        files = self.get_file_list()

        if not files:
            return {
                'total_files': 0,
                'earliest_file': None,
                'latest_file': None,
                'time_span_hours': 0
            }

        mod_times = [mtime for _, mtime in files]
        earliest = min(mod_times)
        latest = max(mod_times)
        time_span = (latest - earliest).total_seconds() / 3600

        return {
            'total_files': len(files),
            'earliest_file': earliest.isoformat(),
            'latest_file': latest.isoformat(),
            'time_span_hours': round(time_span, 2)
        }


def filter_archive_for_analysis(
    archive_path: str,
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None,
    buffer_hours: int = 1
) -> str:
    """
    Convenience function to filter an archive for analysis.

    Args:
        archive_path: Path to original archive
        start_time: Start of time range (None = no filtering)
        end_time: End of time range (None = no filtering)
        buffer_hours: Hours to include before/after range

    Returns:
        Path to filtered archive (or original if no filtering needed)
    """
    # If no time range specified, return original
    if start_time is None or end_time is None:
        logger.info("No time range specified, using original archive")
        return archive_path

    # Create filter and apply
    filter_obj = ArchiveFilter(archive_path)
    return filter_obj.filter_by_time_range(start_time, end_time, buffer_hours)


if __name__ == '__main__':
    # Test with sample log file
    logging.basicConfig(level=logging.INFO)

    # Support both local and Docker paths
    sample_path = '/app/test_logs/sample.tar.bz2'
    if not os.path.exists(sample_path):
        sample_path = '/Users/alonraif/Code/ngl/test_logs/sample.tar.bz2'

    if os.path.exists(sample_path):
        print("Testing archive filtering with sample log file...")
        print()

        # Get statistics
        filter_obj = ArchiveFilter(sample_path)
        stats = filter_obj.get_statistics()

        print("Archive Statistics:")
        print(f"  Total files: {stats['total_files']}")
        print(f"  Earliest file: {stats['earliest_file']}")
        print(f"  Latest file: {stats['latest_file']}")
        print(f"  Time span: {stats['time_span_hours']} hours")
        print()

        # Test filtering to a specific date range
        # Based on the sample output, files range from Nov 2024 to Sep 2025
        # Let's filter to just August 2025
        test_start = datetime(2025, 8, 1, 0, 0, 0)
        test_end = datetime(2025, 8, 31, 23, 59, 59)

        print(f"Testing filter: {test_start} to {test_end}")
        filtered_path = filter_obj.filter_by_time_range(test_start, test_end, buffer_hours=0)

        print(f"Filtered archive: {filtered_path}")

        if filtered_path != sample_path:
            # Get stats of filtered archive
            filtered_obj = ArchiveFilter(filtered_path)
            filtered_stats = filtered_obj.get_statistics()

            print()
            print("Filtered Archive Statistics:")
            print(f"  Total files: {filtered_stats['total_files']}")
            print(f"  Earliest file: {filtered_stats['earliest_file']}")
            print(f"  Latest file: {filtered_stats['latest_file']}")
            print(f"  Time span: {filtered_stats['time_span_hours']} hours")

            # Compare sizes
            original_size = os.path.getsize(sample_path)
            filtered_size = os.path.getsize(filtered_path)
            reduction = 100 * (1 - filtered_size / original_size)

            print()
            print(f"Original size: {original_size / 1024 / 1024:.2f} MB")
            print(f"Filtered size: {filtered_size / 1024 / 1024:.2f} MB")
            print(f"Size reduction: {reduction:.1f}%")

            # Clean up temp file
            if filtered_path.startswith('/tmp'):
                os.remove(filtered_path)
                print(f"\nCleaned up temp file: {filtered_path}")
    else:
        print(f"Sample file not found: {sample_path}")
