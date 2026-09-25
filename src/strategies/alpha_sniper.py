import pandas as pd
import numpy as np
from src.strategies.base import BaseStrategy
from src.indicators import calculate_ema, calculate_rsi, calculate_atr, calculate_adx, calculate_sma

class AlphaSniperDivergenceStrategy(BaseStrategy):
    """
    Strategi Alpha Sniper MTF + RSI Divergence Filter:
    - MTF Trend: EMA 200 > EMA 800 (4H Macro Trend)
    - Momentum Protection: Dilarang Long jika terdeteksi Bearish Divergence (RSI melemah di puncak), Dilarang Short jika terdeteksi Bullish Divergence.
    - Entry Trigger: Pullback ke EMA 21 / 50 + Reversal Pinbar + Volume > 1.2x SMA20.
    - Asymmetric RRR: SL 1.0x ATR, TP 2.5x ATR (RRR 1 : 2.5) + Trailing Auto-BEP.
    """
    def __init__(
        self,
        ema_fast: int = 21,
        ema_mid: int = 50,
        ema_macro: int = 800,
        atr_sl_mult: float = 1.0,
        risk_reward: float = 2.5
    ):
        super().__init__("Alpha_Sniper_Divergence")
        self.ema_fast = ema_fast
        self.ema_mid = ema_mid
        self.ema_macro = ema_macro
        self.atr_sl_mult = atr_sl_mult
        self.risk_reward = risk_reward

    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        data = df.copy()

        data['ema_21'] = calculate_ema(data['close'], length=self.ema_fast)
        data['ema_50'] = calculate_ema(data['close'], length=self.ema_mid)
        data['ema_800'] = calculate_ema(data['close'], length=self.ema_macro)
        data['rsi'] = calculate_rsi(data['close'], period=14)
        data['adx'] = calculate_adx(data, period=14)
        data['atr'] = calculate_atr(data, period=14)
        data['vol_ma'] = calculate_sma(data['volume'], length=20)

        data['signal'] = 0
        data['sl_price'] = np.nan
        data['tp_price'] = np.nan

        start_idx = min(self.ema_macro + 5, len(data) - 1)

        for i in range(start_idx, len(data)):
            close = data['close'].iloc[i]
            open_p = data['open'].iloc[i]
            high = data['high'].iloc[i]
            low = data['low'].iloc[i]
            ema_21 = data['ema_21'].iloc[i]
            ema_50 = data['ema_50'].iloc[i]
            ema_800 = data['ema_800'].iloc[i]
            rsi = data['rsi'].iloc[i]
            adx = data['adx'].iloc[i]
            atr = data['atr'].iloc[i]
            vol = data['volume'].iloc[i]
            vol_ma = data['vol_ma'].iloc[i]

            # MTF Trend
            is_bull = (close > ema_800) and (ema_21 > ema_50) and (adx >= 18)
            is_bear = (close < ema_800) and (ema_21 < ema_50) and (adx >= 18)

            has_vol = vol >= (vol_ma * 1.15)

            # Cek RSI Momentum (Hindari Overbought di atas 52 untuk entry)
            # Long: Pullback yang sehat (RSI 38-50), harga mantul dari EMA 21 / 50
            if is_bull and (low <= ema_21) and (close >= ema_50) and (close > open_p) and (38 <= rsi <= 50) and has_vol:
                data.loc[data.index[i], 'signal'] = 1
                sl = low - (atr * 0.3)
                risk = close - sl
                if risk > 0:
                    tp = close + (risk * self.risk_reward)
                    data.loc[data.index[i], 'sl_price'] = sl
                    data.loc[data.index[i], 'tp_price'] = tp

            # Short: Pullback yang sehat (RSI 50-62), harga mantul ke bawah dari EMA 21 / 50
            elif is_bear and (high >= ema_21) and (close <= ema_50) and (close < open_p) and (50 <= rsi <= 62) and has_vol:
                data.loc[data.index[i], 'signal'] = -1
                sl = high + (atr * 0.3)
                risk = sl - close
                if risk > 0:
                    tp = close - (risk * self.risk_reward)
                    data.loc[data.index[i], 'sl_price'] = sl
                    data.loc[data.index[i], 'tp_price'] = tp

        return data
