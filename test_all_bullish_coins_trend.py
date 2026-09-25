import sys
import pandas as pd
import numpy as np
from test_zec_trend_riding import fetch_1year_klines
from src.indicators import calculate_supertrend, calculate_ema
from src.backtester import BacktestEngine

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

def main():
    symbols = ['ZECUSDT', 'JSTUSDT', 'DASHUSDT', 'NEARUSDT', 'ORDIUSDT', 'TRXUSDT', 'AAVEUSDT', 'SKYUSDT']
    print("="*85)
    print("🏆 UJI COBA STRATEGI TREND RIDER (SUPERTREND 1H) PADA 8 KOIN PALING BULLISH 🏆")
    print("="*85)
    print(f"{'Symbol':<12} | {'Net PnL ($)':<16} | {'ROI (%)':<10} | {'Profit Factor':<15} | {'Max DD':<10} | {'Total Trades'}")
    print("-" * 85)

    total_net = 0
    for sym in symbols:
        try:
            df = fetch_1year_klines(sym, '1h')
            df['supertrend'], df['st_dir'] = calculate_supertrend(df, 10, 3.0)
            df['ema_50'] = calculate_ema(df['close'], 50)
            
            # Trend Rider Rules
            df['enter_long'] = np.where((df['st_dir'] == 1) & (df['st_dir'].shift(1) == -1) & (df['close'] > df['ema_50']), 1, 0)
            df['exit_long'] = np.where(df['st_dir'] == -1, 1, 0)
            df['enter_short'] = np.where((df['st_dir'] == -1) & (df['st_dir'].shift(1) == 1) & (df['close'] < df['ema_50']), 1, 0)
            df['exit_short'] = np.where(df['st_dir'] == 1, 1, 0)
            df['sl_price'] = df['supertrend']
            
            engine = BacktestEngine(initial_capital=5000.0, leverage=2.0, fixed_pos_size_pct=0.30, fee_rate=0.0005, slippage_pct=0.0002)
            res = engine.run(df)
            m = res['metrics']
            total_net += m['net_profit']
            
            pnl_str = f"{'+' if m['net_profit']>=0 else ''}${m['net_profit']:,.2f}"
            print(f"{sym:<12} | {pnl_str:>16} | {m['net_profit_pct']:>+9.2f}% | {m['profit_factor']:>14.2f} | {m['max_drawdown_pct']:>8.2f}% | {m['total_trades']:>6}")
        except Exception as e:
            print(f"{sym:<12} | Error: {e}")

    print("="*85)
    print(f"💰 TOTAL AKUMULASI NET PROFIT PORTFOLIO: {'+' if total_net>=0 else ''}${total_net:,.2f} USDT")
    print("="*85)

if __name__ == "__main__":
    main()
