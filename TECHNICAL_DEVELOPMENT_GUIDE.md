
# LLM-Driven Automated Trading System
## Complete Technical Development Guide

**Project**: Automated Trading System (Indian Markets - Stocks + Options)
**Target Audience**: Senior/Lead Developer (Backend + Full-Stack)
**Timeline**: 4-6 weeks (MVP), Ongoing refinement
**Tech Stack**: React/Next.js (Frontend), Python (Backend), FastAPI/Django

---

## 🏗️ PROJECT ARCHITECTURE OVERVIEW

```
┌─────────────────────────────────────────────────────────────────┐
│                        USER (Trader)                             │
└────────────────┬────────────────────────────────────────────────┘
                 │
┌────────────────▼────────────────────────────────────────────────┐
│                    FRONTEND DASHBOARD                            │
│  (React/Next.js) - Configuration + Monitoring UI                │
└────────────────┬────────────────────────────────────────────────┘
                 │ REST API / WebSocket
┌────────────────▼────────────────────────────────────────────────┐
│                    BACKEND API SERVER                            │
│  (FastAPI/Django) - Business Logic + Risk Management            │
└────────────────┬────────────────────────────────────────────────┘
                 │
        ┌────────┴────────┬────────────┐
        │                 │            │
┌───────▼────────┐ ┌─────▼────────┐  │
│  Local Database│ │ Broker API   │  │
│  (SQLite /     │ │  (Zerodha /  │  │
│  PostgreSQL)   │ │   Angel)     │  │
└────────────────┘ └──────────────┘  │
                                     │
                        ┌────────────▼──────┐
                        │  Claude API       │
                        │  (LLM Decisions)  │
                        └───────────────────┘

┌────────────────────────────────────────────────────────────────┐
│                   TRADING ENGINE (Background)                   │
│  - Data Collection (every 5-15 min)                            │
│  - Indicator Calculation                                        │
│  - Claude Decision Loop                                         │
│  - Order Execution                                              │
│  - Trade Monitoring                                             │
│  - P&L Tracking                                                 │
└────────────────────────────────────────────────────────────────┘
```

---

## 📋 REQUIREMENTS BREAKDOWN

### **Phase 1: Configuration Dashboard (Week 1-2)**

#### **1.1 User Settings Form**

**Inputs the user enters on dashboard:**

```
┌─────────────────────────────────────────────────┐
│         TRADING BOT CONFIGURATION                │
├─────────────────────────────────────────────────┤
│                                                  │
│  ACCOUNT BASICS                                 │
│  ├─ Total Available Funds: ₹10,00,000           │
│  ├─ Daily Target Profit: ₹25,000 (2.5%)         │
│  ├─ Max Daily Loss (Stop): ₹20,000 (2%)         │
│  └─ Risk Per Trade: 1% (₹10,000)                │
│                                                  │
│  RISK APPETITE                                  │
│  ├─ Conservative  ○                             │
│  ├─ Moderate      ●                             │
│  └─ Aggressive    ○                             │
│                                                  │
│  TRADING PREFERENCES                            │
│  ├─ Trading Timeframe:                          │
│  │  ○ Scalping (5-15 min)                      │
│  │  ● Intraday (30 min - 4 hours)               │
│  │  ○ Swing (overnight)                         │
│  │                                              │
│  ├─ Market Hours to Trade:                      │
│  │  ├─ Start Time: 09:15 AM                     │
│  │  ├─ End Time: 03:15 PM (exit all by 3:25)   │
│  │  └─ ✓ Automatically close at 3:25 PM        │
│  │                                              │
│  ├─ Minimum AI Confidence Threshold: 65%        │
│  │  (Only trade if Claude confidence > this)    │
│  │                                              │
│  └─ Max Concurrent Positions: 5 (at same time) │
│                                                  │
│  SYMBOLS & MARKETS                              │
│  ├─ Markets to Trade In:                        │
│  │  ☑ NSE Stocks                                │
│  │  ☑ NSE Options (Indices)                     │
│  │  ☐ BSE Stocks                                │
│  │  ☐ MCX Commodities                           │
│  │                                              │
│  ├─ Symbol Selection Mode:                      │
│  │  ○ Manual (List symbols below)               │
│  │  ● Auto-Select (Claude chooses from list)    │
│  │  ○ Free (Claude trades ANY symbol)           │
│  │                                              │
│  ├─ If Manual: Enter Symbols                    │
│  │  TCS, INFY, RELIANCE, SBIN, BANKNIFTY       │
│  │  [Add Symbol] [Remove Symbol]                │
│  │                                              │
│  ├─ If Auto: Allowed Sectors                    │
│  │  ☑ IT        ☑ Banking    ☑ Auto            │
│  │  ☑ Pharma    ☑ FMCG       ☑ Metals          │
│  │  ☐ Energy    ☐ Telecom                       │
│  │                                              │
│  └─ Require Approval for Each Trade:            │
│     ○ Yes (Manual approval required)            │
│     ● No (Auto-execute approved signals)        │
│                                                  │
│  TRADING STRATEGY                               │
│  ├─ Focus Areas:                                │
│  │  ☑ Breakouts                                 │
│  │  ☑ Mean Reversion                            │
│  │  ☑ Trend Following                           │
│  │  ☑ Options Volatility Plays                  │
│  │  ☐ News-Based Trades                         │
│  │                                              │
│  ├─ Avoid Trading During:                       │
│  │  ☑ Earnings Week                             │
│  │  ☑ RBI/Government Announcements              │
│  │  ☑ First 15 min of market open               │
│  │  ☐ High volatility events                    │
│  │                                              │
│  └─ System Instructions (Custom Prompt):        │
│     [Text Area - 500 chars]                     │
│     "Favor mean reversion in choppy markets.    │
│      Avoid gap openings. Prefer volume          │
│      confirmation..."                           │
│                                                  │
│  API & INTEGRATIONS                             │
│  ├─ Broker:                                     │
│  │  ○ Zerodha (Recommended)                     │
│  │  ○ Angel Broking                             │
│  │  ○ Shoonya                                   │
│  │                                              │
│  ├─ Broker API Key: [****HIDDEN****]            │
│  ├─ Broker API Secret: [****HIDDEN****]         │
│  ├─ Claude API Key: [****HIDDEN****]            │
│  │                                              │
│  └─ [Test Connection] [Save Configuration]     │
│                                                  │
│  MONITORING & ALERTS                            │
│  ├─ Alert on Trade Execution: ☑                │
│  ├─ Alert on SL Hit: ☑                          │
│  ├─ Alert on Target Hit: ☑                      │
│  ├─ Daily Report Email: [email@example.com]    │
│  └─ Send Alerts via: ☑ Email  ☑ SMS  ☑ In-App  │
│                                                  │
│              [SAVE] [RESET] [START BOT]         │
└─────────────────────────────────────────────────┘
```

#### **1.2 Data Structure (Backend)**

**Configuration object stored in database:**

