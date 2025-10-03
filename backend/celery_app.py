"""
Celery application and task configuration
"""
from celery import Celery
from celery.schedules import crontab
import os

# Initialize Celery
celery = Celery('ngl')

# Configure from config module
REDIS_URL = os.getenv('REDIS_URL', 'redis://localhost:6379/0')

celery.conf.update(
    broker_url=REDIS_URL,
    result_backend=REDIS_URL,
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    beat_schedule={
        'cleanup-expired-files': {
            'task': 'celery_app.cleanup_expired_files',
            'schedule': 3600.0,  # Every hour
        },
        'hard-delete-old-soft-deletes': {
            'task': 'celery_app.hard_delete_old_soft_deletes',
            'schedule': 86400.0,  # Every day
        },
    }
)

# Import tasks
if __name__ != '__main__':
    from tasks import cleanup_expired_files, hard_delete_old_soft_deletes
