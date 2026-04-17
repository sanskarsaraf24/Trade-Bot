import logging
from abc import ABC, abstractmethod
from typing import Dict, List, Optional
import time

logger = logging.getLogger(__name__)

class BaseBroker(ABC):
    @abstractmethod
    def get_price(self, symbol: str) -> float: pass
    @abstractmethod
    def get_ohlcv(self, symbol: str, bars: int, interval: str) -> list[dict]: pass
    @abstractmethod
    def place_order(self, symbol: str, action: str, quantity: int, order_type: str, price: Optional[float]) -> dict: pass
    @abstractmethod
    def get_account_balance(self) -> float: pass

class PaperBroker(BaseBroker):
    def __init__(self, starting_balance: float = 1_000_000):
        self.balance = starting_balance
        self.positions = {}
        self.price_cache = {}

    def get_price(self, symbol: str) -> float: return self.price_cache.get(symbol, 100.0)
    def set_price(self, symbol: str, price: float): self.price_cache[symbol] = price
    def get_ohlcv(self, symbol: str, bars: int = 100, interval: str = "5minute") -> list[dict]:
        import random
        from datetime import datetime, timedelta
        now = datetime.utcnow()
        return [{"timestamp": (now - timedelta(minutes=i*5)).isoformat(), "open": 100, "high": 105, "low": 95, "close": 100, "volume": 1000} for i in range(bars)]
    
    def place_order(self, symbol: str, action: str, quantity: int, order_type: str = "MARKET", price: Optional[float] = None) -> dict:
        return {"order_id": f"paper_{int(time.time())}", "status": "COMPLETED"}
    
    def get_account_balance(self) -> float: return self.balance

class ZerodhaBroker(BaseBroker):
    def __init__(self, api_key: str, api_secret: str, access_token: str = None, request_token: str = None):
        self.api_key = api_key
        self.api_secret = api_secret
        self.instrument_tokens = {}
        self._all_instruments = []
        self.ltp_cache = {}
        self.ticker = None
        
        try:
            from kiteconnect import KiteConnect
            self.kite = KiteConnect(api_key=api_key)
            
            if access_token:
                self.kite.set_access_token(access_token)
                self.access_token = access_token
            elif request_token:
                data = self.kite.generate_session(request_token, api_secret=api_secret)
                self.kite.set_access_token(data["access_token"])
                self.access_token = data["access_token"]
                logger.info("Zerodha session generated successfully.")
            else:
                self.access_token = None
        except Exception as e:
            logger.error(f"Zerodha init error: {e}")
            raise

    def generate_totp(self, secret: str) -> str:
        try:
            import pyotp
            totp = pyotp.TOTP(secret)
            return totp.now()
        except Exception as e:
            logger.error(f"TOTP generation failed: {e}")
            return ""

    def start_websocket(self):
        if not self.access_token: return
        try:
            from kiteconnect import KiteTicker
            self.ticker = KiteTicker(self.api_key, self.access_token)
            def on_ticks(ws, ticks):
                for tick in ticks:
                    token = tick.get("instrument_token")
                    price = tick.get("last_price")
                    if token and price:
                        for sym, t in self.instrument_tokens.items():
                            if t == token: self.ltp_cache[sym] = price; break
            def on_connect(ws, response):
                if self.instrument_tokens:
                    tokens = list(self.instrument_tokens.values())
                    ws.subscribe(tokens)
                    ws.set_mode(ws.MODE_FULL, tokens)
            self.ticker.on_ticks = on_ticks
            self.ticker.on_connect = on_connect
            self.ticker.connect(threaded=True)
        except Exception as e:
            logger.error(f"WebSocket error: {e}")

    def get_price(self, symbol: str) -> float:
        if symbol in self.ltp_cache: return self.ltp_cache[symbol]
        try:
            exchange_symbol = f"NSE:{symbol}"
            data = self.kite.ltp([exchange_symbol])
            if exchange_symbol in data:
                price = data[exchange_symbol]["last_price"]
                self.ltp_cache[symbol] = price
                return price
        except: return 0.0
        return 0.0

    def get_ohlcv(self, symbol: str, bars: int = 100, interval: str = "5minute") -> list[dict]:
        from datetime import date, timedelta
        to_date = date.today()
        from_date = to_date - timedelta(days=7)
        try:
            token = self._get_instrument_token(symbol)
            data = self.kite.historical_data(token, from_date, to_date, interval)
            return [{"timestamp": d["date"].isoformat(), "open": d["open"], "high": d["high"], "low": d["low"], "close": d["close"], "volume": d["volume"]} for d in data[-bars:]]
        except Exception as e:
            logger.error(f"Historical data error {symbol}: {e}")
            return []

    def place_order(self, symbol: str, action: str, quantity: int, order_type: str = "MARKET", price: Optional[float] = None) -> dict:
        try:
            transaction = self.kite.TRANSACTION_TYPE_BUY if action == "BUY" else self.kite.TRANSACTION_TYPE_SELL
            order_id = self.kite.place_order(tradingsymbol=symbol, exchange=self.kite.EXCHANGE_NSE, transaction_type=transaction, quantity=quantity, product=self.kite.PRODUCT_MIS, order_type=getattr(self.kite, f"ORDER_TYPE_{order_type}"), price=price)
            return {"order_id": order_id, "status": "PLACED"}
        except Exception as e: return {"error": str(e), "status": "FAILED"}

    def get_account_balance(self) -> float:
        try: return self.kite.margins()["equity"]["net"]
        except: return 0.0

    def subscribe_symbols(self, symbols: list[str]):
        new_tokens = []
        for sym in symbols:
            try:
                token = self._get_instrument_token(sym)
                if token: self.instrument_tokens[sym] = token; new_tokens.append(token)
            except: continue
        if self.ticker and self.ticker.is_connected() and new_tokens:
            self.ticker.subscribe(new_tokens)
            self.ticker.set_mode(self.ticker.MODE_FULL, new_tokens)

    def _get_instrument_token(self, symbol: str) -> int:
        if symbol in self.instrument_tokens: return self.instrument_tokens[symbol]
        if not self._all_instruments: self._all_instruments = self.kite.instruments("NSE")
        for inst in self._all_instruments:
            if inst["tradingsymbol"] == symbol:
                token = inst["instrument_token"]
                self.instrument_tokens[symbol] = token
                return token
        raise ValueError(f"Symbol {symbol} not found")

def create_broker(broker_type: str, api_key: str = "", api_secret: str = "", access_token: str = "", balance: float = 1_000_000) -> BaseBroker:
    if broker_type == "zerodha":
        return ZerodhaBroker(api_key=api_key, api_secret=api_secret, access_token=access_token)
    return PaperBroker(starting_balance=balance)
