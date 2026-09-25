import pandas as pd
from src.data_fetcher import fetch_binance_futures_klines
from src.indicators import calculate_supertrend
from src.backtester import BacktestEngine
from src.strategies.base import BaseStrategy

class TrueSupertrendFlip(BaseStrategy):
    """
    Exit HANYA ketika Supertrend resmi FLIP arah (Candle Closing berubah warna).
    Tidak keluar prematur oleh sentuhan low wick di tengah jalan.
    """
    def __init__(self, period=10, multiplier=3.0):
        super().__init__('True_Supertrend_Flip')
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

strat = TrueSupertrendFlip(10, 3.0)
df = fetch_binance_futures_klines('SUIUSDT', '5m', 3000, use_cache=True)
engine = BacktestEngine(initial_capital=1000.0, leverage=2.0, fixed_pos_size_pct=0.5)
res = engine.run(strat.generate_signals(df))
df_t = res['trades_df']
print(f"Total Trades SUI 5M True Flip: {len(df_t)}")
sub = df_t.tail(6)
for idx, t in sub.iterrows():
    e_wib = pd.to_datetime(t['entry_time']) + pd.Timedelta(hours=7)
    x_wib = pd.to_datetime(t['exit_time']) + pd.Timedelta(hours=7)
    print(f"#{idx+1} {t['type']:5} | In: {e_wib.strftime('%Y-%m-%d %H:%M')} @ ${t['entry_price']:.6f} | Out: {x_wib.strftime('%Y-%m-%d %H:%M')} @ ${t['exit_price']:.6f} | Net: ${t['net_pnl']:+.2f} | Reason: {t['exit_reason']}")
