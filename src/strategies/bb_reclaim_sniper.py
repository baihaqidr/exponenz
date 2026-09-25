import pandas as pd
import numpy as np
from src.strategies.base import BaseStrategy
from src.indicators import calculate_bollinger_bands

class BBReclaimSniperStrategy(BaseStrategy):
    """
    Strategi Bollinger Band Breach & Reclaim Sniper (Pure 1 Indicator + RR & Trailing):
    
    1. Logika Entry BUY (LONG):
       * Candle 1 (i-1): Candle merah yang seluruh/sebagian body-nya keluar menembus ke bawah Lower Band (Close[i-1] < Lower[i-1]).
       * Candle 2 (i): Candle hijau yang berhasil memantul dan CLOSING KEMBALI DI ATAS Lower Band (Close[i] > Lower[i] dan Close[i] > Open[i]).
       * Entry: BUY di harga penutupan (Close[i]).
       * Stop Loss (SL): Min(Low[i-1], Low[i]) * 0.999 (titik terendah ekor kepanikan).
       * Take Profit (TP): Entry + (Risk:Reward * Jarak SL), default R:R 1:2.0.
       * Trailing Stop: Trailing dinamis untuk mengunci profit saat tren berlanjut.
       
    2. Logika Entry SELL (SHORT):
       * Candle 1 (i-1): Candle hijau yang keluar menembus ke atas Upper Band (Close[i-1] > Upper[i-1]).
       * Candle 2 (i): Candle merah yang berhasil memantul turun dan CLOSING KEMBALI DI BAWAH Upper Band (Close[i] < Upper[i] dan Close[i] < Open[i]).
       * Entry: SELL di harga penutupan (Close[i]).
       * Stop Loss (SL): Max(High[i-1], High[i]) * 1.001 (titik tertinggi ekor FOMO).
       * Take Profit (TP): Entry - (Risk:Reward * Jarak SL), default R:R 1:2.0.
       * Trailing Stop: Trailing dinamis merayap dari atas saat tren turun berlanjut.
    """
    def __init__(self, bb_length: int = 20, bb_std: float = 2.0, risk_reward: float = 2.0):
        super().__init__("BB_Reclaim_Sniper")
        self.bb_length = bb_length
        self.bb_std = bb_std
        self.risk_reward = risk_reward

    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        data = df.copy()
        upper, middle, lower = calculate_bollinger_bands(data['close'], length=self.bb_length, std_dev=self.bb_std)
        data['upper'] = upper
        data['middle'] = middle
        data['lower'] = lower

        data['signal'] = 0
        data['sl_price'] = np.nan
        data['tp_price'] = np.nan

        open_p = data['open'].values
        high_p = data['high'].values
        low_p = data['low'].values
        close_p = data['close'].values
        lower_p = data['lower'].values
        upper_p = data['upper'].values

        for i in range(self.bb_length, len(data)):
            c1_open, c1_close = open_p[i-1], close_p[i-1]
            c2_open, c2_close = open_p[i], close_p[i]
            c1_high, c1_low = high_p[i-1], low_p[i-1]
            c2_high, c2_low = high_p[i], low_p[i]
            
            c1_lower, c2_lower = lower_p[i-1], lower_p[i]
            c1_upper, c2_upper = upper_p[i-1], upper_p[i]

            if np.isnan(c1_lower) or np.isnan(c2_lower):
                continue

            # 1. SETUP BUY (LONG) - Breach & Reclaim Lower Band
            # Syarat 1: Candle 1 sempat keluar/closing di bawah Lower Band
            # Syarat 2: Candle 2 berhasil closing kembali di atas Lower Band dan candle hijau (Close > Open)
            if c1_close < c1_lower and c2_close > c2_lower and c2_close > c2_open:
                entry = c2_close
                sl = min(c1_low, c2_low) * 0.999
                sl_dist = entry - sl
                if sl_dist > 0:
                    tp = entry + (sl_dist * self.risk_reward)
                    data.loc[data.index[i], 'signal'] = 1
                    data.loc[data.index[i], 'sl_price'] = sl
                    data.loc[data.index[i], 'tp_price'] = tp

            # 2. SETUP SELL (SHORT) - Breach & Reclaim Upper Band
            # Syarat 1: Candle 1 sempat keluar/closing di atas Upper Band
            # Syarat 2: Candle 2 berhasil closing kembali di bawah Upper Band dan candle merah (Close < Open)
            elif c1_close > c1_upper and c2_close < c2_upper and c2_close < c2_open:
                entry = c2_close
                sl = max(c1_high, c2_high) * 1.001
                sl_dist = sl - entry
                if sl_dist > 0:
                    tp = entry - (sl_dist * self.risk_reward)
                    data.loc[data.index[i], 'signal'] = -1
                    data.loc[data.index[i], 'sl_price'] = sl
                    data.loc[data.index[i], 'tp_price'] = tp

        return data
