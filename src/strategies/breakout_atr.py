import pandas as pd
import numpy as np
from src.strategies.base import BaseStrategy
from src.indicators import calculate_atr, calculate_sma

class BreakoutATRStrategy(BaseStrategy):
    """
    Strategi Donchian Channel / Range Breakout dengan Volume & ATR SL/TP:
    - Long: Close bar menembus High N-periode tertinggi sebelumnya dengan volume > rata-rata volume 20 bar.
    - Short: Close bar menembus Low N-periode terendah sebelumnya dengan volume > rata-rata volume 20 bar.
    """
    def __init__(self, channel_period: int = 20, atr_sl_mult: float = 1.5, risk_reward: float = 2.0):
        super().__init__("Breakout_ATR")
        self.channel_period = channel_period
        self.atr_sl_mult = atr_sl_mult
        self.risk_reward = risk_reward

    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        data = df.copy()

        data['highest_high'] = data['high'].shift(1).rolling(window=self.channel_period).max()
        data['lowest_low'] = data['low'].shift(1).rolling(window=self.channel_period).min()
        data['vol_sma'] = calculate_sma(data['volume'], 20)
        data['atr'] = calculate_atr(data, period=14)

        data['signal'] = 0
        data['sl_price'] = np.nan
        data['tp_price'] = np.nan

        for i in range(self.channel_period + 1, len(data)):
            close = data['close'].iloc[i]
            prev_high = data['highest_high'].iloc[i]
            prev_low = data['lowest_low'].iloc[i]
            vol = data['volume'].iloc[i]
            vol_sma = data['vol_sma'].iloc[i]
            atr = data['atr'].iloc[i]

            # Breakout Up
            if close > prev_high and vol > vol_sma:
                data.loc[data.index[i], 'signal'] = 1
                sl = close - (atr * self.atr_sl_mult)
                tp = close + (atr * self.atr_sl_mult * self.risk_reward)
                data.loc[data.index[i], 'sl_price'] = sl
                data.loc[data.index[i], 'tp_price'] = tp

            # Breakout Down
            elif close < prev_low and vol > vol_sma:
                data.loc[data.index[i], 'signal'] = -1
                sl = close + (atr * self.atr_sl_mult)
                tp = close - (atr * self.atr_sl_mult * self.risk_reward)
                data.loc[data.index[i], 'sl_price'] = sl
                data.loc[data.index[i], 'tp_price'] = tp

        return data
