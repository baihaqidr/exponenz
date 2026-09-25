import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import requests
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
import time
import pandas as pd
from datetime import datetime
from src.strategy_registry import get_strategy_instance
from src.backtester import BacktestEngine

from src.data_fetcher import fetch_fast_api_klines

print("Mengunduh data SAGAUSDT 5m...")
df = fetch_fast_api_klines(symbol='SAGAUSDT', interval='5m', total_candles=50000)
print(f"Total lilin 5m terkumpul: {len(df)} bar (Dari {df['timestamp'].min()} sampai {df['timestamp'].max()})")
print(f"Total lilin 5m terkumpul: {len(df)} bar (Dari {df['timestamp'].min()} sampai {df['timestamp'].max()})")

strategy = get_strategy_instance('freqtrade_bband_rsi')
df_sig = strategy.generate_signals(df)

engine = BacktestEngine(
    initial_capital=1000.0,
    leverage=2.0,
    risk_per_trade_pct=0.02,
    fixed_pos_size_pct=0.5, # $250 Notional / 50% margin
    fee_rate=0.0005,
    slippage_pct=0.0002
)
res = engine.run(df_sig)
metrics = res["metrics"]
trades_df = res["trades_df"]

print("\n========================================================")
print("=== HASIL BACKTEST HISTORIS PENUH [SAGAUSDT - 5m - Freqtrade BbandRsi] ===")
print("========================================================")
print(f"Total Transaksi Selesai : {metrics.get('total_trades')}")
print(f"Win Rate               : {metrics.get('win_rate', 0):.1f}%")
print(f"Total Net PnL          : ${metrics.get('net_profit', 0):.2f} ({metrics.get('roi_pct', 0):.2f}%)")
print(f"Profit Factor          : {metrics.get('profit_factor', 0):.2f}")
print(f"Max Drawdown           : {metrics.get('max_drawdown_pct', 0):.2f}%")
print(f"Menang / Kalah         : {metrics.get('win_count')} Win / {metrics.get('loss_count')} Loss")
print(f"Rata-rata Win / Loss   : ${metrics.get('avg_win', 0):.2f} / ${metrics.get('avg_loss', 0):.2f}")

if not trades_df.empty:
    trades_df['exit_time'] = pd.to_datetime(trades_df['exit_time'])
    tz_offset = pd.Timedelta(hours=7)
    trades_df['exit_wib'] = trades_df['exit_time'] + tz_offset
    trades_df['month'] = trades_df['exit_wib'].dt.strftime('%Y-%m')
    monthly = trades_df.groupby('month').agg(
        trades=('net_pnl', 'count'),
        wins=('net_pnl', lambda x: (x > 0).sum()),
        losses=('net_pnl', lambda x: (x <= 0).sum()),
        net_pnl=('net_pnl', 'sum')
    )
    monthly['win_rate'] = (monthly['wins'] / monthly['trades'] * 100).round(1)
    monthly['net_pnl'] = monthly['net_pnl'].round(2)
    print("\n=== BREAKDOWN PnL BULAN KE BULAN ===")
    print(monthly[['trades', 'wins', 'losses', 'win_rate', 'net_pnl']])
