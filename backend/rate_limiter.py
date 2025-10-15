"""
Rate limiter instance for the application
"""
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from config import Config

def _parse_default_limits(raw_limit: str):
    """Parse configurable default rate limits into a list for Flask-Limiter."""
    if not raw_limit:
        return []
    # Allow comma or semicolon separated values for multiple limits
    separators = [',', ';']
    for sep in separators:
        if sep in raw_limit:
            return [limit.strip() for limit in raw_limit.split(sep) if limit.strip()]
    return [raw_limit]


default_limits = _parse_default_limits(Config.RATE_LIMIT_DEFAULT)

# Initialize limiter with optional global default limits
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=default_limits,
    storage_uri=Config.REDIS_URL
)
