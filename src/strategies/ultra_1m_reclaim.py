import numpy as np
import pandas as pd
from src.strategies.base import BaseStrategy

class Ultra1mReclaimScalper(BaseStrategy):
    """
    ⚡ ULTRA 1M VOLATILITY RECLAIM & SNAP-BACK SCALPER
    Khusus Timeframe 1 Menit Binance Futures.
    
    Konsep Kuantitatif:
    1. Bollinger Band (20, 2.2) + RSI (9) + EMA 50 Baseline
    2. Long Trigger: Harga menusuk ke bawah Lower Band (Oversold Panic / Liquidation Wick),
       lalu lilin konfirmasi MENEMBUS KEMBALI KE ATAS (Reclaim) Lower Band dengan RSI oversold (< 30 bounce).
    3. Short Trigger: Harga menusuk ke atas Upper Band (Overbought FOMO Wick),
       lalu lilin konfirmasi MENEMBUS KEMBALI KE BAWAH (Reclaim) Upper Band dengan RSI overbought (> 70 reject).
    4. TP Target Cepat: Mid-Band (SMA 20) / +0.40% s/d +0.60%
    5. SL Protektif: Di bawah ekor jarum/wick (max 0.30% - 0.40%)
    """
    def __init__(self, bb_period: int = 20, bb_std: float = 2.2, rsi_period: int = 9, ema_trend: int = 50):
        super().__init__(name="Ultra 1M Reclaim Scalper")
        self.bb_period = bb_period
        self.bb_std = bb_std
        self.rsi_period = rsi_period
        self.ema_trend = ema_trend

    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        
        # 1. Bollinger Bands
        df['sma_mid'] = df['close'].rolling(window=self.bb_period).mean()
        df['bb_std'] = df['close'].rolling(window=self.bb_period).std()
        df['bb_upper'] = df['sma_mid'] + (df['bb_std'] * self.bb_std)
        df['bb_lower'] = df['sma_mid'] - (df['bb_std'] * self.bb_std)
        
        # 2. EMA Trend Filter
        df['ema_trend'] = df['close'].ewm(span=self.ema_trend, adjust=False).mean()
        
        # 3. RSI
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=self.rsi_period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=self.rsi_period).mean()
        rs = gain / (loss + 1e-9)
        df['rsi'] = 100 - (100 / (1 + rs))
        
        # 4. Volume Spike Filter
        df['vol_ma'] = df['volume'].rolling(window=15).mean()
        df['vol_active'] = df['volume'] > (df['vol_ma'] * 0.8)

        df['signal'] = 0
        df['stop_loss'] = np.nan
        df['take_profit'] = np.nan

        for i in range(max(self.bb_period, self.ema_trend) + 2, len(df)):
            close_curr = df['close'].iloc[i]
            close_prev = df['close'].iloc[i-1]
            low_prev = df['low'].iloc[i-1]
            high_prev = df['high'].iloc[i-1]
            
            bb_l_curr = df['bb_lower'].iloc[i]
            bb_l_prev = df['bb_lower'].iloc[i-1]
            bb_u_curr = df['bb_upper'].iloc[i]
            bb_u_prev = df['bb_upper'].iloc[i-1]
            bb_m = df['sma_mid'].iloc[i]
            
            ema_t = df['ema_trend'].iloc[i]
            rsi = df['rsi'].iloc[i]
            rsi_prev = df['rsi'].iloc[i-1]
            vol_ok = df['vol_active'].iloc[i]

            # 🟢 BUY SETUP (Panic Wick Reclaim):
            # Lilin sebelumnya tembus ke bawah Lower Band (atau wick menusuk bawah), lilin sekarang close di atas Lower Band
            # RSI oversold < 35 lalu naik
            lower_pierce = (low_prev <= bb_l_prev) or (close_prev < bb_l_prev)
            reclaim_up = (close_curr > bb_l_curr) and (close_curr > close_prev)
            rsi_bounce = (rsi_prev <= 38) and (rsi > rsi_prev)

            if lower_pierce and reclaim_up and rsi_bounce and vol_ok:
                df.iloc[i, df.columns.get_loc('signal')] = 1
                sl = min(low_prev, df['low'].iloc[i]) * 0.9985
                sl = max(sl, close_curr * 0.9955) # max 0.45% SL
                tp = max(bb_m, close_curr + (close_curr - sl) * 1.5)
                df.iloc[i, df.columns.get_loc('stop_loss')] = sl
                df.iloc[i, df.columns.get_loc('take_profit')] = tp
                continue

            # 🔴 SELL SETUP (FOMO Wick Reclaim / Rejection):
            # Lilin sebelumnya tembus ke atas Upper Band, lilin sekarang close di bawah Upper Band
            # RSI overbought > 65 lalu turun
            upper_pierce = (high_prev >= bb_u_prev) or (close_prev > bb_u_prev)
            reclaim_down = (close_curr < bb_u_curr) and (close_curr < close_prev)
            rsi_reject = (rsi_prev >= 62) and (rsi < rsi_prev)

            if upper_pierce and reclaim_down and rsi_reject and vol_ok:
                df.iloc[i, df.columns.get_loc('signal')] = -1
                sl = max(high_prev, df['high'].iloc[i]) * 1.0015
                sl = min(sl, close_curr * 1.0045) # max 0.45% SL
                tp = min(bb_m, close_curr - (sl - close_curr) * 1.5)
                df.iloc[i, df.columns.get_loc('stop_loss')] = sl
                df.iloc[i, df.columns.get_loc('take_profit')] = tp

        return df
