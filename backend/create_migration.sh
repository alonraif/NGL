#!/bin/bash
# Create initial database migration

cd /app

# Wait for postgres to be ready
echo "Waiting for PostgreSQL..."
until PGPASSWORD=ngl_password psql -h postgres -U ngl_user -d ngl_db -c '\q' 2>/dev/null; do
  sleep 1
done

echo "PostgreSQL is ready!"

# Create initial migration
echo "Creating initial migration..."
alembic revision --autogenerate -m "Initial migration"

# Apply migration
echo "Applying migration..."
alembic upgrade head

echo "Migration complete!"
