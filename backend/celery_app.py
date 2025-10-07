"""Celery application and task configuration."""
from celery import Celery
import os

from config import Config

# Initialize Celery with automatic task discovery
celery = Celery('ngl', include=['tasks'])

# Configure from environment / config
REDIS_URL = os.getenv('REDIS_URL', 'redis://localhost:6379/0')

celery.conf.update(
    broker_url=REDIS_URL,
    result_backend=REDIS_URL,
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    beat_schedule=Config.CELERY_BEAT_SCHEDULE,
    imports=('tasks',),
)
