import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean, Column, DateTime, Enum, Float, Integer,
    JSON, String, Text, ForeignKey,
)
from sqlalchemy.orm import DeclarativeBase, relationship
import enum


class Base(DeclarativeBase):
    pass


# ─────────────────────────────────────────────
# Enums
# ─────────────────────────────────────────────
class RiskAppetite(str, enum.Enum):
    conservative = "conservative"
    moderate = "moderate"
    aggressive = "aggressive"


class Timeframe(str, enum.Enum):
    scalp = "scalp"
    intraday = "intraday"
    swing = "swing"


class TradeSignal(str, enum.Enum):
    BUY_STOCK = "BUY_STOCK"
    SELL_STOCK = "SELL_STOCK"
    BUY_CALL = "BUY_CALL"
    BUY_PUT = "BUY_PUT"
    EXIT = "EXIT"
    HOLD = "HOLD"


class TradeStatus(str, enum.Enum):
    OPEN = "OPEN"
    CLOSED = "CLOSED"
    CANCELLED = "CANCELLED"


class BotStatus(str, enum.Enum):
    running = "running"
    paused = "paused"
    stopped = "stopped"


# ─────────────────────────────────────────────
# User
# ─────────────────────────────────────────────
class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    email = Column(String, unique=True, nullable=False, index=True)
    hashed_password = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    config = relationship("TradingConfiguration", back_populates="user", uselist=False)
    trades = relationship("Trade", back_populates="user")
    bot_sessions = relationship("BotSession", back_populates="user")
    logs = relationship("SystemLog", back_populates="user")


# ─────────────────────────────────────────────
# Trading Configuration
# ─────────────────────────────────────────────
class TradingConfiguration(Base):
    __tablename__ = "trading_configurations"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), unique=True, nullable=False)

    # Account
    account_balance = Column(Float, nullable=False, default=100000)
    daily_profit_target = Column(Float, nullable=False, default=5000)
    daily_loss_limit = Column(Float, nullable=False, default=3000)
    risk_per_trade_percent = Column(Float, nullable=False, default=1.0)

    # Risk
    risk_appetite = Column(Enum(RiskAppetite), default=RiskAppetite.moderate)

    # Timing
    market_start_time = Column(String, default="09:15")
    market_end_time = Column(String, default="15:15")
    auto_exit_time = Column(String, default="15:25")

    # Symbol selection
    symbol_selection_mode = Column(String, default="auto")  # manual | auto | free
    manual_symbols = Column(JSON, default=list)
    allowed_sectors = Column(JSON, default=list)

    # Parameters
    min_confidence_threshold = Column(Float, default=65.0)
    max_concurrent_positions = Column(Integer, default=5)
    timeframe = Column(Enum(Timeframe), default=Timeframe.intraday)
    analysis_interval_minutes = Column(Integer, default=15)

    # Markets
    markets_enabled = Column(JSON, default=lambda: {"NSE_STOCKS": True, "NSE_OPTIONS": False})

    # Strategy
    enabled_strategies = Column(JSON, default=list)
    avoid_trading_during = Column(JSON, default=list)
    require_manual_approval = Column(Boolean, default=False)
    system_instructions = Column(Text, default="")

    # Broker
    broker_type = Column(String, default="paper")
    broker_api_key = Column(String, default="")
    broker_api_secret = Column(String, default="")
    broker_access_token = Column(String, default="")
    broker_totp_secret = Column(String, default="")

    # Alerts
    email_alerts_enabled = Column(Boolean, default=True)
    alert_email = Column(String, default="")

    # Meta
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User", back_populates="config")


# ─────────────────────────────────────────────
# Trade
# ─────────────────────────────────────────────
class Trade(Base):
    __tablename__ = "trades"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    bot_session_id = Column(String, ForeignKey("bot_sessions.id"), nullable=True)

    # Symbol & direction
    symbol = Column(String, nullable=False, index=True)
    signal = Column(Enum(TradeSignal), nullable=False)
    status = Column(Enum(TradeStatus), default=TradeStatus.OPEN)

    # Prices
    entry_price = Column(Float, nullable=False)
    exit_price = Column(Float, nullable=True)
    stop_loss = Column(Float, nullable=True)
    target = Column(Float, nullable=True)
    quantity = Column(Integer, nullable=False, default=1)

    # P&L
    pnl = Column(Float, default=0.0)
    pnl_percent = Column(Float, default=0.0)

    # AI metadata
    confidence = Column(Float, default=0.0)
    claude_reasoning = Column(Text, default="")

    # Order IDs (from broker)
    main_order_id = Column(String, default="")
    sl_order_id = Column(String, default="")
    target_order_id = Column(String, default="")

    # Exit
    exit_reason = Column(String, nullable=True)  # SL_HIT, TARGET_HIT, MANUAL, EOD

    # Timestamps
    entry_time = Column(DateTime, default=datetime.utcnow)
    exit_time = Column(DateTime, nullable=True)

    user = relationship("User", back_populates="trades")
    bot_session = relationship("BotSession", back_populates="trades")


# ─────────────────────────────────────────────
# Bot Session
# ─────────────────────────────────────────────
class BotSession(Base):
    __tablename__ = "bot_sessions"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    status = Column(Enum(BotStatus), default=BotStatus.running)
    started_at = Column(DateTime, default=datetime.utcnow)
    stopped_at = Column(DateTime, nullable=True)

    user = relationship("User", back_populates="bot_sessions")
    trades = relationship("Trade", back_populates="bot_session")


# ─────────────────────────────────────────────
# System Log
# ─────────────────────────────────────────────
class SystemLog(Base):
    __tablename__ = "system_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    event_type = Column(String, nullable=False)  # trade_opened, signal, error, info
    message = Column(Text, nullable=False)
    severity = Column(String, default="info")  # info | warning | error
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)

    user = relationship("User", back_populates="logs")
