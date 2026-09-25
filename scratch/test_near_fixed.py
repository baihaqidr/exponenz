import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from src.data_fetcher import fetch_fast_api_klines
from src.strategy_registry import get_strategy_instance
from src.backtester import BacktestEngine
import pandas as pd

df = fetch_fast_api_klines('NEARUSDT', '5m', total_candles=500)
strategy = get_strategy_instance('freqtrade_bband_rsi')
df_sig = strategy.generate_signals(df)

engine = BacktestEngine(initial_capital=1000.0, leverage=2.0, risk_per_trade_pct=0.02, fixed_pos_size_pct=0.5)
res = engine.run(df_sig)
trades = res['trades_df']
trades['entry_wib'] = pd.to_datetime(trades['entry_time']) + pd.Timedelta(hours=7)
trades['exit_wib'] = pd.to_datetime(trades['exit_time']) + pd.Timedelta(hours=7)

target_trades = trades[trades['entry_wib'] >= '2026-09-23 20:00']
print("Trades executed after 20:00 WIB on NEARUSDT:")
for idx, r in target_trades.iterrows():
    e_time = r['entry_wib'].strftime('%Y-%m-%d %H:%M')
    x_time = r['exit_wib'].strftime('%Y-%m-%d %H:%M')
    print(f"Trade #{idx+1}:")
    print(f"  Entry : {e_time} WIB @ ${r['entry_price']:.4f}")
    print(f"  Exit  : {x_time} WIB @ ${r['exit_price']:.4f}")
    print(f"  Reason: {r['exit_reason']}")
    print(f"  Net PnL: ${r['net_pnl']:.2f}")
