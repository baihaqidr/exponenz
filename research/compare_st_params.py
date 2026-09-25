import pandas as pd
from src.data_fetcher import fetch_binance_futures_klines
from src.indicators import calculate_supertrend

df = fetch_binance_futures_klines('SUIUSDT', '5m', 3000, use_cache=True)
df['time_wib'] = pd.to_datetime(df['timestamp']) + pd.Timedelta(hours=7)

st10_3_v, st10_3_d = calculate_supertrend(df, 10, 3.0)
st10_4_v, st10_4_d = calculate_supertrend(df, 10, 4.0)
st16_4_v, st16_4_d = calculate_supertrend(df, 16, 4.0)

df['st_10_3'] = st10_3_v
df['dir_10_3'] = st10_3_d
df['st_10_4'] = st10_4_v
df['dir_10_4'] = st10_4_d
df['st_16_4'] = st16_4_v
df['dir_16_4'] = st16_4_d

sub = df[(df['time_wib'] >= '2026-09-13 21:30') & (df['time_wib'] <= '2026-09-13 23:05')]
print("Time WIB | Close    | High     | Low      | ST(10,3) Line & Dir | ST(16,4) Line & Dir")
print("-" * 85)
for _, r in sub.iterrows():
    d10 = "HIJAU" if r['dir_10_3'] == 1 else "MERAH"
    d16 = "HIJAU" if r['dir_16_4'] == 1 else "MERAH"
    print(f"{r['time_wib'].strftime('%H:%M')}    | {r['close']:.6f} | {r['high']:.6f} | {r['low']:.6f} | {r['st_10_3']:.6f} ({d10}) | {r['st_16_4']:.6f} ({d16})")
