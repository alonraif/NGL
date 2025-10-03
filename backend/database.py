"""
Database configuration and session management
"""
import os
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

DATABASE_URL = os.getenv('DATABASE_URL', 'postgresql://ngl_user:ngl_password@localhost:5432/ngl_db')

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    """Dependency for database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db():
    """Initialize database tables"""
    from models import User, Parser, ParserPermission, LogFile, Analysis, AnalysisResult
    from models import RetentionPolicy, DeletionLog, AuditLog, Session, Notification, AlertRule
    Base.metadata.create_all(bind=engine)
