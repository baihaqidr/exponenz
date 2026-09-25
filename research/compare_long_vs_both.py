import sys
import pandas as pd
import numpy as np
from test_unbiased_20_pairs import fetch_1year_klines, calculate_supertrend, calculate_ema
from src.backtester import BacktestEngine

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

pairs = ['SOLUSDT', 'BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'INJUSDT', 'ARBUSDT', 'FILUSDT', 'AVAXUSDT', 'NEARUSDT', 'PEPEUSDT', 'STRKUSDT', 'SEIUSDT']
res_long_only = []
res_both = []

print("="*85)
print(f"{'Symbol':<12} | {'Mode LONG ONLY':<25} | {'Mode DUA ARAH (LONG+SHORT)':<25}")
print("-" * 85)

for s in pairs:
    try:
        df = fetch_1year_klines(s, '1h')
        if df is None:
            continue
        df['supertrend'], df['st_dir'] = calculate_supertrend(df, 10, 3.0)
        df['ema_50'] = calculate_ema(df['close'], 50)
        
        # 1. LONG ONLY
        df_long = df.copy()
        df_long['enter_long'] = np.where((df_long['st_dir'] == 1) & (df_long['st_dir'].shift(1) == -1) & (df_long['close'] > df_long['ema_50']), 1, 0)
        df_long['exit_long'] = np.where(df_long['st_dir'] == -1, 1, 0)
        df_long['enter_short'] = 0
        df_long['exit_short'] = 0
        df_long['sl_price'] = df_long['supertrend']
        
        # 2. BOTH (LONG + SHORT)
        df_both = df.copy()
        df_both['enter_long'] = np.where((df_both['st_dir'] == 1) & (df_both['st_dir'].shift(1) == -1) & (df_both['close'] > df_both['ema_50']), 1, 0)
        df_both['exit_long'] = np.where(df_both['st_dir'] == -1, 1, 0)
        df_both['enter_short'] = np.where((df_both['st_dir'] == -1) & (df_both['st_dir'].shift(1) == 1) & (df_both['close'] < df_both['ema_50']), 1, 0)
        df_both['exit_short'] = np.where(df_both['st_dir'] == 1, 1, 0)
        df_both['sl_price'] = df_both['supertrend']
        
        engine = BacktestEngine(5000.0, 2.0, 0.20, 0.0005, 0.0002)
        m_l = engine.run(df_long)['metrics']
        m_b = engine.run(df_both)['metrics']
        
        res_long_only.append(m_l['net_profit'])
        res_both.append(m_b['net_profit'])
        
        pnl_l = f"{'+' if m_l['net_profit']>=0 else ''}${m_l['net_profit']:,.2f} (WR: {m_l['win_rate']:.1f}%)"
        pnl_b = f"{'+' if m_b['net_profit']>=0 else ''}${m_b['net_profit']:,.2f} (WR: {m_b['win_rate']:.1f}%)"
        print(f"{s:<12} | {pnl_l:<25} | {pnl_b:<25}")
    except Exception:
        pass

print("="*85)
print(f"💰 TOTAL PORTOFOLIO LONG ONLY  : {'+' if sum(res_long_only)>=0 else ''}${sum(res_long_only):,.2f}")
print(f"💰 TOTAL PORTOFOLIO DUA ARAH   : {'+' if sum(res_both)>=0 else ''}${sum(res_both):,.2f}")
print("="*85)
