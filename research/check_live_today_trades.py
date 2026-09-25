import sys
import pandas as pd
from src.data_fetcher import fetch_fast_api_klines
from src.strategies.rsi_first_ema7_crossover import RsiFirstEma7CrossoverStrategy
from src.backtester import BacktestEngine

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

def check_recent(symbol):
    df = fetch_fast_api_klines(symbol, '1m', 3000)
    strat = RsiFirstEma7CrossoverStrategy(rsi_period=14, rsi_oversold=30.0, ema_period=7, rr_multiplier=2.0)
    df_signals = strat.generate_signals(df)
    engine = BacktestEngine(5000.0, 3.0, 0.25, 0.0005, 0.0002)
    res = engine.run(df_signals)
    t = res['trades_df']
    
    last_candle_utc = df['timestamp'].iloc[-1]
    last_candle_wib = last_candle_utc + pd.Timedelta(hours=7)
    
    print("="*90)
    print(f"📊 DATA LIVE BINANCE TERBARU S/D HARI INI (23-Sep-2026) : {symbol}")
    print(f"   Lilin Terakhir: {last_candle_wib.strftime('%Y-%m-%d %H:%M:%S WIB')} ({last_candle_utc.strftime('%Y-%m-%d %H:%M:%S UTC')})")
    print("="*90)
    
    if t.empty:
        print(f"Tidak ada trade setup dalam {len(df)} lilin 1m terakhir.")
        return
        
    for idx, row in t.tail(5).iterrows():
        en_t = pd.to_datetime(row['entry_time'])
        en_wib = en_t + pd.Timedelta(hours=7)
        ex_t = pd.to_datetime(row['exit_time']) if pd.notnull(row['exit_time']) else None
        ex_wib = ex_t + pd.Timedelta(hours=7) if ex_t else None
        
        c = df[df['timestamp'] == en_t].iloc[0]
        st_icon = "🟢 PROFIT (TP HIT)" if row['net_pnl'] > 0 else "🔴 LOSS (SL HIT)"
        
        # Ambil detail target jika ada di dataframe signal
        sig_match = df_signals[df_signals['timestamp'] == en_t]
        tp_target = sig_match['take_profit'].values[0] if not sig_match.empty and 'take_profit' in sig_match.columns else None
        sl_target = sig_match['stop_loss'].values[0] if not sig_match.empty and 'stop_loss' in sig_match.columns else None
        
        print(f"📌 Trade #{idx+1}:")
        print(f"   • Waktu Entry (WIB) : {en_wib.strftime('%Y-%m-%d %H:%M:%S WIB')} ({en_t.strftime('%Y-%m-%d %H:%M:%S UTC')})")
        print(f"   • Lilin Entry OHLC  : Open={c['open']:.4f} | High={c['high']:.4f} | Low={c['low']:.4f} | Close={c['close']:.4f}")
        print(f"   • Harga Beli (Entry): ${row['entry_price']:,.4f}")
        print(f"   • Harga Jual (Exit) : ${row['exit_price']:,.4f}")
        if tp_target and sl_target:
            print(f"   • Setup TP / SL     : TP=${tp_target:,.4f} | SL=${sl_target:,.4f}")
        print(f"   • Alasan Keluar     : {row['exit_reason']} -> {st_icon}")
        print(f"   • Net PnL           : {'+' if row['net_pnl']>=0 else ''}${row['net_pnl']:,.2f}")
        if ex_wib:
            print(f"   • Waktu Selesai     : {ex_wib.strftime('%Y-%m-%d %H:%M:%S WIB')}")
        print("-" * 90)

def main():
    for s in ['BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'ZETAUSDT']:
        check_recent(s)

if __name__ == "__main__":
    main()
