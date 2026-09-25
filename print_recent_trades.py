import sys
import pandas as pd
from src.data_fetcher import fetch_fast_api_klines
from src.strategies.rsi_first_ema7_crossover import RsiFirstEma7CrossoverStrategy
from src.backtester import BacktestEngine

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

def run_check():
    for s in ['BTCUSDT', 'ETHUSDT', 'SOLUSDT']:
        df = fetch_fast_api_klines(s, '1m', 3000)
        if df is None or len(df) == 0:
            continue
        strat = RsiFirstEma7CrossoverStrategy(rsi_period=14, rsi_oversold=30.0, ema_period=7, rr_multiplier=2.0)
        df_signals = strat.generate_signals(df)
        engine = BacktestEngine(5000.0, 3.0, 0.25, 0.0005, 0.0002)
        res = engine.run(df_signals)
        t = res['trades_df']
        
        last_dt_wib = df['timestamp'].iloc[-1] + pd.Timedelta(hours=7)
        print("="*90)
        print(f"🔥 TRADE TERAKHIR REAL-TIME {s} (DATA S/D {last_dt_wib.strftime('%d-%b-%Y %H:%M:%S WIB')}):")
        print("="*90)
        
        for idx, row in t.tail(3).iterrows():
            en_t = pd.to_datetime(row['entry_time'])
            en_wib = en_t + pd.Timedelta(hours=7)
            ex_t = pd.to_datetime(row['exit_time']) if pd.notnull(row['exit_time']) else None
            ex_wib = ex_t + pd.Timedelta(hours=7) if ex_t else None
            c = df[df['timestamp'] == en_t].iloc[0]
            st_icon = "🟢 PROFIT" if row['net_pnl'] > 0 else ("🟡 BEP" if row['net_pnl'] == 0 else "🔴 LOSS")
            
            print(f"📌 Trade #{idx+1} ({s}):")
            print(f"   • Waktu Entry (WIB) : {en_wib.strftime('%Y-%m-%d %H:%M:%S WIB')} (UTC: {en_t.strftime('%Y-%m-%d %H:%M:%S')})")
            print(f"   • OHLC Lilin Entry  : Open={c['open']} | High={c['high']} | Low={c['low']} | Close={c['close']}")
            print(f"   • Harga Beli (Entry): ${row['entry_price']:,.2f}")
            print(f"   • Harga Jual (Exit) : ${row['exit_price']:,.2f}")
            print(f"   • Alasan Exit       : {row['exit_reason']} ({st_icon})")
            print(f"   • Net PnL           : {row['net_pnl']:,.2f} USDT")
            if ex_wib:
                print(f"   • Waktu Exit (WIB)  : {ex_wib.strftime('%Y-%m-%d %H:%M:%S WIB')}")
            print("-" * 90)

if __name__ == "__main__":
    run_check()