```python
# models/trading_config.py

class TradingConfiguration(BaseModel):
    # Account Settings
    user_id: str
    account_balance: float  # ₹10,00,000
    daily_profit_target: float  # ₹25,000
    daily_loss_limit: float  # ₹20,000
    risk_per_trade_percent: float  # 1%
    
    # Risk Profile
    risk_appetite: Enum["conservative", "moderate", "aggressive"]  # "moderate"
    
    # Trading Hours
    market_start_time: str  # "09:15"
    market_end_time: str  # "03:15"
    auto_exit_time: str  # "03:25"
    
    # Symbol Selection
    symbol_selection_mode: Enum["manual", "auto", "free"]  # "auto"
    manual_symbols: List[str]  # ["TCS", "INFY", "RELIANCE"]
    allowed_sectors: List[str]  # ["IT", "Banking", "Auto"]
    
    # Trading Parameters
    min_confidence_threshold: float  # 65 (%)
    max_concurrent_positions: int  # 5
    timeframe: Enum["scalp", "intraday", "swing"]  # "intraday"
    
    # Market Selection
    markets_enabled: Dict[str, bool]  # {"NSE_STOCKS": true, "NSE_OPTIONS": true}
    
    # Strategy Preferences
    enabled_strategies: List[str]  # ["breakouts", "mean_reversion", "trend"]
    avoid_trading_during: List[str]  # ["earnings", "rbi_announcement"]
    
    # Approval Requirements
    require_manual_approval: bool  # false
    
    # Custom Instructions
    system_instructions: str  # "Favor mean reversion..."
    
    # Integrations
    broker_type: str  # "zerodha"
    broker_api_key: str  # encrypted
    broker_api_secret: str  # encrypted
    claude_api_key: str  # encrypted
    
    # Alerts
    email_alerts_enabled: bool
    sms_alerts_enabled: bool
    email_address: str
    phone_number: str
    
    # Metadata
    created_at: datetime
    updated_at: datetime
    is_active: bool
    
    class Config:
        schema_extra = {
            "example": {
                "account_balance": 1000000,
                "daily_profit_target": 25000,
                "risk_per_trade_percent": 1.0,
                "min_confidence_threshold": 65,
                "max_concurrent_positions": 5
            }
        }
```

---

### **Phase 2: Live Trading Dashboard (Week 2-3)**

#### **2.1 Dashboard Displays (Real-Time)**

**Once bot is running, user sees:**

```
┌──────────────────────────────────────────────────────────────┐
│              LIVE TRADING DASHBOARD                           │
├──────────────────────────────────────────────────────────────┤
│                                                               │
│  TOP METRICS BAR                                             │
│  ├─ Account Balance: ₹10,00,000                              │
│  ├─ Today's P&L: +₹18,750 (1.875%) 📈                        │
│  ├─ Daily Target: ₹25,000 (75% reached)                      │
│  ├─ Open Positions: 3/5                                      │
│  └─ Last Update: 2024-01-15 10:35 AM                         │
│                                                               │
│  STATUS INDICATORS                                           │
│  ├─ Bot Status: ✓ RUNNING (Green light)                      │
│  ├─ Market Status: ✓ OPEN                                    │
│  ├─ Broker Connection: ✓ CONNECTED                           │
│  └─ Claude API: ✓ HEALTHY                                    │
│                                                               │
│  OPEN TRADES (Real-time)                                     │
│  ┌────────────────────────────────────────────────────────┐  │
│  │ Symbol | Entry | Current | P&L | Duration | Status    │  │
│  ├────────────────────────────────────────────────────────┤  │
│  │ TCS    │3,845  │ 3,820   │-₹3,750 (0.6%) │ 45 min  │  │
│  │        │ SELL  │ ↓       │ -1.8%  │ SL: 3,860      │  │
│  │        │       │         │        │ Target: 3,790  │  │
│  │        │       │         │        │ Confidence: 75%│  │
│  ├────────────────────────────────────────────────────────┤  │
│  │ INFY   │ 2,100 │ 2,105   │ +₹500 (1.2%)  │ 20 min  │  │
│  │        │ BUY   │ ↑       │ +0.24% │ SL: 2,090       │  │
│  │        │       │         │        │ Target: 2,150   │  │
│  │        │       │         │        │ Confidence: 68% │  │
│  ├────────────────────────────────────────────────────────┤  │
│  │ BANKNIFTY CALL (52000)                                  │  │
│  │        │ ₹250  │ ₹265    │ +₹3,000 (2.4%)│ 35 min  │  │
│  │        │ BUY   │ ↑       │ +6%    │ SL: ₹200        │  │
│  │        │       │         │        │ Target: ₹320    │  │
│  │        │       │         │        │ Confidence: 82% │  │
│  └────────────────────────────────────────────────────────┘  │
│  [Exit All] [Refresh] [View Details]                         │
│                                                               │
│  RECENT TRADES (Today Completed)                            │
│  ┌────────────────────────────────────────────────────────┐  │
│  │ CLOSED │ Time   │ Entry  │ Exit   │ P&L      │ Type  │  │
│  ├────────────────────────────────────────────────────────┤  │
│  │ RELIANCE│ 09:45 │3,270 │3,280 │ +₹2,500 │ ✓ WIN  │  │
│  │ SBIN   │ 10:10 │ 680  │ 675  │ -₹1,000 │ ✗ LOSS │  │
│  │ HDFCBANK│ 10:55 │1,850│1,860│ +₹5,000 │ ✓ WIN  │  │
│  │ WIPRO  │ 11:30 │ 420  │ 415  │ -₹2,500 │ ✗ LOSS │  │
│  │ MARUTI │ 12:00 │8,100│8,150│ +₹3,000 │ ✓ WIN  │  │
│  └────────────────────────────────────────────────────────┘  │
│                                                               │
│  DAILY STATISTICS                                            │
│  ├─ Total Trades: 8                                          │
│  ├─ Win Rate: 62.5% (5/8)                                    │
│  ├─ Avg Win: ₹3,500                                          │
│  ├─ Avg Loss: ₹1,750                                         │
│  ├─ Best Trade: BANKNIFTY (+₹3,000)                          │
│  ├─ Worst Trade: SBIN (-₹1,000)                              │
│  └─ Profit Factor: 2.3x (Good)                               │
│                                                               │
│  SYSTEM LOG (Last 10 events)                                 │
│  ├─ 10:45 AM - Trade closed: INFY +₹500                      │
│  ├─ 10:42 AM - Claude signal: TCS SELL (Confidence: 75%)    │
│  ├─ 10:40 AM - New trade opened: INFY BUY                    │
│  ├─ 10:35 AM - SL hit: SBIN -₹1,000 (Exit)                   │
│  ├─ 10:30 AM - Claude signal: RELIANCE BUY (Confidence: 58%) │
│  ├─ 10:30 AM - Signal skipped (Confidence < 60%)             │
│  ├─ 10:25 AM - Data refresh complete                         │
│  ├─ 10:20 AM - Trade closed: RELIANCE +₹2,500                │
│  ├─ 10:15 AM - New trade: BANKNIFTY CALL BUY                 │
│  └─ 10:10 AM - Bot running normally                          │
│                                                               │
│  NEXT ACTIONS                                                │
│  ├─ Next data refresh: in 5 min (10:50 AM)                   │
│  ├─ Next Claude analysis: 5 symbols queued                   │
│  └─ [Pause Bot] [Stop Bot] [Settings]                        │
│                                                               │
└──────────────────────────────────────────────────────────────┘
```

