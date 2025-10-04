"""
Modular log parsers for LiveU logs
Uses lula_wrapper to delegate to proven lula2.py script
"""
from .base import BaseParser
from .lula_wrapper import (
    BandwidthParser,
    ModemStatsParser,
    SessionsParser,
    ErrorParser,
    SystemParser,
    DeviceIDParser
)

# Parser registry
PARSERS = {
    'bw': BandwidthParser,
    'md-bw': BandwidthParser,
    'md-db-bw': BandwidthParser,
    'md': ModemStatsParser,
    'sessions': SessionsParser,
    'known': ErrorParser,
    'error': ErrorParser,
    'v': ErrorParser,
    'all': ErrorParser,
    'memory': SystemParser,
    'grading': SystemParser,
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
    'BandwidthParser',
    'ModemStatsParser',
    'SessionsParser',
    'ErrorParser',
    'SystemParser',
    'DeviceIDParser',
    'get_parser',
    'PARSERS',
]
