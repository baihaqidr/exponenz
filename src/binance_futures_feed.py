import asyncio
import json
import threading
import time
from typing import Dict, Any, List, Optional

class BinanceFuturesLiveFeed:
    """
    Live Real-Time Market Data Provider for Binance Futures USDT Perpetual Contracts.
    Connects to unblocked Binance Futures WebSocket stream (wss://stream.binancefuture.com/ws/!ticker@arr)
    to ingest all 400+ perpetual pairs with zero delay, including newly listed tokens.
    """
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(BinanceFuturesLiveFeed, cls).__new__(cls)
                cls._instance._initialized = False
            return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self.tickers: Dict[str, Dict[str, Any]] = {}
        self.data_lock = threading.Lock()
        self.running = True
        self.ready_event = threading.Event()
        self.last_update_ts = 0

        # Start background thread for continuous live WebSocket feed
        self.thread = threading.Thread(target=self._run_event_loop, daemon=True, name="BinanceFuturesLiveFeed")
        self.thread.start()

        # Wait briefly up to 4s for initial batch of tickers
        self.ready_event.wait(timeout=4.0)

    def _run_event_loop(self):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(self._worker())

    async def _worker(self):
        import websockets
        ws_url = "wss://stream.binancefuture.com/ws/!ticker@arr"
        
        while self.running:
            try:
                async with websockets.connect(ws_url, ping_interval=20, ping_timeout=10, close_timeout=5) as ws:
                    while self.running:
                        msg = await ws.recv()
                        data = json.loads(msg)
                        if not isinstance(data, list):
                            continue

                        stables = {
                            "USDCUSDT", "FDUSDUSDT", "TUSDUSDT", "USDPUSDT", 
                            "BUSDUSDT", "EURUSDT", "GBPUSDT", "USD1USDT", "AEURUSDT"
                        }
                        
                        updated = {}
                        now_ts = time.time()
                        for item in data:
                            sym = item.get("s", "")
                            if not sym.endswith("USDT") or sym in stables:
                                continue

                            try:
                                c_price = float(item.get("c", 0.0))
                                pct_chg = float(item.get("P", 0.0))
                                vol_usdt = float(item.get("q", 0.0))
                                high_24 = float(item.get("h", 0.0))
                                low_24 = float(item.get("l", 0.0))
                                
                                updated[sym] = {
                                    "symbol": sym,
                                    "price": c_price,
                                    "priceChangePercent": pct_chg,
                                    "quoteVolume": vol_usdt,
                                    "highPrice": high_24,
                                    "lowPrice": low_24,
                                    "updated_at": now_ts
                                }
                            except (ValueError, TypeError):
                                continue

                        if updated:
                            with self.data_lock:
                                self.tickers.update(updated)
                                self.last_update_ts = now_ts

                            if not self.ready_event.is_set():
                                self.ready_event.set()

            except Exception:
                await asyncio.sleep(2.0)

    def get_all_tickers(self) -> Dict[str, Dict[str, Any]]:
        with self.data_lock:
            return dict(self.tickers)

    def get_ticker(self, symbol: str) -> Optional[Dict[str, Any]]:
        sym = symbol.upper().strip()
        with self.data_lock:
            return self.tickers.get(sym)

    def get_all_symbols(self) -> List[str]:
        with self.data_lock:
            return list(self.tickers.keys())

    def get_top_symbols(self, limit: int = 50, sort_by: str = "volume") -> List[str]:
        with self.data_lock:
            all_t = list(self.tickers.values())

        if not all_t:
            return []

        if sort_by == "gainers":
            all_t.sort(key=lambda x: x.get("priceChangePercent", 0.0), reverse=True)
        elif sort_by == "losers":
            all_t.sort(key=lambda x: x.get("priceChangePercent", 0.0))
        else: # "volume"
            all_t.sort(key=lambda x: x.get("quoteVolume", 0.0), reverse=True)

        return [x["symbol"] for x in all_t[:limit]]

    def get_top_gainers(self, limit: int = 20) -> List[Dict[str, Any]]:
        with self.data_lock:
            all_t = list(self.tickers.values())
        all_t.sort(key=lambda x: x.get("priceChangePercent", 0.0), reverse=True)
        return all_t[:limit]


# Global Singleton Feed
futures_live_feed = BinanceFuturesLiveFeed()
