"""
Admin-only routes for user and parser management
"""
from flask import Blueprint, request, jsonify
from sqlalchemy import func
from database import SessionLocal
from models import User, Parser, ParserPermission, LogFile, Analysis, DeletionLog
from auth import admin_required, log_audit
from datetime import datetime
import os

admin_bp = Blueprint('admin', __name__)


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
            }
        }), 200

    except Exception as e:
        return jsonify({'error': f'Failed to get stats: {str(e)}'}), 500
