"""
Wrapper for lula2.py - delegates parsing to the proven script
"""
import subprocess
import os
import re
import signal
from .base import BaseParser


class LulaWrapperParser(BaseParser):
    """
    Base parser that delegates to lula2.py

    This provides the modular architecture while using lula2.py's proven parsing logic.
    Individual parsers can override parse() to add custom post-processing.
    """

    def parse(self, log_path, timezone='US/Eastern', begin_date=None, end_date=None):
        """
        Parse using lula2.py

        Args:
            log_path: Path to messages.log or directory containing it
            timezone: Timezone for date parsing
            begin_date: Optional start date filter
            end_date: Optional end date filter

        Returns:
            dict with 'raw_output' and 'parsed_data'
        """
        # Note: This should not be called directly - use process() instead
        # which will be overridden to pass the archive file to lula2.py
        raise NotImplementedError("Use process() method instead")

    def process(self, archive_path, timezone='US/Eastern', begin_date=None, end_date=None, analysis_id=None, redis_client=None):
        """
        Full processing pipeline: call lula2.py with archive file directly

        Overrides BaseParser.process() to skip extraction and call lula2.py directly

        Args:
            analysis_id: Analysis ID for tracking (optional)
            redis_client: Redis client for storing PID (optional)
        """
        # Normalize timestamps to remove microseconds (lula2.py doesn't handle them correctly)
        from dateutil import parser as date_parser

        normalized_begin_date = begin_date
        normalized_end_date = end_date

        if begin_date:
            try:
                dt = date_parser.parse(begin_date)
                # Format: YYYY-MM-DD HH:MM:SS+TZ (no microseconds)
                if dt.tzinfo:
                    normalized_begin_date = dt.strftime('%Y-%m-%d %H:%M:%S%z')
                    # Add colon in timezone offset (e.g., +00:00 instead of +0000)
                    if len(normalized_begin_date) > 19:
                        normalized_begin_date = normalized_begin_date[:-2] + ':' + normalized_begin_date[-2:]
                else:
                    normalized_begin_date = dt.strftime('%Y-%m-%d %H:%M:%S')
            except Exception:
                pass  # Use original if parsing fails

        if end_date:
            try:
                dt = date_parser.parse(end_date)
                # Format: YYYY-MM-DD HH:MM:SS+TZ (no microseconds)
                if dt.tzinfo:
                    normalized_end_date = dt.strftime('%Y-%m-%d %H:%M:%S%z')
                    # Add colon in timezone offset (e.g., +00:00 instead of +0000)
                    if len(normalized_end_date) > 19:
                        normalized_end_date = normalized_end_date[:-2] + ':' + normalized_end_date[-2:]
                else:
                    normalized_end_date = dt.strftime('%Y-%m-%d %H:%M:%S')
            except Exception:
                pass  # Use original if parsing fails

        # Build lula2.py command with the archive file
        cmd = ['python3', '/app/lula2.py', archive_path, '-p', self.mode, '-t', timezone]

        if normalized_begin_date:
            cmd.extend(['-b', normalized_begin_date])
        if normalized_end_date:
            cmd.extend(['-e', normalized_end_date])

        # Log the command for debugging
        import logging
        logger = logging.getLogger(__name__)
        if begin_date != normalized_begin_date or end_date != normalized_end_date:
            logger.info(f"Normalized timestamps for lula2.py: begin={normalized_begin_date}, end={normalized_end_date} (original: begin={begin_date}, end={end_date})")

        # Execute lula2.py using Popen to track PID
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            preexec_fn=os.setsid  # Create new process group for easy killing
        )

        # Store PID in Redis if provided
        if analysis_id and redis_client:
            redis_key = f"analysis:{analysis_id}:pid"
            redis_client.setex(redis_key, 3600, str(process.pid))  # Expire after 1 hour
            print(f"[Parser] Stored PID {process.pid} for analysis {analysis_id}")

        # Wait for completion
        try:
            stdout, stderr = process.communicate(timeout=1800)
            returncode = process.returncode
        except subprocess.TimeoutExpired:
            # Kill the entire process group
            os.killpg(os.getpgid(process.pid), signal.SIGKILL)
            raise Exception("lula2.py processing timed out after 30 minutes")

        if returncode != 0:
            # Clean up Redis entry on error
            if analysis_id and redis_client:
                redis_client.delete(f"analysis:{analysis_id}:pid")

            # Check if process was killed (signal -9 = SIGKILL)
            if returncode == -9 or returncode == -signal.SIGKILL:
                raise Exception("Process was cancelled by user")

            raise Exception(f"lula2.py error: {stderr}")

        # Clean up Redis entry on success
        if analysis_id and redis_client:
            redis_client.delete(f"analysis:{analysis_id}:pid")

        raw_output = stdout

        # Parse output based on mode
        parsed_data = self.parse_output(raw_output)

        return {
            'raw_output': raw_output,
            'parsed_data': parsed_data
        }

    def parse_output(self, output):
        """
        Parse lula2.py output into structured data
        Override in subclasses for mode-specific parsing
        """
        # Default: return raw text split into lines
        return {'lines': output.split('\n')}


