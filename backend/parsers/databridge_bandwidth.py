"""Native parser for the ``md-db-bw`` mode."""
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


@dataclass
class DataBridgeRow:
    modem_id: str
    timestamp: str
    bandwidth: float
    loss: float
    delay: float
    notes: str = ""


class DataBridgeBandwidthParser(BaseParser):
    """Reimplementation of Lula2's data bridge modem bandwidth output."""

    MODEM_PATTERN = re.compile(
        r"Modem Statistics for modem (\d+): (\d+)k?bps, (\d+)\% loss, (\d+)ms delay"
    )
    START_PATTERN = re.compile(r"INFO:Entering state \"StartDatabridgeStreamer\"")
    END_PATTERN = re.compile(r"INFO:Entering state \"StopCollectorAndStreamer\"")
    MODEM_REMOVED_PATTERN = re.compile(r"INFO:Modem removed id: (\d+)")

    def parse(self, archive_path: str, *, timezone: str, begin_date: Optional[str], end_date: Optional[str]):
        if dateutil_parser is None or pytz is None:
            raise RuntimeError("dateutil and pytz are required for DataBridgeBandwidthParser")

        daterange = DateRange(begin_date, end_date)
        rows: List[DataBridgeRow] = []
        modem_notes: Dict[str, str] = {}

        for log_line in self.iter_archive(archive_path, timezone=timezone):
            self.ensure_not_cancelled()

            dt = _parse_timestamp(log_line.line, timezone)
            if dt is None or not daterange.contains(dt):
                continue
            timestamp = dt.strftime("%Y-%m-%d %H:%M:%S")

            if match := self.MODEM_PATTERN.search(log_line.line):
                rows.append(
                    DataBridgeRow(
                        modem_id=match.group(1),
                        timestamp=timestamp,
                        bandwidth=float(match.group(2)),
                        loss=float(match.group(3)),
                        delay=float(match.group(4)),
                        notes=modem_notes.pop(match.group(1), ""),
                    )
                )
            elif self.START_PATTERN.search(log_line.line):
                rows.append(DataBridgeRow("", timestamp, 0, 0, 0, "Stream start"))
            elif self.END_PATTERN.search(log_line.line):
                rows.append(DataBridgeRow("", timestamp, 0, 0, 0, "Stream end"))
            elif match := self.MODEM_REMOVED_PATTERN.search(log_line.line):
                modem_notes[match.group(1)] = "Modem disconnected"

        structured = _group_databridge_rows(rows)
        raw_output = _databridge_rows_to_tsv(structured)
        return {"raw_output": raw_output, "parsed_data": structured}


def _group_databridge_rows(rows: List[DataBridgeRow]):
    modems: Dict[str, List[dict]] = {}
    special_rows = []

    for row in rows:
        if row.modem_id:
            entry = {
                'datetime': row.timestamp,
                'bandwidth': row.bandwidth,
                'loss': row.loss,
                'delay': row.delay,
                'notes': row.notes
            }
            modems.setdefault(row.modem_id, []).append(entry)
        else:
            special_rows.append({'datetime': row.timestamp, 'notes': row.notes})

    return {
        'mode': 'md-db-bw',
        'modems': modems,
        'events': special_rows
    }


def _databridge_rows_to_tsv(structured) -> str:
    lines = ["ModemID\tDate/time\tPotentialBW\tLoss\tDelay\tNotes"]
    for modem_id, entries in structured['modems'].items():
        for entry in entries:
            lines.append(
                f"Modem{modem_id}\t{entry['datetime']}\t{entry['bandwidth']}\t{entry['loss']}\t{entry['delay']}\t{entry['notes']}"
            )
    for event in structured['events']:
        lines.append(f"\t{event['datetime']}\t0\t0\t0\t{event['notes']}")
    return "\n".join(lines)


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


__all__ = ["DataBridgeBandwidthParser"]
