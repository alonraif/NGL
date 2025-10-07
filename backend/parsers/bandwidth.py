"""Native bandwidth parsers that replace lula2 for stream and modem modes."""
from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Dict, List, Optional

try:  # pragma: no cover - dependencies available in runtime image
    from dateutil import parser as dateutil_parser
    import pytz
except ImportError:  # pragma: no cover
    dateutil_parser = None
    pytz = None

from .base import BaseParser, DateRange
from .lula_wrapper import BandwidthParser as LegacyBandwidthParser


@dataclass
class StreamRow:
    timestamp: str
    total_bitrate: str
    video_bitrate: str
    notes: str = ""

    def as_dict(self) -> dict:
        return {
            "datetime": self.timestamp,
            "total bitrate": self.total_bitrate,
            "video bitrate": self.video_bitrate,
            "notes": self.notes,
        }


class StreamBandwidthParser(BaseParser):
    """Parser for ``bw`` mode using modular pipeline."""

    FLOW_AVAILABLE_PATTERN = re.compile(
        r"Detected (?:flow|congestion) in outgoing queue \(available <Bandwidth: (\d+)kbps>\): Setting bitrate to <Bandwidth: (\d+)kbps>",
        re.IGNORECASE,
    )
    FLOW_POTENTIAL_PATTERN = re.compile(
        r"Detected flow in outgoing queue \(potential (\d+) kbps\): Setting bitrate to (\d+) kbps",
        re.IGNORECASE,
    )
    FLOW_CONGESTION_PATTERN = re.compile(
        r"Detected congestion in outgoing queue:  drain time = (\d+) ms, potential bandwidth (\d+) kbps: Setting bitrate to (\d+) kbps",
        re.IGNORECASE,
    )
    STREAM_START_PATTERN = re.compile(
        r"Entering state \"StartStreamer\" with args: \(\).+'collectorAddressList'\: \[\[u?'([\d\.]+)', \d+\]\]"
    )
    STREAM_END_PATTERN = re.compile(r"Entering state \"StopStreamer\"")

    def parse(self, archive_path: str, *, timezone: str, begin_date: Optional[str], end_date: Optional[str]):
        if dateutil_parser is None or pytz is None:
            raise RuntimeError("dateutil and pytz are required for StreamBandwidthParser")

        daterange = DateRange(begin_date, end_date)
        rows: List[StreamRow] = []

        for log_line in self.iter_archive(archive_path, timezone=timezone):
            self.ensure_not_cancelled()

            dt = _parse_timestamp(log_line.line, timezone)
            if dt is None or not daterange.contains(dt):
                continue

            timestamp = dt.strftime("%Y-%m-%d %H:%M:%S")
            note = None
            total = None
            video = None

            if match := self.FLOW_AVAILABLE_PATTERN.search(log_line.line):
                total = match.group(1)
                video = match.group(2)
            elif match := self.FLOW_POTENTIAL_PATTERN.search(log_line.line):
                total = match.group(1)
                video = match.group(2)
            elif match := self.FLOW_CONGESTION_PATTERN.search(log_line.line):
                total = match.group(2)
                video = match.group(3)
            elif self.STREAM_START_PATTERN.search(log_line.line):
                total = "0"
                video = "0"
                note = "Stream start"
            elif self.STREAM_END_PATTERN.search(log_line.line):
                total = "0"
                video = "0"
                note = "Stream end"

            if total is not None and video is not None:
                rows.append(StreamRow(timestamp, total, video, note or ""))

        if not rows:
            legacy = LegacyBandwidthParser(self.mode)
            return legacy.process(archive_path, timezone=timezone, begin_date=begin_date, end_date=end_date)

        csv_lines = _build_csv_lines(rows)
        raw_output = "\n".join(csv_lines)
        parsed_data = _parse_stream_bandwidth(csv_lines, end_date)
        return {"raw_output": raw_output, "parsed_data": parsed_data}


@dataclass
class ModemRow:
    modem_id: str
    timestamp: str
    potential_bw: float
    loss: float
    upstream: float
    shortest_rtt: float
    smooth_rtt: float
    min_rtt: float


class ModemBandwidthParser(BaseParser):
    """Parser for ``md-bw`` mode returning Lula2-compatible structures."""

    MODEM_PATTERN = re.compile(
        r"Modem Statistics for modem (\d+): potentialBW (\d+)k?bps, (\d+)\% loss, (\d+)ms up extrapolated delay, (\d+)ms shortest round trip delay, (\d+)ms smooth round trip delay, (\d+)ms minimum smooth round trip delay",
        re.IGNORECASE,
    )
    MODEM_DB_PATTERN = re.compile(
        r"Modem Statistics for modem (\d+): (\d+)k?bps, (\d+)\% loss, (\d+)ms delay",
        re.IGNORECASE,
    )

    def parse(self, archive_path: str, *, timezone: str, begin_date: Optional[str], end_date: Optional[str]):
        if dateutil_parser is None or pytz is None:
            raise RuntimeError("dateutil and pytz are required for ModemBandwidthParser")

        daterange = DateRange(begin_date, end_date)
        rows: List[ModemRow] = []

        for log_line in self.iter_archive(archive_path, timezone=timezone):
            self.ensure_not_cancelled()
            match = self.MODEM_PATTERN.search(log_line.line)
            if match:
                stats = (
                    float(match.group(2)),
                    float(match.group(3)),
                    float(match.group(4)),
                    float(match.group(5)),
                    float(match.group(6)),
                    float(match.group(7)),
                )
            else:
                match = self.MODEM_DB_PATTERN.search(log_line.line)
                if not match:
                    continue
                stats = (
                    float(match.group(2)),
                    float(match.group(3)),
                    float(match.group(4)),
                    0.0,
                    0.0,
                    0.0,
                )

            dt = _parse_timestamp(log_line.line, timezone)
            if dt is None or not daterange.contains(dt):
                continue

            rows.append(
                ModemRow(
                    modem_id=match.group(1),
                    timestamp=dt.strftime("%Y-%m-%d %H:%M:%S"),
                    potential_bw=stats[0],
                    loss=stats[1],
                    upstream=stats[2],
                    shortest_rtt=stats[3],
                    smooth_rtt=stats[4],
                    min_rtt=stats[5],
                )
            )

        if not rows:
            legacy = LegacyBandwidthParser(self.mode)
            return legacy.process(archive_path, timezone=timezone, begin_date=begin_date, end_date=end_date)

        structured = _group_modem_rows(rows)
        raw_output = _modem_rows_to_tsv(structured)
        return {"raw_output": raw_output, "parsed_data": structured}


