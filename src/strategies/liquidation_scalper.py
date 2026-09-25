import pandas as pd
import numpy as np
from src.strategies.base import BaseStrategy
from src.indicators import calculate_rsi, calculate_bollinger_bands, calculate_atr, calculate_ema

class LiquidationBounceScalper(BaseStrategy):
    """
    Strategi Liquidation & Extreme Reversal Scalper:
    - Long: Harga menembus ke bawah Lower Bollinger Band (Bandwidth melebar), RSI < 28 (Extreme Oversold), lalu candle ditutup hijau dengan ekor bawah panjang (Rejection Pinbar).
    - Short: Harga menembus ke atas Upper Bollinger Band, RSI > 72 (Extreme Overbought), lalu candle ditutup merah dengan ekor atas panjang.
    - TP: Kembali ke Middle Band (SMA 20) atau 1.5x Risk.
    - SL: 1.0x ATR di luar wick.
    """
    def __init__(self, bb_len: int = 20, bb_std: float = 2.2, rsi_len: int = 14, risk_reward: float = 1.5):
        super().__init__("Liquidation_Bounce_Scalper")
        self.bb_len = bb_len
        self.bb_std = bb_std
        self.rsi_len = rsi_len
        self.risk_reward = risk_reward

    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        data = df.copy()

        upper, mid, lower = calculate_bollinger_bands(data['close'], length=self.bb_len, std_dev=self.bb_std)
        data['bb_up'] = upper
        data['bb_mid'] = mid
        data['bb_low'] = lower
        data['rsi'] = calculate_rsi(data['close'], period=self.rsi_len)
        data['atr'] = calculate_atr(data, period=14)

        data['signal'] = 0
        data['sl_price'] = np.nan
        data['tp_price'] = np.nan

        for i in range(self.bb_len + 1, len(data)):
            open_p = data['open'].iloc[i]
            close = data['close'].iloc[i]
            high = data['high'].iloc[i]
            low = data['low'].iloc[i]
            bb_l = data['bb_low'].iloc[i]
            bb_u = data['bb_up'].iloc[i]
            bb_m = data['bb_mid'].iloc[i]
            rsi = data['rsi'].iloc[i]
            atr = data['atr'].iloc[i]

            # Rejection Pinbar Calculation
            body = abs(close - open_p)
            lower_wick = min(open_p, close) - low
            upper_wick = high - max(open_p, close)

            # 🟢 LONG: Liquidation Dump Rejection
            # Low menembus Lower Band, RSI < 30, Pinbar ekor bawah panjang (lower wick >= body * 1.5)
            if (low < bb_l) and (rsi <= 32) and (lower_wick >= body * 1.2) and (close > low + atr * 0.3):
                data.loc[data.index[i], 'signal'] = 1
                sl = low - (atr * 0.5)
                risk = close - sl
                tp = close + (risk * self.risk_reward)
                data.loc[data.index[i], 'sl_price'] = sl
                data.loc[data.index[i], 'tp_price'] = tp

            # 🔴 SHORT: Liquidation Pump Rejection
            elif (high > bb_u) and (rsi >= 68) and (upper_wick >= body * 1.2) and (close < high - atr * 0.3):
                data.loc[data.index[i], 'signal'] = -1
                sl = high + (atr * 0.5)
                risk = sl - close
                tp = close - (risk * self.risk_reward)
                data.loc[data.index[i], 'sl_price'] = sl
                data.loc[data.index[i], 'tp_price'] = tp

        return data
