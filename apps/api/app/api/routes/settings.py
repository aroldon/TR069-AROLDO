from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import AuthContext, get_current_auth
from app.cpe.extract import optical_thresholds_ordered
from app.models.settings import AppSettings

router = APIRouter(prefix="/settings", tags=["settings"])


def _row(db: Session) -> AppSettings:
    row = db.query(AppSettings).first()
    if not row:
        row = AppSettings()
        db.add(row)
        db.commit()
        db.refresh(row)
    return row


class SettingsOut(BaseModel):
    installed: bool
    timezone: str
    locale: str
    approved_dns: list[str]
    online_threshold_s: int
    diagnostic_cooldown_s: int
    diagnostic_timeout_s: int
    optical_rx_no_signal_dbm: float
    optical_rx_critical_dbm: float
    optical_rx_warning_dbm: float
    optical_rx_overload_dbm: float


class SettingsPatch(BaseModel):
    timezone: str | None = None
    locale: str | None = None
    approved_dns: list[str] | None = None
    online_threshold_s: int | None = Field(default=None, ge=30, le=86400)
    diagnostic_cooldown_s: int | None = Field(default=None, ge=0, le=3600)
    diagnostic_timeout_s: int | None = Field(default=None, ge=30, le=600)
    optical_rx_no_signal_dbm: float | None = Field(default=None, ge=-70, le=10)
    optical_rx_critical_dbm: float | None = Field(default=None, ge=-70, le=10)
    optical_rx_warning_dbm: float | None = Field(default=None, ge=-70, le=10)
    optical_rx_overload_dbm: float | None = Field(default=None, ge=-70, le=10)


@router.get("", response_model=SettingsOut)
def get_settings(db: Session = Depends(get_db), auth: AuthContext = Depends(get_current_auth)):
    auth.require("settings.view")
    s = _row(db)
    return SettingsOut(
        installed=s.installed,
        timezone=s.timezone,
        locale=s.locale,
        approved_dns=list(s.approved_dns or []),
        online_threshold_s=s.online_threshold_s,
        diagnostic_cooldown_s=s.diagnostic_cooldown_s,
        diagnostic_timeout_s=s.diagnostic_timeout_s,
        optical_rx_no_signal_dbm=s.optical_rx_no_signal_dbm,
        optical_rx_critical_dbm=s.optical_rx_critical_dbm,
        optical_rx_warning_dbm=s.optical_rx_warning_dbm,
        optical_rx_overload_dbm=s.optical_rx_overload_dbm,
    )


@router.patch("", response_model=SettingsOut)
def patch_settings(body: SettingsPatch, db: Session = Depends(get_db), auth: AuthContext = Depends(get_current_auth)):
    auth.require("settings.edit")
    s = _row(db)
    data = body.model_dump(exclude_unset=True)
    for k, v in data.items():
        setattr(s, k, v)
    if not optical_thresholds_ordered(
        s.optical_rx_no_signal_dbm,
        s.optical_rx_critical_dbm,
        s.optical_rx_warning_dbm,
        s.optical_rx_overload_dbm,
    ):
        db.rollback()
        raise HTTPException(
            status_code=400,
            detail="Limiares de RX devem seguir sem sinal ≤ crítico ≤ atenção < sobrecarga",
        )
    db.commit()
    db.refresh(s)
    return get_settings(db=db, auth=auth)
