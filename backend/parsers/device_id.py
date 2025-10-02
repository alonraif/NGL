"""
Device ID parser for id mode
"""
import re
from .base import BaseParser


class DeviceIDParser(BaseParser):
    """Parser for device and server IDs"""

    # Patterns for ID extraction
    BOSS_ID_PATTERN = re.compile(r'boss[_\s]*id[:\s]*([a-zA-Z0-9-]+)', re.IGNORECASE)
    DEVICE_ID_PATTERN = re.compile(r'device[_\s]*id[:\s]*([a-zA-Z0-9-]+)', re.IGNORECASE)
    SERVER_ID_PATTERN = re.compile(r'server[_\s]*id[:\s]*([a-zA-Z0-9-]+)', re.IGNORECASE)
    SERIAL_PATTERN = re.compile(r'serial[_\s]*(?:number|num)?[:\s]*([a-zA-Z0-9-]+)', re.IGNORECASE)

    def parse(self, log_path, timezone='US/Eastern', begin_date=None, end_date=None):
        """
        Parse device and server identification information

        Returns boss ID, device ID, server ID, serial numbers
        """
        ids = {
            'boss_id': None,
            'device_id': None,
            'server_id': None,
            'serial_number': None
        }
        raw_lines = []

        with open(log_path, 'r', encoding='utf-8', errors='ignore') as f:
            for line in f:
                # Look for ID-related keywords
                if any(keyword in line.lower() for keyword in ['boss', 'device', 'server', 'serial']):

                    # Boss ID
                    boss_match = self.BOSS_ID_PATTERN.search(line)
                    if boss_match and not ids['boss_id']:
                        ids['boss_id'] = boss_match.group(1)
                        raw_lines.append(f"Boss ID: {boss_match.group(1)} | {line.strip()}")

                    # Device ID
                    device_match = self.DEVICE_ID_PATTERN.search(line)
                    if device_match and not ids['device_id']:
                        ids['device_id'] = device_match.group(1)
                        raw_lines.append(f"Device ID: {device_match.group(1)} | {line.strip()}")

                    # Server ID
                    server_match = self.SERVER_ID_PATTERN.search(line)
                    if server_match and not ids['server_id']:
                        ids['server_id'] = server_match.group(1)
                        raw_lines.append(f"Server ID: {server_match.group(1)} | {line.strip()}")

                    # Serial Number
                    serial_match = self.SERIAL_PATTERN.search(line)
                    if serial_match and not ids['serial_number']:
                        ids['serial_number'] = serial_match.group(1)
                        raw_lines.append(f"Serial: {serial_match.group(1)} | {line.strip()}")

                # Stop once we have all IDs
                if all(ids.values()):
                    break

        raw_output = '\n'.join(raw_lines) if raw_lines else 'No device IDs found in log file'

        # Format parsed data
        parsed_data = {
            'boss_id': ids['boss_id'] or 'Not found',
            'device_id': ids['device_id'] or 'Not found',
            'server_id': ids['server_id'] or 'Not found',
            'serial_number': ids['serial_number'] or 'Not found'
        }

        return {
            'raw_output': raw_output,
            'parsed_data': parsed_data
        }
