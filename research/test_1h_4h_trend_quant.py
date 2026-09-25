import os
import sys
import requests
import urllib3
import pandas as pd
import numpy as np
from src.indicators import calculate_rsi, calculate_sma, calculate_ema, calculate_atr
from src.backtester import BacktestEngine

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

urllib3.disable_warnings()

def fetch_1year_klines(symbol: str, interval: str):
    url = f"https://data-api.binance.vision/api/v3/klines?symbol={symbol}&interval={interval}&limit=1000"
    r = requests.get(url, verify=False).json()
    cols = ['open_time', 'open', 'high', 'low', 'close', 'volume', 'close_time', 'quote_volume', 'count', 'taker_buy_volume', 'taker_buy_quote_volume', 'ignore']
    df = pd.DataFrame(r, columns=cols[:len(r[0])])
    df['timestamp'] = pd.to_datetime(df['open_time'], unit='ms')
    for c in ['open', 'high', 'low', 'close', 'volume']:
        df[c] = df[c].astype(float)
    return df

def run_higher_tf_quant(symbol="ETHUSDT", interval="1h"):
    df = fetch_1year_klines(symbol, interval)
    
    # Indikator Klasik Quant (Andreas Clenow & Freqtrade Trend Master)
    df['ema_20'] = calculate_ema(df['close'], 20)
    df['ema_50'] = calculate_ema(df['close'], 50)
    df['ema_200'] = calculate_ema(df['close'], 200)
    df['atr'] = calculate_atr(df, 14)
    df['rsi'] = calculate_rsi(df['close'], 14)
    
    # Model 1: EMA Ribbon Trend Pullback (1h)
    # Long: EMA 20 > EMA 50 > EMA 200 & Pullback sentuh EMA 20 & RSI 40-50 & Bullish Candle
    # TP: +5.0%, SL: -2.0% (RRR 1 : 2.5)
    long_cond = (df['ema_20'] > df['ema_50']) & (df['ema_50'] > df['ema_200']) & (df['low'] <= df['ema_20']) & (df['rsi'] < 52) & (df['close'] > df['open'])
    short_cond = (df['ema_20'] < df['ema_50']) & (df['ema_50'] < df['ema_200']) & (df['high'] >= df['ema_20']) & (df['rsi'] > 48) & (df['close'] < df['open'])
    
    df['enter_long'] = np.where(long_cond, 1, 0)
    df['enter_short'] = np.where(short_cond, 1, 0)
    df['tp_price'] = np.where(df['enter_long'] == 1, df['close'] * 1.050, np.where(df['enter_short'] == 1, df['close'] * 0.950, np.nan))
    df['sl_price'] = np.where(df['enter_long'] == 1, df['close'] * 0.980, np.where(df['enter_short'] == 1, df['close'] * 1.020, np.nan))
    
    engine = BacktestEngine(initial_capital=5000.0, leverage=3.0, fixed_pos_size_pct=0.25, fee_rate=0.0005, slippage_pct=0.0002)
    res = engine.run(df)
    m = res['metrics']
    t = res['trades_df']
    
    print(f"\n🚀 HASIL QUANT STRATEGY ({symbol} - Timeframe {interval.upper()}):")
    print(f"   • Total Net PnL   : {'+' if m['net_profit']>=0 else ''}${m['net_profit']:,.2f} USDT ({m['net_profit_pct']:+.2f}% ROI)")
    print(f"   • Win Rate        : {m['win_rate']:.1f}% ({m['win_count']} Win / {m['loss_count']} Loss)")
    print(f"   • Total Trades    : {m['total_trades']} Transaksi")
    print(f"   • Profit Factor   : {m['profit_factor']:.2f}")
    print(f"   • Max Drawdown    : -{m['max_drawdown_pct']:.2f}%")
    
    if not t.empty and 'entry_time' in t.columns:
        t['month'] = pd.to_datetime(t['entry_time']).dt.strftime('%Y-%m')
        mb = t.groupby('month').agg(total=('net_pnl','count'), win=('net_pnl', lambda x: (x>0).sum()), pnl=('net_pnl','sum')).reset_index()
        mb['wr'] = (mb['win']/mb['total'])*100
        print(f"\n📅 Rincian Bulanan {symbol} ({interval}):")
        for _, r in mb.iterrows():
            print(f"   {r['month']}: {int(r['total'])} trades | WR {r['wr']:>5.1f}% | PnL: {'+' if r['pnl']>=0 else ''}${r['pnl']:,.2f}")

if __name__ == "__main__":
    run_higher_tf_quant("ETHUSDT", "1h")
    run_higher_tf_quant("BTCUSDT", "1h")
    run_higher_tf_quant("SOLUSDT", "1h")
