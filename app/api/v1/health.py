from fastapi import APIRouter
from app.core.config import settings
from fastapi import Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.db.session import get_db

router=APIRouter()


@router.get("/health")
def health_check():
     return {
        "status": "ok",
        "service": settings.app_name,
        "environment": settings.environment
    }


@router.get("/health/db")
def database_health(db: Session = Depends(get_db)):
    try:
        result = db.execute(text("SELECT 1"))
        result.scalar_one()

        return {
            "status": "ok",
            "database": "connected",
        }

    except SQLAlchemyError:
        raise HTTPException(
            status_code=503,
            detail="Database connection unavailable",
        )