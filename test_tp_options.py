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

def fetch_1m_data(symbol='ETHUSDT', limit=1000):
    url = f'https://data-api.binance.vision/api/v3/klines?symbol={symbol}&interval=1m&limit={limit}'
    r = requests.get(url, verify=False).json()
    cols = ['open_time', 'open', 'high', 'low', 'close', 'volume', 'close_time', 'quote_volume', 'count', 'taker_buy_volume', 'taker_buy_quote_volume', 'ignore']
    df = pd.DataFrame(r, columns=cols[:len(r[0])])
    df['timestamp'] = pd.to_datetime(df['open_time'], unit='ms')
    for c in ['open', 'high', 'low', 'close', 'volume']:
        df[c] = df[c].astype(float)
    return df

def test_dynamic_exits(symbol='ETHUSDT', exit_type='rsi_60'):
    df = fetch_1m_data(symbol, 1000)
    if df is None or len(df) < 300:
        return
    
    df['ema_7'] = calculate_ema(df['close'], 7)
    df['rsi'] = calculate_rsi(df['close'], 14)
    df['bb_mid'] = calculate_sma(df['close'], 20)
    
    # Entry: Oversold RSI < 30 + Cross Up EMA 7
    recent_oversold = df['rsi'].rolling(5).min() < 30
    cross_up = (df['close'].shift(1) <= df['ema_7'].shift(1)) & (df['close'] > df['ema_7'])
    df['enter_long'] = np.where(recent_oversold & cross_up, 1, 0)
    
    if exit_type == 'fixed_tp_0.8': # Fixed Target +0.8%, SL -0.4%
        df['tp_price'] = df['close'] * 1.008
        df['sl_price'] = df['close'] * 0.996
    elif exit_type == 'rsi_60': # TP saat RSI balik ke 60
        df['exit_long'] = np.where(df['rsi'] >= 60, 1, 0)
        df['sl_price'] = df['close'] * 0.995
    elif exit_type == 'ema7_cross_down': # Trailing EMA 7: Exit saat candle tembus kembali ke bawah EMA 7
        df['exit_long'] = np.where(df['close'] < df['ema_7'], 1, 0)
        df['sl_price'] = df['close'] * 0.995
    elif exit_type == 'bb_mid': # TP saat menyentuh Middle Bollinger Band (SMA 20)
        df['exit_long'] = np.where(df['close'] >= df['bb_mid'], 1, 0)
        df['sl_price'] = df['close'] * 0.995
        
    engine = BacktestEngine(5000.0, 3.0, 0.25, 0.0005, 0.0002)
    res = engine.run(df)
    m = res['metrics']
    pnl_str = f"{'+' if m['net_profit']>=0 else ''}${m['net_profit']:,.2f}"
    print(f"{symbol:<10} [{exit_type:<17}]: Net PnL {pnl_str:>12} ({m['net_profit_pct']:>+5.2f}%) | WR: {m['win_rate']:>5.1f}% ({m['win_count']}W/{m['loss_count']}L) | PF: {m['profit_factor']:>4.2f} | Trades: {m['total_trades']}")

def main():
    symbols = ['BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'NEARUSDT', 'SAGAUSDT', 'ENAUSDT']
    print("="*95)
    print("🎯 PENGUJIAN METODE TAKE PROFIT (TP) PADA STRATEGI RSI OVERSOLD + EMA 7 (1 MENIT)")
    print("="*95)
    for ext in ['fixed_tp_0.8', 'rsi_60', 'ema7_cross_down', 'bb_mid']:
        print(f"\n--- Skenario TP: {ext} ---")
        for s in symbols:
            test_dynamic_exits(s, ext)

if __name__ == "__main__":
    main()
