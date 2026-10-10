"""Auth router: login, logout, me."""

from fastapi import APIRouter, Request, Response
from pydantic import BaseModel, Field

from ..models import User
from ..permissions import ROLES, permissions_for
from ..services import auth as auth_service
from ..services.common import all_settings
from .deps import SESSION_COOKIE, CurrentUser, Db

router = APIRouter(prefix="/api/auth", tags=["auth"])


class LoginIn(BaseModel):
    username: str = Field(min_length=1, max_length=120)
    password: str = Field(min_length=1, max_length=200)


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
