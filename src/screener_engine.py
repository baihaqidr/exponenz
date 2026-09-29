import time
import requests
import urllib3
import pandas as pd
import numpy as np
from typing import List, Dict, Any, Optional
from concurrent.futures import ThreadPoolExecutor

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class BollingerScreenerEngine:
    """
    Mesin Screening Bollinger Bands Binance Futures Multi-Timeframe.
    Menghitung:
    1. Bollinger Bandwidth (BBW%): (Upper - Lower) / Mid * 100%
    2. %B (Posisi Harga vs Bands): (Price - Lower) / (Upper - Lower)
    3. Status Ekstrem: Super Expansion (Ledakan Tren) vs Super Squeeze (Persiapan Ledakan).
    """
    def __init__(self):
        self.cache = {}
        self.cache_ttl = 15 # 15 detik cache per timeframe
        self.symbols_cache = []
        self.symbols_cache_ts = 0

    def get_top_symbols(self, limit: int = 60) -> List[str]:
        now = time.time()
        if self.symbols_cache and (now - self.symbols_cache_ts < 600):
            return self.symbols_cache[:limit]

        symbols = []
        urls = [
            "https://data-api.binance.vision/api/v3/ticker/24hr",
            "https://api.binance.com/api/v3/ticker/24hr"
        ]
        headers = {'User-Agent': 'Mozilla/5.0'}
        for u in urls:
            try:
                r = requests.get(u, headers=headers, verify=False, timeout=5)
                if r.status_code == 200:
                    data = r.json()
                    if isinstance(data, list):
                        usdt_pairs = [
                            x for x in data 
                            if x.get('symbol', '').endswith('USDT') 
                            and not any(x['symbol'].startswith(s) for s in ['USDC', 'FDUSD', 'TUSD', 'EUR', 'BUSD', 'DAI'])
                        ]
                        # Urutkan berdasarkan quote volume 24h tertinggi
                        usdt_pairs.sort(key=lambda x: float(x.get('quoteVolume', 0)), reverse=True)
                        symbols = [x['symbol'] for x in usdt_pairs]
                        break
            except Exception:
                continue

        if not symbols:
            symbols = [
                "BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "DOGEUSDT", "SUIUSDT", "NEARUSDT", "AVAXUSDT",
                "XRPUSDT", "LINKUSDT", "ADAUSDT", "APTUSDT", "ARBUSDT", "OPUSDT", "INJUSDT", "TIAUSDT",
                "RENDERUSDT", "FETUSDT", "TAOUSDT", "SEIUSDT", "WIFUSDT", "SHIBUSDT", "DOTUSDT", "LTCUSDT",
                "PEPEUSDT", "1000PEPEUSDT", "SAGAUSDT", "ONEUSDT", "GTCUSDT", "MAGICUSDT", "TRXUSDT"
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

    def _fetch_klines_and_calc_bb(self, symbol: str, timeframe: str = "15m", period: int = 20, std_dev: float = 2.0) -> Optional[Dict[str, Any]]:
        clean_sym = symbol.upper().strip()
        spot_sym = clean_sym[4:] if clean_sym.startswith("1000") else clean_sym

        # Fetch Klines (70 candles for accurate RSI 14 & BB 20)
        limit_count = 70
        urls = [
            f"https://data-api.binance.vision/api/v3/klines?symbol={spot_sym}&interval={timeframe}&limit={limit_count}",
            f"https://testnet.binancefuture.com/fapi/v1/klines?symbol={clean_sym}&interval={timeframe}&limit={limit_count}"
        ]
        headers = {'User-Agent': 'Mozilla/5.0'}
        candles = None
        for u in urls:
            try:
                r = requests.get(u, headers=headers, verify=False, timeout=3)
                if r.status_code == 200:
                    d = r.json()
                    if isinstance(d, list) and len(d) >= period:
                        candles = d
                        break
            except Exception:
                continue

        if not candles:
            return None

        try:
            closes = np.array([float(c[4]) for c in candles], dtype=np.float64)
            highs = np.array([float(c[2]) for c in candles], dtype=np.float64)
            lows = np.array([float(c[3]) for c in candles], dtype=np.float64)
            volumes = np.array([float(c[5]) for c in candles], dtype=np.float64)

            curr_price = float(closes[-1])
            curr_volume = float(volumes[-1])

            # Hitung RSI (14 period)
            rsi = self._calculate_rsi(closes, period=14)

            # Hitung Bollinger Bands (SMA 20 & Standard Deviation 2.0)
            window_closes = closes[-period:]
            sma = float(np.mean(window_closes))
            std = float(np.std(window_closes))

            upper_band = sma + (std_dev * std)
            lower_band = sma - (std_dev * std)

            # Bollinger Bandwidth % (BBW)
            if sma > 0:
                bandwidth_pct = ((upper_band - lower_band) / sma) * 100.0
            else:
                bandwidth_pct = 0.0

            # %B (Posisi relatif harga di dalam band: <0 = tembus bawah, >100 = tembus atas)
            band_range = upper_band - lower_band
            if band_range > 0:
                percent_b = ((curr_price - lower_band) / band_range) * 100.0
            else:
                percent_b = 50.0

            # 24h change estimasi dari candle awal
            price_change_pct = ((curr_price - closes[0]) / closes[0]) * 100.0 if closes[0] > 0 else 0.0

            # Klasifikasi Kondisi Bollinger & RSI Combo
            is_oversold_combo = (curr_price <= lower_band or percent_b <= 0.0) and (rsi <= 30.0)
            is_overbought_combo = (curr_price >= upper_band or percent_b >= 100.0) and (rsi >= 70.0)

            if is_oversold_combo:
                signal = "SUPER OVERSOLD (RSI < 30 & BELOW LOWER)"
                signal_color = "#10b981"
                signal_badge = "🚀 OVERSOLD LONG (RSI<30)"
            elif is_overbought_combo:
                signal = "SUPER OVERBOUGHT (RSI > 70 & ABOVE UPPER)"
                signal_color = "#f43f5e"
                signal_badge = "⚠️ OVERBOUGHT SHORT (RSI>70)"
            elif percent_b >= 100.0:
                signal = "SUPER BREAKOUT (ABOVE UPPER)"
                signal_color = "#38bdf8"
                signal_badge = "🔥 TEMBUS UPPER"
            elif percent_b <= 0.0:
                signal = "SUPER DUMP (BELOW LOWER)"
                signal_color = "#fb7185"
                signal_badge = "📉 TEMBUS LOWER"
            elif rsi <= 30.0:
                signal = "RSI OVERSOLD (RSI < 30)"
                signal_color = "#34d399"
                signal_badge = "💎 RSI OVERSOLD"
            elif rsi >= 70.0:
                signal = "RSI OVERBOUGHT (RSI > 70)"
                signal_color = "#f87171"
                signal_badge = "⚡ RSI OVERBOUGHT"
            elif bandwidth_pct >= 12.0:
                signal = "SUPER EXPANSION (HIGH VOLATILITY)"
                signal_color = "#60a5fa"
                signal_badge = "⚡ SUPER EXPANSION"
            elif bandwidth_pct <= 3.0:
                signal = "SUPER SQUEEZE (READY TO EXPLODE)"
                signal_color = "#f59e0b"
                signal_badge = "🎯 SUPER SQUEEZE"
            else:
                signal = "NORMAL VOLATILITY"
                signal_color = "#64748b"
                signal_badge = "NORMAL"

            return {
                "symbol": clean_sym,
                "timeframe": timeframe,
                "current_price": curr_price,
                "rsi": round(rsi, 2),
                "upper_band": round(upper_band, 6) if upper_band < 1 else round(upper_band, 4),
                "mid_band": round(sma, 6) if sma < 1 else round(sma, 4),
                "lower_band": round(lower_band, 6) if lower_band < 1 else round(lower_band, 4),
                "bandwidth_pct": round(bandwidth_pct, 2),
                "percent_b": round(percent_b, 1),
                "price_change_pct": round(price_change_pct, 2),
                "signal": signal,
                "signal_color": signal_color,
                "signal_badge": signal_badge,
                "is_oversold_combo": is_oversold_combo,
                "volume": round(curr_volume, 2)
            }
        except Exception as e:
            return None

    def _fetch_klines_df(self, symbol: str, timeframe: str = "15m", limit: int = 80) -> Optional[pd.DataFrame]:
        clean_sym = symbol.upper().strip()
        spot_sym = clean_sym[4:] if clean_sym.startswith("1000") else clean_sym

        urls = [
            f"https://data-api.binance.vision/api/v3/klines?symbol={spot_sym}&interval={timeframe}&limit={limit}",
            f"https://testnet.binancefuture.com/fapi/v1/klines?symbol={clean_sym}&interval={timeframe}&limit={limit}",
            f"https://api.binance.com/api/v3/klines?symbol={spot_sym}&interval={timeframe}&limit={limit}"
        ]
        headers = {'User-Agent': 'Mozilla/5.0'}
        candles = None
        for u in urls:
            try:
                r = requests.get(u, headers=headers, verify=False, timeout=3.5)
                if r.status_code == 200:
                    d = r.json()
                    if isinstance(d, list) and len(d) >= 20:
                        candles = d
                        break
            except Exception:
                continue

        if not candles:
            return None

        try:
            df = pd.DataFrame(candles, columns=[
                'timestamp', 'open', 'high', 'low', 'close', 'volume',
                'close_time', 'quote_volume', 'trades', 'taker_buy_base', 'taker_buy_quote', 'ignored'
            ])
            for col in ['open', 'high', 'low', 'close', 'volume']:
                df[col] = df[col].astype(float)
            return df
        except Exception:
            return None

    def evaluate_symbol_strategy(self, symbol: str, strategy_id: str, timeframe: str = "15m") -> Optional[Dict[str, Any]]:
        df = self._fetch_klines_df(symbol, timeframe, limit=80)
        if df is None or len(df) < 20:
            return None

        try:
            from src.strategy_registry import get_strategy_instance
            strat = get_strategy_instance(strategy_id)
            sig_df = strat.generate_signals(df)

            curr_price = float(df['close'].iloc[-1])
            curr_volume = float(df['volume'].iloc[-1])
            price_change_pct = ((curr_price - df['close'].iloc[0]) / df['close'].iloc[0]) * 100.0 if df['close'].iloc[0] > 0 else 0.0

            # Signal evaluation on latest candles
            last_sig = int(sig_df['signal'].iloc[-1]) if 'signal' in sig_df else 0
            prev_sig = int(sig_df['signal'].iloc[-2]) if len(sig_df) >= 2 and 'signal' in sig_df else 0
            
            enter_long = int(sig_df['enter_long'].iloc[-1]) if 'enter_long' in sig_df else (1 if last_sig == 1 else 0)
            enter_short = int(sig_df['enter_short'].iloc[-1]) if 'enter_short' in sig_df else (1 if last_sig == -1 else 0)

            # Check status
            is_open_signal = False
            signal_side = "STANDBY"
            signal_badge = "⏳ STANDBY"
            signal_color = "#64748b"
            signal_desc = "Menunggu konfirmasi setup strategi"

            if last_sig == 1 or enter_long == 1:
                is_open_signal = True
                signal_side = "LONG"
                signal_badge = "🟢 OPEN LONG ENTRY"
                signal_color = "#10b981"
                signal_desc = f"Trigger Buy/Long Aktif ({timeframe})"
            elif last_sig == -1 or enter_short == 1:
                is_open_signal = True
                signal_side = "SHORT"
                signal_badge = "🔴 OPEN SHORT ENTRY"
                signal_color = "#f43f5e"
                signal_desc = f"Trigger Sell/Short Aktif ({timeframe})"
            elif prev_sig == 1:
                is_open_signal = True
                signal_side = "LONG"
                signal_badge = "⚡ RECENT LONG (1 Bar)"
                signal_color = "#059669"
                signal_desc = f"Trigger Long 1 lilin lalu ({timeframe})"
            elif prev_sig == -1:
                is_open_signal = True
                signal_side = "SHORT"
                signal_badge = "⚡ RECENT SHORT (1 Bar)"
                signal_color = "#e11d48"
                signal_desc = f"Trigger Short 1 lilin lalu ({timeframe})"

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

            # Entry Trigger Price & Live Floating PnL
            if prev_sig == 1 or prev_sig == -1:
                entry_price = float(df['close'].iloc[-2])
            else:
                entry_price = float(df['open'].iloc[-1]) if len(df) >= 1 else curr_price

            live_pnl_pct = 0.0
            live_pnl_usd = 0.0
            default_notional = 50.0

            if signal_side == "LONG" and entry_price > 0:
                gross_pct = ((curr_price - entry_price) / entry_price) * 100.0
                fee_pct = 0.08
                live_pnl_pct = gross_pct - fee_pct
                live_pnl_usd = (live_pnl_pct / 100.0) * default_notional
            elif signal_side == "SHORT" and entry_price > 0:
                gross_pct = ((entry_price - curr_price) / entry_price) * 100.0
                fee_pct = 0.08
                live_pnl_pct = gross_pct - fee_pct
                live_pnl_usd = (live_pnl_pct / 100.0) * default_notional

            return {
                "symbol": symbol.upper().strip(),
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
                "upper_band": round(upper_band, 4),
                "lower_band": round(lower_band, 4),
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
