import sys
import pandas as pd
import numpy as np
from test_zec_trend_riding import fetch_1year_klines
from src.indicators import calculate_supertrend, calculate_ema
from src.backtester import BacktestEngine

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

def main():
    pairs = ['BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'BNBUSDT', 'XRPUSDT', 'ADAUSDT', 'DOGEUSDT', 'AVAXUSDT', 'DOTUSDT', 'LINKUSDT', 'NEARUSDT', 'LTCUSDT', 'ATOMUSDT', 'UNIUSDT', 'FILUSDT', 'ETCUSDT', 'APTUSDT', 'OPUSDT', 'ARBUSDT', 'INJUSDT']
    print("="*85)
    print("🔬 UJI COBA TANPA BIAS: SUPERTREND PADA 20 KOIN UTAMA MARKET (BULL, BEAR, & CHOP)...")
    print("="*85)
    
    results = []
    for sym in pairs:
        try:
            df = fetch_1year_klines(sym, '1h')
            df['supertrend'], df['st_dir'] = calculate_supertrend(df, 10, 3.0)
            df['ema_50'] = calculate_ema(df['close'], 50)
            
            df['enter_long'] = np.where((df['st_dir'] == 1) & (df['st_dir'].shift(1) == -1) & (df['close'] > df['ema_50']), 1, 0)
            df['exit_long'] = np.where(df['st_dir'] == -1, 1, 0)
            df['enter_short'] = np.where((df['st_dir'] == -1) & (df['st_dir'].shift(1) == 1) & (df['close'] < df['ema_50']), 1, 0)
            df['exit_short'] = np.where(df['st_dir'] == 1, 1, 0)
            df['sl_price'] = df['supertrend']
            
            engine = BacktestEngine(initial_capital=5000.0, leverage=2.0, fixed_pos_size_pct=0.20, fee_rate=0.0005, slippage_pct=0.0002)
            res = engine.run(df)
            m = res['metrics']
            results.append({
                'symbol': sym,
                'net_pnl': m['net_profit'],
                'roi_pct': m['net_profit_pct'],
                'win_rate': m['win_rate'],
                'profit_factor': m['profit_factor'],
                'max_dd': m['max_drawdown_pct'],
                'trades': m['total_trades']
            })
        except Exception as e:
            pass
            
    df_res = pd.DataFrame(results)
    print(f"{'Symbol':<12} | {'Net PnL ($)':<14} | {'ROI (%)':<9} | {'Win Rate':<9} | {'Profit Factor':<14} | {'Max DD'}")
    print("-" * 80)
    for _, r in df_res.iterrows():
        pnl_str = f"{'+' if r['net_pnl']>=0 else ''}${r['net_pnl']:,.2f}"
        print(f"{r['symbol']:<12} | {pnl_str:>14} | {r['roi_pct']:>+7.2f}% | {r['win_rate']:>6.1f}% | {r['profit_factor']:>12.2f} | {r['max_dd']:>5.2f}%")
    print("="*80)
    print(f"💰 Total Portofolio Net PnL (20 Koin): {'+' if df_res['net_pnl'].sum()>=0 else ''}${df_res['net_pnl'].sum():,.2f}")
    print(f"📊 Koin Menghasilkan Profit           : {(df_res['net_pnl'] > 0).sum()} dari {len(df_res)} koin ({(df_res['net_pnl'] > 0).sum()/len(df_res)*100:.0f}%)")
    print(f"📉 Koin Mengalami Kerugian            : {(df_res['net_pnl'] <= 0).sum()} dari {len(df_res)} koin")
    print("="*80)

if __name__ == "__main__":
    main()
