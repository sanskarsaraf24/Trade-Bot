import logging
import random
from typing import List
from sqlalchemy.orm import Session
from database.models import TradingConfiguration
from services.broker_connector import BaseBroker

logger = logging.getLogger(__name__)

# A large pool of highly liquid and volatile NSE symbols to scan from.
# This ensures we always find "movers" without scanning 2000 dead stocks.
LIQUID_POOL = [
    "RELIANCE", "TCS", "INFY", "HDFCBANK", "ICICIBANK", "SBIN", "TITAN", "BHARTIARTL", 
    "WIPRO", "MARUTI", "ADANIENT", "ADANIPORTS", "ZOMATO", "PAYTM", "JIOFIN", "TATASTEEL",
    "JSWSTEEL", "HINDALCO", "COALINDIA", "BHEL", "BEL", "PFC", "RECLTD", "POWERGRID",
    "NTPC", "ONGC", "BPCL", "IOC", "GAIL", "DIVISLAB", "SUNPHARMA", "DRREDDY", "CIPLA",
    "APOLLOHOSP", "MAXHEALTH", "INDIGO", "TATACOMM", "AXISBANK", "KOTAKBANK", "INDUSINDBK",
    "FEDERALBNK", "IDFCFIRSTB", "AUBANK", "YESBANK", "TATAMOTORS", "M&M", "EICHERMOT",
    "ASHOKLEY", "BAJFINANCE", "BAJAJFINSV", "CHOLAFIN", "SHRIRAMFIN", "HDFCLIFE", "SBILIFE",
    "ICICIPRULI", "HINDUNILVR", "ITC", "NESTLEIND", "BRITANNIA", "VBL", "DLF", "LODHA",
    "OBEROIRLTY", "GRASIM", "ULTRACEMCO", "ACC", "AMBUJACEM", "LT", "SIEMENS", "ABB",
    "CUMMINSIND", "HAL", "MAZDOCK", "RVNL", "IRFC", "CONCOR", "PERSISTENT", "KPITTECH",
    "COFORGE", "LTIM", "MPHASIS", "DIXON", "POLYCAB", "KEI", "HAVELLS", "VOLTAS",
]

class ScannerService:
    def __init__(self, broker: BaseBroker):
        self.broker = broker

    async def scan_for_movers(self, limit: int = 10) -> List[str]:
        """
        Scan the liquid pool for the top mover symbols based on intraday momentum.
        """
        logger.info(f"Scanning market for top {limit} movers...")
        
        movers = []
        # Sample 40 symbols from the pool to avoid Rate Limits while ensuring variety
        sample_size = min(40, len(LIQUID_POOL))
        test_pool = random.sample(LIQUID_POOL, sample_size)
        
        scored_symbols = []
        
        for symbol in test_pool:
            try:
                # Use a small window to check immediate momentum
                candles = self.broker.get_ohlcv(symbol, bars=20, interval="5minute")
                if not candles or len(candles) < 2:
                    continue
                
                start_px = float(candles[0]["close"])
                curr_px = float(candles[-1]["close"])
                change_pct = (curr_px - start_px) / start_px * 100
                
                # We look for absolute volatility (highest absolute change)
                score = abs(change_pct)
                scored_symbols.append((symbol, score))
            except Exception as e:
                logger.debug(f"Scanner skipped {symbol}: {e}")
                continue
        
        # Sort by score descending
        scored_symbols.sort(key=lambda x: x[1], reverse=True)
        top_symbols = [x[0] for x in scored_symbols[:limit]]
        
        logger.info(f"Scanner found top movers: {top_symbols}")
        return top_symbols

    async def update_watchlist(self, db: Session, user_id: str):
        """
        Perform a scan and update the user's manual_symbols configuration.
        """
        new_symbols = await self.scan_for_movers()
        if not new_symbols:
            return
            
        config = db.query(TradingConfiguration).filter(
            TradingConfiguration.user_id == user_id
        ).first()
        
        if config:
            config.manual_symbols = new_symbols
            # Force mode to manual so the engine uses these specific scanned symbols
            config.symbol_selection_mode = "manual"
            db.commit()
            logger.info(f"Watchlist updated for user {user_id}: {new_symbols}")
            return new_symbols
        return []
