"""
Error parsers for known, error, v, all modes
"""
import re
from datetime import datetime
from .base import BaseParser


class ErrorParser(BaseParser):
    """Parser for error and event logs"""

    # Known error patterns (subset - add more as needed)
    KNOWN_ERRORS = [
        r'error',
        r'failed',
        r'exception',
        r'critical',
        r'fatal',
        r'warning',
        r'timeout',
        r'disconnect',
        r'connection lost',
        r'unable to',
        r'could not',
        r'cannot',
    ]

    # Verbose error patterns (more inclusive)
    VERBOSE_ERRORS = KNOWN_ERRORS + [
        r'retry',
        r'attempt',
        r'invalid',
        r'missing',
        r'denied',
        r'refused',
        r'rejected',
    ]

    def parse(self, log_path, timezone='US/Eastern', begin_date=None, end_date=None):
        """
        Parse error/event logs based on mode

        Modes:
        - known: Small set of known errors
        - error: Any line containing 'ERROR'
        - v: Verbose - more common errors
        - all: Return all log lines
        """
        matched_lines = []
        all_lines = []

        # Compile patterns based on mode
        if self.mode == 'known':
            patterns = [re.compile(p, re.IGNORECASE) for p in self.KNOWN_ERRORS]
        elif self.mode == 'error':
            patterns = [re.compile(r'ERROR', re.IGNORECASE)]
        elif self.mode == 'v':
            patterns = [re.compile(p, re.IGNORECASE) for p in self.VERBOSE_ERRORS]
        else:  # all
            patterns = None

        with open(log_path, 'r', encoding='utf-8', errors='ignore') as f:
            for line in f:
                all_lines.append(line.rstrip())

                # For 'all' mode, include everything
                if self.mode == 'all':
                    matched_lines.append(line.rstrip())
                    continue

                # For other modes, filter by patterns
                if patterns:
                    for pattern in patterns:
                        if pattern.search(line):
                            matched_lines.append(line.rstrip())
                            break

        # Date filtering
        if begin_date or end_date:
            filtered = []
            timestamp_pattern = re.compile(r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})')

            for line in matched_lines:
                match = timestamp_pattern.search(line)
                if match:
                    try:
                        dt = datetime.strptime(match.group(1), '%Y-%m-%d %H:%M:%S')

                        if begin_date:
                            begin_dt = datetime.strptime(begin_date, '%Y-%m-%d %H:%M:%S')
                            if dt < begin_dt:
                                continue

                        if end_date:
                            end_dt = datetime.strptime(end_date, '%Y-%m-%d %H:%M:%S')
                            if dt > end_dt:
                                continue

                        filtered.append(line)
                    except:
                        # If timestamp parsing fails, include the line
                        filtered.append(line)
                else:
                    # No timestamp found, include the line
                    filtered.append(line)

            matched_lines = filtered

        raw_output = '\n'.join(matched_lines)

        # For error modes, structured data is just the lines with some metadata
        parsed_data = {
            'total_lines': len(all_lines),
            'matched_lines': len(matched_lines),
            'mode': self.mode,
            'lines': matched_lines[:1000]  # Limit to first 1000 for performance
        }

        return {
            'raw_output': raw_output,
            'parsed_data': parsed_data
        }
