import pandas as pd
import numpy as np
from src.strategies.base import BaseStrategy
from src.indicators import calculate_ema, calculate_atr

class EMACrossoverStrategy(BaseStrategy):
    """
    Strategi EMA Crossover (Fast EMA & Slow EMA) dengan Trend Filter 200 EMA dan Dynamic ATR Stop Loss:
    - Long: Fast EMA menembus ke atas Slow EMA saat harga di atas 200 EMA.
    - Short: Fast EMA menembus ke bawah Slow EMA saat harga di bawah 200 EMA.
    - SL: 1.5x ATR dari harga entry.
    - TP: 3.0x ATR dari harga entry (Risk-Reward 1:2).
    """
    def __init__(self, fast_ema: int = 9, slow_ema: int = 21, trend_ema: int = 200, atr_sl_mult: float = 1.5, risk_reward: float = 2.0):
        super().__init__("EMA_Crossover")
        self.fast_ema = fast_ema
        self.slow_ema = slow_ema
        self.trend_ema = trend_ema
        self.atr_sl_mult = atr_sl_mult
        self.risk_reward = risk_reward

    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        data = df.copy()

        data['ema_fast'] = calculate_ema(data['close'], length=self.fast_ema)
        data['ema_slow'] = calculate_ema(data['close'], length=self.slow_ema)
        data['ema_trend'] = calculate_ema(data['close'], length=self.trend_ema)
        data['atr'] = calculate_atr(data, period=14)

        # Deteksi Cross
        data['diff'] = data['ema_fast'] - data['ema_slow']
        data['prev_diff'] = data['diff'].shift(1)

        data['signal'] = 0
        data['sl_price'] = np.nan
        data['tp_price'] = np.nan

        for i in range(1, len(data)):
            diff = data['diff'].iloc[i]
            prev_diff = data['prev_diff'].iloc[i]
            close = data['close'].iloc[i]
            trend_ema = data['ema_trend'].iloc[i]
            atr = data['atr'].iloc[i]

            # Bullish Cross
            if prev_diff <= 0 and diff > 0 and close > trend_ema:
                data.loc[data.index[i], 'signal'] = 1
                sl = close - (atr * self.atr_sl_mult)
                tp = close + (atr * self.atr_sl_mult * self.risk_reward)
                data.loc[data.index[i], 'sl_price'] = sl
                data.loc[data.index[i], 'tp_price'] = tp

            # Bearish Cross
            elif prev_diff >= 0 and diff < 0 and close < trend_ema:
                data.loc[data.index[i], 'signal'] = -1
                sl = close + (atr * self.atr_sl_mult)
                tp = close - (atr * self.atr_sl_mult * self.risk_reward)
                data.loc[data.index[i], 'sl_price'] = sl
                data.loc[data.index[i], 'tp_price'] = tp

        return data
