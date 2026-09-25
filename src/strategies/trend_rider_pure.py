import pandas as pd
import numpy as np
from src.strategies.base import BaseStrategy
from src.indicators import calculate_supertrend

class TrendRiderPureStrategy(BaseStrategy):
    """
    Strategi Trend Rider Pure (Tanpa ADX - True Supertrend Flip Reversal):
    - SuperTrend Murni (Period: 16, Multiplier: 4.0)
    - Exit HANYA terjadi saat Supertrend resmi flip / berubah warna pada penutupan candle (Candle Close).
    - Tidak ada cut loss prematur di tengah jalan.
    - Begitu Supertrend Flip: Posisi lama ditutup dan posisi baru langsung dibuka di titik yang sama.
    """
    def __init__(self, period: int = 16, multiplier: float = 4.0):
        super().__init__("Trend_Rider_Pure")
        self.period = period
        self.multiplier = multiplier

    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        data = df.copy()

        st_val, st_dir = calculate_supertrend(data, period=self.period, multiplier=self.multiplier)
        data['supertrend'] = st_val
        data['st_dir'] = st_dir

        data['signal'] = 0
        data['sl_price'] = np.nan
        data['tp_price'] = np.nan

        for i in range(1, len(data)):
            st_curr = data['st_dir'].iloc[i]
            st_prev = data['st_dir'].iloc[i-1]

            # Long Entry (Flip to Bullish)
            if st_curr == 1 and st_prev == -1:
                data.loc[data.index[i], 'signal'] = 1
            # Short Entry (Flip to Bearish)
            elif st_curr == -1 and st_prev == 1:
                data.loc[data.index[i], 'signal'] = -1

        return data
