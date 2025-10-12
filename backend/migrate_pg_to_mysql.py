"""
PostgreSQL to MySQL Migration Script for NGL

This script exports all data from PostgreSQL and prepares it for MySQL import.
Run this BEFORE switching to MySQL.

Usage:
    python migrate_pg_to_mysql.py export    # Export PostgreSQL data
    python migrate_pg_to_mysql.py import    # Import into MySQL
    python migrate_pg_to_mysql.py verify    # Verify data integrity
"""

import sys
import json
import os
from datetime import datetime
from pathlib import Path
import hashlib

# Ensure we can import our models
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import sessionmaker
from models import (
    User, Parser, ParserPermission, LogFile, Analysis, AnalysisResult,
    RetentionPolicy, DeletionLog, AuditLog, Session as UserSession,
    Notification, AlertRule, S3Configuration, SSLConfiguration
)
from config import Config

# Migration settings
MIGRATION_DIR = Path('/app/migration_data')
MIGRATION_DIR.mkdir(exist_ok=True)

# Table order matters for foreign keys
TABLE_ORDER = [
    ('users', User),
    ('parsers', Parser),
    ('parser_permissions', ParserPermission),
    ('log_files', LogFile),
    ('analyses', Analysis),
    ('analysis_results', AnalysisResult),
    ('retention_policies', RetentionPolicy),
    ('deletion_log', DeletionLog),
    ('audit_log', AuditLog),
    ('sessions', UserSession),
    ('notifications', Notification),
    ('alert_rules', AlertRule),
    ('s3_configurations', S3Configuration),
    ('ssl_configurations', SSLConfiguration),
]


