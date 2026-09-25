import os
import sys
import pandas as pd
import numpy as np
from test_state_machine_1year import fetch_1year_data
from src.indicators import calculate_rsi, calculate_ema, calculate_sma
from src.backtester import BacktestEngine

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

def test_1y_with_ema200(symbol='BTCUSDT', interval='15m'):
    df = fetch_1year_data(symbol, interval)
    if df is None or len(df) < 500:
        return
    
    df['ema_7'] = calculate_ema(df['close'], 7)
    df['ema_200'] = calculate_ema(df['close'], 200)
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
        ema200_val = df.loc[i, 'ema_200']
        prev_close = df.loc[i-1, 'close']
        prev_ema7 = df.loc[i-1, 'ema_7']
        
        # Hanya aktif jika harga di atas EMA 200 (Tren Bullish)
        if rsi_val < 32 and close_val > ema200_val:
            armed = True
            
        if armed and (prev_close <= prev_ema7) and (close_val > ema7_val):
            enter_long[i] = 1
            armed = False
            
    df['enter_long'] = enter_long
    df['exit_long'] = np.where((df['close'] >= df['bb_up']) | (df['rsi'] >= 65), 1, 0)
    df['sl_price'] = df['close'] * 0.985 # SL -1.5%
    
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
    print(f"{symbol:<10} (1-Year Bullish Dip): Net PnL {pnl_str:>12} ({m['net_profit_pct']:>+6.2f}%) | WR: {m['win_rate']:>5.1f}% ({m['win_count']}W/{m['loss_count']}L) | PF: {m['profit_factor']:>4.2f} | MaxDD: {m['max_drawdown_pct']:>4.2f}% | Trades: {m['total_trades']}")
    return m

def main():
    symbols = ['BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'NEARUSDT', 'SAGAUSDT', 'ENAUSDT', 'ONEUSDT', 'SYNUSDT', 'ZECUSDT', 'DASHUSDT']
    print("="*105)
    print("🎯 HASIL 1 TAHUN PENUH: RSI < 30 + FIRST EMA 7 CROSSOVER + FILTER EMA 200 BULLISH (15m)")
    print("="*105)
    for s in symbols:
        test_1y_with_ema200(s, '15m')

if __name__ == "__main__":
    main()
