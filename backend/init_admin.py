#!/usr/bin/env python3
"""
Initialize default admin user
Run this once after database setup
"""
from database import SessionLocal, init_db
from models import User

def create_admin():
    """Create default admin user"""
    db = SessionLocal()
    try:
        # Check if admin already exists
        existing_admin = db.query(User).filter(User.username == 'admin').first()
        if existing_admin:
            print("Admin user already exists")
            return

        # Create admin user
        admin = User(
            username='admin',
            email='admin@ngl.local',
            role='admin',
            is_active=True,
            storage_quota_mb=100000  # 100GB for admin
        )
        admin.set_password('Admin123!')  # Change this password after first login!

        db.add(admin)
        db.commit()

        print("✓ Admin user created successfully!")
        print("  Username: admin")
        print("  Password: Admin123!")
        print("  ⚠️  Please change this password after first login!")

    except Exception as e:
        db.rollback()
        print(f"Error creating admin user: {e}")
    finally:
        db.close()


if __name__ == '__main__':
    print("Initializing database...")
    init_db()
    print("Creating admin user...")
    create_admin()
