"""Native parser for modem grading mode."""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Dict, List, Optional

try:  # pragma: no cover
    from dateutil import parser as dateutil_parser
    import pytz
except ImportError:  # pragma: no cover
    dateutil_parser = None
    pytz = None

from .base import BaseParser, DateRange
from .lula_wrapper import SystemParser as LegacySystemParser


GRADE_CHANGE_PATTERN = re.compile(
    r"INFO:ModemGrading: changed grade of modem (\d+) from (Full Service|Limited Service) to (Full Service|Limited Service)",
    re.IGNORECASE,
)

RTT_PATTERN = re.compile(
    r"INFO:modem (\d+) extrapolated smooth rtt \((\d+)\) or (?:extrapolated )?upstreamdelay \((\d+)\) (good enough for full service|NOT good enough for full service)",
    re.IGNORECASE,
)

LOSS_PATTERN = re.compile(
    r"INFO:modem (\d+) loss \( (\d+) \) (above full service ceil (\d+)|below limited service floor (\d+))",
    re.IGNORECASE,
)


@dataclass
class GradingEvent:
    modem_id: str
    timestamp: str
    status: str
    detail: Optional[str] = None

    def as_dict(self) -> dict:
        return {
            'modem_id': self.modem_id,
            'timestamp': self.timestamp,
            'status': self.status,
            'detail': self.detail,
        }


class GradingParser(BaseParser):
    """Reimplementation of Lula2 grading mode."""

    def parse(self, archive_path: str, *, timezone: str, begin_date: Optional[str], end_date: Optional[str]):
        if dateutil_parser is None or pytz is None:
            raise RuntimeError("dateutil and pytz are required for GradingParser")

        daterange = DateRange(begin_date, end_date)
        events: List[GradingEvent] = []
        raw_lines: List[str] = []

        for log_line in self.iter_archive(archive_path, timezone=timezone):
            self.ensure_not_cancelled()

            dt = _parse_timestamp(log_line.line, timezone)
            if dt is None or not daterange.contains(dt):
                continue
            timestamp = dt.strftime("%Y-%m-%d %H:%M:%S")

            line = log_line.line

            if match := GRADE_CHANGE_PATTERN.search(line):
                modem_id, _, new_state = match.groups()
                status = 'Limited Service' if 'Limited' in new_state else 'Full Service'
                events.append(GradingEvent(modem_id, timestamp, status))
                raw_lines.append(line.strip())
                continue

            if match := RTT_PATTERN.search(line):
                modem_id, rtt, delay, outcome = match.groups()
                status = 'Full Service' if 'good enough' in outcome.lower() else 'Limited Service'
                detail = f"rtt={rtt}, delay={delay}"
                events.append(GradingEvent(modem_id, timestamp, status, detail))
                raw_lines.append(line.strip())
                continue

            if match := LOSS_PATTERN.search(line):
                modem_id = match.group(1)
                loss_value = match.group(2)
                status = 'Limited Service' if 'above' in match.group(3).lower() else 'Full Service'
                detail = f"loss={loss_value}"
                events.append(GradingEvent(modem_id, timestamp, status, detail))
                raw_lines.append(line.strip())

        if not events:
            legacy = LegacySystemParser('grading')
            return legacy.process(archive_path, timezone=timezone, begin_date=begin_date, end_date=end_date)

        return {
            'raw_output': '\n'.join(raw_lines),
            'parsed_data': [event.as_dict() for event in events],
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


__all__ = ["GradingParser"]
