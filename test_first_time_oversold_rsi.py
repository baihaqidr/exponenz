import os
import sys
import pandas as pd
import numpy as np
from test_zec_trend_riding import fetch_1year_klines
from src.indicators import calculate_rsi, calculate_sma, calculate_ema, calculate_atr
from src.backtester import BacktestEngine

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

def test_first_time_oversold(symbol="ETHUSDT", interval="15m"):
    df = fetch_1year_klines(symbol, interval)
    if df is None or len(df) < 500:
        return

    df['ema_200'] = calculate_ema(df['close'], 200)
    df['ema_50'] = calculate_ema(df['close'], 50)
    df['bb_mid'] = calculate_sma(df['close'], 20)
    df['bb_std'] = df['close'].rolling(20).std()
    df['bb_lower'] = df['bb_mid'] - 2.0 * df['bb_std']
    df['rsi'] = calculate_rsi(df['close'], 14)
    df['atr'] = calculate_atr(df, 14)

    # 1. Konsep "First Time Oversold":
    # Cek apakah dalam 30 lilin sebelumnya (lookback 30), RSI TIDAK PERNAH < 35 (artinya tren sebelumnya kuat/normal).
    # Dan SEKARANG adalah PERTAMA KALINYA RSI anjlok < 32 & sentuh Lower BB!
    
    rsi_min_prev_30 = df['rsi'].shift(1).rolling(window=30).min()
    was_healthy_before = rsi_min_prev_30 >= 35
    
    # Entry Long: First Time Oversold saat tren di atas EMA 200 + Lilin Reversal Hijau
    first_time_dip = (
        (df['close'] > df['ema_200']) &          # Tren Makro Bullish
        was_healthy_before &                     # 30 lilin sebelumnya tidak pernah oversold (First Dip!)
        (df['rsi'] < 34) &                       # Baru pertama kali tembus oversold
        (df['low'] <= df['bb_lower']) &          # Sentuh Lower Bollinger Band
        (df['close'] > df['open'])               # Lilin pembalikan arah hijau
    )

    # First Time Overbought untuk SHORT:
    rsi_max_prev_30 = df['rsi'].shift(1).rolling(window=30).max()
    was_low_before = rsi_max_prev_30 <= 65
    first_time_pop = (
        (df['close'] < df['ema_200']) &          # Tren Makro Bearish
        was_low_before &                         # 30 lilin sebelumnya tidak pernah overbought (First Pop!)
        (df['rsi'] > 66) &                       # Baru pertama kali tembus overbought
        (df['high'] >= df['bb_mid'] + 2.0 * df['bb_std']) &
        (df['close'] < df['open'])
    )

    df['enter_long'] = np.where(first_time_dip, 1, 0)
    df['enter_short'] = np.where(first_time_pop, 1, 0)
    
    # Exit di Middle BB (SMA 20) atau TP +2.5%, SL ketat -1.0%
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
    t = res['trades_df']

    pnl_str = f"{'+' if m['net_profit']>=0 else ''}${m['net_profit']:,.2f}"
    print(f"{symbol:<10} ({interval}): Net PnL {pnl_str:>14} ({m['net_profit_pct']:>+6.2f}%) | WR: {m['win_rate']:>5.1f}% ({m['win_count']}W/{m['loss_count']}L) | PF: {m['profit_factor']:>4.2f} | MaxDD: {m['max_drawdown_pct']:>4.2f}% | Trades: {m['total_trades']}")
    return m

def main():
    print("="*85)
    print("🎯 MENGUJI LOGIKA 'FIRST TIME OVERSOLD RSI' PADA BERBAGAI KOIN (1 TAHUN)...")
    print("="*85)
    
    symbols = ['ETHUSDT', 'BTCUSDT', 'SOLUSDT', 'NEARUSDT', 'AVAXUSDT', 'SAGAUSDT', 'ENAUSDT']
    for sym in symbols:
        test_first_time_oversold(sym, "15m")
    print("="*85)

if __name__ == "__main__":
    main()
