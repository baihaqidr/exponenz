import pandas as pd
from src.data_fetcher import fetch_binance_futures_klines
from src.indicators import calculate_supertrend, calculate_ema, calculate_atr
from src.backtester import BacktestEngine
from src.strategies.base import BaseStrategy

pairs = ['BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'BNBUSDT', 'DOGEUSDT', '1000PEPEUSDT', 'SUIUSDT', 'NEARUSDT', 'AVAXUSDT', 'XRPUSDT', 'LINKUSDT', 'ADAUSDT']

class ST_SmartPro(BaseStrategy):
    """
    Supertrend + EMA 200 Baseline + Fixed Risk 2%
    """
    def __init__(self, period=10, multiplier=3.0, ema_len=200):
        super().__init__('ST_SmartPro')
        self.period = period
        self.multiplier = multiplier
        self.ema_len = ema_len

    def generate_signals(self, df):
        d = df.copy()
        v, s = calculate_supertrend(d, self.period, self.multiplier)
        d['st_dir'] = s
        d['supertrend'] = v
        d['ema'] = calculate_ema(d['close'], self.ema_len)
        d['signal'] = 0
        d['sl_price'] = float('nan')
        d['tp_price'] = float('nan')

        for i in range(1, len(d)):
            ema = d['ema'].iloc[i]
            c = d['close'].iloc[i]
            # Long: Supertrend Bullish + Harga di atas EMA (Trend Utama Bullish)
            if d['st_dir'].iloc[i] == 1 and d['st_dir'].iloc[i-1] == -1 and c > ema:
                d.loc[d.index[i], 'signal'] = 1
            # Short: Supertrend Bearish + Harga di bawah EMA (Trend Utama Bearish)
            elif d['st_dir'].iloc[i] == -1 and d['st_dir'].iloc[i-1] == 1 and c < ema:
                d.loc[d.index[i], 'signal'] = -1
        return d

strat = ST_SmartPro(10, 3.0, 200)
tot_pnl = 0
print("=== HASIL SUPERTREND + FILTER EMA 200 (4H) ===")
for sym in pairs:
    df = fetch_binance_futures_klines(sym, '4h', 3000, use_cache=True)
    res = BacktestEngine(1000.0, 2.0, fixed_pos_size_pct=0.5).run(strat.generate_signals(df))
    m = res['metrics']
    tot_pnl += m['net_profit']
    print(f"{sym:12} | Net PnL: ${m['net_profit']:+8.2f} (ROI: {m['net_profit_pct']:+6.1f}%) | WR: {m['win_rate']:4.1f}% | Trades: {m['total_trades']}")

print("-" * 65)
print(f"TOTAL PORTOFOLIO NET PnL: ${tot_pnl:+.2f}")
