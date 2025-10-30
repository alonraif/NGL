"""
Sessions parser for sessions mode
"""
import re
from datetime import datetime
from .base import BaseParser


class SessionsParser(BaseParser):
    """Parser for streaming sessions"""

    # Patterns for session extraction
    SESSION_START = re.compile(r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}).*?session.*?start', re.IGNORECASE)
    SESSION_END = re.compile(r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}).*?session.*?end', re.IGNORECASE)
    SESSION_ID = re.compile(r'session[_\s]*id[:\s]*([a-zA-Z0-9-]+)', re.IGNORECASE)
    BITRATE = re.compile(r'bitrate[:\s]*(\d+)', re.IGNORECASE)
    DURATION = re.compile(r'duration[:\s]*(\d+)', re.IGNORECASE)

    def parse(self, log_path, timezone='US/Eastern', begin_date=None, end_date=None):
        """
        Parse streaming session information from messages.log

        Returns list of sessions with start/end times, duration, bitrate
        """
        sessions = []
        current_session = None
        raw_lines = []

        with open(log_path, 'r', encoding='utf-8', errors='ignore') as f:
            for line in f:
                if 'session' in line.lower():
                    raw_lines.append(line.strip())

                    # Session start
                    start_match = self.SESSION_START.search(line)
                    if start_match:
                        if current_session:
                            # Save previous session
                            sessions.append(current_session)

                        current_session = {
                            'start_time': start_match.group(1),
                            'end_time': None,
                            'duration': None,
                            'session_id': None,
                            'avg_bitrate': None
                        }

                        # Extract session ID if present
                        id_match = self.SESSION_ID.search(line)
                        if id_match:
                            current_session['session_id'] = id_match.group(1)

                    # Session end
                    end_match = self.SESSION_END.search(line)
                    if end_match and current_session:
                        current_session['end_time'] = end_match.group(1)

                        # Try to extract duration
                        duration_match = self.DURATION.search(line)
                        if duration_match:
                            current_session['duration'] = int(duration_match.group(1))
                        elif current_session['start_time']:
                            # Calculate duration
                            try:
                                start = datetime.strptime(current_session['start_time'], '%Y-%m-%d %H:%M:%S')
                                end = datetime.strptime(current_session['end_time'], '%Y-%m-%d %H:%M:%S')
                                current_session['duration'] = int((end - start).total_seconds())
                            except:
                                pass

                        # Extract bitrate
                        bitrate_match = self.BITRATE.search(line)
                        if bitrate_match:
                            current_session['avg_bitrate'] = int(bitrate_match.group(1))

                        sessions.append(current_session)
                        current_session = None

        # Save last session if still open
        if current_session:
            sessions.append(current_session)

        # Date filtering
        if begin_date or end_date:
            from dateutil import parser as date_parser

            filtered = []
            for session in sessions:
                try:
                    start_dt = datetime.strptime(session['start_time'], '%Y-%m-%d %H:%M:%S')

                    if begin_date:
                        # Use dateutil.parser for flexible parsing (handles microseconds, timezones)
                        begin_dt = date_parser.parse(begin_date)
                        if begin_dt.tzinfo is not None:
                            begin_dt = begin_dt.replace(tzinfo=None)
                        if start_dt < begin_dt:
                            continue

                    if end_date:
                        # Use dateutil.parser for flexible parsing (handles microseconds, timezones)
                        end_dt = date_parser.parse(end_date)
                        if end_dt.tzinfo is not None:
                            end_dt = end_dt.replace(tzinfo=None)
                        if start_dt > end_dt:
                            continue

                    filtered.append(session)
                except:
                    filtered.append(session)

            sessions = filtered

        raw_output = '\n'.join(raw_lines)

        return {
            'raw_output': raw_output,
            'parsed_data': sessions
        }
