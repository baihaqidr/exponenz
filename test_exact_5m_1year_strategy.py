import sys
import os
import io
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

from src.indicators import calculate_rsi, calculate_ema

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

def fetch_1year_5m_data(symbol="ETHUSDT"):
    now = datetime.now()
    urls = []
    for m in range(13, 0, -1):
        dt = now - timedelta(days=m * 30.5)
        ym = dt.strftime("%Y-%m")
        url = f"{BINANCE_FUTURES_MONTHLY_URL}/{symbol}/5m/{symbol}-5m-{ym}.zip"
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

def backtest_5m_exact(symbol="SOLUSDT"):
    df = fetch_1year_5m_data(symbol)
    if df is None or len(df) < 5000:
        print(f"❌ Gagal mengambil data 5m untuk {symbol}")
        return None

    df['ema_7'] = calculate_ema(df['close'], 7)
    df['rsi'] = calculate_rsi(df['close'], 14)

    closes = df['close'].values
    highs = df['high'].values
    lows = df['low'].values
    rsis = df['rsi'].values
    ema7s = df['ema_7'].values
    timestamps = df['timestamp'].values
    n = len(df)

    armed = False
    enter_long = np.zeros(n, dtype=int)
    sl_arr = np.zeros(n, dtype=float)
    tp_arr = np.zeros(n, dtype=float)

    for i in range(1, n):
        rsi = rsis[i]
        c = closes[i]
        low_c = lows[i]
        ema7 = ema7s[i]
        prev_c = closes[i-1]
        prev_ema7 = ema7s[i-1]

        if np.isnan(rsi) or np.isnan(ema7):
            continue

        if rsi < 30.0:
            armed = True

        # First candle cross above EMA 7
        if armed and prev_c <= prev_ema7 and c > ema7:
            enter_long[i] = 1
            risk = c - low_c
            sl_arr[i] = low_c
            tp_arr[i] = c + (2.0 * risk) # RR 1:2
            armed = False

    # Fast Realistic Simulation
    capital = 5000.0
    init_cap = 5000.0
    fee_rate = 0.0005 # 0.05% taker fee
    slippage = 0.0002 # 0.02% slippage
    lev = 3.0
    pos_pct = 0.25 # 25% margin

    in_pos = False
    entry_p = 0.0
    curr_sl = 0.0
    curr_tp = 0.0
    qty = 0.0
    trades_list = []
    peak = capital
    max_dd = 0.0

    for i in range(n):
        c = closes[i]
        h = highs[i]
        l = lows[i]
        t = timestamps[i]

        if in_pos:
            exit_p = 0.0
            reason = ""
            if l <= curr_sl:
                exit_p = curr_sl * (1.0 - slippage)
                reason = "SL Hit"
            elif h >= curr_tp:
                exit_p = curr_tp * (1.0 - slippage)
                reason = "TP Hit"

            if exit_p > 0:
                fee = (exit_p * qty) * fee_rate
                net = (exit_p - entry_p) * qty - fee
                capital += net
                trades_list.append({
                    "timestamp": t,
                    "net_pnl": net,
                    "reason": reason,
                    "win": 1 if net > 0 else 0
                })
                in_pos = False
                if capital > peak:
                    peak = capital
                dd = (peak - capital) / peak * 100.0
                if dd > max_dd:
                    max_dd = dd
                if capital <= 10:
                    break

        if not in_pos and capital > 10 and enter_long[i] == 1:
            entry_p = c * (1.0 + slippage)
            curr_sl = sl_arr[i]
            curr_tp = tp_arr[i]
            if curr_sl < entry_p:
                notional = capital * pos_pct * lev
                qty = notional / entry_p
                entry_fee = notional * fee_rate
                capital -= entry_fee
                in_pos = True

    total_trades = len(trades_list)
    wins = sum(1 for t in trades_list if t['win'] == 1)
    wr = (wins / total_trades * 100.0) if total_trades > 0 else 0.0
    net_pnl = capital - init_cap
    pnl_pct = (net_pnl / init_cap) * 100.0

    t_start = pd.to_datetime(df['timestamp'].iloc[0]).strftime('%d-%b-%Y')
    t_end = pd.to_datetime(df['timestamp'].iloc[-1]).strftime('%d-%b-%Y')

    pnl_str = f"{'+' if net_pnl>=0 else ''}${net_pnl:,.2f}"
    st = "🟢 PROFIT" if net_pnl >= 0 else "🔴 LOSS"

    print("="*90)
    print(f"📊 HASIL 1 TAHUN PENUH TIMEFRAME 5-MENIT (5m) : {symbol}")
    print(f"📅 Rentang: {t_start} s/d {t_end} ({len(df):,} Lilin 5m)")
    print(f"⚙️ Aturan: RSI < 30 (State Armed) -> 1st Cross EMA 7 -> SL Low Lilin, TP 2x Risk")
    print("="*90)
    print(f"  • Modal Awal             : ${init_cap:,.2f} USDT (Leverage 3x)")
    print(f"  • Modal Akhir            : ${capital:,.2f} USDT")
    print(f"  • Total Net PnL ($)      : {pnl_str} ({pnl_pct:>+6.2f}%) [{st}]")
    print(f"  • Total Transaksi        : {total_trades:,} Trades (Win: {wins}, Loss: {total_trades - wins})")
    print(f"  • Win Rate               : {wr:.1f}%")
    print(f"  • Maximum Drawdown       : -{max_dd:.2f}%")
    print("-" * 90)

    # Rincian Bulanan
    if trades_list:
        tdf = pd.DataFrame(trades_list)
        tdf['month'] = pd.to_datetime(tdf['timestamp']).dt.strftime('%Y-%m')
        mb = tdf.groupby('month').agg(
            total=('net_pnl', 'count'),
            win=('win', 'sum'),
            pnl=('net_pnl', 'sum')
        ).reset_index()
        mb['wr'] = (mb['win'] / mb['total']) * 100
        print(f"📅 Rincian Performa Bulan Per Bulan (5m):")
        print(f"{'Bulan':<10} | {'Trades':<8} | {'Win Rate':<10} | {'Net PnL ($)':<16} | {'Status'}")
        print("-" * 65)
        for _, row in mb.iterrows():
            m_pnl = f"{'+' if row['pnl'] >= 0 else ''}${row['pnl']:,.2f}"
            st_m = "🟢 PROFIT" if row['pnl'] >= 0 else "🔴 LOSS"
            print(f"{row['month']:<10} | {int(row['total']):<8} | {row['wr']:>6.1f}%   | {m_pnl:>14}  | {st_m}")
        print("=" * 90)

def main():
    for s in ['SOLUSDT', 'BTCUSDT', 'ETHUSDT', 'NEARUSDT']:
        backtest_5m_exact(s)

if __name__ == "__main__":
    main()
