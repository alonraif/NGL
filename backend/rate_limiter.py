"""
Rate limiter instance for the application
"""
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from config import Config

# Initialize limiter
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["200 per hour"],
    storage_uri=Config.REDIS_URL
)
