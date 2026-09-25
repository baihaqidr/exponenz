import pandas as pd
from src.data_fetcher import fetch_binance_futures_klines
from src.indicators import calculate_supertrend, calculate_ema, calculate_atr
from src.backtester import BacktestEngine
from src.strategies.base import BaseStrategy

pairs = ['BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'BNBUSDT', 'DOGEUSDT', '1000PEPEUSDT', 'SUIUSDT', 'NEARUSDT', 'AVAXUSDT', 'XRPUSDT', 'LINKUSDT', 'ADAUSDT']

# 1. Base Pure Supertrend (10, 3.0)
class BaselineST(BaseStrategy):
    def generate_signals(self, df):
        d = df.copy()
        v, s = calculate_supertrend(d, 10, 3.0)
        d['st_dir'] = s
        d['signal'] = 0
        for i in range(1, len(d)):
            if d['st_dir'].iloc[i] == 1 and d['st_dir'].iloc[i-1] == -1: d.loc[d.index[i], 'signal'] = 1
            elif d['st_dir'].iloc[i] == -1 and d['st_dir'].iloc[i-1] == 1: d.loc[d.index[i], 'signal'] = -1
        return d

# 2. Supertrend + EMA 200 Trend Filter
class ST_EMA200(BaseStrategy):
    def generate_signals(self, df):
        d = df.copy()
        v, s = calculate_supertrend(d, 10, 3.0)
        d['st_dir'] = s
        d['ema200'] = calculate_ema(d['close'], 200)
        d['signal'] = 0
        for i in range(1, len(d)):
            ema = d['ema200'].iloc[i]
            c = d['close'].iloc[i]
            if d['st_dir'].iloc[i] == 1 and d['st_dir'].iloc[i-1] == -1 and c > ema:
                d.loc[d.index[i], 'signal'] = 1
            elif d['st_dir'].iloc[i] == -1 and d['st_dir'].iloc[i-1] == 1 and c < ema:
                d.loc[d.index[i], 'signal'] = -1
        return d

# 3. Supertrend + Wider Multiplier (14, 4.0)
class ST_Wider(BaseStrategy):
    def generate_signals(self, df):
        d = df.copy()
        v, s = calculate_supertrend(d, 14, 4.0)
        d['st_dir'] = s
        d['signal'] = 0
        for i in range(1, len(d)):
            if d['st_dir'].iloc[i] == 1 and d['st_dir'].iloc[i-1] == -1: d.loc[d.index[i], 'signal'] = 1
            elif d['st_dir'].iloc[i] == -1 and d['st_dir'].iloc[i-1] == 1: d.loc[d.index[i], 'signal'] = -1
        return d

tests = [
    ("1. Pure Supertrend (10, 3.0)", BaselineST("B")),
    ("2. Supertrend + Filter EMA 200", ST_EMA200("EMA")),
    ("3. Supertrend Anti-Chop (14, 4.0)", ST_Wider("Wider"))
]

for name, strat in tests:
    tot_pnl = 0
    tot_trades = 0
    wins = 0
    losses = 0
    for sym in pairs:
        df = fetch_binance_futures_klines(sym, '4h', 3000, use_cache=True)
        res = BacktestEngine(1000.0, 2.0, fixed_pos_size_pct=0.5).run(strat.generate_signals(df))
        m = res['metrics']
        tot_pnl += m['net_profit']
        tot_trades += m['total_trades']
        wins += m['win_count']
        losses += m['loss_count']
    wr = (wins / tot_trades * 100) if tot_trades > 0 else 0
    print(f"{name:35} -> Total Net PnL: ${tot_pnl:+.2f} | Win Rate: {wr:.1f}% | Total Trades: {tot_trades} (Losses Cut: {losses})")
