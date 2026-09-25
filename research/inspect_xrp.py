from src.data_fetcher import fetch_fast_api_klines
from src.indicators import calculate_bollinger_bands
import pandas as pd

df = fetch_fast_api_klines('XRPUSDT', '1h', total_candles=200)
upper, middle, lower = calculate_bollinger_bands(df['close'], 20, 2.0)
df['upper'] = upper
df['middle'] = middle
df['lower'] = lower

df_sub = df[df['timestamp'] >= '2026-09-10']
print("="*110)
print(f"{'TIMESTAMP':19} | {'OPEN':7} | {'HIGH':7} | {'LOW':7} | {'CLOSE':7} | {'LOWER':7} | {'MIDDLE':7} | {'UPPER':7} | {'BB STATUS'}")
print("="*110)
for idx, r in df_sub.iterrows():
    c_type = 'GREEN' if r['close'] >= r['open'] else 'RED'
    status = 'INSIDE'
    if max(r['open'], r['close']) < r['lower']:
        status = 'FULL_BELOW_LOWER'
    elif r['close'] < r['lower']:
        status = 'CLOSE_BELOW_LOWER'
    elif min(r['open'], r['close']) > r['upper']:
        status = 'FULL_ABOVE_UPPER'
    elif r['close'] > r['upper']:
        status = 'CLOSE_ABOVE_UPPER'
    print(f"{str(r['timestamp']):19} | {r['open']:7.4f} | {r['high']:7.4f} | {r['low']:7.4f} | {r['close']:7.4f} | {r['lower']:7.4f} | {r['middle']:7.4f} | {r['upper']:7.4f} | {c_type:5} | {status}")
print("="*110)
