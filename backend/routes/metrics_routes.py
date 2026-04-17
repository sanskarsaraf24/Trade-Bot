from datetime import datetime, date

from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from database.session import get_db
from database.models import Trade, TradeStatus, User
from routes.auth import get_current_user

router = APIRouter()


def _today_range():
    today = date.today()
    start = datetime.combine(today, datetime.min.time())
    end = datetime.combine(today, datetime.max.time())
    return start, end


@router.get("/metrics/daily")
async def daily_metrics(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Today's trading metrics."""
    start, end = _today_range()
    trades = db.query(Trade).filter(
        Trade.user_id == current_user.id,
        Trade.status == TradeStatus.CLOSED,
        Trade.exit_time >= start,
        Trade.exit_time <= end,
    ).all()

    open_trades = db.query(Trade).filter(
        Trade.user_id == current_user.id,
        Trade.status == TradeStatus.OPEN,
    ).count()

    if not trades:
        return {
            "date": str(date.today()),
            "total_trades": 0,
            "winning_trades": 0,
            "losing_trades": 0,
            "win_rate": 0,
            "total_pnl": 0,
            "pnl_percent": 0,
            "largest_win": 0,
            "largest_loss": 0,
            "avg_win": 0,
            "avg_loss": 0,
            "profit_factor": 0,
            "open_positions": open_trades,
        }

    wins = [t for t in trades if t.pnl > 0]
    losses = [t for t in trades if t.pnl <= 0]
    total_pnl = sum(t.pnl for t in trades)
    gross_profit = sum(t.pnl for t in wins) if wins else 0
    gross_loss = abs(sum(t.pnl for t in losses)) if losses else 0

    # Get account balance from config
    from database.models import TradingConfiguration
    config = db.query(TradingConfiguration).filter(
        TradingConfiguration.user_id == current_user.id
    ).first()
    balance = config.account_balance if config else 100000

    return {
        "date": str(date.today()),
        "total_trades": len(trades),
        "winning_trades": len(wins),
        "losing_trades": len(losses),
        "win_rate": round(len(wins) / len(trades) * 100, 1) if trades else 0,
        "total_pnl": round(total_pnl, 2),
        "pnl_percent": round(total_pnl / balance * 100, 3) if balance else 0,
        "largest_win": round(max((t.pnl for t in wins), default=0), 2),
        "largest_loss": round(min((t.pnl for t in losses), default=0), 2),
        "avg_win": round(gross_profit / len(wins), 2) if wins else 0,
        "avg_loss": round(gross_loss / len(losses), 2) if losses else 0,
        "profit_factor": round(gross_profit / gross_loss, 2) if gross_loss > 0 else 0,
        "open_positions": open_trades,
    }


@router.get("/metrics/weekly")
async def weekly_metrics(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Last 7 days grouped by day."""
    from datetime import timedelta
    rows = []
    for i in range(6, -1, -1):
        d = date.today() - timedelta(days=i)
        start = datetime.combine(d, datetime.min.time())
        end = datetime.combine(d, datetime.max.time())
        trades = db.query(Trade).filter(
            Trade.user_id == current_user.id,
            Trade.status == TradeStatus.CLOSED,
            Trade.exit_time >= start,
            Trade.exit_time <= end,
        ).all()
        pnl = sum(t.pnl for t in trades)
        rows.append({"date": str(d), "trades": len(trades), "pnl": round(pnl, 2)})
    return rows


@router.get("/metrics/claude-accuracy")
async def claude_accuracy(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Claude AI signal accuracy statistics."""
    trades = db.query(Trade).filter(
        Trade.user_id == current_user.id,
        Trade.status == TradeStatus.CLOSED,
        Trade.confidence > 0,
    ).all()

    if not trades:
        return {"total_signals": 0, "accuracy_percent": 0}

    wins = [t for t in trades if t.pnl > 0]
    return {
        "total_signals": len(trades),
        "profitable_signals": len(wins),
        "losing_signals": len(trades) - len(wins),
        "accuracy_percent": round(len(wins) / len(trades) * 100, 1),
        "avg_confidence": round(sum(t.confidence for t in trades) / len(trades), 1),
        "avg_confidence_wins": round(sum(t.confidence for t in wins) / len(wins), 1) if wins else 0,
    }


@router.get("/logs")
async def get_logs(
    limit: int = 50,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    from database.models import SystemLog
    logs = (
        db.query(SystemLog)
        .filter(SystemLog.user_id == current_user.id)
        .order_by(SystemLog.timestamp.desc())
        .limit(limit)
        .all()
    )
    return [
        {
            "id": log.id,
            "event_type": log.event_type,
            "message": log.message,
            "severity": log.severity,
            "timestamp": log.timestamp,
        }
        for log in logs
    ]
