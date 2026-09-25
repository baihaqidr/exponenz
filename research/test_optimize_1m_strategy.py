import os
import sys
import time
import pandas as pd
import numpy as np
from test_backtest_eth_1y import fetch_1year_1m_eth
from src.indicators import calculate_rsi, calculate_sma, calculate_ema, calculate_atr
from src.backtester import BacktestEngine

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

def run_1m_quant_research():
    df = fetch_1year_1m_eth()
    if df is None or len(df) < 10000:
        print("Data tidak mencukupi.")
        return

    print("\n" + "="*70)
    print("🔬 MENELITI & MENGUJI STRATEGI QUANT TERBAIK PADA 1-MENIT (571.740 LILIN)...")
    print("="*70)

    # 1. Hitung Indikator Inti
    df['ema_50'] = calculate_ema(df['close'], 50)
    df['ema_200'] = calculate_ema(df['close'], 200)
    df['bb_mid'] = calculate_sma(df['close'], 20)
    df['bb_std'] = df['close'].rolling(20).std()
    df['bb_lower'] = df['bb_mid'] - 2.0 * df['bb_std']
    df['bb_upper'] = df['bb_mid'] + 2.0 * df['bb_std']
    df['rsi'] = calculate_rsi(df['close'], 14)
    df['atr'] = calculate_atr(df, 14)

    # Variasi 1: Trend-Following Pullback (Long saat Bullish di atas EMA 200, Short saat Bearish di bawah EMA 200)
    # Variasi 2: Reversal Candle Confirmation
    # Variasi 3: Dynamic TP di Middle BB + ATR Stop Loss

    results = []

    configs = [
        {"name": "1. Trend Pullback (EMA 200 Filter + Reversal + Mid-BB TP)", "ema_filter": True, "reversal": True, "tp_mode": "mid_bb", "sl_atr": 1.5, "two_way": True},
        {"name": "2. High-Reward Trend Rider (EMA 200 + RSI Dip + TP 1.5% + SL 0.8%)", "ema_filter": True, "reversal": True, "tp_mode": "fixed_tp", "tp_pct": 0.015, "sl_pct": 0.008, "two_way": True},
        {"name": "3. Pure Scalper 1m (EMA 50/200 Trend + BB Rebound + TP 1.0% + SL 0.6%)", "ema_filter": True, "reversal": False, "tp_mode": "fixed_tp", "tp_pct": 0.010, "sl_pct": 0.006, "two_way": True},
        {"name": "4. Mean Reversion Long-Only + EMA 200 Safe Filter (TP 1.2% + SL 0.7%)", "ema_filter": True, "reversal": True, "tp_mode": "fixed_tp", "tp_pct": 0.012, "sl_pct": 0.007, "two_way": False},
        {"name": "5. Breakout Super-Momentum (Volume Spike + BB Expansion)", "ema_filter": False, "reversal": False, "tp_mode": "fixed_tp", "tp_pct": 0.020, "sl_pct": 0.010, "two_way": True}
    ]

    for cfg in configs:
        data = df.copy()
        data['enter_long'] = 0
        data['enter_short'] = 0
        data['exit_long'] = 0
        data['exit_short'] = 0
        data['sl_price'] = np.nan
        data['tp_price'] = np.nan

        # Entry Long
        if cfg["name"].startswith("1."):
            long_cond = (data['close'] > data['ema_200']) & (data['low'] <= data['bb_lower']) & (data['rsi'] < 35) & (data['close'] > data['open'])
            short_cond = (data['close'] < data['ema_200']) & (data['high'] >= data['bb_upper']) & (data['rsi'] > 65) & (data['close'] < data['open'])
            data.loc[long_cond, 'enter_long'] = 1
            data.loc[short_cond, 'enter_short'] = 1
            data['exit_long'] = np.where(data['close'] >= data['bb_mid'], 1, 0)
            data['exit_short'] = np.where(data['close'] <= data['bb_mid'], 1, 0)
            data['sl_price'] = np.where(data['enter_long'] == 1, data['close'] - cfg['sl_atr'] * data['atr'],
                               np.where(data['enter_short'] == 1, data['close'] + cfg['sl_atr'] * data['atr'], np.nan))

        elif cfg["name"].startswith("2."):
            long_cond = (data['close'] > data['ema_200']) & (data['low'] <= data['bb_lower']) & (data['rsi'] < 32) & (data['close'] > data['open'])
            short_cond = (data['close'] < data['ema_200']) & (data['high'] >= data['bb_upper']) & (data['rsi'] > 68) & (data['close'] < data['open'])
            data.loc[long_cond, 'enter_long'] = 1
            data.loc[short_cond, 'enter_short'] = 1
            data['tp_price'] = np.where(data['enter_long'] == 1, data['close'] * (1 + cfg['tp_pct']),
                               np.where(data['enter_short'] == 1, data['close'] * (1 - cfg['tp_pct']), np.nan))
            data['sl_price'] = np.where(data['enter_long'] == 1, data['close'] * (1 - cfg['sl_pct']),
                               np.where(data['enter_short'] == 1, data['close'] * (1 + cfg['sl_pct']), np.nan))

        elif cfg["name"].startswith("3."):
            long_cond = (data['close'] > data['ema_200']) & (data['rsi'] < 30)
            short_cond = (data['close'] < data['ema_200']) & (data['rsi'] > 70)
            data.loc[long_cond, 'enter_long'] = 1
            data.loc[short_cond, 'enter_short'] = 1
            data['tp_price'] = np.where(data['enter_long'] == 1, data['close'] * (1 + cfg['tp_pct']),
                               np.where(data['enter_short'] == 1, data['close'] * (1 - cfg['tp_pct']), np.nan))
            data['sl_price'] = np.where(data['enter_long'] == 1, data['close'] * (1 - cfg['sl_pct']),
                               np.where(data['enter_short'] == 1, data['close'] * (1 + cfg['sl_pct']), np.nan))

        elif cfg["name"].startswith("4."):
            long_cond = (data['close'] > data['ema_200']) & (data['low'] <= data['bb_lower']) & (data['rsi'] < 32) & (data['close'] > data['open'])
            data.loc[long_cond, 'enter_long'] = 1
            data['tp_price'] = np.where(data['enter_long'] == 1, data['close'] * (1 + cfg['tp_pct']), np.nan)
            data['sl_price'] = np.where(data['enter_long'] == 1, data['close'] * (1 - cfg['sl_pct']), np.nan)

        elif cfg["name"].startswith("5."):
            # BB Squeeze Breakout + Volume
            vol_ma = data['volume'].rolling(20).mean()
            long_cond = (data['close'] > data['bb_upper']) & (data['volume'] > 2.0 * vol_ma) & (data['rsi'] > 60)
            short_cond = (data['close'] < data['bb_lower']) & (data['volume'] > 2.0 * vol_ma) & (data['rsi'] < 40)
            data.loc[long_cond, 'enter_long'] = 1
            data.loc[short_cond, 'enter_short'] = 1
            data['tp_price'] = np.where(data['enter_long'] == 1, data['close'] * (1 + cfg['tp_pct']),
                               np.where(data['enter_short'] == 1, data['close'] * (1 - cfg['tp_pct']), np.nan))
            data['sl_price'] = np.where(data['enter_long'] == 1, data['close'] * (1 - cfg['sl_pct']),
                               np.where(data['enter_short'] == 1, data['close'] * (1 + cfg['sl_pct']), np.nan))

        engine = BacktestEngine(
            initial_capital=5000.0,
            leverage=3.0,
            fixed_pos_size_pct=0.20,
            fee_rate=0.0005,
            slippage_pct=0.0002
        )
        res = engine.run(data)
        m = res.get("metrics", {})
        results.append({
            "name": cfg["name"],
            "trades": m.get("total_trades", 0),
            "win_rate": m.get("win_rate", 0),
            "net_pnl": m.get("net_profit", 0),
            "roi": m.get("net_profit_pct", 0),
            "profit_factor": m.get("profit_factor", 0),
            "max_dd": m.get("max_drawdown_pct", 0)
        })
        print(f"  [DONE] {cfg['name']}: Net PnL {'+' if m.get('net_profit',0)>=0 else ''}${m.get('net_profit',0):,.2f} ({m.get('net_profit_pct',0):+.1f}%), WinRate {m.get('win_rate',0):.1f}%, Trades {m.get('total_trades',0)}")

    print("\n" + "="*80)
    print("🏆 PERBANDINGAN STRATEGI 1-MENIT (1 TAHUN PENUH ETHUSDT - 571.740 LILIN) 🏆")
    print("="*80)
    print(f"{'Nama Strategi':<42} | {'Trades':<7} | {'WinRate':<8} | {'Net PnL ($)':<14} | {'ROI (%)':<8} | {'Max DD'}")
    print("-" * 90)
    for r in results:
        pnl_str = f"{'+' if r['net_pnl'] >= 0 else ''}${r['net_pnl']:,.2f}"
        print(f"{r['name'][:42]:<42} | {r['trades']:<7} | {r['win_rate']:>6.1f}% | {pnl_str:>14} | {r['roi']:>+6.1f}% | {r['max_dd']:>5.1f}%")
    print("="*80)

if __name__ == "__main__":
    run_1m_quant_research()