#### **2.2 Real-Time Data Updates**

**WebSocket connection for live updates:**

```python
# routes/websocket.py

from fastapi import WebSocket, WebSocketDisconnect
import json
import asyncio

class TradingWebSocketManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
    
    async def connect(self, websocket: WebSocket, user_id: str):
        await websocket.accept()
        self.active_connections.append({
            'websocket': websocket,
            'user_id': user_id
        })
    
    async def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)
    
    async def broadcast_trade_update(self, trade_data: dict):
        """Send when trade is opened/updated/closed"""
        message = {
            "type": "trade_update",
            "data": trade_data,
            "timestamp": datetime.now().isoformat()
        }
        for conn in self.active_connections:
            await conn['websocket'].send_json(message)
    
    async def broadcast_metrics_update(self, metrics: dict):
        """Send updated P&L, balance, etc every 30 sec"""
        message = {
            "type": "metrics_update",
            "data": metrics,
            "timestamp": datetime.now().isoformat()
        }
        for conn in self.active_connections:
            await conn['websocket'].send_json(message)
    
    async def broadcast_log_event(self, event: str):
        """Send system log events in real-time"""
        message = {
            "type": "log_event",
            "message": event,
            "timestamp": datetime.now().isoformat()
        }
        for conn in self.active_connections:
            await conn['websocket'].send_json(message)

# Usage in trading engine:
# await ws_manager.broadcast_trade_update({
#     'symbol': 'TCS',
#     'signal': 'SELL',
#     'entry': 3845,
#     'status': 'OPEN',
#     'pnl': -3750
# })
```

---

### **Phase 3: Backend Trading Engine (Week 1-3, Parallel)**

#### **3.1 Core API Endpoints**

**All endpoints the frontend needs:**

