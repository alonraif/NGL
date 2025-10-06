"""
Celery background tasks
"""
from celery_app import celery
from database import SessionLocal
from models import LogFile, Analysis, DeletionLog
from datetime import datetime, timedelta
import os
from storage_service import StorageFactory


@celery.task(name='celery_app.cleanup_expired_files')
def cleanup_expired_files():
    """
    Clean up expired log files and analyses
    Runs every hour
    """
    db = SessionLocal()
    try:
        now = datetime.utcnow()

        # Find expired log files (not pinned, not already deleted)
        expired_files = db.query(LogFile).filter(
            LogFile.expires_at <= now,
            LogFile.is_pinned == False,
            LogFile.is_deleted == False
        ).all()

        deleted_count = 0
        for log_file in expired_files:
            # Soft delete the file
            log_file.is_deleted = True
            log_file.deleted_at = now
            log_file.deletion_type = 'soft'

            # Log the deletion
            deletion_log = DeletionLog(
                entity_type='log_file',
                entity_id=log_file.id,
                entity_name=log_file.original_filename,
                deletion_type='auto',
                reason='Expired (retention period exceeded)',
                can_recover=True,
                context_data={
                    'retention_days': log_file.retention_days,
                    'expires_at': log_file.expires_at.isoformat() if log_file.expires_at else None
                }
            )
            db.add(deletion_log)
            deleted_count += 1

        # Find expired analyses (not already deleted)
        expired_analyses = db.query(Analysis).filter(
            Analysis.expires_at <= now,
            Analysis.is_deleted == False
        ).all()

        for analysis in expired_analyses:
            # Soft delete the analysis
            analysis.is_deleted = True
            analysis.deleted_at = now

            # Log the deletion
            deletion_log = DeletionLog(
                entity_type='analysis',
                entity_id=analysis.id,
                entity_name=f"Analysis {analysis.id} - {analysis.parse_mode}",
                deletion_type='auto',
                reason='Expired (retention period exceeded)',
                can_recover=True,
                context_data={
                    'parse_mode': analysis.parse_mode,
                    'retention_days': analysis.retention_days,
                    'expires_at': analysis.expires_at.isoformat() if analysis.expires_at else None
                }
            )
            db.add(deletion_log)
            deleted_count += 1

        db.commit()

        return {
            'status': 'success',
            'deleted_count': deleted_count,
            'timestamp': now.isoformat()
        }

    except Exception as e:
        db.rollback()
        return {
            'status': 'error',
            'error': str(e)
        }
    finally:
        db.close()


@celery.task(name='celery_app.hard_delete_old_soft_deletes')
def hard_delete_old_soft_deletes():
    """
    Permanently delete files that have been soft-deleted for > 90 days
    Runs daily
    """
    db = SessionLocal()
    try:
        grace_period_days = 90
        cutoff_date = datetime.utcnow() - timedelta(days=grace_period_days)

        # Find old soft-deleted log files
        old_deleted_files = db.query(LogFile).filter(
            LogFile.is_deleted == True,
            LogFile.deletion_type == 'soft',
            LogFile.deleted_at <= cutoff_date
        ).all()

        deleted_count = 0
        for log_file in old_deleted_files:
            # Delete physical file based on storage type
            try:
                if log_file.storage_type == 's3':
                    # Delete from S3
                    storage_service = StorageFactory.get_storage_service()
                    if storage_service.get_storage_type() == 's3':
                        storage_service.delete_file(log_file.file_path)
                    else:
                        print(f"Warning: S3 storage not available to delete {log_file.file_path}")
                else:
                    # Delete from local storage
                    if os.path.exists(log_file.file_path):
                        os.remove(log_file.file_path)
            except Exception as e:
                print(f"Error deleting file {log_file.file_path} (storage: {log_file.storage_type}): {e}")

            # Log hard deletion
            deletion_log = DeletionLog(
                entity_type='log_file',
                entity_id=log_file.id,
                entity_name=log_file.original_filename,
                deletion_type='hard',
                reason=f'Hard delete after {grace_period_days} day grace period',
                can_recover=False,
                context_data={
                    'soft_deleted_at': log_file.deleted_at.isoformat() if log_file.deleted_at else None,
                    'file_path': log_file.file_path,
                    'file_size_bytes': log_file.file_size_bytes,
                    'storage_type': log_file.storage_type
                }
            )
            db.add(deletion_log)

            # Delete from database
            db.delete(log_file)
            deleted_count += 1

        # Find old soft-deleted analyses
        old_deleted_analyses = db.query(Analysis).filter(
            Analysis.is_deleted == True,
            Analysis.deleted_at <= cutoff_date
        ).all()

        for analysis in old_deleted_analyses:
            # Log hard deletion
            deletion_log = DeletionLog(
                entity_type='analysis',
                entity_id=analysis.id,
                entity_name=f"Analysis {analysis.id}",
                deletion_type='hard',
                reason=f'Hard delete after {grace_period_days} day grace period',
                can_recover=False
            )
            db.add(deletion_log)

            # Delete from database (cascade will handle results)
            db.delete(analysis)
            deleted_count += 1

        db.commit()

        return {
            'status': 'success',
            'deleted_count': deleted_count,
            'grace_period_days': grace_period_days,
            'timestamp': datetime.utcnow().isoformat()
        }

    except Exception as e:
        db.rollback()
        return {
            'status': 'error',
            'error': str(e)
        }
    finally:
        db.close()
