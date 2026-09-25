import pandas as pd
import numpy as np
from src.strategies.base import BaseStrategy
from src.indicators import calculate_bollinger_bands, calculate_atr, calculate_rsi

class BBMiddleSniperStrategy(BaseStrategy):
    """
    Strategi Bollinger Middle Band Rejection Sniper (Trap & Trail):
    
    1. Logika Entry BUY (LONG):
       * Intra-candle harga sempat tembus ke bawah Middle Band (SMA 20): Low < Middle Band.
       * Closing candle gagal tembus dan ditutup di atas Middle Band: Close > Middle Band.
       * Candle membentuk ekor jarum bawah (Rejection Wick).
       * Entry: BUY di harga penutupan (Close).
       * Stop Loss (SL): Di ujung ekor jarum terendah (Low Candle) - 0.1% buffer.
       * Take Profit (TP): Entry + (Risk:Reward * Jarak SL), default R:R 1:2.0.
       * Trailing Stop: Mengikuti pergerakan garis Middle Band (SMA 20) untuk menunggangi tren panjang.
       
    2. Logika Entry SELL (SHORT):
       * Intra-candle harga sempat tembus ke atas Middle Band (SMA 20): High > Middle Band.
       * Closing candle gagal tembus dan ditutup di bawah Middle Band: Close < Middle Band.
       * Candle membentuk ekor jarum atas (Rejection Wick).
       * Entry: SELL di harga penutupan (Close).
       * Stop Loss (SL): Di ujung ekor jarum tertinggi (High Candle) + 0.1% buffer.
       * Take Profit (TP): Entry - (Risk:Reward * Jarak SL), default R:R 1:2.0.
       * Trailing Stop: Mengikuti pergerakan garis Middle Band (SMA 20) dari atas.
    """
    def __init__(self, bb_length: int = 20, bb_std: float = 2.0, risk_reward: float = 2.0, min_wick_ratio: float = 0.2):
        super().__init__("BB_Middle_Sniper")
        self.bb_length = bb_length
        self.bb_std = bb_std
        self.risk_reward = risk_reward
        self.min_wick_ratio = min_wick_ratio

    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        data = df.copy()
        upper, middle, lower = calculate_bollinger_bands(data['close'], length=self.bb_length, std_dev=self.bb_std)
        data['upper'] = upper
        data['middle'] = middle
        data['lower'] = lower
        data['atr'] = calculate_atr(data, 14)

        data['signal'] = 0
        data['sl_price'] = np.nan
        data['tp_price'] = np.nan

        open_p = data['open'].values
        high_p = data['high'].values
        low_p = data['low'].values
        close_p = data['close'].values
        mid_p = data['middle'].values

        for i in range(self.bb_length, len(data)):
            c_open, c_close = open_p[i], close_p[i]
            c_high, c_low = high_p[i], low_p[i]
            c_mid = mid_p[i]
            c_body = abs(c_close - c_open)
            c_range = c_high - c_low

            if c_range <= 0 or np.isnan(c_mid):
                continue

            # 1. SETUP BUY (LONG) - Rejection Mantul dari Bawah Middle Band
            # Syarat: Low sempat menusuk tembus ke bawah Middle Band, tapi Close ditutup di atas Middle Band
            if c_low < c_mid and c_close > c_mid:
                lower_wick = min(c_open, c_close) - c_low
                # Konfirmasi ekor jarum bawah yang menembus garis
                if lower_wick >= (c_body * self.min_wick_ratio) or c_close >= c_open:
                    entry = c_close
                    sl = c_low * 0.999 # SL tepat di ujung ekor jarum
                    sl_dist = entry - sl
                    if sl_dist > 0:
                        tp = entry + (sl_dist * self.risk_reward)
                        data.loc[data.index[i], 'signal'] = 1
                        data.loc[data.index[i], 'sl_price'] = sl
                        data.loc[data.index[i], 'tp_price'] = tp

            # 2. SETUP SELL (SHORT) - Rejection Tertolak dari Atas Middle Band
            # Syarat: High sempat menusuk tembus ke atas Middle Band, tapi Close ditutup di bawah Middle Band
            elif c_high > c_mid and c_close < c_mid:
                upper_wick = c_high - max(c_open, c_close)
                # Konfirmasi ekor jarum atas yang menembus garis
                if upper_wick >= (c_body * self.min_wick_ratio) or c_close <= c_open:
                    entry = c_close
                    sl = c_high * 1.001 # SL tepat di ujung ekor jarum
                    sl_dist = sl - entry
                    if sl_dist > 0:
                        tp = entry - (sl_dist * self.risk_reward)
                        data.loc[data.index[i], 'signal'] = -1
                        data.loc[data.index[i], 'sl_price'] = sl
                        data.loc[data.index[i], 'tp_price'] = tp

        return data
