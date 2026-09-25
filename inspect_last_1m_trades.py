import os
import sys
import pandas as pd
import numpy as np
from datetime import datetime

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

from test_1year_1m_strategy_pnl import fetch_1year_1m_data
from src.strategies.rsi_first_ema7_crossover import RsiFirstEma7CrossoverStrategy
from src.backtester import BacktestEngine

def inspect_last_trades(symbol="BTCUSDT"):
    df = fetch_1year_1m_data(symbol)
    if df is None:
        return
    
    strat = RsiFirstEma7CrossoverStrategy(rsi_period=14, rsi_oversold=30.0, ema_period=7, rr_multiplier=2.0)
    df_signals = strat.generate_signals(df)
    
    engine = BacktestEngine(5000.0, 3.0, 0.25, 0.0005, 0.0002)
    res = engine.run(df_signals)
    t = res['trades_df']
    
    if t.empty:
        print(f"Tidak ada trade untuk {symbol}")
        return
        
    print("="*90)
    print(f"🔍 DETAIL TRADE TERAKHIR {symbol} DI TIMEFRAME 1-MENIT (1m):")
    print("="*90)
    
    # Ambil 3 trade terakhir
    for idx, row in t.tail(3).iterrows():
        entry_t = pd.to_datetime(row['entry_time'])
        exit_t = pd.to_datetime(row['exit_time']) if pd.notnull(row['exit_time']) else None
        
        entry_wib = entry_t + pd.Timedelta(hours=7)
        exit_wib = exit_t + pd.Timedelta(hours=7) if exit_t else None
        
        # Cari lilin entry di df
        c_match = df[df['timestamp'] == entry_t]
        ohlc_str = ""
        if not c_match.empty:
            c = c_match.iloc[0]
            ohlc_str = f"Open={c['open']:.2f} | High={c['high']:.2f} | Low={c['low']:.2f} | Close={c['close']:.2f}"
            
        st_icon = "🟢 PROFIT (TP HIT)" if row['net_pnl'] > 0 else "🔴 LOSS (SL HIT)"
        
        print(f"📌 TRADE #{idx + 1}:")
        print(f"   • Waktu Entry (WIB) : {entry_wib.strftime('%Y-%m-%d %H:%M:%S WIB')} ({entry_t.strftime('%Y-%m-%d %H:%M:%S UTC')})")
        if ohlc_str:
            print(f"   • OHLC Lilin Entry  : {ohlc_str}")
        print(f"   • Harga Beli (Entry): ${row['entry_price']:,.2f}")
        print(f"   • Harga Jual (Exit) : ${row['exit_price']:,.2f}")
        print(f"   • Alasan Exit       : {row['exit_reason']}")
        print(f"   • Hasil Akhir       : {st_icon}")
        print(f"   • Realized Net PnL  : {'+' if row['net_pnl']>=0 else ''}${row['net_pnl']:,.2f}")
        if exit_wib:
            print(f"   • Waktu Selesai (WIB): {exit_wib.strftime('%Y-%m-%d %H:%M:%S WIB')}")
        print("-" * 90)

def main():
    for s in ['BTCUSDT', 'ETHUSDT', 'SOLUSDT']:
        inspect_last_trades(s)

if __name__ == "__main__":
    main()
