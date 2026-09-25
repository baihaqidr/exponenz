import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import requests
import pandas as pd
from datetime import datetime
from src.strategy_registry import get_strategy_instance
from src.backtester import BacktestEngine

def fetch_data(symbol='SAGAUSDT', interval='5m', max_batches=20):
    url = "https://data-api.binance.vision/api/v3/klines"
    all_rows = []
    end_time = None
    
    for i in range(max_batches):
        params = {"symbol": symbol, "interval": interval, "limit": 1000}
        if end_time:
            params["endTime"] = end_time - 1
        try:
            r = requests.get(url, params=params, timeout=5)
            data = r.json()
            if not data or not isinstance(data, list) or len(data) == 0:
                break
            all_rows = data + all_rows
            end_time = data[0][0]
            if len(data) < 1000:
                break
        except Exception:
            break
            
    cols = ['open_time', 'open', 'high', 'low', 'close', 'volume', 'close_time', 'quote_volume', 'count', 'taker_buy_volume', 'taker_buy_quote_volume', 'ignore']
    df = pd.DataFrame(all_rows, columns=cols[:len(all_rows[0])])
    df['timestamp'] = pd.to_datetime(df['open_time'], unit='ms')
    for c in ['open', 'high', 'low', 'close', 'volume']:
        df[c] = df[c].astype(float)
    df.drop_duplicates(subset=['timestamp'], inplace=True)
    df.sort_values('timestamp', inplace=True)
    return df.reset_index(drop=True)

df = fetch_data('SAGAUSDT', interval='5m', max_batches=20)

strategy = get_strategy_instance('binance_bband_wilder_rsi')
df_sig = strategy.generate_signals(df)

engine = BacktestEngine(
    initial_capital=1000.0,
    leverage=2.0,
    risk_per_trade_pct=0.02,
    fixed_pos_size_pct=0.5,
    fee_rate=0.0005,
    slippage_pct=0.0002
)
res = engine.run(df_sig)
trades_df = res["trades_df"]

print(f"Total Trade Binance Wilder di SAGAUSDT: {len(trades_df)}\n", flush=True)

tz_offset = pd.Timedelta(hours=7)
trades_df['entry_wib'] = pd.to_datetime(trades_df['entry_time']) + tz_offset
trades_df['exit_wib'] = pd.to_datetime(trades_df['exit_time']) + tz_offset

last_5 = trades_df.tail(5).reset_index(drop=True)
for idx, row in last_5.iterrows():
    trade_num = len(trades_df) - len(last_5) + idx + 1
    pnl = float(row['net_pnl'])
    pnl_str = f"+${pnl:.2f}" if pnl > 0 else f"-${abs(pnl):.2f}"
    entry_t = row['entry_wib'].strftime('%Y-%m-%d %H:%M')
    exit_t = row['exit_wib'].strftime('%Y-%m-%d %H:%M')
    print(f"Posisi #{trade_num}:", flush=True)
    print(f"  * Entry        : {entry_t} WIB @ ${row['entry_price']:.5f}", flush=True)
    print(f"  * Exit         : {exit_t} WIB @ ${row['exit_price']:.5f}", flush=True)
    print(f"  * Alasan Exit  : {row['exit_reason']}", flush=True)
    print(f"  * Net PnL      : {pnl_str}", flush=True)
    print("-" * 55, flush=True)