class BandwidthParser(LulaWrapperParser):
    """Parser for bandwidth modes (bw, md-bw, md-db-bw)"""

    def process(self, archive_path, timezone='US/Eastern', begin_date=None, end_date=None, analysis_id=None, redis_client=None):
        """Override to store date filters for forward fill"""
        # Store original end_date for forward filling in bw mode
        # The parent process() will normalize it for lula2.py, but we keep the original for parsing
        self.end_date = end_date
        self.timezone = timezone
        return super().process(archive_path, timezone, begin_date, end_date, analysis_id, redis_client)

    def parse_output(self, output):
        """Parse CSV bandwidth data"""
        lines = output.strip().split('\n')
        if len(lines) < 2:
            return []

        # Check if it's tab-delimited (md-bw, md-db-bw) or comma-delimited (bw)
        header = lines[0]
        is_tab_delimited = '\t' in header

        if is_tab_delimited and self.mode == 'md-bw':
            # md-bw format - structure by modem
            # Header: ModemID\tDate/time\tPotentialBW\tLoss\tExtrapolated smooth upstream\t
            #         Shortest round trip\tExtrapolated smooth round trip\tMinimum smooth round trip\tNotes
            return self._parse_modem_bandwidth(lines)
        elif is_tab_delimited:
            # md-db-bw format (tab-delimited, different structure)
            return self._parse_tab_delimited(lines)
        else:
            # bw format (comma-delimited)
            return self._parse_stream_bandwidth(lines)

    def _parse_modem_bandwidth(self, lines):
        """Parse md-bw modem bandwidth data, grouped by modem"""
        modems = {}
        all_timestamps = set()

        for line in lines[1:]:  # Skip header
            if not line.strip():
                continue

            parts = [p.strip() for p in line.split('\t')]
            if len(parts) < 8:
                continue

            modem_id = parts[0]

            # Skip "Modem" (stream end marker) but allow "Modem0", "Modem1", etc.
            if modem_id == "Modem":
                continue

            # Also skip if it doesn't start with "Modem" followed by a digit
            if modem_id.startswith("Modem"):
                modem_number = modem_id.replace("Modem", "")
                if not modem_number or not modem_number.isdigit():
                    continue
            else:
                # Skip anything that doesn't start with "Modem"
                continue

            datetime = parts[1]
            potential_bw = float(parts[2]) if parts[2] and parts[2] != '' else 0
            loss = float(parts[3]) if parts[3] and parts[3] != '' else 0
            upstream = float(parts[4]) if parts[4] and parts[4] != '' else 0
            shortest_rtt = float(parts[5]) if parts[5] and parts[5] != '' else 0
            smooth_rtt = float(parts[6]) if parts[6] and parts[6] != '' else 0
            min_rtt = float(parts[7]) if parts[7] and parts[7] != '' else 0

            all_timestamps.add(datetime)

            if modem_id not in modems:
                modems[modem_id] = []

            modems[modem_id].append({
                'datetime': datetime,
                'potential_bw': potential_bw,
                'loss': loss,
                'upstream': upstream,
                'shortest_rtt': shortest_rtt,
                'smooth_rtt': smooth_rtt,
                'min_rtt': min_rtt
            })

        # Create aggregated bandwidth (sum across all modems per timestamp)
        aggregated = []
        for timestamp in sorted(all_timestamps):
            total_bw = 0
            for modem_data in modems.values():
                for entry in modem_data:
                    if entry['datetime'] == timestamp:
                        total_bw += entry['potential_bw']
                        break
            aggregated.append({
                'datetime': timestamp,
                'total_bw': total_bw
            })

        return {
            'mode': 'md-bw',
            'modems': modems,
            'aggregated': aggregated
        }

    def _parse_tab_delimited(self, lines):
        """Parse generic tab-delimited bandwidth data"""
        data = []
        for line in lines[1:]:  # Skip header
            if not line.strip():
                continue
            parts = [p.strip() for p in line.split('\t')]
            if len(parts) >= 3:
                data.append({
                    'modem_id': parts[0],
                    'datetime': parts[1],
                    'value': parts[2],
                    'notes': parts[-1] if len(parts) > 3 else ''
                })
        return data

    def _parse_stream_bandwidth(self, lines):
        """Parse bw stream bandwidth data with forward fill for continuous visualization"""
        from datetime import datetime, timedelta

        data = []
        for line in lines[1:]:  # Skip header
            if not line.strip():
                continue
            # Don't skip "0,0,0" lines - they may be stream end markers
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

        # Forward fill gaps with last known bandwidth value
        filled_data = []
        fill_interval_seconds = 5  # Add point every 5 seconds during gaps

        for i, point in enumerate(data):
            filled_data.append(point)

            # Check if there's a next point
            if i < len(data) - 1:
                try:
                    # Parse timestamps (format: "2025-10-03 07:36:39")
                    current_time = datetime.strptime(point['datetime'], '%Y-%m-%d %H:%M:%S')
                    next_time = datetime.strptime(data[i+1]['datetime'], '%Y-%m-%d %H:%M:%S')

                    gap_seconds = (next_time - current_time).total_seconds()

                    # If gap > fill_interval_seconds, fill with intermediate points
                    # Only fill if current point is not "Stream end" or "Stream start"
                    if gap_seconds > fill_interval_seconds and 'Stream' not in point['notes']:
                        num_fills = int(gap_seconds / fill_interval_seconds)

                        # Limit fills to prevent excessive data (max 1000 points per gap)
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

                except (ValueError, KeyError) as e:
                    # If timestamp parsing fails, skip filling for this gap
                    continue

        # If we have an end_date filter and the last point isn't a stream end,
        # fill forward to the end_date
        if len(filled_data) > 0 and hasattr(self, 'end_date') and self.end_date:
            last_point = filled_data[-1]

            # Don't fill beyond stream end markers
            if 'Stream' not in last_point['notes']:
                try:
                    last_time = datetime.strptime(last_point['datetime'], '%Y-%m-%d %H:%M:%S')

                    # Parse end_date using dateutil.parser for flexible parsing (handles microseconds, timezones)
                    from dateutil import parser as date_parser
                    end_time_parsed = date_parser.parse(self.end_date)

                    # Remove timezone info if present (make naive for comparison with last_time)
                    if end_time_parsed.tzinfo is not None:
                        end_time_parsed = end_time_parsed.replace(tzinfo=None)

                    end_time = end_time_parsed

                    gap_seconds = (end_time - last_time).total_seconds()

                    if gap_seconds > fill_interval_seconds:
                        num_fills = int(gap_seconds / fill_interval_seconds)

                        # Limit fills to prevent excessive data (max 1000 points)
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
                                    'notes': '(forward filled to end_date)'
                                })

                except (ValueError, KeyError) as e:
                    # If timestamp parsing fails, skip end filling
                    pass

        return filled_data


