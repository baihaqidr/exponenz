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

SCREENER_PRESETS = {
    "top_10_pnl": ["ETHUSDT", "BTCUSDT", "SOLUSDT", "DOGEUSDT", "1000PEPEUSDT", "SUIUSDT", "NEARUSDT", "BNBUSDT", "AVAXUSDT", "ENAUSDT"],
    "top_12": ["ETHUSDT", "BTCUSDT", "SOLUSDT", "DOGEUSDT", "SUIUSDT", "NEARUSDT", "BNBUSDT", "1000PEPEUSDT", "AVAXUSDT", "LINKUSDT", "XRPUSDT", "ADAUSDT"],
    "top_25": ["ETHUSDT", "BTCUSDT", "SOLUSDT", "DOGEUSDT", "SUIUSDT", "NEARUSDT", "BNBUSDT", "1000PEPEUSDT", "AVAXUSDT", "LINKUSDT", "XRPUSDT", "ADAUSDT", "APTUSDT", "ARBUSDT", "OPUSDT", "INJUSDT", "TIAUSDT", "RENDERUSDT", "FETUSDT", "TAOUSDT", "SEIUSDT", "WIFUSDT", "1000SHIBUSDT", "DOTUSDT", "LTCUSDT"],
    "top_50": [
        "ETHUSDT", "BTCUSDT", "SOLUSDT", "DOGEUSDT", "SUIUSDT", "NEARUSDT", "BNBUSDT", "1000PEPEUSDT", "AVAXUSDT", "LINKUSDT",
        "XRPUSDT", "ADAUSDT", "APTUSDT", "ARBUSDT", "OPUSDT", "INJUSDT", "TIAUSDT", "RENDERUSDT", "FETUSDT", "TAOUSDT",
        "SEIUSDT", "WIFUSDT", "1000SHIBUSDT", "DOTUSDT", "LTCUSDT", "1000BONKUSDT", "1000FLOKIUSDT", "ENAUSDT", "HBARUSDT", "TRXUSDT",
        "FTMUSDT", "GALAUSDT", "SANDUSDT", "MANAUSDT", "CRVUSDT", "DYDXUSDT", "AAVEUSDT", "UNIUSDT", "PENDLEUSDT", "JTOUSDT",
        "JUPUSDT", "ORDIUSDT", "BLURUSDT", "KASUSDT", "STXUSDT", "ATOMUSDT", "FILUSDT", "ICPUSDT", "RUNEUSDT", "THETAUSDT"
    ],
    "all_coins": [
        "ETHUSDT", "BTCUSDT", "SOLUSDT", "DOGEUSDT", "SUIUSDT", "NEARUSDT", "BNBUSDT", "1000PEPEUSDT", "AVAXUSDT", "LINKUSDT",
        "XRPUSDT", "ADAUSDT", "APTUSDT", "ARBUSDT", "OPUSDT", "INJUSDT", "TIAUSDT", "RENDERUSDT", "FETUSDT", "TAOUSDT",
        "SEIUSDT", "WIFUSDT", "1000SHIBUSDT", "DOTUSDT", "LTCUSDT", "1000BONKUSDT", "1000FLOKIUSDT", "ENAUSDT", "HBARUSDT", "TRXUSDT",
        "FTMUSDT", "GALAUSDT", "SANDUSDT", "MANAUSDT", "CRVUSDT", "DYDXUSDT", "AAVEUSDT", "UNIUSDT", "PENDLEUSDT", "JTOUSDT",
        "JUPUSDT", "ORDIUSDT", "BLURUSDT", "KASUSDT", "STXUSDT", "ATOMUSDT", "FILUSDT", "ICPUSDT", "RUNEUSDT", "THETAUSDT",
        "ALGOUSDT", "AXSUSDT", "BCHUSDT", "ETCUSDT", "XLMUSDT", "GMXUSDT", "KAVAUSDT", "POLUSDT", "MKRUSDT", "SNXUSDT"
    ]
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

    def get_top_symbols(self, limit: int = 50, preset: str = None) -> List[str]:
        if preset and preset in SCREENER_PRESETS:
            return SCREENER_PRESETS[preset][:limit]

        # Use verified liquid universe directly to prevent low-cap / illiquid / dead tokens from cluttering the screener
        verified_pool = SCREENER_PRESETS.get("all_coins", [])
        return verified_pool[:limit]

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
            df = fetch_fast_api_klines(clean_sym, timeframe, total_candles=1000)
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

            # Run realistic backtest engine matching the Live Chart & Backtest Matrix exactly
            is_long_only = getattr(strat, "is_long_only", False)
            engine = BacktestEngine(initial_capital=1000.0, leverage=2.0, risk_per_trade_pct=0.02, is_long_only=is_long_only)
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

            # STRICT CRITERIA: A coin is marked as Active Open Signal if it currently holds an open position or has an active unclosed entry
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
            else:
                # Check recent candle signals (within last 3 candles) if not yet exited
                recent = sig_df.tail(3)
                for idx in range(len(recent) - 1, -1, -1):
                    r_row = recent.iloc[idx]
                    if r_row.get('exit_long', 0) == 1:
                        break
                    if r_row.get('enter_long', 0) == 1 or r_row.get('signal', 0) == 1:
                        is_open_signal = True
                        signal_side = "LONG"
                        entry_price = float(r_row['close'])
                        signal_badge = "🟢 SINYAL BUY AKTIF"
                        signal_color = "#10b981"
                        signal_desc = "Sinyal Buy Baru Terkonfirmasi"
                        if entry_price > 0:
                            gross_pct = ((curr_price - entry_price) / entry_price) * 100.0
                            live_pnl_pct = gross_pct - 0.08
                            live_pnl_usd = (live_pnl_pct / 100.0) * default_notional
                        break
                    elif not is_long_only and (r_row.get('enter_short', 0) == 1 or r_row.get('signal', 0) == -1):
                        is_open_signal = True
                        signal_side = "SHORT"
                        entry_price = float(r_row['close'])
                        signal_badge = "🔴 SINYAL SHORT AKTIF"
                        signal_color = "#f43f5e"
                        signal_desc = "Sinyal Short Baru Terkonfirmasi"
                        if entry_price > 0:
                            gross_pct = ((entry_price - curr_price) / entry_price) * 100.0
                            live_pnl_pct = gross_pct - 0.08
                            live_pnl_usd = (live_pnl_pct / 100.0) * default_notional
                        break

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

    def scan_strategy(self, strategy_id: str = "trend_rider_supertrend", timeframe: str = "15m", limit: int = 50, signal_only: bool = False, preset: str = None, custom_symbols: List[str] = None, method: str = "candle_spike_volume") -> List[Dict[str, Any]]:
        if strategy_id in ["pump_sniper", "pump", "pump_spikes"]:
            return self.scan_pump_spikes(timeframe=timeframe, limit=limit, preset=preset, custom_symbols=custom_symbols, method=method)

        now = time.time()
        preset_key = preset or ("custom" if custom_symbols else "all")
        cache_key = f"strat_{strategy_id}_{timeframe}_{limit}_{preset_key}"
        if not custom_symbols and cache_key in self.cache:
            entry = self.cache[cache_key]
            if now - entry["ts"] < self.cache_ttl:
                data = entry["data"]
                if signal_only:
                    return [x for x in data if x.get("is_open_signal")]
                return data

        if custom_symbols and len(custom_symbols) > 0:
            symbols = [s.upper().strip() for s in custom_symbols]
        else:
            symbols = self.get_top_symbols(limit=limit, preset=preset)

        results = []

        with ThreadPoolExecutor(max_workers=16) as executor:
            futures = [executor.submit(self.evaluate_symbol_strategy, sym, strategy_id, timeframe) for sym in symbols]
            for f in futures:
                res = f.result()
                if res:
                    results.append(res)

        # Sort: Open signals first, then by 24h change / volume
        results.sort(key=lambda x: (1 if x.get("is_open_signal") else 0, x.get("volume", 0)), reverse=True)

        if not custom_symbols:
            self.cache[cache_key] = {"data": results, "ts": now}
        if signal_only:
            return [x for x in results if x.get("is_open_signal")]
        return results

    def _evaluate_pump_spike(self, symbol: str, timeframe: str = "1m", method: str = "candle_spike_volume") -> Optional[Dict[str, Any]]:
        clean_sym = symbol.upper().strip()
        if clean_sym in FUTURES_PAIR_MAPPING:
            clean_sym = FUTURES_PAIR_MAPPING[clean_sym]

        try:
            from src.data_fetcher import fetch_fast_api_klines
            df = fetch_fast_api_klines(clean_sym, timeframe, total_candles=50)
            if df is None or len(df) < 20:
                return None

            curr_close = float(df['close'].iloc[-1])
            curr_open = float(df['open'].iloc[-1])
            curr_vol = float(df['volume'].iloc[-1]) if 'volume' in df.columns else 0.0

            # 1m Candle Spike %
            spike_1m_pct = ((curr_close - curr_open) / curr_open) * 100.0 if curr_open > 0 else 0.0
            
            # 5m Momentum %
            five_bar_open = float(df['open'].iloc[-5]) if len(df) >= 5 else curr_open
            spike_5m_pct = ((curr_close - five_bar_open) / five_bar_open) * 100.0 if five_bar_open > 0 else 0.0

            # 15m Momentum %
            fifteen_bar_open = float(df['open'].iloc[-15]) if len(df) >= 15 else five_bar_open
            spike_15m_pct = ((curr_close - fifteen_bar_open) / fifteen_bar_open) * 100.0 if fifteen_bar_open > 0 else 0.0

            # Volume Surge Multiplier
            past_vols = df['volume'].iloc[-21:-1] if 'volume' in df.columns and len(df) >= 21 else pd.Series([curr_vol])
            avg_vol = float(past_vols.mean()) if len(past_vols) > 0 else (curr_vol or 1.0)
            vol_mult = round(curr_vol / (avg_vol + 1e-6), 1) if avg_vol > 0 else 1.0

            # 1m RSI
            rsi = self._calculate_rsi(df['close'].values, period=14)

            # 24h Change % (estimate from 50 bars)
            chg_24h = ((curr_close - df['close'].iloc[0]) / df['close'].iloc[0]) * 100.0 if df['close'].iloc[0] > 0 else 0.0
            highest_50 = float(df['high'].max())
            is_breakout = (curr_close >= highest_50 * 0.995)

            # Status Badge & Detection by Method
            if method == "cumulative_5bar_momentum":
                is_active = (spike_5m_pct >= 2.0 or vol_mult >= 2.0)
                if spike_5m_pct >= 5.0:
                    badge = f"📈 5M WAVE (+{round(spike_5m_pct, 1)}%)"
                    badge_color = "#10b981"
                    status_desc = f"Gelombang momentum kuat +{round(spike_5m_pct, 2)}% dalam 5 lilin"
                elif spike_5m_pct >= 2.0:
                    badge = f"🔥 5M PUSH (+{round(spike_5m_pct, 1)}%)"
                    badge_color = "#06b6d4"
                    status_desc = f"Akumulasi dorongan bullish +{round(spike_5m_pct, 2)}%"
                else:
                    badge = "⚡ 5M NORMAL"
                    badge_color = "#8b5cf6"
                    status_desc = "Fluktuasi 5 bar wajar"
            elif method == "breakout_24h_high":
                is_active = is_breakout or (vol_mult >= 2.5)
                if is_breakout and vol_mult >= 2.0:
                    badge = "💥 BREAKOUT HIGH"
                    badge_color = "#10b981"
                    status_desc = f"Penembusan High terdekat dengan volume {vol_mult}x"
                elif is_breakout:
                    badge = "🚀 AT HIGH LEVEL"
                    badge_color = "#06b6d4"
                    status_desc = "Menyentuh level tertinggi 50 lilin"
                else:
                    badge = "📊 CONSOLIDATING"
                    badge_color = "#64748b"
                    status_desc = "Di bawah level resistance"
            elif method == "rapid_rsi_extreme":
                is_active = (rsi >= 70 or rsi <= 30)
                if rsi >= 75:
                    badge = f"🔥 RSI OVERBOUGHT ({round(rsi, 1)})"
                    badge_color = "#f59e0b"
                    status_desc = "Momentum beli ekstrem (Overbought)"
                elif rsi <= 25:
                    badge = f"🟢 RSI OVERSOLD ({round(rsi, 1)})"
                    badge_color = "#10b981"
                    status_desc = "Momentum jual jenuh (Oversold)"
                else:
                    badge = f"⚡ RSI NEUTRAL ({round(rsi, 1)})"
                    badge_color = "#64748b"
                    status_desc = "RSI dalam rentang normal"
            else: # candle_spike_volume
                is_active = (spike_1m_pct >= 2.0 or spike_5m_pct >= 4.0 or vol_mult >= 2.5)
                if spike_1m_pct >= 5.0 or spike_5m_pct >= 8.0:
                    badge = f"🚀 SUPER PUMP (+{round(spike_1m_pct, 1)}%)"
                    badge_color = "#10b981"
                    status_desc = f"Lonjakan harga ekstrem +{round(spike_1m_pct, 2)}% dalam 1m"
                elif vol_mult >= 3.0:
                    badge = f"⚡ VOL SURGE ({vol_mult}x)"
                    badge_color = "#f59e0b"
                    status_desc = f"Volume meledak {vol_mult}x lipat dari normal"
                elif spike_1m_pct >= 2.5:
                    badge = f"🔥 MOMENTUM (+{round(spike_1m_pct, 1)}%)"
                    badge_color = "#06b6d4"
                    status_desc = f"Momentum bullish kuat +{round(spike_1m_pct, 2)}%"
                elif spike_1m_pct <= -3.0:
                    badge = f"🔻 DUMP SPIKE ({round(spike_1m_pct, 1)}%)"
                    badge_color = "#f43f5e"
                    status_desc = f"Penurunan tajam {round(spike_1m_pct, 2)}%"
                else:
                    badge = "📈 NORMAL SPIKE"
                    badge_color = "#8b5cf6"
                    status_desc = "Fluktuasi harga wajar"

            return {
                "symbol": clean_sym,
                "current_price": curr_close,
                "spike_1m_pct": round(spike_1m_pct, 2),
                "spike_5m_pct": round(spike_5m_pct, 2),
                "spike_15m_pct": round(spike_15m_pct, 2),
                "vol_multiplier": vol_mult,
                "current_volume": round(curr_vol, 2),
                "rsi": round(rsi, 1),
                "price_change_pct": round(chg_24h, 2),
                "badge": badge,
                "badge_color": badge_color,
                "status_desc": status_desc,
                "is_pump": is_active
            }
        except Exception:
            return None

    def scan_pump_spikes(self, timeframe: str = "1m", min_pct: float = 2.0, min_vol_mult: float = 1.5, limit: int = 50, preset: str = None, custom_symbols: List[str] = None, method: str = "candle_spike_volume") -> List[Dict[str, Any]]:
        now = time.time()
        preset_key = preset or ("custom" if custom_symbols else "all")
        cache_key = f"pump_{method}_{timeframe}_{limit}_{preset_key}_{min_pct}_{min_vol_mult}"
        
        # 10 second fast cache for live momentum screener
        if not custom_symbols and cache_key in self.cache:
            entry = self.cache[cache_key]
            if now - entry["ts"] < 10:
                return entry["data"]

        if custom_symbols and len(custom_symbols) > 0:
            symbols = [s.upper().strip() for s in custom_symbols]
        else:
            symbols = self.get_top_symbols(limit=limit, preset=preset)

        results = []
        with ThreadPoolExecutor(max_workers=16) as executor:
            futures = [executor.submit(self._evaluate_pump_spike, sym, timeframe, method) for sym in symbols]
            for f in futures:
                res = f.result()
                if res:
                    results.append(res)

        # Sorting logic based on method
        if method == "cumulative_5bar_momentum":
            results.sort(key=lambda x: (x.get("spike_5m_pct", 0), x.get("vol_multiplier", 0)), reverse=True)
        elif method == "breakout_24h_high":
            results.sort(key=lambda x: (x.get("vol_multiplier", 0), x.get("price_change_pct", 0)), reverse=True)
        elif method == "rapid_rsi_extreme":
            results.sort(key=lambda x: (abs(x.get("rsi", 50) - 50), x.get("vol_multiplier", 0)), reverse=True)
        else:
            results.sort(key=lambda x: (x.get("spike_1m_pct", 0), x.get("vol_multiplier", 0)), reverse=True)

        if not custom_symbols:
            self.cache[cache_key] = {"data": results, "ts": now}
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
