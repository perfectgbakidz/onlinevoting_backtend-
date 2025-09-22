# app/auth.py
from datetime import datetime, timedelta, timezone
from typing import Optional
from jose import jwt, JWTError, ExpiredSignatureError
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from . import models, database, config, schemas

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# OAuth2 bearer token scheme (used in login)
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/token")


# --- Password utilities ---
def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain password against its bcrypt hash"""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Hash a password for storing in the database"""
    return pwd_context.hash(password)


# --- JWT utilities ---
def create_access_token(
    subject: str,
    role: str,
    expires_delta: Optional[timedelta] = None,
    user_id: Optional[int] = None,
) -> str:
    """Generate a JWT access token"""
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=config.settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode = {
        "sub": str(subject),     # usually the user's email
        "role": str(role),
        "user_id": user_id,
        "iat": datetime.now(timezone.utc),
        "exp": expire,
    }
    return jwt.encode(
        to_encode,
        config.settings.SECRET_KEY,
        algorithm=config.settings.ALGORITHM,
    )


def decode_token(token: str):
    """Decode and validate a JWT token"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        return jwt.decode(
            token,
            config.settings.SECRET_KEY,
            algorithms=[config.settings.ALGORITHM],
        )
    except ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
        )
    except JWTError:
        raise credentials_exception


# --- User authentication ---
def authenticate_user(db: Session, identifier: str, password: str):
    """
    Authenticate user by email OR student_id (matric number).
    """
    user = (
        db.query(models.User)
        .filter(
            (models.User.email == identifier) | (models.User.student_id == identifier)
        )
        .first()
    )
    if not user:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    return user


# --- Get current user from token ---
def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(database.get_db),
) -> schemas.UserResponse:
    """Get the current logged-in user from their JWT token"""
    payload = decode_token(token)
    email = payload.get("sub")
    if not email:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
        )

    user = db.query(models.User).filter(models.User.email == str(email)).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )

    return schemas.UserResponse.model_validate(user)
