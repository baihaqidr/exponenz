import pandas as pd
import numpy as np
from src.strategies.base import BaseStrategy
from src.indicators import calculate_ema, calculate_rsi, calculate_atr, calculate_adx, calculate_sma

class AlphaTrendPullbackStrategy(BaseStrategy):
    """
    Strategi Alpha Trend Pullback (ATP):
    - Konfirmasi 1: Trend Filter Makro (EMA 200) + ADX > 20 (Tren bertenaga)
    - Konfirmasi 2: Pullback ke Dynamic Support/Resistance Zone (antara EMA 21 & EMA 50)
    - Konfirmasi 3: RSI mendingin ke zona sehat (40-54 untuk Long, 46-60 untuk Short)
    - Konfirmasi 4: Volume confirmation (> 1.1x SMA Volume 20) + Reversal Candle
    - Konfirmasi 5: Asymmetric Risk:Reward (SL: 1.5x ATR, TP: 3.0x ATR = RRR 1:2.0)
    """
    def __init__(
        self,
        ema_fast: int = 21,
        ema_mid: int = 50,
        ema_macro: int = 200,
        adx_threshold: float = 20.0,
        atr_sl_mult: float = 1.5,
        risk_reward: float = 2.0
    ):
        super().__init__("Alpha_Trend_Pullback")
        self.ema_fast = ema_fast
        self.ema_mid = ema_mid
        self.ema_macro = ema_macro
        self.adx_threshold = adx_threshold
        self.atr_sl_mult = atr_sl_mult
        self.risk_reward = risk_reward

    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        data = df.copy()

        # Hitung Indikator
        data['ema_21'] = calculate_ema(data['close'], length=self.ema_fast)
        data['ema_50'] = calculate_ema(data['close'], length=self.ema_mid)
        data['ema_200'] = calculate_ema(data['close'], length=self.ema_macro)
        data['rsi'] = calculate_rsi(data['close'], period=14)
        data['adx'] = calculate_adx(data, period=14)
        data['atr'] = calculate_atr(data, period=14)
        data['vol_ma'] = calculate_sma(data['volume'], length=20)

        data['signal'] = 0
        data['sl_price'] = np.nan
        data['tp_price'] = np.nan

        for i in range(self.ema_macro + 1, len(data)):
            close = data['close'].iloc[i]
            open_p = data['open'].iloc[i]
            high = data['high'].iloc[i]
            low = data['low'].iloc[i]
            ema_21 = data['ema_21'].iloc[i]
            ema_50 = data['ema_50'].iloc[i]
            ema_200 = data['ema_200'].iloc[i]
            rsi = data['rsi'].iloc[i]
            adx = data['adx'].iloc[i]
            atr = data['atr'].iloc[i]
            vol = data['volume'].iloc[i]
            vol_ma = data['vol_ma'].iloc[i]

            # Kondisi Tren Kuat
            is_bull_trend = (close > ema_200) and (ema_21 > ema_50) and (adx >= self.adx_threshold)
            is_bear_trend = (close < ema_200) and (ema_21 < ema_50) and (adx >= self.adx_threshold)

            # Volume Filter
            has_volume = vol >= (vol_ma * 1.1)

            # 🟢 LONG SETUP:
            # 1. Bullish macro trend
            # 2. Pullback: Low menyentuh area EMA 21 atau EMA 50, dan Close ditutup di atas EMA 50
            # 3. Candle hijau (Close > Open)
            # 4. RSI sehat (40 <= RSI <= 56)
            if is_bull_trend and (low <= ema_21) and (close >= ema_50) and (close > open_p) and (40 <= rsi <= 56) and has_volume:
                data.loc[data.index[i], 'signal'] = 1
                sl = close - (atr * self.atr_sl_mult)
                tp = close + ((close - sl) * self.risk_reward)
                data.loc[data.index[i], 'sl_price'] = sl
                data.loc[data.index[i], 'tp_price'] = tp

            # 🔴 SHORT SETUP:
            # 1. Bearish macro trend
            # 2. Pullback: High menyentuh area EMA 21 atau EMA 50, dan Close ditutup di bawah EMA 50
            # 3. Candle merah (Close < Open)
            # 4. RSI sehat (44 <= RSI <= 60)
            elif is_bear_trend and (high >= ema_21) and (close <= ema_50) and (close < open_p) and (44 <= rsi <= 60) and has_volume:
                data.loc[data.index[i], 'signal'] = -1
                sl = close + (atr * self.atr_sl_mult)
                tp = close - ((sl - close) * self.risk_reward)
                data.loc[data.index[i], 'sl_price'] = sl
                data.loc[data.index[i], 'tp_price'] = tp

        return data
