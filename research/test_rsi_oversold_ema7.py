import os
import sys
import pandas as pd
import numpy as np
from test_zec_trend_riding import fetch_1year_klines
from src.indicators import calculate_rsi, calculate_ema, calculate_sma, calculate_atr
from src.backtester import BacktestEngine

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

def test_strategy(symbol="ETHUSDT", interval="15m", use_trend_filter=True, lookback_rsi=5, rsi_thresh=35):
    df = fetch_1year_klines(symbol, interval)
    if df is None or len(df) < 500:
        return None
    
    df['ema_7'] = calculate_ema(df['close'], 7)
    df['ema_200'] = calculate_ema(df['close'], 200)
    df['rsi'] = calculate_rsi(df['close'], 14)
    df['atr'] = calculate_atr(df, 14)

    # 1. Kondisi Oversold RSI baru-baru ini
    recent_rsi_oversold = df['rsi'].rolling(window=lookback_rsi).min() < rsi_thresh
    
    # 2. Trigger: Candle Close melintasi (cross up) ke atas EMA 7
    ema7_cross_up = (df['close'].shift(1) <= df['ema_7'].shift(1)) & (df['close'] > df['ema_7'])
    
    # 3. Macro Trend Filter (Opsional)
    if use_trend_filter:
        long_cond = recent_rsi_oversold & ema7_cross_up & (df['close'] > df['ema_200'])
        
        recent_rsi_overbought = df['rsi'].rolling(window=lookback_rsi).max() > (100 - rsi_thresh)
        ema7_cross_down = (df['close'].shift(1) >= df['ema_7'].shift(1)) & (df['close'] < df['ema_7'])
        short_cond = recent_rsi_overbought & ema7_cross_down & (df['close'] < df['ema_200'])
    else:
        long_cond = recent_rsi_oversold & ema7_cross_up
        recent_rsi_overbought = df['rsi'].rolling(window=lookback_rsi).max() > (100 - rsi_thresh)
        ema7_cross_down = (df['close'].shift(1) >= df['ema_7'].shift(1)) & (df['close'] < df['ema_7'])
        short_cond = recent_rsi_overbought & ema7_cross_down

    df['enter_long'] = np.where(long_cond, 1, 0)
    df['enter_short'] = np.where(short_cond, 1, 0)

    # RRR Target: TP 2.5%, SL 1.0% (RRR 2.5:1)
    df['tp_price'] = np.where(df['enter_long'] == 1, df['close'] * 1.025, np.where(df['enter_short'] == 1, df['close'] * 0.975, np.nan))
    df['sl_price'] = np.where(df['enter_long'] == 1, df['close'] * 0.990, np.where(df['enter_short'] == 1, df['close'] * 1.010, np.nan))

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
    print(f"{symbol:<10} ({interval}): Net PnL {pnl_str:>14} ({m['net_profit_pct']:>+6.2f}%) | WR: {m['win_rate']:>5.1f}% ({m['win_count']}W/{m['loss_count']}L) | PF: {m['profit_factor']:>4.2f} | MaxDD: {m['max_drawdown_pct']:>4.2f}% | Trades: {m['total_trades']}")
    return m

def main():
    symbols = ['BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'NEARUSDT', 'AVAXUSDT', 'SAGAUSDT', 'ENAUSDT', 'ONEUSDT', 'SYNUSDT', 'ZECUSDT', 'DASHUSDT', 'DOGEUSDT']
    
    print("="*95)
    print("TEST 1: RSI OVERSOLD (<35 dl 5 bar) + EMA 7 PRICE CROSSOVER (WITH EMA 200 TREND FILTER - 15m)")
    print("="*95)
    for s in symbols:
        test_strategy(s, interval="15m", use_trend_filter=True, lookback_rsi=5, rsi_thresh=35)

    print("\n" + "="*95)
    print("TEST 2: RSI OVERSOLD (<30) + EMA 7 PRICE CROSSOVER (WITHOUT TREND FILTER - MURNI REVERSAL - 15m)")
    print("="*95)
    for s in symbols:
        test_strategy(s, interval="15m", use_trend_filter=False, lookback_rsi=5, rsi_thresh=30)

    print("\n" + "="*95)
    print("TEST 3: FIRST TIME OVERSOLD (Lookback 30 min RSI >= 35) + EMA 7 CROSSOVER (WITH EMA 200 - 15m)")
    print("="*95)
    for s in symbols:
        # First dip version
        test_strategy(s, interval="15m", use_trend_filter=True, lookback_rsi=3, rsi_thresh=35)

if __name__ == "__main__":
    main()
