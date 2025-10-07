"""Native implementation of the sessions parser."""
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

try:  # pragma: no cover
    from dateutil import parser as dateutil_parser
    import pytz
except ImportError:  # pragma: no cover
    dateutil_parser = None
    pytz = None

from .base import BaseParser, DateRange
from .lula_wrapper import SessionsParser as LegacySessionsParser


@dataclass
class Session:
    session_id: Optional[str]
    start: Optional[str]
    end: Optional[str]

    @property
    def duration(self) -> Optional[float]:
        if not self.start or not self.end:
            return None
        from datetime import datetime

        try:
            start_dt = datetime.fromisoformat(self.start)
            end_dt = datetime.fromisoformat(self.end)
            return (end_dt - start_dt).total_seconds()
        except ValueError:
            return None

    def as_dict(self):
        status = "Complete" if self.start and self.end else "Start Only" if self.start else "End Only"
        return {
            'session_id': self.session_id,
            'start': self.start,
            'end': self.end,
            'duration_seconds': self.duration,
            'status': status
        }


class SessionsParser(BaseParser):
    """Reimplementation of Lula2 session tracking."""

    START_PATTERNS = [
        '>>> Stream start',
        '<~~ Stream start',
        '<~ Stream start'
    ]
    END_PATTERNS = [
        '~~~ Stream stop',
        '~> Stream end',
        '~~> Stream stop',
        'Stream ended',
    ]

    SESSION_ID_PATTERNS = [
        ' session id: ',
        ' (session id:'
    ]

    def parse(self, archive_path: str, *, timezone: str, begin_date: Optional[str], end_date: Optional[str]):
        if dateutil_parser is None or pytz is None:
            raise RuntimeError("dateutil and pytz are required for SessionsParser")

        daterange = DateRange(begin_date, end_date)
        sessions: List[Session] = []
        current_start = None
        current_session_id = None

        for log_line in self.iter_archive(archive_path, timezone=timezone):
            self.ensure_not_cancelled()
            dt = _parse_timestamp(log_line.line, timezone)
            if dt is None or not daterange.contains(dt):
                continue
            timestamp = dt.isoformat()

            session_id = _extract_session_id(log_line.line)
            if session_id:
                current_session_id = session_id

            if any(marker in log_line.line for marker in self.START_PATTERNS):
                if current_start:
                    sessions.append(Session(current_session_id, current_start, None))
                current_start = timestamp
            elif any(marker in log_line.line for marker in self.END_PATTERNS):
                if current_start:
                    sessions.append(Session(current_session_id, current_start, timestamp))
                    current_start = None
                    current_session_id = None
                else:
                    sessions.append(Session(current_session_id, None, timestamp))
                    current_session_id = None

        if current_start:
            sessions.append(Session(current_session_id, current_start, None))

        raw_lines = ["Session Report"]
        for session in sessions:
            entry = session.as_dict()
            raw_lines.append(str(entry))

        if not sessions:
            legacy = LegacySessionsParser(self.mode)
            return legacy.process(archive_path, timezone=timezone, begin_date=begin_date, end_date=end_date)

        return {
            'raw_output': "\n".join(raw_lines),
            'parsed_data': [session.as_dict() for session in sessions]
        }


def _parse_timestamp(line: str, tz_name: str):
    parts = line.split()
    if len(parts) < 2:
        return None
    ts_raw = f"{parts[0]} {parts[1].rstrip(':')}"
    try:
        parsed = dateutil_parser.parse(ts_raw)
    except Exception:
        return None

    tz = pytz.timezone(tz_name)
    if parsed.tzinfo is None:
        parsed = tz.localize(parsed)
    else:
        parsed = parsed.astimezone(tz)
    return parsed


def _extract_session_id(line: str) -> Optional[str]:
    import re

    match = re.search(r'session id\: ([^\s]+)', line, re.IGNORECASE)
    if match:
        return match.group(1)
    return None


__all__ = ["SessionsParser"]
