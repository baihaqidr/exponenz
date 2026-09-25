import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from src.data_fetcher import fetch_fast_api_klines
from src.strategy_registry import get_strategy_instance
from src.backtester import BacktestEngine
import pandas as pd

df = fetch_fast_api_klines('SAGAUSDT', '5m', total_candles=1500)
strategy = get_strategy_instance('binance_bband_wilder_rsi')
df_sig = strategy.generate_signals(df)

engine = BacktestEngine(initial_capital=1000.0, leverage=2.0, risk_per_trade_pct=0.02)
res = engine.run(df_sig)
trades = res['trades_df']
print(f'Total trades on recent 1500 candles: {len(trades)}\n')
if not trades.empty:
    trades['entry_wib'] = pd.to_datetime(trades['entry_time']) + pd.Timedelta(hours=7)
    trades['exit_wib'] = pd.to_datetime(trades['exit_time']) + pd.Timedelta(hours=7)
    for idx, r in trades.iterrows():
        e_time = r['entry_wib'].strftime('%Y-%m-%d %H:%M')
        x_time = r['exit_wib'].strftime('%Y-%m-%d %H:%M')
        pnl = r['net_pnl']
        print(f"Trade #{idx+1}:")
        print(f"  Entry: {e_time} WIB @ ${r['entry_price']:.5f}")
        print(f"  Exit : {x_time} WIB @ ${r['exit_price']:.5f}")
        print(f"  Reason: {r['exit_reason']}")
        print(f"  Net PnL: ${pnl:.2f}")
        print("-" * 50)
