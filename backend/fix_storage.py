#!/usr/bin/env python3
"""
Fix storage quota by recalculating from actual log files
"""
from database import SessionLocal
from models import User, LogFile
from sqlalchemy import func

def fix_storage_quota():
    db = SessionLocal()
    try:
        # Get all users
        users = db.query(User).all()

        for user in users:
            # Calculate actual storage used from non-deleted files
            actual_storage = db.query(func.sum(LogFile.file_size_bytes)).filter(
                LogFile.user_id == user.id,
                LogFile.is_deleted == False
            ).scalar() or 0

            actual_storage_mb = actual_storage / (1024 * 1024)

            print(f"User: {user.username}")
            print(f"  Current storage_used_mb: {user.storage_used_mb}")
            print(f"  Actual storage from files: {actual_storage_mb:.2f} MB")

            # Update user's storage
            user.storage_used_mb = actual_storage_mb

        db.commit()
        print("\nStorage quotas fixed successfully!")

    except Exception as e:
        print(f"Error: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == '__main__':
    fix_storage_quota()
