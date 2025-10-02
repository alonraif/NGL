"""
Wrapper for lula2.py - delegates parsing to the proven script
"""
import subprocess
import os
import re
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

    def process(self, archive_path, timezone='US/Eastern', begin_date=None, end_date=None):
        """
        Full processing pipeline: call lula2.py with archive file directly

        Overrides BaseParser.process() to skip extraction and call lula2.py directly
        """
        # Build lula2.py command with the archive file
        cmd = ['python3', '/app/lula2.py', archive_path, '-p', self.mode, '-t', timezone]

        if begin_date:
            cmd.extend(['-b', begin_date])
        if end_date:
            cmd.extend(['-e', end_date])

        # Execute lula2.py
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=600
        )

        if result.returncode != 0:
            raise Exception(f"lula2.py error: {result.stderr}")

        raw_output = result.stdout

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

    def parse_output(self, output):
        """Parse CSV bandwidth data"""
        lines = output.strip().split('\n')
        if len(lines) < 2:
            return []

        # Parse CSV
        data = []
        for line in lines[1:]:  # Skip header
            if not line.strip() or line.startswith('0,0,0'):
                continue
            parts = [p.strip() for p in line.split(',')]
            if len(parts) >= 3:
                data.append({
                    'datetime': parts[0],
                    'total bitrate': parts[1],
                    'video bitrate': parts[2],
                    'notes': parts[3] if len(parts) > 3 else ''
                })
        return data


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

        if current_modem:
            modems.append(current_modem)

        return modems


class SessionsParser(LulaWrapperParser):
    """Parser for sessions"""

    def parse_output(self, output):
        """Parse session output"""
        sessions = []
        lines = output.split('\n')

        for line in lines:
            if 'Stream session' in line or 'Session' in line:
                # Parse session info (basic extraction)
                session = {'raw': line.strip()}
                sessions.append(session)

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
        return {
            'lines': lines,
            'count': len(lines)
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
