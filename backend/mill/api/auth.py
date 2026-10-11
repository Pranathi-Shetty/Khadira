"""Auth router: login, logout, me."""

from fastapi import APIRouter, Request, Response
from pydantic import BaseModel, Field
from sqlalchemy import select

from ..models import User
from ..permissions import ROLES, permissions_for
from ..services import auth as auth_service
from ..services.common import DomainError, all_settings
from .deps import SESSION_COOKIE, CurrentUser, Db

router = APIRouter(prefix="/api/auth", tags=["auth"])


class LoginIn(BaseModel):
    username: str = Field(min_length=1, max_length=120)
    password: str = Field(min_length=1, max_length=200)


class RegisterIn(BaseModel):
    username: str = Field(min_length=2, max_length=120)
    password: str = Field(min_length=3, max_length=200)
    full_name: str | None = None
    email: str | None = None
    role: str = Field(default="office")


def me_out(user: User, db) -> dict:
    return {
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "full_name": user.full_name,
        "role": user.role,
        "role_label": ROLES.get(user.role, {}).get("label", user.role),
        "permissions": sorted(permissions_for(user.role)),
        "company": {k: v for k, v in all_settings(db).items()
                    if k in ("company_name", "currency")},
    }


@router.post("/login")
def login(body: LoginIn, request: Request, response: Response, db: Db) -> dict:
    settings = request.app.state.settings
    user = auth_service.authenticate(db, body.username, body.password)
    token = auth_service.start_session(db, user, settings.session_hours)
    db.commit()
    response.set_cookie(
        SESSION_COOKIE, token,
        max_age=settings.session_hours * 3600,
        httponly=True, samesite="lax",
        secure=settings.cookie_secure, path="/",
    )
    return me_out(user, db)


@router.post("/register", status_code=201)
def register(body: RegisterIn, request: Request, response: Response, db: Db) -> dict:
    canonical_user = body.username.strip().lower()
    existing = db.scalar(
        select(User).where((User.username == canonical_user) | (User.username == body.username.strip()))
    )
    if existing:
        raise DomainError(f"Username '{body.username}' is already taken. Please choose another username.", 400)

    role = body.role.strip().lower()
    if role not in ROLES:
        role = "office"

    user = User(
        username=canonical_user,
        full_name=body.full_name.strip() if body.full_name else body.username.strip().title(),
        email=body.email.strip() if body.email else None,
        hashed_password=auth_service.hash_password(body.password),
        role=role,
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    settings = request.app.state.settings
    token = auth_service.start_session(db, user, settings.session_hours)
    db.commit()
    response.set_cookie(
        SESSION_COOKIE, token,
        max_age=settings.session_hours * 3600,
        httponly=True, samesite="lax",
        secure=settings.cookie_secure, path="/",
    )
    return me_out(user, db)


@router.get("/roles")
def get_roles() -> list[dict]:
    return [
        {
            "role": key,
            "label": val.get("label", key),
            "permissions_count": len(permissions_for(key)),
        }
        for key, val in ROLES.items()
    ]


@router.get("/directory")
def user_directory(db: Db) -> list[dict]:
    users = db.scalars(select(User).where(User.is_active.is_(True)).order_by(User.id.asc())).all()
    return [
        {
            "id": u.id,
            "username": u.username,
            "full_name": u.full_name or u.username,
            "role": u.role,
            "role_label": ROLES.get(u.role, {}).get("label", u.role),
        }
        for u in users
    ]


@router.post("/logout", status_code=204)
def logout(request: Request, response: Response, db: Db) -> None:
    token = request.cookies.get(SESSION_COOKIE)
    if token:
        auth_service.end_session(db, token)
        db.commit()
    response.delete_cookie(SESSION_COOKIE, path="/")


@router.get("/me")
def me(user: CurrentUser, db: Db) -> dict:
    return me_out(user, db)

