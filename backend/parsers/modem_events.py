"""Native modem events parsers replacing Lula2 implementations."""
from __future__ import annotations

import ast
import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional

try:  # pragma: no cover
    from dateutil import parser as dateutil_parser
    import pytz
except ImportError:  # pragma: no cover - available in runtime image
    dateutil_parser = None
    pytz = None

from .base import BaseParser, DateRange


@dataclass
class ModemEvent:
    timestamp: str
    event_type: str
    message: str
    port: Optional[str] = None
    metadata: Dict[str, object] = field(default_factory=dict)

    def as_dict(self) -> dict:
        return {
            'timestamp': self.timestamp,
            'event_type': self.event_type,
            'message': self.message,
            'port': self.port,
            'metadata': self.metadata,
        }


class ICCID:
    """Simple ICCID prefix map replicated from Lula2."""

    PROVIDERS = {
        '898523': 'Webbing',
        '893108': 'RiteSIM',
        '89011': 'AT&T Roaming',
    }

    def __init__(self, iccid: Optional[str]):
        self.iccid = iccid or ''

    @property
    def provider(self) -> str:
        for prefix, name in self.PROVIDERS.items():
            if self.iccid.startswith(prefix):
                return name
        return 'Unknown'


class ModemEventsParser(BaseParser):
    """Parse modem connectivity events in chronological order."""

    def parse(self, archive_path: str, *, timezone: str, begin_date: Optional[str], end_date: Optional[str]):
        if dateutil_parser is None or pytz is None:
            raise RuntimeError("dateutil and pytz are required for ModemEventsParser")

        daterange = DateRange(begin_date, end_date)
        events: List[ModemEvent] = []
        raw_lines: List[str] = []

        for log_line in self.iter_archive(archive_path, timezone=timezone):
            self.ensure_not_cancelled()

            dt = _parse_timestamp(log_line.line, timezone)
            if dt is None or not daterange.contains(dt):
                continue
            timestamp = dt.strftime("%Y-%m-%d %H:%M:%S")

            parsed = _parse_event(log_line.line)
            if parsed:
                event = ModemEvent(timestamp=timestamp, **parsed)
                events.append(event)
                raw_lines.append(event.message)

        return {
            'raw_output': '\n'.join(raw_lines),
            'parsed_data': [event.as_dict() for event in events],
        }


class ModemEventsSortedParser(ModemEventsParser):
    """Return modem events grouped by modem/port."""

    def parse(self, archive_path: str, *, timezone: str, begin_date: Optional[str], end_date: Optional[str]):
        base = super().parse(archive_path, timezone=timezone, begin_date=begin_date, end_date=end_date)
        events = [ModemEvent(**evt) for evt in base['parsed_data']]  # type: ignore

        grouped: Dict[str, Dict[str, object]] = {}
        for evt in events:
            key = evt.port or 'general'
            bucket = grouped.setdefault(key, {'port': key, 'events': []})
            bucket['events'].append(evt.as_dict())

        base['parsed_data'] = {
            'modems': list(grouped.values()),
            'all_events': [evt.as_dict() for evt in events],
        }
        return base


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

PORT_EVENT_PATTERNS = [
    (
        'current_operator',
        re.compile(r"INFO: ([^:]+): Current operator: (.*), technology: (.*) \(", re.IGNORECASE),
        lambda match: {
            'message': f"   {match.group(1)} Current Operator: {match.group(2)} Tech {match.group(3)}",
            'port': match.group(1),
            'metadata': {
                'operator': match.group(2),
                'technology': match.group(3),
            },
        },
    ),
    (
        'manual_operator',
        re.compile(r"INFO: ([^:]+): Setting modem to manually selected operator. mccmnc: (\d+)", re.IGNORECASE),
        lambda match: {
            'message': f"   {match.group(1)} Manually selecting operator: {match.group(2)}",
            'port': match.group(1),
            'metadata': {'mccmnc': match.group(2)},
        },
    ),
    (
        'roaming_service',
        re.compile(r"INFO: ([^:]+): Finished cellular network selection per roaming distribution rules, selected operator: (\d+)", re.IGNORECASE),
        lambda match: {
            'message': f"   {match.group(1)} Roaming service selected operator: {match.group(2)}",
            'port': match.group(1),
            'metadata': {'operator': match.group(2)},
        },
    ),
    (
        'link_connected',
        re.compile(r"INFO: ([^:]+): Link connected. APN: ([^\s]*)", re.IGNORECASE),
        lambda match: {
            'message': f"   {match.group(1)} Link connect with apn: {match.group(2)}",
            'port': match.group(1),
            'metadata': {'apn': match.group(2)},
        },
    ),
    (
        'qmi_link',
        re.compile(r"INFO: ([^:]+): QMI link: \<([^>]*)\> is ready after: (\d*) attempts", re.IGNORECASE),
        lambda match: {
            'message': f"   {match.group(1)} QMI Link made after {match.group(3)} attempts: {match.group(2)}",
            'port': match.group(1),
            'metadata': {'link_info': match.group(2), 'attempts': int(match.group(3) or 0)},
        },
    ),
]

