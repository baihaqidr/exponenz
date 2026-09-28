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

    def _fetch_klines_and_calc_bb(self, symbol: str, timeframe: str = "15m", period: int = 20, std_dev: float = 2.0) -> Optional[Dict[str, Any]]:
        clean_sym = symbol.upper().strip()
        spot_sym = clean_sym[4:] if clean_sym.startswith("1000") else clean_sym

        # Fetch Klines
        urls = [
            f"https://data-api.binance.vision/api/v3/klines?symbol={spot_sym}&interval={timeframe}&limit={period + 30}",
            f"https://testnet.binancefuture.com/fapi/v1/klines?symbol={clean_sym}&interval={timeframe}&limit={period + 30}"
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

            # %B (Posisi relatif harga di dalam band: <0 = tembus bawah, >1 = tembus atas)
            band_range = upper_band - lower_band
            if band_range > 0:
                percent_b = ((curr_price - lower_band) / band_range) * 100.0
            else:
                percent_b = 50.0

            # 24h change estimasi dari candle awal
            price_change_pct = ((curr_price - closes[0]) / closes[0]) * 100.0 if closes[0] > 0 else 0.0

            # Klasifikasi Kondisi Bollinger
            if percent_b >= 100.0:
                signal = "SUPER BREAKOUT (ABOVE UPPER)"
                signal_color = "#10b981"
                signal_badge = "🔥 TEMBUS UPPER"
            elif percent_b <= 0.0:
                signal = "SUPER DUMP (BELOW LOWER)"
                signal_color = "#f43f5e"
                signal_badge = "⚠️ TEMBUS LOWER"
            elif bandwidth_pct >= 12.0:
                signal = "SUPER EXPANSION (HIGH VOLATILITY)"
                signal_color = "#3b82f6"
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
                "upper_band": round(upper_band, 6) if upper_band < 1 else round(upper_band, 4),
                "mid_band": round(sma, 6) if sma < 1 else round(sma, 4),
                "lower_band": round(lower_band, 6) if lower_band < 1 else round(lower_band, 4),
                "bandwidth_pct": round(bandwidth_pct, 2),
                "percent_b": round(percent_b, 1),
                "price_change_pct": round(price_change_pct, 2),
                "signal": signal,
                "signal_color": signal_color,
                "signal_badge": signal_badge,
                "volume": round(curr_volume, 2)
            }
        except Exception as e:
            return None

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