class ModemStatsParser(LulaWrapperParser):
    """Parser for modem statistics (md)"""

    def parse_output(self, output):
        """Parse modem statistics output"""
        modems = []
        lines = output.split('\n')
        current_modem = None

        for line in lines:
            if line.startswith('Modem '):
                if current_modem:
                    modems.append(current_modem)
                modem_match = re.search(r'Modem (\d+)', line)
                if modem_match:
                    current_modem = {'modem_id': modem_match.group(1), 'stats': {}}
            elif current_modem and '\t' in line:
                # Parse modem stats lines
                if 'Potential Bandwidth' in line:
                    match = re.search(r'\(L/H/A\): ([\d.]+) / ([\d.]+) / ([\d.]+)', line)
                    if match:
                        current_modem['stats']['bandwidth'] = {
                            'low': float(match.group(1)),
                            'high': float(match.group(2)),
                            'avg': float(match.group(3))
                        }
                elif 'Percent Loss' in line:
                    match = re.search(r'\(L/H/A\): ([\d.]+) / ([\d.]+) / ([\d.]+)', line)
                    if match:
                        current_modem['stats']['loss'] = {
                            'low': float(match.group(1)),
                            'high': float(match.group(2)),
                            'avg': float(match.group(3))
                        }
                elif 'Extrapolated Up Delay' in line:
                    match = re.search(r'\(L/H/A\): ([\d.]+) / ([\d.]+) / ([\d.]+)', line)
                    if match:
                        current_modem['stats']['up_delay'] = {
                            'low': float(match.group(1)),
                            'high': float(match.group(2)),
                            'avg': float(match.group(3))
                        }
                elif 'Shortest Round Trip Delay' in line:
                    match = re.search(r'\(L/H/A\): ([\d.]+) / ([\d.]+) / ([\d.]+)', line)
                    if match:
                        current_modem['stats']['shortest_rtt'] = {
                            'low': float(match.group(1)),
                            'high': float(match.group(2)),
                            'avg': float(match.group(3))
                        }
                elif 'Smooth Round Trip' in line and 'Minimum' not in line:
                    match = re.search(r'\(L/H/A\): ([\d.]+) / ([\d.]+) / ([\d.]+)', line)
                    if match:
                        current_modem['stats']['smooth_rtt'] = {
                            'low': float(match.group(1)),
                            'high': float(match.group(2)),
                            'avg': float(match.group(3))
                        }
                elif 'Minimum Smooth Round Trip' in line:
                    match = re.search(r'\(L/H/A\): ([\d.]+) / ([\d.]+) / ([\d.]+)', line)
                    if match:
                        current_modem['stats']['min_rtt'] = {
                            'low': float(match.group(1)),
                            'high': float(match.group(2)),
                            'avg': float(match.group(3))
                        }

        if current_modem:
            modems.append(current_modem)

        return modems


