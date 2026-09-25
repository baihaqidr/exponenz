import os
import sys
import requests
import urllib3
import pandas as pd
import numpy as np
from src.indicators import calculate_rsi, calculate_ema, calculate_sma, calculate_atr
from src.backtester import BacktestEngine

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

urllib3.disable_warnings()

from src.data_fetcher import fetch_binance_futures_klines

def fetch_klines(symbol='ZETAUSDT', interval='5m', limit=1500):
    try:
        return fetch_binance_futures_klines(symbol, interval, total_candles=limit)
    except Exception as e:
        print(f"Error fetching {symbol}: {e}")
        return None

def test_zeta_setup(symbol='ZETAUSDT', interval='5m', sl_pct=0.015):
    df = fetch_klines(symbol, interval, 1500)
    if df is None or len(df) < 200:
        return
    
    df['ema_7'] = calculate_ema(df['close'], 7)
    df['rsi'] = calculate_rsi(df['close'], 14)
    df['bb_mid'] = calculate_sma(df['close'], 20)
    df['bb_std'] = df['close'].rolling(20).std()
    df['bb_up'] = df['bb_mid'] + 2.0 * df['bb_std']
    df['atr'] = calculate_atr(df, 14)
    
    # State Machine: 
    # 1. State 'armed' aktif saat RSI < 30 (Oversold terjadi)
    # 2. Begitu armed, lilin pertama yang Close > EMA 7 memicu ENTRY LONG, lalu armed di-reset ke False (First Cross Only)
    
    armed = False
    enter_long = [0] * len(df)
    
    for i in range(1, len(df)):
        rsi_val = df.loc[i, 'rsi']
        close_val = df.loc[i, 'close']
        ema7_val = df.loc[i, 'ema_7']
        prev_close = df.loc[i-1, 'close']
        prev_ema7 = df.loc[i-1, 'ema_7']
        
        if rsi_val < 30:
            armed = True
        
        # Lilin pertama yang cross up ke atas EMA 7
        if armed and (prev_close <= prev_ema7) and (close_val > ema7_val):
            enter_long[i] = 1
            armed = False # Hanya 1x entry per siklus oversold!
            
    df['enter_long'] = enter_long
    
    # Target Exit: Upper Bollinger Band atau RSI >= 65
    df['exit_long'] = np.where((df['close'] >= df['bb_up']) | (df['rsi'] >= 65), 1, 0)
    df['sl_price'] = df['close'] * (1.0 - sl_pct)
    
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
    
    pnl_str = f"{'+' if m['net_profit']>=0 else ''}${m['net_profit']:,.2f}"
    print(f"{symbol:<10} ({interval}): Net PnL {pnl_str:>12} ({m['net_profit_pct']:>+5.2f}%) | WR: {m['win_rate']:>5.1f}% ({m['win_count']}W/{m['loss_count']}L) | PF: {m['profit_factor']:>4.2f} | Trades: {m['total_trades']}")
    if not t.empty:
        for _, row in t.tail(2).iterrows():
            print(f"   ↳ Trade: {str(row['entry_time'])[-8:]} @ {row['entry_price']:.5f} -> {str(row['exit_time'])[-8:]} @ {row['exit_price']:.5f} | Net: {'+' if row['net_pnl']>=0 else ''}${row['net_pnl']:.2f}")
    return m

def main():
    symbols = ['ZETAUSDT', 'NEARUSDT', 'SOLUSDT', 'BTCUSDT', 'ETHUSDT', 'SAGAUSDT', 'ENAUSDT', 'ONEUSDT', 'SYNUSDT', 'DOGEUSDT', 'ZECUSDT']
    print("="*95)
    print("🎯 HASIL BACKTEST EXACT STATE MACHINE (RSI < 30 -> FIRST CANDLE CROSS UP EMA 7 -> EXIT UPPER BB / RSI 65)")
    print("="*95)
    for s in symbols:
        test_zeta_setup(s, '5m', sl_pct=0.015)

if __name__ == "__main__":
    main()
