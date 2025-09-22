from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from .. import models, schemas, database, auth, dependencies

router = APIRouter(prefix="/superadmin", tags=["SuperAdmin"])

# ---------------- Admin Management ----------------
@router.get("/admins", response_model=List[schemas.UserResponse])
def list_admins(
    db: Session = Depends(database.get_db),
    current_user=Depends(dependencies.require_role("superadmin"))
):
    return db.query(models.User).filter(models.User.role == "admin").all()

@router.post("/admins", response_model=schemas.UserResponse, status_code=status.HTTP_201_CREATED)
def create_admin(
    user_in: schemas.UserCreate,
    db: Session = Depends(database.get_db),
    current_user=Depends(dependencies.require_role("superadmin"))
):
    existing = db.query(models.User).filter(models.User.email == user_in.email).first()
    if existing:
        raise HTTPException(status_code=409, detail="Email already registered")

    hashed = auth.get_password_hash(user_in.password)
    admin = models.User(name=user_in.name, email=user_in.email, hashed_password=hashed, role="admin")
    db.add(admin)
    db.commit()
    db.refresh(admin)

    audit = models.AuditLog(
        user_email=current_user.email,
        action="Create Admin",
        status="success",
        details=f"Created admin {admin.email}"
    )
    db.add(audit)
    db.commit()
    return admin

@router.delete("/admins/{admin_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_admin(
    admin_id: int,
    db: Session = Depends(database.get_db),
    current_user=Depends(dependencies.require_role("superadmin"))
):
    admin = db.query(models.User).filter(models.User.id == admin_id, models.User.role == "admin").first()
    if not admin:
        raise HTTPException(status_code=404, detail="Admin not found")

    db.delete(admin)
    db.commit()

    audit = models.AuditLog(
        user_email=current_user.email,
        action="Delete Admin",
        status="success",
        details=f"Deleted admin {admin.email}"
    )
    db.add(audit)
    db.commit()
    return None
