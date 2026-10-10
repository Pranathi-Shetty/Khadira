"""Authentication, permissions and current-user dependency."""
from __future__ import annotations

import os
from datetime import datetime, timedelta
from typing import Optional

from fastapi import Cookie, Depends, HTTPException, status
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from mill.database import get_db
from mill.models import User, UserRole

SECRET_KEY = os.environ.get("SECRET_KEY", "khadira-textile-dev-secret-change-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 12   # 12 hours

pwd_context = CryptContext(schemes=["bcrypt", "sha256_crypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def get_current_user(
    access_token: Optional[str] = Cookie(default=None),
    db: Session = Depends(get_db),
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Not authenticated",
    )
    if not access_token:
        raise credentials_exception
    try:
        payload = jwt.decode(access_token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: int = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    user = db.query(User).filter(User.id == int(user_id), User.is_active == True).first()
    if user is None:
        raise credentials_exception
    return user


# ---------------------------------------------------------------------------
# Permission matrix
# ---------------------------------------------------------------------------

ROLE_PERMISSIONS: dict[UserRole, set[str]] = {
    UserRole.admin: {
        "users.manage", "settings.manage",
        "items.read", "items.write",
        "partners.read", "partners.write",
        "purchasing.read", "purchasing.write",
        "orders.read", "orders.write",
        "machines.read", "machines.write",
        "production.read", "production.write",
        "rolls.read", "rolls.write",
        "qc.read", "qc.write",
        "dispatch.read", "dispatch.write",
        "finance.read", "finance.write",
        "attendance.read", "attendance.write", "attendance.approve",
        "wages.read", "wages.write", "wages.finalise",
        "costing.read", "costing.write",
        "reports.read",
    },
    UserRole.owner: {
        "items.read", "partners.read", "purchasing.read", "orders.read",
        "machines.read", "production.read", "rolls.read", "qc.read",
        "dispatch.read", "finance.read", "finance.write",
        "attendance.read", "attendance.approve",
        "wages.read", "wages.write", "wages.finalise",
        "costing.read", "costing.write",
        "reports.read", "settings.manage",
    },
    UserRole.store: {
        "items.read", "purchasing.read", "purchasing.write",
        "orders.read", "rolls.read", "rolls.write",
        "dispatch.read", "dispatch.write",
    },
    UserRole.floor_supervisor: {
        "items.read", "orders.read", "machines.read", "machines.write",
        "production.read", "production.write",
        "rolls.read", "rolls.write",
        "attendance.read", "attendance.write", "attendance.approve",
    },
    UserRole.qc: {
        "items.read", "orders.read", "rolls.read", "rolls.write",
        "qc.read", "qc.write",
    },
    UserRole.office: {
        "items.read", "partners.read", "partners.write",
        "purchasing.read", "purchasing.write",
        "orders.read", "orders.write",
        "dispatch.read", "finance.read", "finance.write",
        "wages.read", "costing.read", "reports.read",
    },
}


def can(permission: str):
    """Return a FastAPI dependency that checks the given permission."""
    def checker(current_user: User = Depends(get_current_user)):
        if permission not in ROLE_PERMISSIONS.get(current_user.role, set()):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission denied: {permission}",
            )
        return current_user
    return checker
