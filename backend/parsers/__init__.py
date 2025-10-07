"""
Modular log parsers for LiveU logs
Uses lula_wrapper to delegate to proven lula2.py script
"""
from .base import BaseParser
from .bandwidth import StreamBandwidthParser, ModemBandwidthParser
from .databridge_bandwidth import DataBridgeBandwidthParser
from .memory import MemoryParser
from .grading import GradingParser
from .cpu import CpuParser
from .modem_events import ModemEventsParser, ModemEventsSortedParser
from .sessions_native import SessionsParser
from .lula_wrapper import (
    ModemStatsParser,
    ErrorParser,
    SystemParser,
    DeviceIDParser
)

# Parser registry
PARSERS = {
    'bw': StreamBandwidthParser,
    'md-bw': ModemBandwidthParser,
    'md-db-bw': DataBridgeBandwidthParser,
    'md': ModemStatsParser,
    'sessions': SessionsParser,
    'known': ErrorParser,
    'error': ErrorParser,
    'v': ErrorParser,
    'all': ErrorParser,
    'memory': MemoryParser,
    'grading': GradingParser,
    'cpu': CpuParser,
    'modemevents': ModemEventsParser,
    'modemeventssorted': ModemEventsSortedParser,
    'id': DeviceIDParser,
}

def get_parser(mode):
    """Get parser instance for the given mode"""
    parser_class = PARSERS.get(mode)
    if not parser_class:
        raise ValueError(f"Unknown parse mode: {mode}")
    return parser_class(mode)

__all__ = [
    'BaseParser',
    'StreamBandwidthParser',
    'ModemStatsParser',
    'SessionsParser',
    'ErrorParser',
    'SystemParser',
    'DeviceIDParser',
    'get_parser',
    'PARSERS',
]
