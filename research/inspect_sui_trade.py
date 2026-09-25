import pandas as pd
from src.data_fetcher import fetch_binance_futures_klines
from src.indicators import calculate_supertrend

df = fetch_binance_futures_klines('SUIUSDT', '5m', 3000, use_cache=True)
st_val, st_dir = calculate_supertrend(df, 16, 4.0)
df['st'] = st_val
df['dir'] = st_dir
df['time_wib'] = pd.to_datetime(df['timestamp']) + pd.Timedelta(hours=7)

sub = df[(df['time_wib'] >= '2026-09-13 20:30') & (df['time_wib'] <= '2026-09-13 23:15')]
for _, r in sub.iterrows():
    print(f"{r['time_wib'].strftime('%Y-%m-%d %H:%M')} | O: {r['open']:.6f} H: {r['high']:.6f} L: {r['low']:.6f} C: {r['close']:.6f} | ST Line: {r['st']:.6f} | Dir: {int(r['dir'])}")