```python
# routes/api.py

from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from models.trading_config import TradingConfiguration
from models.trade import Trade, TradeSignal
from services.trading_engine import TradingEngine
from services.broker_connector import BrokerConnector
from services.claude_service import ClaudeService

router = APIRouter(prefix="/api", tags=["trading"])

# ═══════════════════════════════════════════════════════════
# CONFIGURATION ENDPOINTS
# ═══════════════════════════════════════════════════════════

@router.post("/config/save")
async def save_configuration(config: TradingConfiguration, user_id: str):
    """
    Save user's trading configuration
    
    Request Body:
    {
        "account_balance": 1000000,
        "daily_profit_target": 25000,
        "daily_loss_limit": 20000,
        "risk_per_trade_percent": 1.0,
        "risk_appetite": "moderate",
        "market_start_time": "09:15",
        "market_end_time": "03:15",
        "symbol_selection_mode": "auto",
        "manual_symbols": ["TCS", "INFY"],
        "allowed_sectors": ["IT", "Banking"],
        "min_confidence_threshold": 65,
        "max_concurrent_positions": 5,
        "require_manual_approval": false,
        ... (all other fields)
    }
    
    Response:
    {
        "success": true,
        "message": "Configuration saved successfully",
        "config_id": "cfg_12345"
    }
    """
    try:
        saved_config = db.save_config(user_id, config)
        return {"success": True, "config_id": saved_config.id}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/config/get/{user_id}")
async def get_configuration(user_id: str):
    """
    Retrieve user's current configuration
    
    Response:
    {
        "account_balance": 1000000,
        "daily_profit_target": 25000,
        ... (all config fields)
    }
    """
    config = db.get_config(user_id)
    if not config:
        raise HTTPException(status_code=404, detail="Configuration not found")
    return config

@router.post("/config/test-connection")
async def test_broker_connection(broker_type: str, api_key: str, api_secret: str):
    """
    Test broker API connection before saving
    
    Response:
    {
        "success": true,
        "message": "Connected to Zerodha API",
        "account_balance": 1000000
    }
    """
    try:
        broker = BrokerConnector(broker_type, api_key, api_secret)
        balance = broker.get_account_balance()
        return {"success": True, "account_balance": balance}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Connection failed: {str(e)}")

# ═══════════════════════════════════════════════════════════
# BOT CONTROL ENDPOINTS
# ═══════════════════════════════════════════════════════════

@router.post("/bot/start")
async def start_trading_bot(user_id: str, background_tasks: BackgroundTasks):
    """
    Start the trading bot
    
    Response:
    {
        "success": true,
        "message": "Trading bot started",
        "bot_id": "bot_12345"
    }
    
    Backend:
    - Load user config
    - Validate all settings
    - Start trading engine in background task
    - Begin data collection loop
    - Start Claude analysis loop
    """
    try:
        config = db.get_config(user_id)
        engine = TradingEngine(config)
        
        # Start trading engine in background
        background_tasks.add_task(engine.run_trading_loop)
        
        # Store bot instance
        db.save_bot_session(user_id, engine.bot_id, "running")
        
        return {
            "success": True,
            "bot_id": engine.bot_id,
            "message": "Trading bot started successfully"
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/bot/pause")
async def pause_trading_bot(user_id: str):
    """Pause bot (don't close positions, just stop new trades)"""
    engine = get_active_engine(user_id)
    engine.pause()
    db.update_bot_status(user_id, "paused")
    return {"success": True, "message": "Bot paused"}

@router.post("/bot/stop")
async def stop_trading_bot(user_id: str):
    """
    Stop bot and close all open positions
    
    Response:
    {
        "success": true,
        "message": "Bot stopped and all positions closed",
        "positions_closed": 3,
        "final_pnl": 18750
    }
    """
    engine = get_active_engine(user_id)
    closed_trades = engine.close_all_positions()
    engine.stop()
    db.update_bot_status(user_id, "stopped")
    return {
        "success": True,
        "positions_closed": len(closed_trades),
        "message": "Bot stopped"
    }

@router.get("/bot/status/{user_id}")
async def get_bot_status(user_id: str):
    """
    Get current bot status
    
    Response:
    {
        "bot_id": "bot_12345",
        "status": "running",
        "uptime_seconds": 3600,
        "last_update": "2024-01-15T10:45:00",
        "open_positions": 3,
        "todays_pnl": 18750,
        "pnl_percent": 1.875
    }
    """
    session = db.get_bot_session(user_id)
    engine = get_active_engine(user_id)
    
    return {
        "bot_id": session.bot_id,
        "status": session.status,
        "uptime_seconds": (datetime.now() - session.started_at).total_seconds(),
        "last_update": engine.last_update,
        "open_positions": len(engine.open_trades),
        "todays_pnl": engine.calculate_todays_pnl(),
        "pnl_percent": (engine.calculate_todays_pnl() / config.account_balance) * 100
    }

# ═══════════════════════════════════════════════════════════
# TRADES ENDPOINTS (Live Data)
# ═══════════════════════════════════════════════════════════

@router.get("/trades/open/{user_id}")
async def get_open_trades(user_id: str):
    """
    Get all currently open trades
    
    Response:
    [
        {
            "trade_id": "TRD_001",
            "symbol": "TCS",
            "signal": "SELL",
            "entry_price": 3845,
            "current_price": 3820,
            "pnl": -3750,
            "pnl_percent": -0.97,
            "duration_minutes": 45,
            "entry_time": "2024-01-15T10:00:00",
            "stop_loss": 3860,
            "target": 3790,
            "confidence": 75,
            "status": "OPEN",
            "reason": "Overbought at resistance"
        }
    ]
    """
    engine = get_active_engine(user_id)
    open_trades = db.get_open_trades(user_id)
    
    result = []
    for trade in open_trades:
        current_price = engine.broker.get_price(trade.symbol)
        pnl = calculate_pnl(trade, current_price)
        
        result.append({
            "trade_id": trade.id,
            "symbol": trade.symbol,
            "signal": trade.signal,
            "entry_price": trade.entry_price,
            "current_price": current_price,
            "pnl": pnl,
            "pnl_percent": (pnl / (trade.entry_price * trade.quantity)) * 100,
            "duration_minutes": (datetime.now() - trade.entry_time).total_seconds() / 60,
            "entry_time": trade.entry_time,
            "stop_loss": trade.stop_loss,
            "target": trade.target,
            "confidence": trade.confidence,
            "status": "OPEN",
            "reason": trade.claude_reasoning
        })
    
    return result

@router.get("/trades/closed/{user_id}")
async def get_closed_trades(user_id: str, limit: int = 20):
    """Get today's closed trades (paginated)"""
    trades = db.get_closed_trades(user_id, limit=limit)
    return trades

@router.post("/trades/manual-exit/{trade_id}")
async def manual_exit_trade(trade_id: str, user_id: str):
    """
    Manually exit a specific trade
    
    Response:
    {
        "success": true,
        "trade_id": "TRD_001",
        "exit_price": 3825,
        "pnl": -3000,
        "message": "Trade closed manually"
    }
    """
    trade = db.get_trade(trade_id)
    engine = get_active_engine(user_id)
    
    exit_price = engine.broker.get_price(trade.symbol)
    engine.exit_trade(trade_id, exit_price, "MANUAL_EXIT")
    
    pnl = calculate_pnl(trade, exit_price)
    
    return {
        "success": True,
        "trade_id": trade_id,
        "exit_price": exit_price,
        "pnl": pnl,
        "message": "Trade closed manually"
    }

@router.post("/trades/exit-all/{user_id}")
async def exit_all_trades(user_id: str):
    """Exit all open positions immediately"""
    engine = get_active_engine(user_id)
    closed_trades = engine.close_all_positions()
    
    return {
        "success": True,
        "trades_closed": len(closed_trades),
        "total_pnl": sum([t['pnl'] for t in closed_trades]),
        "message": f"Closed {len(closed_trades)} positions"
    }

# ═══════════════════════════════════════════════════════════
# METRICS & ANALYTICS ENDPOINTS
# ═══════════════════════════════════════════════════════════

@router.get("/metrics/daily/{user_id}")
async def get_daily_metrics(user_id: str):
    """
    Get today's trading metrics
    
    Response:
    {
        "date": "2024-01-15",
        "total_trades": 8,
        "winning_trades": 5,
        "losing_trades": 3,
        "win_rate": 0.625,
        "total_pnl": 18750,
        "pnl_percent": 1.875,
        "largest_win": 5000,
        "largest_loss": 2500,
        "avg_win": 3500,
        "avg_loss": 1750,
        "profit_factor": 2.3,
        "account_balance": 1018750,
        "max_drawdown": 0.015
    }
    """
    metrics = db.calculate_daily_metrics(user_id)
    return metrics

@router.get("/metrics/weekly/{user_id}")
async def get_weekly_metrics(user_id: str):
    """Weekly performance summary"""
    pass

@router.get("/metrics/claude-accuracy/{user_id}")
async def get_claude_accuracy(user_id: str):
    """
    Claude AI signal accuracy
    
    Response:
    {
        "total_signals": 40,
        "profitable_signals": 28,
        "losing_signals": 12,
        "accuracy_percent": 70,
        "best_performing_setup": "Breakouts",
        "best_accuracy": 78,
        "worst_performing_setup": "Mean Reversion",
        "worst_accuracy": 55
    }
    """
    pass

# ═══════════════════════════════════════════════════════════
# LOGS ENDPOINTS
# ═══════════════════════════════════════════════════════════

@router.get("/logs/{user_id}")
async def get_system_logs(user_id: str, limit: int = 50):
    """
    Get system event logs (last N events)
    
    Response:
    [
        {
            "timestamp": "2024-01-15T10:45:00",
            "event_type": "trade_closed",
            "message": "Trade closed: INFY +₹500",
            "severity": "info"
        },
        {
            "timestamp": "2024-01-15T10:42:00",
            "event_type": "signal_generated",
            "message": "Claude signal: TCS SELL (Confidence: 75%)",
            "severity": "info"
        }
    ]
    """
    logs = db.get_logs(user_id, limit=limit)
    return logs

@router.post("/logs/clear/{user_id}")
async def clear_logs(user_id: str):
    """Clear all logs for the user"""
    db.clear_logs(user_id)
    return {"success": True, "message": "Logs cleared"}

# ═══════════════════════════════════════════════════════════
# APPROVAL ENDPOINTS (if manual approval enabled)
# ═══════════════════════════════════════════════════════════

@router.get("/approvals/pending/{user_id}")
async def get_pending_approvals(user_id: str):
    """
    Get signals waiting for user approval
    
    Response:
    [
        {
            "approval_id": "APR_001",
            "signal": {
                "symbol": "TCS",
                "action": "SELL",
                "entry": 3845,
                "stop_loss": 3860,
                "target": 3790,
                "confidence": 75,
                "reasoning": "Overbought at resistance..."
            },
            "created_at": "2024-01-15T10:42:00"
        }
    ]
    """
    pass

@router.post("/approvals/approve/{approval_id}")
async def approve_trade(approval_id: str, user_id: str):
    """User approves a trade signal"""
    pass

@router.post("/approvals/reject/{approval_id}")
async def reject_trade(approval_id: str, user_id: str, reason: str):
    """User rejects a trade signal"""
    pass

# ═══════════════════════════════════════════════════════════
# EXPORT ENDPOINTS
# ═══════════════════════════════════════════════════════════

@router.get("/export/daily-report/{user_id}")
async def export_daily_report(user_id: str):
    """
    Export daily report as PDF or CSV
    
    Returns: PDF or CSV file
    """
    pass

@router.get("/export/trades-csv/{user_id}")
async def export_trades_csv(user_id: str, start_date: str, end_date: str):
    """Export trades in date range as CSV"""
    pass
```

#### **3.2 Background Trading Engine**

**The core loop that runs continuously:**

