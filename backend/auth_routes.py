"""
Authentication routes
"""
from flask import Blueprint, request, jsonify
from database import SessionLocal
from models import User, Session as UserSession
from auth import create_access_token, token_required, log_audit, hash_token, admin_required
from datetime import datetime, timedelta
import re
from rate_limiter import limiter

auth_bp = Blueprint('auth', __name__)


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


@auth_bp.route('/register', methods=['POST'])
def register():
    """Public registration disabled - only admins can create users"""
    return jsonify({
        'error': 'Public registration is disabled. Please contact an administrator to create an account.'
    }), 403


@auth_bp.route('/login', methods=['POST'])
@limiter.limit("5 per minute")
def login():
    """User login"""
    db = SessionLocal()
    username = None  # Initialize to avoid UnboundLocalError
    try:
        data = request.get_json()

        username = data.get('username', '').strip()
        password = data.get('password', '')

        if not username or not password:
            return jsonify({'error': 'Username and password are required'}), 400

        # Find user
        user = db.query(User).filter(User.username == username).first()

        if not user or not user.check_password(password):
            log_audit(db, None, 'login', success=False, error_message='Invalid credentials')
            return jsonify({'error': 'Invalid username or password'}), 401

        if not user.is_active:
            log_audit(db, user.id, 'login', success=False, error_message='Account inactive')
            return jsonify({'error': 'Account is inactive'}), 403

        # Create access token
        access_token = create_access_token(user.id, user.username, user.role)

        # Update last login
        user.last_login = datetime.utcnow()

        # Create session record
        session = UserSession(
            user_id=user.id,
            token_hash=hash_token(access_token),
            expires_at=datetime.utcnow() + timedelta(hours=24),
            ip_address=request.remote_addr,
            user_agent=request.headers.get('User-Agent')
        )
        db.add(session)

        db.commit()

        # Log successful login
        log_audit(db, user.id, 'login', 'user', user.id)

        return jsonify({
            'success': True,
            'access_token': access_token,
            'user': {
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'role': user.role,
                'storage_quota_mb': user.storage_quota_mb,
                'storage_used_mb': user.storage_used_mb
            }
        }), 200

    except Exception as e:
        db.rollback()
        # Log detailed error server-side but return generic message to user
        import logging
        logging.error(f'Login error for user {username}: {str(e)}')
        return jsonify({'error': 'An error occurred during login. Please try again.'}), 500
    finally:
        db.close()


@auth_bp.route('/me', methods=['GET'])
@token_required
def get_current_user_info(current_user, db):
    """Get current user information"""
    return jsonify({
        'id': current_user.id,
        'username': current_user.username,
        'email': current_user.email,
        'role': current_user.role,
        'storage_quota_mb': current_user.storage_quota_mb,
        'storage_used_mb': current_user.storage_used_mb,
        'created_at': current_user.created_at.isoformat(),
        'last_login': current_user.last_login.isoformat() if current_user.last_login else None
    }), 200


@auth_bp.route('/logout', methods=['POST'])
@token_required
def logout(current_user, db):
    """User logout"""
    try:
        # Get token from header
        auth_header = request.headers.get('Authorization', '')
        token = auth_header.split(' ')[1] if ' ' in auth_header else None

        if token:
            # Delete session
            token_hash_value = hash_token(token)
            session = db.query(UserSession).filter(UserSession.token_hash == token_hash_value).first()
            if session:
                db.delete(session)
                db.commit()

        # Log logout
        log_audit(db, current_user.id, 'logout', 'user', current_user.id)

        return jsonify({'success': True, 'message': 'Logged out successfully'}), 200

    except Exception as e:
        db.rollback()
        import logging
        logging.error(f'Logout error for user {current_user.id}: {str(e)}')
        return jsonify({'error': 'An error occurred during logout.'}), 500


@auth_bp.route('/change-password', methods=['POST'])
@token_required
def change_password(current_user, db):
    """Change user password"""
    try:
        data = request.get_json()

        current_password = data.get('current_password', '')
        new_password = data.get('new_password', '')

        if not current_password or not new_password:
            return jsonify({'error': 'Current and new password are required'}), 400

        # Verify current password
        if not current_user.check_password(current_password):
            return jsonify({'error': 'Current password is incorrect'}), 401

        # Validate new password
        valid_password, password_error = validate_password(new_password)
        if not valid_password:
            return jsonify({'error': password_error}), 400

        # Update password
        current_user.set_password(new_password)
        db.commit()

        # Log password change
        log_audit(db, current_user.id, 'change_password', 'user', current_user.id)

        return jsonify({'success': True, 'message': 'Password changed successfully'}), 200

    except Exception as e:
        db.rollback()
        import logging
        logging.error(f'Password change error for user {current_user.id}: {str(e)}')
        return jsonify({'error': 'An error occurred while changing password.'}), 500
