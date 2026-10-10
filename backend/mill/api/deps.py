"""Shared request plumbing: session, auth dependency, pagination."""

from typing import Annotated, Any, Callable

from fastapi import Depends, HTTPException, Query, Request
from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session

from ..models import User
from ..permissions import permissions_for
from ..services import auth as auth_service

SESSION_COOKIE = "mill_session"


def get_db(request: Request):
    factory = request.app.state.session_factory
    db: Session = factory()
    try:
        yield db
    finally:
        db.close()


Db = Annotated[Session, Depends(get_db)]


def current_user(request: Request, db: Db) -> User:
    token = request.cookies.get(SESSION_COOKIE)
    user = auth_service.user_for_token(db, token) if token else None
    if user is None:
        raise HTTPException(401, "Please log in.")
    return user


CurrentUser = Annotated[User, Depends(current_user)]


def require(permission: str) -> Callable[[User], User]:
    def check(user: CurrentUser) -> User:
        if permission not in permissions_for(user.role):
            raise HTTPException(403, "Your role does not allow this.")
        return user
    return check


class _CanMeta(type):
    def __getitem__(cls, permission: str):
        return Annotated[User, Depends(require(permission))]

    def __call__(cls, permission: str):
        return Annotated[User, Depends(require(permission))]


class can(metaclass=_CanMeta):
    """Dependency that returns the user if they hold `permission`.
    Supports both can['permission'] (static type checking friendly) and can('permission').
    """
    pass


class ListParams:
    def __init__(
        self,
        page: Annotated[int, Query(ge=1)] = 1,
        page_size: Annotated[int, Query(ge=1, le=200)] = 25,
        q: Annotated[str | None, Query(max_length=100)] = None,
        sort: Annotated[str | None, Query(max_length=40)] = None,
    ):
        self.page = page
        self.page_size = page_size
        self.q = q.strip() if q and q.strip() else None
        self.sort = sort


Params = Annotated[ListParams, Depends()]


def paginate(
    db: Session,
    stmt: Select,
    params: ListParams,
    serialize: Callable[[Any], dict],
    sortable: dict[str, Any] | None = None,
    default_sort: list | None = None,
    scalars: bool = True,
) -> dict:
    total = db.scalar(select(func.count()).select_from(stmt.order_by(None).subquery()))
    order = list(default_sort or [])
    if params.sort and sortable:
        key = params.sort.lstrip("-")
        if key in sortable:
            column = sortable[key]
            order = [column.desc() if params.sort.startswith("-") else column.asc(), *order]
    if order:
        stmt = stmt.order_by(*order)
    stmt = stmt.offset((params.page - 1) * params.page_size).limit(params.page_size)
    rows = db.scalars(stmt).all() if scalars else db.execute(stmt).all()
    return {"items": [serialize(r) for r in rows], "total": total,
            "page": params.page, "page_size": params.page_size}


def like(value: str) -> str:
    return f"%{value.replace('%', '').replace('_', ' ')}%"
