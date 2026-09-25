from src.data_fetcher import fetch_fast_api_klines
from src.indicators import calculate_bollinger_bands
import pandas as pd

df = fetch_fast_api_klines('XRPUSDT', '1h', total_candles=300)
df['timestamp_wib'] = df['timestamp'] + pd.Timedelta(hours=7)
upper, middle, lower = calculate_bollinger_bands(df['close'], 20, 2.0)
df['upper'] = upper
df['middle'] = middle
df['lower'] = lower

df_wib = df[(df['timestamp_wib'] >= '2026-09-10 18:00') & (df['timestamp_wib'] <= '2026-09-11 15:00')]
for idx, r in df_wib.iterrows():
    print(f"WIB: {r['timestamp_wib']} | O: {r['open']:.4f} H: {r['high']:.4f} L: {r['low']:.4f} C: {r['close']:.4f} | Lower: {r['lower']:.4f} Mid: {r['middle']:.4f} Upper: {r['upper']:.4f}")
