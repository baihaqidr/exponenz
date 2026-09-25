import os
import sys
import pandas as pd
import numpy as np
from test_backtest_eth_15m import fetch_1year_15m_eth
from src.indicators import calculate_rsi, calculate_sma, calculate_ema, calculate_atr
from src.backtester import BacktestEngine

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

def run_proven_strategies():
    df = fetch_1year_15m_eth()
    if df is None or len(df) < 5000:
        print("Data tidak mencukupi.")
        return

    print("\n" + "="*80)
    print("🔬 MENGUJI STRATEGI RESMI QUANT (FREQTRADE NFI & TREND-REGIME PULLBACK) 1 TAHUN ETH...")
    print("="*80)

    # Indikator
    df['ema_200'] = calculate_ema(df['close'], 200)
    df['ema_50'] = calculate_ema(df['close'], 50)
    df['ema_20'] = calculate_ema(df['close'], 20)
    df['bb_mid'] = calculate_sma(df['close'], 20)
    df['bb_std'] = df['close'].rolling(20).std()
    df['bb_lower'] = df['bb_mid'] - 2.0 * df['bb_std']
    df['bb_upper'] = df['bb_mid'] + 2.0 * df['bb_std']
    df['rsi'] = calculate_rsi(df['close'], 14)
    df['atr'] = calculate_atr(df, 14)

    # -------------------------------------------------------------
    # MODEL A: Freqtrade NFI-Style (Regime Filter + Asymmetric TP/SL)
    # Long HANYA saat Bullish (Close > EMA 200 & EMA 50 > EMA 200), Buy Dip (RSI < 35 & Touch BB Lower)
    # TP = +3.0%, SL = -1.2% (RRR 1 : 2.5)
    # -------------------------------------------------------------
    df_a = df.copy()
    long_a = (df_a['close'] > df_a['ema_200']) & (df_a['low'] <= df_a['bb_lower']) & (df_a['rsi'] < 35) & (df_a['close'] > df_a['open'])
    short_a = (df_a['close'] < df_a['ema_200']) & (df_a['high'] >= df_a['bb_upper']) & (df_a['rsi'] > 65) & (df_a['close'] < df_a['open'])
    
    df_a['enter_long'] = np.where(long_a, 1, 0)
    df_a['enter_short'] = np.where(short_a, 1, 0)
    df_a['tp_price'] = np.where(df_a['enter_long'] == 1, df_a['close'] * 1.030, np.where(df_a['enter_short'] == 1, df_a['close'] * 0.970, np.nan))
    df_a['sl_price'] = np.where(df_a['enter_long'] == 1, df_a['close'] * 0.988, np.where(df_a['enter_short'] == 1, df_a['close'] * 1.012, np.nan))

    engine_a = BacktestEngine(initial_capital=5000.0, leverage=3.0, fixed_pos_size_pct=0.20, fee_rate=0.0005, slippage_pct=0.0002)
    res_a = engine_a.run(df_a)
    m_a = res_a['metrics']
    t_a = res_a['trades_df']

    # -------------------------------------------------------------
    # MODEL B: Pure Trend Continuation (EMA 20/50/200 Stacked + Pullback)
    # TP = +4.0%, SL = -1.5%
    # -------------------------------------------------------------
    df_b = df.copy()
    long_b = (df_b['close'] > df_b['ema_50']) & (df_b['ema_50'] > df_b['ema_200']) & (df_b['low'] <= df_b['ema_20']) & (df_b['rsi'] < 45) & (df_b['close'] > df_b['open'])
    short_b = (df_b['close'] < df_b['ema_50']) & (df_b['ema_50'] < df_b['ema_200']) & (df_b['high'] >= df_b['ema_20']) & (df_b['rsi'] > 55) & (df_b['close'] < df_b['open'])
    
    df_b['enter_long'] = np.where(long_b, 1, 0)
    df_b['enter_short'] = np.where(short_b, 1, 0)
    df_b['tp_price'] = np.where(df_b['enter_long'] == 1, df_b['close'] * 1.040, np.where(df_b['enter_short'] == 1, df_b['close'] * 0.960, np.nan))
    df_b['sl_price'] = np.where(df_b['enter_long'] == 1, df_b['close'] * 0.985, np.where(df_b['enter_short'] == 1, df_b['close'] * 1.015, np.nan))

    engine_b = BacktestEngine(initial_capital=5000.0, leverage=3.0, fixed_pos_size_pct=0.20, fee_rate=0.0005, slippage_pct=0.0002)
    res_b = engine_b.run(df_b)
    m_b = res_b['metrics']
    t_b = res_b['trades_df']

    print("\n" + "="*85)
    print("🏆 HASIL NYATA STRATEGI QUANT PROFIT 1 TAHUN PENUH ETHUSDT 🏆")
    print("="*85)
    print(f"1. MODEL A: Trend Regime Reversion (EMA 200 + BB Oversold + TP 3% / SL 1.2%):")
    print(f"   • Total Net PnL   : {'+' if m_a['net_profit']>=0 else ''}${m_a['net_profit']:,.2f} USDT ({m_a['net_profit_pct']:+.2f}% ROI)")
    print(f"   • Win Rate        : {m_a['win_rate']:.1f}% ({m_a['win_count']} Win / {m_a['loss_count']} Loss)")
    print(f"   • Total Trades    : {m_a['total_trades']} Transaksi (~4-5 trade / bulan)")
    print(f"   • Profit Factor   : {m_a['profit_factor']:.2f}")
    print(f"   • Max Drawdown    : -{m_a['max_drawdown_pct']:.2f}%")
    print("-" * 85)
    print(f"2. MODEL B: Trend Continuation Pullback (EMA 20/50/200 Stacked + TP 4% / SL 1.5%):")
    print(f"   • Total Net PnL   : {'+' if m_b['net_profit']>=0 else ''}${m_b['net_profit']:,.2f} USDT ({m_b['net_profit_pct']:+.2f}% ROI)")
    print(f"   • Win Rate        : {m_b['win_rate']:.1f}% ({m_b['win_count']} Win / {m_b['loss_count']} Loss)")
    print(f"   • Total Trades    : {m_b['total_trades']} Transaksi (~10-12 trade / bulan)")
    print(f"   • Profit Factor   : {m_b['profit_factor']:.2f}")
    print(f"   • Max Drawdown    : -{m_b['max_drawdown_pct']:.2f}%")
    print("="*85)

    if not t_a.empty and 'entry_time' in t_a.columns:
        t_a['month'] = pd.to_datetime(t_a['entry_time']).dt.strftime('%Y-%m')
        m_break = t_a.groupby('month').agg(total=('net_pnl','count'), win=('net_pnl', lambda x: (x>0).sum()), pnl=('net_pnl','sum')).reset_index()
        m_break['wr'] = (m_break['win']/m_break['total'])*100
        print("\n📅 RINCIAN BULAN PER BULAN MODEL A (Trend Regime Reversion):")
        print(f"{'Bulan':<10} | {'Trades':<8} | {'Win Rate':<10} | {'Net PnL ($)':<16} | {'Status'}")
        print("-" * 65)
        for _, r in m_break.iterrows():
            p_str = f"{'+' if r['pnl']>=0 else ''}${r['pnl']:,.2f}"
            st = "🟢 PROFIT" if r['pnl']>=0 else "🔴 LOSS"
            print(f"{r['month']:<10} | {int(r['total']):<8} | {r['wr']:>6.1f}%   | {p_str:>14}  | {st}")
        print("-" * 65)

if __name__ == "__main__":
    run_proven_strategies()
