# 🚀 PANDUAN CARA MENJALANKAN APLIKASI EXPONENZ

Aplikasi ini memiliki **Web Dashboard Interaktif** yang terhubung langsung ke **Binance Futures Real-Time (0-ms WebSocket)**, mesin **Backtest Matriks Multi-Pair**, dan **Funding Rate Sniper**.

---

## ⚡ CARA 1: Paling Mudah (1-Klik via File Batch)

1. Buka folder proyek ini di Windows Explorer:
   `D:\Vibe Coding Application\binance-futures-bot`
2. **Klik 2x (Double Click)** pada file:
   👉 **`START_DASHBOARD.bat`**
3. Server otomatis berjalan dan **Google Chrome/browser Anda akan otomatis terbuka** menuju:
   🌐 **`http://localhost:5000/`**

---

## 💻 CARA 2: Lewat Terminal / Command Prompt / PowerShell

Jika Anda sedang membuka VS Code atau Terminal Windows:

1. Buka terminal di folder proyek ini:
   ```bash
   cd "d:\Vibe Coding Application\binance-futures-bot"
   ```
2. Jalankan perintah:
   ```bash
   python run_dashboard.py
   ```
3. Buka browser dan ketik alamat:
   👉 **`http://localhost:5000/`**

---

## 📊 CARA 3: Menjalankan Backtest via Terminal (CLI Mode)

Jika Anda ingin melihat kalkulasi backtest secara langsung di terminal tanpa membuka website:

```bash
# Backtest koin ETHUSDT timeframe 5m strategi Freqtrade Bband RSI
python run_backtest.py --symbol ETHUSDT --interval 5m --strategy freqtrade_bband_rsi

# Backtest strategi Price Action Liquidity Sweep timeframe 15m
python run_backtest.py --symbol ETHUSDT --interval 15m --strategy pure_price_action_sweep

# Backtest strategi EMA 7 Fast Scalp Crossover timeframe 1m
python run_backtest.py --symbol ETHUSDT --interval 1m --strategy price_ema_7
```

---

## 🧭 FITUR & CARA PAKAI DI DALAM DASHBOARD (3 TAB UTAMA):

### 1. Tab `Backtest Matriks` (Analisis Strategi & Portofolio)
* Pilih strategi dari dropdown (tersedia 21+ strategi termasuk Freqtrade & Price Action).
* Pilih timeframe (`1m`, `5m`, `15m`, `1h`, `4h`).
* Klik tombol **Hitung Matriks**: sistem akan menguji seluruh pair crypto sekaligus.
* Klik nama koin (misal: `ETHUSDT`) untuk melihat **Detail Riwayat Seluruh Trade (WIB)**.

### 2. Tab `🎯 Funding Sniper Live` (Arbitrase Delta-Neutral Tanpa Risiko Arah)
* Memindai seluruh koin Binance Futures untuk mencari peluang suku bunga funding tertinggi.
* Klik tombol **Simulasi** untuk menghitung estimasi profit bersih setelah fee taker.

### 3. Tab `🤖 Live Bot Demo (Binance)` (Chart TradingView Real-Time)
* **Koin Real-Time**: Harga live tick Binance Futures via WebSocket 0-ms.
* **Dynamic Indicators**: 
  * Garis Kuning = Indikator Utama (EMA / Bollinger Middle Band).
  * Garis Cyan Dotted = Upper Band / Swing High.
  * Garis Pink Dotted = Lower Band / Swing Low.
* **Sinyal & Eksekusi**:
  * Panah Hijau = BUY (Trigger Masuk).
  * Panah Merah = SELL (Trigger Keluar / Take Profit).
* Klik tombol **START BOT AUTOMATION** untuk mengaktifkan bot simulasi trading otomatis.

---

## 🛑 CARA MEMATIKAN APLIKASI

* Pada jendela terminal / CMD yang sedang berjalan, tekan tombol:
  `Ctrl + C`
* Jendela terminal bisa langsung ditutup (*close window*).

---

> *Dibuat untuk EXPONENZ — "The more you know, the more you see."*
