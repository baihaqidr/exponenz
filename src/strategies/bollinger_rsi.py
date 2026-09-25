import pandas as pd
import numpy as np
from src.strategies.base import BaseStrategy
from src.indicators import calculate_rsi, calculate_bollinger_bands, calculate_atr, calculate_ema

class BollingerRSIScalperStrategy(BaseStrategy):
    """
    Strategi Mean-Reversion / Pullback Scalping (Bollinger Bands + RSI Confirmation):
    - Long: Harga menyentuh / menembus Lower Bollinger Band, RSI < 35 (Oversold), dan candle mulai reversal.
    - Short: Harga menyentuh / menembus Upper Bollinger Band, RSI > 65 (Overbought), dan candle mulai reversal.
    - Target TP: Middle Band (SMA 20) atau 1.5x Risk.
    - Stop Loss: 1.0x ATR di bawah lower band.
    """
    def __init__(self, bb_period: int = 20, bb_std: float = 2.0, rsi_period: int = 14, risk_reward: float = 1.5):
        super().__init__("Bollinger_RSI_Scalper")
        self.bb_period = bb_period
        self.bb_std = bb_std
        self.rsi_period = rsi_period
        self.risk_reward = risk_reward

    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        data = df.copy()

        upper, mid, lower = calculate_bollinger_bands(data['close'], length=self.bb_period, std_dev=self.bb_std)
        data['bb_upper'] = upper
        data['bb_mid'] = mid
        data['bb_lower'] = lower
        data['rsi'] = calculate_rsi(data['close'], period=self.rsi_period)
        data['atr'] = calculate_atr(data, period=14)

        data['signal'] = 0
        data['sl_price'] = np.nan
        data['tp_price'] = np.nan

        for i in range(self.bb_period + 1, len(data)):
            close = data['close'].iloc[i]
            low = data['low'].iloc[i]
            high = data['high'].iloc[i]
            bb_low = data['bb_lower'].iloc[i]
            bb_up = data['bb_upper'].iloc[i]
            bb_m = data['bb_mid'].iloc[i]
            rsi = data['rsi'].iloc[i]
            atr = data['atr'].iloc[i]

            # Long Setup: Rejection dari Lower Band + Oversold RSI
            if low <= bb_low and close > bb_low and rsi <= 38:
                data.loc[data.index[i], 'signal'] = 1
                sl = close - (atr * 1.0)
                tp = close + ((close - sl) * self.risk_reward)
                data.loc[data.index[i], 'sl_price'] = sl
                data.loc[data.index[i], 'tp_price'] = tp

            # Short Setup: Rejection dari Upper Band + Overbought RSI
            elif high >= bb_up and close < bb_up and rsi >= 62:
                data.loc[data.index[i], 'signal'] = -1
                sl = close + (atr * 1.0)
                tp = close - ((sl - close) * self.risk_reward)
                data.loc[data.index[i], 'sl_price'] = sl
                data.loc[data.index[i], 'tp_price'] = tp

        return data
