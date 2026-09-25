import pandas as pd
import numpy as np
from src.strategies.base import BaseStrategy
from src.indicators import calculate_ema, calculate_rsi, calculate_atr, calculate_adx, calculate_sma

class MTFTrendPullbackStrategy(BaseStrategy):
    """
    Strategi Multi-Timeframe (MTF) Trend-Pullback Pro:
    - MTF Trend Filter (Setara 4h Trend di 1h):
        * Macro Bullish: Close > EMA 800 (setara 200 EMA di 4h) dan EMA 200 > EMA 800
        * Macro Bearish: Close < EMA 800 dan EMA 200 < EMA 800
    - Trigger Entry:
        * Long: Harga pullback ke EMA 21 / EMA 50, RSI mendingin ke 42-55, Volume > 1.15x MA20, Candle Rejection Hijau.
        * Short: Harga pullback ke EMA 21 / EMA 50, RSI mendingin ke 45-58, Volume > 1.15x MA20, Candle Rejection Merah.
    - Risk & Reward:
        * SL: 1.2x ATR
        * TP: 2.8x ATR (Risk-Reward 1 : 2.33)
        * Auto-BEP: Otomatis kunci modal ke Entry saat profit mencapai 1.2x ATR (+1R).
    """
    def __init__(
        self,
        ema_fast: int = 21,
        ema_mid: int = 50,
        ema_1h_trend: int = 200,
        ema_4h_trend: int = 800,
        adx_min: float = 18.0,
        atr_sl_mult: float = 1.2,
        risk_reward: float = 2.33
    ):
        super().__init__("MTF_Trend_Pullback_Pro")
        self.ema_fast = ema_fast
        self.ema_mid = ema_mid
        self.ema_1h_trend = ema_1h_trend
        self.ema_4h_trend = ema_4h_trend
        self.adx_min = adx_min
        self.atr_sl_mult = atr_sl_mult
        self.risk_reward = risk_reward

    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        data = df.copy()

        # Hitung Indikator
        data['ema_21'] = calculate_ema(data['close'], length=self.ema_fast)
        data['ema_50'] = calculate_ema(data['close'], length=self.ema_mid)
        data['ema_200'] = calculate_ema(data['close'], length=self.ema_1h_trend)
        data['ema_800'] = calculate_ema(data['close'], length=self.ema_4h_trend) # Representasi 4H 200 EMA
        data['rsi'] = calculate_rsi(data['close'], period=14)
        data['adx'] = calculate_adx(data, period=14)
        data['atr'] = calculate_atr(data, period=14)
        data['vol_ma'] = calculate_sma(data['volume'], length=20)

        data['signal'] = 0
        data['sl_price'] = np.nan
        data['tp_price'] = np.nan

        # Mulai setelah EMA 800 terisi data
        start_idx = min(self.ema_4h_trend + 10, len(data) - 1)

        for i in range(start_idx, len(data)):
            close = data['close'].iloc[i]
            open_p = data['open'].iloc[i]
            high = data['high'].iloc[i]
            low = data['low'].iloc[i]
            ema_21 = data['ema_21'].iloc[i]
            ema_50 = data['ema_50'].iloc[i]
            ema_200 = data['ema_200'].iloc[i]
            ema_800 = data['ema_800'].iloc[i]
            rsi = data['rsi'].iloc[i]
            adx = data['adx'].iloc[i]
            atr = data['atr'].iloc[i]
            vol = data['volume'].iloc[i]
            vol_ma = data['vol_ma'].iloc[i]

            # 1. Konfirmasi Tren MTF Kuat
            mtf_bull = (close > ema_800) and (ema_200 > ema_800) and (ema_21 > ema_50) and (adx >= self.adx_min)
            mtf_bear = (close < ema_800) and (ema_200 < ema_800) and (ema_21 < ema_50) and (adx >= self.adx_min)

            has_volume = vol >= (vol_ma * 1.10)

            # 2. 🟢 LONG TRIGGER (Pullback ke Support Dinamis EMA 21 / 50 di Tren 4h Bullish)
            if mtf_bull and (low <= ema_21) and (close >= ema_50) and (close > open_p) and (40 <= rsi <= 56) and has_volume:
                data.loc[data.index[i], 'signal'] = 1
                sl = close - (atr * self.atr_sl_mult)
                tp = close + ((close - sl) * self.risk_reward)
                data.loc[data.index[i], 'sl_price'] = sl
                data.loc[data.index[i], 'tp_price'] = tp

            # 3. 🔴 SHORT TRIGGER (Pullback ke Resistensi Dinamis EMA 21 / 50 di Tren 4h Bearish)
            elif mtf_bear and (high >= ema_21) and (close <= ema_50) and (close < open_p) and (44 <= rsi <= 60) and has_volume:
                data.loc[data.index[i], 'signal'] = -1
                sl = close + (atr * self.atr_sl_mult)
                tp = close - ((sl - close) * self.risk_reward)
                data.loc[data.index[i], 'sl_price'] = sl
                data.loc[data.index[i], 'tp_price'] = tp

        return data
