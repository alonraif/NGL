"""
Bandwidth parser for bw, md-bw, md-db-bw modes
"""
import re
from datetime import datetime
from .base import BaseParser


class BandwidthParser(BaseParser):
    """Parser for bandwidth-related modes"""

    # Pre-compiled regex patterns for bandwidth extraction (class-level for performance)
    BW_PATTERN = re.compile(
        r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}).*?'
        r'bitrate.*?(\d+).*?video.*?(\d+)',
        re.IGNORECASE
    )

    # Fast keyword check (avoid regex on every line)
    _KEYWORD = 'bitrate'

    def parse(self, log_path, timezone='US/Eastern', begin_date=None, end_date=None):
        """
        Parse bandwidth data from messages.log

        Returns CSV-formatted data with datetime, total bitrate, video bitrate
        """
        bandwidth_data = []

        with open(log_path, 'r', encoding='utf-8', errors='ignore') as f:
            for line in f:
                # Fast keyword pre-filter (avoid regex on irrelevant lines)
                if self._KEYWORD not in line.lower():
                    continue

                # Look for bandwidth information with regex
                match = self.BW_PATTERN.search(line)
                if match:
                    timestamp = match.group(1)
                    total_bitrate = match.group(2)
                    video_bitrate = match.group(3)

                    # Date filtering
                    if begin_date or end_date:
                        try:
                            dt = datetime.strptime(timestamp, '%Y-%m-%d %H:%M:%S')
                            if begin_date:
                                begin_dt = datetime.strptime(begin_date, '%Y-%m-%d %H:%M:%S')
                                if dt < begin_dt:
                                    continue
                            if end_date:
                                end_dt = datetime.strptime(end_date, '%Y-%m-%d %H:%M:%S')
                                if dt > end_dt:
                                    continue
                        except ValueError:
                            pass

                    bandwidth_data.append({
                        'datetime': timestamp,
                        'total_bitrate': total_bitrate,
                        'video_bitrate': video_bitrate,
                        'notes': ''
                    })

        # Format as CSV
        csv_lines = ['datetime,total bitrate,video bitrate,notes']
        for entry in bandwidth_data:
            csv_lines.append(
                f"{entry['datetime']},{entry['total_bitrate']},{entry['video_bitrate']},{entry['notes']}"
            )

        # Add stream end marker
        if bandwidth_data:
            csv_lines.append('0,0,0,Stream end')

        raw_output = '\n'.join(csv_lines)

        # Parse CSV into structured data for frontend
        parsed_data = []
        for entry in bandwidth_data:
            parsed_data.append({
                'datetime': entry['datetime'],
                'total bitrate': entry['total_bitrate'],
                'video bitrate': entry['video_bitrate'],
                'notes': entry['notes']
            })

        return {
            'raw_output': raw_output,
            'parsed_data': parsed_data
        }
