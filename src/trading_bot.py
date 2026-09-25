import time
import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from typing import Dict, List, Any, Optional
import pandas as pd

from src.execution_engine import BinanceExecutionEngine
from src.strategy_registry import get_strategy_instance
from src.data_fetcher import fetch_fast_api_klines

import json
import os

class LiveTradingBot:
    """
    Automated Trading Bot untuk Binance Futures (Live Demo & Real Account).
    100% Disiplin MQL5 1:1 Signal Execution & Live Plotting Synchronization.
    """
    _instance = None

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self):
        self.engine = BinanceExecutionEngine()
        self.is_running = False
        self.active_strategy_id = "binance_bband_wilder_rsi"
        self.timeframe = "1m"
        self.watchlist = ["XTZUSDT", "GUSDT", "ARUSDT", "ENAUSDT"]
        self.leverage = 3
        self.risk_pct = "fixed_250" # Default Fixed $250 USDT Notional Size
        self.max_open_positions = 10 # Maksimal 10 posisi terbuka secara simultan
        
        self.logs: List[Dict[str, str]] = []
        self.trade_history: List[Dict[str, Any]] = []
        self.last_traded_candles: Dict[str, Any] = {} # {symbol: timestamp}
        self.session_start_time = int(time.time() * 1000)
        self._thread: Optional[threading.Thread] = None

        self._log("SYSTEM", "Live Trading Bot Engine Initialized - Binance Pro Wilder Engine")

    def reset_session(self):
        """Reset total sesi trading baru dari modal awal $5,000"""
        self.stop()
        for p in self.engine.get_open_positions():
            self.engine.close_position(p["symbol"])
        
        self.trade_history.clear()
        self.logs.clear()
        self.last_traded_candles.clear()
        self.session_start_time = int(time.time() * 1000)
        
        if os.path.exists("data/bot_trades.json"):
            try:
                os.remove("data/bot_trades.json")
            except Exception:
                pass

        self._log("RESET", "🔄 Sesi trading telah di-reset dari awal! Modal bersih $5,000.00.")
        return {"status": "reset_success"}

    def _log(self, tag: str, message: str):
        now_str = datetime.now().strftime("%H:%M:%S")
        entry = {"time": now_str, "tag": tag, "message": message}
        self.logs.insert(0, entry)
        if len(self.logs) > 150:
            self.logs = self.logs[:150]
        try:
            print(f"[{now_str}] [{tag}] {message}")
        except Exception:
            safe_msg = message.encode('ascii', 'replace').decode('ascii')
            print(f"[{now_str}] [{tag}] {safe_msg}")

    def start(self, strategy_id: str, timeframe: str = "1m", watchlist: List[str] = None, leverage: int = 3, risk_pct: Any = 0.20):
        if self.is_running:
            return {"status": "already_running"}

        self.active_strategy_id = strategy_id
        self.timeframe = timeframe
        if watchlist:
            self.watchlist = [s.upper().strip() for s in watchlist]
        self.leverage = leverage
        self.risk_pct = risk_pct
        self.is_running = True
        self.start_time_ms = int(time.time() * 1000)
        self.last_traded_candles.clear()
        self._configured_leverage_symbols = set()

        risk_desc = f"{risk_pct*100:.0f}% Modal" if isinstance(risk_pct, (int, float)) and risk_pct <= 1.0 else str(risk_pct).replace("fixed_", "Fixed $") + " USDT"
        pairs_desc = f"{len(self.watchlist)} Koin (Auto-Hunt Universe)" if len(self.watchlist) > 12 else ', '.join(self.watchlist)
        self._log("START", f"🚀 BOT AKTIF (MQL5 1:1 STANDBY)! Pair: {pairs_desc} | TF: {timeframe} | Sizing: {risk_desc} ({leverage}x Lev)")

        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()
        return {"status": "started", "strategy": strategy_id, "timeframe": timeframe, "total_pairs": len(self.watchlist)}

    def stop(self):
        if not self.is_running:
            return {"status": "not_running"}
        self.is_running = False
        self._log("STOP", "🛑 Bot Automation dihentikan oleh pengguna.")
        return {"status": "stopped"}

    def get_status(self) -> Dict[str, Any]:
        bal = self.engine.get_account_balance()
        positions = self.engine.get_open_positions()
        
        # Only query recent trades for active positions and top 12 watchlist symbols to keep response instant
        symbols_to_query = list(set([p["symbol"] for p in positions] + self.watchlist[:12]))
        binance_trades = self.engine.get_account_trades(symbols_to_query, limit_per_sym=20, start_time_ms=self.session_start_time)
        
        session_net_pnl = sum(t.get("realized_pnl", 0.0) - t.get("commission", 0.0) for t in binance_trades)
        session_wallet_bal = round(5000.0 + session_net_pnl, 2)
        unrealized_pnl = sum(p.get("unrealized_pnl", 0.0) for p in positions)
        
        bal["total_wallet_balance"] = session_wallet_bal
        bal["available_balance"] = round(session_wallet_bal - bal.get("total_margin", 0.0), 2)
        bal["total_unrealized_pnl"] = round(unrealized_pnl, 2)
        bal["session_net_pnl"] = round(session_net_pnl, 2)

        return {
            "is_running": self.is_running,
            "active_strategy_id": self.active_strategy_id,
            "timeframe": self.timeframe,
            "watchlist": self.watchlist,
            "leverage": self.leverage,
            "risk_pct": self.risk_pct,
            "balance": bal,
            "open_positions": positions,
            "recent_logs": self.logs[:40],
            "trade_history": self.trade_history[:30],
            "binance_trades": binance_trades
        }

    def _run_loop(self):
        while self.is_running:
            try:
                self._scan_market()
            except Exception as e:
                self._log("ERROR", f"Error pemindaian market: {e}")

            # Polling kilat 500ms agar tepat mengeksekusi di detik :00 saat pergantian lilin
            for _ in range(5):
                if not self.is_running:
                    break
                time.sleep(0.1)

    def _scan_market(self):
        strategy = get_strategy_instance(self.active_strategy_id)
        open_positions = {p["symbol"]: p for p in self.engine.get_open_positions()}

        def scan_symbol(sym: str):
            if not self.is_running:
                return

            try:
                # Ambil 100 candle (ringan & cepat) untuk kalkulasi sinyal MQL5
                df = fetch_fast_api_klines(sym, self.timeframe, total_candles=100)
                if df is None or len(df) < 15:
                    return

                # Hitung sinyal strategi
                df_sig = strategy.generate_signals(df)
                
                # Lilin yang baru saja resmi ditutup (Bar 1 MQL5)
                closed_candle = df_sig.iloc[-2]
                closed_time = str(closed_candle["timestamp"])
                closed_signal = int(closed_candle.get("signal", 0))
                closed_close = float(closed_candle["close"])
                closed_ema = float(closed_candle.get("ema_7", closed_candle.get("ema_main", closed_close)))
                closed_high = float(closed_candle.get("high", closed_close))
                closed_low = float(closed_candle.get("low", closed_close))

                # Proteksi awal saat start bot
                if sym not in self.last_traded_candles:
                    self.last_traded_candles[sym] = closed_time
                    return

                # Wajib HANYA mengevaluasi saat lilin baru resmi close
                if self.last_traded_candles.get(sym) == closed_time:
                    return

                current_price = float(df_sig.iloc[-1]["close"])
                has_pos = sym in open_positions
                pos_side = open_positions[sym]["side"] if has_pos else None

                is_long_only = getattr(strategy, 'is_long_only', False)

                if closed_signal == 1:
                    # 🟢 BUY SIGNAL (Oversold Dip / Crossover)
                    self.last_traded_candles[sym] = closed_time
                    if has_pos and pos_side == "SHORT":
                        self._log("FLIP", f"⚡ REVERSAL: {sym} Close @ ${closed_close:.4f}. Close SHORT & Balik ke LONG!")
                        self.engine.close_position(sym)
                        time.sleep(0.3)
                    
                    if not has_pos or pos_side == "SHORT":
                        # Cek proteksi batas maksimal 10 posisi terbuka
                        live_open_count = len(self.engine.get_open_positions())
                        if not has_pos and live_open_count >= getattr(self, 'max_open_positions', 10):
                            self._log("MAX_POS", f"⏸️ Signal BUY {sym} diabaikan: Batas maksimal {self.max_open_positions} posisi terbuka aktif tercapai ({live_open_count}/{self.max_open_positions}).")
                            return

                        self._log("ENTRY", f"🟢 BUY SIGNAL: {sym} Dip Terpenuhi @ ${closed_close:.4f} ({self.active_strategy_id})")
                        self._open_order(sym, "BUY", current_price, closed_ema, closed_low, closed_time)

                elif closed_signal == -1:
                    self.last_traded_candles[sym] = closed_time
                    if is_long_only:
                        # 🎯 LONG-ONLY STRATEGY: HANYA TUTUP POSISI LONG (TAKE PROFIT / EXIT), JANGAN BUKA SHORT!
                        if has_pos and pos_side == "LONG":
                            self._log("EXIT", f"🎯 TAKE PROFIT / EXIT LONG: {sym} Close @ ${closed_close:.4f} (RSI Overbought Target Terpenuhi)!")
                            self.engine.close_position(sym)
                    else:
                        # 🔴 DUAL-DIRECTION STRATEGY: Buka SHORT / Reversal
                        if has_pos and pos_side == "LONG":
                            self._log("FLIP", f"⚡ REVERSAL: {sym} Close @ ${closed_close:.4f}. Close LONG & Balik ke SHORT!")
                            self.engine.close_position(sym)
                            time.sleep(0.3)
                        
                        if not has_pos or pos_side == "LONG":
                            live_open_count = len(self.engine.get_open_positions())
                            if not has_pos and live_open_count >= getattr(self, 'max_open_positions', 10):
                                self._log("MAX_POS", f"⏸️ Signal SELL {sym} diabaikan: Batas maksimal {self.max_open_positions} posisi terbuka aktif tercapai ({live_open_count}/{self.max_open_positions}).")
                                return

                            self._log("ENTRY", f"🔴 SELL SIGNAL: {sym} Trigger Terpenuhi @ ${closed_close:.4f} ({self.active_strategy_id})")
                            self._open_order(sym, "SELL", current_price, closed_ema, closed_high, closed_time)
                else:
                    self.last_traded_candles[sym] = closed_time
            except Exception as e:
                pass

        workers = min(len(self.watchlist), 25) if len(self.watchlist) > 0 else 1
        with ThreadPoolExecutor(max_workers=workers) as executor:
            list(executor.map(scan_symbol, self.watchlist))

    def _open_order(self, sym: str, side: str, entry_price: float, ema_val: float, extreme_val: float, candle_time: Any):
        # Konfigurasi leverage secara lazy hanya ketika hendak membuka posisi
        if not hasattr(self, '_configured_leverage_symbols'):
            self._configured_leverage_symbols = set()
        if sym not in self._configured_leverage_symbols:
            try:
                self.engine.set_leverage(sym, self.leverage)
                self._configured_leverage_symbols.add(sym)
            except Exception:
                pass

        bal = self.engine.get_account_balance()
        wallet_bal = bal.get("total_wallet_balance", 5000.0)
        avail_bal = bal.get("available_balance", wallet_bal)

        # Hitung ukuran notional size ($2,500 USDT)
        risk_val = getattr(self, "risk_pct", 0.20)
        if isinstance(risk_val, str) and risk_val.startswith("fixed_"):
            notional_size = float(risk_val.replace("fixed_", ""))
        elif isinstance(risk_val, (int, float)) and risk_val > 1.0:
            notional_size = float(risk_val)
        else:
            pct = float(risk_val) if risk_val else 0.20
            margin_per_trade = avail_bal * pct
            notional_size = max(margin_per_trade * self.leverage, 10.0)

        max_qty = notional_size / entry_price

        # Stop loss tipis di ekor lilin
        if side == "BUY":
            sl_price = max(float(extreme_val) * 0.999, entry_price * 0.9975)
        else:
            sl_price = min(float(extreme_val) * 1.001, entry_price * 1.0025)

        formatted_qty = self.engine.format_qty(sym, max_qty)
        self._log("ORDER", f"Mengirim order {side} {formatted_qty} {sym} ke Binance Testnet...")
        res = self.engine.place_order(
            symbol=sym,
            side=side,
            quantity=formatted_qty,
            stop_loss_price=sl_price,
            take_profit_price=None
        )

        if res.get("status") == "success":
            self.last_traded_candles[sym] = str(candle_time)
            self._log("SUCCESS", f"✅ Order Sukses: {side} {res.get('quantity')} {sym} @ ${res.get('entry_price')} | SL: ${sl_price:.4f}")
            self.trade_history.insert(0, res)
            if len(self.trade_history) > 100:
                self.trade_history = self.trade_history[:100]
        else:
            self._log("REJECT", f"❌ Order ditolak: {res.get('message')}")
