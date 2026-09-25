import pandas as pd
import numpy as np
from src.strategies.base import BaseStrategy
from src.indicators import calculate_supertrend, calculate_adx

class TrendRiderProStrategy(BaseStrategy):
    """
    Strategi Trend Rider Pro (4H Optimized):
    - SuperTrend (Period: 16, Multiplier: 4.0)
    - ADX Trend Strength Filter (ADX >= 15)
    - Sinyal:
        * Long: SuperTrend Flip ke Bullish + ADX >= 15
        * Short: SuperTrend Flip ke Bearish + ADX >= 15
        * SL / Trailing Stop: Mengikuti garis SuperTrend dinamis
    """
    def __init__(self, period: int = 16, multiplier: float = 4.0, adx_min: float = 15.0):
        super().__init__("Trend_Rider_Pro")
        self.period = period
        self.multiplier = multiplier
        self.adx_min = adx_min

    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        data = df.copy()

        st_val, st_dir = calculate_supertrend(data, period=self.period, multiplier=self.multiplier)
        data['supertrend'] = st_val
        data['st_dir'] = st_dir
        data['adx'] = calculate_adx(data, period=14)

        data['signal'] = 0
        data['sl_price'] = np.nan
        data['tp_price'] = np.nan

        for i in range(1, len(data)):
            st_curr = data['st_dir'].iloc[i]
            st_prev = data['st_dir'].iloc[i-1]
            adx = data['adx'].iloc[i]
            st_val_curr = data['supertrend'].iloc[i]

            # Long Entry (Flip to Bullish)
            if st_curr == 1 and st_prev == -1 and adx >= self.adx_min:
                data.loc[data.index[i], 'signal'] = 1
                data.loc[data.index[i], 'sl_price'] = st_val_curr
            # Short Entry (Flip to Bearish)
            elif st_curr == -1 and st_prev == 1 and adx >= self.adx_min:
                data.loc[data.index[i], 'signal'] = -1
                data.loc[data.index[i], 'sl_price'] = st_val_curr

        return data
