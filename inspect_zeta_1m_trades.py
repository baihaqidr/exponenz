import sys
import requests
import urllib3
import pandas as pd
import numpy as np
from datetime import datetime

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

urllib3.disable_warnings()

def fetch_live_1m():
    url = 'https://fapi.binance.com/fapi/v1/klines?symbol=ZETAUSDT&interval=1m&limit=1500'
    r = requests.get(url, verify=False, timeout=10).json()
    cols = ['open_time', 'open', 'high', 'low', 'close', 'volume', 'close_time', 'quote_volume', 'count', 'taker_buy_volume', 'taker_buy_quote_volume', 'ignore']
    df = pd.DataFrame(r, columns=cols[:len(r[0])])
    df['timestamp'] = pd.to_datetime(df['open_time'], unit='ms')
    for c in ['open', 'high', 'low', 'close', 'volume']:
        df[c] = df[c].astype(float)
    return df

def calculate_rsi(series, period=14):
    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1/period, min_periods=period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1/period, min_periods=period, adjust=False).mean()
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))

def calculate_ema(series, period=7):
    return series.ewm(span=period, adjust=False).mean()

def main():
    df = fetch_live_1m()
    df['rsi'] = calculate_rsi(df['close'], 14)
    df['ema_7'] = calculate_ema(df['close'], 7)

    trades = []
    armed = False
    active_trade = None

    for i in range(1, len(df)):
        row = df.iloc[i]
        prev = df.iloc[i-1]
        
        # Check ongoing trade
        if active_trade is not None:
            high = row['high']
            low = row['low']
            t_time = row['timestamp']
            
            hit_tp = high >= active_trade['tp_price']
            hit_sl = low <= active_trade['sl_price']
            
            if hit_tp and hit_sl:
                active_trade['exit_time'] = t_time
                active_trade['exit_price'] = active_trade['sl_price']
                active_trade['result'] = 'LOSS (Ambiguous SL hit)'
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
            sl_p = row['low'] # SL di Low lilin
            risk = entry_p - sl_p
            if risk <= 0:
                risk = entry_p * 0.001
                sl_p = entry_p - risk
                
            tp_p = entry_p + (2.0 * risk) # TP 2x Risk
            
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
                'result': 'SEDANG BERJALAN (OPEN)'
            }
            armed = False

    if active_trade is not None:
        trades.append(active_trade)

    print("="*90)
    print("🎯 HASIL PENGECEKAN TRADE TERAKHIR ZETAUSDT DI TIMEFRAME 1-MENIT (1m)")
    print(f"Data Live Binance Futures: {df['timestamp'].iloc[0]} s/d {df['timestamp'].iloc[-1]} UTC")
    print(f"Total Trade Terdeteksi: {len(trades)} Transaksi")
    print("="*90)

    last_trade = trades[-1]
    wib_in = last_trade['entry_time'] + pd.Timedelta(hours=7)
    
    print(f"🏆 TRADE TERAKHIR ZETAUSDT (1m):")
    print(f"   • Waktu Entry (WIB) : {wib_in.strftime('%Y-%m-%d %H:%M:%S WIB')} ({last_trade['entry_time']} UTC)")
    print(f"   • OHLC Lilin Entry  :")
    print(f"     - Open  : {last_trade['entry_candle']['O']:.5f}")
    print(f"     - High  : {last_trade['entry_candle']['H']:.5f}")
    print(f"     - Low   : {last_trade['entry_candle']['L']:.5f}")
    print(f"     - Close : {last_trade['entry_candle']['C']:.5f}")
    print(f"   • Indikator Saat Entry:")
    print(f"     - RSI(14) : {last_trade['rsi_at_entry']:.2f} (Setelah sebelumnya < 30)")
    print(f"     - EMA(7)  : {last_trade['ema7_at_entry']:.5f} (Candle Close berhasil tembus di atas EMA 7)")
    print(f"   • Parameter Eksekusi:")
    print(f"     - Entry Price : {last_trade['entry_price']:.5f} (di Close)")
    print(f"     - Stop Loss   : {last_trade['sl_price']:.5f} (di Low Lilin Entry | Jarak Risk: -{last_trade['risk_pct']:.3f}%)")
    print(f"     - Take Profit : {last_trade['tp_price']:.5f} (Target 2x Risk | Jarak Reward: +{last_trade['reward_pct']:.3f}%)")
    print(f"   • HASIL AKHIR   : {last_trade['result']}")
    if last_trade['exit_time']:
        wib_out = last_trade['exit_time'] + pd.Timedelta(hours=7)
        print(f"   • Waktu Exit  : {wib_out.strftime('%Y-%m-%d %H:%M:%S WIB')} @ {last_trade['exit_price']:.5f}")
    print("="*90)

if __name__ == "__main__":
    main()
