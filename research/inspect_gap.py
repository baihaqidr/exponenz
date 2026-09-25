import pandas as pd
from src.data_fetcher import fetch_binance_futures_klines
from src.indicators import calculate_supertrend

df = fetch_binance_futures_klines('SUIUSDT', '5m', 3000, use_cache=True)
df['time_wib'] = pd.to_datetime(df['timestamp']) + pd.Timedelta(hours=7)
st10, d10 = calculate_supertrend(df, 10, 3.0)
st16, d16 = calculate_supertrend(df, 16, 4.0)
df['st10'] = st10
df['d10'] = d10
df['st16'] = st16
df['d16'] = d16

sub = df[(df['time_wib'] >= '2026-09-13 22:45') & (df['time_wib'] <= '2026-09-14 03:00')]
for _, r in sub.iterrows():
    if r['time_wib'].minute in [0, 15, 30, 45] or r['time_wib'].strftime('%H:%M') in ['22:55', '02:35']:
        print(f"{r['time_wib'].strftime('%Y-%m-%d %H:%M')} | Close: {r['close']:.6f} | ST(10,3) Dir: {int(r['d10']):+d} | ST(16,4) Dir: {int(r['d16']):+d}")
