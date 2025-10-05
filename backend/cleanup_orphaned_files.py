#!/usr/bin/env python3
"""
Delete orphaned log files (files with no associated analyses)
"""
from database import SessionLocal
from models import User, LogFile, Analysis, DeletionLog
from datetime import datetime
import os

def cleanup_orphaned_files():
    db = SessionLocal()
    try:
        # Find all log files that have no associated analyses
        orphaned_files = db.query(LogFile).filter(
            ~LogFile.id.in_(
                db.query(Analysis.log_file_id).filter(Analysis.log_file_id.isnot(None))
            )
        ).all()

        print(f"Found {len(orphaned_files)} orphaned log files")

        deleted_count = 0
        total_size_freed = 0

        for log_file in orphaned_files:
            # Delete physical file
            if os.path.exists(log_file.file_path):
                try:
                    os.remove(log_file.file_path)
                    print(f"Deleted physical file: {log_file.file_path}")
                except Exception as e:
                    print(f"Warning: Failed to delete {log_file.file_path}: {e}")

            # Update user's storage quota
            file_owner = db.query(User).filter(User.id == log_file.user_id).first()
            if file_owner:
                file_size_mb = log_file.file_size_bytes / (1024 * 1024)
                file_owner.storage_used_mb = max(0, file_owner.storage_used_mb - file_size_mb)
                total_size_freed += log_file.file_size_bytes
                print(f"  User {file_owner.username}: freed {file_size_mb:.2f} MB")

            # Log deletion
            deletion_log = DeletionLog(
                entity_type='log_file',
                entity_id=log_file.id,
                entity_name=log_file.original_filename,
                deleted_by=1,  # Admin user ID
                deletion_type='hard',
                reason='Cleanup orphaned file (no associated analyses)',
                can_recover=False,
                context_data={
                    'file_path': log_file.file_path,
                    'file_size_bytes': log_file.file_size_bytes
                }
            )
            db.add(deletion_log)

            # Delete from database
            db.delete(log_file)
            deleted_count += 1

        db.commit()

        print(f"\nCleanup complete!")
        print(f"  Deleted {deleted_count} orphaned files")
        print(f"  Total storage freed: {total_size_freed / (1024 * 1024):.2f} MB")

    except Exception as e:
        print(f"Error: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == '__main__':
    cleanup_orphaned_files()
