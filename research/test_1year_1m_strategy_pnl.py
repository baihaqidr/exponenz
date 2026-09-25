import os
import io
import sys
import time
import zipfile
import requests
import urllib3
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

urllib3.disable_warnings()

from src.strategies.rsi_first_ema7_crossover import RsiFirstEma7CrossoverStrategy
from src.backtester import BacktestEngine

BINANCE_FUTURES_MONTHLY_URL = "https://data.binance.vision/data/futures/um/monthly/klines"

def download_monthly_zip(url: str):
    try:
        r = requests.get(url, verify=False, timeout=10)
        if r.status_code == 200:
            z = zipfile.ZipFile(io.BytesIO(r.content))
            csv_file = z.namelist()[0]
            df = pd.read_csv(z.open(csv_file))
            if 'open_time' not in df.columns:
                cols = ['open_time', 'open', 'high', 'low', 'close', 'volume', 'close_time', 'quote_volume', 'count', 'taker_buy_volume', 'taker_buy_quote_volume', 'ignore']
                df.columns = cols[:len(df.columns)]
            df['timestamp'] = pd.to_datetime(df['open_time'], unit='ms')
            for c in ['open', 'high', 'low', 'close', 'volume']:
                if c in df.columns:
                    df[c] = df[c].astype(float)
            return df[['timestamp', 'open', 'high', 'low', 'close', 'volume']]
    except Exception:
        pass
    return None

def fetch_1year_1m_data(symbol="ETHUSDT"):
    now = datetime.now()
    urls = []
    for m in range(13, 0, -1):
        dt = now - timedelta(days=m * 30.5)
        ym = dt.strftime("%Y-%m")
        url = f"{BINANCE_FUTURES_MONTHLY_URL}/{symbol}/1m/{symbol}-1m-{ym}.zip"
        if url not in urls:
            urls.append(url)
            
    with ThreadPoolExecutor(max_workers=8) as executor:
        results = list(executor.map(download_monthly_zip, urls))
        
    dfs = [r for r in results if r is not None]
    if not dfs:
        return None

    full_df = pd.concat(dfs, ignore_index=True)
    full_df.drop_duplicates(subset=['timestamp'], inplace=True)
    full_df.sort_values('timestamp', inplace=True)
    full_df.reset_index(drop=True, inplace=True)
    return full_df

def run_1year_1m_test(symbol="ETHUSDT"):
    print(f"\n🔄 Mengunduh & memproses 1 tahun 1m untuk {symbol}...")
    t0 = time.time()
    df = fetch_1year_1m_data(symbol)
    if df is None or len(df) < 5000:
        print(f"❌ {symbol}: Data 1m tidak mencukupi.")
        return None
    
    t_dl = time.time() - t0
    print(f"✅ Data {symbol} siap ({len(df):,} lilin 1m dalam {t_dl:.1f}s)")
    
    strategy = RsiFirstEma7CrossoverStrategy(rsi_period=14, rsi_oversold=30.0, ema_period=7, rr_multiplier=2.0)
    df_signals = strategy.generate_signals(df)
    
    initial_cap = 5000.0
    engine = BacktestEngine(
        initial_capital=initial_cap,
        leverage=3.0,
        fixed_pos_size_pct=0.25, # 25% margin allocation per trade
        fee_rate=0.0005,         # 0.05% taker fee
        slippage_pct=0.0002      # 0.02% slippage
    )
    
    res = engine.run(df_signals)
    m = res['metrics']
    t = res['trades_df']
    
    t_start = df['timestamp'].iloc[0].strftime('%d-%b-%Y')
    t_end = df['timestamp'].iloc[-1].strftime('%d-%b-%Y')
    total_days = (df['timestamp'].iloc[-1] - df['timestamp'].iloc[0]).total_seconds() / 86400
    
    pnl_str = f"{'+' if m['net_profit']>=0 else ''}${m['net_profit']:,.2f}"
    st = "🟢 PROFIT" if m['net_profit'] >= 0 else "🔴 LOSS"
    
    print("\n" + "="*85)
    print(f"🏆 HASIL 1 TAHUN PENUH TIMEFRAME 1-MENIT (1m) : {symbol}")
    print(f"📅 Rentang: {t_start} s/d {t_end} ({total_days:.0f} Hari | {len(df):,} Lilin 1m)")
    print("="*85)
    print(f"  • Modal Awal             : ${initial_cap:,.2f} USDT (Leverage 3x)")
    print(f"  • Modal Akhir            : ${m['final_capital']:,.2f} USDT")
    print(f"  • Total Net PnL ($)      : {pnl_str} USDT ({m['net_profit_pct']:>+6.2f}%) [{st}]")
    print(f"  • Total Transaksi        : {m['total_trades']:,} Trades (Win: {m['win_count']}, Loss: {m['loss_count']})")
    print(f"  • Win Rate               : {m['win_rate']:.1f}%")
    print(f"  • Profit Factor          : {m['profit_factor']:.2f}")
    print(f"  • Maximum Drawdown       : -{m['max_drawdown_pct']:.2f}%")
    print("-" * 85)
    
    if not t.empty and 'entry_time' in t.columns:
        t['month'] = pd.to_datetime(t['entry_time']).dt.strftime('%Y-%m')
        mb = t.groupby('month').agg(
            total=('net_pnl', 'count'),
            win=('net_pnl', lambda x: (x > 0).sum()),
            pnl=('net_pnl', 'sum')
        ).reset_index()
        mb['wr'] = (mb['win'] / mb['total']) * 100
        
        print(f"📅 Rincian Performa Bulan Per Bulan (1-Menit):")
        print(f"{'Bulan':<10} | {'Trades':<8} | {'Win Rate':<10} | {'Net PnL ($)':<16} | {'Status'}")
        print("-" * 65)
        for _, row in mb.iterrows():
            m_pnl = f"{'+' if row['pnl'] >= 0 else ''}${row['pnl']:,.2f}"
            st_m = "🟢 PROFIT" if row['pnl'] >= 0 else "🔴 LOSS"
            print(f"{row['month']:<10} | {int(row['total']):<8} | {row['wr']:>6.1f}%   | {m_pnl:>14}  | {st_m}")
        print("=" * 85)
    return m

def main():
    print("="*95)
    print("🚀 MENGHITUNG NET PNL 1 TAHUN PENUH DI TIMEFRAME 1-MENIT (1m)")
    print("   Strategi: RSI Oversold (<30) -> First Candle Cross EMA 7 -> SL Low Lilin, TP 2x Risk")
    print("="*95)
    
    symbols = ['BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'NEARUSDT', 'ENAUSDT']
    for s in symbols:
        run_1year_1m_test(s)

if __name__ == "__main__":
    main()
