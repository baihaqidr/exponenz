from src.data_fetcher import fetch_fast_api_klines
from concurrent.futures import ThreadPoolExecutor
import pandas as pd
import numpy as np

symbols = ['BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'XRPUSDT', 'BNBUSDT', 'DOGEUSDT', 'ADAUSDT']
timeframes = ['15m', '1h', '4h']

data_cache = {tf: {} for tf in timeframes}
def fetch_w(args):
    sym, tf = args
    df = fetch_fast_api_klines(sym, tf, total_candles=1000)
    return sym, tf, df

tasks = [(sym, tf) for tf in timeframes for sym in symbols]
with ThreadPoolExecutor(max_workers=10) as ex:
    for sym, tf, df in ex.map(fetch_w, tasks):
        if df is not None:
            data_cache[tf][sym] = df

tf_buckets = {
    '15m': [(0.3, 0.7, "0.3% - 0.7% (Kecil)"), (0.7, 1.5, "0.7% - 1.5% (Ideal Breakout)"), (1.5, 3.0, "1.5% - 3.0% (Strong Momentum)"), (3.0, 10.0, "> 3.0% (Exhaustion)")],
    '1h':  [(0.5, 1.2, "0.5% - 1.2% (Kecil)"), (1.2, 2.5, "1.2% - 2.5% (Ideal Breakout)"), (2.5, 4.5, "2.5% - 4.5% (Strong Momentum)"), (4.5, 15.0, "> 4.5% (Exhaustion)")],
    '4h':  [(1.0, 2.5, "1.0% - 2.5% (Kecil)"), (2.5, 5.0, "2.5% - 5.0% (Ideal Breakout)"), (5.0, 8.0, "5.0% - 8.0% (Strong Momentum)"), (8.0, 25.0, "> 8.0% (Exhaustion)")]
}

print("="*95)
print("HASIL RISET LENGKAP: RENTANG % UKURAN LILIN IMPULSIF IDEAL (15m, 1h, 4h)")
print("="*95)

for tf in timeframes:
    print(f"\n--- TIMEFRAME {tf} ---")
    print(f"{'RENTANG UKURAN LILIN':35} | {'TOTAL SINYAL':14} | {'WIN RATE (1:2 RR)':18} | {'WIN RATE (1:1.5 RR)'}")
    print("-" * 95)
    for min_pct, max_pct, label in tf_buckets[tf]:
        total_signals = 0
        win_2rr = 0
        win_1_5rr = 0
        
        for sym, df in data_cache[tf].items():
            open_p = df['open'].values
            high_p = df['high'].values
            low_p = df['low'].values
            close_p = df['close'].values
            
            for i in range(25, len(df) - 20):
                o, h, l, c = open_p[i], high_p[i], low_p[i], close_p[i]
                body_pct = (abs(c - o) / o) * 100
                
                prev_highs = high_p[i-15:i]
                if c > np.max(prev_highs) and c > o:
                    if min_pct <= body_pct < max_pct:
                        total_signals += 1
                        entry = c
                        sl = l * 0.999
                        sl_dist = entry - sl
                        if sl_dist <= 0: continue
                        tp_2 = entry + (sl_dist * 2.0)
                        tp_1_5 = entry + (sl_dist * 1.5)
                        
                        f_highs = high_p[i+1:i+21]
                        f_lows = low_p[i+1:i+21]
                        
                        hit_tp2 = False
                        hit_tp1_5 = False
                        for fh, fl in zip(f_highs, f_lows):
                            if fl <= sl: break
                            if fh >= tp_2:
                                hit_tp2 = True
                                break
                            if fh >= tp_1_5:
                                hit_tp1_5 = True
                        if hit_tp2: win_2rr += 1
                        if hit_tp1_5 or hit_tp2: win_1_5rr += 1
                        
        if total_signals > 0:
            wr2 = (win_2rr / total_signals) * 100
            wr15 = (win_1_5rr / total_signals) * 100
            print(f"{label:35} | {total_signals:4} sinyal     | {wr2:5.1f}%             | {wr15:5.1f}%")

print("="*95)
