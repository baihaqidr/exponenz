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
        # Fallback to fast API
        from src.data_fetcher import fetch_binance_futures_klines
        try:
            return fetch_binance_futures_klines(symbol, "5m", total_candles=3000)
        except Exception:
            return None

    full_df = pd.concat(dfs, ignore_index=True)
    full_df.drop_duplicates(subset=['timestamp'], inplace=True)
    full_df.sort_values('timestamp', inplace=True)
    full_df.reset_index(drop=True, inplace=True)
    return full_df

def backtest_5m_1year(symbol="BTCUSDT", sl_pct=0.012):
    df = fetch_1year_5m_data(symbol)
    if df is None or len(df) < 1000:
        print(f"❌ {symbol:<10}: Data tidak cukup")
        return None

    df['ema_7'] = calculate_ema(df['close'], 7)
    df['rsi'] = calculate_rsi(df['close'], 14)
    df['bb_mid'] = calculate_sma(df['close'], 20)
    df['bb_std'] = df['close'].rolling(20).std()
    df['bb_up'] = df['bb_mid'] + 2.0 * df['bb_std']
    
    armed = False
    enter_long = [0] * len(df)
    
    for i in range(1, len(df)):
        rsi_val = df.loc[i, 'rsi']
        close_val = df.loc[i, 'close']
        ema7_val = df.loc[i, 'ema_7']
        prev_close = df.loc[i-1, 'close']
        prev_ema7 = df.loc[i-1, 'ema_7']
        
        # 1. State Armed: RSI < 30
        if rsi_val < 30:
            armed = True
            
        # 2. State Execute: First Candle Close > EMA 7
        if armed and (prev_close <= prev_ema7) and (close_val > ema7_val):
            enter_long[i] = 1
            armed = False
            
    df['enter_long'] = enter_long
    # TP: Upper Bollinger Band atau RSI >= 65
    df['exit_long'] = np.where((df['close'] >= df['bb_up']) | (df['rsi'] >= 65), 1, 0)
    df['sl_price'] = df['close'] * (1.0 - sl_pct)
    
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
    st = "🟢" if m['net_profit']>=0 else "🔴"
    print(f"• {symbol:<10} (5m | {t_start} s/d {t_end} | {total_days:.0f} Hari | {len(df):,} Lilin):")
    print(f"  ↳ Net PnL: {pnl_str:>12} ({m['net_profit_pct']:>+6.2f}%) {st} | WR: {m['win_rate']:>5.1f}% ({m['win_count']}W/{m['loss_count']}L) | PF: {m['profit_factor']:>4.2f} | MaxDD: {m['max_drawdown_pct']:>4.2f}% | Trades: {m['total_trades']}")
    
    if not t.empty and 'entry_time' in t.columns:
        t['month'] = pd.to_datetime(t['entry_time']).dt.strftime('%Y-%m')
        mb = t.groupby('month').agg(total=('net_pnl','count'), win=('net_pnl', lambda x: (x>0).sum()), pnl=('net_pnl','sum')).reset_index()
        mb['wr'] = (mb['win']/mb['total'])*100
        profitable_months = (mb['pnl'] > 0).sum()
        print(f"  ↳ Konsistensi Bulanan: {profitable_months}/{len(mb)} Bulan Hijau")
    print("-" * 95)
    return m

def main():
    symbols = ['BTCUSDT', 'SOLUSDT', 'ETHUSDT', 'NEARUSDT', 'ENAUSDT', 'SAGAUSDT', 'SYNUSDT', 'ONEUSDT', 'DASHUSDT', 'ZECUSDT']
    print("="*95)
    print("🚀 MENGUJI 1 TAHUN PENUH STATE MACHINE DI TIMEFRAME 5-MENIT (~105,000 LILIN)")
    print("   Setup: RSI < 30 -> First Cross Up EMA 7 -> TP Upper BB / RSI 65 | SL -1.2%")
    print("="*95)
    
    for s in symbols:
        backtest_5m_1year(s, sl_pct=0.012)

if __name__ == "__main__":
    main()
