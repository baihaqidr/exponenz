import os
import io
import sys
import time
import zipfile
import requests
import urllib3
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

urllib3.disable_warnings()

from src.indicators import calculate_rsi, calculate_ema, calculate_sma, calculate_atr
from src.backtester import BacktestEngine
from test_state_machine_5m_1year import fetch_1year_5m_data
from test_state_machine_1year import fetch_1year_data

def backtest_rr_1to2(symbol="BTCUSDT", interval="5m"):
    if interval == "5m":
        df = fetch_1year_5m_data(symbol)
    else:
        df = fetch_1year_data(symbol, interval)
        
    if df is None or len(df) < 1000:
        print(f"❌ {symbol:<10}: Data tidak cukup")
        return None

    df['ema_7'] = calculate_ema(df['close'], 7)
    df['rsi'] = calculate_rsi(df['close'], 14)
    df['atr'] = calculate_atr(df, 14)
    
    armed = False
    enter_long = [0] * len(df)
    tp_price = [np.nan] * len(df)
    sl_price = [np.nan] * len(df)
    
    for i in range(1, len(df)):
        rsi_val = df.loc[i, 'rsi']
        close_val = df.loc[i, 'close']
        low_val = df.loc[i, 'low']
        ema7_val = df.loc[i, 'ema_7']
        prev_close = df.loc[i-1, 'close']
        prev_ema7 = df.loc[i-1, 'ema_7']
        
        # 1. State Armed saat RSI < 30
        if rsi_val < 30:
            armed = True
            
        # 2. Trigger Entry saat lilin pertama Close > EMA 7
        if armed and (prev_close <= prev_ema7) and (close_val > ema7_val):
            enter_long[i] = 1
            armed = False
            
            # SL di Low lilin entry (atau candle sebelumnya jika low lilin sama dengan close)
            entry_p = close_val
            sl_p = low_val
            risk = entry_p - sl_p
            
            # Minimum risk buffer (minimal 0.25% agar tidak terlalu rapat akibat no-wick candle)
            min_risk = entry_p * 0.0025
            if risk < min_risk:
                risk = min_risk
                sl_p = entry_p - risk
                
            # TP = Entry + (2 * Risk) -> Rasio R:R 1:2
            tp_p = entry_p + (2.0 * risk)
            
            sl_price[i] = sl_p
            tp_price[i] = tp_p
            
    df['enter_long'] = enter_long
    df['tp_price'] = tp_price
    df['sl_price'] = sl_price
    
    engine = BacktestEngine(
        initial_capital=5000.0,
        leverage=3.0,
        fixed_pos_size_pct=0.25,
        fee_rate=0.0005,
        slippage_pct=0.0002
    )
    res = engine.run(df)
    m = res['metrics']
    t = res['trades_df']
    
    t_start = df['timestamp'].iloc[0].strftime('%Y-%m-%d')
    t_end = df['timestamp'].iloc[-1].strftime('%Y-%m-%d')
    total_days = (df['timestamp'].iloc[-1] - df['timestamp'].iloc[0]).total_seconds() / 86400
    
    pnl_str = f"{'+' if m['net_profit']>=0 else ''}${m['net_profit']:,.2f}"
    st = "🟢" if m['net_profit']>=0 else "🔴"
    print(f"• {symbol:<10} ({interval} | {total_days:.0f} Hari | {len(df):,} Lilin):")
    print(f"  ↳ Net PnL: {pnl_str:>12} ({m['net_profit_pct']:>+6.2f}%) {st} | WR: {m['win_rate']:>5.1f}% ({m['win_count']}W/{m['loss_count']}L) | PF: {m['profit_factor']:>4.2f} | MaxDD: {m['max_drawdown_pct']:>4.2f}% | Trades: {m['total_trades']}")
    
    if not t.empty and 'entry_time' in t.columns:
        t['month'] = pd.to_datetime(t['entry_time']).dt.strftime('%Y-%m')
        mb = t.groupby('month').agg(total=('net_pnl','count'), win=('net_pnl', lambda x: (x>0).sum()), pnl=('net_pnl','sum')).reset_index()
        mb['wr'] = (mb['win']/mb['total'])*100
        profitable_months = (mb['pnl'] > 0).sum()
        print(f"  ↳ Konsistensi Bulanan: {profitable_months}/{len(mb)} Bulan Hijau")
    print("-" * 95)
    return m

def main():
    symbols = ['BTCUSDT', 'SOLUSDT', 'ETHUSDT', 'NEARUSDT', 'ENAUSDT', 'SAGAUSDT', 'SYNUSDT', 'ONEUSDT', 'DASHUSDT', 'ZECUSDT']
    
    print("="*95)
    print("🎯 PENGUJIAN 1 TAHUN DENGAN RISK-TO-REWARD (R:R) 1:2")
    print("   SL = Low Candle Entry | TP = Entry + (2 * Risk) | Timeframe 5-Menit (5m)")
    print("="*95)
    for s in symbols:
        backtest_rr_1to2(s, "5m")

    print("\n" + "="*95)
    print("🎯 PENGUJIAN 1 TAHUN DENGAN RISK-TO-REWARD (R:R) 1:2 | Timeframe 15-Menit (15m)")
    print("="*95)
    for s in symbols:
        backtest_rr_1to2(s, "15m")

if __name__ == "__main__":
    main()