LINK_INFO_PATTERN = re.compile(r"INFO: ([^:]+): Link\s+\<([^>]+)\>", re.IGNORECASE)
DHCP_LINK_PATTERN = re.compile(r"INFO: ([^:]+): DHCP link:\s+\<([^>]+)\>", re.IGNORECASE)
LINK_READY_PATTERN = re.compile(r"(?:INFO: )?([^:]+): Link is ready for streaming: \((.+)\)\s+\(eagle", re.IGNORECASE)
INTERFACES_READY_PATTERN = re.compile(r"INFO:found (\d+) links ready for streaming", re.IGNORECASE)


def _parse_event(line: str) -> Optional[Dict[str, object]]:
    stripped = line.strip()

    # First, handle the PORT_EVENT_PATTERNS list
    for event_type, pattern, builder in PORT_EVENT_PATTERNS:
        match = pattern.search(line)
        if match:
            payload = builder(match)
            payload.setdefault('metadata', {})
            payload['event_type'] = event_type
            payload['message'] = payload['message']
            return payload

    # Link ready for streaming with detailed dictionary
    match = LINK_READY_PATTERN.search(line)
    if match:
        port = match.group(1)
        info_str = match.group(2)
        sanitized = re.sub(r"\<[^>]*?\>", "'__object__'", info_str)
        try:
            info = ast.literal_eval(sanitized)
        except Exception:
            info = {}
        iccid = ICCID(str(info.get('iccid')))
        message = (
            f"   Link ready for streaming, {port}: Description: {info.get('description')}, "
            f"modemType: {info.get('modemType')}, ICCID: {info.get('iccid')} [{iccid.provider}], "
            f"tech: {info.get('technology')}, operatorName: {info.get('operatorName')}, "
            f"activeSIM: {info.get('activeSim')}, isRoaming: {info.get('isCurrentlyRoaming')}, rssi: {info.get('rssi')}"
        )
        metadata = {k: info.get(k) for k in ['description', 'modemType', 'iccid', 'technology', 'operatorName', 'activeSim', 'isCurrentlyRoaming', 'rssi']}
        metadata['provider'] = iccid.provider
        return {
            'event_type': 'link_ready',
            'message': message,
            'port': port,
            'metadata': metadata,
        }

    match = LINK_INFO_PATTERN.search(line)
    if match:
        port = match.group(1)
        message = f"   Link: {port} {match.group(2)}"
        return {
            'event_type': 'link_info',
            'message': message,
            'port': port,
            'metadata': {'details': match.group(2)},
        }

    match = DHCP_LINK_PATTERN.search(line)
    if match:
        port = match.group(1)
        message = f"   DHCP Link: {port} {match.group(2)}"
        return {
            'event_type': 'dhcp_link',
            'message': message,
            'port': port,
            'metadata': {'details': match.group(2)},
        }

    match = INTERFACES_READY_PATTERN.search(line)
    if match:
        count = int(match.group(1))
        message = f"   Number of interfaces ready for streaming: {count}"
        return {
            'event_type': 'interfaces_ready',
            'message': message,
            'port': None,
            'metadata': {'count': count},
        }

    return None


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


__all__ = ["ModemEventsParser", "ModemEventsSortedParser"]
