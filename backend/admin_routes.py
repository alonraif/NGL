"""
Admin-only routes for user and parser management
"""
from flask import Blueprint, request, jsonify
from sqlalchemy import func
from database import SessionLocal
from models import (
    User,
    Parser,
    ParserPermission,
    LogFile,
    Analysis,
    DeletionLog,
    S3Configuration,
    SSLConfiguration,
)
from auth import admin_required, log_audit
from datetime import datetime
import os
import re
import time
from storage_service import StorageFactory
from config import Config
from ssl_service import (
    SSLConfigurationError,
    SSLVerificationError,
    cert_paths_exist,
    cleanup_uploaded_files,
    disable_nginx_ssl_snippet,
    ensure_directories,
    get_lets_encrypt_live_paths,
    is_valid_domain,
    normalize_domains,
    serialize_ssl_configuration,
    store_uploaded_material,
    validate_certificate_pair,
    verify_https_endpoint,
    write_enforce_redirect,
    write_http_redirect_snippet,
    write_nginx_ssl_snippet,
    read_certificate_metadata_from_path,
)
from tasks import issue_ssl_certificate, renew_ssl_certificate, verify_ssl_health

admin_bp = Blueprint('admin', __name__)


def validate_email(email):
    """Validate email format"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None


def validate_password(password):
    """Validate password strength - requires 12+ chars with uppercase, lowercase, number, and special character"""
    if len(password) < 12:
        return False, "Password must be at least 12 characters long"
    if not re.search(r'[A-Z]', password):
        return False, "Password must contain at least one uppercase letter"
    if not re.search(r'[a-z]', password):
        return False, "Password must contain at least one lowercase letter"
    if not re.search(r'[0-9]', password):
        return False, "Password must contain at least one number"
    if not re.search(r'[!@#$%^&*(),.?":{}|<>_\-+=\[\]\\\/~`]', password):
        return False, "Password must contain at least one special character (!@#$%^&* etc.)"
    return True, None


def get_or_create_ssl_config(db):
    """Return the singleton SSL configuration row, creating it if necessary."""
    ssl_config = db.query(SSLConfiguration).first()
    if not ssl_config:
        ssl_config = SSLConfiguration()
        db.add(ssl_config)
        db.commit()
        db.refresh(ssl_config)
    return ssl_config


def validate_domains(primary_domain, alternate_domains):
    """Validate domain inputs and return normalized list."""
    domains = normalize_domains(primary_domain, alternate_domains)
    for domain in domains:
        if not is_valid_domain(domain):
            raise SSLConfigurationError(f'Invalid domain: {domain}')
    return domains


@admin_bp.route('/users', methods=['GET'])
@admin_required
def list_users(current_user, db):
    """List all users (admin only)"""
    try:
        users = db.query(User).all()

        return jsonify({
            'users': [{
                'id': u.id,
                'username': u.username,
                'email': u.email,
                'role': u.role,
                'is_active': u.is_active,
                'storage_quota_mb': u.storage_quota_mb,
                'storage_used_mb': u.storage_used_mb,
                'created_at': u.created_at.isoformat(),
                'last_login': u.last_login.isoformat() if u.last_login else None
            } for u in users]
        }), 200

    except Exception as e:
        return jsonify({'error': f'Failed to list users: {str(e)}'}), 500


@admin_bp.route('/users', methods=['POST'])
@admin_required
def create_user(current_user, db):
    """Create a new user (admin only)"""
    try:
        data = request.get_json()

        # Validate input
        username = data.get('username', '').strip()
        email = data.get('email', '').strip().lower()
        password = data.get('password', '')
        role = data.get('role', 'user')  # Default role
        storage_quota_mb = data.get('storage_quota_mb', 500)  # Default 500MB

        if not username or not email or not password:
            return jsonify({'error': 'Username, email, and password are required'}), 400

        if len(username) < 3:
            return jsonify({'error': 'Username must be at least 3 characters long'}), 400

        if not validate_email(email):
            return jsonify({'error': 'Invalid email format'}), 400

        valid_password, password_error = validate_password(password)
        if not valid_password:
            return jsonify({'error': password_error}), 400

        if role not in ['user', 'admin']:
            return jsonify({'error': 'Invalid role. Must be "user" or "admin"'}), 400

        # Check if user already exists
        existing_user = db.query(User).filter(
            (User.username == username) | (User.email == email)
        ).first()

        if existing_user:
            if existing_user.username == username:
                return jsonify({'error': 'Username already exists'}), 409
            else:
                return jsonify({'error': 'Email already exists'}), 409

        # Create new user
        user = User(
            username=username,
            email=email,
            role=role,
            storage_quota_mb=storage_quota_mb
        )
        user.set_password(password)

        db.add(user)
        db.commit()
        db.refresh(user)

        # Log user creation
        log_audit(db, current_user.id, 'create_user', 'user', user.id, {
            'username': username,
            'email': email,
            'role': role,
            'created_by': current_user.username
        })

        return jsonify({
            'success': True,
            'message': 'User created successfully',
            'user': {
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'role': user.role,
                'storage_quota_mb': user.storage_quota_mb
            }
        }), 201

    except Exception as e:
        db.rollback()
        return jsonify({'error': f'Failed to create user: {str(e)}'}), 500


@admin_bp.route('/users/<int:user_id>', methods=['PUT'])
@admin_required
def update_user(user_id, current_user, db):
    """Update user (admin only)"""
    try:
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            return jsonify({'error': 'User not found'}), 404

        data = request.get_json()

        # Update allowed fields
        if 'role' in data:
            user.role = data['role']
        if 'is_active' in data:
            user.is_active = data['is_active']
        if 'storage_quota_mb' in data:
            user.storage_quota_mb = data['storage_quota_mb']

        db.commit()

        # Log the update
        log_audit(db, current_user.id, 'update_user', 'user', user_id, data)

        return jsonify({
            'success': True,
            'user': {
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'role': user.role,
                'is_active': user.is_active,
                'storage_quota_mb': user.storage_quota_mb
            }
        }), 200

    except Exception as e:
        db.rollback()
        return jsonify({'error': f'Failed to update user: {str(e)}'}), 500


@admin_bp.route('/users/<int:user_id>/reset-password', methods=['POST'])
@admin_required
def reset_user_password(user_id, current_user, db):
    """Reset user password (admin only)"""
    try:
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            return jsonify({'error': 'User not found'}), 404

        data = request.get_json()
        new_password = data.get('new_password', '')

        if not new_password:
            return jsonify({'error': 'New password is required'}), 400

        # Validate new password
        valid_password, password_error = validate_password(new_password)
        if not valid_password:
            return jsonify({'error': password_error}), 400

        # Update password
        user.set_password(new_password)
        db.commit()

        # Log password reset
        log_audit(db, current_user.id, 'reset_user_password', 'user', user_id, {
            'target_user': user.username,
            'reset_by': current_user.username
        })

        return jsonify({
            'success': True,
            'message': f'Password reset successfully for user {user.username}'
        }), 200

    except Exception as e:
        db.rollback()
        import logging
        logging.error(f'Failed to reset password for user {user_id}: {str(e)}')
        return jsonify({'error': 'An error occurred while resetting password.'}), 500


@admin_bp.route('/users/<int:user_id>', methods=['DELETE'])
@admin_required
def delete_user(user_id, current_user, db):
    """Delete user (admin only)"""
    try:
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            return jsonify({'error': 'User not found'}), 404

        # Cannot delete yourself
        if user.id == current_user.id:
            return jsonify({'error': 'Cannot delete your own account'}), 400

        # Log the deletion
        log_audit(db, current_user.id, 'delete_user', 'user', user_id, {
            'username': user.username,
            'email': user.email
        })

        # Delete user (cascades to related records)
        db.delete(user)
        db.commit()

        return jsonify({'success': True, 'message': 'User deleted successfully'}), 200

    except Exception as e:
        db.rollback()
        return jsonify({'error': f'Failed to delete user: {str(e)}'}), 500


@admin_bp.route('/parsers', methods=['GET'])
@admin_required
def list_parsers(current_user, db):
    """List all parsers with their availability settings (admin only)"""
    try:
        parsers = db.query(Parser).all()

        return jsonify({
            'parsers': [{
                'id': p.id,
                'parser_key': p.parser_key,
                'name': p.name,
                'description': p.description,
                'is_enabled': p.is_enabled,
                'is_available_to_users': p.is_available_to_users,
                'is_admin_only': p.is_admin_only,
                'created_at': p.created_at.isoformat()
            } for p in parsers]
        }), 200

    except Exception as e:
        return jsonify({'error': f'Failed to list parsers: {str(e)}'}), 500


@admin_bp.route('/parsers/<int:parser_id>', methods=['PUT'])
@admin_required
def update_parser(parser_id, current_user, db):
    """Update parser availability (admin only)"""
    try:
        parser = db.query(Parser).filter(Parser.id == parser_id).first()
        if not parser:
            return jsonify({'error': 'Parser not found'}), 404

        data = request.get_json()

        # Update allowed fields
        if 'is_enabled' in data:
            parser.is_enabled = data['is_enabled']
        if 'is_available_to_users' in data:
            parser.is_available_to_users = data['is_available_to_users']
        if 'is_admin_only' in data:
            parser.is_admin_only = data['is_admin_only']
        if 'name' in data:
            parser.name = data['name']
        if 'description' in data:
            parser.description = data['description']

        db.commit()

        # Log the update
        log_audit(db, current_user.id, 'update_parser', 'parser', parser_id, data)

        return jsonify({
            'success': True,
            'parser': {
                'id': parser.id,
                'parser_key': parser.parser_key,
                'name': parser.name,
                'description': parser.description,
                'is_enabled': parser.is_enabled,
                'is_available_to_users': parser.is_available_to_users,
                'is_admin_only': parser.is_admin_only
            }
        }), 200

    except Exception as e:
        db.rollback()
        return jsonify({'error': f'Failed to update parser: {str(e)}'}), 500


@admin_bp.route('/files/<int:file_id>/delete', methods=['DELETE'])
@admin_required
def admin_delete_file(file_id, current_user, db):
    """Admin delete a log file (soft or hard)"""
    try:
        log_file = db.query(LogFile).filter(LogFile.id == file_id).first()
        if not log_file:
            return jsonify({'error': 'File not found'}), 404

        # Get deletion type from query params
        deletion_type = request.args.get('type', 'soft')  # 'soft' or 'hard'

        if deletion_type == 'hard':
            # Hard delete - permanent
            # Delete physical file
            if os.path.exists(log_file.file_path):
                try:
                    os.remove(log_file.file_path)
                except Exception as e:
                    return jsonify({'error': f'Failed to delete physical file: {str(e)}'}), 500

            # Update user's storage quota
            file_owner = db.query(User).filter(User.id == log_file.user_id).first()
            if file_owner:
                file_size_mb = log_file.file_size_bytes / (1024 * 1024)
                file_owner.storage_used_mb = max(0, file_owner.storage_used_mb - file_size_mb)

            # Log hard deletion
            deletion_log = DeletionLog(
                entity_type='log_file',
                entity_id=log_file.id,
                entity_name=log_file.original_filename,
                deleted_by=current_user.id,
                deletion_type='hard',
                reason='Admin hard delete',
                can_recover=False,
                context_data={
                    'file_path': log_file.file_path,
                    'file_size_bytes': log_file.file_size_bytes
                }
            )
            db.add(deletion_log)

            # Delete from database
            db.delete(log_file)
            db.commit()

            # Log audit
            log_audit(db, current_user.id, 'hard_delete_file', 'log_file', file_id, {
                'filename': log_file.original_filename
            })

            return jsonify({
                'success': True,
                'message': 'File permanently deleted',
                'deletion_type': 'hard'
            }), 200

        else:
            # Soft delete - recoverable
            log_file.is_deleted = True
            log_file.deleted_at = datetime.utcnow()
            log_file.deletion_type = 'soft'
            log_file.deleted_by = current_user.id

            # Log soft deletion
            deletion_log = DeletionLog(
                entity_type='log_file',
                entity_id=log_file.id,
                entity_name=log_file.original_filename,
                deleted_by=current_user.id,
                deletion_type='soft',
                reason='Admin soft delete',
                can_recover=True
            )
            db.add(deletion_log)
            db.commit()

            # Log audit
            log_audit(db, current_user.id, 'soft_delete_file', 'log_file', file_id, {
                'filename': log_file.original_filename
            })

            return jsonify({
                'success': True,
                'message': 'File soft deleted (recoverable for 90 days)',
                'deletion_type': 'soft'
            }), 200

    except Exception as e:
        db.rollback()
        return jsonify({'error': f'Failed to delete file: {str(e)}'}), 500


@admin_bp.route('/analyses/<int:analysis_id>/delete', methods=['DELETE'])
@admin_required
def admin_delete_analysis(analysis_id, current_user, db):
    """Admin delete an analysis (soft or hard)"""
    try:
        analysis = db.query(Analysis).filter(Analysis.id == analysis_id).first()
        if not analysis:
            return jsonify({'error': 'Analysis not found'}), 404

        deletion_type = request.args.get('type', 'soft')

        if deletion_type == 'hard':
            # Get associated log file before deleting analysis
            log_file_id = analysis.log_file_id
            log_file = None
            if log_file_id:
                log_file = db.query(LogFile).filter(LogFile.id == log_file_id).first()

            # Log hard deletion
            deletion_log = DeletionLog(
                entity_type='analysis',
                entity_id=analysis.id,
                entity_name=f"Analysis {analysis.id} - {analysis.parse_mode}",
                deleted_by=current_user.id,
                deletion_type='hard',
                reason='Admin hard delete',
                can_recover=False
            )
            db.add(deletion_log)

            # Delete from database (cascade will handle results)
            db.delete(analysis)

            # Delete associated log file
            if log_file:
                # Delete physical file
                if os.path.exists(log_file.file_path):
                    try:
                        os.remove(log_file.file_path)
                    except Exception as e:
                        print(f"Warning: Failed to delete physical file {log_file.file_path}: {e}")

                # Update user's storage quota
                file_owner = db.query(User).filter(User.id == log_file.user_id).first()
                if file_owner:
                    file_size_mb = log_file.file_size_bytes / (1024 * 1024)
                    file_owner.storage_used_mb = max(0, file_owner.storage_used_mb - file_size_mb)

                # Log file deletion
                file_deletion_log = DeletionLog(
                    entity_type='log_file',
                    entity_id=log_file.id,
                    entity_name=log_file.original_filename,
                    deleted_by=current_user.id,
                    deletion_type='hard',
                    reason='Associated with hard-deleted analysis',
                    can_recover=False,
                    context_data={
                        'file_path': log_file.file_path,
                        'file_size_bytes': log_file.file_size_bytes
                    }
                )
                db.add(file_deletion_log)

                # Delete from database
                db.delete(log_file)

            db.commit()

            # Log audit
            log_audit(db, current_user.id, 'hard_delete_analysis', 'analysis', analysis_id)

            return jsonify({
                'success': True,
                'message': 'Analysis permanently deleted',
                'deletion_type': 'hard'
            }), 200

        else:
            # Soft delete
            analysis.is_deleted = True
            analysis.deleted_at = datetime.utcnow()

            # Log soft deletion
            deletion_log = DeletionLog(
                entity_type='analysis',
                entity_id=analysis.id,
                entity_name=f"Analysis {analysis.id} - {analysis.parse_mode}",
                deleted_by=current_user.id,
                deletion_type='soft',
                reason='Admin soft delete',
                can_recover=True
            )
            db.add(deletion_log)
            db.commit()

            # Log audit
            log_audit(db, current_user.id, 'soft_delete_analysis', 'analysis', analysis_id)

            return jsonify({
                'success': True,
                'message': 'Analysis soft deleted (recoverable for 90 days)',
                'deletion_type': 'soft'
            }), 200

    except Exception as e:
        db.rollback()
        return jsonify({'error': f'Failed to delete analysis: {str(e)}'}), 500


@admin_bp.route('/analyses', methods=['GET'])
@admin_required
def list_all_analyses(current_user, db):
    """List ALL analyses from all users with filtering (admin only)"""
    try:
        # Get filter parameters
        user_id = request.args.get('user_id', type=int)
        parse_mode = request.args.get('parse_mode')
        status = request.args.get('status')
        include_deleted = request.args.get('include_deleted', 'false').lower() == 'true'

        # Build query
        query = db.query(Analysis)

        # Apply filters
        if user_id:
            query = query.filter(Analysis.user_id == user_id)

        if parse_mode:
            query = query.filter(Analysis.parse_mode == parse_mode)

        if status:
            query = query.filter(Analysis.status == status)

        if not include_deleted:
            query = query.filter(Analysis.is_deleted == False)

        # Order by most recent first
        analyses = query.order_by(Analysis.created_at.desc()).all()

        return jsonify({
            'analyses': [{
                'id': a.id,
                'user_id': a.user_id,
                'username': a.user.username if a.user else None,
                'parse_mode': a.parse_mode,
                'session_name': a.session_name,
                'zendesk_case': a.zendesk_case,
                'filename': a.log_file.original_filename if a.log_file else None,
                'storage_type': a.log_file.storage_type if a.log_file else 'local',
                'status': a.status,
                'created_at': a.created_at.isoformat(),
                'completed_at': a.completed_at.isoformat() if a.completed_at else None,
                'processing_time_seconds': a.processing_time_seconds,
                'error_message': a.error_message,
                'is_deleted': a.is_deleted,
                'deleted_at': a.deleted_at.isoformat() if a.deleted_at else None
            } for a in analyses]
        }), 200

    except Exception as e:
        return jsonify({'error': f'Failed to list analyses: {str(e)}'}), 500


@admin_bp.route('/analyses/bulk-delete', methods=['POST'])
@admin_required
def bulk_delete_analyses(current_user, db):
    """Bulk delete analyses for a user or by filter (admin only)"""
    try:
        data = request.get_json()
        user_id = data.get('user_id')
        analysis_ids = data.get('analysis_ids', [])
        deletion_type = data.get('type', 'soft')  # 'soft' or 'hard'

        if not user_id and not analysis_ids:
            return jsonify({'error': 'Either user_id or analysis_ids must be provided'}), 400

        # Build query
        if analysis_ids:
            query = db.query(Analysis).filter(Analysis.id.in_(analysis_ids))
        else:
            query = db.query(Analysis).filter(Analysis.user_id == user_id)

        analyses = query.all()

        if not analyses:
            return jsonify({'error': 'No analyses found matching criteria'}), 404

        deleted_count = 0
        deleted_files = set()  # Track unique files to delete

        for analysis in analyses:
            if deletion_type == 'hard':
                # Track log file for deletion
                if analysis.log_file_id and analysis.log_file_id not in deleted_files:
                    deleted_files.add(analysis.log_file_id)

                # Log hard deletion
                deletion_log = DeletionLog(
                    entity_type='analysis',
                    entity_id=analysis.id,
                    entity_name=f"Analysis {analysis.id} - {analysis.parse_mode}",
                    deleted_by=current_user.id,
                    deletion_type='hard',
                    reason=f'Admin bulk delete for user {user_id}' if user_id else 'Admin bulk delete',
                    can_recover=False
                )
                db.add(deletion_log)

                # Delete from database
                db.delete(analysis)
            else:
                # Soft delete
                analysis.is_deleted = True
                analysis.deleted_at = datetime.utcnow()

                # Log soft deletion
                deletion_log = DeletionLog(
                    entity_type='analysis',
                    entity_id=analysis.id,
                    entity_name=f"Analysis {analysis.id} - {analysis.parse_mode}",
                    deleted_by=current_user.id,
                    deletion_type='soft',
                    reason=f'Admin bulk delete for user {user_id}' if user_id else 'Admin bulk delete',
                    can_recover=True
                )
                db.add(deletion_log)

            deleted_count += 1

        # Delete associated log files if hard delete
        if deletion_type == 'hard' and deleted_files:
            for file_id in deleted_files:
                log_file = db.query(LogFile).filter(LogFile.id == file_id).first()
                if log_file:
                    # Delete physical file
                    if os.path.exists(log_file.file_path):
                        try:
                            os.remove(log_file.file_path)
                        except Exception as e:
                            print(f"Warning: Failed to delete physical file {log_file.file_path}: {e}")

                    # Update user's storage quota
                    file_owner = db.query(User).filter(User.id == log_file.user_id).first()
                    if file_owner:
                        file_size_mb = log_file.file_size_bytes / (1024 * 1024)
                        file_owner.storage_used_mb = max(0, file_owner.storage_used_mb - file_size_mb)

                    # Log file deletion
                    deletion_log = DeletionLog(
                        entity_type='log_file',
                        entity_id=log_file.id,
                        entity_name=log_file.original_filename,
                        deleted_by=current_user.id,
                        deletion_type='hard',
                        reason='Associated with hard-deleted analyses',
                        can_recover=False,
                        context_data={
                            'file_path': log_file.file_path,
                            'file_size_bytes': log_file.file_size_bytes
                        }
                    )
                    db.add(deletion_log)

                    # Delete from database
                    db.delete(log_file)

        db.commit()

        # Log audit
        log_audit(db, current_user.id, f'bulk_{deletion_type}_delete_analyses', 'analysis', None, {
            'user_id': user_id,
            'count': deleted_count,
            'files_deleted': len(deleted_files) if deletion_type == 'hard' else 0,
            'deletion_type': deletion_type
        })

        return jsonify({
            'success': True,
            'message': f'{deleted_count} analyses {"permanently" if deletion_type == "hard" else "soft"} deleted',
            'count': deleted_count,
            'deletion_type': deletion_type
        }), 200

    except Exception as e:
        db.rollback()
        return jsonify({'error': f'Failed to bulk delete analyses: {str(e)}'}), 500


@admin_bp.route('/stats', methods=['GET'])
@admin_required
def get_system_stats(current_user, db):
    """Get system statistics (admin only)"""
    try:
        total_users = db.query(User).count()
        active_users = db.query(User).filter(User.is_active == True).count()
        total_files = db.query(LogFile).count()
        active_files = db.query(LogFile).filter(LogFile.is_deleted == False).count()
        total_analyses = db.query(Analysis).count()

        # Calculate total storage
        total_storage = db.query(LogFile).filter(LogFile.is_deleted == False).with_entities(
            func.sum(LogFile.file_size_bytes)
        ).scalar() or 0

        ssl_config = db.query(SSLConfiguration).first()
        ssl_summary = None
        if ssl_config:
            ssl_summary = {
                'mode': ssl_config.mode,
                'enforce_https': ssl_config.enforce_https,
                'certificate_status': ssl_config.certificate_status,
                'expires_at': ssl_config.expires_at.isoformat() if ssl_config.expires_at else None
            }

        return jsonify({
            'users': {
                'total': total_users,
                'active': active_users
            },
            'files': {
                'total': total_files,
                'active': active_files
            },
            'analyses': {
                'total': total_analyses
            },
            'storage': {
                'total_bytes': int(total_storage) if total_storage else 0,
                'total_mb': round(int(total_storage) / (1024 * 1024), 2) if total_storage else 0
            },
            'ssl': ssl_summary
        }), 200

    except Exception as e:
        return jsonify({'error': f'Failed to get stats: {str(e)}'}), 500


# ============================================================================
# S3 Configuration Routes
# ============================================================================

@admin_bp.route('/s3/config', methods=['GET'])
@admin_required
def get_s3_config(current_user, db):
    """Get S3 configuration (admin only) with masked credentials"""
    try:
        s3_config = db.query(S3Configuration).first()

        if not s3_config:
            return jsonify({
                'configured': False,
                'config': None
            }), 200

        # Mask credentials for security
        masked_access_key = s3_config.aws_access_key_id[:4] + '*' * (len(s3_config.aws_access_key_id) - 4) if len(s3_config.aws_access_key_id) > 4 else '****'

        return jsonify({
            'configured': True,
            'config': {
                'id': s3_config.id,
                'aws_access_key_id': masked_access_key,
                'bucket_name': s3_config.bucket_name,
                'region': s3_config.region,
                'server_side_encryption': s3_config.server_side_encryption,
                'is_enabled': s3_config.is_enabled,
                'last_test_success': s3_config.last_test_success,
                'last_test_at': s3_config.last_test_at.isoformat() if s3_config.last_test_at else None,
                'last_test_message': s3_config.last_test_message
            }
        }), 200

    except Exception as e:
        return jsonify({'error': f'Failed to get S3 config: {str(e)}'}), 500


@admin_bp.route('/s3/config', methods=['PUT'])
@admin_required
def update_s3_config(current_user, db):
    """Update S3 configuration (admin only)"""
    try:
        data = request.get_json()

        # Validate required fields
        required_fields = ['aws_access_key_id', 'aws_secret_access_key', 'bucket_name', 'region']
        for field in required_fields:
            if field not in data or not data[field].strip():
                return jsonify({'error': f'{field} is required'}), 400

        # Get or create S3 configuration
        s3_config = db.query(S3Configuration).first()

        if s3_config:
            # Update existing
            s3_config.aws_access_key_id = data['aws_access_key_id'].strip()
            s3_config.aws_secret_access_key = data['aws_secret_access_key'].strip()
            s3_config.bucket_name = data['bucket_name'].strip()
            s3_config.region = data['region'].strip()
            s3_config.server_side_encryption = data.get('server_side_encryption', True)
            s3_config.updated_at = datetime.utcnow()
        else:
            # Create new
            s3_config = S3Configuration(
                aws_access_key_id=data['aws_access_key_id'].strip(),
                aws_secret_access_key=data['aws_secret_access_key'].strip(),
                bucket_name=data['bucket_name'].strip(),
                region=data['region'].strip(),
                server_side_encryption=data.get('server_side_encryption', True),
                is_enabled=False  # Don't enable automatically
            )
            db.add(s3_config)

        db.commit()
        db.refresh(s3_config)

        # Log the update
        log_audit(db, current_user.id, 'update_s3_config', 's3_configuration', s3_config.id, {
            'bucket': s3_config.bucket_name,
            'region': s3_config.region
        })

        # Mask credentials for response
        masked_access_key = s3_config.aws_access_key_id[:4] + '*' * (len(s3_config.aws_access_key_id) - 4) if len(s3_config.aws_access_key_id) > 4 else '****'

        return jsonify({
            'success': True,
            'message': 'S3 configuration updated successfully',
            'config': {
                'id': s3_config.id,
                'aws_access_key_id': masked_access_key,
                'bucket_name': s3_config.bucket_name,
                'region': s3_config.region,
                'server_side_encryption': s3_config.server_side_encryption,
                'is_enabled': s3_config.is_enabled
            }
        }), 200

    except Exception as e:
        db.rollback()
        return jsonify({'error': f'Failed to update S3 config: {str(e)}'}), 500


@admin_bp.route('/s3/test', methods=['POST'])
@admin_required
def test_s3_connection(current_user, db):
    """Test S3 connection by creating and deleting a test file (admin only)"""
    try:
        s3_config = db.query(S3Configuration).first()

        if not s3_config:
            return jsonify({'error': 'S3 not configured'}), 400

        # Run connection test
        success, message = StorageFactory.test_s3_connection(s3_config)

        # Update test results
        s3_config.last_test_success = success
        s3_config.last_test_at = datetime.utcnow()
        s3_config.last_test_message = message
        db.commit()

        # Log the test
        log_audit(db, current_user.id, 'test_s3_connection', 's3_configuration', s3_config.id, {
            'success': success,
            'message': message
        })

        return jsonify({
            'success': success,
            'message': message,
            'tested_at': s3_config.last_test_at.isoformat()
        }), 200 if success else 500

    except Exception as e:
        return jsonify({'error': f'Failed to test S3 connection: {str(e)}'}), 500


@admin_bp.route('/s3/enable', methods=['POST'])
@admin_required
def enable_s3_storage(current_user, db):
    """Enable S3 storage (admin only)"""
    try:
        s3_config = db.query(S3Configuration).first()

        if not s3_config:
            return jsonify({'error': 'S3 not configured. Please configure S3 first.'}), 400

        # Test connection before enabling
        success, message = StorageFactory.test_s3_connection(s3_config)

        if not success:
            return jsonify({
                'error': 'Cannot enable S3: connection test failed',
                'message': message
            }), 400

        # Enable S3
        s3_config.is_enabled = True
        s3_config.last_test_success = True
        s3_config.last_test_at = datetime.utcnow()
        s3_config.last_test_message = message
        db.commit()

        # Log the action
        log_audit(db, current_user.id, 'enable_s3_storage', 's3_configuration', s3_config.id)

        return jsonify({
            'success': True,
            'message': 'S3 storage enabled successfully'
        }), 200

    except Exception as e:
        db.rollback()
        return jsonify({'error': f'Failed to enable S3 storage: {str(e)}'}), 500


@admin_bp.route('/s3/disable', methods=['POST'])
@admin_required
def disable_s3_storage(current_user, db):
    """Disable S3 storage (admin only) - falls back to local storage"""
    try:
        s3_config = db.query(S3Configuration).first()

        if not s3_config:
            return jsonify({'message': 'S3 not configured'}), 200

        # Disable S3
        s3_config.is_enabled = False
        db.commit()

        # Log the action
        log_audit(db, current_user.id, 'disable_s3_storage', 's3_configuration', s3_config.id)

        return jsonify({
            'success': True,
            'message': 'S3 storage disabled. System will use local storage.'
        }), 200

    except Exception as e:
        db.rollback()
        return jsonify({'error': f'Failed to disable S3 storage: {str(e)}'}), 500


@admin_bp.route('/s3/stats', methods=['GET'])
@admin_required
def get_s3_stats(current_user, db):
    """Get S3 vs Local storage statistics (admin only)"""
    try:
        # Count files by storage type
        s3_files = db.query(LogFile).filter(
            LogFile.storage_type == 's3',
            LogFile.is_deleted == False
        ).count()

        local_files = db.query(LogFile).filter(
            LogFile.storage_type == 'local',
            LogFile.is_deleted == False
        ).count()

        # Calculate storage used by type
        s3_storage = db.query(LogFile).filter(
            LogFile.storage_type == 's3',
            LogFile.is_deleted == False
        ).with_entities(func.sum(LogFile.file_size_bytes)).scalar() or 0

        local_storage = db.query(LogFile).filter(
            LogFile.storage_type == 'local',
            LogFile.is_deleted == False
        ).with_entities(func.sum(LogFile.file_size_bytes)).scalar() or 0

        total_storage = s3_storage + local_storage

        # Calculate percentages
        s3_percentage = (s3_storage / total_storage * 100) if total_storage > 0 else 0
        local_percentage = (local_storage / total_storage * 100) if total_storage > 0 else 0

        # Get S3 config status
        s3_config = db.query(S3Configuration).first()
        storage_mode = 's3' if (s3_config and s3_config.is_enabled) else 'local'

        return jsonify({
            'storage_mode': storage_mode,
            's3_enabled': s3_config.is_enabled if s3_config else False,
            'files': {
                's3': s3_files,
                'local': local_files,
                'total': s3_files + local_files
            },
            'storage': {
                's3': {
                    'bytes': int(s3_storage),
                    'mb': round(s3_storage / (1024 * 1024), 2),
                    'gb': round(s3_storage / (1024 * 1024 * 1024), 2),
                    'percentage': round(s3_percentage, 1)
                },
                'local': {
                    'bytes': int(local_storage),
                    'mb': round(local_storage / (1024 * 1024), 2),
                    'gb': round(local_storage / (1024 * 1024 * 1024), 2),
                    'percentage': round(local_percentage, 1)
                },
                'total': {
                    'bytes': int(total_storage),
                    'mb': round(total_storage / (1024 * 1024), 2),
                    'gb': round(total_storage / (1024 * 1024 * 1024), 2)
                }
            }
        }), 200

    except Exception as e:
        return jsonify({'error': f'Failed to get S3 stats: {str(e)}'}), 500


# ============================================================================
# SSL Configuration Routes
# ============================================================================


@admin_bp.route('/ssl', methods=['GET'])
@admin_required
def get_ssl_configuration(current_user, db):
    """Return current SSL configuration."""
    try:
        ensure_directories()
        ssl_config = get_or_create_ssl_config(db)
        return jsonify({'ssl': serialize_ssl_configuration(ssl_config)}), 200
    except Exception as exc:
        return jsonify({'error': f'Failed to load SSL configuration: {str(exc)}'}), 500


@admin_bp.route('/ssl/settings', methods=['POST'])
@admin_required
def update_ssl_settings(current_user, db):
    """Update SSL mode and domain settings."""
    data = request.get_json() or {}
    mode = data.get('mode', 'lets_encrypt')

    if mode not in ('lets_encrypt', 'uploaded'):
        return jsonify({'error': 'mode must be "lets_encrypt" or "uploaded"'}), 400

    primary_domain = (data.get('primary_domain') or '').strip().lower() or None
    alternate_domains = data.get('alternate_domains', []) or []
    if not isinstance(alternate_domains, list):
        return jsonify({'error': 'alternate_domains must be a list'}), 400

    verification_hostname = (data.get('verification_hostname') or '').strip().lower() or None
    auto_renew = bool(data.get('auto_renew', True))

    try:
        domains = []
        if primary_domain or alternate_domains:
            domains = validate_domains(primary_domain, alternate_domains)

        if mode == 'lets_encrypt' and not domains:
            return jsonify({'error': 'Primary domain is required for Let\'s Encrypt mode'}), 400

        if verification_hostname and not is_valid_domain(verification_hostname):
            raise SSLConfigurationError(f'Invalid verification hostname: {verification_hostname}')

        ssl_config = get_or_create_ssl_config(db)

        if domains:
            ssl_config.primary_domain = domains[0]
            ssl_config.alternate_domains = domains[1:]
        else:
            ssl_config.primary_domain = None
            ssl_config.alternate_domains = []

        ssl_config.mode = mode
        ssl_config.auto_renew = auto_renew
        ssl_config.verification_hostname = verification_hostname or ssl_config.primary_domain

        if mode == 'lets_encrypt' and ssl_config.certificate_status not in ('verified', 'pending_issue', 'renewing'):
            ssl_config.certificate_status = 'idle'

        ssl_config.updated_at = datetime.utcnow()
        db.commit()

        log_audit(db, current_user.id, 'update_ssl_settings', 'ssl_configuration', ssl_config.id, {
            'mode': ssl_config.mode,
            'primary_domain': ssl_config.primary_domain,
            'alternate_domains': ssl_config.alternate_domains,
            'auto_renew': ssl_config.auto_renew
        })

        return jsonify({'success': True, 'ssl': serialize_ssl_configuration(ssl_config)}), 200

    except SSLConfigurationError as exc:
        db.rollback()
        return jsonify({'error': str(exc)}), 400
    except Exception as exc:
        db.rollback()
        return jsonify({'error': f'Failed to update SSL settings: {str(exc)}'}), 500


def _read_uploaded_text(file_storage, label):
    try:
        content = file_storage.read()
        if isinstance(content, bytes):
            return content.decode('utf-8')
        return str(content)
    except Exception as exc:
        raise SSLConfigurationError(f'Failed to read {label}: {exc}')


@admin_bp.route('/ssl/upload', methods=['POST'])
@admin_required
def upload_ssl_certificate(current_user, db):
    """Upload custom certificate material for HTTPS."""
    data = None
    certificate_pem = None
    private_key_pem = None

    if request.content_type and request.content_type.startswith('multipart/form-data'):
        cert_file = request.files.get('certificate_file')
        key_file = request.files.get('private_key_file')

        if not cert_file or not key_file:
            return jsonify({'error': 'Certificate and private key files are required'}), 400

        certificate_pem = _read_uploaded_text(cert_file, 'certificate file')
        private_key_pem = _read_uploaded_text(key_file, 'private key file')
    else:
        data = request.get_json() or {}
        certificate_pem = data.get('certificate_pem')
        private_key_pem = data.get('private_key_pem')

    if not certificate_pem or not private_key_pem:
        return jsonify({'error': 'Certificate and private key content are required'}), 400

    try:
        metadata = validate_certificate_pair(certificate_pem, private_key_pem)
        new_paths = store_uploaded_material(certificate_pem, private_key_pem)
        ssl_config = get_or_create_ssl_config(db)

        existing_paths = {
            'certificate_path': ssl_config.uploaded_certificate_path,
            'private_key_path': ssl_config.uploaded_private_key_path,
            'chain_path': ssl_config.uploaded_chain_path,
        }

        ssl_config.mode = 'uploaded'
        ssl_config.is_enabled = True
        ssl_config.certificate_status = 'verified'
        ssl_config.uploaded_certificate_path = new_paths['certificate_path']
        ssl_config.uploaded_private_key_path = new_paths['private_key_path']
        ssl_config.uploaded_chain_path = new_paths.get('chain_path')
        ssl_config.uploaded_fingerprint = metadata.fingerprint_sha256
        now = datetime.utcnow()
        ssl_config.uploaded_at = now
        ssl_config.last_verified_at = now
        ssl_config.last_issued_at = now
        ssl_config.expires_at = metadata.expires_at
        ssl_config.last_error = None
        ssl_config.is_enabled = True
        ssl_config.updated_at = now

        if not ssl_config.primary_domain:
            ssl_config.primary_domain = ssl_config.verification_hostname or None

        db.commit()

        # Clean up previous uploaded files after successful commit
        cleanup_uploaded_files(existing_paths)

        log_audit(db, current_user.id, 'upload_ssl_certificate', 'ssl_configuration', ssl_config.id, {
            'mode': 'uploaded',
            'fingerprint_sha256': ssl_config.uploaded_fingerprint,
            'expires_at': ssl_config.expires_at.isoformat() if ssl_config.expires_at else None
        })

        return jsonify({'success': True, 'ssl': serialize_ssl_configuration(ssl_config)}), 200

    except SSLConfigurationError as exc:
        if 'new_paths' in locals():
            cleanup_uploaded_files(new_paths)
        return jsonify({'error': str(exc)}), 400
    except Exception as exc:
        db.rollback()
        cleanup_uploaded_files(new_paths if 'new_paths' in locals() else {})
        return jsonify({'error': f'Failed to store uploaded certificate: {str(exc)}'}), 500


@admin_bp.route('/ssl/issue', methods=['POST'])
@admin_required
def issue_lets_encrypt_certificate(current_user, db):
    """Trigger Let\'s Encrypt certificate issuance via Celery."""
    data = request.get_json() or {}
    staging = bool(data.get('staging', Config.SSL_STAGING))

    try:
        ssl_config = get_or_create_ssl_config(db)

        if ssl_config.mode != 'lets_encrypt':
            return jsonify({'error': 'System is not in Let\'s Encrypt mode'}), 400

        if not ssl_config.primary_domain:
            return jsonify({'error': 'Primary domain must be configured before issuing a certificate'}), 400

        domains = validate_domains(ssl_config.primary_domain, ssl_config.alternate_domains or [])

        ssl_config.certificate_status = 'pending_issue'
        ssl_config.last_error = None
        ssl_config.updated_at = datetime.utcnow()
        db.commit()

        issue_ssl_certificate.delay(ssl_config.id, staging)

        log_audit(db, current_user.id, 'issue_ssl_certificate', 'ssl_configuration', ssl_config.id, {
            'domains': domains,
            'staging': staging
        })

        return jsonify({'success': True, 'message': 'Certificate issuance started', 'ssl': serialize_ssl_configuration(ssl_config)}), 202

    except SSLConfigurationError as exc:
        db.rollback()
        return jsonify({'error': str(exc)}), 400
    except Exception as exc:
        db.rollback()
        return jsonify({'error': f'Failed to trigger certificate issuance: {str(exc)}'}), 500


