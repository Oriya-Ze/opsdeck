# OpsDeck Backend

FastAPI backend for the OpsDeck HomeLab management platform.

## Local Development

```bash
pip install -r requirements.txt
export DATABASE_URL=postgresql://opsdeck:opsdeck@localhost:5432/opsdeck
alembic upgrade head
python -c "from app.core.database import SessionLocal; from app.mock.seed_data import seed_database; seed_database(SessionLocal())"
uvicorn app.main:app --reload --port 8000
```

API docs: http://localhost:8000/docs
