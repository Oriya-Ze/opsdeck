from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db

router = APIRouter(tags=["System"])


@router.get("/health")
def health():
    return {"status": "healthy", "service": settings.APP_NAME}


@router.get("/ready")
def ready(db: Session = Depends(get_db)):
    try:
        db.execute(text("SELECT 1"))
        return {"status": "ready", "database": "connected"}
    except Exception as e:
        return {"status": "not_ready", "database": str(e)}


@router.get("/version")
def version():
    return {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "description": "HomeLab management platform for DevOps users",
    }
