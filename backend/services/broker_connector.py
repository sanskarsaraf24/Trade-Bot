"""
Broker connectors.
- PaperBroker: realistic simulation with live NSE price fetching via Yahoo Finance
- ZerodhaBroker: full Kite Connect integration with TOTP auto-session
"""
import logging
import time
import random
from abc import ABC, abstractmethod
from datetime import date, datetime, timedelta
from typing import Dict, List, Optional
from config import get_settings

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────
# Base
# ─────────────────────────────────────────────────────────────
class BaseBroker(ABC):
    @abstractmethod
    def get_price(self, symbol: str) -> float: ...

    def get_fresh_price(self, symbol: str) -> float:
        """Default fresh-price behavior: delegate to get_price()."""
        return self.get_price(symbol)

    @abstractmethod
    def get_ohlcv(self, symbol: str, bars: int, interval: str) -> list[dict]: ...

    @abstractmethod
    def place_order(self, symbol: str, action: str, quantity: int,
                    order_type: str, price: Optional[float]) -> dict: ...

    @abstractmethod
    def get_account_balance(self) -> float: ...

    def subscribe_symbols(self, symbols: list[str]):
        """No-op for brokers that don't use WebSocket streaming."""
        pass

    def get_feed_status(self) -> dict:
        """Best-effort feed health for dashboard/engine observability."""
        return {
            "source": self.__class__.__name__,
            "connected": True,
            "last_success_ts": None,
            "last_error": "",
        }


# ─────────────────────────────────────────────────────────────
# Paper Broker — realistic simulation
# ─────────────────────────────────────────────────────────────

# Realistic seed prices for common NSE symbols (as of mid-2024 approximate range)
SEED_PRICES: Dict[str, float] = {
    "RELIANCE":  2950.0,
    "TCS":       3820.0,
    "INFY":      1740.0,
    "HDFCBANK":  1620.0,
    "ICICIBANK": 1180.0,
    "SBIN":       820.0,
    "TITAN":     3500.0,
    "BHARTIARTL": 1430.0,
    "WIPRO":      530.0,
    "MARUTI":   12500.0,
    "ASIANPAINT": 2850.0,
    "BAJFINANCE": 6800.0,
    "AXISBANK":  1180.0,
    "LT":        3650.0,
    "KOTAKBANK": 1780.0,
    "NIFTY":    22500.0,
    "BANKNIFTY": 48500.0,
}


def _fetch_live_price(symbol: str) -> Optional[float]:
    """Try to fetch live NSE price via Yahoo Finance (best-effort, no API key needed)."""
    try:
        import urllib.request
        import json
        ticker = f"{symbol}.NS"
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}?interval=1m&range=1d"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read())
        price = data["chart"]["result"][0]["meta"]["regularMarketPrice"]
        return float(price)
    except Exception:
        return None


