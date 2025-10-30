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

    # Pre-compile patterns at class level for performance (compile once, use many times)
    _COMPILED_KNOWN = [re.compile(p, re.IGNORECASE) for p in KNOWN_ERRORS]
    _COMPILED_VERBOSE = [re.compile(p, re.IGNORECASE) for p in VERBOSE_ERRORS]
    _COMPILED_ERROR = [re.compile(r'ERROR', re.IGNORECASE)]

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

        # Use pre-compiled patterns for performance
        if self.mode == 'known':
            patterns = self._COMPILED_KNOWN
        elif self.mode == 'error':
            patterns = self._COMPILED_ERROR
        elif self.mode == 'v':
            patterns = self._COMPILED_VERBOSE
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
            # Match ISO 8601 format: 2025-09-26T12:15:30.207700+00:00
            timestamp_pattern = re.compile(r'(\d{4}-\d{2}-\d{2})[T ](\d{2}:\d{2}:\d{2})')

            for line in matched_lines:
                match = timestamp_pattern.search(line)
                if match:
                    try:
                        from dateutil import parser as date_parser

                        # Combine date and time parts
                        timestamp_str = f"{match.group(1)} {match.group(2)}"
                        dt = datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S')

                        if begin_date:
                            # Use dateutil.parser for flexible parsing (handles microseconds, timezones)
                            begin_dt = date_parser.parse(begin_date)
                            if begin_dt.tzinfo is not None:
                                begin_dt = begin_dt.replace(tzinfo=None)
                            if dt < begin_dt:
                                continue

                        if end_date:
                            # Use dateutil.parser for flexible parsing (handles microseconds, timezones)
                            end_dt = date_parser.parse(end_date)
                            if end_dt.tzinfo is not None:
                                end_dt = end_dt.replace(tzinfo=None)
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
