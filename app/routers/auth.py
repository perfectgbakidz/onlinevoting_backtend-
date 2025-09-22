# app/routers/auth.py
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from .. import auth as auth_utils, database, schemas, models

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post("/token", response_model=schemas.Token)
def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(database.get_db),
):
    """
    Login user with email OR student_id.
    Accepts form-data with `username` (email or student_id) and `password`.
    """

    # Authenticate user
    user = auth_utils.authenticate_user(db, form_data.username, form_data.password)
    if not user:
        # Log failed attempt
        log = models.AuditLog(
            user_email=form_data.username,
            action="Login",
            status="failed",
            details="Invalid email/student_id or password",
        )
        db.add(log)
        db.commit()

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email/student_id or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Create JWT token
    access_token = auth_utils.create_access_token(
        subject=user.email,  # always use email in token
        role=str(user.role),
        user_id=user.id,
    )

    # Log successful login
    log = models.AuditLog(
        user_email=user.email,
        action="Login",
        status="success",
        details=f"User {user.email} logged in successfully",
    )
    db.add(log)
    db.commit()

    return schemas.Token(
        access_token=access_token,
        token_type="bearer",
        user=schemas.UserResponse.model_validate(user),
    )
