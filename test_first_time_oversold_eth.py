import os
import sys
import pandas as pd
import numpy as np
from test_backtest_eth_15m import fetch_1year_15m_eth
from src.indicators import calculate_rsi, calculate_sma, calculate_ema, calculate_atr
from src.backtester import BacktestEngine

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

def run_first_time_oversold_eth():
    df = fetch_1year_15m_eth()
    if df is None:
        return

    df['ema_200'] = calculate_ema(df['close'], 200)
    df['ema_50'] = calculate_ema(df['close'], 50)
    df['bb_mid'] = calculate_sma(df['close'], 20)
    df['bb_std'] = df['close'].rolling(20).std()
    df['bb_lower'] = df['bb_mid'] - 2.0 * df['bb_std']
    df['bb_upper'] = df['bb_mid'] + 2.0 * df['bb_std']
    df['rsi'] = calculate_rsi(df['close'], 14)

    # 1. First Time Oversold Filter:
    # Dalam 20 lilin terakhir, RSI TIDAK PERNAH < 35 (sebelumnya sehat)
    # SEKARANG adalah sentuhan pertama (first touch)
    df['prev_rsi_min_20'] = df['rsi'].shift(1).rolling(20).min()
    was_healthy = df['prev_rsi_min_20'] >= 35

    # First Time Overbought untuk Short
    df['prev_rsi_max_20'] = df['rsi'].shift(1).rolling(20).max()
    was_low = df['prev_rsi_max_20'] <= 65

    # LONG: First Time Dip saat Bullish di atas EMA 200 + Reversal Candle Hijau
    long_cond = (
        (df['close'] > df['ema_200']) &
        was_healthy &
        (df['rsi'] < 35) &
        (df['low'] <= df['bb_lower']) &
        (df['close'] > df['open'])
    )

    # SHORT: First Time Pop saat Bearish di bawah EMA 200 + Reversal Candle Merah
    short_cond = (
        (df['close'] < df['ema_200']) &
        was_low &
        (df['rsi'] > 65) &
        (df['high'] >= df['bb_upper']) &
        (df['close'] < df['open'])
    )

    df['enter_long'] = np.where(long_cond, 1, 0)
    df['enter_short'] = np.where(short_cond, 1, 0)

    # Target Asimetris: TP +2.5% vs SL -1.0% (RRR 2.5 : 1)
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

    print("\n" + "="*85)
    print("🏆 HASIL 1 TAHUN STRATEGI 'FIRST TIME OVERSOLD RSI' PADA ETHUSDT (15M - 39.516 LILIN) 🏆")
    print("="*85)
    print(f"  • Modal Awal             : $5,000.00 USDT (Leverage 3x)")
    print(f"  • Modal Akhir            : ${m['final_capital']:,.2f} USDT")
    print(f"  • Total Net PnL ($)      : {'+' if m['net_profit']>=0 else ''}${m['net_profit']:,.2f} USDT")
    print(f"  • Total Return (ROI %)   : {'+' if m['net_profit_pct']>=0 else ''}{m['net_profit_pct']:.2f}%")
    print(f"  • Total Trades           : {m['total_trades']} Transaksi (Win: {m['win_count']}, Loss: {m['loss_count']})")
    print(f"  • Win Rate               : {m['win_rate']:.1f}%")
    print(f"  • Profit Factor          : {m['profit_factor']:.2f}")
    print(f"  • Maximum Drawdown       : -{m['max_drawdown_pct']:.2f}%")
    print("-" * 85)

    if not t.empty and 'entry_time' in t.columns:
        t['month'] = pd.to_datetime(t['entry_time']).dt.strftime('%Y-%m')
        mb = t.groupby('month').agg(total=('net_pnl','count'), win=('net_pnl', lambda x: (x>0).sum()), pnl=('net_pnl','sum')).reset_index()
        mb['wr'] = (mb['win']/mb['total'])*100
        print(f"📅 Rincian Bulan per Bulan:")
        for _, r in mb.iterrows():
            print(f"   {r['month']}: {int(r['total']):>2} trades | WR {r['wr']:>5.1f}% | PnL: {'+' if r['pnl']>=0 else ''}${r['pnl']:,.2f}")

if __name__ == "__main__":
    run_first_time_oversold_eth()
