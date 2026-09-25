import os
import sys
import requests
import urllib3
import pandas as pd
import numpy as np
from src.indicators import calculate_rsi, calculate_ema, calculate_atr
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

def test_1m_rsi_ema7(symbol='ETHUSDT', tp_pct=0.008, sl_pct=0.004, use_trend=False):
    df = fetch_1m_data(symbol, 1000)
    if df is None or len(df) < 300:
        return
    
    df['ema_7'] = calculate_ema(df['close'], 7)
    df['ema_200'] = calculate_ema(df['close'], 200)
    df['rsi'] = calculate_rsi(df['close'], 14)
    
    # 1. Oversold RSI < 30 dalam 5 candle terakhir
    recent_oversold = df['rsi'].rolling(5).min() < 30
    
    # 2. Crossover EMA 7
    cross_up = (df['close'].shift(1) <= df['ema_7'].shift(1)) & (df['close'] > df['ema_7'])
    
    # Sinyal Long
    if use_trend:
        long_cond = recent_oversold & cross_up & (df['close'] > df['ema_200'])
    else:
        long_cond = recent_oversold & cross_up
        
    df['enter_long'] = np.where(long_cond, 1, 0)
    
    # Target scalping 1m
    df['tp_price'] = np.where(df['enter_long'] == 1, df['close'] * (1.0 + tp_pct), np.nan)
    df['sl_price'] = np.where(df['enter_long'] == 1, df['close'] * (1.0 - sl_pct), np.nan)
    
    engine = BacktestEngine(
        initial_capital=5000.0,
        leverage=3.0,
        fixed_pos_size_pct=0.25,
        fee_rate=0.0005,
        slippage_pct=0.0002
    )
    res = engine.run(df)
    m = res['metrics']
    pnl_str = f"{'+' if m['net_profit']>=0 else ''}${m['net_profit']:,.2f}"
    print(f"{symbol:<10} (1m): Net PnL {pnl_str:>12} ({m['net_profit_pct']:>+5.2f}%) | WR: {m['win_rate']:>5.1f}% ({m['win_count']}W/{m['loss_count']}L) | PF: {m['profit_factor']:>4.2f} | MaxDD: {m['max_drawdown_pct']:>4.2f}% | Trades: {m['total_trades']}")
    return m

def main():
    symbols = ['BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'NEARUSDT', 'AVAXUSDT', 'SAGAUSDT', 'ENAUSDT', 'ONEUSDT', 'SYNUSDT', 'DOGEUSDT', 'ZECUSDT', 'DASHUSDT']
    
    print("="*95)
    print("TEST 1: 1-MINUTE SCALPING - RSI OVERSOLD (<30) + EMA 7 CROSS (TP 0.8%, SL 0.4% - MURNI)")
    print("="*95)
    for s in symbols:
        test_1m_rsi_ema7(s, tp_pct=0.008, sl_pct=0.004, use_trend=False)

    print("\n" + "="*95)
    print("TEST 2: 1-MINUTE SCALPING - RSI OVERSOLD (<30) + EMA 7 CROSS + EMA 200 TREND FILTER")
    print("="*95)
    for s in symbols:
        test_1m_rsi_ema7(s, tp_pct=0.008, sl_pct=0.004, use_trend=True)

if __name__ == "__main__":
    main()