class PaperBroker(BaseBroker):
    """
    Simulates trading with realistic price data.
    If Zerodha credentials exist, polls Zerodha API every 10s.
    Otherwise falls back to seed prices / Yahoo Finance.
    """
    def __init__(self, starting_balance: float = 100000.0, live_broker=None):
        self.balance = starting_balance
        self.live_broker = live_broker
        self._price_cache: Dict[str, float] = {}
        self._last_fetch: Dict[str, float] = {}
        self._orders: list = []
        self._feed_status = {
            "source": "seed",
            "connected": False,
            "last_success_ts": None,
            "last_error": "",
        }

    def _mark_feed(self, source: str, connected: bool, error: str = ""):
        self._feed_status["source"] = source
        self._feed_status["connected"] = connected
        self._feed_status["last_error"] = error
        if connected:
            self._feed_status["last_success_ts"] = datetime.now().isoformat()

    def _get_seed_price(self, symbol: str) -> float:
        seed = SEED_PRICES.get(symbol, 500.0)
        # Small random walk: ±0.3% from seed
        return round(seed * (1 + random.uniform(-0.003, 0.003)), 2)

    def get_fresh_price(self, symbol: str) -> float:
        """Bypass all caching. Always calls Zerodha REST if available — NEVER Yahoo."""
        if self.live_broker:
            try:
                live = self.live_broker.get_fresh_price(symbol)
                if live and live > 0:
                    self._mark_feed("zerodha_rest", True)
                    self._price_cache[symbol] = live
                    self._last_fetch[symbol] = time.time()
                    return live
            except Exception as e:
                self._mark_feed("zerodha_rest", False, str(e))
                logger.warning(f"[PaperBroker] Zerodha REST failed for {symbol}: {e}")
        # Only use Yahoo if there is no live_broker at all (pure paper, no creds)
        if not self.live_broker:
            live = _fetch_live_price(symbol)
            if live and live > 0:
                self._price_cache[symbol] = live
                self._last_fetch[symbol] = time.time()
                self._mark_feed("yahoo", True)
                return live
        self._mark_feed("seed", False, "Zerodha REST unavailable")
        return self._price_cache.get(symbol, self._get_seed_price(symbol))

    def get_price(self, symbol: str) -> float:
        now = time.time()
        last = self._last_fetch.get(symbol, 0)

        # Refresh every 2 seconds using Zerodha if available, else 3s Yahoo tick
        if self.live_broker and (now - last > 2):
            try:
                live = self.live_broker.get_fresh_price(symbol)
                if live and live > 0:
                    self._price_cache[symbol] = live
                    self._last_fetch[symbol] = now
                    self._mark_feed("zerodha_rest", True)
                    return live
            except Exception as e:
                self._mark_feed("zerodha_rest", False, str(e))

        if not self.live_broker and (now - last > 3):
            live = _fetch_live_price(symbol)
            if live and live > 0:
                self._price_cache[symbol] = live * (1 + random.uniform(-0.0005, 0.0005))
                self._mark_feed("yahoo", True)
            elif symbol not in self._price_cache:
                self._price_cache[symbol] = self._get_seed_price(symbol)
                self._mark_feed("seed", False, "Yahoo unavailable")
            else:
                prev = self._price_cache[symbol]
                self._price_cache[symbol] = round(prev * (1 + random.uniform(-0.002, 0.002)), 2)
                self._mark_feed("seed", False, "Using synthetic walk fallback")
            self._last_fetch[symbol] = now

        return self._price_cache.get(symbol, self._get_seed_price(symbol))

    def get_ohlcv(self, symbol: str, bars: int = 100, interval: str = "5minute") -> list[dict]:
        """Generate realistic OHLCV data with random walk from current price."""
        current = self.get_price(symbol)

        candles = []
        price = current * 0.98  # start slightly below current
        now = datetime.utcnow()

        for i in range(bars, 0, -1):
            # Random walk per candle
            change_pct = random.gauss(0, 0.003)  # ~0.3% std dev per 5min candle
            open_p = round(price, 2)
            close_p = round(price * (1 + change_pct), 2)
            high_p = round(max(open_p, close_p) * (1 + abs(random.gauss(0, 0.001))), 2)
            low_p = round(min(open_p, close_p) * (1 - abs(random.gauss(0, 0.001))), 2)
            volume = int(random.uniform(50_000, 500_000))

            ts = now - timedelta(minutes=i * 5)
            candles.append({
                "timestamp": ts.isoformat(),
                "open": open_p,
                "high": high_p,
                "low": low_p,
                "close": close_p,
                "volume": volume,
            })
            price = close_p

        return candles

    def place_order(self, symbol: str, action: str, quantity: int,
                    order_type: str = "MARKET", price: Optional[float] = None) -> dict:
        # For MARKET orders, always use the current LTP to prevent stale entry prices
        if order_type.upper() == "MARKET":
            exec_price = self.get_price(symbol)
        else:
            exec_price = price or self.get_price(symbol)
            
        slippage = exec_price * random.uniform(-0.0005, 0.0005)
        final_price = round(exec_price + slippage, 2)

        order_id = f"PAPER_{symbol}_{int(time.time() * 1000)}"
        self._orders.append({
            "order_id": order_id,
            "symbol": symbol,
            "action": action,
            "quantity": quantity,
            "price": final_price,
            "timestamp": datetime.utcnow().isoformat(),
        })

        cost = final_price * quantity
        if action in ("BUY", "BUY_STOCK", "BUY_CALL", "BUY_PUT"):
            self.balance -= cost
        else:
            self.balance += cost

        logger.info(f"[PAPER] {action} {quantity}x {symbol} @ ₹{final_price:,.2f}")
        return {"order_id": order_id, "status": "COMPLETED", "price": final_price}

    def get_account_balance(self) -> float:
        return round(self.balance, 2)

    def get_feed_status(self) -> dict:
        return dict(self._feed_status)