class MigrationHelper:
    def __init__(self):
        self.pg_url = Config.DATABASE_URL
        self.mysql_url = None  # Will be set from env for import

    def serialize_row(self, obj, model_class):
        """Convert SQLAlchemy object to JSON-serializable dict"""
        data = {}
        for column in inspect(model_class).columns:
            value = getattr(obj, column.name)

            # Handle datetime objects
            if isinstance(value, datetime):
                data[column.name] = value.isoformat()
            # Handle None
            elif value is None:
                data[column.name] = None
            # Handle JSON/dict
            elif isinstance(value, (dict, list)):
                data[column.name] = value
            # Everything else
            else:
                data[column.name] = value

        return data

    def export_table(self, session, table_name, model_class):
        """Export a single table to JSON"""
        print(f"  Exporting {table_name}...", end=' ')

        rows = session.query(model_class).all()
        data = [self.serialize_row(row, model_class) for row in rows]

        output_file = MIGRATION_DIR / f"{table_name}.json"
        with open(output_file, 'w') as f:
            json.dump(data, f, indent=2, default=str)

        # Calculate checksum
        checksum = hashlib.sha256(json.dumps(data, sort_keys=True).encode()).hexdigest()

        print(f"✓ {len(data)} rows (checksum: {checksum[:8]}...)")

        return {
            'table': table_name,
            'rows': len(data),
            'checksum': checksum,
            'file': str(output_file)
        }

    def export_all_data(self):
        """Export all PostgreSQL data"""
        print("\n" + "="*60)
        print("POSTGRESQL DATA EXPORT")
        print("="*60)
        print(f"Source: {self.pg_url.split('@')[1]}")  # Hide password
        print(f"Output: {MIGRATION_DIR}")
        print()

        engine = create_engine(self.pg_url)
        SessionLocal = sessionmaker(bind=engine)
        session = SessionLocal()

        manifest = {
            'exported_at': datetime.utcnow().isoformat(),
            'source_db': 'postgresql',
            'target_db': 'mysql',
            'tables': []
        }

        try:
            for table_name, model_class in TABLE_ORDER:
                table_info = self.export_table(session, table_name, model_class)
                manifest['tables'].append(table_info)

            # Save manifest
            manifest_file = MIGRATION_DIR / 'migration_manifest.json'
            with open(manifest_file, 'w') as f:
                json.dump(manifest, f, indent=2)

            print("\n" + "="*60)
            print(f"✓ Export completed successfully!")
            print(f"  Total tables: {len(manifest['tables'])}")
            print(f"  Total rows: {sum(t['rows'] for t in manifest['tables'])}")
            print(f"  Manifest: {manifest_file}")
            print("="*60 + "\n")

            return manifest

        finally:
            session.close()

    def deserialize_row(self, data):
        """Convert JSON data back to proper Python types"""
        result = {}
        for key, value in data.items():
            # Convert ISO datetime strings back to datetime objects
            if isinstance(value, str) and 'T' in value:
                try:
                    # Try parsing as datetime
                    result[key] = datetime.fromisoformat(value.replace('Z', '+00:00'))
                except:
                    # Not a datetime, keep as string
                    result[key] = value
            else:
                result[key] = value
        return result

    def import_table(self, session, table_name, model_class):
        """Import a single table from JSON"""
        print(f"  Importing {table_name}...", end=' ')

        input_file = MIGRATION_DIR / f"{table_name}.json"
        if not input_file.exists():
            print(f"⚠ File not found, skipping")
            return 0

        with open(input_file, 'r') as f:
            data = json.load(f)

        if not data:
            print(f"✓ 0 rows (empty table)")
            return 0

        # Insert rows
        inserted = 0
        for row_data in data:
            try:
                # Deserialize dates and other types
                clean_data = self.deserialize_row(row_data)

                # Create object
                obj = model_class(**clean_data)
                session.add(obj)
                inserted += 1

                # Commit in batches for performance
                if inserted % 100 == 0:
                    session.commit()

            except Exception as e:
                print(f"\n    Error on row {inserted + 1}: {e}")
                session.rollback()
                raise

        # Final commit
        session.commit()

        print(f"✓ {inserted} rows")
        return inserted

    def import_all_data(self):
        """Import all data into MySQL"""
        print("\n" + "="*60)
        print("MYSQL DATA IMPORT")
        print("="*60)

        # Get MySQL URL from environment
        self.mysql_url = os.getenv('MYSQL_DATABASE_URL')
        if not self.mysql_url:
            print("ERROR: MYSQL_DATABASE_URL environment variable not set!")
            print("Example: export MYSQL_DATABASE_URL='mysql+pymysql://user:pass@mysql:3306/ngl_db'")
            sys.exit(1)

        print(f"Target: {self.mysql_url.split('@')[1]}")  # Hide password
        print(f"Source: {MIGRATION_DIR}")
        print()

        # Load manifest
        manifest_file = MIGRATION_DIR / 'migration_manifest.json'
        if not manifest_file.exists():
            print(f"ERROR: Manifest file not found: {manifest_file}")
            print("Please run 'export' first!")
            sys.exit(1)

        with open(manifest_file, 'r') as f:
            manifest = json.load(f)

        print(f"Manifest: {manifest['exported_at']}")
        print(f"Tables: {len(manifest['tables'])}")
        print()

        # Connect to MySQL
        engine = create_engine(self.mysql_url, echo=False)
        SessionLocal = sessionmaker(bind=engine)
        session = SessionLocal()

        total_rows = 0

        try:
            # Disable foreign key checks temporarily
            session.execute(text("SET FOREIGN_KEY_CHECKS=0"))

            for table_name, model_class in TABLE_ORDER:
                rows = self.import_table(session, table_name, model_class)
                total_rows += rows

            # Re-enable foreign key checks
            session.execute(text("SET FOREIGN_KEY_CHECKS=1"))
            session.commit()

            print("\n" + "="*60)
            print(f"✓ Import completed successfully!")
            print(f"  Total tables: {len(TABLE_ORDER)}")
            print(f"  Total rows: {total_rows}")
            print("="*60 + "\n")

        except Exception as e:
            print(f"\n✗ Import failed: {e}")
            session.rollback()
            raise
        finally:
            session.close()

    def verify_migration(self):
        """Verify data integrity between PostgreSQL and MySQL"""
        print("\n" + "="*60)
        print("MIGRATION VERIFICATION")
        print("="*60)

        # Load manifest
        manifest_file = MIGRATION_DIR / 'migration_manifest.json'
        with open(manifest_file, 'r') as f:
            manifest = json.load(f)

        # Get MySQL URL
        self.mysql_url = os.getenv('MYSQL_DATABASE_URL')
        if not self.mysql_url:
            print("ERROR: MYSQL_DATABASE_URL not set!")
            sys.exit(1)

        # Connect to MySQL
        engine = create_engine(self.mysql_url)
        SessionLocal = sessionmaker(bind=engine)
        session = SessionLocal()

        all_ok = True

        try:
            for table_name, model_class in TABLE_ORDER:
                # Count rows in MySQL
                mysql_count = session.query(model_class).count()

                # Get expected count from manifest
                table_info = next((t for t in manifest['tables'] if t['table'] == table_name), None)
                if not table_info:
                    print(f"  {table_name}: ⚠ Not in manifest")
                    continue

                expected_count = table_info['rows']

                if mysql_count == expected_count:
                    print(f"  {table_name}: ✓ {mysql_count} rows")
                else:
                    print(f"  {table_name}: ✗ Expected {expected_count}, got {mysql_count}")
                    all_ok = False

            print("\n" + "="*60)
            if all_ok:
                print("✓ All tables verified successfully!")
            else:
                print("✗ Verification failed - row counts don't match")
            print("="*60 + "\n")

        finally:
            session.close()

        return all_ok


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    command = sys.argv[1].lower()
    helper = MigrationHelper()

    if command == 'export':
        helper.export_all_data()
        print("\nNext steps:")
        print("  1. Stop the application: docker-compose down")
        print("  2. Switch to MySQL in docker-compose.yml")
        print("  3. Start MySQL: docker-compose up -d mysql")
        print("  4. Create schema: docker-compose exec backend alembic upgrade head")
        print("  5. Import data: docker-compose exec backend python migrate_pg_to_mysql.py import")

    elif command == 'import':
        helper.import_all_data()
        print("\nNext steps:")
        print("  1. Verify data: docker-compose exec backend python migrate_pg_to_mysql.py verify")
        print("  2. Test the application thoroughly")
        print("  3. Keep PostgreSQL backup until confident!")

    elif command == 'verify':
        success = helper.verify_migration()
        sys.exit(0 if success else 1)

    else:
        print(f"Unknown command: {command}")
        print(__doc__)
        sys.exit(1)


if __name__ == '__main__':
    main()
