"""
Database models for NGL application
"""
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, ForeignKey, JSON, BigInteger, Index
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base
import bcrypt

class User(Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(20), default='user', nullable=False)  # 'user' or 'admin'
    is_active = Column(Boolean, default=True, nullable=False)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    last_login = Column(DateTime(timezone=True))

    # Quota management
    storage_quota_mb = Column(Integer, default=5000)  # 5GB default
    storage_used_mb = Column(Integer, default=0)

    # Relationships
    log_files = relationship("LogFile", foreign_keys="LogFile.user_id", back_populates="user", cascade="all, delete-orphan")
    analyses = relationship("Analysis", foreign_keys="Analysis.user_id", back_populates="user", cascade="all, delete-orphan")
    parser_permissions = relationship("ParserPermission", back_populates="user", cascade="all, delete-orphan")
    sessions = relationship("Session", back_populates="user", cascade="all, delete-orphan")
    notifications = relationship("Notification", back_populates="user", cascade="all, delete-orphan")
    alert_rules = relationship("AlertRule", back_populates="user", cascade="all, delete-orphan")
    bookmarks = relationship("Bookmark", back_populates="user", cascade="all, delete-orphan")

    def set_password(self, password):
        """Hash and set password"""
        self.password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

    def check_password(self, password):
        """Verify password"""
        return bcrypt.checkpw(password.encode('utf-8'), self.password_hash.encode('utf-8'))

    def is_admin(self):
        """Check if user is admin"""
        return self.role == 'admin'


class UserInvite(Base):
    __tablename__ = 'user_invites'

    id = Column(Integer, primary_key=True)
    email = Column(String(255), nullable=False, index=True)
    username = Column(String(50), nullable=False)
    role = Column(String(20), default='user', nullable=False)
    storage_quota_mb = Column(Integer, default=5000)
    token_hash = Column(String(64), nullable=False, unique=True, index=True)
    expires_at = Column(DateTime(timezone=True), nullable=False, index=True)
    used_at = Column(DateTime(timezone=True))
    created_by = Column(Integer, ForeignKey('users.id', ondelete='SET NULL'))
    user_id = Column(Integer, ForeignKey('users.id', ondelete='SET NULL'))
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class Parser(Base):
    __tablename__ = 'parsers'

    id = Column(Integer, primary_key=True)
    parser_key = Column(String(50), unique=True, nullable=False, index=True)
    name = Column(String(100), nullable=False)
    description = Column(Text)

    # Availability controls
    is_enabled = Column(Boolean, default=True, nullable=False)
    is_available_to_users = Column(Boolean, default=True, nullable=False)
    is_admin_only = Column(Boolean, default=False, nullable=False)

    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    parser_permissions = relationship("ParserPermission", back_populates="parser", cascade="all, delete-orphan")
    analyses = relationship("Analysis", back_populates="parser")


class ParserPermission(Base):
    __tablename__ = 'parser_permissions'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    parser_id = Column(Integer, ForeignKey('parsers.id', ondelete='CASCADE'), nullable=False)
    is_allowed = Column(Boolean, default=True, nullable=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    user = relationship("User", back_populates="parser_permissions")
    parser = relationship("Parser", back_populates="parser_permissions")

    # Unique constraint
    __table_args__ = (
        Index('idx_user_parser', 'user_id', 'parser_id', unique=True),
    )


class LogFile(Base):
    __tablename__ = 'log_files'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False)

    # File metadata
    original_filename = Column(String(255), nullable=False)
    stored_filename = Column(String(255), nullable=False, unique=True)
    file_path = Column(String(512), nullable=False)
    file_size_bytes = Column(BigInteger, nullable=False)
    file_hash = Column(String(64))  # SHA256
    storage_type = Column(String(20), default='local', nullable=False)  # 'local' or 's3'

    # Lifecycle management
    retention_days = Column(Integer, default=30, nullable=False)
    expires_at = Column(DateTime(timezone=True))
    is_pinned = Column(Boolean, default=False, nullable=False)

    # Deletion tracking
    is_deleted = Column(Boolean, default=False, nullable=False, index=True)
    deleted_at = Column(DateTime(timezone=True))
    deletion_type = Column(String(20))  # 'soft' or 'hard'
    deleted_by = Column(Integer, ForeignKey('users.id', ondelete='SET NULL'))

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    user = relationship("User", foreign_keys=[user_id], back_populates="log_files")
    analyses = relationship("Analysis", back_populates="log_file", cascade="all, delete-orphan")


