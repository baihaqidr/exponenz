import pandas as pd
from src.data_fetcher import fetch_binance_futures_klines
from src.indicators import calculate_supertrend
from src.backtester import BacktestEngine
from src.strategies.base import BaseStrategy

class SupertrendReversalStrategy(BaseStrategy):
    """
    Pure Supertrend Flip Reversal:
    - Tutup LONG & langsung Buka SHORT di candle flip yang sama.
    - Tutup SHORT & langsung Buka LONG di candle flip yang sama.
    - Stoploss tidak terbuang oleh sentuhan jarum di tengah jalan (kebal wick hunting).
    """
    def __init__(self, period=10, multiplier=3.0):
        super().__init__('Supertrend_Reversal')
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
            # Bullish Flip -> Signal 1 (Close Short, Open Long)
            if data['st_dir'].iloc[i] == 1 and data['st_dir'].iloc[i-1] == -1:
                data.loc[data.index[i], 'signal'] = 1
            # Bearish Flip -> Signal -1 (Close Long, Open Short)
            elif data['st_dir'].iloc[i] == -1 and data['st_dir'].iloc[i-1] == 1:
                data.loc[data.index[i], 'signal'] = -1

        return data

strat = SupertrendReversalStrategy(10, 3.0)
df = fetch_binance_futures_klines('SUIUSDT', '5m', 3000, use_cache=True)
engine = BacktestEngine(initial_capital=1000.0, leverage=2.0, fixed_pos_size_pct=0.5)
res = engine.run(strat.generate_signals(df))
df_t = res['trades_df']
print(f"Total Trades SUI (5m) Reversal: {len(df_t)}")
sub = df_t.tail(10)
for idx, t in sub.iterrows():
    print(f"Trade #{idx+1} {t['type']} | In: {t['entry_time']} @ ${t['entry_price']:.6f} | Out: {t['exit_time']} @ ${t['exit_price']:.6f} | Net: {t['net_pnl']:+.2f} ({t['exit_reason']})")
