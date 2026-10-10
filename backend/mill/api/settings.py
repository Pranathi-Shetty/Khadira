"""Settings router: company name, currency, thresholds."""

from fastapi import APIRouter
from pydantic import BaseModel

from ..services.common import all_settings, set_setting
from .deps import Db, can

router = APIRouter(prefix="/api/settings", tags=["settings"])

DEFAULTS = {
    "company_name": "Khadira",
    "currency": "INR",
    "low_stock_threshold_kg": "500",
}


@router.get("")
def get_settings(db: Db, _: can("settings.read")) -> dict:
    stored = all_settings(db)
    return {k: stored.get(k, v) for k, v in DEFAULTS.items()}


class SettingPatch(BaseModel):
    key: str
    value: str


@router.patch("")
def update_setting(body: SettingPatch, db: Db, _: can("settings.write")) -> dict:
    from ..services.common import DomainError
    if body.key not in DEFAULTS:
        raise DomainError(f"Unknown setting key '{body.key}'.")
    set_setting(db, body.key, body.value)
    db.commit()
    return get_settings(db, _)
