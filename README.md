---
title: Exponenz Trading Bot
emoji: ⚡
colorFrom: yellow
colorTo: red
sdk: docker
app_port: 7860
pinned: false
---

# 🚀 Binance Futures Strategy Backtester & Trading Bot

Engine backtesting dan otomasi strategi trading Binance Futures dengan Python, mendukung kalkulasi fee nyata, slippage, simulasi eksekusi Long & Short, dan Stop Loss (SL) / Take Profit (TP) per candlestick.

---

## 📂 Struktur Proyek

```
binance-futures-bot/
├── data/                  # Cache data candlestick historis (CSV)
├── results/               # Log lengkap hasil trade backtest (CSV)
├── src/
│   ├── data_fetcher.py    # Downloader data OHLCV Binance (Multi-batch & Fallback)
│   ├── indicators.py      # Indikator teknikal (Supertrend, EMA, RSI, ATR, MACD, BB)
│   ├── backtester.py      # Core simulation engine (Futures Long/Short + SL/TP + Fees)
│   └── strategies/        # Modul strategi modular
│       ├── base.py
│       ├── supertrend_rsi.py
│       ├── ema_crossover.py
│       ├── breakout_atr.py
│       └── bollinger_rsi.py
├── run_backtest.py        # CLI Runner untuk menjalankan backtest
└── requirements.txt
```

---

## ⚡ Cara Menjalankan Backtest

Jalankan perintah berikut di terminal:

### 1. Uji Strategi Supertrend + RSI (Default)
```bash
python run_backtest.py --symbol BTCUSDT --interval 1h --candles 3000 --strategy supertrend
```

### 2. Uji Strategi EMA Crossover (Fast/Slow EMA + 200 Trend Filter)
```bash
python run_backtest.py --symbol ETHUSDT --interval 4h --candles 3000 --strategy ema --leverage 3.0
```

### 3. Uji Strategi Breakout ATR (Donchian Channel + Volume Spike)
```bash
python run_backtest.py --symbol CVCUSDT --interval 15m --candles 3000 --strategy breakout
```

### 4. Uji Strategi Bollinger Bands + RSI Scalper
```bash
python run_backtest.py --symbol BTCUSDT --interval 15m --candles 3000 --strategy bollinger
```

---

## ⚙️ Parameter CLI yang Tersedia

| Parameter | Deskripsi | Default |
| :--- | :--- | :--- |
| `--symbol` | Simbol pair Binance Futures (misal: `BTCUSDT`, `ETHUSDT`, `CVCUSDT`) | `BTCUSDT` |
| `--interval` | Timeframe bar candle (`1m`, `5m`, `15m`, `1h`, `4h`, `1d`) | `15m` |
| `--candles` | Jumlah total candlestick historis yang diuji | `3000` |
| `--strategy` | Pilihan strategi (`supertrend`, `ema`, `breakout`, `bollinger`) | `supertrend` |
| `--capital` | Modal awal USDT | `1000.0` |
| `--leverage` | Tingkat leverage Futures (misal: `1x`, `3x`, `5x`, `10x`) | `3.0` |
| `--pos_size` | Proporsi margin modal yang dialokasikan per trade (`0.1` s/d `1.0`) | `0.5` (50%) |
| `--no_cache` | Paksa unduh ulang data candlestick dari Binance tanpa memakai cache | `False` |

---

## 📊 Metrik Evaluasi Backtest

* **Net Profit ($ / %):** Total keuntungan atau kerugian bersih setelah dipotong fee & slippage.
* **Win Rate (%):** Persentase transaksi yang berakhir profit.
* **Profit Factor:** Rasio Total Keuntungan Kotor dibagi Total Kerugian Kotor. *(Target: > 1.50)*
* **Risk-to-Reward Ratio (RRR):** Rata-rata keuntungan per transaksi menang dibandingkan kerugian per transaksi kalah.
* **Maximum Drawdown (MDD):** Penurunan saldo terdalam dari titik puncak tertinggi (*peak equity*).
