"""Native parser for CPU usage mode."""
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


CPU_DETAIL_PATTERN = re.compile(
    r"(vic|corecard) monitor.+(INFO|WARNING):CPU usage in detail is scputimes\([^\)]*idle=([\d\.]+)",
    re.IGNORECASE,
)

CPU_CORE_WARNING_PATTERN = re.compile(
    r"(vic|corecard|server) monitor.+WARNING:CPU utilization on core (\d+) \(index starts from \d+\) is high:.+idle=([\d\.]+)",
    re.IGNORECASE,
)

CPU_SERVER_PATTERN = re.compile(
    r"server monitor.+(INFO|WARNING):CPU usage is at ([\d\.]+)%",
    re.IGNORECASE,
)


@dataclass
class CpuEvent:
    component: str
    timestamp: str
    idle_percent: Optional[float] = None
    total_percent: Optional[float] = None
    core_index: Optional[int] = None
    level: str = "INFO"

    def as_dict(self) -> dict:
        return {
            'component': self.component,
            'timestamp': self.timestamp,
            'idle_percent': self.idle_percent,
            'core_index': self.core_index,
            'total_percent': self.total_percent,
            'level': self.level,
        }


class CpuParser(BaseParser):
    """Reimplementation of Lula2 CPU mode."""

    COMPONENT_MAP = {
        'vic': 'VIC',
        'corecard': 'Corecard',
        'server': 'Server',
    }

    def parse(self, archive_path: str, *, timezone: str, begin_date: Optional[str], end_date: Optional[str]):
        if dateutil_parser is None or pytz is None:
            raise RuntimeError("dateutil and pytz are required for CpuParser")

        daterange = DateRange(begin_date, end_date)
        events: List[CpuEvent] = []
        raw_lines: List[str] = []

        for log_line in self.iter_archive(archive_path, timezone=timezone):
            self.ensure_not_cancelled()
            line = log_line.line

            # Check patterns FIRST before timestamp parsing (more efficient)
            has_cpu_pattern = (CPU_DETAIL_PATTERN.search(line) or
                              CPU_CORE_WARNING_PATTERN.search(line) or
                              CPU_SERVER_PATTERN.search(line))

            if not has_cpu_pattern:
                continue

            dt = _parse_timestamp(line, timezone)
            if dt is None:
                continue

            if not daterange.contains(dt):
                continue

            timestamp = dt.strftime("%Y-%m-%d %H:%M:%S")

            if match := CPU_DETAIL_PATTERN.search(line):
                component = self.COMPONENT_MAP.get(match.group(1).lower(), 'Unknown')
                level = match.group(2).upper()
                idle = float(match.group(3))
                events.append(CpuEvent(component, timestamp, idle_percent=idle, level=level))
                raw_lines.append(line.strip())
                continue

            if match := CPU_CORE_WARNING_PATTERN.search(line):
                component = self.COMPONENT_MAP.get(match.group(1).lower(), 'Unknown')
                core_index = int(match.group(2))
                idle = float(match.group(3))
                events.append(CpuEvent(component, timestamp, idle_percent=idle, core_index=core_index, level='WARNING'))
                raw_lines.append(line.strip())
                continue

            if match := CPU_SERVER_PATTERN.search(line):
                level = match.group(1).upper()
                total = float(match.group(2))
                events.append(CpuEvent('Server', timestamp, total_percent=total, level=level))
                raw_lines.append(line.strip())

        return {
            'raw_output': '\n'.join(raw_lines),
            'parsed_data': [event.as_dict() for event in events],
        }


def _parse_timestamp(line: str, tz_name: str):
    """Parse timestamp from log line.

    The timestamp is in ISO 8601 format at the beginning of the line,
    e.g., '2025-10-02T18:42:16.388503+00:00 corecard monitor...'
    """
    parts = line.split()
    if len(parts) < 1:
        return None

    # The timestamp is complete in the first part (ISO 8601 format with T separator)
    ts_raw = parts[0]
    try:
        parsed = dateutil_parser.parse(ts_raw)
    except Exception:
        return None

    try:
        tz = pytz.timezone(tz_name)
        if parsed.tzinfo is None:
            parsed = tz.localize(parsed)
        else:
            parsed = parsed.astimezone(tz)
        return parsed
    except Exception:
        return None


__all__ = ["CpuParser"]
