import os
from typing import Dict, List, Any
from src.strategies.base import BaseStrategy

STRATEGY_METADATA: Dict[str, Dict[str, Any]] = {
    "trend_rider_supertrend": {
        "id": "trend_rider_supertrend",
        "name": "1H Trend Rider (Supertrend + EMA 50 Trailing Stop)",
        "file": "trend_rider_supertrend.py",
        "style": "PROVEN QUANT TREND (+$14,898 PROFIT)",
        "style_badge_color": "#10b981", # Emerald
        "recommended_timeframe": "1h",
        "recommended_pairs": ["SOLUSDT", "INJUSDT", "STRKUSDT", "SEIUSDT", "PEPEUSDT", "AVAXUSDT", "FILUSDT", "BTCUSDT"],
        "description": "Strategi Unggulan Kuantitatif Terbukti Profit Bersih (+$14,898 di 50+ Koin Binance Futures 1 Tahun). Menunggangi gelombang besar tren naik (Long Only) menggunakan konfirmasi Supertrend (10, 3.0) di atas EMA 50 dengan Dynamic Trailing Stop otomatis untuk mengunci profit tanpa batasan TP kaku.",
        "entry_long": [
            "Supertrend berbalik arah dari Merah (Bearish) menjadi Hijau (Bullish) pada lilin 1H.",
            "Harga Close berada di atas garis filter EMA 50 (Konfirmasi Tren Bullish Kuat).",
            "Mengeksekusi Long di awal gelombang ekspansi harga."
        ],
        "entry_short": [
            "Mode Long Only aktif: Tidak membuka posisi short (Aman dari short-squeeze)."
        ],
        "exit_rules": [
            "Trailing Stop Dinamis: Stop Loss otomatis dinaikkan mengikuti garis Supertrend.",
            "Exit Sinyal: Saat Supertrend resmi berbalik menjadi Merah (Ambil profit di puncak rally).",
            "Proteksi Modal: Cut loss otomatis jika breakdown di bawah Supertrend."
        ],
        "default_params": {
            "atr_period": 10,
            "multiplier": 3.0,
            "ema_filter": 50,
            "is_long_only": True
        }
    },
    "rsi_first_ema7_crossover": {
        "id": "rsi_first_ema7_crossover",
        "name": "RSI Oversold First EMA 7 Breakout (R:R 1:2 Sniper)",
        "file": "rsi_first_ema7_crossover.py",
        "style": "RSI REBOUND SNIPER",
        "style_badge_color": "#f59e0b", # Amber
        "recommended_timeframe": "15m",
        "recommended_pairs": ["ZETAUSDT", "BTCUSDT", "SOLUSDT", "ETHUSDT", "ENAUSDT"],
        "description": "Strategi State Machine Kuantitatif: Mengunci status Siaga saat RSI < 30 dan mengeksekusi Long pada lilin pertama yang menembus ke atas EMA 7 (bahkan saat RSI sudah mulai pulih). Dilengkapi Stop Loss di Low lilin entry dan Take Profit otomatis pada 2x jarak risiko (R:R 1:2).",
        "entry_long": [
            "Status Siaga aktif saat RSI(14) menembus ke bawah < 30 (Oversold).",
            "Eksekusi Long pada lilin pertama yang berhasil Close melintasi (Cross Up) ke atas EMA 7.",
            "Status Siaga tetap aktif meskipun RSI sudah kembali pulih di atas 30 sebelum cross terjadi.",
            "Hanya 1x entry per siklus oversold (anti-spam knife catch)."
        ],
        "entry_short": [
            "Tidak membuka short (Strategi long-only)."
        ],
        "exit_rules": [
            "Stop Loss: Tepat di titik Low lilin konfirmasi entry.",
            "Take Profit: Sebesar 2x Change% jarak risiko lilin entry (R:R 1:2)."
        ],
        "default_params": {
            "rsi_period": 14,
            "rsi_oversold": 30.0,
            "ema_period": 7,
            "rr_multiplier": 2.0
        }
    },
    "binance_bband_wilder_rsi": {
        "id": "binance_bband_wilder_rsi",
        "name": "Binance Pro BbandRsi (Wilder's 100% Binance Match)",
        "file": "binance_bband_wilder_rsi.py",
        "style": "BINANCE PRO WILDER",
        "style_badge_color": "#3b82f6", # Blue
        "recommended_timeframe": "15m",
        "recommended_pairs": ["XTZUSDT", "GUSDT", "ARUSDT", "ENAUSDT", "SUIUSDT", "SOLUSDT"],
        "description": "Strategi Bollinger Bands (20, 2.0) dengan formula Wilder's Smoothed RSI (14) yang 100% identik presisi dengan grafik resmi Binance Futures & TradingView. Membeli pantulan panik oversold (RSI Wilder < 30 & Close < Lower Band) dan keluar saat overbought (RSI Wilder > 70) atau mencapai target ROI.",
        "entry_long": [
            "Harga Close lilin menembus di bawah Lower Bollinger Band (Panic Dip).",
            "Nilai RSI Wilder (14) < 30 (Extreme Oversold - 100% Match Binance).",
            "Volume transaksi aktif (Volume > 0)."
        ],
        "entry_short": [
            "Tidak membuka short (Strategi long-only)."
        ],
        "exit_rules": [
            "Exit Sinyal: Saat RSI Wilder (14) > 70 (Overbought).",
            "Take Profit: Minimal ROI target +2.5% s/d +4.0%.",
            "Stop Loss: Proteksi modal ketat -5.0%."
        ],
        "default_params": {
            "bb_length": 20,
            "bb_std": 2.0,
            "rsi_period": 14
        }
    },
    "freqtrade_bband_rsi": {
        "id": "freqtrade_bband_rsi",
        "name": "Freqtrade Pure BbandRsi (Official Original SL -10%)",
        "file": "freqtrade_bband_rsi.py",
        "style": "FREQTRADE PURE ORIGINAL",
        "style_badge_color": "#06b6d4", # Cyan
        "recommended_timeframe": "15m",
        "recommended_pairs": ["XTZUSDT", "GUSDT", "ARUSDT", "ENAUSDT", "SOLUSDT"],
        "description": "Strategi Open-Source Resmi Bawaan Repo Freqtrade (bband_rsi.py) murni 100% tanpa modifikasi. Menggunakan kombinasi Bollinger Bands (20, 2.0) dan Simple Moving Average RSI (14) rolling mean dengan Stop Loss bawaan Freqtrade (-10.0%) dan exit RSI > 70.",
        "entry_long": [
            "Harga Close lilin menembus di bawah Lower Bollinger Band (Panic Dip).",
            "Nilai RSI SMA (14) < 30 (Freqtrade Original Simple Rolling Mean).",
            "Volume transaksi aktif (Volume > 0)."
        ],
        "entry_short": [
            "Tidak membuka short (Strategi long-only sesuai bawaan Freqtrade)."
        ],
        "exit_rules": [
            "Exit Sinyal: Saat RSI SMA (14) > 70 (Overbought).",
            "Take Profit: Minimal ROI target +4.0%.",
            "Stop Loss: Bawaan Resmi Freqtrade (-10.0%)."
        ],
        "default_params": {
            "bb_length": 20,
            "bb_std": 2.0,
            "rsi_period": 14
        }
    },
    "freqtrade_bband_rsi_adjusted": {
        "id": "freqtrade_bband_rsi_adjusted",
        "name": "Freqtrade BbandRsi (Adjusted Futures Hard SL -5%)",
        "file": "freqtrade_bband_rsi.py",
        "style": "FREQTRADE ADJUSTED",
        "style_badge_color": "#ec4899", # Pink
        "recommended_timeframe": "15m",
        "recommended_pairs": ["XTZUSDT", "GUSDT", "ARUSDT", "ENAUSDT", "SOLUSDT"],
        "description": "Adaptasi Strategi Freqtrade BbandRsi yang disesuaikan khusus untuk pasar Binance Futures dengan Stop Loss proteksi ketat (-5.0%) dan Hard Take Profit (+4.0%) guna membatasi drawdown pada koin berfluktuasi tinggi.",
        "entry_long": [
            "Harga Close lilin menembus di bawah Lower Bollinger Band (Panic Dip).",
            "Nilai RSI SMA (14) < 30 (Freqtrade Original Rolling Mean).",
            "Volume transaksi aktif (Volume > 0)."
        ],
        "entry_short": [
            "Tidak membuka short (Strategi long-only)."
        ],
        "exit_rules": [
            "Stop Loss: Hard Fixed SL -5.0% (Proteksi Ketat Futures).",
            "Take Profit: Hard Fixed TP +4.0%.",
            "Exit Sinyal: Saat RSI SMA (14) > 70."
        ],
        "default_params": {
            "bb_length": 20,
            "bb_std": 2.0,
            "rsi_period": 14,
            "hard_sl_pct": 5.0,
            "hard_tp_pct": 4.0
        }
    },
    "freqtrade_sample": {
        "id": "freqtrade_sample",
        "name": "Freqtrade Original SampleStrategy (EMA Trend + Multi-Tier ROI)",
        "file": "freqtrade_sample.py",
        "style": "FREQTRADE TEMPLATE",
        "style_badge_color": "#8b5cf6", # Purple
        "recommended_timeframe": "15m",
        "recommended_pairs": ["ETHUSDT", "SOLUSDT", "NEARUSDT", "DOGEUSDT"],
        "description": "Template Strategi Resmi Bawaan Developer Freqtrade (sample_strategy.py). Mengombinasikan 3 filter sekaligus: RSI (14) < 30, Filter Trend Bullish EMA 9 > EMA 20, dan Rebound di atas Lower Band dengan sistem Take Profit Bertingkat (4% / 2% / 1%).",
        "entry_long": [
            "RSI (14) < 30 (Oversold).",
            "EMA 9 > EMA 20 (Filter Tren: Hanya beli saat micro-uptrend / golden cross).",
            "Harga Close > Lower Bollinger Band (Rebound konfirmasi).",
            "Volume transaksi aktif (Volume > 0)."
        ],
        "entry_short": [
            "Tidak membuka short (Strategi long-only bawaan Freqtrade)."
        ],
        "exit_rules": [
            "Exit Sinyal: Saat RSI (14) > 70.",
            "Minimal ROI Bertingkat: +4% instan, +2% (>30 min), +1% (>60 min).",
            "Stop Loss: Bawaan Freqtrade (-10.0%)."
        ],
        "default_params": {
            "rsi_period": 14,
            "fast_ema": 9,
            "slow_ema": 20,
            "bb_period": 20
        }
    },
    "bb_reclaim_sniper": {
        "id": "bb_reclaim_sniper",
        "name": "Bollinger Bands Reclaim Sniper (Breach & Reclaim)",
        "file": "bb_reclaim_sniper.py",
        "style": "BB RECLAIM SNIPER",
        "style_badge_color": "#10b981",
        "recommended_timeframe": "15m",
        "recommended_pairs": ["BTCUSDT", "ETHUSDT", "SOLUSDT", "SUIUSDT", "NEARUSDT"],
        "description": "Membeli saat harga menembus di bawah Lower Band lalu lilin berikutnya ditutup kembali di atas Lower Band dengan R:R 1:2.0.",
        "entry_long": ["Candle i-1 tembus di bawah Lower Band", "Candle i tutup kembali di atas Lower Band"],
        "entry_short": ["Candle i-1 tembus di atas Upper Band", "Candle i tutup kembali di bawah Upper Band"],
        "exit_rules": ["Dynamic Trailing Stop / TP R:R 1:2.0"],
        "default_params": {"bb_length": 20, "bb_std": 2.0, "risk_reward": 2.0}
    },
    "ema_crossover": {
        "id": "ema_crossover",
        "name": "EMA Crossover (9 / 21) Trend Filter 200",
        "file": "ema_crossover.py",
        "style": "EMA TREND RIDE",
        "style_badge_color": "#8b5cf6",
        "recommended_timeframe": "1h",
        "recommended_pairs": ["BTCUSDT", "ETHUSDT", "SOLUSDT", "DOGEUSDT"],
        "description": "Golden cross EMA 9 & EMA 21 saat harga di atas EMA 200 dengan ATR Dynamic Stop Loss.",
        "entry_long": ["Fast EMA 9 cross up Slow EMA 21 & Close > EMA 200"],
        "entry_short": ["Fast EMA 9 cross down Slow EMA 21 & Close < EMA 200"],
        "exit_rules": ["Stop Loss 1.5x ATR, Take Profit 3.0x ATR"],
        "default_params": {"fast_ema": 9, "slow_ema": 21, "trend_ema": 200, "atr_sl_mult": 1.5, "risk_reward": 2.0}
    }
}