@admin_bp.route('/ssl/renew', methods=['POST'])
@admin_required
def renew_ssl_certificate_now(current_user, db):
    """Trigger a renewal task manually."""
    data = request.get_json() or {}
    force = bool(data.get('force', False))

    try:
        ssl_config = get_or_create_ssl_config(db)
        if ssl_config.mode != 'lets_encrypt':
            return jsonify({'error': 'Manual renewal is only available for Let\'s Encrypt mode'}), 400

        if ssl_config.certificate_status not in ('verified', 'error', 'idle'):
            return jsonify({'error': f'Cannot renew while status is {ssl_config.certificate_status}'}), 400

        ssl_config.certificate_status = 'renewing'
        ssl_config.updated_at = datetime.utcnow()
        db.commit()

        renew_ssl_certificate.delay(ssl_config.id, force)

        log_audit(db, current_user.id, 'renew_ssl_certificate', 'ssl_configuration', ssl_config.id, {
            'force': force
        })

        return jsonify({'success': True, 'message': 'Renewal started', 'ssl': serialize_ssl_configuration(ssl_config)}), 202

    except Exception as exc:
        db.rollback()
        return jsonify({'error': f'Failed to trigger renewal: {str(exc)}'}), 500


@admin_bp.route('/ssl/enforce', methods=['POST'])
@admin_required
def toggle_ssl_enforcement(current_user, db):
    """Enable or disable HTTPS enforcement by updating nginx runtime files."""
    data = request.get_json() or {}
    enforce = data.get('enforce')
    skip_verification = bool(data.get('skip_verification', False))
    verification_host_override = (data.get('verification_host') or '').strip().lower() or None

    if enforce is None:
        return jsonify({'error': 'enforce flag is required'}), 400

    try:
        ensure_directories()
        ssl_config = get_or_create_ssl_config(db)

        verification_host = (
            verification_host_override
            or ssl_config.verification_hostname
            or Config.SSL_VERIFICATION_HOST
            or ssl_config.primary_domain
        )

        if enforce:
            if ssl_config.mode == 'lets_encrypt':
                if not ssl_config.primary_domain:
                    return jsonify({'error': 'Configure a primary domain before enabling HTTPS'}), 400
                paths = get_lets_encrypt_live_paths(ssl_config.primary_domain)
            else:
                paths = {
                    'certificate_path': ssl_config.uploaded_certificate_path,
                    'private_key_path': ssl_config.uploaded_private_key_path,
                }

            cert_path = paths.get('certificate_path')
            key_path = paths.get('private_key_path')

            if not cert_paths_exist(cert_path, key_path):
                return jsonify({'error': 'Certificate files not found. Issue or upload a certificate before enforcing HTTPS.'}), 400

            write_nginx_ssl_snippet(ssl_config.mode, cert_path, key_path)
            write_http_redirect_snippet(True)

            verification_error = None
            if verification_host and not skip_verification:
                for attempt in range(3):
                    try:
                        verify_https_endpoint(verification_host, Config.SSL_HEALTHCHECK_PATH)
                        verification_error = None
                        break
                    except SSLVerificationError as exc:
                        verification_error = str(exc)
                        time.sleep(2)

            if verification_error:
                disable_nginx_ssl_snippet()
                write_http_redirect_snippet(False)
                ssl_config.last_error = verification_error
                ssl_config.updated_at = datetime.utcnow()
                db.commit()
                return jsonify({'error': verification_error}), 502

            if ssl_config.mode == 'lets_encrypt':
                cert_metadata = read_certificate_metadata_from_path(cert_path)
                if cert_metadata:
                    ssl_config.expires_at = cert_metadata.expires_at

            ssl_config.enforce_https = True
            ssl_config.is_enabled = True
            ssl_config.last_verified_at = datetime.utcnow()
            ssl_config.verification_hostname = verification_host
            ssl_config.last_error = None
            write_enforce_redirect(True)
            write_http_redirect_snippet(True)

        else:
            write_http_redirect_snippet(False)

            if Config.SSL_ALLOW_OPTIONAL_HTTPS:
                if ssl_config.mode == 'lets_encrypt':
                    if not ssl_config.primary_domain:
                        return jsonify({'error': 'Configure a primary domain before enabling HTTPS access'}), 400
                    paths = get_lets_encrypt_live_paths(ssl_config.primary_domain)
                else:
                    paths = {
                        'certificate_path': ssl_config.uploaded_certificate_path,
                        'private_key_path': ssl_config.uploaded_private_key_path,
                    }

                cert_path = paths.get('certificate_path')
                key_path = paths.get('private_key_path')

                if not cert_paths_exist(cert_path, key_path):
                    return jsonify({'error': 'Certificate files not found. Issue or upload a certificate before enabling HTTPS access.'}), 400

                write_nginx_ssl_snippet(ssl_config.mode, cert_path, key_path)
                ssl_config.is_enabled = True
            else:
                disable_nginx_ssl_snippet()
                try:
                    verify_ssl_health.delay(ssl_config.id, False)
                except Exception:
                    pass

            ssl_config.enforce_https = False
            write_enforce_redirect(False)

        ssl_config.updated_at = datetime.utcnow()
        db.commit()

        log_audit(db, current_user.id, 'toggle_ssl_enforcement', 'ssl_configuration', ssl_config.id, {
            'enforce': bool(enforce),
            'verification_host': verification_host,
            'skip_verification': skip_verification
        })

        return jsonify({'success': True, 'ssl': serialize_ssl_configuration(ssl_config)}), 200

    except SSLConfigurationError as exc:
        db.rollback()
        return jsonify({'error': str(exc)}), 500
    except Exception as exc:
        db.rollback()
        return jsonify({'error': f'Failed to update HTTPS enforcement: {str(exc)}'}), 500


@admin_bp.route('/ssl/health-check', methods=['POST'])
@admin_required
def trigger_ssl_health_check(current_user, db):
    """Queue a health check job to validate HTTPS serving."""
    data = request.get_json() or {}
    force = bool(data.get('force', False))

    try:
        ssl_config = get_or_create_ssl_config(db)
        verify_ssl_health.delay(ssl_config.id, force)

        log_audit(db, current_user.id, 'trigger_ssl_health_check', 'ssl_configuration', ssl_config.id, {
            'force': force
        })

        return jsonify({'success': True, 'message': 'SSL health check scheduled'}), 202

    except Exception as exc:
        return jsonify({'error': f'Failed to queue SSL health check: {str(exc)}'}), 500
