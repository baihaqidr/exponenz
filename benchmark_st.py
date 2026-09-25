import pandas as pd
from src.data_fetcher import fetch_binance_futures_klines
from src.indicators import calculate_supertrend
from src.backtester import BacktestEngine
from src.strategies.base import BaseStrategy

class PureST(BaseStrategy):
    def __init__(self, p=16, m=4.0):
        super().__init__('Trend_Rider_Pure')
        self.p = p
        self.m = m
    def generate_signals(self, df):
        d = df.copy()
        v, s = calculate_supertrend(d, self.p, self.m)
        d['supertrend'] = v
        d['st_dir'] = s
        d['signal'] = 0
        d['sl_price'] = float('nan')
        d['tp_price'] = float('nan')
        for i in range(1, len(d)):
            if d['st_dir'].iloc[i] == 1 and d['st_dir'].iloc[i-1] == -1:
                d.loc[d.index[i], 'signal'] = 1
                d.loc[data_idx := d.index[i], 'sl_price'] = d['supertrend'].iloc[i]
            elif d['st_dir'].iloc[i] == -1 and d['st_dir'].iloc[i-1] == 1:
                d.loc[d.index[i], 'signal'] = -1
                d.loc[data_idx := d.index[i], 'sl_price'] = d['supertrend'].iloc[i]
        return d

pairs = ['BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'BNBUSDT', 'DOGEUSDT', '1000PEPEUSDT', 'SUIUSDT', 'NEARUSDT', 'AVAXUSDT', 'XRPUSDT', 'LINKUSDT', 'ADAUSDT']

for (p, m) in [(16, 4.0), (10, 3.0), (14, 3.0), (20, 5.0)]:
    st = PureST(p, m)
    tot = 0
    print(f"\n=== Supertrend ({p}, {m}) NO ADX ===")
    for sym in pairs:
        df = fetch_binance_futures_klines(sym, '4h', 3000, use_cache=True)
        res = BacktestEngine(1000.0, 2.0, 0.02).run(st.generate_signals(df))
        met = res['metrics']
        tot += met['net_profit']
        print(f"  {sym}: Net PnL {met['net_profit']:+.2f} (WR: {met['win_rate']:.1f}%, Trades: {met['total_trades']})")
    print(f"TOTAL PORTFOLIO: {tot:+.2f}")
