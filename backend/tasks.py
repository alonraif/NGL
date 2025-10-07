"""
Celery background tasks
"""
from celery_app import celery
from celery.utils.log import get_task_logger
from database import SessionLocal
from models import LogFile, Analysis, DeletionLog, SSLConfiguration
from datetime import datetime, timedelta
import os
from storage_service import StorageFactory
from config import Config
from ssl_service import (
    SSLConfigurationError,
    cert_paths_exist,
    disable_nginx_ssl_snippet,
    get_lets_encrypt_live_paths,
    normalize_domains,
    read_certificate_metadata_from_path,
    run_certbot,
    verify_https_endpoint,
    write_enforce_redirect,
    write_http_redirect_snippet,
)


logger = get_task_logger(__name__)


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


def _load_ssl_config(db, config_id):
    return db.query(SSLConfiguration).filter(SSLConfiguration.id == config_id).first()


from typing import Optional


@celery.task(name='tasks.issue_ssl_certificate')
def issue_ssl_certificate(config_id: int, staging: Optional[bool] = None):
    """Request a new Let\'s Encrypt certificate via certbot."""
    db = SessionLocal()
    try:
        ssl_config = _load_ssl_config(db, config_id)
        if not ssl_config:
            logger.error('SSL configuration %s not found for issuance', config_id)
            return {'status': 'error', 'message': 'SSL configuration not found'}

        domains = normalize_domains(ssl_config.primary_domain, ssl_config.alternate_domains or [])
        if not domains:
            logger.error('No domains configured for SSL issuance (config_id=%s)', config_id)
            ssl_config.certificate_status = 'error'
            ssl_config.last_error = 'No domains configured'
            ssl_config.updated_at = datetime.utcnow()
            db.commit()
            return {'status': 'error', 'message': 'No domains configured'}

        staging_flag = Config.SSL_STAGING if staging is None else staging
        result = run_certbot(domains, Config.SSL_CERTBOT_EMAIL, staging_flag)
        output = (result.stdout or '') + (result.stderr or '')

        if result.returncode != 0:
            logger.error('Certbot issuance failed (config_id=%s): %s', config_id, output)
            ssl_config.certificate_status = 'error'
            ssl_config.last_error = output[-2000:]
            ssl_config.updated_at = datetime.utcnow()
            db.commit()
            return {
                'status': 'error',
                'message': 'Certbot failed',
                'returncode': result.returncode,
                'output': output[-4000:],
            }

        paths = get_lets_encrypt_live_paths(ssl_config.primary_domain)
        if not cert_paths_exist(paths['certificate_path'], paths['private_key_path']):
            raise SSLConfigurationError('Certificate material missing after certbot run')

        metadata = read_certificate_metadata_from_path(paths['certificate_path'])
        now = datetime.utcnow()
        ssl_config.certificate_status = 'verified'
        ssl_config.is_enabled = True
        ssl_config.last_issued_at = now
        ssl_config.last_verified_at = now
        ssl_config.expires_at = metadata.expires_at if metadata else None
        ssl_config.last_error = None
        ssl_config.updated_at = now
        db.commit()

        logger.info('Certificate issued successfully for config_id=%s', config_id)
        return {
            'status': 'success',
            'expires_at': ssl_config.expires_at.isoformat() if ssl_config.expires_at else None,
            'output': result.stdout,
        }

    except Exception as exc:
        logger.exception('Unexpected error during certificate issuance (config_id=%s)', config_id)
        try:
            db.rollback()
        except Exception:
            pass
        db = SessionLocal()
        ssl_config = _load_ssl_config(db, config_id)
        if ssl_config:
            ssl_config.certificate_status = 'error'
            ssl_config.last_error = str(exc)
            ssl_config.updated_at = datetime.utcnow()
            db.commit()
        db.close()
        return {'status': 'error', 'message': str(exc)}
    finally:
        try:
            db.close()
        except Exception:
            pass


