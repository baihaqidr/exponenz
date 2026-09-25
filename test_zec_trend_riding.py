import os
import sys
import requests
import urllib3
import pandas as pd
import numpy as np
from src.indicators import calculate_supertrend, calculate_ema, calculate_atr
from src.backtester import BacktestEngine

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

urllib3.disable_warnings()

def fetch_1year_klines(symbol: str, interval: str = "1h"):
    url = f"https://data-api.binance.vision/api/v3/klines?symbol={symbol}&interval={interval}&limit=1000"
    r = requests.get(url, verify=False).json()
    cols = ['open_time', 'open', 'high', 'low', 'close', 'volume', 'close_time', 'quote_volume', 'count', 'taker_buy_volume', 'taker_buy_quote_volume', 'ignore']
    df = pd.DataFrame(r, columns=cols[:len(r[0])])
    df['timestamp'] = pd.to_datetime(df['open_time'], unit='ms')
    for c in ['open', 'high', 'low', 'close', 'volume']:
        df[c] = df[c].astype(float)
    return df

def test_zec_trend():
    print("="*75)
    print("🚀 MENGUJI STRATEGI TREND RIDER PADA KOIN BULLISH ZECUSDT (1 TAHUN)...")
    print("="*75)

    # Uji di 1h dan 15m
    for tf in ["1h", "15m"]:
        df = fetch_1year_klines("ZECUSDT", tf)
        
        # 1. Supertrend Trend Rider (ATR 10, Multiplier 3.0) + EMA 50
        df['supertrend'], df['st_dir'] = calculate_supertrend(df, period=10, multiplier=3.0)
        df['ema_50'] = calculate_ema(df['close'], 50)

        df['ema_200'] = calculate_ema(df['close'], 200)
        
        # Sinyal Trend Rider:
        # Masuk LONG saat Supertrend berbalik HIJAU (st_dir == 1) & Harga > EMA 50
        # Keluar LONG saat Supertrend berbalik MERAH (st_dir == -1) atau Trailing Stop
        df['enter_long'] = np.where((df['st_dir'] == 1) & (df['st_dir'].shift(1) == -1) & (df['close'] > df['ema_50']), 1, 0)
        df['exit_long'] = np.where((df['st_dir'] == -1), 1, 0)
        df['enter_short'] = np.where((df['st_dir'] == -1) & (df['st_dir'].shift(1) == 1) & (df['close'] < df['ema_50']), 1, 0)
        df['exit_short'] = np.where((df['st_dir'] == 1), 1, 0)
        
        df['sl_price'] = df['supertrend'] # Trailing stop otomatis mengikuti garis Supertrend
        
        engine = BacktestEngine(
            initial_capital=5000.0,
            leverage=2.0,
            fixed_pos_size_pct=0.30, # 30% margin allocation
            fee_rate=0.0005,
            slippage_pct=0.0002
        )
        
        res = engine.run(df)
        m = res['metrics']
        t = res['trades_df']
        
        print(f"\n🏆 HASIL TREND RIDER SUPERTREND PADA ZECUSDT ({tf.upper()}):")
        print("-" * 65)
        print(f"  • Modal Awal             : $5,000.00 USDT (Leverage 2x)")
        print(f"  • Modal Akhir            : ${m['final_capital']:,.2f} USDT")
        print(f"  • Total Net PnL ($)      : {'+' if m['net_profit']>=0 else ''}${m['net_profit']:,.2f} USDT")
        print(f"  • Total Return (ROI %)   : {'+' if m['net_profit_pct']>=0 else ''}{m['net_profit_pct']:.2f}%")
        print(f"  • Total Trades           : {m['total_trades']} Transaksi (Win: {m['win_count']}, Loss: {m['loss_count']})")
        print(f"  • Win Rate               : {m['win_rate']:.1f}%")
        print(f"  • Profit Factor          : {m['profit_factor']:.2f}")
        print(f"  • Maximum Drawdown       : -{m['max_drawdown_pct']:.2f}%")
        print("-" * 65)
        
        if not t.empty and 'entry_time' in t.columns:
            t['month'] = pd.to_datetime(t['entry_time']).dt.strftime('%Y-%m')
            mb = t.groupby('month').agg(total=('net_pnl','count'), win=('net_pnl', lambda x: (x>0).sum()), pnl=('net_pnl','sum')).reset_index()
            mb['wr'] = (mb['win']/mb['total'])*100
            print(f"📅 Rincian Bulanan ZECUSDT ({tf}):")
            for _, r in mb.iterrows():
                print(f"   {r['month']}: {int(r['total']):>2} trades | WR {r['wr']:>5.1f}% | PnL: {'+' if r['pnl']>=0 else ''}${r['pnl']:,.2f}")

if __name__ == "__main__":
    test_zec_trend()