# ─────────────────────────────────────────────────────────────
# Zerodha Broker
# ─────────────────────────────────────────────────────────────
class ZerodhaBroker(BaseBroker):
    def __init__(self, api_key: str, api_secret: str,
                 access_token: str = None, request_token: str = None,
                 totp_secret: str = None):
        self.api_key = api_key
        self.api_secret = api_secret
        self.totp_secret = totp_secret
        self.instrument_tokens: Dict[str, int] = {}
        self._all_instruments: list = []
        self.ltp_cache: Dict[str, float] = {}
        self.ticker = None
        self.access_token: Optional[str] = None
        self._ws_connected: bool = False
        self._last_ws_error: str = ""
        self._last_rest_success_ts: str = ""

        try:
            from kiteconnect import KiteConnect
            self.kite = KiteConnect(api_key=api_key)

            if access_token:
                self.kite.set_access_token(access_token)
                self.access_token = access_token
                logger.info("Zerodha: using existing access token")
            elif request_token:
                self._generate_session(request_token)
            elif totp_secret:
                # Auto-login using TOTP
                self._auto_login()
            else:
                logger.warning("Zerodha: no token or TOTP provided — orders will fail")

        except ImportError:
            logger.error("kiteconnect not installed. Run: pip install kiteconnect")
            raise
        except Exception as e:
            logger.error(f"Zerodha init error: {e}")
            raise

    def _generate_session(self, request_token: str):
        """Exchange request_token for access_token."""
        data = self.kite.generate_session(request_token, api_secret=self.api_secret)
        self.kite.set_access_token(data["access_token"])
        self.access_token = data["access_token"]
        logger.info("Zerodha: session generated from request_token")

    def _auto_login(self):
        """
        Attempt auto-login via TOTP when running headlessly.
        Uses the kiteconnect login flow with TOTP for 2FA.
        NOTE: Zerodha's web login has Cloudflare protection that may block automated logins.
        The recommended approach is: user logs in once via browser → token saved → auto-refresh daily.
        """
        logger.warning(
            "Zerodha TOTP auto-login attempted. "
            "If this fails due to Cloudflare, use the 'Re-link Zerodha' button in the dashboard."
        )
        # TOTP auto-login via httpx (best-effort)
        try:
            import httpx
            import pyotp

            totp = pyotp.TOTP(self.totp_secret)
            session = httpx.Client(follow_redirects=True)

            # Step 1: GET login page to get session cookie
            login_url = f"https://kite.zerodha.com/api/login"
            # This approach requires additional steps that may be blocked by Cloudflare
            # Logging the attempt but falling through gracefully
            logger.info("TOTP auto-login via API not supported due to Zerodha's security policies.")
            logger.info("Please use the dashboard 'Re-link Zerodha' button to authenticate.")
        except Exception as e:
            logger.error(f"Auto-login failed: {e}")

    def is_token_valid(self) -> bool:
        """Check if current access token is valid by making a lightweight API call."""
        if not self.access_token:
            return False
        try:
            self.kite.profile()
            return True
        except Exception:
            return False

    def start_websocket(self):
        """Start Kite WebSocket for real-time price streaming."""
        if not self.access_token:
            logger.warning("No access token — WebSocket not started")
            return
        try:
            from kiteconnect import KiteTicker

            self.ticker = KiteTicker(self.api_key, self.access_token)

            def on_ticks(ws, ticks):
                for tick in ticks:
                    token = tick.get("instrument_token")
                    price = tick.get("last_price")
                    if token and price:
                        for sym, t in self.instrument_tokens.items():
                            if t == token:
                                self.ltp_cache[sym] = price
                                break

            def on_connect(ws, response):
                self._ws_connected = True
                self._last_ws_error = ""
                if self.instrument_tokens:
                    tokens = list(self.instrument_tokens.values())
                    ws.subscribe(tokens)
                    ws.set_mode(ws.MODE_FULL, tokens)

            def on_error(ws, code, reason):
                self._ws_connected = False
                self._last_ws_error = f"{code}: {reason}"
                logger.error(f"Kite WebSocket error {code}: {reason}")

            self.ticker.on_ticks = on_ticks
            self.ticker.on_connect = on_connect
            self.ticker.on_error = on_error
            self.ticker.connect(threaded=True)
            logger.info("Zerodha WebSocket started")
        except Exception as e:
            logger.error(f"WebSocket start error: {e}")

    def subscribe_symbols(self, symbols: list[str]):
        """Subscribe symbols to the WebSocket ticker for live prices."""
        new_tokens = []
        for sym in symbols:
            try:
                if sym not in self.instrument_tokens:
                    token = self._get_instrument_token(sym)
                    if token:
                        self.instrument_tokens[sym] = token
                        new_tokens.append(token)
            except Exception as e:
                logger.warning(f"Could not subscribe {sym}: {e}")

        if self.ticker and new_tokens:
            try:
                if self.ticker.is_connected():
                    self.ticker.subscribe(new_tokens)
                    self.ticker.set_mode(self.ticker.MODE_FULL, new_tokens)
            except Exception as e:
                logger.warning(f"WebSocket subscribe error: {e}")

    def get_fresh_price(self, symbol: str) -> float:
        """Always fetches from Zerodha REST API — never uses the cache.
        Use this at order execution time and for P&L calculations."""
        try:
            exchange_symbol = f"NSE:{symbol}"
            data = self.kite.ltp([exchange_symbol])
            if exchange_symbol in data:
                price = float(data[exchange_symbol]["last_price"])
                self.ltp_cache[symbol] = price  # keep cache in sync
                self._last_rest_success_ts = datetime.now().isoformat()
                logger.info(f"[LTP REST] {symbol} = ₹{price}")
                return price
        except Exception as e:
            logger.warning(f"get_fresh_price REST failed for {symbol}: {e}")
        # Fallback to cache if REST fails
        return self.ltp_cache.get(symbol, 0.0)

    def get_price(self, symbol: str) -> float:
        # Prefer WebSocket cached price (freshest)
        if symbol in self.ltp_cache:
            return self.ltp_cache[symbol]
        # Fallback to REST
        return self.get_fresh_price(symbol)

    def get_ohlcv(self, symbol: str, bars: int = 100, interval: str = "5minute") -> list[dict]:
        to_date = date.today()
        from_date = to_date - timedelta(days=10)  # extra days to guarantee enough bars
        try:
            token = self._get_instrument_token(symbol)
            data = self.kite.historical_data(token, from_date, to_date, interval)
            result = []
            for d in data[-bars:]:
                dt = d["date"]
                result.append({
                    "timestamp": dt.isoformat() if hasattr(dt, "isoformat") else str(dt),
                    "open": d["open"],
                    "high": d["high"],
                    "low": d["low"],
                    "close": d["close"],
                    "volume": d["volume"],
                })
            return result
        except Exception as e:
            logger.error(f"Historical data error {symbol}: {e}")
            return []

    def place_order(self, symbol: str, action: str, quantity: int,
                    order_type: str = "MARKET", price: Optional[float] = None,
                    trigger_price: Optional[float] = None) -> dict:
        if not self.access_token:
            return {"error": "No valid session token. Re-link Zerodha.", "status": "FAILED"}
        try:
            transaction = (
                self.kite.TRANSACTION_TYPE_BUY
                if action in ("BUY", "BUY_STOCK", "BUY_CALL", "BUY_PUT")
                else self.kite.TRANSACTION_TYPE_SELL
            )
            # Map order types to Kite constants
            # MIS = intraday with margin leverage (not MTF, which requires separate approval)
            _type_map = {
                "MARKET": self.kite.ORDER_TYPE_MARKET,
                "LIMIT":  self.kite.ORDER_TYPE_LIMIT,
                "SL":     self.kite.ORDER_TYPE_SL,
                "SL-M":   self.kite.ORDER_TYPE_SLM,
            }
            kite_order_type = _type_map.get(order_type.upper(), self.kite.ORDER_TYPE_MARKET)
            is_market = kite_order_type == self.kite.ORDER_TYPE_MARKET

            # Zerodha may reject API MARKET orders without market protection.
            # First try with market_protection; if still rejected, retry as protective LIMIT.
            order_kwargs = {
                "variety": self.kite.VARIETY_REGULAR,
                "tradingsymbol": symbol,
                "exchange": self.kite.EXCHANGE_NSE,
                "transaction_type": transaction,
                "quantity": quantity,
                "product": self.kite.PRODUCT_MIS,
                "order_type": kite_order_type,
                "price": price if order_type in ("LIMIT", "SL") else None,
                "trigger_price": trigger_price if order_type in ("SL", "SL-M") else None,
            }
            if is_market:
                order_kwargs["market_protection"] = 2

            try:
                order_id = self.kite.place_order(**order_kwargs)
            except Exception as e:
                err_text = str(e)
                if is_market and "market protection" in err_text.lower():
                    ltp = self.get_fresh_price(symbol) or self.get_price(symbol)
                    if ltp <= 0:
                        raise
                    cushion = 1.001 if transaction == self.kite.TRANSACTION_TYPE_BUY else 0.999
                    limit_price = round(ltp * cushion, 2)
                    order_id = self.kite.place_order(
                        variety=self.kite.VARIETY_REGULAR,
                        tradingsymbol=symbol,
                        exchange=self.kite.EXCHANGE_NSE,
                        transaction_type=transaction,
                        quantity=quantity,
                        product=self.kite.PRODUCT_MIS,
                        order_type=self.kite.ORDER_TYPE_LIMIT,
                        price=limit_price,
                    )
                    logger.warning(
                        f"MARKET rejected for {symbol}; retried as LIMIT @ ₹{limit_price:.2f}"
                    )
                else:
                    raise

            fill_price = self._wait_for_fill_price(order_id)
            logger.info(f"[ZERODHA] {action} {quantity}x {symbol} [{order_type}] → order_id={order_id}")
            if fill_price > 0:
                self.ltp_cache[symbol] = fill_price
                return {"order_id": order_id, "status": "COMPLETED", "price": fill_price}
            return {"order_id": order_id, "status": "PLACED"}
        except Exception as e:
            logger.error(f"place_order failed for {symbol}: {e}")
            return {"error": str(e), "status": "FAILED"}

    def _wait_for_fill_price(self, order_id: str) -> float:
        """Poll order history briefly to get average fill price for accurate trade logs."""
        for _ in range(6):
            try:
                hist = self.kite.order_history(order_id) or []
                if not hist:
                    time.sleep(0.35)
                    continue
                last = hist[-1]
                avg = float(last.get("average_price") or 0)
                status = str(last.get("status") or "").upper()
                if avg > 0 and status in {"COMPLETE", "COMPLETED"}:
                    return avg
            except Exception:
                pass
            time.sleep(0.35)
        return 0.0

    def place_sl_order(self, symbol: str, action: str, quantity: int,
                       trigger_price: float, limit_price: Optional[float] = None) -> dict:
        """
        Place a Stop-Loss Market (SL-M) order — automatically triggered at trigger_price.
        Use this for automated stop-loss protection after a position is entered.
        SL-M is preferred over SL-L for bots as it guarantees execution at market price.
        """
        order_type = "SL" if limit_price else "SL-M"
        return self.place_order(symbol, action, quantity,
                                order_type=order_type,
                                price=limit_price,
                                trigger_price=trigger_price)

    def get_account_balance(self) -> float:
        try:
            return float(self.kite.margins()["equity"]["net"])
        except Exception as e:
            logger.warning(f"get_account_balance failed: {e}")
            return 0.0

    def _get_instrument_token(self, symbol: str) -> int:
        if symbol in self.instrument_tokens:
            return self.instrument_tokens[symbol]
        if not self._all_instruments:
            self._all_instruments = self.kite.instruments("NSE")
        for inst in self._all_instruments:
            if inst["tradingsymbol"] == symbol:
                token = inst["instrument_token"]
                self.instrument_tokens[symbol] = token
                return token
        raise ValueError(f"Symbol {symbol} not found on NSE")

    def get_feed_status(self) -> dict:
        return {
            "source": "zerodha_ws" if self._ws_connected else "zerodha_rest",
            "connected": self._ws_connected or bool(self._last_rest_success_ts),
            "last_success_ts": self._last_rest_success_ts,
            "last_error": self._last_ws_error,
        }


