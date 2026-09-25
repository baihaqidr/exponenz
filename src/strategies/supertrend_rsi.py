import pandas as pd
import numpy as np
from src.strategies.base import BaseStrategy
from src.indicators import calculate_supertrend, calculate_rsi, calculate_atr, calculate_ema

class SupertrendRSIStrategy(BaseStrategy):
    """
    Strategi SuperTrend + RSI Filter:
    - Long: SuperTrend berubah menjadi Bullish (1) dan RSI > 50 serta RSI < 70 (tidak overbought).
    - Short: SuperTrend berubah menjadi Bearish (-1) dan RSI < 50 serta RSI > 30 (tidak oversold).
    - SL: Ditetapkan pada garis Supertrend atau berbasis ATR.
    - TP: Berdasarkan rasio Risk:Reward (misal 1:2 atau 1:1.5).
    """
    def __init__(self, st_period: int = 10, st_multiplier: float = 3.0, rsi_period: int = 14, ema_filter_period: int = 200, risk_reward: float = 1.5):
        super().__init__("Supertrend_RSI")
        self.st_period = st_period
        self.st_multiplier = st_multiplier
        self.rsi_period = rsi_period
        self.ema_filter_period = ema_filter_period
        self.risk_reward = risk_reward

    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        data = df.copy()
        
        # Hitung Indikator
        st_val, st_dir = calculate_supertrend(data, period=self.st_period, multiplier=self.st_multiplier)
        data['supertrend'] = st_val
        data['st_dir'] = st_dir
        data['rsi'] = calculate_rsi(data['close'], period=self.rsi_period)
        data['ema_trend'] = calculate_ema(data['close'], length=self.ema_filter_period)
        data['atr'] = calculate_atr(data, period=14)

        # Deteksi pergantian arah Supertrend (Flip)
        data['st_flip'] = data['st_dir'].diff()

        data['signal'] = 0
        data['sl_price'] = np.nan
        data['tp_price'] = np.nan

        for i in range(1, len(data)):
            st_flip = data['st_flip'].iloc[i]
            st_dir = data['st_dir'].iloc[i]
            rsi = data['rsi'].iloc[i]
            close = data['close'].iloc[i]
            ema_200 = data['ema_trend'].iloc[i]
            atr = data['atr'].iloc[i]

            # Long Signal (Supertrend flip to Bullish or Bullish pullback with trend)
            if st_flip == 2 and rsi >= 48 and rsi <= 72 and close > ema_200:
                data.loc[data.index[i], 'signal'] = 1
                sl = data['supertrend'].iloc[i]
                risk = close - sl
                if risk > 0:
                    tp = close + (risk * self.risk_reward)
                    data.loc[data.index[i], 'sl_price'] = sl
                    data.loc[data.index[i], 'tp_price'] = tp

            # Short Signal (Supertrend flip to Bearish or Bearish pullback with trend)
            elif st_flip == -2 and rsi <= 52 and rsi >= 28 and close < ema_200:
                data.loc[data.index[i], 'signal'] = -1
                sl = data['supertrend'].iloc[i]
                risk = sl - close
                if risk > 0:
                    tp = close - (risk * self.risk_reward)
                    data.loc[data.index[i], 'sl_price'] = sl
                    data.loc[data.index[i], 'tp_price'] = tp

        return data
