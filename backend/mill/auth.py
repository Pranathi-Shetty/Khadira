"""Authentication, permissions and current-user dependency."""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
from datetime import datetime, timedelta, timezone
from typing import Optional

import bcrypt
from fastapi import Cookie, Depends, HTTPException, status
from sqlalchemy.orm import Session

from mill.database import get_db
from mill.models import User, UserRole

SECRET_KEY = os.environ.get("SECRET_KEY", "everest-textile-dev-secret-change-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 12   # 12 hours


class JWTError(Exception):
    pass


def _b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _b64url_decode(s: str) -> bytes:
    padding = 4 - (len(s) % 4)
    if padding != 4:
        s += "=" * padding
    return base64.urlsafe_b64decode(s.encode("ascii"))


class _SimpleJWT:
    @staticmethod
    def encode(claims: dict, key: str, algorithm: str = "HS256") -> str:
        header = {"alg": algorithm, "typ": "JWT"}
        header_b64 = _b64url_encode(json.dumps(header, separators=(",", ":")).encode("utf-8"))
        clean_claims = {}
        for k, v in claims.items():
            if isinstance(v, datetime):
                clean_claims[k] = int(v.timestamp())
            else:
                clean_claims[k] = v
        payload_b64 = _b64url_encode(json.dumps(clean_claims, separators=(",", ":")).encode("utf-8"))
        signing_input = f"{header_b64}.{payload_b64}".encode("utf-8")
        signature = hmac.new(key.encode("utf-8"), signing_input, hashlib.sha256).digest()
        sig_b64 = _b64url_encode(signature)
        return f"{header_b64}.{payload_b64}.{sig_b64}"

    @staticmethod
    def decode(token: str, key: str, algorithms: list[str] | None = None) -> dict:
        parts = token.split(".")
        if len(parts) != 3:
            raise JWTError("Invalid token segments")
        header_b64, payload_b64, sig_b64 = parts
        signing_input = f"{header_b64}.{payload_b64}".encode("utf-8")
        expected_sig = hmac.new(key.encode("utf-8"), signing_input, hashlib.sha256).digest()
        actual_sig = _b64url_decode(sig_b64)
        if not hmac.compare_digest(expected_sig, actual_sig):
            raise JWTError("Signature verification failed")
        payload = json.loads(_b64url_decode(payload_b64).decode("utf-8"))
        if "exp" in payload:
            if datetime.now(timezone.utc).timestamp() > payload["exp"]:
                raise JWTError("Token expired")
        return payload


jwt = _SimpleJWT()


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))
    except Exception:
        return False


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
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
