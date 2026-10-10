"""Auth service: password hashing, sessions."""

from datetime import datetime, timedelta, timezone

import bcrypt
from sqlalchemy import select
from sqlalchemy.orm import Session as DbSession

from ..models import Session, User
from .common import DomainError


def hash_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode(), bcrypt.gensalt()).decode()


def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode(), hashed.encode())


def authenticate(db: DbSession, username: str, password: str) -> User:
    user = db.scalar(select(User).where(User.username == username, User.is_active.is_(True)))
    if not user or not verify_password(password, user.hashed_password):
        raise DomainError("Invalid username or password.", 401)
    return user


def start_session(db: DbSession, user: User, hours: int = 8) -> str:
    expires = datetime.now(timezone.utc) + timedelta(hours=hours)
    sess = Session(user_id=user.id, expires_at=expires)
    db.add(sess)
    db.flush()
    return sess.token


def end_session(db: DbSession, token: str) -> None:
    sess = db.scalar(select(Session).where(Session.token == token))
    if sess:
        db.delete(sess)


def user_for_token(db: DbSession, token: str | None) -> User | None:
    if not token:
        return None
    now = datetime.now(timezone.utc)
    sess = db.scalar(
        select(Session)
        .where(Session.token == token, Session.expires_at > now)
    )
    return sess.user if sess else None
