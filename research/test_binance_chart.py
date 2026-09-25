import pandas as pd
from src.data_fetcher import fetch_binance_futures_klines
from src.indicators import calculate_supertrend
from src.backtester import BacktestEngine
from src.strategies.base import BaseStrategy

class BinanceExactSupertrend(BaseStrategy):
    """
    Supertrend (10, 4.0) matching user's Binance chart exactly
    """
    def __init__(self, period=10, multiplier=4.0):
        super().__init__('Binance_Exact_ST')
        self.period = period
        self.multiplier = multiplier

    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        data = df.copy()
        st_val, st_dir = calculate_supertrend(data, period=self.period, multiplier=self.multiplier)
        data['supertrend'] = st_val
        data['st_dir'] = st_dir
        data['signal'] = 0
        data['sl_price'] = float('nan')
        data['tp_price'] = float('nan')

        for i in range(1, len(data)):
            if data['st_dir'].iloc[i] == 1 and data['st_dir'].iloc[i-1] == -1:
                data.loc[data.index[i], 'signal'] = 1
            elif data['st_dir'].iloc[i] == -1 and data['st_dir'].iloc[i-1] == 1:
                data.loc[data.index[i], 'signal'] = -1
        return data

# Test on 15m matching user chart
df15 = fetch_binance_futures_klines('SUIUSDT', '15m', 1000, use_cache=True)
strat = BinanceExactSupertrend(10, 4.0)
sig15 = strat.generate_signals(df15)
engine = BacktestEngine(1000.0, 2.0, fixed_pos_size_pct=0.5)
res15 = engine.run(sig15)
df_t15 = res15['trades_df']
print(f"=== SUIUSDT 15M (Supertrend 10, 4.0) ===")
for idx, t in df_t15.tail(5).iterrows():
    e_wib = pd.to_datetime(t['entry_time']) + pd.Timedelta(hours=7)
    x_wib = pd.to_datetime(t['exit_time']) + pd.Timedelta(hours=7)
    print(f"Trade #{idx+1} {t['type']:5} | In: {e_wib.strftime('%Y-%m-%d %H:%M')} @ ${t['entry_price']:.6f} | Out: {x_wib.strftime('%Y-%m-%d %H:%M')} @ ${t['exit_price']:.6f} | Net: ${t['net_pnl']:+.2f} ({t['exit_reason']})")