class Analysis(Base):
    __tablename__ = 'analyses'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    log_file_id = Column(Integer, ForeignKey('log_files.id', ondelete='CASCADE'), nullable=False)
    parser_id = Column(Integer, ForeignKey('parsers.id', ondelete='SET NULL'))

    # Analysis metadata
    parse_mode = Column(String(50), nullable=False, index=True)
    session_name = Column(String(255), nullable=False, index=True)  # User-friendly name for identification
    zendesk_case = Column(String(100), index=True)  # Optional Zendesk ticket reference
    timezone = Column(String(50))
    begin_date = Column(String(50))
    end_date = Column(String(50))

    # Drill-down tracking
    parent_analysis_id = Column(Integer, ForeignKey('analyses.id', ondelete='SET NULL'), index=True)
    is_drill_down = Column(Boolean, default=False, nullable=False, index=True)

    # Status tracking
    status = Column(String(20), default='pending', nullable=False, index=True)  # pending, running, completed, failed
    started_at = Column(DateTime(timezone=True))
    completed_at = Column(DateTime(timezone=True))
    processing_time_seconds = Column(Integer)

    # Error tracking
    error_message = Column(Text)

    # Lifecycle
    retention_days = Column(Integer, default=30, nullable=False)
    expires_at = Column(DateTime(timezone=True))
    is_deleted = Column(Boolean, default=False, nullable=False, index=True)
    deleted_at = Column(DateTime(timezone=True))

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    user = relationship("User", back_populates="analyses")
    log_file = relationship("LogFile", back_populates="analyses")
    parser = relationship("Parser", back_populates="analyses")
    results = relationship("AnalysisResult", back_populates="analysis", cascade="all, delete-orphan")
    bookmarks = relationship("Bookmark", back_populates="analysis", cascade="all, delete-orphan")

    # Parent-child relationship for drill-down analyses
    parent_analysis = relationship("Analysis", remote_side=[id], backref="child_analyses")


class AnalysisResult(Base):
    __tablename__ = 'analysis_results'

    id = Column(Integer, primary_key=True)
    analysis_id = Column(Integer, ForeignKey('analyses.id', ondelete='CASCADE'), nullable=False)

    # Result data
    raw_output = Column(Text)
    parsed_data = Column(JSON)
    result_summary = Column(JSON)  # For quick stats/overview

    # File storage (optional - for large outputs)
    result_file_path = Column(String(512))
    result_size_bytes = Column(BigInteger)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    analysis = relationship("Analysis", back_populates="results")


class RetentionPolicy(Base):
    __tablename__ = 'retention_policies'

    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    description = Column(Text)

    # Policy settings
    retention_days = Column(Integer, nullable=False)
    applies_to = Column(String(20), nullable=False)  # 'log_files', 'analyses', 'both'
    is_active = Column(Boolean, default=True, nullable=False)

    # Target criteria (JSON for flexibility)
    criteria = Column(JSON)  # e.g., {"user_role": "user", "parser_type": "known"}

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


class DeletionLog(Base):
    __tablename__ = 'deletion_log'

    id = Column(Integer, primary_key=True)

    # What was deleted
    entity_type = Column(String(50), nullable=False, index=True)  # 'log_file', 'analysis', etc.
    entity_id = Column(Integer, nullable=False)
    entity_name = Column(String(255))

    # Who and when
    deleted_by = Column(Integer, ForeignKey('users.id', ondelete='SET NULL'))
    deleted_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)
    deletion_type = Column(String(20), nullable=False)  # 'soft', 'hard', 'auto'

    # Context
    reason = Column(Text)
    context_data = Column(JSON)  # Additional context

    # Recovery
    can_recover = Column(Boolean, default=False, nullable=False)
    recovered_at = Column(DateTime(timezone=True))
    recovered_by = Column(Integer, ForeignKey('users.id', ondelete='SET NULL'))


class AuditLog(Base):
    __tablename__ = 'audit_log'

    id = Column(Integer, primary_key=True)

    # Who and when
    user_id = Column(Integer, ForeignKey('users.id', ondelete='SET NULL'), index=True)
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)

    # What action
    action = Column(String(50), nullable=False, index=True)  # 'login', 'upload', 'analyze', 'delete', etc.
    entity_type = Column(String(50), index=True)
    entity_id = Column(Integer)

    # Details
    details = Column(JSON)
    ip_address = Column(String(45))
    user_agent = Column(String(512))

    # Result
    success = Column(Boolean, default=True, nullable=False)
    error_message = Column(Text)


