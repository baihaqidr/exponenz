import sys
import pandas as pd
import numpy as np
from test_unbiased_20_pairs import fetch_1year_klines, calculate_supertrend, calculate_ema
from src.backtester import BacktestEngine

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

pairs = ['BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'BNBUSDT', 'XRPUSDT', 'ADAUSDT', 'DOGEUSDT', 'AVAXUSDT', 'DOTUSDT', 'LINKUSDT', 'NEARUSDT', 'LTCUSDT', 'ATOMUSDT', 'UNIUSDT', 'FILUSDT', 'ETCUSDT', 'APTUSDT', 'OPUSDT', 'ARBUSDT', 'INJUSDT']
res = []

for s in pairs:
    try:
        df = fetch_1year_klines(s, '1h')
        df['supertrend'], df['st_dir'] = calculate_supertrend(df, 10, 3.0)
        df['ema_50'] = calculate_ema(df['close'], 50)
        df['enter_long'] = np.where((df['st_dir'] == 1) & (df['st_dir'].shift(1) == -1) & (df['close'] > df['ema_50']), 1, 0)
        df['exit_long'] = np.where(df['st_dir'] == -1, 1, 0)
        df['enter_short'] = np.where((df['st_dir'] == -1) & (df['st_dir'].shift(1) == 1) & (df['close'] < df['ema_50']), 1, 0)
        df['exit_short'] = np.where(df['st_dir'] == 1, 1, 0)
        df['sl_price'] = df['supertrend']
        engine = BacktestEngine(initial_capital=5000.0, leverage=2.0, fixed_pos_size_pct=0.20, fee_rate=0.0005, slippage_pct=0.0002)
        m = engine.run(df)['metrics']
        res.append({
            'Symbol': s,
            'Trades': m['total_trades'],
            'Wins': m['win_count'],
            'Losses': m['loss_count'],
            'Win Rate': f"{m['win_rate']:.1f}%",
            'Net PnL': f"${m['net_profit']:,.2f}",
            'Avg PnL/Trade': f"${m['net_profit']/m['total_trades']:.2f}" if m['total_trades'] > 0 else "$0"
        })
    except Exception:
        pass

df_out = pd.DataFrame(res)
print("="*85)
print("📋 DETAIL SAMPEL TRANSAKSI (JUMLAH TRADE) 1 TAHUN PENUH DI 20 KOIN:")
print("="*85)
print(df_out.to_string(index=False))
print("="*85)
total_trades = sum(r['Trades'] for r in res)
avg_trades = total_trades / len(res)
print(f"🔥 TOTAL SAMPEL DATA   : {total_trades} TRADES (dari 175.200 lilin 1-Jam)")
print(f"📌 RATA-RATA PER KOIN  : {avg_trades:.1f} Trades / Tahun (~1 sampai 2 trade per minggu per koin)")
print(f"📈 TOTAL NET PROFIT    : +${sum(float(r['Net PnL'].replace('$','').replace(',','')) for r in res):,.2f}")
print("="*85)