```python
# services/trading_engine.py

import asyncio
from datetime import datetime, time
from services.broker_connector import BrokerConnector
from services.claude_service import ClaudeService
from services.risk_manager import RiskManager
from database import Database

class TradingEngine:
    def __init__(self, config: TradingConfiguration):
        self.config = config
        self.broker = BrokerConnector(config.broker_type, config.broker_api_key, config.broker_api_secret)
        self.claude = ClaudeService(config.claude_api_key)
        self.risk_manager = RiskManager(config)
        self.db = Database()
        
        self.is_running = False
        self.is_paused = False
        self.open_trades = {}
        self.last_update = None
        self.bot_id = str(uuid.uuid4())
    
    async def run_trading_loop(self):
        """
        Main trading loop - runs continuously during market hours
        Executes every 5-15 minutes (configurable)
        """
        self.is_running = True
        
        while self.is_running:
            try:
                # Check if market is open
                if not self.is_market_open():
                    await asyncio.sleep(60)  # Check again in 1 min
                    continue
                
                # Check if we should exit (within 5 min of market close)
                if self.is_near_market_close():
                    self.close_all_positions()
                    self.is_running = False
                    break
                
                # Step 1: Data Collection
                market_data = await self.collect_market_data()
                
                # Step 2: Feature Engineering
                features = await self.engineer_features(market_data)
                
                # Step 3: Claude Decision Making
                signals = await self.get_claude_signals(features)
                
                # Step 4: Risk Validation
                validated_signals = self.risk_manager.validate_signals(signals)
                
                # Step 5: Order Execution
                for signal in validated_signals:
                    await self.execute_trade(signal)
                
                # Step 6: Monitor Open Trades
                await self.monitor_open_trades()
                
                # Step 7: Update Database & Broadcast
                self.last_update = datetime.now()
                await self.broadcast_status_update()
                
                # Sleep until next cycle (default 5 min)
                await asyncio.sleep(self.config.analysis_interval * 60)
                
            except Exception as e:
                logger.error(f"Trading loop error: {str(e)}")
                await self.log_event("error", f"Trading error: {str(e)}")
                await asyncio.sleep(30)  # Wait before retry
    
    async def collect_market_data(self) -> dict:
        """
        Fetch live market data for all symbols
        """
        symbols = self.get_symbols_to_trade()
        market_data = {}
        
        for symbol in symbols:
            try:
                # Current candle
                candle = self.broker.get_latest_candle(symbol)
                
                # Historical data (last 100 candles)
                history = self.broker.get_ohlcv(symbol, bars=100)
                
                # Options data (if trading options)
                options_data = None
                if self.config.markets_enabled.get("NSE_OPTIONS"):
                    options_data = self.broker.get_option_chain(symbol)
                
                market_data[symbol] = {
                    'current_candle': candle,
                    'history': history,
                    'options': options_data,
                    'timestamp': datetime.now()
                }
            except Exception as e:
                logger.warning(f"Failed to fetch data for {symbol}: {str(e)}")
                continue
        
        return market_data
    
    async def engineer_features(self, market_data: dict) -> dict:
        """
        Calculate technical indicators and generate narratives
        """
        features = {}
        
        for symbol, data in market_data.items():
            try:
                history = data['history']
                
                # Calculate indicators
                indicators = {
                    'sma_20': self.calculate_sma(history, 20),
                    'sma_50': self.calculate_sma(history, 50),
                    'sma_200': self.calculate_sma(history, 200),
                    'rsi': self.calculate_rsi(history, 14),
                    'macd': self.calculate_macd(history),
                    'bollinger_bands': self.calculate_bollinger(history),
                    'atr': self.calculate_atr(history),
                    'volume_trend': self.calculate_volume_trend(history),
                }
                
                # Current price and position
                current_price = data['current_candle']['close']
                
                # Generate narrative description
                narrative = self.generate_narrative(symbol, indicators, current_price)
                
                features[symbol] = {
                    'indicators': indicators,
                    'current_price': current_price,
                    'narrative': narrative,
                    'options_data': data['options'] if data['options'] else None
                }
            except Exception as e:
                logger.warning(f"Feature engineering failed for {symbol}: {str(e)}")
                continue
        
        return features
    
    async def get_claude_signals(self, features: dict) -> list:
        """
        Call Claude API to get trade signals
        """
        signals = []
        
        # Batch symbols to save API calls (3-5 per call)
        batches = self.batch_symbols(features.keys(), batch_size=5)
        
        for batch in batches:
            try:
                # Build prompt
                prompt = self.build_claude_prompt(batch, features)
                
                # Call Claude
                response = self.claude.get_analysis(prompt)
                
                # Parse response
                batch_signals = self.parse_claude_response(response)
                signals.extend(batch_signals)
                
            except Exception as e:
                logger.error(f"Claude API call failed: {str(e)}")
                continue
        
        return signals
    
    def build_claude_prompt(self, symbols: list, features: dict) -> str:
        """
        Build the prompt to send to Claude
        """
        prompt = f"""You are an expert Indian market trader. Analyze these {len(symbols)} symbols and provide trade signals.

System Instructions:
{self.config.system_instructions}

Current Account State:
- Balance: ₹{self.config.account_balance:,.0f}
- Open Positions: {len(self.open_trades)}
- Max Positions: {self.config.max_concurrent_positions}
- Risk Per Trade: ₹{self.config.account_balance * self.config.risk_per_trade_percent / 100:,.0f}

SYMBOLS TO ANALYZE:
"""
        for symbol in symbols:
            feat = features[symbol]
            prompt += f"""
{symbol}:
- Current Price: ₹{feat['current_price']:,.2f}
- Description: {feat['narrative']}
- IV Level: {feat.get('iv_percentile', 'N/A')}
"""
        
        prompt += f"""

For each symbol, respond ONLY with valid JSON (no markdown, no backticks):
{{
  "{symbols[0]}": {{
    "signal": "BUY_STOCK or SELL_STOCK or BUY_CALL or BUY_PUT or HOLD or EXIT",
    "confidence": 0-100,
    "reasoning": "Your analysis here",
    "entry_level": price,
    "stop_loss": price,
    "target": price,
    "position_size": "qty recommendation",
    "risk_reward": "1:X ratio"
  }}
}}

Constraints:
- Only suggest signals with confidence > {self.config.min_confidence_threshold}%
- Respect max {self.config.max_concurrent_positions} open positions
- Avoid trading windows: {', '.join(self.config.avoid_trading_during)}
- Must be valid JSON only"""
        
        return prompt
    
    async def execute_trade(self, signal: dict):
        """
        Validate signal and execute order
        """
        symbol = signal['symbol']
        
        try:
            # Final risk check
            if not self.risk_manager.can_execute(signal):
                await self.log_event("warning", f"Signal skipped for {symbol}: Risk check failed")
                return
            
            # Calculate position size
            qty = self.risk_manager.calculate_position_size(
                symbol,
                signal['entry_level'],
                signal['stop_loss']
            )
            
            # Place main order
            main_order = self.broker.place_order(
                symbol=symbol,
                action=signal['signal'],  # BUY/SELL
                quantity=qty,
                order_type="LIMIT",
                price=signal['entry_level']
            )
            
            # Place stop-loss order
            sl_order = self.broker.place_order(
                symbol=symbol,
                action="SELL" if signal['signal'] == "BUY" else "BUY",
                quantity=qty,
                order_type="STOP_LOSS_LIMIT",
                stop_price=signal['stop_loss'],
                limit_price=signal['stop_loss'] + (5 if signal['signal'] == "BUY" else -5)
            )
            
            # Place target order (optional)
            target_order = self.broker.place_order(
                symbol=symbol,
                action="SELL" if signal['signal'] == "BUY" else "BUY",
                quantity=qty,
                order_type="LIMIT",
                price=signal['target']
            )
            
            # Log trade
            trade = Trade(
                symbol=symbol,
                signal=signal['signal'],
                entry_price=signal['entry_level'],
                stop_loss=signal['stop_loss'],
                target=signal['target'],
                quantity=qty,
                confidence=signal['confidence'],
                claude_reasoning=signal['reasoning'],
                entry_time=datetime.now(),
                main_order_id=main_order['order_id'],
                sl_order_id=sl_order['order_id'],
                target_order_id=target_order['order_id']
            )
            
            self.db.save_trade(trade)
            self.open_trades[symbol] = trade
            
            await self.log_event("trade_opened", f"Opened {signal['signal']} on {symbol} @ ₹{signal['entry_level']}")
            await self.broadcast_trade_update(trade)
            
        except Exception as e:
            logger.error(f"Trade execution failed for {symbol}: {str(e)}")
            await self.log_event("error", f"Execution error on {symbol}: {str(e)}")
    
    async def monitor_open_trades(self):
        """
        Monitor open trades and check for exits (SL/Target hits)
        """
        for symbol, trade in list(self.open_trades.items()):
            try:
                current_price = self.broker.get_price(symbol)
                pnl = self.calculate_pnl(trade, current_price)
                
                # Check if SL hit
                if trade.signal == "BUY" and current_price <= trade.stop_loss:
                    await self.exit_trade(trade.id, current_price, "SL_HIT")
                elif trade.signal == "SELL" and current_price >= trade.stop_loss:
                    await self.exit_trade(trade.id, current_price, "SL_HIT")
                
                # Check if Target hit
                elif trade.signal == "BUY" and current_price >= trade.target:
                    await self.exit_trade(trade.id, current_price, "TARGET_HIT")
                elif trade.signal == "SELL" and current_price <= trade.target:
                    await self.exit_trade(trade.id, current_price, "TARGET_HIT")
                
                # Update P&L in DB
                self.db.update_trade_pnl(trade.id, pnl)
                
            except Exception as e:
                logger.warning(f"Monitor failed for {symbol}: {str(e)}")
    
    async def exit_trade(self, trade_id: str, exit_price: float, reason: str):
        """Close a trade"""
        trade = self.db.get_trade(trade_id)
        pnl = self.calculate_pnl(trade, exit_price)
        
        self.db.close_trade(trade_id, {
            'exit_price': exit_price,
            'exit_reason': reason,
            'exit_time': datetime.now(),
            'pnl': pnl,
            'status': 'CLOSED'
        })
        
        del self.open_trades[trade.symbol]
        
        await self.log_event("trade_closed", f"Closed {trade.symbol}: {reason}, P&L: ₹{pnl}")
        await self.broadcast_trade_update(trade)
    
    def close_all_positions(self) -> list:
        """Close all open trades immediately"""
        closed = []
        for symbol, trade in list(self.open_trades.items()):
            current_price = self.broker.get_price(symbol)
            self.exit_trade(trade.id, current_price, "MANUAL_CLOSE")
            closed.append(trade)
        return closed
    
    def is_market_open(self) -> bool:
        """Check if NSE is open (9:15 AM - 3:30 PM IST)"""
        now = datetime.now(IST)
        market_open = time(9, 15)
        market_close = time(15, 30)
        
        # Check if weekday (Mon-Fri)
        if now.weekday() >= 5:  # Saturday = 5, Sunday = 6
            return False
        
        return market_open <= now.time() <= market_close
    
    def is_near_market_close(self) -> bool:
        """Check if within 5 minutes of market close"""
        now = datetime.now(IST)
        market_close = time(15, 25)
        return now.time() >= market_close
    
    async def broadcast_status_update(self):
        """Send updated metrics to all connected WebSocket clients"""
        metrics = {
            'account_balance': self.config.account_balance,
            'todays_pnl': self.calculate_todays_pnl(),
            'open_positions': len(self.open_trades),
            'last_update': datetime.now().isoformat()
        }
        await ws_manager.broadcast_metrics_update(metrics)
    
    async def log_event(self, event_type: str, message: str):
        """Log system event and broadcast to dashboard"""
        log_entry = {
            'timestamp': datetime.now(),
            'event_type': event_type,
            'message': message,
            'severity': 'info' if event_type != 'error' else 'error'
        }
        self.db.save_log(log_entry)
        await ws_manager.broadcast_log_event(message)
    
    def pause(self):
        """Pause trading (don't execute new trades)"""
        self.is_paused = True
    
    def resume(self):
        """Resume trading"""
        self.is_paused = False
    
    def stop(self):
        """Stop the trading engine"""
        self.is_running = False

# ─────────────────────────────────────────────
# HELPER FUNCTIONS
# ─────────────────────────────────────────────

def calculate_sma(candles, period):
    """Simple Moving Average"""
    closes = [c['close'] for c in candles[-period:]]
    return sum(closes) / len(closes) if len(closes) == period else None

def calculate_rsi(candles, period):
    """Relative Strength Index"""
    # Standard RSI calculation
    pass

def calculate_macd(candles):
    """MACD indicator"""
    pass

def calculate_atr(candles):
    """Average True Range"""
    pass

def calculate_pnl(trade, current_price):
    """Calculate P&L for a trade"""
    if trade.signal == "BUY":
        return (current_price - trade.entry_price) * trade.quantity
    else:  # SELL
        return (trade.entry_price - current_price) * trade.quantity

def calculate_todays_pnl(self):
    """Sum of all closed trades today"""
    closed_today = self.db.get_closed_trades_today(self.config.user_id)
    return sum([t['pnl'] for t in closed_today])
```

