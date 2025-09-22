from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List
from .. import models, schemas, database, dependencies

router = APIRouter(prefix="/audit-logs", tags=["Audit Logs"])


@router.get("/", response_model=List[schemas.AuditLogResponse])
def get_logs(
    q: str = None,
    db: Session = Depends(database.get_db),
    current_user=Depends(dependencies.require_role("auditor")),
):
    query = db.query(models.AuditLog)
    if q:
        query = query.filter(models.AuditLog.details.ilike(f"%{q}%"))
    return query.order_by(models.AuditLog.timestamp.desc()).all()