class SessionsParser(LulaWrapperParser):
    """Parser for sessions with metadata extraction from raw logs"""

    def process(self, archive_path, timezone='US/Eastern', begin_date=None, end_date=None):
        """
        Override to extract metadata from raw messages.log before parsing sessions
        """
        # Call parent process() to get session summary from lula2.py FIRST
        result = super().process(archive_path, timezone, begin_date, end_date)

        # Store archive path for on-demand metadata extraction
        self._archive_path = archive_path

        return result

    def _extract_metadata_from_raw_log(self, session_ids, session_timestamps):
        """
        Extract session metadata from raw messages.log files using grep for speed
        Returns dict of session_id -> metadata
        """
        import subprocess
        import re

        if not hasattr(self, '_archive_path') or not self._archive_path:
            return {}

        session_metadata = {}

        try:
            # For each session, use tar + zcat + grep to find it quickly
            for session_id in session_ids:
                # Search for "Allocate SESSION ID" or "Received SESSION ID" (first occurrence)
                # Get 200 lines after to capture all session metadata
                cmd = f'tar -xOf {self._archive_path} "messages.log*.gz" 2>/dev/null | zcat 2>/dev/null | grep -A 200 "Allocate SESSION ID:.*{session_id}\\|Received SESSION ID:.*{session_id}" | head -200'

                result = subprocess.run(
                    cmd,
                    shell=True,
                    capture_output=True,
                    text=True,
                    timeout=30
                )

                if result.returncode == 0 and result.stdout:
                    # Found the session - extract metadata
                    session_metadata[session_id] = {
                        'server': {},
                        'network': {},
                        'config': {},
                        'timing': {},
                        'modems': [],
                        'system': {}
                    }

                    self._extract_session_metadata_from_text(result.stdout, session_id, session_metadata[session_id])

        except Exception as e:
            print(f"Warning: Error extracting metadata: {e}")

        return session_metadata

    def _extract_session_metadata_from_text(self, text, session_id, metadata):
        """Extract metadata for a specific session from log text"""
        lines = text.split('\n')

        # Find the SESSION ID line
        session_line_idx = None
        for i, line in enumerate(lines):
            if f'SESSION ID: {session_id}' in line or f'SESSION ID:{session_id}' in line:
                session_line_idx = i
                break

        if session_line_idx is None:
            return

        # Look at 100 lines before and 200 lines after
        start_idx = max(0, session_line_idx - 100)
        end_idx = min(len(lines), session_line_idx + 200)

        for line in lines[start_idx:end_idx]:
                # Server instance and version
                server_match = re.search(r"from (Boss\S+) with version: ([\d\w.]+)", line)
                if server_match:
                    metadata['server']['instance'] = server_match.group(1)
                    metadata['server']['version'] = server_match.group(2)

                # Channel capabilities
                cap_match = re.search(r"channel capabilities: (\[.*?\])", line)
                if cap_match:
                    metadata['server']['capabilities'] = cap_match.group(1)

                # Collector address
                collector_match = re.search(r"'destination': \['([\d.]+)', (\d+)\]", line)
                if collector_match:
                    metadata['network']['collector_address'] = f"{collector_match.group(1)}:{collector_match.group(2)}"

                # IFB address
                ifb_match = re.search(r"ifbAddress: \['([\d.]+)', (\d+)\]", line)
                if ifb_match:
                    metadata['network']['ifb_address'] = f"{ifb_match.group(1)}:{ifb_match.group(2)}"

                # STUN server
                stun_match = re.search(r"'host': '([^']+)'.*'port': (\d+)", line)
                if stun_match:
                    metadata['network']['stun_server'] = f"{stun_match.group(1)}:{stun_match.group(2)}"

                # NAT punching
                nat_match = re.search(r"natPuncturingConfiguration:.*'enabled': (True|False)", line)
                if nat_match:
                    metadata['network']['nat_punching'] = nat_match.group(1) == 'True'

                # Streamer port
                port_match = re.search(r"listening to socket on port (\d+)", line)
                if port_match:
                    metadata['network']['streamer_port'] = int(port_match.group(1))

                # Pipeline type
                pipeline_match = re.search(r"'type': '(liveStreaming|preview|playback)'", line)
                if pipeline_match:
                    metadata['config']['pipeline_type'] = pipeline_match.group(1)

                # Profile
                profile_match = re.search(r"profile (\w+)", line)
                if profile_match and 'profile' not in metadata['config']:
                    metadata['config']['profile'] = profile_match.group(1)

                # State timing
                timing_match = re.search(r'Spent: "([0-9.]+)" seconds in state: "(\w+)"', line)
                if timing_match:
                    state_name = timing_match.group(2).lower() + '_duration'
                    metadata['timing'][state_name] = float(timing_match.group(1))

                # Active modems from ping
                ping_match = re.search(r'PING ([\d.:a-f]+).*from.*?(\w+):', line)
                if ping_match:
                    target = ping_match.group(1)
                    interface = ping_match.group(2)
                    ip_version = 'IPv6' if ':' in target else 'IPv4'
                    metadata['_temp_modem'] = {'interface': interface, 'target': target, 'ip_version': ip_version}

                # RTT from ping
                rtt_match = re.search(r'time=([0-9.]+)\s*ms', line)
                if rtt_match and '_temp_modem' in metadata:
                    modem = metadata['_temp_modem']
                    modem['rtt'] = float(rtt_match.group(1))
                    # Check if modem not already added
                    if modem not in metadata['modems']:
                        metadata['modems'].append(modem.copy())
                    del metadata['_temp_modem']

                # System readiness
                video_match = re.search(r"'video': '(\w+)'", line)
                if video_match:
                    metadata['system']['video_state'] = video_match.group(1)

                # Camera status
                camera_match = re.search(r"camera connected=(True|False)", line)
                if camera_match:
                    metadata['system']['camera_connected'] = camera_match.group(1) == 'True'

    def parse_output(self, output):
        """Parse session output with detailed metadata extraction"""
        from datetime import datetime

        session_starts = {}  # session_id -> start_time
        session_ends = {}    # session_id -> end_time
        session_timestamps = {}  # session_id -> timestamp for finding right log file

        lines = output.split('\n')

        # First pass: collect all session IDs and their timestamps from lula2.py output
        session_ids_found = set()

        for line in lines:
            # Strip ANSI color codes
            clean_line = re.sub(r'\x1b\[\d+m', '', line)

            # Match session start
            start_match = re.search(r'(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}\.\d+[+-]\d{2}:\d{2}).*Session id:\s*(\d+)', clean_line)
            if start_match:
                timestamp = start_match.group(1)
                session_id = start_match.group(2)
                if session_id not in session_starts:
                    session_starts[session_id] = timestamp
                    session_timestamps[session_id] = timestamp
                    session_ids_found.add(session_id)
                continue

            # Match "End Only" summary line
            end_match = re.search(r'End Only \(session id:\s*(\d+)\):\s*(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}\.\d+[+-]\d{2}:\d{2})', clean_line)
            if end_match:
                session_id = end_match.group(1)
                timestamp = end_match.group(2)
                session_ids_found.add(session_id)
                session_timestamps[session_id] = timestamp
                if session_id not in session_ends:
                    session_ends[session_id] = timestamp
                continue

            # Match stream end
            stream_end_match = re.search(r'(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}\.\d+[+-]\d{2}:\d{2}).*Stream end', clean_line)
            if stream_end_match:
                timestamp = stream_end_match.group(1)
                if session_starts:
                    last_session_id = list(session_starts.keys())[-1]
                    if last_session_id not in session_ends:
                        session_ends[last_session_id] = timestamp
                continue

        # TODO: Metadata extraction disabled - needs optimization
        # The grep approach is too slow for large archives with 40+ compressed log files
        session_metadata = {}
        # session_metadata = self._extract_metadata_from_raw_log(session_ids_found, session_timestamps)

        # Create session objects with metadata
        all_session_ids = set(list(session_starts.keys()) + list(session_ends.keys()))

        sessions = []
        # Sort by start timestamp (or end if no start), not by session ID
        def get_sort_key(sid):
            if sid in session_starts:
                return session_starts[sid]
            elif sid in session_ends:
                return session_ends[sid]
            return ""

        for session_id in sorted(all_session_ids, key=get_sort_key):
            start = session_starts.get(session_id)
            end = session_ends.get(session_id)

            # Determine session type
            if start and end:
                session_type = 'complete'
                # Calculate duration
                try:
                    start_dt = datetime.fromisoformat(start)
                    end_dt = datetime.fromisoformat(end)
                    duration_seconds = (end_dt - start_dt).total_seconds()
                    hours = int(duration_seconds // 3600)
                    minutes = int((duration_seconds % 3600) // 60)
                    seconds = int(duration_seconds % 60)
                    duration = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
                except:
                    duration = 'N/A'
            elif start:
                session_type = 'start_only'
                duration = None
            else:
                session_type = 'end_only'
                duration = None

            # Get metadata for this session (may be empty if not found in logs)
            metadata = session_metadata.get(session_id, {
                'server': {},
                'network': {},
                'config': {},
                'timing': {},
                'modems': [],
                'system': {}
            })

            # Calculate time to stream
            timing = metadata.get('timing', {})
            time_to_stream = sum([
                timing.get('selectchannel_duration', 0),
                timing.get('startcollector_duration', 0)
            ])
            if time_to_stream > 0:
                metadata['timing']['time_to_stream'] = round(time_to_stream, 3)

            # Clean up temp fields
            if '_temp_modem' in metadata:
                del metadata['_temp_modem']

            sessions.append({
                'session_id': session_id,
                'type': session_type,
                'start': start,
                'end': end,
                'duration': duration,
                'metadata': metadata
            })

        return sessions


class ErrorParser(LulaWrapperParser):
    """Parser for error modes (known, error, v, all)"""

    def parse_output(self, output):
        """Parse error output"""
        lines = output.strip().split('\n')
        return {
            'total_lines': len(lines),
            'lines': lines[:1000]  # Limit to first 1000 for performance
        }


class SystemParser(LulaWrapperParser):
    """Parser for system metrics (memory, grading)"""

    def parse_output(self, output):
        """Parse system metrics output"""
        lines = output.strip().split('\n')

        if self.mode == 'memory':
            return self._parse_memory_output(lines)
        elif self.mode == 'grading':
            return self._parse_grading_output(lines)
        else:
            return {
                'lines': lines,
                'count': len(lines)
            }

    def _parse_memory_output(self, lines):
        """Parse memory usage output into structured data for visualization"""
        data_points = []

        for line in lines:
            # Strip ANSI color codes
            clean_line = re.sub(r'\x1b\[\d+m', '', line)

            # Extract timestamp (format: 2024-01-15 14:32:45.123456-05:00 or similar)
            timestamp_match = re.search(r'(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2})', clean_line)
            if not timestamp_match:
                continue

            timestamp = timestamp_match.group(1)

            # Determine component (VIC, COR for Corecard, or Server)
            component = 'Unknown'
            if 'VIC:' in line:
                component = 'VIC'
            elif 'COR:' in line:
                component = 'Corecard'
            elif line.strip().startswith('20') and 'VIC' not in line and 'COR' not in line:
                # Server logs (just timestamp at start, no prefix)
                component = 'Server'

            # Parse memory usage patterns
            # Pattern 1: "25.7% (531 MB out of 2069 MB), cached - 145 MB"
            usage_match = re.search(r'(\d+\.?\d*)%\s*\((\d+)\s*MB\s*out of\s*(\d+)\s*MB\)', clean_line)
            if usage_match:
                percent = float(usage_match.group(1))
                used_mb = int(usage_match.group(2))
                total_mb = int(usage_match.group(3))

                # Extract cached memory if present
                cached_mb = 0
                cached_match = re.search(r'cached\s*-\s*(\d+)\s*MB', clean_line)
                if cached_match:
                    cached_mb = int(cached_match.group(1))

                data_points.append({
                    'timestamp': timestamp,
                    'component': component,
                    'percent': percent,
                    'used_mb': used_mb,
                    'total_mb': total_mb,
                    'cached_mb': cached_mb,
                    'is_warning': 'WARNING' in line or 'too high' in line
                })
                continue

            # Pattern 2: "Memory usage is too high: 95.7%"
            warning_match = re.search(r'(\d+\.?\d*)%', clean_line)
            if warning_match and ('too high' in clean_line or 'WARNING' in line):
                percent = float(warning_match.group(1))
                data_points.append({
                    'timestamp': timestamp,
                    'component': component,
                    'percent': percent,
                    'used_mb': None,
                    'total_mb': None,
                    'cached_mb': 0,
                    'is_warning': True
                })
                continue

            # Pattern 3: Simple format "COR: 7.8%" or "VIC: 25.7%"
            simple_match = re.search(r'(\d+\.?\d*)%', clean_line)
            if simple_match:
                percent = float(simple_match.group(1))
                data_points.append({
                    'timestamp': timestamp,
                    'component': component,
                    'percent': percent,
                    'used_mb': None,
                    'total_mb': None,
                    'cached_mb': 0,
                    'is_warning': False
                })

        return data_points

    def _parse_grading_output(self, lines):
        """Parse modem grading output into structured data for visualization"""
        events = []
        current_timestamp = None

        for line in lines:
            # Strip ANSI color codes
            clean_line = re.sub(r'\x1b\[\d+m', '', line)

            # Extract timestamp
            timestamp_match = re.search(r'(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2})', clean_line)
            if timestamp_match:
                current_timestamp = timestamp_match.group(1)
            else:
                continue

            # Skip empty lines
            if not clean_line.strip():
                continue

            # Parse different line formats
            parts = clean_line.split('\t')
            if len(parts) < 3:
                continue

            # Remove timestamp prefix if present
            if ':' in parts[0]:
                parts = parts[0].split(':', 1)[1].strip().split('\t') + parts[1:]

            # Format 1: "ModemID 0 Full Service" or "ModemID 0 Limited Service"
            if 'Service' in clean_line and ('Full' in clean_line or 'Limited' in clean_line):
                modem_match = re.search(r'ModemID\s+(\d+)\s+(Full|Limited)\s+Service', clean_line)
                if modem_match:
                    modem_id = int(modem_match.group(1))
                    service_level = modem_match.group(2)
                    events.append({
                        'timestamp': current_timestamp,
                        'modem_id': modem_id,
                        'event_type': 'service_change',
                        'service_level': service_level,
                        'metric1': None,
                        'metric2': None,
                        'quality_status': None
                    })

            # Format 2: "ModemID 0 126 86 Good enough for full service"
            # or "ModemID 0 539 490 Not good enough for full service"
            elif 'good enough' in clean_line.lower() or 'not good enough' in clean_line.lower():
                metric_match = re.search(r'ModemID\s+(\d+)\s+(\d+)\s+(\d+)\s+(.*)', clean_line)
                if metric_match:
                    modem_id = int(metric_match.group(1))
                    metric1 = int(metric_match.group(2))
                    metric2 = int(metric_match.group(3))
                    quality_status = metric_match.group(4).strip()

                    # Determine if this is good or bad quality
                    is_good_quality = 'not good enough' not in quality_status.lower()

                    events.append({
                        'timestamp': current_timestamp,
                        'modem_id': modem_id,
                        'event_type': 'quality_metric',
                        'service_level': None,
                        'metric1': metric1,
                        'metric2': metric2,
                        'quality_status': quality_status,
                        'is_good_quality': is_good_quality
                    })

        # Organize events by modem for easier visualization
        modems = {}
        for event in events:
            modem_id = event['modem_id']
            if modem_id not in modems:
                modems[modem_id] = {
                    'modem_id': modem_id,
                    'events': [],
                    'service_changes': [],
                    'quality_metrics': []
                }

            modems[modem_id]['events'].append(event)

            if event['event_type'] == 'service_change':
                modems[modem_id]['service_changes'].append({
                    'timestamp': event['timestamp'],
                    'service_level': event['service_level']
                })
            elif event['event_type'] == 'quality_metric':
                modems[modem_id]['quality_metrics'].append({
                    'timestamp': event['timestamp'],
                    'metric1': event['metric1'],
                    'metric2': event['metric2'],
                    'quality_status': event['quality_status'],
                    'is_good_quality': event['is_good_quality']
                })

        return {
            'modems': list(modems.values()),
            'all_events': events
        }


class DeviceIDParser(LulaWrapperParser):
    """Parser for device IDs"""

    def parse_output(self, output):
        """Parse device ID output"""
        # Extract IDs from output
        boss_id = None
        device_id = None

        for line in output.split('\n'):
            if 'Boss' in line or 'boss' in line:
                match = re.search(r'[:\s]([a-zA-Z0-9-]+)', line)
                if match and not boss_id:
                    boss_id = match.group(1)
            if 'Device' in line or 'device' in line:
                match = re.search(r'[:\s]([a-zA-Z0-9-]+)', line)
                if match and not device_id:
                    device_id = match.group(1)

        return {
            'boss_id': boss_id or 'Not found',
            'device_id': device_id or 'Not found',
            'raw_lines': output.split('\n')[:10]
        }


class DebugParser(LulaWrapperParser):
    """Parser for debug-level logs"""

    def parse_output(self, output):
        """Parse debug output"""
        lines = output.strip().split('\n')
        return {
            'total_lines': len(lines),
            'lines': lines[:1000]  # Limit to first 1000 for performance
        }


class FFmpegParser(LulaWrapperParser):
    """Parser for FFmpeg-related logs"""

    def parse_output(self, output):
        """Parse FFmpeg logs"""
        lines = output.strip().split('\n')
        return {
            'total_lines': len(lines),
            'lines': lines[:1000]  # Limit to first 1000 for performance
        }


class FFmpegVerboseParser(LulaWrapperParser):
    """Parser for FFmpeg verbose logs"""

    def parse_output(self, output):
        """Parse FFmpeg verbose output"""
        lines = output.strip().split('\n')
        return {
            'total_lines': len(lines),
            'lines': lines[:1000]  # Limit to first 1000 for performance
        }


class FFmpegAudioParser(LulaWrapperParser):
    """Parser for FFmpeg audio-related logs"""

    def parse_output(self, output):
        """Parse FFmpeg audio logs"""
        lines = output.strip().split('\n')
        return {
            'total_lines': len(lines),
            'lines': lines[:1000]  # Limit to first 1000 for performance
        }