---

## 🛠️ TECH STACK DETAILS

### **Frontend**

```yaml
Framework: React 18 + Next.js 14
- Routing: Next.js App Router
- Build: Vercel, self-hosted, or Docker

UI Library: Tailwind CSS + shadcn/ui
- For clean, professional dashboard
- Customizable, production-ready components

State Management: Zustand or Redux Toolkit
- Manage: config, live trades, metrics, logs
- Real-time state updates from WebSocket

Real-time Communication:
- WebSocket (Socket.io or native WebSocket)
- For live trade updates, P&L, system logs

Charts & Visualizations:
- Recharts or Chart.js
- Display: Daily P&L, win rate, trade history

Forms & Validation:
- React Hook Form + Zod
- Type-safe form handling

API Integration:
- Axios or TanStack Query (React Query)
- Manage API calls to backend, caching

Environment:
- Node.js 18+
- npm or yarn

Deployment:
- Vercel (recommended for Next.js)
- AWS EC2 / Render
- Docker container
```

### **Backend**

```yaml
Framework: FastAPI (Python 3.11+)
- Async-first, very fast
- Auto API documentation (Swagger)
- Easy integration with Claude API

Database:
- Primary: PostgreSQL (production)
  * Tables: users, configurations, trades, logs
  * Time-series data: trades, daily metrics
- Cache: Redis (optional, for WebSocket sessions)

Broker Integration:
- Library: Python broker APIs
  * Zerodha: py_voicetrader or native
  * Angel: Angel Broking SDK
  * Shoonya: NorenRestApiPy

Technical Analysis:
- TA-Lib or pandas_ta
- For indicator calculation

LLM Integration:
- anthropic Python SDK
- For Claude API calls

Async Task Queue (Optional):
- Celery + Redis
- For background data collection, historical backtesting
- If not needed initially, use FastAPI background tasks

API Security:
- JWT for user authentication
- API key encryption for broker/Claude keys
- Rate limiting (for API endpoints)

Logging:
- Python logging module
- Structured logging to files/database

Deployment:
- Docker container
- AWS ECR / GCP Cloud Run / DigitalOcean
- Self-hosted Linux VPS (recommended)
- Run 24/5 in background during market hours

Code Structure:
```
backend/
├── main.py                 # FastAPI app entry
├── config.py              # Settings, env variables
├── routes/                # API endpoints
│   ├── api.py            # /api/* endpoints
│   ├── websocket.py      # /ws/* websocket
│   └── health.py         # /health check
├── models/               # Pydantic models
│   ├── trading_config.py
│   ├── trade.py
│   └── user.py
├── services/            # Business logic
│   ├── trading_engine.py
│   ├── broker_connector.py
│   ├── claude_service.py
│   ├── risk_manager.py
│   └── indicators.py
├── database/           # Database models & queries
│   ├── models.py      # SQLAlchemy models
│   └── queries.py
├── utils/             # Helper functions
│   ├── calculations.py
│   └── validators.py
├── logs/              # Log files
└── requirements.txt
```

```

