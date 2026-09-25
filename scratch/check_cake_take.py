import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from src.data_fetcher import fetch_fast_api_klines
from src.strategy_registry import get_strategy_instance
from src.backtester import BacktestEngine
import pandas as pd

def check_symbol_trades(symbol):
    print(f"\n=======================================================", flush=True)
    print(f"=== CHECK TRADE UNTUK: {symbol} (5m) ===", flush=True)
    print(f"=======================================================", flush=True)
    
    df = fetch_fast_api_klines(symbol, '5m', total_candles=1500)
    if df is None or len(df) == 0:
        print(f"[ERROR] Pair {symbol} tidak ditemukan atau tidak aktif di Binance Futures.", flush=True)
        return

    print(f"[OK] Data {symbol} berhasil diambil: {len(df)} candles ({df['timestamp'].min()} s/d {df['timestamp'].max()})", flush=True)

    for strat_id in ['freqtrade_bband_rsi', 'binance_bband_wilder_rsi']:
        strategy = get_strategy_instance(strat_id)
        df_sig = strategy.generate_signals(df)
        
        engine = BacktestEngine(initial_capital=1000.0, leverage=2.0, risk_per_trade_pct=0.02, fixed_pos_size_pct=0.5)
        res = engine.run(df_sig)
        trades_df = res["trades_df"]
        
        print(f"\n--- Strategi: {strategy.name} ---", flush=True)
        print(f"Total Trades: {len(trades_df)}", flush=True)
        
        if not trades_df.empty:
            trades_df['entry_wib'] = pd.to_datetime(trades_df['entry_time']) + pd.Timedelta(hours=7)
            trades_df['exit_wib'] = pd.to_datetime(trades_df['exit_time']) + pd.Timedelta(hours=7)
            last_tr = trades_df.iloc[-1]
            pnl = float(last_tr['net_pnl'])
            pnl_str = f"+${pnl:.2f}" if pnl > 0 else f"-${abs(pnl):.2f}"
            print(f"  --> TRADE TERAKHIR {symbol}:", flush=True)
            print(f"     * Entry : {last_tr['entry_wib'].strftime('%Y-%m-%d %H:%M')} WIB @ ${last_tr['entry_price']:.4f}", flush=True)
            print(f"     * Exit  : {last_tr['exit_wib'].strftime('%Y-%m-%d %H:%M')} WIB @ ${last_tr['exit_price']:.4f}", flush=True)
            print(f"     * Alasan: {last_tr['exit_reason']}", flush=True)
            print(f"     * Net PnL: {pnl_str}", flush=True)
        else:
            print(f"  Belum ada sinyal trade yang terpicu di {symbol} dalam rentang ini.", flush=True)

# Test CAKEUSDT, TAOUSDT, and check why TAKEUSDT is not in list
for sym in ['CAKEUSDT', 'TAOUSDT', 'TAKEUSDT']:
    check_symbol_trades(sym)
