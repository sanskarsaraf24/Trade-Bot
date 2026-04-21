from datetime import datetime
import math
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field, model_validator
from sqlalchemy.orm import Session

from database.session import get_db
from database.models import TradingConfiguration, User, ist_now
from routes.auth import get_current_user

router = APIRouter()


# ─── Pydantic Schemas ─────────────────────────────────────────
class ConfigRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")

    account_balance: float = 100000
    daily_profit_target: float = 5000
    daily_loss_limit: float = 3000
    max_daily_loss_percent: Optional[float] = Field(default=None)
    risk_per_trade_percent: float = 1.0
    risk_appetite: str = "moderate"

    market_start_time: str = "09:15"
    market_end_time: str = "15:15"
    auto_exit_time: str = "15:25"

    symbol_selection_mode: str = "auto"
    manual_symbols: List[str] = []
    allowed_sectors: List[str] = []

    min_confidence_threshold: float = 65.0
    max_concurrent_positions: int = 5
    timeframe: str = "intraday"
    analysis_interval_minutes: int = 15

    margin_multiplier: float = 1.0
    min_profit_absolute: Optional[float] = None
    min_profit_percent: Optional[float] = None
    default_stop_loss_percent: float = 0.5
    default_target_percent: float = 1.0

    markets_enabled: dict = {"NSE_STOCKS": True, "NSE_OPTIONS": False}
    enabled_strategies: List[str] = []
    avoid_trading_during: List[str] = []
    require_manual_approval: bool = False
    system_instructions: str = ""

    broker_type: str = "paper"
    broker_api_key: str = ""
    broker_api_secret: str = ""
    broker_access_token: str = ""
    broker_totp_secret: str = ""

    email_alerts_enabled: bool = True
    alert_email: str = ""

    @model_validator(mode="before")
    @classmethod
    def normalize_dashboard_payload(cls, raw):
        if not isinstance(raw, dict):
            return raw
        data = dict(raw)

        # New dashboard sends percentage-based daily loss control.
        if data.get("max_daily_loss_percent") is not None:
            try:
                bal = float(data.get("account_balance") or 100000)
                pct = float(data.get("max_daily_loss_percent") or 0)
                data["daily_loss_limit"] = (bal * pct) / 100.0
            except Exception:
                pass

        # Accept manual symbols from comma-separated textbox.
        if isinstance(data.get("manual_symbols_text"), str) and not data.get("manual_symbols"):
            parsed = [s.strip().upper() for s in data["manual_symbols_text"].split(",") if s.strip()]
            data["manual_symbols"] = parsed

        # Backward-compatible broker mode aliases from older UI variants.
        broker_type = str(data.get("broker_type") or "paper").strip().lower()
        if broker_type in {"production", "prod", "live"}:
            broker_type = "zerodha"
        elif broker_type in {"simulator", "demo"}:
            broker_type = "paper"
        data["broker_type"] = broker_type

        for key in ("broker_api_key", "broker_api_secret", "broker_access_token", "broker_totp_secret"):
            if isinstance(data.get(key), str):
                data[key] = data[key].strip()

        # Prevent null/NaN from frontend from causing 422/400 on required numbers.
        numeric_defaults = {
            "account_balance": 100000,
            "daily_profit_target": 5000,
            "daily_loss_limit": 3000,
            "risk_per_trade_percent": 1.0,
            "min_confidence_threshold": 65.0,
            "max_concurrent_positions": 5,
            "analysis_interval_minutes": 15,
            "margin_multiplier": 1.0,
            "default_stop_loss_percent": 0.5,
            "default_target_percent": 1.0,
        }
        for key, default in numeric_defaults.items():
            val = data.get(key)
            if val is None:
                data[key] = default
                continue
            try:
                f = float(val)
                if math.isnan(f) or math.isinf(f):
                    data[key] = default
            except Exception:
                data[key] = default

        for opt_key in ("min_profit_absolute", "min_profit_percent"):
            val = data.get(opt_key)
            if val is None:
                continue
            try:
                f = float(val)
                if math.isnan(f) or math.isinf(f):
                    data[opt_key] = None
            except Exception:
                data[opt_key] = None

        return data


class ConfigResponse(ConfigRequest):
    id: str
    user_id: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ─── Endpoints ────────────────────────────────────────────────
@router.get("/config", response_model=ConfigResponse)
async def get_config(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get the current user's trading configuration."""
    config = db.query(TradingConfiguration).filter(
        TradingConfiguration.user_id == current_user.id
    ).first()
    if not config:
        raise HTTPException(status_code=404, detail="No configuration found. Please create one.")
    return config


@router.post("/config", response_model=ConfigResponse)
async def save_config(
    req: ConfigRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Save or update trading configuration."""
    payload = req.model_dump(exclude={"max_daily_loss_percent"})
    sensitive_fields = {
        "broker_api_key",
        "broker_api_secret",
        "broker_access_token",
        "broker_totp_secret",
    }

    # Guard rails
    if req.daily_loss_limit > req.account_balance * 0.10:
        raise HTTPException(status_code=400, detail="Daily loss limit cannot exceed 10% of balance")
    if req.max_concurrent_positions > 10:
        raise HTTPException(status_code=400, detail="Max 10 concurrent positions allowed")
    if req.risk_per_trade_percent > 5:
        raise HTTPException(status_code=400, detail="Risk per trade cannot exceed 5%")

    config = db.query(TradingConfiguration).filter(
        TradingConfiguration.user_id == current_user.id
    ).first()

    if config:
        for key, value in payload.items():
            if key in sensitive_fields and value == "":
                continue
            setattr(config, key, value)
        config.updated_at = ist_now()
    else:
        config = TradingConfiguration(user_id=current_user.id, **payload)
        db.add(config)

    db.commit()
    db.refresh(config)
    return config


@router.delete("/config")
async def reset_config(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Delete configuration (resets to defaults)."""
    config = db.query(TradingConfiguration).filter(
        TradingConfiguration.user_id == current_user.id
    ).first()
    if config:
        db.delete(config)
        db.commit()
    return {"success": True, "message": "Configuration reset"}