---

## 🔐 SECURITY REQUIREMENTS

### **Critical Security Measures**

```python
# 1. API Key Storage (NEVER expose)
# Use environment variables or secure vaults

from fastapi import APIRouter, Depends
from fastapi.security import HTTPBearer, HTTPAuthCredential
import os
from dotenv import load_dotenv

load_dotenv()

CLAUDE_API_KEY = os.getenv("CLAUDE_API_KEY")  # From .env
BROKER_API_KEY = os.getenv("BROKER_API_KEY")  # Encrypted

# 2. User Authentication
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from datetime import datetime, timedelta
import bcrypt

security = OAuth2PasswordBearer(tokenUrl="token")

def create_access_token(data: dict, expires_delta: timedelta | None = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(hours=24)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, os.getenv("SECRET_KEY"), algorithm="HS256")
    return encoded_jwt

async def get_current_user(token: str = Depends(security)):
    try:
        payload = jwt.decode(token, os.getenv("SECRET_KEY"), algorithms=["HS256"])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise HTTPException(status_code=401, detail="Invalid token")
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")
    return user_id

# 3. Input Validation
from pydantic import BaseModel, Field, validator

class TradingConfiguration(BaseModel):
    account_balance: float = Field(..., gt=0, le=10000000)  # Max ₹1 crore
    daily_profit_target: float = Field(..., gt=0)
    risk_per_trade_percent: float = Field(..., gt=0, le=5)  # Max 5% per trade
    
    @validator('account_balance')
    def validate_balance(cls, v):
        if v < 10000:  # Min ₹10,000
            raise ValueError('Minimum ₹10,000 required')
        return v

# 4. Rate Limiting
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter

@router.get("/api/status")
@limiter.limit("5/minute")
async def get_status(request: Request):
    # Can only be called 5 times per minute
    pass

# 5. CORS (Restrict to your domain)
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://yourdomain.com"],  # Only your domain
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

# 6. Trade Approval (prevent accidental trades)
REQUIRE_APPROVAL_FOR_TRADES = True  # Override in config

@router.post("/api/config/save")
async def save_config(config: TradingConfiguration, user_id: str):
    # Validate all constraints
    if config.daily_loss_limit > config.account_balance * 0.10:
        raise HTTPException(detail="Daily loss limit too high")
    
    if config.max_concurrent_positions > 10:
        raise HTTPException(detail="Too many positions")
    
    return db.save(user_id, config)
```

---

## 📊 DATABASE SCHEMA

```sql
-- Users Table
CREATE TABLE users (
    id UUID PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    created_at TIMESTAMP,
    last_login TIMESTAMP
);

-- Trading Configurations
CREATE TABLE trading_configurations (
    id UUID PRIMARY KEY,
    user_id UUID REFERENCES users(id),
    account_balance DECIMAL(15, 2),
    daily_profit_target DECIMAL(15, 2),
    daily_loss_limit DECIMAL(15, 2),
    risk_per_trade_percent DECIMAL(5, 2),
    risk_appetite VARCHAR(50),
    market_start_time TIME,
    market_end_time TIME,
    symbol_selection_mode VARCHAR(50),
    manual_symbols TEXT[],
    allowed_sectors TEXT[],
    min_confidence_threshold INT,
    max_concurrent_positions INT,
    broker_type VARCHAR(50),
    broker_api_key VARCHAR(255),  -- encrypted
    broker_api_secret VARCHAR(255),  -- encrypted
    claude_api_key VARCHAR(255),  -- encrypted
    require_manual_approval BOOLEAN,
    is_active BOOLEAN,
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);

-- Trades
CREATE TABLE trades (
    id UUID PRIMARY KEY,
    user_id UUID REFERENCES users(id),
    symbol VARCHAR(20),
    signal VARCHAR(20),  -- BUY_STOCK, SELL_STOCK, BUY_CALL, BUY_PUT
    entry_price DECIMAL(15, 2),
    entry_time TIMESTAMP,
    current_price DECIMAL(15, 2),
    exit_price DECIMAL(15, 2),
    exit_time TIMESTAMP,
    stop_loss DECIMAL(15, 2),
    target DECIMAL(15, 2),
    quantity INT,
    pnl DECIMAL(15, 2),
    pnl_percent DECIMAL(5, 2),
    confidence INT,
    claude_reasoning TEXT,
    status VARCHAR(50),  -- OPEN, CLOSED, CANCELLED
    exit_reason VARCHAR(50),  -- SL_HIT, TARGET_HIT, MANUAL_EXIT
    created_at TIMESTAMP,
    updated_at TIMESTAMP,
    INDEX idx_user_date (user_id, entry_time)
);

-- System Logs
CREATE TABLE system_logs (
    id UUID PRIMARY KEY,
    user_id UUID REFERENCES users(id),
    event_type VARCHAR(50),  -- trade_opened, trade_closed, error, signal_generated
    message TEXT,
    severity VARCHAR(20),  -- info, warning, error
    timestamp TIMESTAMP,
    INDEX idx_user_time (user_id, timestamp)
);

-- Trading Sessions (Bot running sessions)
CREATE TABLE trading_sessions (
    id UUID PRIMARY KEY,
    user_id UUID REFERENCES users(id),
    bot_id VARCHAR(255),
    status VARCHAR(50),  -- running, paused, stopped
    started_at TIMESTAMP,
    stopped_at TIMESTAMP
);
```

