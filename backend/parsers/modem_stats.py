"""
Modem statistics parser for md mode
"""
import re
from .base import BaseParser


class ModemStatsParser(BaseParser):
    """Parser for modem statistics"""

    # Pattern for modem info lines
    MODEM_PATTERN = re.compile(
        r'Modem\s+(\d+).*?'
        r'Type:\s*(\w+).*?'
        r'Signal:\s*(-?\d+).*?'
        r'Throughput:\s*(\d+)',
        re.IGNORECASE | re.DOTALL
    )

    def parse(self, log_path, timezone='US/Eastern', begin_date=None, end_date=None):
        """
        Parse modem statistics from messages.log

        Returns structured modem data with signal strength, throughput, etc.
        """
        modems = {}
        raw_lines = []

        with open(log_path, 'r', encoding='utf-8', errors='ignore') as f:
            for line in f:
                # Look for modem-related information
                if 'modem' in line.lower() and any(keyword in line.lower() for keyword in ['signal', 'throughput', 'type']):
                    raw_lines.append(line.strip())

                    # Try to extract structured data
                    match = self.MODEM_PATTERN.search(line)
                    if match:
                        modem_id = match.group(1)
                        modem_type = match.group(2)
                        signal = match.group(3)
                        throughput = match.group(4)

                        if modem_id not in modems:
                            modems[modem_id] = {
                                'id': modem_id,
                                'type': modem_type,
                                'signal_samples': [],
                                'throughput_samples': []
                            }

                        modems[modem_id]['signal_samples'].append(int(signal))
                        modems[modem_id]['throughput_samples'].append(int(throughput))

        # Calculate statistics for each modem
        parsed_data = []
        for modem_id, data in modems.items():
            if data['signal_samples'] and data['throughput_samples']:
                parsed_data.append({
                    'modem_id': modem_id,
                    'type': data['type'],
                    'avg_signal': sum(data['signal_samples']) / len(data['signal_samples']),
                    'min_signal': min(data['signal_samples']),
                    'max_signal': max(data['signal_samples']),
                    'avg_throughput': sum(data['throughput_samples']) / len(data['throughput_samples']),
                    'min_throughput': min(data['throughput_samples']),
                    'max_throughput': max(data['throughput_samples']),
                    'sample_count': len(data['signal_samples'])
                })

        raw_output = '\n'.join(raw_lines)

        return {
            'raw_output': raw_output,
            'parsed_data': parsed_data
        }