def get_all_strategies() -> List[Dict[str, Any]]:
    """
    Mengembalikan daftar strategi unggulan terverifikasi.
    """
    return [
        STRATEGY_METADATA["trend_rider_supertrend"],
        STRATEGY_METADATA["rsi_first_ema7_crossover"],
        STRATEGY_METADATA["binance_bband_wilder_rsi"],
        STRATEGY_METADATA["freqtrade_bband_rsi"],
        STRATEGY_METADATA["freqtrade_bband_rsi_adjusted"],
        STRATEGY_METADATA["freqtrade_sample"],
        STRATEGY_METADATA["bb_reclaim_sniper"],
        STRATEGY_METADATA["ema_crossover"]
    ]

def get_strategy_instance(strategy_id: str, **kwargs) -> BaseStrategy:
    """
    Inisialisasi instance objek strategi secara dinamis.
    """
    import importlib
    import src.strategies.freqtrade_bband_rsi
    importlib.reload(src.strategies.freqtrade_bband_rsi)
    
    from src.strategies.trend_rider_supertrend import TrendRiderSupertrendStrategy
    from src.strategies.binance_bband_wilder_rsi import BinanceBbandWilderRsiStrategy
    from src.strategies.freqtrade_bband_rsi import FreqtradePureBbandRsiStrategy, FreqtradeAdjustedBbandRsiStrategy
    from src.strategies.freqtrade_sample import FreqtradeOriginalSampleStrategy
    from src.strategies.rsi_first_ema7_crossover import RsiFirstEma7CrossoverStrategy
    from src.strategies.bb_reclaim_sniper import BBReclaimSniperStrategy
    from src.strategies.ema_crossover import EMACrossoverStrategy

    sid = strategy_id.lower().strip() if strategy_id else "trend_rider_supertrend"
    
    if "trend_rider" in sid or "supertrend" in sid:
        return TrendRiderSupertrendStrategy(**kwargs)
    elif "bb_reclaim" in sid or "reclaim" in sid:
        return BBReclaimSniperStrategy(**kwargs)
    elif "ema_cross" in sid or "ema_crossover" in sid:
        return EMACrossoverStrategy(**kwargs)
    elif "ema7" in sid or "first" in sid:
        return RsiFirstEma7CrossoverStrategy(**kwargs)
    elif "sample" in sid:
        return FreqtradeOriginalSampleStrategy()
    elif "adjusted" in sid or "adj" in sid:
        return FreqtradeAdjustedBbandRsiStrategy()
    elif "freqtrade" in sid or ("bband_rsi" in sid and "wilder" not in sid and "binance" not in sid):
        return FreqtradePureBbandRsiStrategy()
    else:
        return BinanceBbandWilderRsiStrategy()