class Session(Base):
    __tablename__ = 'sessions'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False)

    # Session data
    token_hash = Column(String(255), unique=True, nullable=False, index=True)
    expires_at = Column(DateTime(timezone=True), nullable=False, index=True)

    # Metadata
    ip_address = Column(String(45))
    user_agent = Column(String(512))

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    last_activity = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    user = relationship("User", back_populates="sessions")


class Notification(Base):
    __tablename__ = 'notifications'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False)

    # Notification content
    title = Column(String(255), nullable=False)
    message = Column(Text, nullable=False)
    notification_type = Column(String(50), nullable=False)  # 'info', 'warning', 'error', 'success'

    # Related entity (optional)
    entity_type = Column(String(50))
    entity_id = Column(Integer)

    # Status
    is_read = Column(Boolean, default=False, nullable=False, index=True)
    read_at = Column(DateTime(timezone=True))

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)

    # Relationships
    user = relationship("User", back_populates="notifications")


class AlertRule(Base):
    __tablename__ = 'alert_rules'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False)

    # Rule definition
    name = Column(String(100), nullable=False)
    description = Column(Text)
    rule_type = Column(String(50), nullable=False)  # 'parse_failure', 'quota_exceeded', etc.

    # Conditions (JSON)
    conditions = Column(JSON, nullable=False)

    # Actions
    notify_user = Column(Boolean, default=True, nullable=False)
    notify_email = Column(Boolean, default=False, nullable=False)

    # Status
    is_active = Column(Boolean, default=True, nullable=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    user = relationship("User", back_populates="alert_rules")


class Bookmark(Base):
    __tablename__ = 'bookmarks'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    analysis_id = Column(Integer, ForeignKey('analyses.id', ondelete='CASCADE'), nullable=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)

    # Relationships
    user = relationship("User", back_populates="bookmarks")
    analysis = relationship("Analysis", back_populates="bookmarks")

    # Unique constraint: one user can't bookmark the same analysis twice
    __table_args__ = (
        Index('idx_user_analysis_bookmark', 'user_id', 'analysis_id', unique=True),
    )


class S3Configuration(Base):
    __tablename__ = 's3_configurations'

    id = Column(Integer, primary_key=True)

    # AWS Credentials (should be encrypted at application level)
    aws_access_key_id = Column(String(255), nullable=False)
    aws_secret_access_key = Column(String(255), nullable=False)

    # S3 Settings
    bucket_name = Column(String(255), nullable=False)
    region = Column(String(50), nullable=False)

    # Encryption
    server_side_encryption = Column(Boolean, default=True, nullable=False)

    # Status
    is_enabled = Column(Boolean, default=False, nullable=False)
    last_test_success = Column(Boolean)
    last_test_at = Column(DateTime(timezone=True))
    last_test_message = Column(Text)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


class SSLConfiguration(Base):
    __tablename__ = 'ssl_configurations'

    id = Column(Integer, primary_key=True)
    mode = Column(String(20), nullable=False, default='lets_encrypt')
    primary_domain = Column(String(255))
    alternate_domains = Column(JSON)
    enforce_https = Column(Boolean, nullable=False, default=False)
    is_enabled = Column(Boolean, nullable=False, default=False)
    certificate_status = Column(String(50), nullable=False, default='idle')
    last_issued_at = Column(DateTime(timezone=True))
    last_verified_at = Column(DateTime(timezone=True))
    expires_at = Column(DateTime(timezone=True))
    last_error = Column(Text)
    verification_hostname = Column(String(255))
    uploaded_certificate_path = Column(String(512))
    uploaded_private_key_path = Column(String(512))
    uploaded_chain_path = Column(String(512))
    uploaded_fingerprint = Column(String(128))
    uploaded_at = Column(DateTime(timezone=True))
    auto_renew = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    def get_all_domains(self):
        """Return a list of all domains associated with the certificate."""
        domains = []
        if self.primary_domain:
            domains.append(self.primary_domain)
        if self.alternate_domains:
            domains.extend([d for d in self.alternate_domains if d])
        return domains


class SMTPConfiguration(Base):
    __tablename__ = 'smtp_configurations'

    id = Column(Integer, primary_key=True)
    host = Column(String(255))
    port = Column(Integer, default=587)
    username = Column(String(255))
    password = Column(String(255))
    from_email = Column(String(255), default='no-reply@ngl.local')
    use_tls = Column(Boolean, default=True, nullable=False)
    is_enabled = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
