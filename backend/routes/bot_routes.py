import asyncio
import logging

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy.orm import Session

from database.session import get_db
from database.models import BotSession, BotStatus, TradingConfiguration, User, ist_now
from routes.auth import get_current_user
from services.trading_engine import TradingEngine

logger = logging.getLogger(__name__)
router = APIRouter()

# ── In-memory registry of running engines (per user_id) ──────
_active_engines: dict[str, TradingEngine] = {}


def _get_engine(user_id: str) -> TradingEngine:
    engine = _active_engines.get(user_id)
    if not engine:
        raise HTTPException(status_code=404, detail="Bot is not running")
    return engine


# ─── Start ────────────────────────────────────────────────────
@router.post("/bot/start")
async def start_bot(
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Start the trading bot. Creates a BotSession and fires the engine loop."""
    if current_user.id in _active_engines:
        raise HTTPException(status_code=400, detail="Bot is already running")

    config = db.query(TradingConfiguration).filter(
        TradingConfiguration.user_id == current_user.id
    ).first()
    if not config:
        raise HTTPException(
            status_code=400,
            detail="No configuration found. Please save a trading configuration first."
        )

    # Zerodha: warn if token missing
    if config.broker_type == "zerodha" and not config.broker_access_token:
        raise HTTPException(
            status_code=400,
            detail="Zerodha access token missing. Click 'Re-link Zerodha' in Config to authenticate."
        )

    # Create DB session record
    session = BotSession(user_id=current_user.id, status=BotStatus.running)
    db.add(session)
    db.commit()
    db.refresh(session)

    # Build engine and register it
    engine = TradingEngine(
        config=config,
        session_id=session.id,
        user_id=current_user.id,
    )
    _active_engines[current_user.id] = engine

    # Fire loop in background
    background_tasks.add_task(_run_engine, engine, current_user.id, session.id)

    logger.info(f"Bot started for user {current_user.email} (session {session.id})")
    return {
        "success": True,
        "session_id": session.id,
        "message": "Trading bot started",
    }


async def _run_engine(engine: TradingEngine, user_id: str, session_id: str):
    """Wrapper that cleans up after the engine loop exits."""
    try:
        await engine.run_trading_loop()
    except Exception as e:
        logger.error(f"Engine crashed for user {user_id}: {e}")
    finally:
        # Always clean up
        _active_engines.pop(user_id, None)
        # Mark session as stopped if still running
        from database.session import SessionLocal
        db = SessionLocal()
        try:
            db.query(BotSession).filter(
                BotSession.id == session_id,
                BotSession.status.in_([BotStatus.running, BotStatus.paused]),
            ).update({"status": BotStatus.stopped, "stopped_at": ist_now()})
            db.commit()
        finally:
            db.close()
        logger.info(f"Engine loop ended for user {user_id}")


# ─── Pause ────────────────────────────────────────────────────
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
    return {"success": True, "message": "Bot paused — open positions remain open"}


# ─── Resume ───────────────────────────────────────────────────
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


# ─── Stop ─────────────────────────────────────────────────────
@router.post("/bot/stop")
async def stop_bot(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Stop the trading bot. Closes positions and removes from active registry."""
    engine = _active_engines.get(current_user.id)
    closed_count = 0
    
    if engine:
        try:
            closed = await engine.close_all_positions()
            closed_count = len(closed)
            engine.stop()
        except Exception as e:
            logger.error(f"Error during engine shutdown for {current_user.email}: {e}")
        finally:
            _active_engines.pop(current_user.id, None)

    # Database cleanup: update ANY running or paused session for this user to 'stopped'
    updated_count = db.query(BotSession).filter(
        BotSession.user_id == current_user.id,
        BotSession.status.in_([BotStatus.running, BotStatus.paused]),
    ).update({
        "status": BotStatus.stopped, 
        "stopped_at": ist_now()
    })
    db.commit()

    if not engine and updated_count == 0:
        raise HTTPException(status_code=404, detail="Bot is not running")

    message = f"Bot stopped. {closed_count} position(s) closed."
    if not engine and updated_count > 0:
        message = "Stale bot session cleaned up (engine was already closed or offline)."

    return {
        "success": True,
        "positions_closed": closed_count,
        "message": message,
    }


# ─── Status ───────────────────────────────────────────────────
@router.get("/bot/status")
async def bot_status(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get latest bot status."""
    session = (
        db.query(BotSession)
        .filter(BotSession.user_id == current_user.id)
        .order_by(BotSession.started_at.desc())
        .first()
    )
    engine = _active_engines.get(current_user.id)

    if not session:
        return {
            "status": "never_started",
            "open_positions": 0,
            "is_paused": False,
            "last_update": None,
            "uptime_seconds": None,
        }

    uptime = None
    if session.started_at and not session.stopped_at:
        uptime = int((ist_now() - session.started_at).total_seconds())

    return {
        "session_id": session.id,
        "status": session.status.value,
        "started_at": session.started_at,
        "stopped_at": session.stopped_at,
        "uptime_seconds": uptime,
        "open_positions": len(engine.open_trades) if engine else 0,
        "is_paused": engine.is_paused if engine else False,
        "last_update": engine.last_update if engine else None,
        "broker_type": (engine.config.broker_type if engine else None),
    }
