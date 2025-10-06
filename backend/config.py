"""
Configuration management
"""
import os
from datetime import timedelta

class Config:
    """Base configuration"""
    # Database
    DATABASE_URL = os.getenv('DATABASE_URL', 'postgresql://ngl_user:ngl_password@localhost:5432/ngl_db')

    # Redis
    REDIS_URL = os.getenv('REDIS_URL', 'redis://localhost:6379/0')

    # JWT
    JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY', 'your-secret-key-change-in-production')
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=24)
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(days=30)

    # CORS
    CORS_ORIGINS = os.getenv('CORS_ORIGINS', 'http://localhost:3000').split(',')

    # File uploads
    UPLOAD_FOLDER = os.getenv('UPLOAD_FOLDER', '/app/uploads')
    TEMP_FOLDER = os.getenv('TEMP_FOLDER', '/app/temp')
    MAX_CONTENT_LENGTH = 500 * 1024 * 1024  # 500MB

    # Retention
    UPLOAD_RETENTION_DAYS = int(os.getenv('UPLOAD_RETENTION_DAYS', '30'))
    SOFT_DELETE_GRACE_DAYS = 90

    # Celery
    CELERY_BROKER_URL = REDIS_URL
    CELERY_RESULT_BACKEND = REDIS_URL
    CELERY_BEAT_SCHEDULE = {
        'cleanup-expired-files': {
            'task': 'tasks.cleanup_expired_files',
            'schedule': 3600.0,  # Every hour
        },
        'hard-delete-old-soft-deletes': {
            'task': 'tasks.hard_delete_old_soft_deletes',
            'schedule': 86400.0,  # Every day
        },
    }
