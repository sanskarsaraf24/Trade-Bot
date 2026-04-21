from datetime import datetime, date
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database.session import get_db
from database.models import Trade, TradeStatus, User, ist_now
from routes.auth import get_current_user
from routes.bot_routes import _active_engines

router = APIRouter()


# ─── Schemas ──────────────────────────────────────────────────
class TradeOut(BaseModel):
    id: str
    symbol: str
    signal: str
    status: str
    entry_price: float
    exit_price: Optional[float]
    stop_loss: Optional[float]
    target: Optional[float]
    quantity: int
    pnl: float
    pnl_percent: float
    confidence: float
    claude_reasoning: str
    entry_time: datetime
    exit_time: Optional[datetime]
    exit_reason: Optional[str]

    class Config:
        from_attributes = True

class TradeUpdateRequest(BaseModel):
    stop_loss: Optional[float] = None
    target: Optional[float] = None


# ─── Open Trades ──────────────────────────────────────────────
@router.get("/trades/open", response_model=List[TradeOut])
async def get_open_trades(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    trades = db.query(Trade).filter(
        Trade.user_id == current_user.id,
        Trade.status == TradeStatus.OPEN,
    ).all()
    return trades


# ─── Closed Trades ────────────────────────────────────────────
@router.get("/trades/closed", response_model=List[TradeOut])
async def get_closed_trades(
    limit: int = 30,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    trades = (
        db.query(Trade)
        .filter(
            Trade.user_id == current_user.id,
            Trade.status == TradeStatus.CLOSED,
        )
        .order_by(Trade.exit_time.desc())
        .limit(limit)
        .all()
    )
    return trades


# ─── Manual Exit single trade ─────────────────────────────────
@router.post("/trades/exit/{trade_id}")
async def exit_trade(
    trade_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    trade = db.query(Trade).filter(
        Trade.id == trade_id,
        Trade.user_id == current_user.id,
    ).first()
    if not trade:
        raise HTTPException(status_code=404, detail="Trade not found")
    if trade.status != TradeStatus.OPEN:
        raise HTTPException(status_code=400, detail="Trade is already closed")

    engine = _active_engines.get(current_user.id)
    if engine:
        await engine.exit_trade(trade_id, reason="MANUAL_EXIT")
    else:
        # Bot not running — close in DB directly
        trade.status = TradeStatus.CLOSED
        trade.exit_reason = "MANUAL_EXIT"
        trade.exit_time = ist_now()
        db.commit()

    return {"success": True, "trade_id": trade_id, "message": "Trade closed manually"}


# ─── Exit All ─────────────────────────────────────────────────
@router.post("/trades/exit-all")
async def exit_all_trades(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    engine = _active_engines.get(current_user.id)
    if engine:
        closed = await engine.close_all_positions()
        return {
            "success": True,
            "trades_closed": len(closed),
            "message": f"Closed {len(closed)} positions",
        }
    # Bot not running — close all open trades in DB
    trades = db.query(Trade).filter(
        Trade.user_id == current_user.id,
        Trade.status == TradeStatus.OPEN,
    ).all()
    for t in trades:
        t.status = TradeStatus.CLOSED
        t.exit_reason = "MANUAL_EXIT"
        t.exit_time = ist_now()
    db.commit()
    return {"success": True, "trades_closed": len(trades), "message": f"Closed {len(trades)} positions"}


# ─── Update Trade (DB only — for backward compat) ────────────
@router.post("/trades/update/{trade_id}")
async def update_trade(
    trade_id: str,
    payload: TradeUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update trade SL/Target in DB and in-memory. Does NOT touch broker orders."""
    trade = db.query(Trade).filter(
        Trade.id == trade_id,
        Trade.user_id == current_user.id
    ).first()
    if not trade:
        raise HTTPException(status_code=404, detail="Trade not found")

    if payload.stop_loss is not None:
        trade.stop_loss = payload.stop_loss
    if payload.target is not None:
        trade.target = payload.target
    db.commit()

    # Update engine's in-memory tracking if running
    engine = _active_engines.get(current_user.id)
    if engine and trade.symbol in engine.open_trades:
        if payload.stop_loss is not None:
            engine.open_trades[trade.symbol]["stop_loss"] = payload.stop_loss
        if payload.target is not None:
            engine.open_trades[trade.symbol]["target"] = payload.target

    return {"success": True, "message": "Trade parameters updated (DB only)"}


class BracketModifyRequest(BaseModel):
    stop_loss: Optional[float] = None
    target: Optional[float] = None


# ─── Modify Bracket Orders (SL + Target on exchange) ─────────
@router.patch("/trades/bracket/{trade_id}")
async def modify_bracket_orders(
    trade_id: str,
    payload: BracketModifyRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Modify LIVE bracket orders for an open trade.
    Calls broker.modify_order() on the actual Zerodha SL-M and LIMIT orders,
    then syncs DB and in-memory state.
    """
    trade = db.query(Trade).filter(
        Trade.id == trade_id,
        Trade.user_id == current_user.id,
        Trade.status == TradeStatus.OPEN,
    ).first()
    if not trade:
        raise HTTPException(status_code=404, detail="Open trade not found")

    engine = _active_engines.get(current_user.id)
    if not engine:
        raise HTTPException(status_code=400, detail="Bot is not running — cannot modify live orders")

    results = {}

    # ── Modify SL-M order on exchange ──────────────────────────
    if payload.stop_loss is not None and trade.sl_order_id:
        result = engine.broker.modify_order(
            order_id=trade.sl_order_id,
            trigger_price=round(payload.stop_loss, 2)
        )
        results["sl_order"] = result
        if result.get("status") != "FAILED":
            trade.stop_loss = payload.stop_loss
            if trade.symbol in engine.open_trades:
                engine.open_trades[trade.symbol]["stop_loss"] = payload.stop_loss
        else:
            raise HTTPException(status_code=502,
                detail=f"Failed to modify SL order on exchange: {result.get('error')}")

    # ── Modify Target LIMIT order on exchange ──────────────────
    if payload.target is not None and trade.target_order_id:
        result = engine.broker.modify_order(
            order_id=trade.target_order_id,
            price=round(payload.target, 2)
        )
        results["target_order"] = result
        if result.get("status") != "FAILED":
            trade.target = payload.target
            if trade.symbol in engine.open_trades:
                engine.open_trades[trade.symbol]["target"] = payload.target
        else:
            raise HTTPException(status_code=502,
                detail=f"Failed to modify target order on exchange: {result.get('error')}")

    # ── Fallback: update DB only if no live order IDs ──────────
    if payload.stop_loss is not None and not trade.sl_order_id:
        trade.stop_loss = payload.stop_loss
        if trade.symbol in engine.open_trades:
            engine.open_trades[trade.symbol]["stop_loss"] = payload.stop_loss
        results["sl_note"] = "No live SL order — DB and memory updated only"

    if payload.target is not None and not trade.target_order_id:
        trade.target = payload.target
        if trade.symbol in engine.open_trades:
            engine.open_trades[trade.symbol]["target"] = payload.target
        results["target_note"] = "No live target order — DB and memory updated only"

    db.commit()
    return {"success": True, "trade_id": trade_id, "results": results}


# ─── Floating P&L (BUG FIX: was missing entirely) ────────────
@router.get("/trades/floating-pnl")
async def get_floating_pnl(
    current_user: User = Depends(get_current_user),
):
    """
    Returns live unrealized P&L for all open positions.
    Uses engine's broker.get_price() for real-time prices.
    Fallback: returns 0 if bot is not running.
    """
    engine = _active_engines.get(current_user.id)
    if not engine or not engine.open_trades:
        return {"total_floating_pnl": 0.0, "positions": []}

    positions = []
    total = 0.0
    for symbol, pos in engine.open_trades.items():
        try:
            current_price = engine.broker.get_fresh_price(symbol)
            if current_price <= 0:
                continue
            qty = pos.get("qty", 0)
            entry = pos.get("entry", 0)
            sig = pos.get("signal", "BUY")
            unreal = (current_price - entry) * qty if "BUY" in sig else (entry - current_price) * qty
            total += unreal
            positions.append({
                "symbol": symbol,
                "signal": sig,
                "entry_price": entry,
                "current_price": current_price,
                "quantity": qty,
                "floating_pnl": round(unreal, 2),
                "floating_pnl_pct": round((unreal / (entry * qty)) * 100, 2) if entry and qty else 0,
                "stop_loss": pos.get("stop_loss", 0),
                "target": pos.get("target", 0),
            })
        except Exception:
            pass

    return {
        "total_floating_pnl": round(total, 2),
        "positions": positions,
    }
