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

from src.strategies.binance_bband_wilder_rsi import BinanceBbandWilderRsiStrategy
from src.strategies.freqtrade_bband_rsi import FreqtradeBbandRsiStrategy
from src.backtester import BacktestEngine

urllib3.disable_warnings()

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
            print(f"  [OK] Downloaded: {url.split('/')[-1]} ({len(df)} candles)")
            return df[['timestamp', 'open', 'high', 'low', 'close', 'volume']]
    except Exception as e:
        print(f"  [SKIP] {url.split('/')[-1]}: {e}")
    return None

def fetch_1year_15m_eth():
    print("="*65)
    print("🔄 Mengunduh Data Historis 1 Tahun ETHUSDT Timeframe 15-Menit (15m)...")
    print("="*65)
    
    urls = []
    for m in range(13, 0, -1):
        dt = datetime.utcnow() - timedelta(days=m * 30.5)
        ym = dt.strftime("%Y-%m")
        url = f"{BINANCE_FUTURES_MONTHLY_URL}/ETHUSDT/15m/ETHUSDT-15m-{ym}.zip"
        if url not in urls:
            urls.append(url)
            
    with ThreadPoolExecutor(max_workers=8) as executor:
        results = list(executor.map(download_monthly_zip, urls))
        
    dfs = [r for r in results if r is not None]
    
    # Recent days
    try:
        r_recent = requests.get("https://testnet.binancefuture.com/fapi/v1/klines?symbol=ETHUSDT&interval=15m&limit=1500", verify=False, timeout=5)
        if r_recent.status_code == 200:
            data = r_recent.json()
            if isinstance(data, list) and len(data) > 0:
                cols = ['open_time', 'open', 'high', 'low', 'close', 'volume', 'close_time', 'quote_volume', 'count', 'taker_buy_volume', 'taker_buy_quote_volume', 'ignore']
                df_rec = pd.DataFrame(data, columns=cols[:len(data[0])])
                df_rec['timestamp'] = pd.to_datetime(df_rec['open_time'], unit='ms')
                for c in ['open', 'high', 'low', 'close', 'volume']:
                    df_rec[c] = df_rec[c].astype(float)
                dfs.append(df_rec[['timestamp', 'open', 'high', 'low', 'close', 'volume']])
    except Exception:
        pass

    if not dfs:
        print("❌ Gagal mengunduh data.")
        return None

    full_df = pd.concat(dfs, ignore_index=True)
    full_df.drop_duplicates(subset=['timestamp'], inplace=True)
    full_df.sort_values('timestamp', inplace=True)
    full_df.reset_index(drop=True, inplace=True)
    
    print(f"\n✅ TOTAL CANDLES 15-MENIT TERKUMPUL: {len(full_df):,} Lilin")
    print(f"📅 Rentang Waktu: {full_df['timestamp'].iloc[0].strftime('%Y-%m-%d %H:%M')} s/d {full_df['timestamp'].iloc[-1].strftime('%Y-%m-%d %H:%M')}")
    return full_df

def run_eth_15m_backtest():
    df = fetch_1year_15m_eth()
    if df is None or len(df) < 500:
        print("Data tidak mencukupi.")
        return

    print("\n" + "="*65)
    print("📊 MENGHITUNG STRATEGI: Binance Pro Wilder BBand + RSI (15-Menit)")
    print("="*65)
    
    strat_wilder = BinanceBbandWilderRsiStrategy(bb_length=20, bb_std=2.0, rsi_period=14)
    t0 = time.time()
    df_wilder = strat_wilder.generate_signals(df)
    t1 = time.time()
    print(f"⚡ Kalkulasi Indikator Selesai dalam {t1 - t0:.2f} detik.")
    
    # Engine Settings
    initial_cap = 5000.0
    engine = BacktestEngine(
        initial_capital=initial_cap,
        leverage=3.0,
        fixed_pos_size_pct=0.20, # 20% margin ($1,000 margin = $3,000 notional)
        fee_rate=0.0005, # 0.05% Taker fee
        slippage_pct=0.0002
    )
    
    res = engine.run(df_wilder)
    metrics = res.get("metrics", {})
    trades_df = res.get("trades_df", pd.DataFrame())
    
    total_trades = metrics.get("total_trades", len(trades_df))
    win_rate = metrics.get("win_rate", 0.0)
    profit_factor = metrics.get("profit_factor", 0.0)
    max_dd = metrics.get("max_drawdown_pct", 0.0)
    total_net_pnl = metrics.get("net_profit", 0.0)
    roi_pct = metrics.get("net_profit_pct", 0.0)
    final_cap = metrics.get("final_capital", initial_cap + total_net_pnl)
    win_count = metrics.get("win_count", 0)
    loss_count = metrics.get("loss_count", 0)
    
    print("\n" + "🏆 HASIL BACKTEST 1 TAHUN ETHUSDT (TIMEFRAME 15-MENIT) 🏆")
    print("-" * 65)
    print(f"  • Modal Awal             : ${initial_cap:,.2f} USDT (Leverage 3x)")
    print(f"  • Modal Akhir            : ${final_cap:,.2f} USDT")
    print(f"  • Total Net PnL ($)      : {'+' if total_net_pnl >= 0 else ''}${total_net_pnl:,.2f} USDT")
    print(f"  • Total Return (ROI %)   : {'+' if roi_pct >= 0 else ''}{roi_pct:.2f}%")
    print(f"  • Total Trades           : {total_trades:,} Transaksi (Win: {win_count}, Loss: {loss_count})")
    print(f"  • Win Rate               : {win_rate:.1f}%")
    print(f"  • Profit Factor          : {profit_factor:.2f}")
    print(f"  • Maximum Drawdown       : -{max_dd:.2f}%")
    print("-" * 65)
    
    # Monthly Breakdown
    if not trades_df.empty and 'entry_time' in trades_df.columns:
        trades_df['month'] = pd.to_datetime(trades_df['entry_time']).dt.strftime('%Y-%m')
        
        monthly = trades_df.groupby('month').agg(
            total_trades=('net_pnl', 'count'),
            win_trades=('net_pnl', lambda x: (x > 0).sum()),
            net_pnl=('net_pnl', 'sum')
        ).reset_index()
        monthly['win_rate'] = (monthly['win_trades'] / monthly['total_trades']) * 100
        
        print("\n📅 BREAKDOWN PERFORMA BULAN PER BULAN (TIMEFRAME 15-MENIT):")
        print(f"{'Bulan':<10} | {'Total Trades':<14} | {'Win Rate':<10} | {'Net PnL ($)':<16} | {'Status'}")
        print("-" * 68)
        for _, row in monthly.iterrows():
            pnl_str = f"{'+' if row['net_pnl'] >= 0 else ''}${row['net_pnl']:,.2f}"
            status = "🟢 PROFIT" if row['net_pnl'] >= 0 else "🔴 LOSS"
            print(f"{row['month']:<10} | {int(row['total_trades']):<14} | {row['win_rate']:>6.1f}%   | {pnl_str:>14}  | {status}")
        print("-" * 68)

if __name__ == "__main__":
    run_eth_15m_backtest()
