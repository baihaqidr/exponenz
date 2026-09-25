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

from src.indicators import calculate_rsi, calculate_ema, calculate_sma, calculate_atr
from src.backtester import BacktestEngine

BINANCE_FUTURES_MONTHLY_URL = "https://data.binance.vision/data/futures/um/monthly/klines"

def download_monthly_zip(url: str):
    try:
        r = requests.get(url, verify=False, timeout=8)
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

def fetch_1year_data(symbol="ETHUSDT", interval="15m"):
    now = datetime.utcnow()
    urls = []
    for m in range(13, 0, -1):
        dt = now - timedelta(days=m * 30.5)
        ym = dt.strftime("%Y-%m")
        url = f"{BINANCE_FUTURES_MONTHLY_URL}/{symbol}/{interval}/{symbol}-{interval}-{ym}.zip"
        if url not in urls:
            urls.append(url)
            
    with ThreadPoolExecutor(max_workers=8) as executor:
        results = list(executor.map(download_monthly_zip, urls))
        
    dfs = [r for r in results if r is not None]
    if not dfs:
        # Fallback to Binance Vision REST
        url = f"https://data-api.binance.vision/api/v3/klines?symbol={symbol}&interval={interval}&limit=1000"
        try:
            r = requests.get(url, verify=False, timeout=5).json()
            cols = ['open_time', 'open', 'high', 'low', 'close', 'volume', 'close_time', 'quote_volume', 'count', 'taker_buy_volume', 'taker_buy_quote_volume', 'ignore']
            df = pd.DataFrame(r, columns=cols[:len(r[0])])
            df['timestamp'] = pd.to_datetime(df['open_time'], unit='ms')
            for c in ['open', 'high', 'low', 'close', 'volume']:
                df[c] = df[c].astype(float)
            return df[['timestamp', 'open', 'high', 'low', 'close', 'volume']]
        except Exception:
            return None

    full_df = pd.concat(dfs, ignore_index=True)
    full_df.drop_duplicates(subset=['timestamp'], inplace=True)
    full_df.sort_values('timestamp', inplace=True)
    full_df.reset_index(drop=True, inplace=True)
    return full_df

def backtest_1year_state_machine(symbol="ETHUSDT", interval="15m"):
    df = fetch_1year_data(symbol, interval)
    if df is None or len(df) < 500:
        print(f"❌ {symbol:<10}: Data tidak cukup")
        return None

    df['ema_7'] = calculate_ema(df['close'], 7)
    df['rsi'] = calculate_rsi(df['close'], 14)
    df['bb_mid'] = calculate_sma(df['close'], 20)
    df['bb_std'] = df['close'].rolling(20).std()
    df['bb_up'] = df['bb_mid'] + 2.0 * df['bb_std']
    
    # State Machine:
    # 1. Armed saat RSI < 30
    # 2. Execute saat First Candle Close > EMA 7
    # 3. Disarm & lock
    armed = False
    enter_long = [0] * len(df)
    
    for i in range(1, len(df)):
        rsi_val = df.loc[i, 'rsi']
        close_val = df.loc[i, 'close']
        ema7_val = df.loc[i, 'ema_7']
        prev_close = df.loc[i-1, 'close']
        prev_ema7 = df.loc[i-1, 'ema_7']
        
        if rsi_val < 30:
            armed = True
            
        if armed and (prev_close <= prev_ema7) and (close_val > ema7_val):
            enter_long[i] = 1
            armed = False
            
    df['enter_long'] = enter_long
    df['exit_long'] = np.where((df['close'] >= df['bb_up']) | (df['rsi'] >= 65), 1, 0)
    df['sl_price'] = df['close'] * 0.985 # SL -1.5%
    
    engine = BacktestEngine(
        initial_capital=5000.0,
        leverage=3.0,
        fixed_pos_size_pct=0.25,
        fee_rate=0.0005,
        slippage_pct=0.0002
    )
    res = engine.run(df)
    m = res['metrics']
    t = res['trades_df']
    
    t_start = df['timestamp'].iloc[0].strftime('%Y-%m-%d')
    t_end = df['timestamp'].iloc[-1].strftime('%Y-%m-%d')
    total_days = (df['timestamp'].iloc[-1] - df['timestamp'].iloc[0]).total_seconds() / 86400
    
    pnl_str = f"{'+' if m['net_profit']>=0 else ''}${m['net_profit']:,.2f}"
    print(f"{symbol:<10} ({interval} | {t_start} s/d {t_end} | {total_days:.0f} Hari | {len(df):,} Lilin):")
    print(f"   ↳ Net PnL: {pnl_str:>12} ({m['net_profit_pct']:>+6.2f}%) | WR: {m['win_rate']:>5.1f}% ({m['win_count']}W/{m['loss_count']}L) | PF: {m['profit_factor']:>4.2f} | MaxDD: {m['max_drawdown_pct']:>4.2f}% | Trades: {m['total_trades']}")
    
    # Monthly breakdown
    if not t.empty and 'entry_time' in t.columns:
        t['month'] = pd.to_datetime(t['entry_time']).dt.strftime('%Y-%m')
        mb = t.groupby('month').agg(total=('net_pnl','count'), win=('net_pnl', lambda x: (x>0).sum()), pnl=('net_pnl','sum')).reset_index()
        mb['wr'] = (mb['win']/mb['total'])*100
        print("   📅 Rincian Per Bulan:")
        for _, r in mb.iterrows():
            m_pnl = f"{'+' if r['pnl']>=0 else ''}${r['pnl']:,.2f}"
            st = "🟢" if r['pnl']>=0 else "🔴"
            print(f"      {r['month']}: {int(r['total']):>2} trades | WR {r['wr']:>5.1f}% | PnL: {m_pnl:>11} {st}")
    print("-" * 95)
    return m

def main():
    symbols = ['BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'NEARUSDT', 'SAGAUSDT', 'ENAUSDT', 'ONEUSDT', 'SYNUSDT', 'ZECUSDT', 'DASHUSDT']
    print("="*95)
    print("🚀 MENGUJI 1 TAHUN PENUH STATE MACHINE (RSI < 30 -> FIRST CANDLE CROSS UP EMA 7 -> EXIT UPPER BB)")
    print("="*95)
    
    print("\n--- TIMEFRAME 15-MENIT (1 TAHUN PENUH ~ 35,000 LILIN) ---")
    for s in symbols:
        backtest_1year_state_machine(s, "15m")

if __name__ == "__main__":
    main()
