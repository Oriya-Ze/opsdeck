#!/bin/bash
set -e

echo "Waiting for PostgreSQL..."
while ! python -c "
import psycopg2, os, sys
try:
    conn = psycopg2.connect(os.environ.get('DATABASE_URL', 'postgresql://opsdeck:opsdeck@postgres:5432/opsdeck'))
    conn.close()
    sys.exit(0)
except Exception:
    sys.exit(1)
" 2>/dev/null; do
  sleep 2
done

echo "Running migrations..."
alembic upgrade head

echo "Seeding database..."
python -c "
from app.core.database import SessionLocal
from app.mock.seed_data import seed_database
db = SessionLocal()
try:
    seed_database(db)
    print('Seed complete.')
finally:
    db.close()
"

echo "Starting OpsDeck API..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000
