import pandas as pd
import numpy as np
from src.strategies.base import BaseStrategy
from src.indicators import calculate_ema

class PriceEMACrossoverStrategy(BaseStrategy):
    """
    Strategi MQL5 1:1 Price EMA Crossover 7:
    - BUY (Buffer1): Close[1] > MA[1] dan Close[2] < MA[2] (Menembus ke atas garis EMA 7)
    - SELL (Buffer2): Close[1] < MA[1] dan Close[2] > MA[2] (Menembus ke bawah garis EMA 7)
    """
    def __init__(
        self,
        ema_period: int = 7,
        risk_reward: float = 2.0,
        sl_buffer_pct: float = 0.001,
        name_suffix: str = ""
    ):
        name = f"Price_EMA_{ema_period}_Crossover" if not name_suffix else f"Price_EMA_{ema_period}_{name_suffix}"
        super().__init__(name)
        self.ema_period = ema_period
        self.risk_reward = risk_reward
        self.sl_buffer_pct = sl_buffer_pct

    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        data = df.copy()

        ema_col = f"ema_{self.ema_period}"
        data[ema_col] = calculate_ema(data['close'], length=self.ema_period)
        data['ema_main'] = data[ema_col]
        data['ema_7'] = data[ema_col]

        data['signal'] = 0
        data['sl_price'] = np.nan
        data['tp_price'] = np.nan

        close = data['close'].values
        high = data['high'].values
        low = data['low'].values
        ema = data['ema_main'].values

        n = len(data)
        for i in range(1, n):
            c_curr = close[i]       # Bar 1 (Closed)
            ema_curr = ema[i]       # Bar 1 EMA 7
            c_prev = close[i-1]     # Bar 2 (Lilin sebelum Bar 1)
            ema_prev = ema[i-1]     # Bar 2 EMA 7

            # BUY CROSS (MQL5: Close[1] > MA[1] && Close[2] < MA[2])
            if c_curr > ema_curr and c_prev < ema_prev:
                entry = c_curr
                sl = low[i] * (1.0 - self.sl_buffer_pct)
                sl_dist = entry - sl
                tp = entry + (sl_dist * self.risk_reward) if sl_dist > 0 else entry * 1.01
                data.loc[data.index[i], 'signal'] = 1
                data.loc[data.index[i], 'sl_price'] = sl
                data.loc[data.index[i], 'tp_price'] = tp

            # SELL CROSS (MQL5: Close[1] < MA[1] && Close[2] > MA[2])
            elif c_curr < ema_curr and c_prev > ema_prev:
                entry = c_curr
                sl = high[i] * (1.0 + self.sl_buffer_pct)
                sl_dist = sl - entry
                tp = entry - (sl_dist * self.risk_reward) if sl_dist > 0 else entry * 0.99
                data.loc[data.index[i], 'signal'] = -1
                data.loc[data.index[i], 'sl_price'] = sl
                data.loc[data.index[i], 'tp_price'] = tp

        return data