@celery.task(name='tasks.renew_ssl_certificate')
def renew_ssl_certificate(config_id: int, force: bool = False):
    """Renew an existing Let\'s Encrypt certificate."""
    db = SessionLocal()
    try:
        ssl_config = _load_ssl_config(db, config_id)
        if not ssl_config:
            logger.error('SSL configuration %s not found for renewal', config_id)
            return {'status': 'error', 'message': 'SSL configuration not found'}

        if ssl_config.mode != 'lets_encrypt':
            return {'status': 'skipped', 'message': 'SSL mode is not lets_encrypt'}

        if not ssl_config.auto_renew and not force:
            return {'status': 'skipped', 'message': 'Auto renew disabled'}

        domains = normalize_domains(ssl_config.primary_domain, ssl_config.alternate_domains or [])
        if not domains:
            return {'status': 'error', 'message': 'No domains configured for renewal'}

        # Skip renewal if certificate is far from expiry unless forced
        now = datetime.utcnow()
        if not force and ssl_config.expires_at and ssl_config.expires_at - now > timedelta(days=45):
            logger.info('Skipping renewal; certificate still valid for >45 days (config_id=%s)', config_id)
            ssl_config.certificate_status = 'verified'
            ssl_config.updated_at = now
            db.commit()
            return {'status': 'skipped', 'message': 'Certificate not due for renewal'}

        result = run_certbot(domains, Config.SSL_CERTBOT_EMAIL, Config.SSL_STAGING, force_renewal=True)
        output = (result.stdout or '') + (result.stderr or '')

        if result.returncode != 0:
            logger.error('Certbot renewal failed (config_id=%s): %s', config_id, output)
            ssl_config.certificate_status = 'error'
            ssl_config.last_error = output[-2000:]
            ssl_config.updated_at = datetime.utcnow()
            db.commit()
            return {'status': 'error', 'message': 'Certbot renewal failed', 'output': output[-4000:]}

        paths = get_lets_encrypt_live_paths(ssl_config.primary_domain)
        if not cert_paths_exist(paths['certificate_path'], paths['private_key_path']):
            raise SSLConfigurationError('Certificate material missing after renewal')

        metadata = read_certificate_metadata_from_path(paths['certificate_path'])
        now = datetime.utcnow()
        ssl_config.certificate_status = 'verified'
        ssl_config.is_enabled = True
        ssl_config.expires_at = metadata.expires_at if metadata else None
        ssl_config.last_verified_at = now
        ssl_config.last_error = None
        ssl_config.updated_at = now
        db.commit()

        logger.info('Certificate renewed successfully (config_id=%s)', config_id)
        return {'status': 'success', 'expires_at': ssl_config.expires_at.isoformat() if ssl_config.expires_at else None}

    except Exception as exc:
        logger.exception('Unexpected error during certificate renewal (config_id=%s)', config_id)
        try:
            db.rollback()
        except Exception:
            pass
        db = SessionLocal()
        ssl_config = _load_ssl_config(db, config_id)
        if ssl_config:
            ssl_config.certificate_status = 'error'
            ssl_config.last_error = str(exc)
            ssl_config.updated_at = datetime.utcnow()
            db.commit()
        db.close()
        return {'status': 'error', 'message': str(exc)}
    finally:
        try:
            db.close()
        except Exception:
            pass


@celery.task(name='tasks.schedule_ssl_renewal')
def schedule_ssl_renewal(force: bool = False):
    """Queue a renewal if Let\'s Encrypt auto-renew is enabled."""
    db = SessionLocal()
    try:
        ssl_config = db.query(SSLConfiguration).first()
        if not ssl_config:
            return {'status': 'skipped', 'message': 'No SSL configuration'}
        if ssl_config.mode != 'lets_encrypt':
            return {'status': 'skipped', 'message': 'SSL mode is not lets_encrypt'}
        if not ssl_config.auto_renew and not force:
            return {'status': 'skipped', 'message': 'Auto renew disabled'}
        renew_ssl_certificate.delay(ssl_config.id, force)
        return {'status': 'queued'}
    finally:
        try:
            db.close()
        except Exception:
            pass


@celery.task(name='tasks.schedule_ssl_health_check')
def schedule_ssl_health_check(force_disable: bool = False):
    """Queue a HTTPS health verification if SSL is enabled."""
    db = SessionLocal()
    try:
        ssl_config = db.query(SSLConfiguration).first()
        if not ssl_config:
            return {'status': 'skipped', 'message': 'No SSL configuration'}
        if not ssl_config.is_enabled and not ssl_config.enforce_https:
            return {'status': 'skipped', 'message': 'SSL not enabled'}
        verify_ssl_health.delay(ssl_config.id, force_disable)
        return {'status': 'queued'}
    finally:
        try:
            db.close()
        except Exception:
            pass


@celery.task(name='tasks.verify_ssl_health')
def verify_ssl_health(config_id: int, force_disable: bool = False):
    """Check HTTPS endpoint availability and optionally disable enforcement on failure."""
    db = SessionLocal()
    try:
        ssl_config = _load_ssl_config(db, config_id)
        if not ssl_config:
            return {'status': 'error', 'message': 'SSL configuration not found'}

        host = ssl_config.verification_hostname or ssl_config.primary_domain
        if not host:
            return {'status': 'skipped', 'message': 'No verification host configured'}

        try:
            verify_https_endpoint(host, Config.SSL_HEALTHCHECK_PATH)
            ssl_config.last_verified_at = datetime.utcnow()
            ssl_config.last_error = None
            ssl_config.certificate_status = 'verified'
            ssl_config.updated_at = datetime.utcnow()
            db.commit()
            return {'status': 'success', 'host': host}
        except Exception as exc:
            message = str(exc)
            ssl_config.last_error = message
            ssl_config.updated_at = datetime.utcnow()
            db.commit()
            logger.error('SSL health check failed for %s: %s', host, message)

            if force_disable and ssl_config.enforce_https:
                try:
                    disable_nginx_ssl_snippet()
                    write_enforce_redirect(False)
                    write_http_redirect_snippet(False)
                    ssl_config.enforce_https = False
                    db.commit()
                except Exception as revert_exc:
                    logger.exception('Failed to disable HTTPS after health failure: %s', revert_exc)

            return {'status': 'error', 'message': message}

    finally:
        try:
            db.close()
        except Exception:
            pass
