import pandas as pd
from src.backtester import BacktestEngine

df = pd.read_csv('data/BTCUSDT_4h_3000.csv')
df['timestamp'] = pd.to_datetime(df['timestamp'])
data = df.copy()
data['signal'] = 0
data['sl_price'] = None
data['tp_price'] = None

max_wick_ratio = 0.05
rr = 2.0

for i in range(1, len(data)):
    c1_open, c1_close = data.loc[i-1, 'open'], data.loc[i-1, 'close']
    c2_open, c2_close = data.loc[i, 'open'], data.loc[i, 'close']
    c1_high, c1_low = data.loc[i-1, 'high'], data.loc[i-1, 'low']
    c2_high, c2_low = data.loc[i, 'high'], data.loc[i, 'low']
    c2_body = abs(c2_close - c2_open)
    c1_body = abs(c1_close - c1_open)

    # Bullish Engulfing: Full body without wick atas bawah
    if c1_close < c1_open and c2_close > c2_open:
        if c2_open <= c1_close and c2_close >= c1_open and c2_body > 0:
            upper_wick = c2_high - c2_close
            lower_wick = c2_open - c2_low
            if upper_wick <= c2_body * max_wick_ratio and lower_wick <= c2_body * max_wick_ratio:
                entry = c2_close
                sl = c2_low * 0.999
                sl_dist = entry - sl
                tp = entry + (sl_dist * rr)
                data.loc[i, 'signal'] = 1
                data.loc[i, 'sl_price'] = sl
                data.loc[i, 'tp_price'] = tp

    # Bearish Engulfing: Full body without wick atas bawah
    elif c1_close > c1_open and c2_close < c2_open:
        if c2_open >= c1_close and c2_close <= c1_open and c2_body > 0:
            upper_wick = c2_high - c2_open
            lower_wick = c2_close - c2_low
            if upper_wick <= c2_body * max_wick_ratio and lower_wick <= c2_body * max_wick_ratio:
                entry = c2_close
                sl = c2_high * 1.001
                sl_dist = sl - entry
                tp = entry - (sl_dist * rr)
                data.loc[i, 'signal'] = -1
                data.loc[i, 'sl_price'] = sl
                data.loc[i, 'tp_price'] = tp

engine = BacktestEngine(initial_capital=1000.0)
res = engine.run(data)
m = res['metrics']
print('Total Trades:', m['total_trades'])
print(f"Win Rate: {m['win_rate_pct']:.1f}%")
print(f"Net PnL: ${m['total_pnl']:.2f} ({m['total_return_pct']:.1f}%)")
print('Profit Factor:', m['profit_factor'])
trades = res['trades_df']
if not trades.empty:
    for _, t in trades.iterrows():
        print(f"{t['type']} | Entry:{t['entry_time']} @ {t['entry_price']:.2f} | Exit:{t['exit_time']} @ {t['exit_price']:.2f} | PnL:{t['net_pnl']:.2f} ({t['pnl_pct']:.2f}%) | Reason:{t['exit_reason']}")
