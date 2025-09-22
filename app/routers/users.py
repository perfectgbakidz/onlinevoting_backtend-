from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from .. import models, schemas, database, auth
from ..auth import get_password_hash

router = APIRouter(prefix="/users", tags=["Users"])


@router.post("/register", response_model=schemas.UserResponse, status_code=status.HTTP_201_CREATED)
def register_user(user_in: schemas.UserCreate, db: Session = Depends(database.get_db)):
    """Register a new voter"""
    # Enforce course requirement for HND
    if user_in.level and user_in.level.upper().startswith("HND") and not user_in.course:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Course is required for HND students"
        )

    # Ensure email or student_id is unique
    existing = db.query(models.User).filter(
        (models.User.email == user_in.email) | (models.User.student_id == user_in.student_id)
    ).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email or Student ID already registered")

    hashed = get_password_hash(user_in.password)
    user = models.User(
        name=user_in.name,
        email=user_in.email,
        student_id=user_in.student_id,
        level=user_in.level,
        course=user_in.course,
        hashed_password=hashed,
        role="voter"  # enforce voter role on registration
    )
    db.add(user)

    # Audit log
    audit = models.AuditLog(
        user_email=user.email,
        action="User Registration",
        status="success",
        details=f"Registered voter {user.email}"
    )
    db.add(audit)

    db.commit()
    db.refresh(user)
    return user


@router.get('/me', response_model=schemas.UserResponse)
def read_users_me(current_user: models.User = Depends(auth.get_current_user)):
    """Get current logged-in user's profile"""
    return current_user
