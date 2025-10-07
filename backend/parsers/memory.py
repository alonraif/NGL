"""Native parser for memory usage mode."""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import List, Optional

try:  # pragma: no cover
    from dateutil import parser as dateutil_parser
    import pytz
except ImportError:  # pragma: no cover
    dateutil_parser = None
    pytz = None

from .base import BaseParser, DateRange
from .lula_wrapper import SystemParser as LegacySystemParser


MEMORY_LINE = re.compile(
    r"(?P<component>vic|corecard|server) monitor.+(?P<level>INFO|WARNING):Memory usage is (?P<percent>[\d\.]+)% \((?P<used>[\d\.]+) MB out of (?P<total>[\d\.]+) MB\)",
    re.IGNORECASE,
)


@dataclass
class MemoryPoint:
    component: str
    timestamp: str
    percent: float
    used_mb: float
    total_mb: float
    is_warning: bool

    def as_dict(self) -> dict:
        return {
            'component': self.component,
            'timestamp': self.timestamp,
            'percent': self.percent,
            'used_mb': self.used_mb,
            'total_mb': self.total_mb,
            'is_warning': self.is_warning,
        }


class MemoryParser(BaseParser):
    """Reimplementation of Lula2 memory mode."""

    COMPONENT_MAP = {
        'vic': 'VIC',
        'corecard': 'Corecard',
        'server': 'Server',
    }

    def parse(self, archive_path: str, *, timezone: str, begin_date: Optional[str], end_date: Optional[str]):
        if dateutil_parser is None or pytz is None:
            raise RuntimeError("dateutil and pytz are required for MemoryParser")

        daterange = DateRange(begin_date, end_date)
        points: List[MemoryPoint] = []
        raw_lines: List[str] = []

        for log_line in self.iter_archive(archive_path, timezone=timezone):
            self.ensure_not_cancelled()
            match = MEMORY_LINE.search(log_line.line)
            if not match:
                continue

            dt = _parse_timestamp(log_line.line, timezone)
            if dt is None or not daterange.contains(dt):
                continue

            component = self.COMPONENT_MAP.get(match.group('component').lower(), 'Unknown')
            percent = float(match.group('percent'))
            used = float(match.group('used'))
            total = float(match.group('total'))
            is_warning = match.group('level').upper() == 'WARNING'

            points.append(
                MemoryPoint(
                    component=component,
                    timestamp=dt.strftime("%Y-%m-%d %H:%M:%S"),
                    percent=percent,
                    used_mb=used,
                    total_mb=total,
                    is_warning=is_warning,
                )
            )
            raw_lines.append(log_line.line.strip())

        if not points:
            legacy = LegacySystemParser('memory')
            return legacy.process(archive_path, timezone=timezone, begin_date=begin_date, end_date=end_date)

        return {
            'raw_output': '\n'.join(raw_lines),
            'parsed_data': [point.as_dict() for point in points],
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


__all__ = ["MemoryParser"]
