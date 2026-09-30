import time
import requests
import urllib3
import pandas as pd
import numpy as np
from typing import List, Dict, Any, Optional
from concurrent.futures import ThreadPoolExecutor

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

FUTURES_PAIR_MAPPING = {
    "PEPEUSDT": "1000PEPEUSDT",
    "SHIBUSDT": "1000SHIBUSDT",
    "BONKUSDT": "1000BONKUSDT",
    "FLOKIUSDT": "1000FLOKIUSDT",
    "LUNCUSDT": "1000LUNCUSDT",
    "RATSUSDT": "1000RATSUSDT",
    "SATSUSDT": "1000SATSUSDT",
    "CATUSDT": "1000CATUSDT",
    "MOGUSDT": "1000MOGUSDT",
    "NEIROCTOUSDT": "1000NEIROCTOUSDT",
}

class BollingerScreenerEngine:
    """
    Mesin Screening Binance USDT-M Futures Multi-Timeframe.
    Menghitung:
    1. Bollinger Bandwidth (BBW%): (Upper - Lower) / Mid * 100%
    2. %B (Posisi Harga vs Bands): (Price - Lower) / (Upper - Lower)
    3. Status Ekstrem & Sinyal Open Position Strategi Stateful (100% Match dengan Live Chart).
    """
    def __init__(self):
        self.cache = {}
        self.cache_ttl = 15 # 15 detik cache per timeframe
        self.symbols_cache = []
        self.symbols_cache_ts = 0

    def get_top_symbols(self, limit: int = 60) -> List[str]:
        now = time.time()
        if self.symbols_cache and (now - self.symbols_cache_ts < 300):
            return self.symbols_cache[:limit]

        symbols = []
        urls = [
            "https://fapi.binance.com/fapi/v1/ticker/24hr",
            "https://testnet.binancefuture.com/fapi/v1/ticker/24hr",
            "https://data-api.binance.vision/api/v3/ticker/24hr"
        ]
        headers = {'User-Agent': 'Mozilla/5.0'}
        for u in urls:
            try:
                r = requests.get(u, headers=headers, verify=False, timeout=4)
                if r.status_code == 200:
                    data = r.json()
                    if isinstance(data, list) and len(data) > 0:
                        usdt_pairs = [
                            x for x in data 
                            if x.get('symbol', '').endswith('USDT') 
                            and not any(x['symbol'].startswith(s) for s in ['USDC', 'FDUSD', 'TUSD', 'EUR', 'BUSD', 'DAI'])
                        ]
                        usdt_pairs.sort(key=lambda x: float(x.get('quoteVolume', 0)), reverse=True)
                        mapped = []
                        for x in usdt_pairs:
                            s = x['symbol']
                            if s in FUTURES_PAIR_MAPPING:
                                s = FUTURES_PAIR_MAPPING[s]
                            if s not in mapped:
                                mapped.append(s)
                        if mapped:
                            symbols = mapped
                            break
            except Exception:
                continue

        if not symbols:
            symbols = [
                "BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "DOGEUSDT", "SUIUSDT", "NEARUSDT", "AVAXUSDT",
                "XRPUSDT", "LINKUSDT", "ADAUSDT", "APTUSDT", "ARBUSDT", "OPUSDT", "INJUSDT", "TIAUSDT",
                "RENDERUSDT", "FETUSDT", "TAOUSDT", "SEIUSDT", "WIFUSDT", "1000SHIBUSDT", "DOTUSDT", "LTCUSDT",
                "1000PEPEUSDT", "1000BONKUSDT", "1000FLOKIUSDT", "ENAUSDT", "ASTERUSDT", "HBARUSDT", "VTHOUSDT",
                "SAGAUSDT", "ONEUSDT", "GTCUSDT", "MAGICUSDT", "TRXUSDT"
            ]

        self.symbols_cache = symbols
        self.symbols_cache_ts = now
        return self.symbols_cache[:limit]

    def _calculate_rsi(self, closes: np.ndarray, period: int = 14) -> float:
        if len(closes) < period + 1:
            return 50.0
        deltas = np.diff(closes)
        seed = deltas[:period]
        up = seed[seed >= 0].sum() / period
        down = -seed[seed < 0].sum() / period
        if down == 0:
            return 100.0
        rs = up / down
        rsi = 100.0 - (100.0 / (1.0 + rs))

        # Wilder's Smoothing
        for delta in deltas[period:]:
            up_val = delta if delta > 0 else 0.0
            down_val = -delta if delta < 0 else 0.0
            up = (up * (period - 1) + up_val) / period
            down = (down * (period - 1) + down_val) / period
            if down == 0:
                rsi = 100.0
            else:
                rs = up / down
                rsi = 100.0 - (100.0 / (1.0 + rs))
        return float(rsi)

    def evaluate_symbol_strategy(self, symbol: str, strategy_id: str, timeframe: str = "15m") -> Optional[Dict[str, Any]]:
        clean_sym = symbol.upper().strip()
        if clean_sym in FUTURES_PAIR_MAPPING:
            clean_sym = FUTURES_PAIR_MAPPING[clean_sym]

        try:
            from src.data_fetcher import fetch_fast_api_klines
            df = fetch_fast_api_klines(clean_sym, timeframe, total_candles=500)
            if df is None or len(df) < 30:
                return None

            from src.strategy_registry import get_strategy_instance
            from src.backtester import BacktestEngine
            strat = get_strategy_instance(strategy_id)
            sig_df = strat.generate_signals(df)

            curr_price = float(df['close'].iloc[-1])
            curr_volume = float(df['volume'].iloc[-1]) if 'volume' in df.columns else 0.0
            price_change_pct = ((curr_price - df['close'].iloc[0]) / df['close'].iloc[0]) * 100.0 if df['close'].iloc[0] > 0 else 0.0

            # Dynamic SL & TP extraction
            sl_price = None
            tp_price = None
            if 'sl_price' in sig_df and not pd.isna(sig_df['sl_price'].iloc[-1]):
                sl_price = float(sig_df['sl_price'].iloc[-1])
            if 'tp_price' in sig_df and not pd.isna(sig_df['tp_price'].iloc[-1]):
                tp_price = float(sig_df['tp_price'].iloc[-1])

            # Hitung RSI & BB untuk info ringkas
            rsi = self._calculate_rsi(df['close'].values, period=14)
            window_closes = df['close'].values[-20:]
            sma = float(np.mean(window_closes))
            std = float(np.std(window_closes))
            upper_band = sma + (2.0 * std)
            lower_band = sma - (2.0 * std)
            bbw = ((upper_band - lower_band) / sma) * 100.0 if sma > 0 else 0.0

            # Indicator summary text
            indicator_summary = f"RSI: {round(rsi, 1)} | BBW: {round(bbw, 1)}%"
            if 'supertrend' in sig_df and not pd.isna(sig_df['supertrend'].iloc[-1]):
                st_val = float(sig_df['supertrend'].iloc[-1])
                st_dir = "Bullish" if sig_df.get('st_dir', pd.Series([1])).iloc[-1] == 1 else "Bearish"
                indicator_summary = f"Supertrend: {st_dir} (${round(st_val, 4)}) | RSI: {round(rsi, 1)}"
            elif 'ema_fast' in sig_df and not pd.isna(sig_df['ema_fast'].iloc[-1]):
                f_val = float(sig_df['ema_fast'].iloc[-1])
                s_val = float(sig_df['ema_slow'].iloc[-1])
                indicator_summary = f"EMA9: ${round(f_val, 4)} | EMA21: ${round(s_val, 4)}"

            # Run realistic backtest engine matching the Live Chart exactly
            is_long_only = getattr(strat, "is_long_only", False)
            engine = BacktestEngine(initial_capital=1000.0, leverage=3.0, risk_per_trade_pct="fixed_250", is_long_only=is_long_only)
            bt_res = engine.run(sig_df)
            open_pos = bt_res.get("open_position")

            is_open_signal = False
            signal_side = "STANDBY"
            signal_badge = "⏳ STANDBY"
            signal_color = "#64748b"
            signal_desc = "Menunggu konfirmasi setup strategi"
            entry_price = 0.0
            holding_str = "-"
            live_pnl_pct = 0.0
            live_pnl_usd = 0.0
            default_notional = 50.0

            # STRICT CRITERIA: A coin is marked as Active Open Signal ONLY if it currently holds an open position (BUY executed and NOT closed)
            if open_pos is not None:
                is_open_signal = True
                signal_side = open_pos.get("type", "LONG")
                entry_price = float(open_pos.get("entry_price", curr_price))
                entry_time = open_pos.get("entry_time")

                if entry_time:
                    try:
                        latest_time = df['timestamp'].iloc[-1]
                        dur = pd.to_datetime(latest_time) - pd.to_datetime(entry_time)
                        dur_h = int(dur.total_seconds() // 3600)
                        dur_m = int((dur.total_seconds() % 3600) // 60)
                        holding_str = f"{dur_h}j {dur_m}m" if dur_h > 0 else f"{dur_m}m"
                    except Exception:
                        holding_str = "Aktif"

                if signal_side == "LONG" and entry_price > 0:
                    gross_pct = ((curr_price - entry_price) / entry_price) * 100.0
                    fee_pct = 0.08
                    live_pnl_pct = gross_pct - fee_pct
                    live_pnl_usd = (live_pnl_pct / 100.0) * default_notional
                    signal_badge = "🟢 POSISI LONG AKTIF"
                    signal_color = "#10b981"
                    signal_desc = f"Posisi Long Terbuka ({holding_str})"
                elif signal_side == "SHORT" and entry_price > 0:
                    gross_pct = ((entry_price - curr_price) / entry_price) * 100.0
                    fee_pct = 0.08
                    live_pnl_pct = gross_pct - fee_pct
                    live_pnl_usd = (live_pnl_pct / 100.0) * default_notional
                    signal_badge = "🔴 POSISI SHORT AKTIF"
                    signal_color = "#f43f5e"
                    signal_desc = f"Posisi Short Terbuka ({holding_str})"

            return {
                "symbol": clean_sym,
                "timeframe": timeframe,
                "strategy_id": strategy_id,
                "strategy_name": getattr(strat, "name", strategy_id),
                "entry_price": entry_price,
                "current_price": curr_price,
                "live_pnl_pct": round(live_pnl_pct, 2),
                "live_pnl_usd": round(live_pnl_usd, 3),
                "is_open_signal": is_open_signal,
                "signal_side": signal_side,
                "signal_badge": signal_badge,
                "signal_color": signal_color,
                "signal_desc": signal_desc,
                "sl_price": round(sl_price, 6) if sl_price and sl_price < 1 else (round(sl_price, 4) if sl_price else None),
                "tp_price": round(tp_price, 6) if tp_price and tp_price < 1 else (round(tp_price, 4) if tp_price else None),
                "rsi": round(rsi, 1),
                "bandwidth_pct": round(bbw, 2),
                "upper_band": round(upper_band, 6) if upper_band < 1 else round(upper_band, 4),
                "lower_band": round(lower_band, 6) if lower_band < 1 else round(lower_band, 4),
                "indicator_summary": indicator_summary,
                "price_change_pct": round(price_change_pct, 2),
                "volume": round(curr_volume, 2)
            }
        except Exception as e:
            return None

    def scan_strategy(self, strategy_id: str = "trend_rider_supertrend", timeframe: str = "15m", limit: int = 50, signal_only: bool = False) -> List[Dict[str, Any]]:
        now = time.time()
        cache_key = f"strat_{strategy_id}_{timeframe}_{limit}"
        if cache_key in self.cache:
            entry = self.cache[cache_key]
            if now - entry["ts"] < self.cache_ttl:
                data = entry["data"]
                if signal_only:
                    return [x for x in data if x.get("is_open_signal")]
                return data

        symbols = self.get_top_symbols(limit=limit)
        results = []

        with ThreadPoolExecutor(max_workers=16) as executor:
            futures = [executor.submit(self.evaluate_symbol_strategy, sym, strategy_id, timeframe) for sym in symbols]
            for f in futures:
                res = f.result()
                if res:
                    results.append(res)

        # Sort: Open signals first, then by RSI / volume
        results.sort(key=lambda x: (1 if x.get("is_open_signal") else 0, x.get("volume", 0)), reverse=True)

        self.cache[cache_key] = {"data": results, "ts": now}
        if signal_only:
            return [x for x in results if x.get("is_open_signal")]
        return results

    def scan_all(self, timeframe: str = "15m", limit: int = 50) -> List[Dict[str, Any]]:
        now = time.time()
        cache_key = f"{timeframe}_{limit}"
        if cache_key in self.cache:
            entry = self.cache[cache_key]
            if now - entry["ts"] < self.cache_ttl:
                return entry["data"]

        symbols = self.get_top_symbols(limit=limit)
        results = []

        # Multi-threaded concurrent scan
        with ThreadPoolExecutor(max_workers=16) as executor:
            futures = [executor.submit(self._fetch_klines_and_calc_bb, sym, timeframe) for sym in symbols]
            for f in futures:
                res = f.result()
                if res:
                    results.append(res)

        # Default sort by Bandwidth % descending (terbesar ke terkecil)
        results.sort(key=lambda x: x.get("bandwidth_pct", 0.0), reverse=True)

        self.cache[cache_key] = {"data": results, "ts": now}
        return results

# Global Singleton
bollinger_screener = BollingerScreenerEngine()
