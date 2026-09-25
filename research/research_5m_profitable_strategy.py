import os
import sys
import time
import pandas as pd
import numpy as np
from test_backtest_eth_5m import fetch_1year_5m_eth
from src.indicators import calculate_rsi, calculate_sma, calculate_ema, calculate_atr, calculate_supertrend
from src.backtester import BacktestEngine

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

def run_5m_quant_research():
    df = fetch_1year_5m_eth()
    if df is None or len(df) < 10000:
        print("Data 5m tidak mencukupi.")
        return

    print("\n" + "="*85)
    print("🔬 RISET & OPTIMASI KUANTITATIF RESMI: TIMEFRAME 5-MENIT (115.548 LILIN - 1 TAHUN PENUH)...")
    print("="*85)

    # Pra-kalkulasi Indikator Dasar
    df['ema_20'] = calculate_ema(df['close'], 20)
    df['ema_50'] = calculate_ema(df['close'], 50)
    df['ema_200'] = calculate_ema(df['close'], 200)
    df['bb_mid'] = calculate_sma(df['close'], 20)
    df['bb_std'] = df['close'].rolling(20).std()
    df['bb_lower'] = df['bb_mid'] - 2.0 * df['bb_std']
    df['bb_upper'] = df['bb_mid'] + 2.0 * df['bb_std']
    df['rsi'] = calculate_rsi(df['close'], 14)
    df['atr'] = calculate_atr(df, 14)
    df['vol_ma'] = df['volume'].rolling(20).mean()
    df['supertrend'], df['st_dir'] = calculate_supertrend(df, 10, 3.0)

    # Matrix Strategi yang Diuji
    test_cases = [
        # Model 1: Asymmetric Trend Pullback (TP 2.0% vs SL 0.8% - RRR 2.5:1)
        {
            "id": "M1_Trend_Pullback_Asymmetric",
            "name": "1. Asymmetric Trend Pullback (EMA 200 + RSI Dip + TP 2.0% / SL 0.8%)",
            "fn": lambda d: (
                (d['close'] > d['ema_200']) & (d['low'] <= d['bb_lower']) & (d['rsi'] < 34) & (d['close'] > d['open']),
                (d['close'] < d['ema_200']) & (d['high'] >= d['bb_upper']) & (d['rsi'] > 66) & (d['close'] < d['open']),
                d['close'] * 1.020, d['close'] * 0.980,
                d['close'] * 0.992, d['close'] * 1.008,
                None, None
            )
        },
        # Model 2: High Probability Middle Band Exit (TP di SMA 20 + Tight SL 0.7%)
        {
            "id": "M2_Mid_BB_Exit",
            "name": "2. Mean Reversion Middle-Band Exit (Touch Mid-BB TP + SL 0.7%)",
            "fn": lambda d: (
                (d['close'] > d['ema_200']) & (d['low'] <= d['bb_lower']) & (d['rsi'] < 30) & (d['close'] > d['open']),
                (d['close'] < d['ema_200']) & (d['high'] >= d['bb_upper']) & (d['rsi'] > 70) & (d['close'] < d['open']),
                None, None,
                d['close'] * 0.993, d['close'] * 1.007,
                np.where(d['close'] >= d['bb_mid'], 1, 0),
                np.where(d['close'] <= d['bb_mid'], 1, 0)
            )
        },
        # Model 3: EMA Ribbon Trend Flow (EMA 20/50/200 Alignment + TP 2.5% / SL 1.0%)
        {
            "id": "M3_EMA_Ribbon_Flow",
            "name": "3. EMA Ribbon Trend Flow (20 > 50 > 200 + Pullback EMA 20 + TP 2.5% / SL 1.0%)",
            "fn": lambda d: (
                (d['ema_20'] > d['ema_50']) & (d['ema_50'] > d['ema_200']) & (d['low'] <= d['ema_20']) & (d['rsi'] < 48) & (d['close'] > d['open']),
                (d['ema_20'] < d['ema_50']) & (d['ema_50'] < d['ema_200']) & (d['high'] >= d['ema_20']) & (d['rsi'] > 52) & (d['close'] < d['open']),
                d['close'] * 1.025, d['close'] * 0.975,
                d['close'] * 0.990, d['close'] * 1.010,
                None, None
            )
        },
        # Model 4: 5M Supertrend Trailing Scalper
        {
            "id": "M4_Supertrend_5M",
            "name": "4. Supertrend 5M Trailing Scalper (st_dir change + EMA 50 Filter)",
            "fn": lambda d: (
                (d['st_dir'] == 1) & (d['st_dir'].shift(1) == -1) & (d['close'] > d['ema_50']),
                (d['st_dir'] == -1) & (d['st_dir'].shift(1) == 1) & (d['close'] < d['ema_50']),
                None, None,
                d['supertrend'], d['supertrend'],
                np.where(d['st_dir'] == -1, 1, 0),
                np.where(d['st_dir'] == 1, 1, 0)
            )
        },
        # Model 5: High-Reward Sniper (TP 3.0% vs SL 1.0% - RRR 3:1)
        {
            "id": "M5_Sniper_3to1",
            "name": "5. High-Reward Sniper 5M (RRR 3 : 1, TP 3.0% / SL 1.0% + EMA 200)",
            "fn": lambda d: (
                (d['close'] > d['ema_200']) & (d['low'] <= d['bb_lower']) & (d['rsi'] < 30) & (d['close'] > d['open']),
                (d['close'] < d['ema_200']) & (d['high'] >= d['bb_upper']) & (d['rsi'] > 70) & (d['close'] < d['open']),
                d['close'] * 1.030, d['close'] * 0.970,
                d['close'] * 0.990, d['close'] * 1.010,
                None, None
            )
        }
    ]

    results = []

    for tc in test_cases:
        data = df.copy()
        data['enter_long'] = 0
        data['enter_short'] = 0
        data['exit_long'] = 0
        data['exit_short'] = 0
        data['tp_price'] = np.nan
        data['sl_price'] = np.nan

        l_cond, s_cond, tp_l, tp_s, sl_l, sl_s, ex_l, ex_s = tc["fn"](data)
        
        data.loc[l_cond, 'enter_long'] = 1
        data.loc[s_cond, 'enter_short'] = 1

        if tp_l is not None:
            data['tp_price'] = np.where(data['enter_long'] == 1, tp_l, np.where(data['enter_short'] == 1, tp_s, np.nan))
        if sl_l is not None:
            data['sl_price'] = np.where(data['enter_long'] == 1, sl_l, np.where(data['enter_short'] == 1, sl_s, np.nan))
        if ex_l is not None:
            data['exit_long'] = ex_l
            data['exit_short'] = ex_s

        engine = BacktestEngine(
            initial_capital=5000.0,
            leverage=3.0,
            fixed_pos_size_pct=0.20,
            fee_rate=0.0005,
            slippage_pct=0.0002
        )
        res = engine.run(data)
        m = res['metrics']
        t = res['trades_df']

        results.append({
            "name": tc["name"],
            "trades": m['total_trades'],
            "win_rate": m['win_rate'],
            "win_count": m['win_count'],
            "loss_count": m['loss_count'],
            "net_pnl": m['net_profit'],
            "roi_pct": m['net_profit_pct'],
            "profit_factor": m['profit_factor'],
            "max_dd": m['max_drawdown_pct'],
            "trades_df": t
        })
        print(f"  [SELESAI] {tc['name']}: Net PnL {'+' if m['net_profit']>=0 else ''}${m['net_profit']:,.2f} ({m['net_profit_pct']:+.1f}%), WinRate {m['win_rate']:.1f}%, DD {m['max_drawdown_pct']:.1f}%, Trades {m['total_trades']}")

    print("\n" + "="*95)
    print("🏆 HASIL PERBANDINGAN RISET 5-MENIT (1 TAHUN PENUH ETHUSDT - 115.548 LILIN) 🏆")
    print("="*95)
    print(f"{'Nama Model Strategi':<48} | {'Trades':<7} | {'WinRate':<8} | {'Net PnL ($)':<14} | {'ROI (%)':<8} | {'Max DD'}")
    print("-" * 95)
    for r in results:
        pnl_str = f"{'+' if r['net_pnl'] >= 0 else ''}${r['net_pnl']:,.2f}"
        print(f"{r['name'][:48]:<48} | {r['trades']:<7} | {r['win_rate']:>6.1f}% | {pnl_str:>14} | {r['roi_pct']:>+6.1f}% | {r['max_dd']:>5.1f}%")
    print("="*95)

    # Tampilkan rincian bulanan untuk model terbaik
    best_model = sorted(results, key=lambda x: x['net_pnl'], reverse=True)[0]
    print(f"\n🌟 STRATEGI 5M TERBAIK: {best_model['name']}")
    if not best_model['trades_df'].empty and 'entry_time' in best_model['trades_df'].columns:
        bt_df = best_model['trades_df']
        bt_df['month'] = pd.to_datetime(bt_df['entry_time']).dt.strftime('%Y-%m')
        mb = bt_df.groupby('month').agg(total=('net_pnl','count'), win=('net_pnl', lambda x: (x>0).sum()), pnl=('net_pnl','sum')).reset_index()
        mb['wr'] = (mb['win']/mb['total'])*100
        print(f"\n📅 Rincian Bulan per Bulan Strategi Terbaik:")
        print(f"{'Bulan':<10} | {'Trades':<8} | {'Win Rate':<10} | {'Net PnL ($)':<16} | {'Status'}")
        print("-" * 65)
        for _, r in mb.iterrows():
            p_str = f"{'+' if r['pnl']>=0 else ''}${r['pnl']:,.2f}"
            st = "🟢 PROFIT" if r['pnl']>=0 else "🔴 LOSS"
            print(f"{r['month']:<10} | {int(r['total']):<8} | {r['wr']:>6.1f}%   | {p_str:>14}  | {st}")
        print("-" * 65)

if __name__ == "__main__":
    run_5m_quant_research()
