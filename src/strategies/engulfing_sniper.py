import pandas as pd
import numpy as np
from src.strategies.base import BaseStrategy

class EngulfingSniperStrategy(BaseStrategy):
    """
    Strategi Candlestick Engulfing Full Body / Marubozu (Risk:Reward 1:2):
    
    Karakteristik Utama:
    - Candle Engulfing (Candle 2) WAJIB FULL BODY TANPA WICK ATAS DAN BAWAH (Marubozu Body).
    
    1. Bullish Engulfing (Full Body):
       * Candle 1: Merah / Bearish (Close < Open).
       * Candle 2: Hijau / Bullish (Close > Open).
       * Body Candle 2 menelan seluruh Body Candle 1 (Open2 <= Close1 dan Close2 >= Open1).
       * Tanpa Wick Atas & Bawah pada Candle 2:
           - Upper Wick = (High2 - Close2) <= Body2 * max_wick_ratio
           - Lower Wick = (Open2 - Low2) <= Body2 * max_wick_ratio
       * Entry: BUY pada closing Candle 2.
       * Stop Loss (SL): Low Candle 2 (atau Min(Low1, Low2)).
       * Take Profit (TP): Entry + (2.0 * Jarak SL) -> Rasio Risk to Reward 1:2.0.

    2. Bearish Engulfing (Full Body):
       * Candle 1: Hijau / Bullish (Close > Open).
       * Candle 2: Merah / Bearish (Close < Open).
       * Body Candle 2 menelan seluruh Body Candle 1 (Open2 >= Close1 dan Close2 <= Open1).
       * Tanpa Wick Atas & Bawah pada Candle 2:
           - Upper Wick = (High2 - Open2) <= Body2 * max_wick_ratio
           - Lower Wick = (Close2 - Low2) <= Body2 * max_wick_ratio
       * Entry: SELL pada closing Candle 2.
       * Stop Loss (SL): High Candle 2 (atau Max(High1, High2)).
       * Take Profit (TP): Entry - (2.0 * Jarak SL) -> Rasio Risk to Reward 1:2.0.
    """
    def __init__(self, risk_reward: float = 2.0, max_wick_ratio: float = 0.05, min_body_ratio: float = 1.0):
        super().__init__("Engulfing_Sniper")
        self.risk_reward = risk_reward
        self.max_wick_ratio = max_wick_ratio # Toleransi wick (default 0.05 / 5% body untuk menangani micro-tick Binance)
        self.min_body_ratio = min_body_ratio

    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        data = df.copy()

        data['signal'] = 0
        data['sl_price'] = np.nan
        data['tp_price'] = np.nan

        open_p = data['open'].values
        high_p = data['high'].values
        low_p = data['low'].values
        close_p = data['close'].values

        for i in range(1, len(data)):
            c1_open, c1_close = open_p[i-1], close_p[i-1]
            c2_open, c2_close = open_p[i], close_p[i]
            c1_high, c1_low = high_p[i-1], low_p[i-1]
            c2_high, c2_low = high_p[i], low_p[i]

            c1_body = abs(c1_close - c1_open)
            c2_body = abs(c2_close - c2_open)

            if c2_body <= 0:
                continue

            # 1. Bullish Engulfing Full Body (Tanpa Wick Atas & Bawah)
            # Candle 1 Merah, Candle 2 Hijau
            if c1_close < c1_open and c2_close > c2_open:
                # Body 2 menelan Body 1
                if c2_open <= (c1_close + 1e-8) and c2_close >= (c1_open - 1e-8) and c2_body >= (c1_body * self.min_body_ratio):
                    upper_wick = c2_high - c2_close
                    lower_wick = c2_open - c2_low
                    # Syarat Mutlak: Full Body tanpa wick atas bawah
                    if upper_wick <= (c2_body * self.max_wick_ratio) and lower_wick <= (c2_body * self.max_wick_ratio):
                        entry = c2_close
                        sl = min(c1_low, c2_low) * 0.999
                        sl_dist = entry - sl
                        if sl_dist > 0:
                            tp = entry + (sl_dist * self.risk_reward)
                            data.loc[data.index[i], 'signal'] = 1
                            data.loc[data.index[i], 'sl_price'] = sl
                            data.loc[data.index[i], 'tp_price'] = tp

            # 2. Bearish Engulfing Full Body (Tanpa Wick Atas & Bawah)
            # Candle 1 Hijau, Candle 2 Merah
            elif c1_close > c1_open and c2_close < c2_open:
                # Body 2 menelan Body 1
                if c2_open >= (c1_close - 1e-8) and c2_close <= (c1_open + 1e-8) and c2_body >= (c1_body * self.min_body_ratio):
                    upper_wick = c2_high - c2_open
                    lower_wick = c2_close - c2_low
                    # Syarat Mutlak: Full Body tanpa wick atas bawah
                    if upper_wick <= (c2_body * self.max_wick_ratio) and lower_wick <= (c2_body * self.max_wick_ratio):
                        entry = c2_close
                        sl = max(c1_high, c2_high) * 1.001
                        sl_dist = sl - entry
                        if sl_dist > 0:
                            tp = entry - (sl_dist * self.risk_reward)
                            data.loc[data.index[i], 'signal'] = -1
                            data.loc[data.index[i], 'sl_price'] = sl
                            data.loc[data.index[i], 'tp_price'] = tp

        return data
