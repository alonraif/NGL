"""
System parsers for memory, grading, and other system metrics
"""
import re
from datetime import datetime
from .base import BaseParser


class SystemParser(BaseParser):
    """Parser for system metrics (memory, CPU, grading, etc.)"""

    # Patterns for system metrics
    MEMORY_PATTERN = re.compile(
        r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}).*?'
        r'memory.*?(\d+)\s*(MB|KB|GB|bytes)',
        re.IGNORECASE
    )

    GRADING_PATTERN = re.compile(
        r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}).*?'
        r'(?:grade|level|quality)[:\s]*([A-Za-z0-9]+)',
        re.IGNORECASE
    )

    def parse(self, log_path, timezone='US/Eastern', begin_date=None, end_date=None):
        """
        Parse system metrics based on mode

        Modes:
        - memory: Memory consumption data
        - grading: Service level transitions
        """
        data_points = []
        raw_lines = []

        with open(log_path, 'r', encoding='utf-8', errors='ignore') as f:
            for line in f:
                if self.mode == 'memory':
                    # Look for memory information
                    if 'memory' in line.lower():
                        raw_lines.append(line.strip())

                        match = self.MEMORY_PATTERN.search(line)
                        if match:
                            timestamp = match.group(1)
                            value = match.group(2)
                            unit = match.group(3)

                            # Convert to MB for consistency
                            value_mb = self._convert_to_mb(int(value), unit)

                            # Date filtering
                            if self._in_date_range(timestamp, begin_date, end_date):
                                data_points.append({
                                    'datetime': timestamp,
                                    'memory_mb': value_mb,
                                    'original_value': f"{value} {unit}"
                                })

                elif self.mode == 'grading':
                    # Look for grading/quality information
                    if any(keyword in line.lower() for keyword in ['grade', 'level', 'quality']):
                        raw_lines.append(line.strip())

                        match = self.GRADING_PATTERN.search(line)
                        if match:
                            timestamp = match.group(1)
                            grade = match.group(2)

                            # Date filtering
                            if self._in_date_range(timestamp, begin_date, end_date):
                                data_points.append({
                                    'datetime': timestamp,
                                    'grade': grade
                                })

        raw_output = '\n'.join(raw_lines)

        return {
            'raw_output': raw_output,
            'parsed_data': data_points
        }

    def _convert_to_mb(self, value, unit):
        """Convert memory value to MB"""
        unit = unit.upper()
        if unit == 'KB':
            return value / 1024
        elif unit == 'GB':
            return value * 1024
        elif unit == 'BYTES':
            return value / (1024 * 1024)
        else:  # MB
            return value

    def _in_date_range(self, timestamp, begin_date, end_date):
        """Check if timestamp is within date range"""
        if not begin_date and not end_date:
            return True

        try:
            dt = datetime.strptime(timestamp, '%Y-%m-%d %H:%M:%S')

            if begin_date:
                begin_dt = datetime.strptime(begin_date, '%Y-%m-%d %H:%M:%S')
                if dt < begin_dt:
                    return False

            if end_date:
                end_dt = datetime.strptime(end_date, '%Y-%m-%d %H:%M:%S')
                if dt > end_dt:
                    return False

            return True
        except:
            return True
