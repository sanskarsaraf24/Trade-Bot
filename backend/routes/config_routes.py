from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database.session import get_db
from database.models import TradingConfiguration, User
from routes.auth import get_current_user

router = APIRouter()


# ─── Pydantic Schemas ─────────────────────────────────────────
class ConfigRequest(BaseModel):
    account_balance: float = 100000
    daily_profit_target: float = 5000
    daily_loss_limit: float = 3000
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
        for key, value in req.model_dump().items():
            setattr(config, key, value)
        config.updated_at = datetime.utcnow()
    else:
        config = TradingConfiguration(user_id=current_user.id, **req.model_dump())
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
