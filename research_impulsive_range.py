from src.data_fetcher import fetch_fast_api_klines
from concurrent.futures import ThreadPoolExecutor
import pandas as pd
import numpy as np

symbols = ['BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'XRPUSDT', 'BNBUSDT', 'DOGEUSDT', 'ADAUSDT']
timeframes = ['15m', '1h', '4h']

data_cache = {tf: {} for tf in timeframes}

def fetch_worker(args):
    sym, tf = args
    df = fetch_fast_api_klines(sym, tf, total_candles=1000)
    return sym, tf, df

tasks = [(sym, tf) for tf in timeframes for sym in symbols]
with ThreadPoolExecutor(max_workers=10) as executor:
    for sym, tf, df in executor.map(fetch_worker, tasks):
        if df is not None:
            data_cache[tf][sym] = df

print("="*105)
print("ANALISIS RISET KUANTITATIF: RANGE UKURAN IMPULSIVE CANDLE (% & MULTIPLIER)")
print("="*105)

for tf in timeframes:
    print(f"\n==================== HASIL STATISTIK TIMEFRAME: {tf} ====================")
    print(f"{'SYARAT BARS':15} | {'BODY MULTIPLIER':16} | {'AVG CANDLE %':14} | {'TOTAL SINYAL':14} | {'WIN RATE (1:2 RR)':18} | {'WIN RATE (1:1.5 RR)':18}")
    print("-" * 105)
    
    for lookback in [10, 15, 20]:
        for mult in [1.5, 2.0, 2.5, 3.0]:
            total_signals = 0
            win_2rr = 0
            win_1_5rr = 0
            candle_pct_list = []
            
            for sym, df in data_cache[tf].items():
                open_p = df['open'].values
                high_p = df['high'].values
                low_p = df['low'].values
                close_p = df['close'].values
                body_sizes = np.abs(close_p - open_p)
                
                for i in range(lookback + 20, len(df) - 20):
                    o, h, l, c = open_p[i], high_p[i], low_p[i], close_p[i]
                    body = abs(c - o)
                    body_pct = (body / o) * 100
                    avg_body = np.mean(body_sizes[i-lookback:i])
                    
                    prev_highs = high_p[i-lookback:i]
                    if c > np.max(prev_highs) and c > o and body >= (mult * avg_body):
                        total_signals += 1
                        candle_pct_list.append(body_pct)
                        
                        entry = c
                        sl = l * 0.999
                        sl_dist = entry - sl
                        if sl_dist <= 0:
                            continue
                        tp_2 = entry + (sl_dist * 2.0)
                        tp_1_5 = entry + (sl_dist * 1.5)
                        
                        f_highs = high_p[i+1:i+21]
                        f_lows = low_p[i+1:i+21]
                        
                        hit_tp2 = False
                        hit_tp1_5 = False
                        
                        for fh, fl in zip(f_highs, f_lows):
                            if fl <= sl:
                                break
                            if fh >= tp_2:
                                hit_tp2 = True
                                break
                            if fh >= tp_1_5:
                                hit_tp1_5 = True
                                
                        if hit_tp2:
                            win_2rr += 1
                        if hit_tp1_5 or hit_tp2:
                            win_1_5rr += 1
                            
            if total_signals > 0:
                avg_pct = np.mean(candle_pct_list)
                wr2 = (win_2rr / total_signals) * 100
                wr15 = (win_1_5rr / total_signals) * 100
                print(f"Melahap {lookback:2} bar   | {mult:3.1f}x Avg Body     | {avg_pct:5.2f}%         | {total_signals:4} sinyal     | {wr2:5.1f}%             | {wr15:5.1f}%")

print("\n" + "="*105)
