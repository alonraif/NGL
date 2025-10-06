"""
Authentication utilities and middleware
"""
import jwt
import os
from datetime import datetime, timedelta
from functools import wraps
from flask import request, jsonify
from database import SessionLocal
from models import User, Session as UserSession, AuditLog
import hashlib


JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY', 'your-secret-key-change-in-production')
JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=24)


def create_access_token(user_id, username, role):
    """Create JWT access token"""
    payload = {
        'user_id': user_id,
        'username': username,
        'role': role,
        'exp': datetime.utcnow() + JWT_ACCESS_TOKEN_EXPIRES,
        'iat': datetime.utcnow()
    }
    return jwt.encode(payload, JWT_SECRET_KEY, algorithm='HS256')


def decode_token(token):
    """Decode and validate JWT token"""
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=['HS256'])
        return payload
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None


def get_current_user(token):
    """Get user from token"""
    payload = decode_token(token)
    if not payload:
        return None

    db = SessionLocal()
    try:
        user = db.query(User).filter(User.id == payload['user_id'], User.is_active == True).first()
        return user
    finally:
        db.close()


def token_required(f):
    """Decorator to require authentication"""
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None

        # Get token from Authorization header
        if 'Authorization' in request.headers:
            auth_header = request.headers['Authorization']
            try:
                token = auth_header.split(' ')[1]  # Bearer <token>
            except IndexError:
                return jsonify({'error': 'Invalid token format'}), 401

        if not token:
            return jsonify({'error': 'Authentication token is missing'}), 401

        # Decode token
        payload = decode_token(token)
        if not payload:
            return jsonify({'error': 'Invalid or expired token'}), 401

        # Get user
        db = SessionLocal()
        try:
            user = db.query(User).filter(User.id == payload['user_id'], User.is_active == True).first()
            if not user:
                return jsonify({'error': 'User not found or inactive'}), 401

            # Validate session exists and is not expired
            token_hash_value = hash_token(token)
            session = db.query(UserSession).filter(
                UserSession.token_hash == token_hash_value,
                UserSession.expires_at > datetime.utcnow()
            ).first()

            if not session:
                return jsonify({'error': 'Session expired or invalidated'}), 401

            # Add user to kwargs
            kwargs['current_user'] = user
            kwargs['db'] = db

            return f(*args, **kwargs)
        finally:
            db.close()

    return decorated


def admin_required(f):
    """Decorator to require admin role"""
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None

        # Get token from Authorization header
        if 'Authorization' in request.headers:
            auth_header = request.headers['Authorization']
            try:
                token = auth_header.split(' ')[1]
            except IndexError:
                return jsonify({'error': 'Invalid token format'}), 401

        if not token:
            return jsonify({'error': 'Authentication token is missing'}), 401

        # Decode token
        payload = decode_token(token)
        if not payload:
            return jsonify({'error': 'Invalid or expired token'}), 401

        # Check role
        if payload.get('role') != 'admin':
            return jsonify({'error': 'Admin privileges required'}), 403

        # Get user
        db = SessionLocal()
        try:
            user = db.query(User).filter(User.id == payload['user_id'], User.is_active == True).first()
            if not user or not user.is_admin():
                return jsonify({'error': 'Admin privileges required'}), 403

            # Validate session exists and is not expired
            token_hash_value = hash_token(token)
            session = db.query(UserSession).filter(
                UserSession.token_hash == token_hash_value,
                UserSession.expires_at > datetime.utcnow()
            ).first()

            if not session:
                return jsonify({'error': 'Session expired or invalidated'}), 401

            # Add user to kwargs
            kwargs['current_user'] = user
            kwargs['db'] = db

            return f(*args, **kwargs)
        finally:
            db.close()

    return decorated


def log_audit(db, user_id, action, entity_type=None, entity_id=None, details=None, success=True, error_message=None):
    """Log an audit entry"""
    audit_log = AuditLog(
        user_id=user_id,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        details=details,
        ip_address=request.remote_addr if request else None,
        user_agent=request.headers.get('User-Agent') if request else None,
        success=success,
        error_message=error_message
    )
    db.add(audit_log)
    db.commit()


def hash_token(token):
    """Hash token for storage"""
    return hashlib.sha256(token.encode()).hexdigest()
