from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session
from . import database, auth, schemas
from .models import UserRole


# Proper DB session dependency
def get_db():
    db = database.get_db()
    try:
        yield from db
    finally:
        pass  # SQLAlchemy session is closed in database.get_db()


# Extract current user from JWT (returns Pydantic UserResponse)
def get_current_user(
    db: Session = Depends(get_db),
    token: str = Depends(auth.oauth2_scheme),
) -> schemas.UserResponse:
    return auth.get_current_user(token=token, db=db)


# Role-based access with multiple roles + superadmin override
def require_role(*roles: str):
    def inner(user: schemas.UserResponse = Depends(get_current_user)) -> schemas.UserResponse:
        # Always allow superadmin
        if user.role == UserRole.superadmin.value:
            return user

        # Check allowed roles
        if user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"One of these roles is required: {roles}"
            )
        return user
    return inner


# Placeholder for disabling inactive accounts
def get_current_active_user(
    user: schemas.UserResponse = Depends(get_current_user),
) -> schemas.UserResponse:
    return user
