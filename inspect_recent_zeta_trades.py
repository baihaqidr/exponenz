import sys
import io
import zipfile
import requests
import urllib3
import pandas as pd
import numpy as np

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

urllib3.disable_warnings()

from src.indicators import calculate_rsi, calculate_ema

def load_recent_zeta(interval="1m"):
    dfs = []
    for d in ['2026-09-18', '2026-09-19', '2026-09-20', '2026-09-21']:
        url = f"https://data.binance.vision/data/futures/um/daily/klines/ZETAUSDT/{interval}/ZETAUSDT-{interval}-{d}.zip"
        try:
            r = requests.get(url, verify=False, timeout=8)
            if r.status_code == 200:
                z = zipfile.ZipFile(io.BytesIO(r.content))
                csv_file = z.namelist()[0]
                df_day = pd.read_csv(z.open(csv_file))
                cols = ['open_time', 'open', 'high', 'low', 'close', 'volume', 'close_time', 'quote_volume', 'count', 'taker_buy_volume', 'taker_buy_quote_volume', 'ignore']
                df_day.columns = cols[:len(df_day.columns)]
                df_day['timestamp'] = pd.to_datetime(df_day['open_time'], unit='ms')
                for c in ['open', 'high', 'low', 'close', 'volume']:
                    df_day[c] = df_day[c].astype(float)
                dfs.append(df_day[['timestamp', 'open', 'high', 'low', 'close', 'volume']])
        except Exception:
            pass
    if dfs:
        full = pd.concat(dfs, ignore_index=True)
        full.drop_duplicates(subset=['timestamp'], inplace=True)
        full.sort_values('timestamp', inplace=True)
        full.reset_index(drop=True, inplace=True)
        return full
    return None

def analyze_trades(interval="1m"):
    df = load_recent_zeta(interval)
    if df is None:
        print("Gagal memuat data ZETAUSDT.")
        return
        
    df['rsi'] = calculate_rsi(df['close'], 14)
    df['ema_7'] = calculate_ema(df['close'], 7)
    
    trades = []
    armed = False
    active_trade = None

    for i in range(1, len(df)):
        row = df.iloc[i]
        prev = df.iloc[i-1]
        
        # Check active trade
        if active_trade is not None:
            high = row['high']
            low = row['low']
            t_time = row['timestamp']
            
            hit_tp = high >= active_trade['tp_price']
            hit_sl = low <= active_trade['sl_price']
            
            if hit_tp and hit_sl:
                active_trade['exit_time'] = t_time
                active_trade['exit_price'] = active_trade['sl_price']
                active_trade['result'] = 'LOSS (SL Hit)'
                trades.append(active_trade)
                active_trade = None
            elif hit_tp:
                active_trade['exit_time'] = t_time
                active_trade['exit_price'] = active_trade['tp_price']
                active_trade['result'] = 'PROFIT (TP HIT 🟢)'
                trades.append(active_trade)
                active_trade = None
            elif hit_sl:
                active_trade['exit_time'] = t_time
                active_trade['exit_price'] = active_trade['sl_price']
                active_trade['result'] = 'LOSS (SL HIT 🔴)'
                trades.append(active_trade)
                active_trade = None
                
        # 1. State Armed saat RSI < 30
        if row['rsi'] < 30:
            armed = True
            
        # 2. Trigger Entry saat lilin pertama Close > EMA 7
        if armed and (prev['close'] <= prev['ema_7']) and (row['close'] > row['ema_7']) and active_trade is None:
            entry_p = row['close']
            sl_p = row['low']
            risk = entry_p - sl_p
            if risk <= 0:
                risk = entry_p * 0.001
                sl_p = entry_p - risk
                
            tp_p = entry_p + (2.0 * risk) # 2x Risk
            
            active_trade = {
                'entry_idx': i,
                'entry_time': row['timestamp'],
                'entry_candle': {'O': row['open'], 'H': row['high'], 'L': row['low'], 'C': row['close']},
                'rsi_at_entry': row['rsi'],
                'ema7_at_entry': row['ema_7'],
                'entry_price': entry_p,
                'sl_price': sl_p,
                'tp_price': tp_p,
                'risk_pct': (risk / entry_p) * 100,
                'reward_pct': (2.0 * risk / entry_p) * 100,
                'exit_time': None,
                'exit_price': None,
                'result': 'OPEN'
            }
            armed = False

    if active_trade is not None:
        trades.append(active_trade)

    print("="*95)
    print(f"🎯 RINCIAN TRADE REAL-MARKET ZETAUSDT ({interval.upper()}) | PERIODE: 18-Sep s/d 21-Sep-2026")
    print(f"Total Lilin Terkumpul: {len(df):,} Lilin | Total Setup Terbentuk: {len(trades)} Transaksi")
    print("="*95)
    
    for idx, tr in enumerate(trades[-6:], 1):
        wib_in = tr['entry_time'] + pd.Timedelta(hours=7)
        st_icon = "🟢" if "PROFIT" in tr['result'] else "🔴"
        print(f"📌 SETUP #{idx}:")
        print(f"   • Waktu Entry (WIB) : {wib_in.strftime('%d-%b-%Y %H:%M WIB')} ({tr['entry_time']} UTC)")
        print(f"   • OHLC Lilin Entry  : Open={tr['entry_candle']['O']:.5f} | High={tr['entry_candle']['H']:.5f} | Low={tr['entry_candle']['L']:.5f} | Close={tr['entry_candle']['C']:.5f}")
        print(f"   • Indikator         : RSI={tr['rsi_at_entry']:.2f} | EMA(7)={tr['ema7_at_entry']:.5f}")
        print(f"   • Titik Entry (Long): {tr['entry_price']:.5f}")
        print(f"   • Stop Loss (Low)   : {tr['sl_price']:.5f} (Risk: -{tr['risk_pct']:.2f}%)")
        print(f"   • Take Profit (2x)  : {tr['tp_price']:.5f} (Reward: +{tr['reward_pct']:.2f}%)")
        print(f"   • HASIL AKHIR       : {tr['result']} {st_icon}")
        if tr['exit_time']:
            wib_out = tr['exit_time'] + pd.Timedelta(hours=7)
            print(f"   • Waktu Selesai (WIB): {wib_out.strftime('%d-%b-%Y %H:%M WIB')} @ {tr['exit_price']:.5f}")
        print("-" * 95)

if __name__ == "__main__":
    print("\n" + "="*95)
    print("ANALISIS TIMEFRAME 1-MENIT (1m):")
    analyze_trades("1m")
    print("\n" + "="*95)
    print("ANALISIS TIMEFRAME 5-MENIT (5m - Sesuai Screenshot Anda):")
    analyze_trades("5m")
