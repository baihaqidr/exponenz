import os
import sys
import pandas as pd
import numpy as np
from test_backtest_eth_1y import fetch_1year_1m_eth
from src.indicators import calculate_rsi, calculate_sma, calculate_ema, calculate_atr
from src.backtester import BacktestEngine

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

def test_high_frequency_1m_scalping():
    print("="*85)
    print("⚡ MENGUJI FORMULA QUANT SCALPING HIGH-FREQUENCY 1-MENIT (571.740 LILIN)...")
    print("="*85)
    
    df = fetch_1year_1m_eth()
    if df is None:
        return

    # 1. Indikator Scalping Presisi
    df['ema_fast'] = calculate_ema(df['close'], 21)
    df['ema_slow'] = calculate_ema(df['close'], 89)
    df['ema_trend'] = calculate_ema(df['close'], 200)
    df['bb_mid'] = calculate_sma(df['close'], 20)
    df['bb_std'] = df['close'].rolling(20).std()
    df['bb_lower'] = df['bb_mid'] - 2.0 * df['bb_std']
    df['bb_upper'] = df['bb_mid'] + 2.0 * df['bb_std']
    df['bb_width'] = (df['bb_upper'] - df['bb_lower']) / df['bb_mid'] * 100
    df['rsi'] = calculate_rsi(df['close'], 14)
    df['atr'] = calculate_atr(df, 14)
    df['vol_ma'] = df['volume'].rolling(20).mean()

    # Filter Volatilitas: Hanya scalp saat ada pergerakan / likuiditas (BB Width > 0.25% & Volume aktif)
    vol_active = (df['bb_width'] >= 0.25) & (df['volume'] > 0.8 * df['vol_ma'])

    # Sinyal Scalping 2-Arah:
    # LONG: Tren Bullish (Fast > Slow & Price > Trend) + Dip (Low <= BB Lower & RSI < 35) + Reversal Candle (Close > Open)
    # SHORT: Tren Bearish (Fast < Slow & Price < Trend) + Pop (High >= BB Upper & RSI > 65) + Reversal Candle (Close < Open)
    long_cond = vol_active & (df['ema_fast'] > df['ema_slow']) & (df['close'] > df['ema_trend']) & (df['low'] <= df['bb_lower']) & (df['rsi'] < 36) & (df['close'] > df['open'])
    short_cond = vol_active & (df['ema_fast'] < df['ema_slow']) & (df['close'] < df['ema_trend']) & (df['high'] >= df['bb_upper']) & (df['rsi'] > 64) & (df['close'] < df['open'])

    df['enter_long'] = np.where(long_cond, 1, 0)
    df['enter_short'] = np.where(short_cond, 1, 0)
    
    # Asymmetric Scalp Target: TP +1.0% vs SL -0.5% (Risk Reward 2 : 1)
    df['tp_price'] = np.where(df['enter_long'] == 1, df['close'] * 1.010, np.where(df['enter_short'] == 1, df['close'] * 0.990, np.nan))
    df['sl_price'] = np.where(df['enter_long'] == 1, df['close'] * 0.995, np.where(df['enter_short'] == 1, df['close'] * 1.005, np.nan))

    # Test dengan 2 skenario fee:
    # Skenario 1: Taker Standard (0.05%)
    # Skenario 2: Maker / Scalper Pro (0.02% Limit Order)
    print("\n" + "-"*85)
    print("1. SKENARIO PRO SCALPER (Maker Limit Order 0.02% Fee - Binance Futures):")
    engine_maker = BacktestEngine(initial_capital=5000.0, leverage=3.0, fixed_pos_size_pct=0.20, fee_rate=0.0002, slippage_pct=0.0001)
    res_m = engine_maker.run(df)
    m_m = res_m['metrics']
    t_m = res_m['trades_df']
    
    print(f"   • Total Net PnL   : {'+' if m_m['net_profit']>=0 else ''}${m_m['net_profit']:,.2f} USDT ({m_m['net_profit_pct']:+.2f}% ROI)")
    print(f"   • Win Rate        : {m_m['win_rate']:.1f}% ({m_m['win_count']} Win / {m_m['loss_count']} Loss)")
    print(f"   • Total Trades    : {m_m['total_trades']:,} Transaksi")
    print(f"   • Profit Factor   : {m_m['profit_factor']:.2f}")
    print(f"   • Max Drawdown    : -{m_m['max_drawdown_pct']:.2f}%")

    print("\n" + "-"*85)
    print("2. SKENARIO STANDARD TAKER (0.05% Market Order Fee):")
    engine_taker = BacktestEngine(initial_capital=5000.0, leverage=3.0, fixed_pos_size_pct=0.20, fee_rate=0.0005, slippage_pct=0.0002)
    res_t = engine_taker.run(df)
    m_t = res_t['metrics']
    
    print(f"   • Total Net PnL   : {'+' if m_t['net_profit']>=0 else ''}${m_t['net_profit']:,.2f} USDT ({m_t['net_profit_pct']:+.2f}% ROI)")
    print(f"   • Win Rate        : {m_t['win_rate']:.1f}% ({m_t['win_count']} Win / {m_t['loss_count']} Loss)")
    print(f"   • Total Trades    : {m_t['total_trades']:,} Transaksi")
    print(f"   • Profit Factor   : {m_t['profit_factor']:.2f}")
    print(f"   • Max Drawdown    : -{m_t['max_drawdown_pct']:.2f}%")
    print("="*85)

if __name__ == "__main__":
    test_high_frequency_1m_scalping()
