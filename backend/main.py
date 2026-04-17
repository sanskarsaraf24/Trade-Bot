import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config import get_settings
from database.session import engine, SessionLocal
from database import models
from database.models import BotSession, BotStatus
from routes import auth, config_routes, bot_routes, trade_routes, metrics_routes, websocket

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
)
logger = logging.getLogger(__name__)
settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Create all DB tables on startup (idempotent). Clean up zombie sessions."""
    logger.info("Starting LLM Trading System backend…")
    models.Base.metadata.create_all(bind=engine)
    
    # Clean up zombie sessions
    db = SessionLocal()
    try:
        updated = db.query(BotSession).filter(
            BotSession.status.in_([BotStatus.running, BotStatus.paused])
        ).update({"status": BotStatus.stopped}) # or we could add an 'interrupted' status
        db.commit()
        if updated > 0:
            logger.info(f"Cleaned up {updated} interrupted bot sessions.")
    finally:
        db.close()
        
    logger.info("Database initialized and ready.")
    yield
    logger.info("Shutting down…")


app = FastAPI(
    title="LLM Trading System API",
    description="Automated trading bot powered by Claude AI for Indian markets",
    version="1.0.0",
    lifespan=lifespan,
)

# ── CORS ────────────────────────────────────────────────────
origins = (
    ["*"]
    if settings.app_env == "development"
    else [
        "https://trade.sanskarsaraf.in",
        "http://trading_frontend:3000",   # inter-container
    ]
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)

# ── Routers ─────────────────────────────────────────────────
app.include_router(auth.router,           prefix="/api/auth", tags=["Auth"])
app.include_router(config_routes.router,  prefix="/api",      tags=["Config"])
app.include_router(bot_routes.router,     prefix="/api",      tags=["Bot"])
app.include_router(trade_routes.router,   prefix="/api",      tags=["Trades"])
app.include_router(metrics_routes.router, prefix="/api",      tags=["Metrics"])
app.include_router(websocket.router,      prefix="/api/ws",   tags=["WebSocket"])


@app.get("/health", tags=["Health"])
async def health():
    return {"status": "ok", "env": settings.app_env}