---

## 🚀 DEPLOYMENT ARCHITECTURE

```yaml
Production Setup:

Frontend:
  - Hosting: Vercel or AWS S3 + CloudFront
  - Domain: yourdomain.com
  - SSL: Automatic (Let's Encrypt)
  - CDN: CloudFlare for faster load

Backend (Trading Engine):
  - Server: AWS EC2 (t3.small, 2GB RAM)
    OR DigitalOcean Droplet
    OR self-hosted Linux VPS
  - OS: Ubuntu 22.04 LTS
  - Runtime: Python 3.11
  - Process Manager: systemd or supervisor
  - Keep running 24/5 (during market hours)
  
  Install:
  ```bash
  # Clone repo
  git clone <repo>
  cd backend
  
  # Install dependencies
  python -m venv venv
  source venv/bin/activate
  pip install -r requirements.txt
  
  # Set environment variables
  cp .env.example .env
  # Edit .env with real credentials
  
  # Run with supervisor for persistence
  sudo apt install supervisor
  # Create /etc/supervisor/conf.d/trading.conf
  
  # Start
  sudo supervisorctl reread
  sudo supervisorctl update
  sudo supervisorctl start trading
  ```

Database:
  - PostgreSQL on AWS RDS or DigitalOcean
  - Automated backups daily
  - Read replicas for high availability

Monitoring:
  - Uptime monitoring: Uptimerobot or Healthchecks.io
  - Alerts: Email/Slack on bot crash
  - Logs: CloudWatch or Papertrail

DNS:
  - Route53 or Cloudflare
  - Point yourdomain.com to backend + frontend
```

---

## 📈 DEVELOPMENT TIMELINE

```
Week 1:
  ├─ Setup: FastAPI + React boilerplate
  ├─ DB schema design + creation
  ├─ Auth: JWT login/signup
  └─ API: GET/POST /api/config endpoints

Week 2:
  ├─ Frontend: Configuration form UI
  ├─ Broker connection testing
  ├─ API: Bot start/stop endpoints
  └─ WebSocket setup (basic)

Week 3:
  ├─ Trading engine: Core loop
  ├─ Data collection + indicators
  ├─ Claude integration (test with mock data)
  └─ Position sizing + risk management

Week 4:
  ├─ Frontend: Live dashboard UI
  ├─ WebSocket: Real-time updates
  ├─ Order execution logic
  └─ Paper trading (test mode)

Week 5:
  ├─ Trade monitoring + exit logic
  ├─ P&L calculations
  ├─ Reporting + CSV export
  └─ Frontend: Trades history view

Week 6:
  ├─ Integration testing
  ├─ Performance optimization
  ├─ Security hardening
  └─ Deployment setup

Week 7-8:
  ├─ Beta testing (small live account)
  ├─ Bug fixes + refinements
  ├─ Documentation
  └─ Production launch
```

---

## 🎯 SUCCESS CRITERIA

✅ Configuration Dashboard:
- User can save all trading parameters
- Test broker connection
- Start/pause/stop bot with 1 click

✅ Live Dashboard:
- Shows real-time open trades
- Live P&L updates
- System logs streaming
- Beautiful, responsive design

✅ Trading Engine:
- Fetches market data every 5-15 min
- Calls Claude API successfully
- Executes trades with proper risk checks
- Monitors positions automatically
- Closes all positions at market end

✅ Reliability:
- 99.5% uptime during market hours
- Zero missed data points
- Proper error handling + recovery

✅ Performance:
- API response < 200ms
- WebSocket updates < 1 second
- CPU usage < 20% on backend

✅ Security:
- All keys encrypted
- Rate limiting active
- User authentication required
- No hardcoded credentials

---

## 📝 NOTES FOR DEVELOPER

1. **Start with backend** - The trading engine is the core
2. **Paper trade first** - Test with real broker API (no real money)
3. **Monitor Claude costs** - Each API call costs money, optimize batching
4. **Use SQLite initially** - Switch to PostgreSQL only when scaling
5. **Test stop-losses** - Critical for risk management
6. **Log everything** - You'll need these logs for debugging
7. **Circuit breakers** - Implement safety stops early
8. **Gradual scaling** - Start with 1-3 symbols, scale up
9. **Backtest first** - Before trading live, backtest your signals
10. **Keep it simple** - Don't over-engineer initially

---

## 🔗 USEFUL RESOURCES

Broker APIs:
- Zerodha: https://kite.trade/docs/connect/v3/
- Angel Broking: https://angelbroking.com/smartapi
- Shoonya: https://jugalkisor.gitbook.io/shoonya-api

FastAPI:
- Docs: https://fastapi.tiangolo.com
- WebSocket: https://fastapi.tiangolo.com/advanced/websockets/

React/Next.js:
- React Query: https://tanstack.com/query/latest
- Zustand: https://github.com/pmndrs/zustand
- Tailwind: https://tailwindcss.com/docs

Claude API:
- Docs: https://docs.anthropic.com
- Model list: https://docs.anthropic.com/claude/reference/getting-started

Indicators:
- TA-Lib: https://github.com/mrjbq7/ta-lib
- pandas_ta: https://github.com/twopirllc/pandas-ta

---

## 🎓 EXAMPLE: Complete Trade Flow

```
1. User loads dashboard
   └─ Frontend fetches config via GET /api/config/get
   └─ Shows current settings

2. User clicks "START BOT"
   └─ Frontend calls POST /api/bot/start
   └─ Backend loads config
   └─ Backend starts TradingEngine in background task
   └─ Returns bot_id to frontend

3. Backend: Every 5 minutes
   ├─ collect_market_data() → fetch TCS, INFY, BANKNIFTY
   ├─ engineer_features() → calculate RSI, MACD, etc.
   ├─ get_claude_signals() → call Claude API
   │  └─ Claude analyzes and returns:
   │     {
   │       "TCS": {signal: "SELL", confidence: 75, entry: 3845, sl: 3860, target: 3790}
   │     }
   ├─ validate_signals() → risk checks
   ├─ execute_trade() → place order via broker API
   └─ broadcast_status_update() → send to frontend via WebSocket

4. Frontend: Receives WebSocket message
   └─ Updates open trades list
   └─ Updates P&L
   └─ Updates system log

5. User sees live dashboard with new trade:
   TCS │ SELL │ 3845 │ ... │ Confidence: 75%

6. Price moves:
   ├─ 3840 (-₹750)
   ├─ 3820 (-₹3,750)
   ├─ 3810 (-₹5,250)
   └─ 3790 (TARGET HIT - Exit)
   
   └─ Backend: exit_trade() called
   └─ P&L: +₹2,750 profit
   └─ Status: CLOSED
   └─ Frontend: Trade moves to "Closed Trades"

7. End of day (3:25 PM):
   └─ Backend: close_all_positions()
   └─ Generate daily report
   └─ Email summary to user

That's it!
```