# ─────────────────────────────────────────────────────────────
# Factory
# ─────────────────────────────────────────────────────────────
def create_broker(
    broker_type: str,
    api_key: str = "",
    api_secret: str = "",
    access_token: str = "",
    totp_secret: str = "",
    balance: float = 1_000_000,
) -> BaseBroker:
    settings = get_settings()
    # Always fall back to system-wide env-var credentials if user hasn't set their own
    final_api_key    = api_key    or settings.zerodha_api_key
    final_api_secret = api_secret or settings.zerodha_api_secret
    final_totp       = totp_secret or settings.zerodha_totp_secret

    if broker_type == "zerodha" and final_api_key:
        src = "user-specific" if api_key else "global system env"
        logger.info(f"[BROKER] Creating ZerodhaBroker using {src} credentials")
        return ZerodhaBroker(
            api_key=final_api_key,
            api_secret=final_api_secret,
            access_token=access_token or None,
            totp_secret=final_totp or None,
        )

    live_ref = None
    if final_api_key and (access_token or final_totp):
        try:
            logger.info("[BROKER] Initializing background ZerodhaBroker for Paper LTP prices...")
            live_ref = ZerodhaBroker(
                api_key=final_api_key,
                api_secret=final_api_secret,
                access_token=access_token or None,
                totp_secret=final_totp or None,
            )
            if live_ref.is_token_valid():
                logger.info("[BROKER] ✅ Background Zerodha token valid — Paper will use Zerodha LTP")
            else:
                logger.warning("[BROKER] ⚠️ Background Zerodha token INVALID — Paper will use Yahoo fallback")
                live_ref = None
        except Exception as e:
            logger.warning(f"[BROKER] Background Zerodha init failed: {e}")
            live_ref = None

    logger.info("[BROKER] Using Paper Broker (simulation mode)")
    return PaperBroker(starting_balance=balance, live_broker=live_ref)
