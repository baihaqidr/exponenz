import os
import sys
import pandas as pd
import numpy as np
from src.data_fetcher import fetch_binance_futures_klines
from src.indicators import calculate_rsi, calculate_ema, calculate_sma, calculate_atr
from src.backtester import BacktestEngine

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

def run_test(symbol="ZETAUSDT", interval="5m", candles=1500):
    df = fetch_binance_futures_klines(symbol, interval, total_candles=candles)
    if df is None or len(df) < 100:
        return
    
    df['ema_7'] = calculate_ema(df['close'], 7)
    df['rsi'] = calculate_rsi(df['close'], 14)
    df['bb_mid'] = calculate_sma(df['close'], 20)
    df['bb_std'] = df['close'].rolling(20).std()
    df['bb_up'] = df['bb_mid'] + 2.0 * df['bb_std']
    
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
        
        if armed and (prev_close <= prev_ema7) and (close_val > ema7_val):
            enter_long[i] = 1
            armed = False
            
    df['enter_long'] = enter_long
    df['exit_long'] = np.where((df['close'] >= df['bb_up']) | (df['rsi'] >= 65), 1, 0)
    df['sl_price'] = df['close'] * 0.985
    
    engine = BacktestEngine(5000.0, 3.0, 0.25, 0.0005, 0.0002)
    res = engine.run(df)
    m = res['metrics']
    
    t_start = df['timestamp'].iloc[0].strftime('%d-%b-%Y %H:%M')
    t_end = df['timestamp'].iloc[-1].strftime('%d-%b-%Y %H:%M')
    total_days = (df['timestamp'].iloc[-1] - df['timestamp'].iloc[0]).total_seconds() / 86400
    
    pnl_str = f"{'+' if m['net_profit']>=0 else ''}${m['net_profit']:,.2f}"
    print(f"• {symbol:<10} ({interval}): {t_start} s/d {t_end} ({total_days:.1f} Hari | {len(df)} Lilin)")
    print(f"  ↳ Net PnL: {pnl_str} ({m['net_profit_pct']:>+5.2f}%) | WR: {m['win_rate']:>5.1f}% ({m['win_count']}W/{m['loss_count']}L) | PF: {m['profit_factor']:>4.2f} | Trades: {m['total_trades']}")

def main():
    print("="*95)
    print("⏱️ DETAIL PERIODE & DURASI BACKTEST TERAKHIR PADA 5 MENIT (5m):")
    print("="*95)
    symbols = ['ZETAUSDT', 'BTCUSDT', 'ETHUSDT', 'ENAUSDT', 'SAGAUSDT', 'NEARUSDT']
    for s in symbols:
        run_test(s, '5m', 1500)
        
    print("\n" + "="*95)
    print("⏱️ PENGUJIAN PERIODE LEBIH PANJANG (3,000 LILIN 15M ~ 31 HARI / 1 BULAN):")
    print("="*95)
    for s in symbols:
        run_test(s, '15m', 3000)

if __name__ == "__main__":
    main()