def _build_csv_lines(rows: List[StreamRow]) -> List[str]:
    lines = ["datetime,total bitrate,video bitrate,notes"]
    for row in rows:
        lines.append(f"{row.timestamp},{row.total_bitrate},{row.video_bitrate},{row.notes}")
    if rows and rows[-1].notes != "Stream end":
        lines.append("0,0,0,Stream end")
    elif not rows:
        lines.append("0,0,0,Stream end")
    return lines


def _parse_stream_bandwidth(lines: List[str], end_date: Optional[str]):
    data = []
    for line in lines[1:]:
        if not line.strip():
            continue
        parts = [p.strip() for p in line.split(',')]
        if len(parts) >= 3:
            data.append({
                'datetime': parts[0],
                'total bitrate': parts[1],
                'video bitrate': parts[2],
                'notes': parts[3] if len(parts) > 3 else ''
            })

    if len(data) == 0:
        return data

    filled_data = []
    fill_interval_seconds = 5

    for i, point in enumerate(data):
        filled_data.append(point)

        if i < len(data) - 1:
            try:
                current_time = datetime.strptime(point['datetime'], '%Y-%m-%d %H:%M:%S')
                next_time = datetime.strptime(data[i+1]['datetime'], '%Y-%m-%d %H:%M:%S')
                gap_seconds = (next_time - current_time).total_seconds()

                if gap_seconds > fill_interval_seconds and 'Stream' not in point['notes']:
                    num_fills = int(gap_seconds / fill_interval_seconds)
                    if num_fills > 1000:
                        fill_interval = gap_seconds / 1000
                        num_fills = 1000
                    else:
                        fill_interval = fill_interval_seconds

                    for j in range(1, num_fills):
                        fill_time = current_time + timedelta(seconds=j * fill_interval)
                        filled_data.append({
                            'datetime': fill_time.strftime('%Y-%m-%d %H:%M:%S'),
                            'total bitrate': point['total bitrate'],
                            'video bitrate': point['video bitrate'],
                            'notes': '(forward filled)'
                        })

            except (ValueError, KeyError):
                continue

    if filled_data and end_date:
        try:
            last_point = filled_data[-1]
            if 'Stream' not in last_point['notes']:
                last_time = datetime.strptime(last_point['datetime'], '%Y-%m-%d %H:%M:%S')
                end_time = datetime.strptime(end_date, '%Y-%m-%d %H:%M:%S')
                gap_seconds = (end_time - last_time).total_seconds()

                if gap_seconds > fill_interval_seconds:
                    num_fills = int(gap_seconds / fill_interval_seconds)
                    if num_fills > 1000:
                        fill_interval = gap_seconds / 1000
                        num_fills = 1000
                    else:
                        fill_interval = fill_interval_seconds

                    for j in range(1, num_fills + 1):
                        fill_time = last_time + timedelta(seconds=j * fill_interval)
                        if fill_time <= end_time:
                            filled_data.append({
                                'datetime': fill_time.strftime('%Y-%m-%d %H:%M:%S'),
                                'total bitrate': last_point['total bitrate'],
                                'video bitrate': last_point['video bitrate'],
                                'notes': '(forward filled)'
                            })
        except ValueError:
            pass

    return filled_data


def _group_modem_rows(rows: List[ModemRow]):
    modems: Dict[str, List[dict]] = {}
    timestamps = set()
    for row in rows:
        timestamps.add(row.timestamp)
        modems.setdefault(row.modem_id, []).append({
            'datetime': row.timestamp,
            'potential_bw': row.potential_bw,
            'loss': row.loss,
            'upstream': row.upstream,
            'shortest_rtt': row.shortest_rtt,
            'smooth_rtt': row.smooth_rtt,
            'min_rtt': row.min_rtt,
        })

    aggregated = []
    for ts in sorted(timestamps):
        total_bw = sum(entry['potential_bw'] for modem_entries in modems.values() for entry in modem_entries if entry['datetime'] == ts)
        aggregated.append({'datetime': ts, 'total_bw': total_bw})

    return {
        'mode': 'md-bw',
        'modems': modems,
        'aggregated': aggregated
    }


def _modem_rows_to_tsv(structured) -> str:
    lines = ["ModemID\tDate/time\tPotentialBW\tLoss\tExtrapolated smooth upstream\tShortest round trip\tExtrapolated smooth round trip\tMinimum smooth round trip\tNotes"]
    for modem_id, rows in structured['modems'].items():
        for entry in rows:
            lines.append(
                f"Modem{modem_id}\t{entry['datetime']}\t{entry['potential_bw']}\t{entry['loss']}\t{entry['upstream']}\t{entry['shortest_rtt']}\t{entry['smooth_rtt']}\t{entry['min_rtt']}\t"
            )
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


__all__ = ["StreamBandwidthParser", "ModemBandwidthParser"]
