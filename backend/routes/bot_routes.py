import asyncio
import logging
from datetime import datetime

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy.orm import Session

from database.session import get_db
from database.models import BotSession, BotStatus, TradingConfiguration, User
from routes.auth import get_current_user
from services.trading_engine import TradingEngine

logger = logging.getLogger(__name__)
router = APIRouter()

# In-memory registry of currently running engines (per user)
_active_engines: dict[str, TradingEngine] = {}


def _get_engine(user_id: str) -> TradingEngine:
    engine = _active_engines.get(user_id)
    if not engine:
        raise HTTPException(status_code=404, detail="Bot is not running")
    return engine


# ─── Start Bot ────────────────────────────────────────────────
@router.post("/bot/start")
async def start_bot(
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if current_user.id in _active_engines:
        raise HTTPException(status_code=400, detail="Bot is already running")

    config = db.query(TradingConfiguration).filter(
        TradingConfiguration.user_id == current_user.id
    ).first()
    if not config:
        raise HTTPException(status_code=400, detail="Please save a trading configuration first")

    session = BotSession(user_id=current_user.id)
    db.add(session)
    db.commit()
    db.refresh(session)

    engine = TradingEngine(config=config, session_id=session.id, user_id=current_user.id)
    _active_engines[current_user.id] = engine

    background_tasks.add_task(engine.run_trading_loop)

    logger.info(f"Bot started for user {current_user.email} (session {session.id})")
    return {
        "success": True,
        "session_id": session.id,
        "message": "Trading bot started",
    }


# ─── Pause Bot ────────────────────────────────────────────────
@router.post("/bot/pause")
async def pause_bot(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    engine = _get_engine(current_user.id)
    engine.pause()
    db.query(BotSession).filter(
        BotSession.user_id == current_user.id,
        BotSession.status == BotStatus.running,
    ).update({"status": BotStatus.paused})
    db.commit()
    return {"success": True, "message": "Bot paused — open positions remain"}


# ─── Resume Bot ───────────────────────────────────────────────
@router.post("/bot/resume")
async def resume_bot(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    engine = _get_engine(current_user.id)
    engine.resume()
    db.query(BotSession).filter(
        BotSession.user_id == current_user.id,
        BotSession.status == BotStatus.paused,
    ).update({"status": BotStatus.running})
    db.commit()
    return {"success": True, "message": "Bot resumed"}


# ─── Stop Bot ─────────────────────────────────────────────────
@router.post("/bot/stop")
async def stop_bot(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    engine = _get_engine(current_user.id)
    closed = await engine.close_all_positions()
    engine.stop()
    del _active_engines[current_user.id]

    db.query(BotSession).filter(
        BotSession.user_id == current_user.id,
        BotSession.status.in_([BotStatus.running, BotStatus.paused]),
    ).update({"status": BotStatus.stopped, "stopped_at": datetime.utcnow()})
    db.commit()

    return {
        "success": True,
        "positions_closed": len(closed),
        "message": f"Bot stopped. {len(closed)} positions closed.",
    }


# ─── Bot Status ───────────────────────────────────────────────
@router.get("/bot/status")
async def bot_status(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    session = (
        db.query(BotSession)
        .filter(BotSession.user_id == current_user.id)
        .order_by(BotSession.started_at.desc())
        .first()
    )
    engine = _active_engines.get(current_user.id)

    if not session:
        return {"status": "never_started", "open_positions": 0}

    uptime = None
    if session.started_at and not session.stopped_at:
        uptime = int((datetime.utcnow() - session.started_at).total_seconds())

    return {
        "session_id": session.id,
        "status": session.status.value,
        "started_at": session.started_at,
        "stopped_at": session.stopped_at,
        "uptime_seconds": uptime,
        "open_positions": len(engine.open_trades) if engine else 0,
        "is_paused": engine.is_paused if engine else False,
        "last_update": engine.last_update if engine else None,
    }
