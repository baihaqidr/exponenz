import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from src.data_fetcher import fetch_fast_api_klines
from src.strategy_registry import get_strategy_instance
from src.backtester import BacktestEngine
import pandas as pd
import numpy as np

symbols = ['SAGAUSDT', 'SUIUSDT', 'NEARUSDT', 'SOLUSDT', 'DOGEUSDT', 'PEPEUSDT', 'RENDERUSDT', 'AVAXUSDT']
strategy = get_strategy_instance('freqtrade_bband_rsi')

all_trades = []

for sym in symbols:
    df = fetch_fast_api_klines(sym, '5m', total_candles=2000)
    if df is not None and len(df) > 50:
        df_sig = strategy.generate_signals(df)
        engine = BacktestEngine(initial_capital=1000.0, leverage=2.0, risk_per_trade_pct=0.02, fixed_pos_size_pct=0.5)
        res = engine.run(df_sig)
        trades_df = res["trades_df"]
        if not trades_df.empty:
            trades_df['symbol'] = sym
            trades_df['price_change_pct'] = ((trades_df['exit_price'] - trades_df['entry_price']) / trades_df['entry_price']) * 100
            all_trades.append(trades_df)

if all_trades:
    combined = pd.concat(all_trades, ignore_index=True)
    wins = combined[combined['net_pnl'] > 0]
    losses = combined[combined['net_pnl'] <= 0]
    
    avg_win_price_pct = wins['price_change_pct'].mean()
    median_win_price_pct = wins['price_change_pct'].median()
    max_win_price_pct = wins['price_change_pct'].max()
    min_win_price_pct = wins['price_change_pct'].min()
    
    avg_loss_price_pct = losses['price_change_pct'].mean()
    max_loss_price_pct = losses['price_change_pct'].min()
    
    print(f"Total Sampel Trade Teranalisis: {len(combined)} Posisi")
    print(f"Win Rate Rata-rata            : {(len(wins)/len(combined)*100):.1f}%")
    print(f"--------------------------------------------------")
    print(f"KENAIKAN HARGA PADA TRADE MENANG (WINNING TRADES):")
    print(f"  * Rata-rata Kenaikan (% Harga)   : +{avg_win_price_pct:.2f}%")
    print(f"  * Median Kenaikan (% Harga)      : +{median_win_price_pct:.2f}%")
    print(f"  * Kenaikan Terbesar (Max Gain)   : +{max_win_price_pct:.2f}%")
    print(f"  * Kenaikan Terkecil (Min Gain)   : +{min_win_price_pct:.2f}%")
    print(f"--------------------------------------------------")
    print(f"PENURUNAN HARGA PADA TRADE KALAH (LOSING TRADES):")
    print(f"  * Rata-rata Penurunan (% Harga)  : {avg_loss_price_pct:.2f}%")
    print(f"  * Penurunan Maksimal (Hard SL)   : {max_loss_price_pct:.2f}%")
    print(f"--------------------------------------------------")
    print(f"DISTRIBUSI KENAIKAN PROFIT:")
    print(f"  * Profit Scalp Cepat (+1.5% s/d +4.0%) : {len(wins[(wins['price_change_pct'] >= 1.5) & (wins['price_change_pct'] <= 4.0)])} trade ({(len(wins[(wins['price_change_pct'] >= 1.5) & (wins['price_change_pct'] <= 4.0)])/len(wins)*100):.1f}%)")
    print(f"  * Profit Menengah (+4.0% s/d +10.0%)   : {len(wins[(wins['price_change_pct'] > 4.0) & (wins['price_change_pct'] <= 10.0)])} trade ({(len(wins[(wins['price_change_pct'] > 4.0) & (wins['price_change_pct'] <= 10.0)])/len(wins)*100):.1f}%)")
    print(f"  * Profit Super Rally (> +10.0%)        : {len(wins[wins['price_change_pct'] > 10.0])} trade ({(len(wins[wins['price_change_pct'] > 10.0])/len(wins)*100):.1f}%)")
